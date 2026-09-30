"""Génération des PDF fictifs de démonstration (outil de maintenance, hors test).

Rôle : fabriquer, **sans aucune dépendance Python nouvelle**, les PDF utilisés par
les tests de la brique B :

* `dce_fictif.pdf` — le DCE fictif, texte sélectionnable, une page par article ;
* `dce_fictif_sans_date.pdf` — variante sans date limite ni critère ;
* `dce_fictif_scanne.pdf` — la **variante « scannée »** : chaque page est une
  **image** (aucune couche texte), pour exercer réellement le chemin OCR.

Le texte PDF est écrit par un petit générateur PDF de la bibliothèque standard
(Helvetica, encodage WinAnsi) ; la variante scannée est obtenue en rasterisant ce
PDF avec `pdftoppm` (poppler, déjà présent) puis en ré-embarquant les images JPEG
dans un PDF — donc **aucun texte extractible**, exactement comme un scan.

Usage (depuis la racine du projet) :

    .venv/bin/python src/tests/fixtures/generer_fixtures.py

Tous les documents produits portent la mention « DOCUMENT FICTIF — DÉMONSTRATION ».
Aucune donnée réelle n'est utilisée.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent

LARGEUR_PAGE = 595  # A4 en points
HAUTEUR_PAGE = 842
MARGE_GAUCHE = 60
MARGE_HAUTE = 780
CORPS = 11
INTERLIGNE = 16


# --------------------------------------------------------------------------- #
# Écriture d'un PDF de texte minimal (bibliothèque standard uniquement)
# --------------------------------------------------------------------------- #
def _echapper(texte: str) -> bytes:
    """Encodage WinAnsi (cp1252) avec échappement des caractères réservés du PDF."""
    brut = texte.encode("cp1252", errors="replace")
    remplacements = {b"\\": b"\\\\", b"(": b"\\(", b")": b"\\)"}
    sortie = bytearray()
    for octet in brut:
        caractere = bytes([octet])
        sortie += remplacements.get(caractere, caractere)
    return bytes(sortie)


def _paginer(texte: str) -> list[list[str]]:
    """Découpe le texte en pages : une nouvelle page à chaque ligne `ARTICLE`."""
    pages: list[list[str]] = []
    courante: list[str] = []
    for ligne in texte.splitlines():
        if ligne.startswith("ARTICLE ") and courante:
            pages.append(courante)
            courante = []
        courante.append(ligne)
        if len(courante) >= 40:  # garde-fou de mise en page
            pages.append(courante)
            courante = []
    if courante or not pages:
        pages.append(courante)
    return pages


class _Pdf:
    """Assembleur PDF minimal (objets, contenu, table des références)."""

    def __init__(self) -> None:
        self._objets: list[bytes] = []

    def ajouter(self, contenu: bytes) -> int:
        self._objets.append(contenu)
        return len(self._objets)

    def remplacer(self, numero: int, contenu: bytes) -> None:
        """Renseigne un objet réservé (l'objet `/Pages` garde le numéro 2)."""
        self._objets[numero - 1] = contenu

    def rendre(self, racine: int) -> bytes:
        sortie = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        decalages = [0]
        for numero, contenu in enumerate(self._objets, start=1):
            decalages.append(len(sortie))
            sortie += f"{numero} 0 obj\n".encode("ascii") + contenu + b"\nendobj\n"
        debut_xref = len(sortie)
        total = len(self._objets) + 1
        sortie += f"xref\n0 {total}\n".encode("ascii")
        sortie += b"0000000000 65535 f \n"
        for decalage in decalages[1:]:
            sortie += f"{decalage:010d} 00000 n \n".encode("ascii")
        sortie += (
            f"trailer\n<< /Size {total} /Root {racine} 0 R >>\n"
            f"startxref\n{debut_xref}\n%%EOF\n"
        ).encode("ascii")
        return bytes(sortie)


def ecrire_pdf_texte(texte: str, chemin: Path) -> None:
    pdf = _Pdf()
    police = pdf.ajouter(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    pdf.ajouter(b"")  # objet 2 réservé : /Pages (doit exister avant les pages)
    pages = _paginer(texte)

    numeros_pages: list[int] = []
    corps_pages: list[bytes] = []
    for page in pages:
        flux = bytearray(b"BT\n")
        y = MARGE_HAUTE
        for ligne in page:
            flux += (
                f"/F1 {CORPS} Tf 1 0 0 1 {MARGE_GAUCHE} {y} Tm ".encode("ascii")
                + b"("
                + _echapper(ligne)
                + b") Tj\n"
            )
            y -= INTERLIGNE
        flux += b"ET\n"
        corps_pages.append(bytes(flux))

    for flux in corps_pages:
        contenu = pdf.ajouter(
            f"<< /Length {len(flux)} >>\nstream\n".encode("ascii") + flux + b"endstream"
        )
        numero_page = pdf.ajouter(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGEUR_PAGE} {HAUTEUR_PAGE}] "
                f"/Resources << /Font << /F1 {police} 0 R >> >> /Contents {contenu} 0 R >>"
            ).encode("ascii")
        )
        numeros_pages.append(numero_page)

    pdf.remplacer(
        2,
        (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{n} 0 R" for n in numeros_pages)
            + f"] /Count {len(numeros_pages)} >>"
        ).encode("ascii"),
    )
    racine = pdf.ajouter(b"<< /Type /Catalog /Pages 2 0 R >>")
    chemin.write_bytes(pdf.rendre(racine))


