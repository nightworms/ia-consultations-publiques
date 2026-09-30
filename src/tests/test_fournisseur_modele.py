"""Tests de la couche d'abstraction du fournisseur de modèle (D8, annexe A § A7).

Aucune donnée réelle, **aucun appel réseau** : le fournisseur réel est exercé avec un
transport HTTP **simulé en mémoire** (`httpx.MockTransport`), ce qui vérifie la lecture
de la réponse et le refus des valeurs inventées sans sortir de la machine.

Ce que ces tests ne prouvent pas, et qui est écrit franchement : la **qualité** d'une
analyse produite par un vrai grand modèle. Aucune clé d'API n'est disponible (risque R3).
"""

from __future__ import annotations

import json
import socket

import httpx
import pytest

from app.services import extraction_pdf
from app.services.extraction_pdf import ExtractionPdf, PageExtraite
from app.services.fournisseur_modele import (
    FOURNISSEUR_DEFAUT,
    FournisseurFactice,
    ErreurFournisseurModele,
    ReponseModeleInvalide,
    creer_fournisseur,
    verifier_propositions,
)
from app.services.fournisseur_modele.base import PropositionElement, source_presente
from app.services.fournisseur_modele.fournisseur_ue import (
    CONSIGNE,
    FournisseurUe,
    NOM_VARIABLE_CLE,
    NOM_VARIABLE_MODELE,
    NOM_VARIABLE_URL,
)

TEXTE_FICTIF = """DOCUMENT FICTIF — DÉMONSTRATION

ARTICLE 2 — PIÈCES EXIGÉES
- Attestation d'assurance décennale (document fictif)
- Mémoire technique présentant les moyens affectés

ARTICLE 3 — CRITÈRES D'ATTRIBUTION
- Prix des prestations : 40 %
- Valeur technique de l'offre : 35 %

ARTICLE 4 — DATE LIMITE DE REMISE DES OFFRES
La date limite de remise des offres est fixée au 15 décembre 2026 à 12h00.
"""

TEXTE_SANS_SECTIONS = """DOCUMENT FICTIF — DÉMONSTRATION
Un texte sans section reconnaissable : aucune pièce, aucun critère, aucune date.
"""


def _extraction(texte: str, numero: int = 1) -> ExtractionPdf:
    return ExtractionPdf(
        source="fictif.txt",
        pages=(
            PageExtraite(numero=numero, texte=texte, methode="texte", analyseable=True),
        ),
    )


# --------------------------------------------------------------------------- #
# 1. Sélection du fournisseur
# --------------------------------------------------------------------------- #
def test_fournisseur_par_defaut_est_le_factice(monkeypatch):
    monkeypatch.delenv("MODELE_FOURNISSEUR", raising=False)
    fournisseur = creer_fournisseur()
    assert isinstance(fournisseur, FournisseurFactice)
    assert fournisseur.nom == FOURNISSEUR_DEFAUT
    assert "non-IQ" in fournisseur.description() or "sans modèle" in fournisseur.avertissement


def test_fournisseur_inconnu_refuse_explicitement(monkeypatch):
    with pytest.raises(ErreurFournisseurModele) as exc:
        creer_fournisseur("chatgpt-hors-ue")
    assert "inconnu" in str(exc.value)


def test_fournisseur_ue_exige_ses_variables_d_environnement(monkeypatch):
    """Sans configuration, l'erreur est explicite — et aucun appel n'est tenté."""
    for nom in (NOM_VARIABLE_URL, NOM_VARIABLE_CLE, NOM_VARIABLE_MODELE):
        monkeypatch.delenv(nom, raising=False)
    with pytest.raises(ErreurFournisseurModele) as exc:
        creer_fournisseur("ue")
    assert NOM_VARIABLE_URL in str(exc.value)


# --------------------------------------------------------------------------- #
# 2. Fournisseur factice : déterministe, hors réseau, sans invention
# --------------------------------------------------------------------------- #
def test_factice_est_deterministe():
    fournisseur = FournisseurFactice()
    premier = fournisseur.analyser(_extraction(TEXTE_FICTIF))
    second = fournisseur.analyser(_extraction(TEXTE_FICTIF))
    assert premier.propositions == second.propositions
    assert premier.propositions  # sinon le test ne prouverait rien


