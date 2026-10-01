"""Correction du défaut B1 — l'import guidé lit un document courant en français métier.

Défaut constaté par la vérification L8 : les documents du jeu de démonstration L7
(`scripts/jeu-de-test/fictif/*.txt`), écrits en français métier, ne produisaient
**aucune** proposition — le lecteur de démonstration ne reconnaissait que le
micro-format `Entité : …` / `- champ : valeur`.

Ce fichier verrouille la correction par exécution, sur les **documents réels du jeu
L7** (jamais sur une fixture au micro-format) :

1. les trois documents (plaquette → références, mémoire → chapitres, attestation →
   assurances) produisent au moins une proposition, chacune **sourcée** ;
2. aucune proposition enregistrée ne porte un extrait absent du document ;
3. une proposition dont l'extrait est inventé est **refusée** et rien n'est écrit,
   même sur un document courant (le garde-fou n'est pas abaissé) ;
4. l'acceptation écrit un élément `origine = document_extrait`,
   `confiance = a_verifier`, `source_document_id` renseigné, et la décision exige
   toujours un humain nommé.

Aucun réseau : le fournisseur employé est le `FournisseurFactice` (défaut) ou un
faux fournisseur défini ici. Les documents sont fictifs et signalés (D10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import charger_config
from app.services import import_guide
from app.services.analyse_dce import extraire_document
from app.services.bibliotheque import ServiceBibliotheque
from app.services.fournisseur_modele import FournisseurModele
from app.services.fournisseur_modele.base import (
    PropositionImport,
    source_presente,
)
from app.services.import_guide import ErreurImportGuide, ImportNonValidable
from app.storage.connexion import Connexion, ContexteClient
from app.storage.fichiers import StockageFichiers

DECIDEUR_FICTIF = "Décideur fictif (démonstration)"

#: Dossier des documents fictifs du lot L7 (racine du projet / scripts).
FICTIF = Path(__file__).resolve().parents[2] / "scripts" / "jeu-de-test" / "fictif"

#: Les trois documents du jeu L7 et la famille dans laquelle l'écran les range.
DOCUMENTS_JEU_L7: tuple[tuple[str, str], ...] = (
    ("plaquette-presentation-FICTIF.txt", "references_chantiers"),
    ("memoire-technique-anterieur-FICTIF.txt", "memoire_technique"),
    ("attestation-assurance-RCD-FICTIF.txt", "assurances"),
)


def _stockage(config) -> StockageFichiers:
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _preparer_fiche(connexion: Connexion, contexte: ContexteClient, config):
    service = ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)
    entreprise_id = service.creer_entreprise("Entreprise fictive — DÉMONSTRATION")
    fiche = service.ouvrir_fiche(entreprise_id)
    connexion.valider()
    return service, str(fiche["id"])


def _importer(connexion, contexte, config, fiche, nom_fichier: str, famille: str):
    contenu = (FICTIF / nom_fichier).read_bytes()
    return import_guide.importer_document(
        connexion,
        contexte,
        _stockage(config),
        fiche_version_id=fiche,
        famille_cible=famille,
        nom_fichier=nom_fichier,
        contenu=contenu,
        type_mime="text/plain",
    )


def _texte_extrait(contenu: bytes):
    import tempfile

    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / "document.txt"
        chemin.write_bytes(contenu)
        return extraire_document(chemin)


# --------------------------------------------------------------------------- #
# 1. Les trois documents du jeu L7 produisent des propositions sourcées
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nom_fichier, famille", DOCUMENTS_JEU_L7)
def test_document_du_jeu_l7_produit_des_propositions_sourcees(
    connexion, contexte_a, config, nom_fichier, famille
):
    _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer(connexion, contexte_a, config, fiche, nom_fichier, famille)

    assert resultat.import_document["statut"] == "traite"
    assert resultat.propositions, (
        f"{nom_fichier} (famille {famille}) doit produire au moins une proposition"
    )

    # Chaque proposition porte un emplacement source non vide et un extrait qui se
    # retrouve **littéralement** dans le texte réellement extrait du document.
    contenu = _stockage(config).lire(contexte_a.client_id, str(resultat.document["id"]))
    extraction = _texte_extrait(contenu)
    from app.services.fournisseur_modele.base import PropositionElement

    for proposition in resultat.propositions:
        assert proposition["source_emplacement"]
        assert proposition["source_extrait"]
        assert source_presente(
            PropositionElement(
                categorie=str(proposition["entite_cible"]),
                libelle="vérification",
                source_emplacement=str(proposition["source_emplacement"]),
                source_extrait=str(proposition["source_extrait"]),
            ),
            extraction.pages,
        ), f"extrait absent du document : {proposition['source_extrait']!r}"

    # Les champs proposés sont ceux que le document porte réellement.
    champs_vus = set()
    for proposition in resultat.propositions:
        champs_vus.update(proposition["champs_proposes"])
    attendus = {
        "references_chantiers": "intitule_operation",
        "memoire_technique": "titre",
        "assurances": "type_assurance",
    }[famille]
    assert attendus in champs_vus


# --------------------------------------------------------------------------- #
# 2. Le vrai lecteur (factice) ne produit jamais un extrait absent
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nom_fichier, famille", DOCUMENTS_JEU_L7)
def test_jamais_de_proposition_sans_extrait_present(
    connexion, contexte_a, config, nom_fichier, famille
):
    """Contrôle direct du lecteur : sur un document courant, tout extrait est présent."""
    _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer(connexion, contexte_a, config, fiche, nom_fichier, famille)
    contenu = _stockage(config).lire(contexte_a.client_id, str(resultat.document["id"]))
    extraction = _texte_extrait(contenu)
    for proposition in resultat.propositions:
        assert source_presente(
            _element(proposition), extraction.pages
        ), f"extrait absent : {proposition['source_extrait']!r}"


def _element(proposition):
    from app.services.fournisseur_modele.base import PropositionElement

    return PropositionElement(
        categorie=str(proposition["entite_cible"]),
        libelle="vérification",
        source_emplacement=str(proposition["source_emplacement"]),
        source_extrait=str(proposition["source_extrait"]),
    )


# --------------------------------------------------------------------------- #
# 3. Garde-fou non abaissé : un extrait inventé est refusé sur un document courant
# --------------------------------------------------------------------------- #
class FournisseurExtraitInvente(FournisseurModele):
    """Faux fournisseur qui invente un extrait absent d'un document en français métier."""

    nom = "faux-extrait-invente"
    modele = "test"

    def analyser(self, extraction):  # pragma: no cover — non exercé ici
        raise NotImplementedError

    def proposer_elements(self, extraction, *, famille_cible):
        return (
            PropositionImport(
                entite_cible="assurance",
                champs_proposes={"assureur": "Assureur Inventé"},
                source_emplacement="page 1 — section « ATTESTATION D'ASSURANCE »",
                source_extrait="cette phrase ne figure nulle part dans le document",
            ),
        )


