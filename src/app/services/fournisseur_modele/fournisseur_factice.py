"""Fournisseur **factice** — déterministe, sans réseau, utilisé par les tests.

**Avertissement explicite : ce n'est pas une intelligence artificielle.** Ce
fournisseur ne « comprend » rien : il applique des règles de lecture mécaniques sur
du texte, et ne produit jamais autre chose que ce qui est écrit dans le document.

- Aucun réseau, aucun modèle, aucune clé. Le résultat est reproductible au caractère
  près, ce qui est exactement ce qu'un test exige.
- Il ne remplit **jamais** un vide : si une section attendue est absente, il ne renvoie
  rien pour cette catégorie (l'orchestration écrira « non trouvé dans le document »).
- Chaque proposition porte l'extrait littéral de la ligne lue et son emplacement
  (page + section), donc chaque proposition survive au contrôle de source de
  `base.verifier_propositions`.

Règles appliquées (documentées pour être contestables) :

``R1 — pièces exigées``
    Dans une section dont le titre contient « pièce » et « exig », chaque ligne
    commençant par « - » donne une pièce exigée.
``R2 — critères``
    Dans une section dont le titre contient « critère », chaque ligne de la forme
    « - libellé : NN % » donne un critère, avec la pondération **telle qu'écrite**.
``R3 — date limite``
    Dans une section dont le titre contient « date limite », la première date
    reconnue (ISO `AAAA-MM-JJ` ou `JJ mois AAAA` en français) donne la date limite,
    convertie en ISO 8601. Le libellé reprend la ligne littérale : aucune tournure
    n'est inventée.
"""

from __future__ import annotations

import re
from typing import Optional

from app.services.extraction_pdf import ExtractionPdf, PageExtraite
from app.services.fournisseur_modele.base import (
    FournisseurModele,
    PropositionElement,
    ResultatAnalyse,
)

#: Titres de section reconnus. Volontairement grossiers : une règle de lecture, pas
#: une compréhension.
_MOTIF_SECTION_PIECES = re.compile(r"pi[eè]ces?.{0,20}exig", re.IGNORECASE)
_MOTIF_SECTION_CRITERES = re.compile(r"crit[eè]res?", re.IGNORECASE)
_MOTIF_SECTION_DATE = re.compile(r"date\s+limite", re.IGNORECASE)

#: Une ligne de liste : « - texte » (tiret simple, en début de ligne).
_MOTIF_LIGNE_LISTE = re.compile(r"^\s*[-•]\s*(?P<contenu>.+?)\s*$")
#: Un critère pondéré : « libellé : 40 % » (la pondération vient du document).
_MOTIF_CRITERE = re.compile(
    r"^\s*[-•]\s*(?P<libelle>.+?)\s*:\s*(?P<ponderation>\d{1,3})\s*%\s*$"
)
#: Une ligne de titre de section, ex. « Article 4 — Pièces exigées ».
_MOTIF_TITRE = re.compile(r"^\s*(ARTICLE\b.*|[IVX]+\.\s+.*|[0-9]+\.\s+.*)$")

#: Dates reconnues.
_MOTIF_DATE_ISO = re.compile(r"\b(?P<annee>\d{4})-(?P<mois>\d{2})-(?P<jour>\d{2})\b")
_MOTIF_DATE_FR = re.compile(
    r"\b(?P<jour>\d{1,2})\s+(?P<mois>janvier|février|fevrier|mars|avril|mai|juin|juillet|"
    r"août|aout|septembre|octobre|novembre|décembre|decembre)\s+(?P<annee>\d{4})\b",
    re.IGNORECASE,
)

_MOIS_FR = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}

MENTION_FICTIF = "DOCUMENT FICTIF — DÉMONSTRATION"


def _titre_section(ligne: str) -> bool:
    return bool(_MOTIF_TITRE.match(ligne))


def _date_iso(ligne: str) -> Optional[str]:
    """Première date reconnue d'une ligne, en ISO 8601. `None` si aucune."""
    trouve = _MOTIF_DATE_ISO.search(ligne)
    if trouve:
        return f"{trouve.group('annee')}-{trouve.group('mois')}-{trouve.group('jour')}"
    trouve = _MOTIF_DATE_FR.search(ligne)
    if trouve:
        mois = _MOIS_FR[trouve.group("mois").casefold()]
        return f"{trouve.group('annee')}-{mois:02d}-{int(trouve.group('jour')):02d}"
    return None


class FournisseurFactice(FournisseurModele):
    """Fournisseur déterministe, **sans aucune capacité d'interprétation**."""

    nom = "factice"
    modele = "regles-de-lecture-v1"

    @property
    def avertissement(self) -> str:
        return (
            "Fournisseur factice — non-IQ réel : règles de lecture mécaniques, sans modèle "
            "de langage. Aucun élément n'est compris ni déduit ; les tests ne prouvent donc "
            "pas la qualité d'une analyse par un vrai modèle (risque R3)."
        )

    def description(self) -> str:
        return f"{self.nom} ({self.modele}) — non-IQ réel, hors réseau"

    # -- analyse ---------------------------------------------------------------
    def analyser(self, extraction: ExtractionPdf) -> ResultatAnalyse:
        propositions: list[PropositionElement] = []
        for page in extraction.pages:
            propositions.extend(self._lire_page(page))
        return ResultatAnalyse(
            propositions=tuple(propositions),
            fournisseur=self.nom,
            modele=self.modele,
            avertissement=self.avertissement,
        )

    # -- lecture d'une page ----------------------------------------------------
    def _lire_page(self, page: PageExtraite) -> list[PropositionElement]:
        if not page.analyseable:
            # Une page non analysable ne produit rien : elle n'est jamais devinée.
            return []

        resultats: list[PropositionElement] = []
        section: Optional[str] = None
        type_section: Optional[str] = None
        date_limite_vue = False

        for brute in page.texte.splitlines():
            ligne = brute.rstrip()
            if _titre_section(ligne):
                section = ligne.strip()
                if _MOTIF_SECTION_PIECES.search(section):
                    type_section = "pieces"
                elif _MOTIF_SECTION_CRITERES.search(section):
                    type_section = "criteres"
                elif _MOTIF_SECTION_DATE.search(section):
                    type_section = "date"
                else:
                    type_section = None
                continue

            if type_section is None:
                continue

            emplacement = (
                f"page {page.numero} — section « {section} »" if section
                else f"page {page.numero}"
            )

            if type_section == "pieces":
                liste = _MOTIF_LIGNE_LISTE.match(ligne)
                if liste:
                    resultats.append(
                        PropositionElement(
                            categorie="piece_exigee",
                            libelle=liste.group("contenu"),
                            source_emplacement=emplacement,
                            source_extrait=liste.group("contenu"),
                        )
                    )
                continue

            if type_section == "criteres":
                critere = _MOTIF_CRITERE.match(ligne)
                if critere:
                    resultats.append(
                        PropositionElement(
                            categorie="critere",
                            libelle=critere.group("libelle"),
                            valeur=f"{critere.group('ponderation')} %",
                            source_emplacement=emplacement,
                            source_extrait=ligne.strip(),
                        )
                    )
                continue

            if type_section == "date" and not date_limite_vue:
                date_iso = _date_iso(ligne)
                if date_iso:
                    date_limite_vue = True
                    resultats.append(
                        PropositionElement(
                            categorie="date_limite",
                            libelle=ligne.strip(),
                            valeur=date_iso,
                            source_emplacement=emplacement,
                            source_extrait=ligne.strip(),
                        )
                    )
        return resultats
