"""Correctif C1 — une réponse de modèle refusée ne doit pas produire un 500.

Fait constaté le 30/09/2026 : un DCE analysé par un modèle réel (Claude via
OpenRouter) a fait remonter `ReponseModeleInvalide` **non gérée** jusqu'à FastAPI,
donc un `HTTP 500` opaque, et un dossier déposé disparu sans trace.

`ReponseModeleInvalide` n'est pourtant pas un incident : c'est le résultat attendu du
garde-fou anti-invention (SPEC-MVP-V2 § 2, « aucune valeur sans source »). Ce qui est
vérifié ici :

1. le refus est **explicite et exploitable** côté API (422, avec la catégorie et
   l'extrait mis en cause) — jamais 500, jamais 201 ;
2. le refus n'est **jamais** transformé en succès ni en proposition partielle ;
3. le dépôt est **annulé** : aucune ligne orpheline en base (vérifié par une
   connexion **séparée**, qui ne voit donc que l'état réellement validé).

Aucune donnée réelle, aucun appel réseau : le fournisseur employé ici est un faux
fournisseur local qui cite **volontairement** un extrait absent du document.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.api.routes_analyse import obtenir_fournisseur
from app.config import charger_config
from app.services import analyse_dce
from app.services.analyse_dce import AnalyseNonValidable
from app.services.authentification import ServiceAuthentification
from app.services.extraction_pdf import ExtractionPdf
from app.services.fournisseur_modele.base import (
    FournisseurModele,
    PropositionElement,
    ResultatAnalyse,
)
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.fichiers import StockageFichiers

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF_FICTIF = FIXTURES / "dce_fictif.pdf"

LIBELLE_FICTIF = "Consultation fictive (refus de modèle) — DÉMONSTRATION"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel
#: Extrait volontairement inventé : il ne figure dans aucun document, donc le
#: garde-fou doit le refuser (c'est le cas reproduit du 30/09/2026).
EXTRAIT_INVENTE = (
    "ATTESTATION D'ASSURANCE DECENNALE — PASSAGE QUI N'EXISTE DANS AUCUN DOCUMENT"
)


class FournisseurInventeur(FournisseurModele):
    """Fournisseur de test **volontairement fautif** : invente un extrait de source.

    Il ne sert qu'à reproduire le refus du garde-fou ; il n'écrit rien, n'appelle
    rien, et ne prétend pas analyser quoi que ce soit.
    """

    nom = "factice-fautif"
    modele = "modele-de-test-fictif"

    def analyser(self, extraction: ExtractionPdf) -> ResultatAnalyse:
        return ResultatAnalyse(
            propositions=(
                PropositionElement(
                    categorie="piece_exigee",
                    libelle="Attestation inventée par le modèle (test)",
                    source_emplacement="page 1",
                    valeur="attestation inventée",
                    source_extrait=EXTRAIT_INVENTE,
                ),
            ),
            fournisseur=self.nom,
            modele=self.modele,
            avertissement="fournisseur de test volontairement fautif",
        )


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def _stockage(config) -> StockageFichiers:
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _inserer_entreprise(connexion: Connexion, contexte: ContexteClient, libelle: str) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO entreprise (client_id, libelle_court) "
        "VALUES (%(client_id)s, %(libelle)s) RETURNING id;",
        {"libelle": libelle},
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _creer_utilisateur(connexion, contexte, identifiant: str, config) -> None:
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, "Utilisateur fictif", MOT_DE_PASSE_FICTIF)
    connexion.valider()


def _lignes_validees(client_id: str) -> dict[str, int]:
    """Compte les lignes **réellement validées** du client, via une connexion séparée.

    Une connexion distincte ne voit que l'état commité : c'est le seul moyen de
    vérifier qu'aucun dépôt annulé ne laisse de ligne orpheline en base.
    """
    admin = ConnexionAdministration(charger_config().database_url).ouvrir()
    try:
        return {
            table: int(
                admin.lire(f"SELECT count(*) FROM {table} WHERE client_id = %s;", (client_id,))[0][0]
            )
            for table in ("consultation", "document", "extraction_element")
        }
    finally:
        admin.fermer()


# --------------------------------------------------------------------------- #
# 1. Service : le refus est explicite, et le dépôt est annulé
# --------------------------------------------------------------------------- #
def test_un_extrait_invente_est_refuse_sans_laisser_de_ligne(connexion, contexte_a, config):
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — C1")
    avant = _lignes_validees(contexte_a.client_id)

    with pytest.raises(AnalyseNonValidable) as exc:
        analyse_dce.deposer_et_analyser(
            connexion,
            contexte_a,
            _stockage(config),
            entreprise_id=entreprise_id,
            libelle=LIBELLE_FICTIF,
            nom_fichier=PDF_FICTIF.name,
            contenu=PDF_FICTIF.read_bytes(),
            type_mime="application/pdf",
            fournisseur=FournisseurInventeur(),
        )

    message = str(exc.value)
    # Le message dit que le document a bien été reçu, et pourquoi l'analyse est refusée.
    assert "a bien été reçu" in message
    assert "piece_exigee" in message
    assert EXTRAIT_INVENTE in message
    assert "annulé" in message

    # Rien n'a été écrit : ni consultation, ni document, ni élément.
    assert _lignes_validees(contexte_a.client_id) == avant

    # Et aucun fichier chiffré orphelin ne traîne sur disque pour ce client.
    dossier_client = Path(config.repertoire_documents) / "clients" / contexte_a.client_id
    restants = sorted(p.name for p in dossier_client.glob("*.bin")) if dossier_client.is_dir() else []
    assert restants == [], f"fichier de dépôt orphelin : {restants}"


def test_le_refus_n_est_pas_converti_en_succes(connexion, contexte_a, config):
    """Aucune proposition partielle : la consultation ne devient pas `analysee`."""
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — C1 bis")
    with pytest.raises(AnalyseNonValidable):
        analyse_dce.deposer_et_analyser(
            connexion,
            contexte_a,
            _stockage(config),
            entreprise_id=entreprise_id,
            libelle=LIBELLE_FICTIF,
            nom_fichier=PDF_FICTIF.name,
            contenu=PDF_FICTIF.read_bytes(),
            type_mime="application/pdf",
            fournisseur=FournisseurInventeur(),
        )
    restantes = connexion.executer(
        contexte_a,
        "SELECT id, statut FROM consultation WHERE client_id = %(client_id)s;",
    )
    assert restantes == []


# --------------------------------------------------------------------------- #
# 2. Route : 422 explicite, jamais 500 (le cas constaté)
# --------------------------------------------------------------------------- #
def test_la_route_repond_422_et_non_500(connexion, contexte_a, config):
    from app.main import app

    _creer_utilisateur(connexion, contexte_a, "api-refus@fictif.test", config)
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — route C1")
    avant = _lignes_validees(contexte_a.client_id)

    app.dependency_overrides[obtenir_fournisseur] = FournisseurInventeur
    try:
        # `raise_server_exceptions=False` : on veut voir la réponse HTTP **réelle**
        # du serveur (c'est précisément le 500 constaté que l'on reproduit), pas une
        # exception relancée dans le test.
        with TestClient(app, raise_server_exceptions=False) as client:
            assert (
                client.post(
                    "/api/v1/consultations",
                    data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
                    files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
                ).status_code
                == 401
            )
            connexion_ok = client.post(
                "/api/v1/connexion",
                json={
                    "identifiant": "api-refus@fictif.test",
                    "mot_de_passe": MOT_DE_PASSE_FICTIF,
                },
            )
            assert connexion_ok.status_code == 200
            assert NOM_COOKIE_SESSION in connexion_ok.cookies

            refus = client.post(
                "/api/v1/consultations",
                data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
                files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
            )
            assert refus.status_code != 500, f"erreur serveur opaque : {refus.status_code}"
            assert refus.status_code == 422, refus.text
            detail = refus.json()["detail"]
            assert "a bien été reçu" in detail
            assert "piece_exigee" in detail
            assert EXTRAIT_INVENTE in detail
    finally:
        app.dependency_overrides.pop(obtenir_fournisseur, None)

    # Le dossier déposé n'a laissé aucune trace en base.
    assert _lignes_validees(contexte_a.client_id) == avant


def test_la_route_accepte_toujours_une_analyse_valide(connexion, contexte_a, config):
    """Le correctif n'a pas cassé le chemin nominal : le fournisseur factice passe."""
    from app.main import app

    _creer_utilisateur(connexion, contexte_a, "api-nominal@fictif.test", config)
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — nominal")
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(
            "/api/v1/connexion",
            json={"identifiant": "api-nominal@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        depot = client.post(
            "/api/v1/consultations",
            data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
            files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
        )
        assert depot.status_code == 201, depot.text
        corps = depot.json()
        assert corps["consultation"]["statut"] == "analysee"
        assert corps["elements"], "aucun élément extrait du document fictif"
        for element in corps["elements"]:
            assert element["source_emplacement"]
            assert element["source_extrait"]