def test_extrait_absent_refuse_sur_document_courant(connexion, contexte_a, config):
    _, fiche = _preparer_fiche(connexion, contexte_a, config)
    contenu = (FICTIF / "attestation-assurance-RCD-FICTIF.txt").read_bytes()
    with pytest.raises(ImportNonValidable):
        import_guide.importer_document(
            connexion,
            contexte_a,
            _stockage(config),
            fiche_version_id=fiche,
            famille_cible="assurances",
            nom_fichier="attestation-assurance-RCD-FICTIF.txt",
            contenu=contenu,
            type_mime="text/plain",
            fournisseur=FournisseurExtraitInvente(),
        )
    # Rien n'a été enregistré : ni import, ni proposition.
    assert import_guide.lister_imports(connexion, contexte_a) == []
    assert (
        connexion.executer(
            contexte_a,
            "SELECT id FROM import_proposition WHERE client_id = %(client_id)s;",
        )
        == []
    )


# --------------------------------------------------------------------------- #
# 4. Décision humaine sur une proposition issue d'un document courant
# --------------------------------------------------------------------------- #
def test_accepter_une_proposition_de_document_courant(connexion, contexte_a, config):
    service, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer(
        connexion, contexte_a, config, fiche,
        "attestation-assurance-RCD-FICTIF.txt", "assurances",
    )
    proposition = resultat.propositions[0]

    # Décision sans humain nommé : refusée, la proposition reste en attente.
    with pytest.raises(ErreurImportGuide):
        import_guide.decider_proposition(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte_a,
            proposition_id=str(proposition["id"]),
            decision="accepter",
            decide_par="   ",
        )

    decision = import_guide.decider_proposition(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        proposition_id=str(proposition["id"]),
        decision="accepter",
        decide_par=DECIDEUR_FICTIF,
    )
    assert decision["proposition"]["statut"] == "acceptee"
    assert decision["element_id"]

    elements = service.consulter_famille("assurances", fiche)["elements"]["assurance"]
    assert len(elements) == 1
    element = elements[0]
    assert element["origine"] == "document_extrait"
    assert element["confiance"] == "a_verifier"
    assert str(element["source_document_id"]) == str(resultat.document["id"])
    assert str(element["piece"]) == str(resultat.document["id"])
    # La valeur vient littéralement du document.
    assert element["assureur"] == "ASSURANCES-FICTIVES OCÉANE (FICTIF)"


def test_accepter_une_reference_avec_correction_nommee(connexion, contexte_a, config):
    """Une référence lue sans maître d'ouvrage reste acceptable par correction nommée."""
    service, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer(
        connexion, contexte_a, config, fiche,
        "plaquette-presentation-FICTIF.txt", "references_chantiers",
    )
    proposition = resultat.propositions[0]
    assert "intitule_operation" in proposition["champs_proposes"]

    decision = import_guide.decider_proposition(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        proposition_id=str(proposition["id"]),
        decision="accepter",
        decide_par=DECIDEUR_FICTIF,
        corrections={"maitre_ouvrage": "Maître d'ouvrage fictif (démonstration)"},
    )
    assert decision["element_id"]
    elements = service.consulter_famille("references_chantiers", fiche)["elements"][
        "reference_chantier"
    ]
    assert len(elements) == 1
    assert elements[0]["origine"] == "document_extrait"
    assert elements[0]["maitre_ouvrage"] == "Maître d'ouvrage fictif (démonstration)"