def test_factice_n_ouvre_aucune_connexion_reseau(monkeypatch):
    """Si le fournisseur factice touchait au réseau, ce test échouerait."""

    def _interdit(*args, **kwargs):  # pragma: no cover — ne doit jamais être appelé
        raise AssertionError("Le fournisseur factice ne doit pas ouvrir de socket.")

    monkeypatch.setattr(socket, "socket", _interdit)
    resultat = FournisseurFactice().analyser(_extraction(TEXTE_FICTIF))
    assert resultat.propositions


def test_factice_extrait_les_trois_categories_avec_source():
    resultat = FournisseurFactice().analyser(_extraction(TEXTE_FICTIF))
    categories = {p.categorie for p in resultat.propositions}
    assert categories == {"piece_exigee", "critere", "date_limite"}

    criteres = [p for p in resultat.propositions if p.categorie == "critere"]
    assert {c.valeur for c in criteres} == {"40 %", "35 %"}  # pondération telle qu'écrite

    dates = [p for p in resultat.propositions if p.categorie == "date_limite"]
    assert dates[0].valeur == "2026-12-15"  # conversion en ISO 8601, date du document

    for proposition in resultat.propositions:
        assert proposition.source_emplacement.startswith("page 1")
        assert proposition.source_extrait
        assert source_presente(proposition, _extraction(TEXTE_FICTIF).pages)


def test_factice_ne_produit_rien_quand_le_document_ne_dit_rien():
    """Aucune section reconnue ⇒ aucune proposition. Le vide n'est jamais comblé."""
    resultat = FournisseurFactice().analyser(_extraction(TEXTE_SANS_SECTIONS))
    assert resultat.propositions == ()


def test_factice_ne_lit_pas_une_page_non_analysable():
    extraction = ExtractionPdf(
        source="scan.pdf",
        pages=(
            PageExtraite(
                numero=1,
                texte="",
                methode="non_analysable",
                analyseable=False,
                message="Page non analysable.",
            ),
        ),
    )
    assert FournisseurFactice().analyser(extraction).propositions == ()


# --------------------------------------------------------------------------- #
# 3. Contrôle des sources : une valeur inventée est refusée
# --------------------------------------------------------------------------- #
def test_proposition_sans_source_est_refusee():
    pages = _extraction(TEXTE_FICTIF).pages
    inventee = PropositionElement(
        categorie="date_limite",
        libelle="La date limite est fixée au 3 janvier 2027.",
        valeur="2027-01-03",
        source_emplacement="page 1 — section « Article 4 »",
        source_extrait="La date limite est fixée au 3 janvier 2027.",  # absent du document
    )
    with pytest.raises(ReponseModeleInvalide) as exc:
        verifier_propositions([inventee], pages)
    assert "introuvable" in str(exc.value)


def test_proposition_sans_emplacement_est_refusee():
    pages = _extraction(TEXTE_FICTIF).pages
    sans_emplacement = PropositionElement(
        categorie="critere",
        libelle="Prix des prestations",
        source_emplacement="   ",
        source_extrait="Prix des prestations",
    )
    with pytest.raises(ReponseModeleInvalide):
        verifier_propositions([sans_emplacement], pages)


def test_categorie_hors_contrat_refusee():
    pages = _extraction(TEXTE_FICTIF).pages
    hors_contrat = PropositionElement(
        categorie="prix_propose",
        libelle="Prix",
        source_emplacement="page 1",
        source_extrait="Prix des prestations",
    )
    with pytest.raises(ReponseModeleInvalide):
        verifier_propositions([hors_contrat], pages)


def test_propositions_sourcees_sont_acceptees():
    resultat = FournisseurFactice().analyser(_extraction(TEXTE_FICTIF))
    retenues = verifier_propositions(resultat.propositions, _extraction(TEXTE_FICTIF).pages)
    assert len(retenues) == len(resultat.propositions)


