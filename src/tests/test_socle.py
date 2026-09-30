"""Tests du socle L1 — exécutés réellement contre PostgreSQL.

Aucune donnée réelle : tous les identifiants, entreprises et mots de passe sont
fictifs et signalés. Les tests démontrent les exigences vérifiables du lot :

1. migrations `up` / `down` ;
2. cloisonnement : impossible de lire les données d'un autre client ;
3. chiffrement : deux clients ne peuvent pas se déchiffrer mutuellement ;
4. config stricte, mots de passe, stockage fichiers, sessions ;
5. l'application FastAPI démarre et sert ses routes.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION, exiger_contexte_client
from app.config import ErreurConfiguration, charger_config, reinitialiser_cache
from app.securite import mots_de_passe
from app.securite.chiffrement import (
    ErreurDechiffrement,
    chiffrer,
    dechiffrer,
    deriver_cle_client,
)
from app.services.authentification import IdentiteSession, ServiceAuthentification
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
    ContexteClientManquant,
    ErreurCloisonnement,
)
from app.storage.fichiers import ErreurStockage, StockageFichiers, empreinte_sha256
from app.storage.migrations import ExecuteurMigrations, lister_migrations

MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel
LIBELLE_FICTIF = "Entreprise de démonstration — DOCUMENT FICTIF"


# --------------------------------------------------------------------------- #
# Utilitaires de test
# --------------------------------------------------------------------------- #
def _inserer_entreprise(connexion: Connexion, contexte, libelle: str) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO entreprise (client_id, libelle_court) "
        "VALUES (%(client_id)s, %(libelle)s) RETURNING id;",
        {"libelle": libelle},
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _table_existe(conn: ConnexionAdministration, nom: str) -> bool:
    lignes = conn.lire(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s;",
        (nom,),
    )
    return len(lignes) > 0


# --------------------------------------------------------------------------- #
# 1. Configuration stricte
# --------------------------------------------------------------------------- #
def test_config_echoue_si_variable_obligatoire_absente(monkeypatch):
    monkeypatch.delenv("CLE_SESSION", raising=False)
    reinitialiser_cache()
    with pytest.raises(ErreurConfiguration) as exc:
        charger_config()
    assert "CLE_SESSION" in str(exc.value)
    reinitialiser_cache()


def test_config_echoue_si_cle_maitresse_invalide(monkeypatch):
    monkeypatch.setenv("CLE_CHIFFREMENT_MAITRESSE", "trop-court")
    reinitialiser_cache()
    with pytest.raises(ErreurConfiguration):
        charger_config()
    reinitialiser_cache()


def test_config_charge(config):
    assert config.database_url.startswith("postgresql://")
    assert len(config.cle_chiffrement_maitresse) == 32
    assert config.hote_api == "127.0.0.1"


# --------------------------------------------------------------------------- #
# 2. Cloisonnement (exigence vérifiable n° 2)
# --------------------------------------------------------------------------- #
def test_lecture_impossible_des_donnees_d_un_autre_client(connexion, contexte_a, contexte_b):
    """Le contexte de A ne peut pas lire l'entreprise de B."""
    id_a = _inserer_entreprise(connexion, contexte_a, "A — fictif")
    id_b = _inserer_entreprise(connexion, contexte_b, "B — fictif")

    # A ne voit que A.
    lignes_a = connexion.executer(
        contexte_a, "SELECT id FROM entreprise WHERE client_id = %(client_id)s;"
    )
    ids_a = {str(l["id"]) for l in lignes_a}
    assert ids_a == {id_a}

    # A tente explicitement de lire la ligne de B : aucune ligne.
    tentative = connexion.executer(
        contexte_a,
        "SELECT id FROM entreprise WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": id_b},
    )
    assert tentative == []


def test_falsifier_client_id_est_sans_effet(connexion, contexte_a, client_b):
    """Fournir un autre client_id en paramètre ne change rien : le contexte prime."""
    _inserer_entreprise(connexion, contexte_a, "A — fictif")
    lignes = connexion.executer(
        contexte_a,
        "SELECT client_id FROM entreprise WHERE client_id = %(client_id)s;",
        {"client_id": client_b},  # tentative de falsification
    )
    assert lignes  # A voit bien sa ligne
    assert {str(l["client_id"]) for l in lignes} == {contexte_a.client_id}


def test_requete_sans_filtre_client_refusee(connexion, contexte_a):
    with pytest.raises(ErreurCloisonnement):
        connexion.executer(contexte_a, "SELECT id FROM entreprise;")


