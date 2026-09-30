"""Test de non-régression : `pdftotext` doit rester sans `-layout`.

Cas réel qui a motivé ce test (30/09/2026) : sur un DCE de 10 pages, `-layout`
recollait sur une même ligne les deux colonnes d'un tableau et **injectait le
libellé de la colonne voisine au milieu d'une phrase du corps** — lu
« …l'importance du *effectifs moyens et importance* personnel d'encadrement… »
au lieu de « …l'importance du personnel d'encadrement… ». Le modèle citait la
phrase correcte, la vérification de source la rejetait comme non adossée au
document, et l'analyse entière échouait en 500. Le correctif est le retrait de
`-layout` ; ce fichier le verrouille.

Limite connue : sur une page réellement tabulaire, l'ordre de lecture **sans**
`-layout` peut mélanger les colonnes autrement. Ce compromis est retenu pour un
cas ; il devra être réévalué sur plusieurs DCE réels avant d'être figé.

Le document employé est **généré** par `src/tests/fixtures/generer_fixtures.py`
(fixture `dce_fictif_deux_colonnes.pdf`) : aucun document d'acheteur, aucune
donnée réelle n'entre dans le dépôt (règle D10).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.services import extraction_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF_DEUX_COLONNES = FIXTURES / "dce_fictif_deux_colonnes.pdf"

#: Phrase du corps de la fixture — elle doit rester **contiguë** dans le texte lu.
PHRASE_DU_CORPS = "importance du personnel d'encadrement"

#: Ce que produit `-layout` : la colonne latérale soudée au milieu de la phrase.
PHRASE_CORROMPUE = "importance du Effectifs moyens et importance personnel d'encadrement"

#: Libellé de la colonne latérale — sa présence prouve que la fixture est bien lue
#: (sans quoi l'assertion de contiguïté passerait sur un texte vide).
LIBELLE_LATERAL = "Effectifs moyens et importance"

#: Dernière ligne du corps, pour vérifier que la page est lue en entier.
FIN_DU_CORPS = "maitrise des delais"


def _normaliser(texte: str) -> str:
    """Réduit toute suite d'espaces à un seul, pour qu'un saut de ligne ne puisse
    pas masquer une colonne soudée au milieu d'une phrase."""
    return re.sub(r"\s+", " ", texte)


def _page_unique():
    """Extrait la fixture et renvoie sa page 1, en exigeant une lecture par texte."""
    extraction = extraction_pdf.extraire(PDF_DEUX_COLONNES)
    assert extraction.nombre_pages == 1, (
        f"la fixture doit tenir sur une page, {extraction.nombre_pages} page(s) lue(s) "
        f"— régénérer avec : .venv/bin/python src/tests/fixtures/generer_fixtures.py"
    )
    page = extraction.page(1)
    assert page is not None
    assert page.methode == "texte" and page.analyseable, (
        f"la fixture doit être lue comme page textuelle, méthode obtenue : {page.methode}"
    )
    return page


def test_la_phrase_du_corps_reste_contigue() -> None:
    """La phrase du corps ne doit pas être coupée par le libellé de la colonne voisine.

    Échoue si `-layout` est réintroduit dans `app/services/extraction_pdf.py`
    (fonction `_texte_page`) : la colonne latérale vient alors s'insérer entre
    « …du » et « personnel d'encadrement ».
    """
    texte = _normaliser(_page_unique().texte)
    assert LIBELLE_LATERAL in texte, (
        "la colonne latérale de la fixture n'a pas été lue : le test ne prouverait rien."
    )
    assert FIN_DU_CORPS in texte, "le corps de la fixture n'a pas été lu en entier."
    assert PHRASE_DU_CORPS in texte, (
        f"la phrase du corps a été coupée par la colonne voisine : « {PHRASE_DU_CORPS} » "
        f"est absente du texte lu. `-layout` a probablement été réintroduit dans "
        f"`app/services/extraction_pdf.py` (fonction `_texte_page`).\n"
        f"Texte lu : {texte!r}"
    )
    assert PHRASE_CORROMPUE not in texte, (
        "le libellé de la colonne latérale a été recollé au milieu de la phrase du corps "
        f"— c'est exactement le défaut de `-layout`.\nTexte lu : {texte!r}"
    )


def test_aucune_ligne_ne_melange_les_deux_colonnes() -> None:
    """Aucune ligne lue ne doit porter à la fois du corps de texte et un libellé latéral.

    Formulation structurelle du même interdit : `-layout` aligne physiquement les deux
    colonnes, ce qui les fait cohabiter sur une même ligne de sortie.
    """
    lignes = _page_unique().texte.splitlines()
    melangees = [
        ligne
        for ligne in lignes
        if LIBELLE_LATERAL in ligne and "importance du" in ligne and len(ligne.strip()) > len(LIBELLE_LATERAL)
    ]
    assert not melangees, (
        "des lignes lues portent à la fois le corps de texte et la colonne latérale "
        f"— `-layout` a probablement été réintroduit : {melangees!r}"
    )