# --------------------------------------------------------------------------- #
# 4. Fournisseur UE : lecture de réponse, sans réseau
# --------------------------------------------------------------------------- #
def _fournisseur_simule(charge: dict, *, code: int = 200) -> tuple[FournisseurUe, list]:
    appels: list[httpx.Request] = []

    def _repondre(request: httpx.Request) -> httpx.Response:
        appels.append(request)
        if code != 200:
            return httpx.Response(code, json={"erreur": "refus"})
        return httpx.Response(200, json=charge)

    transport = httpx.MockTransport(_repondre)  # en mémoire : aucun accès réseau
    client = httpx.Client(transport=transport)
    fournisseur = FournisseurUe(
        url="https://exemple-fictif.invalid/v1/chat/completions",
        cle="cle-fictive-de-test",
        modele="modele-fictif",
        organisme="Fournisseur fictif (UE)",
        client_http=client,
    )
    return fournisseur, appels


def _charge_modele(elements: list[dict]) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"elements": elements}, ensure_ascii=False)
                }
            }
        ]
    }


def test_ue_lit_une_reponse_conforme_et_ne_sort_pas_sur_le_reseau():
    charge = _charge_modele(
        [
            {
                "categorie": "date_limite",
                "libelle": "La date limite de remise des offres est fixée au 15 décembre 2026 à 12h00.",
                "valeur": "2026-12-15",
                "source_emplacement": "page 1 — Article 4",
                "source_extrait": "La date limite de remise des offres est fixée au 15 décembre 2026 à 12h00.",
            }
        ]
    )
    fournisseur, appels = _fournisseur_simule(charge)
    resultat = fournisseur.analyser(_extraction(TEXTE_FICTIF))
    assert len(appels) == 1  # la requête a bien été construite…
    # … mais elle n'est pas partie sur Internet : le transport est simulé en mémoire.
    assert appels[0].url.host == "exemple-fictif.invalid"
    assert resultat.fournisseur == "ue"
    assert resultat.modele == "modele-fictif"
    assert resultat.propositions[0].valeur == "2026-12-15"

    # L'en-tête d'authentification vient de la variable de test, jamais du dépôt.
    assert appels[0].headers["authorization"] == "Bearer cle-fictive-de-test"
    assert "cle-fictive-de-test" not in fournisseur.description()
    assert CONSIGNE.split(".")[0] in json.loads(appels[0].content.decode("utf-8"))["messages"][0][
        "content"
    ]


def test_ue_rejette_une_valeur_inventee_par_le_modele():
    """Un modèle qui reformule n'est pas une source : la proposition est rejetée."""
    charge = _charge_modele(
        [
            {
                "categorie": "critere",
                "libelle": "Prix",
                "valeur": "50 %",
                "source_emplacement": "page 1",
                "source_extrait": "Prix des prestations : 50 %",
            }
        ]
    )
    fournisseur, _ = _fournisseur_simule(charge)
    resultat = fournisseur.analyser(_extraction(TEXTE_FICTIF))
    with pytest.raises(ReponseModeleInvalide):
        verifier_propositions(resultat.propositions, _extraction(TEXTE_FICTIF).pages)


def test_ue_refuse_une_reponse_hors_format():
    fournisseur, _ = _fournisseur_simule({"choices": []})
    with pytest.raises(ReponseModeleInvalide):
        fournisseur.analyser(_extraction(TEXTE_FICTIF))


def test_ue_erreur_http_explicite():
    fournisseur, _ = _fournisseur_simule({}, code=503)
    with pytest.raises(ErreurFournisseurModele) as exc:
        fournisseur.analyser(_extraction(TEXTE_FICTIF))
    assert "503" in str(exc.value)
    assert "cle-fictive-de-test" not in str(exc.value)


def test_ue_lit_une_reponse_entouree_de_markdown():
    fournisseur, _ = _fournisseur_simule({})
    contenu = '```json\n{"elements": []}\n```'
    assert fournisseur.lire_reponse(contenu) == ()


def test_ue_refuse_une_categorie_hors_contrat():
    fournisseur, _ = _fournisseur_simule({})
    contenu = json.dumps(
        {"elements": [{"categorie": "prix", "libelle": "x", "source_emplacement": "p1",
                       "source_extrait": "x"}]}
    )
    with pytest.raises(ReponseModeleInvalide):
        fournisseur.lire_reponse(contenu)


# --------------------------------------------------------------------------- #
# 5. La couche d'abstraction est bien... une couche
# --------------------------------------------------------------------------- #
def test_ocr_disponible_est_annonce_sans_detour():
    """Le chemin OCR n'est ni supposé ni maquillé : son état est interrogeable."""
    assert isinstance(extraction_pdf.ocr_disponible(), bool)