def test_requete_sans_contexte_client_refusee(connexion):
    with pytest.raises(ContexteClientManquant):
        connexion.executer(None, "SELECT id FROM entreprise WHERE client_id = %(client_id)s;")


def test_contexte_client_refuse_un_identifiant_invalide():
    with pytest.raises(ErreurCloisonnement):
        ContexteClient("pas-un-uuid")


# --------------------------------------------------------------------------- #
# 3. Chiffrement par client (exigence vérifiable n° 3)
# --------------------------------------------------------------------------- #
def test_chiffrement_aller_retour(cle_maitresse, client_a):
    clair = "FR76 3000 6000 0112 3456 7890 189  # IBAN FICTIF"
    stocke = chiffrer(cle_maitresse, client_a, clair)
    assert stocke.startswith("v1:")
    assert clair not in stocke
    assert dechiffrer(cle_maitresse, client_a, stocke) == clair


def test_deux_clients_ne_peuvent_pas_se_dechiffrer(cle_maitresse, client_a, client_b):
    stocke_a = chiffrer(cle_maitresse, client_a, "donnée confidentielle de A (fictive)")
    with pytest.raises(ErreurDechiffrement):
        dechiffrer(cle_maitresse, client_b, stocke_a)


def test_cles_derivees_different_par_client(cle_maitresse, client_a, client_b):
    assert deriver_cle_client(cle_maitresse, client_a) != deriver_cle_client(cle_maitresse, client_b)


def test_chiffrement_non_deterministe(cle_maitresse, client_a):
    assert chiffrer(cle_maitresse, client_a, "même valeur") != chiffrer(
        cle_maitresse, client_a, "même valeur"
    )


def test_dechiffrement_refuse_une_alteration(cle_maitresse, client_a):
    stocke = chiffrer(cle_maitresse, client_a, "valeur")
    altere = stocke[:-4] + ("AAAA" if not stocke.endswith("AAAA") else "BBBB")
    with pytest.raises(ErreurDechiffrement):
        dechiffrer(cle_maitresse, client_a, altere)


# --------------------------------------------------------------------------- #
# 4. Mots de passe
# --------------------------------------------------------------------------- #
def test_hachage_et_verification_mot_de_passe():
    empreinte = mots_de_passe.hacher(MOT_DE_PASSE_FICTIF)
    assert empreinte != MOT_DE_PASSE_FICTIF
    assert MOT_DE_PASSE_FICTIF not in empreinte
    assert mots_de_passe.verifier(MOT_DE_PASSE_FICTIF, empreinte)
    assert not mots_de_passe.verifier("mauvais-mot-de-passe", empreinte)


def test_mot_de_passe_trop_court_refuse():
    with pytest.raises(mots_de_passe.ErreurMotDePasse):
        mots_de_passe.hacher("court")


# --------------------------------------------------------------------------- #
# 5. Stockage des pièces — hors dépôt, cloisonné, chiffré
# --------------------------------------------------------------------------- #
def test_fichiers_aller_retour_et_contenu_chiffre(cle_maitresse, client_a, tmp_path):
    stockage = StockageFichiers(tmp_path, cle_maitresse)
    document_id = str(uuid.uuid4())
    contenu = b"DOCUMENT FICTIF - DEMONSTRATION\ncontenu binaire de test"

    relatif = stockage.ecrire(client_a, document_id, contenu)
    assert relatif == f"clients/{client_a}/{document_id}.bin"
    assert stockage.lire(client_a, document_id) == contenu
    assert empreinte_sha256(contenu) == hashlib.sha256(contenu).hexdigest()

    # Le fichier sur disque ne contient pas le clair.
    brut = (tmp_path / relatif).read_bytes()
    assert contenu not in brut
    assert brut.startswith(b"v1:")


def test_fichier_d_un_client_illisible_par_un_autre(cle_maitresse, client_a, client_b, tmp_path):
    stockage = StockageFichiers(tmp_path, cle_maitresse)
    document_id = str(uuid.uuid4())
    stockage.ecrire(client_a, document_id, b"piece de A")
    # B cherche dans son propre espace : rien.
    with pytest.raises(ErreurStockage):
        stockage.lire(client_b, document_id)
    # Même en lisant le fichier brut de A, B ne peut pas le déchiffrer.
    brut = (tmp_path / f"clients/{client_a}/{document_id}.bin").read_text(encoding="ascii")
    with pytest.raises(ErreurDechiffrement):
        dechiffrer(cle_maitresse, client_b, brut)


