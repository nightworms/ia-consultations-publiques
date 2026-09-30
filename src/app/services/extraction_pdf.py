"""Extraction du texte d'un document PDF, **page par page**, avec repli OCR.

Règles tenues ici (SPEC-MVP-V2 § 3.3, annexe A § A10) :

* Le texte est lu par `pdftotext` (poppler) — déjà présent, aucune dépendance Python.
* Une page **sans texte exploitable** (scan) passe par l'**OCR** (`tesseract`), si le
  binaire est présent. Sinon la page est signalée `ocr_indisponible`.
* Une page que ni le texte ni l'OCR ne rendent lisible est signalée
  **« non analysable »** : elle n'est **jamais devinée** et son contenu n'est jamais
  reconstitué (ligne rouge, SPEC-MVP-V2 § 2).
* Aucun appel réseau. Le résultat porte, pour chaque page, la **méthode** employée,
  pour que la source d'un élément extrait reste vérifiable.

Sortie : `ExtractionPdf` (pages + numéros). Elle est la seule entrée admise par la
couche `fournisseur_modele` : un fournisseur ne voit jamais le fichier, seulement le
texte réellement extrait et le numéro de page.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

#: Nombre minimal de caractères imprimables pour qu'une page soit jugée « textuelle ».
SEUIL_TEXTE_EXPLOITABLE = 40

#: Langues passées à `tesseract` par défaut (surchargeables par `OCR_LANGUES`).
LANGUES_OCR_DEFAUT = "fra"

#: Délai maximal d'une commande externe (secondes).
DELAI_COMMANDE = 120


class ErreurExtractionPdf(RuntimeError):
    """Extraction impossible : outil absent, fichier illisible, commande en échec."""


@dataclass(frozen=True)
class PageExtraite:
    """Une page du document, telle qu'elle a réellement été lue."""

    numero: int
    texte: str
    methode: str  # "texte" | "ocr" | "non_analysable"
    analyseable: bool
    message: Optional[str] = None

    @property
    def est_vide(self) -> bool:
        return not self.texte.strip()


@dataclass(frozen=True)
class ExtractionPdf:
    """Résultat d'extraction : les pages, dans l'ordre du document."""

    source: str
    pages: tuple[PageExtraite, ...] = field(default_factory=tuple)

    @property
    def nombre_pages(self) -> int:
        return len(self.pages)

    @property
    def texte_complet(self) -> str:
        """Texte concaténé, chaque page préfixée par son numéro (traçable)."""
        return "\n".join(
            f"[page {page.numero}]\n{page.texte}" for page in self.pages
        )

    @property
    def pages_non_analysables(self) -> tuple[int, ...]:
        return tuple(p.numero for p in self.pages if not p.analyseable)

    @property
    def ocr_utilise(self) -> bool:
        return any(p.methode == "ocr" for p in self.pages)

    def page(self, numero: int) -> Optional[PageExtraite]:
        for page in self.pages:
            if page.numero == numero:
                return page
        return None

    def resume(self) -> list[dict[str, object]]:
        """Résumé par page, destiné à l'affichage « quels fichiers sont lisibles »."""
        return [
            {
                "page": p.numero,
                "methode": p.methode,
                "analyseable": p.analyseable,
                "caracteres": len(p.texte.strip()),
                "message": p.message,
            }
            for p in self.pages
        ]


# --------------------------------------------------------------------------- #
# Outils externes
# --------------------------------------------------------------------------- #
def _chemin_outil(nom: str) -> Optional[str]:
    return shutil.which(nom)


def _exiger_outil(nom: str) -> str:
    chemin = _chemin_outil(nom)
    if chemin is None:
        raise ErreurExtractionPdf(
            f"Outil requis absent : `{nom}`. Installez poppler (`pdftotext`, `pdfinfo`, "
            "`pdftoppm`) ; pour l'OCR, installez `tesseract`."
        )
    return chemin