# --------------------------------------------------------------------------- #
# Variante « scannée » : des images, aucune couche texte
# --------------------------------------------------------------------------- #
def _dimensions_jpeg(donnees: bytes) -> tuple[int, int]:
    """Largeur et hauteur d'un JPEG, lues dans son marqueur SOF (stdlib)."""
    index = 2
    while index < len(donnees) - 1:
        if donnees[index] != 0xFF:
            index += 1
            continue
        marqueur = donnees[index + 1]
        if marqueur in (0xD8, 0xD9) or 0xD0 <= marqueur <= 0xD7:
            index += 2
            continue
        longueur = struct.unpack(">H", donnees[index + 2 : index + 4])[0]
        if marqueur in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
            hauteur, largeur = struct.unpack(">HH", donnees[index + 5 : index + 9])
            return largeur, hauteur
        index += 2 + longueur
    raise ValueError("Dimensions JPEG introuvables (marqueur SOF absent).")


def _rasteriser(pdf: Path, dossier: Path) -> list[Path]:
    """Rasterise chaque page en JPEG via `pdftoppm` (poppler)."""
    prefixe = dossier / "page"
    resultat = subprocess.run(  # noqa: S603 — commande fixe
        ["pdftoppm", "-jpeg", "-r", "150", str(pdf), str(prefixe)],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        raise RuntimeError(f"pdftoppm a échoué : {resultat.stderr.strip()}")
    images = sorted(dossier.glob("page-*.jpg"))
    if not images:
        raise RuntimeError("Aucune image produite par pdftoppm.")
    return images


def ecrire_pdf_scanne(pdf_source: Path, chemin: Path) -> None:
    """Ré-embarque les pages rasterisées dans un PDF **sans texte extractible**."""
    with tempfile.TemporaryDirectory(prefix="fixture_scan_") as temporaire:
        dossier = Path(temporaire)
        images = _rasteriser(pdf_source, dossier)
        pdf = _Pdf()
        pdf.ajouter(b"")  # objet 1 : réservé, non référencé
        pdf.ajouter(b"")  # objet 2 réservé : /Pages (doit exister avant les pages)
        numeros_pages: list[int] = []
        for image in images:
            donnees = image.read_bytes()
            largeur, hauteur = _dimensions_jpeg(donnees)
            flux_image = pdf.ajouter(
                (
                    f"<< /Type /XObject /Subtype /Image /Width {largeur} /Height {hauteur} "
                    f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                    f"/Length {len(donnees)} >>\nstream\n"
                ).encode("ascii")
                + donnees
                + b"\nendstream"
            )
            # Mise à l'échelle de l'image pour occuper la page A4.
            echelle = min(
                (LARGEUR_PAGE - 2 * MARGE_GAUCHE) / largeur,
                (HAUTEUR_PAGE - 100) / hauteur,
            )
            largeur_affichage = round(largeur * echelle, 2)
            hauteur_affichage = round(hauteur * echelle, 2)
            flux = (
                f"q\n{largeur_affichage} 0 0 {hauteur_affichage} {MARGE_GAUCHE} 60 cm\n"
                f"/Im0 Do\nQ\n"
            ).encode("ascii")
            contenu = pdf.ajouter(
                f"<< /Length {len(flux)} >>\nstream\n".encode("ascii") + flux + b"endstream"
            )
            numero_page = pdf.ajouter(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGEUR_PAGE} {HAUTEUR_PAGE}] "
                    f"/Resources << /XObject << /Im0 {flux_image} 0 R >> >> "
                    f"/Contents {contenu} 0 R >>"
                ).encode("ascii")
            )
            numeros_pages.append(numero_page)

        pdf.remplacer(
            2,
            (
                "<< /Type /Pages /Kids ["
                + " ".join(f"{n} 0 R" for n in numeros_pages)
                + f"] /Count {len(numeros_pages)} >>"
            ).encode("ascii"),
        )
        racine = pdf.ajouter(b"<< /Type /Catalog /Pages 2 0 R >>")
        chemin.write_bytes(pdf.rendre(racine))


def generer_tout() -> list[Path]:
    """Régénère les trois PDF fictifs. Renvoie les chemins écrits."""
    produits: list[Path] = []
    for nom_texte, nom_pdf in (
        ("dce_fictif.txt", "dce_fictif.pdf"),
        ("dce_fictif_sans_date.txt", "dce_fictif_sans_date.pdf"),
    ):
        texte = (ICI / nom_texte).read_text(encoding="utf-8")
        assert "DOCUMENT FICTIF" in texte, f"{nom_texte} doit porter la mention « DOCUMENT FICTIF »."
        destination = ICI / nom_pdf
        ecrire_pdf_texte(texte, destination)
        produits.append(destination)

    scanne = ICI / "dce_fictif_scanne.pdf"
    ecrire_pdf_scanne(ICI / "dce_fictif.pdf", scanne)
    produits.append(scanne)
    return produits


if __name__ == "__main__":  # pragma: no cover — outil de maintenance
    for chemin in generer_tout():
        print(f"écrit : {chemin} ({chemin.stat().st_size} octets)")
    sys.exit(0)