def test_chemin_refuse_identifiant_invalide(cle_maitresse, tmp_path):
    stockage = StockageFichiers(tmp_path, cle_maitresse)
    with pytest.raises(ErreurStockage):
        stockage.chemin_relatif("../../etc", str(uuid.uuid4()))


# --------------------------------------------------------------------------- #
# 6. Authentification et sessions
# --------------------------------------------------------------------------- #
def test_creation_compte_connexion_et_session(connexion, contexte_a, config):
    service = ServiceAuthentification(connexion, config.cle_session)
    utilisateur_id = service.creer_utilisateur(
        contexte_a, "demo@fictif.test", "Relecteur fictif", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()
    assert utilisateur_id

    identite = service.authentifier("demo@fictif.test", MOT_DE_PASSE_FICTIF)
    assert identite is not None
    assert identite.client_id == contexte_a.client_id

    assert service.authentifier("demo@fictif.test", "mauvais") is None
    assert service.authentifier("inconnu@fictif.test", MOT_DE_PASSE_FICTIF) is None

    jeton = service.creer_cookie_session(identite)
    relu = service.lire_session(jeton)
    assert relu == identite


# --------------------------------------------------------------------------- #
# 7. Application FastAPI (exigence vérifiable n° 5)
# --------------------------------------------------------------------------- #
def test_application_demarre_et_sert_la_racine():
    from app.main import app

    with TestClient(app) as client:
        reponse = client.get("/")
        assert reponse.status_code == 200
        assert reponse.json()["application"] == "ia-consultations-publiques"


def test_routes_connexion_et_deconnexion(connexion, contexte_a, config):
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(
        contexte_a, "api@fictif.test", "Utilisateur API fictif", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()

    from app.main import app

    with TestClient(app) as client:
        mauvais = client.post(
            "/api/v1/connexion",
            json={"identifiant": "api@fictif.test", "mot_de_passe": "faux"},
        )
        assert mauvais.status_code == 401

        bon = client.post(
            "/api/v1/connexion",
            json={"identifiant": "api@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        assert bon.status_code == 200
        assert bon.json()["client_id"] == contexte_a.client_id
        assert NOM_COOKIE_SESSION in bon.cookies

        deconnexion = client.post("/api/v1/deconnexion")
        assert deconnexion.status_code == 200


def test_dependance_cloisonnement_401_puis_200(connexion, contexte_a, config):
    """La dépendance obligatoire refuse sans session, puis pose le client_id."""
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(
        contexte_a, "dep@fictif.test", "Utilisateur dépendance fictif", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()

    mini = FastAPI()
    mini.state.config = config

    @mini.get("/qui")
    def qui(contexte=Depends(exiger_contexte_client)):
        return {"client_id": contexte.client_id}

    with TestClient(mini) as client:
        assert client.get("/qui").status_code == 401

        identite = service.authentifier("dep@fictif.test", MOT_DE_PASSE_FICTIF)
        assert identite is not None
        client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
        reponse = client.get("/qui")
        assert reponse.status_code == 200
        assert reponse.json()["client_id"] == contexte_a.client_id


# --------------------------------------------------------------------------- #
# 8. Migrations — up ET down (exigence vérifiable n° 1) — laissé en dernier
# --------------------------------------------------------------------------- #
def test_migrations_lister_0001():
    # Modifié par le lot L3 (phase 3) : l'assertion d'origine exigeait que 0001 soit la
    # SEULE migration du dossier, ce que le plan de phase 3 (annexe A § A4) contredit en
    # réservant 0001 à 0004. L'assertion porte désormais sur ce qui doit rester vrai :
    # 0001 existe, la liste est triée, et chaque migration a ses deux sections.
    migrations = lister_migrations()
    numeros = [m.numero for m in migrations]
    assert "0001" in numeros
    assert numeros == sorted(numeros)
    assert all(m.sql_up and m.sql_down for m in migrations)


def test_migrations_down_puis_up(connexion_admin, base_migree):
    # Modifié par le lot L3 : l'annulation portait sur « 0001 » en dur. Elle porte
    # désormais sur l'ensemble des migrations appliquées, ce qui reste vrai à chaque
    # ajout de lot (0002 bibliothèque, 0003 analyse de DCE, 0004 checklist).
    executeur = ExecuteurMigrations(charger_config().database_url)
    assert _table_existe(connexion_admin, "client")

    annulees = executeur.down(999)
    assert "0001" in annulees
    assert not _table_existe(connexion_admin, "client")
    assert not _table_existe(connexion_admin, "consultation")

    appliquees = executeur.up()
    assert set(appliquees) == set(annulees)
    assert _table_existe(connexion_admin, "client")