def ocr_disponible() -> bool:
    """Vrai si l'OCR peut réellement être tenté sur cette machine."""
    return _chemin_outil("tesseract") is not None


def _executer(commande: Sequence[str], *, binaire: bool = False) -> subprocess.CompletedProcess:
    """Lance une commande externe et remonte l'échec de façon explicite.

    Aucune erreur n'est avalée : la sortie d'erreur réelle accompagne l'exception.
    """
    try:
        return subprocess.run(  # noqa: S603 — commande construite par le code, sans shell
            list(commande),
            capture_output=True,
            text=not binaire,
            timeout=DELAI_COMMANDE,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ErreurExtractionPdf(
            f"Commande interrompue après {DELAI_COMMANDE} s : {' '.join(commande)}"
        ) from exc
    except OSError as exc:  # pragma: no cover — dépend de l'environnement
        raise ErreurExtractionPdf(
            f"Commande impossible : {' '.join(commande)} ({exc})"
        ) from exc


# --------------------------------------------------------------------------- #
# Lecture d'un PDF
# --------------------------------------------------------------------------- #
def nombre_de_pages(chemin: str | os.PathLike[str]) -> int:
    """Nombre de pages, lu par `pdfinfo`. Échec explicite si le PDF est illisible."""
    fichier = Path(chemin)
    if not fichier.is_file():
        raise ErreurExtractionPdf(f"Fichier introuvable : {fichier}")
    pdfinfo = _exiger_outil("pdfinfo")
    resultat = _executer([pdfinfo, str(fichier)])
    if resultat.returncode != 0:
        raise ErreurExtractionPdf(
            f"PDF illisible ({fichier.name}) : {resultat.stderr.strip() or 'pdfinfo a échoué'}"
        )
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith("Pages:"):
            valeur = ligne.split(":", 1)[1].strip()
            if valeur.isdigit():
                return int(valeur)
    raise ErreurExtractionPdf(
        f"Nombre de pages introuvable dans la sortie de pdfinfo pour {fichier.name}."
    )


def _texte_page(chemin: Path, numero: int) -> str:
    """Texte d'une seule page, via `pdftotext` (aucune concaténation de commande).

    **`-layout` volontairement retiré** (correctif du 30/09/2026). Sur un vrai DCE de
    la Commune de Saint-Denis (RC « régénération des pelouses des stades », 10 pages),
    `-layout` recollait les colonnes d'un tableau sur une même ligne et **injectait
    le libellé de la colonne voisine au milieu d'une phrase** :

        source lue avec -layout : « …l'importance du **effectifs moyens et importance**
                                     personnel d'encadrement… »

    Le modèle citait la phrase correcte ; la vérification de source la rejetait, et
    l'analyse entière échouait sur un document pourtant lisible. `pdftotext` sans
    `-layout` restitue l'ordre de lecture et donne le texte attendu.

    Conséquence à surveiller : sur une page réellement tabulaire, l'ordre de lecture
    sans `-layout` peut mélanger les colonnes autrement. Le choix mérite d'être
    réévalué par un agent sur plusieurs DCE réels, et non figé ici sur un seul cas.
    """
    pdftotext = _exiger_outil("pdftotext")
    resultat = _executer(
        [
            pdftotext,
            "-f", str(numero),
            "-l", str(numero),
            "-enc", "UTF-8",
            str(chemin),
            "-",
        ]
    )
    if resultat.returncode != 0:
        raise ErreurExtractionPdf(
            f"pdftotext a échoué sur la page {numero} de {chemin.name} : "
            f"{resultat.stderr.strip()}"
        )
    return resultat.stdout


def _ocr_page(chemin: Path, numero: int, repertoire_travail: Path) -> tuple[str, Optional[str]]:
    """OCR d'une page : rasterisation (`pdftoppm`) puis `tesseract` sur l'image.

    Renvoie (texte, message). Le message explique un échec éventuel sans jamais
    fabriquer de contenu.
    """
    if not ocr_disponible():
        return "", "OCR indisponible : binaire `tesseract` absent de la machine."

    pdftoppm = _exiger_outil("pdftoppm")
    tesseract = _exiger_outil("tesseract")
    prefixe = repertoire_travail / f"page_{numero}"
    rendu = _executer(
        [
            pdftoppm,
            "-f", str(numero),
            "-l", str(numero),
            "-r", "300",
            "-jpeg",
            "-singlefile",
            str(chemin),
            str(prefixe),
        ]
    )
    image = prefixe.with_suffix(".jpg")
    if rendu.returncode != 0 or not image.is_file():
        return "", (
            "Rasterisation impossible (pdftoppm) : "
            f"{rendu.stderr.strip() or 'aucune image produite'}"
        )

    langues = os.environ.get("OCR_LANGUES", LANGUES_OCR_DEFAUT).strip() or LANGUES_OCR_DEFAUT
    resultat = _executer([tesseract, str(image), "stdout", "-l", langues])
    if resultat.returncode != 0:
        # Repli explicite : les données de langue demandées peuvent manquer.
        message = resultat.stderr.strip().splitlines()
        court = message[-1] if message else "échec de tesseract"
        repli = _executer([tesseract, str(image), "stdout"])
        if repli.returncode == 0:
            return repli.stdout, f"Langues « {langues} » indisponibles, OCR en langue par défaut ({court})."
        return "", f"Échec de l’OCR (tesseract) : {court}"
    return resultat.stdout, None


def _texte_exploitable(texte: str) -> bool:
    return len("".join(texte.split())) >= SEUIL_TEXTE_EXPLOITABLE


def extraire(
    chemin: str | os.PathLike[str],
    *,
    ocr: bool = True,
    repertoire_travail: Optional[str | os.PathLike[str]] = None,
) -> ExtractionPdf:
    """Extrait le texte du PDF, page par page, avec repli OCR.

    `ocr=False` désactive le repli (utile pour montrer que le chemin texte seul est
    insuffisant sur une page scannée). Une page reste « non analysable » si rien de
    lisible n'en sort : elle n'est ni devinée, ni complétée.
    """
    fichier = Path(chemin)
    total = nombre_de_pages(fichier)
    pages: list[PageExtraite] = []

    temporaire = (
        Path(repertoire_travail)
        if repertoire_travail is not None
        else None
    )
    if temporaire is not None:
        temporaire.mkdir(parents=True, exist_ok=True)
    contexte_travail = tempfile.TemporaryDirectory(prefix="extraction_pdf_")
    dossier = temporaire if temporaire is not None else Path(contexte_travail.name)

    try:
        for numero in range(1, total + 1):
            texte = _texte_page(fichier, numero)
            if _texte_exploitable(texte):
                pages.append(
                    PageExtraite(numero=numero, texte=texte, methode="texte", analyseable=True)
                )
                continue

            if not ocr:
                pages.append(
                    PageExtraite(
                        numero=numero,
                        texte="",
                        methode="non_analysable",
                        analyseable=False,
                        message=(
                            "Page sans texte exploitable ; repli OCR désactivé pour cet appel."
                        ),
                    )
                )
                continue

            texte_ocr, message = _ocr_page(fichier, numero, dossier)
            if _texte_exploitable(texte_ocr):
                pages.append(
                    PageExtraite(
                        numero=numero,
                        texte=texte_ocr,
                        methode="ocr",
                        analyseable=True,
                        message=message,
                    )
                )
            else:
                pages.append(
                    PageExtraite(
                        numero=numero,
                        texte="",
                        methode="non_analysable",
                        analyseable=False,
                        message=message
                        or "Page non analysable : aucun texte lisible (ni texte, ni OCR).",
                    )
                )
    finally:
        contexte_travail.cleanup()

    return ExtractionPdf(source=str(fichier), pages=tuple(pages))
