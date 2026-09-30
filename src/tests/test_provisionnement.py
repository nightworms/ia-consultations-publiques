"""Tests du provisionnement (lot L2bis) — exécutés réellement contre PostgreSQL local.

Aucune donnée réelle : les clients, entreprises, identifiants et mots de passe de ce
fichier sont **FICTIFS et signalés** (« DÉMONSTRATION »). Aucun secret réel.

Ce que ces tests démontrent, exigence par exigence (énoncé du lot L2bis) :

1. sans session → `401` sur les **trois** routes de provisionnement ;
2. `POST /api/v1/entreprises` crée **une** `entreprise` et **une** `fiche_version`
   `numero_version = 1`, statut `vierge` (vérifié en SQL après coup) ;
3. deux appels successifs → `numero_version` 1 puis 2…, croissant **par entreprise**
   (jamais partagé entre entreprises) ;
4. un client ne peut pas ouvrir de fiche sur l'`entreprise` d'un autre : `404`, et
   **aucune ligne** écrite dans `fiche_version` (vérification SQL après coup) ;
5. un `client_id` envoyé dans le corps de la requête est **ignoré** ;
6. le script d'exploitant **refuse** `--mot-de-passe` et **accepte** la saisie clavier ;
   `creer_client` + `creer_utilisateur` produisent un compte capable de se connecter
   (`POST /api/v1/connexion` → 200) ;
7. les **quatre** routes gelées de la bibliothèque répondent à l'identique — aucune
   n'est renommée.

Le `404` « Provisionnez une entreprise… » de `GET /api/v1/bibliotheque` reste le
comportement tant qu'aucune fiche n'existe, et cesse d'être un cul-de-sac.
"""

from __future__ import annotations

import getpass
import importlib.util
import io
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.services.authentification import ServiceAuthentification
from app.storage.connexion import Connexion, ContexteClient

MENTION = "DÉMONSTRATION"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # FICTIF — jamais un secret réel
RACINE_DEPOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #


def _identifiant_unique(prefixe: str) -> str:
    """Identifiant d'un compte fictif — unique (`utilisateur.identifiant_connexion` est UNIQUE)."""
    return f"{prefixe}-{uuid.uuid4().hex[:12]}@demo.test"


def _client_api(
    connexion: Connexion,
    contexte: ContexteClient,
    config,
    identifiant: str | None = None,
) -> TestClient:
    """Ouvre une session réelle pour le client du contexte, et renvoie un client HTTP."""
    identifiant = identifiant or _identifiant_unique("prov")
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(
        contexte,
        identifiant,
        "Provisionneur Fictif — DÉMONSTRATION",
        MOT_DE_PASSE_FICTIF,
    )
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def _charger_script() -> ModuleType:
    """Charge `scripts/provisionnement.py` comme module, pour l'exécuter dans le test."""
    chemin = RACINE_DEPOT / "scripts" / "provisionnement.py"
    spec = importlib.util.spec_from_file_location("provisionnement_script", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compter(connexion_admin, sql: str, params: tuple) -> int:
    return int(connexion_admin.lire(sql, params)[0][0])


# --------------------------------------------------------------------------- #
# 1. Sans session → 401 sur les trois routes
# --------------------------------------------------------------------------- #


def test_routes_provisionnement_refusent_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.post("/api/v1/entreprises", json={"libelle_court": "X"}).status_code == 401
        assert client.get("/api/v1/entreprises").status_code == 401
        reponse = client.post(f"/api/v1/entreprises/{uuid.uuid4()}/fiches", json={})
        assert reponse.status_code == 401


# --------------------------------------------------------------------------- #
# 2. Création : une entreprise, une fiche numero_version = 1, statut vierge
# --------------------------------------------------------------------------- #


def test_creation_entreprise_et_premiere_fiche(connexion, connexion_admin, contexte_a, config):
    client = _client_api(connexion, contexte_a, config)
    try:
        reponse = client.post(
            "/api/v1/entreprises",
            json={"libelle_court": f"Entreprise fictive — {MENTION}"},
        )
        assert reponse.status_code == 201, reponse.text
        corps = reponse.json()
        assert corps["numero_version"] == 1
        assert corps["statut"] == "vierge"
        assert corps["entreprise_id"] and corps["fiche_version_id"]

        # Vérification SQL après coup : une seule entreprise, une seule fiche.
        n_entreprises = _compter(
            connexion_admin,
            "SELECT count(*) FROM entreprise WHERE client_id = %s;",
            (contexte_a.client_id,),
        )
        assert n_entreprises == 1

        lignes = connexion_admin.lire(
            "SELECT id, numero_version, statut, client_id FROM fiche_version "
            "WHERE entreprise_id = %s;",
            (corps["entreprise_id"],),
        )
        assert len(lignes) == 1
        assert lignes[0][1] == 1
        assert lignes[0][2] == "vierge"
        assert str(lignes[0][3]) == contexte_a.client_id
        assert str(lignes[0][0]) == corps["fiche_version_id"]
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 3. Numérotation croissante par entreprise, jamais partagée
# --------------------------------------------------------------------------- #


def test_numero_version_croissant_par_entreprise(connexion, contexte_a, config):
    client = _client_api(connexion, contexte_a, config)
    try:
        a1 = client.post(
            "/api/v1/entreprises", json={"libelle_court": f"Entreprise A — {MENTION}"}
        )
        assert a1.status_code == 201, a1.text
        assert a1.json()["numero_version"] == 1

        a2 = client.post(
            f"/api/v1/entreprises/{a1.json()['entreprise_id']}/fiches",
            json={"commentaire": "deuxième version — DÉMONSTRATION"},
        )
        assert a2.status_code == 201, a2.text
        assert a2.json()["numero_version"] == 2

        a3 = client.post(f"/api/v1/entreprises/{a1.json()['entreprise_id']}/fiches", json={})
        assert a3.status_code == 201, a3.text
        assert a3.json()["numero_version"] == 3

        # Une autre entreprise du même client repart à 1 : le numéro n'est pas partagé.
        b1 = client.post(
            "/api/v1/entreprises", json={"libelle_court": f"Entreprise B — {MENTION}"}
        )
        assert b1.status_code == 201, b1.text
        assert b1.json()["numero_version"] == 1
        assert b1.json()["entreprise_id"] != a1.json()["entreprise_id"]

        # GET : chaque entreprise est renvoyée avec sa dernière version.
        lecture = client.get("/api/v1/entreprises")
        assert lecture.status_code == 200
        par_id = {e["entreprise_id"]: e for e in lecture.json()["entreprises"]}
        assert par_id[a1.json()["entreprise_id"]]["derniere_fiche"]["numero_version"] == 3
        assert par_id[a1.json()["entreprise_id"]]["derniere_fiche"]["fiche_version_id"] == a3.json()[
            "fiche_version_id"
        ]
        assert par_id[b1.json()["entreprise_id"]]["derniere_fiche"]["numero_version"] == 1
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 4. Un client ne peut pas ouvrir de fiche sur l'entreprise d'un autre
# --------------------------------------------------------------------------- #


def test_second_client_ne_peut_pas_ouvrir_de_fiche(
    connexion, connexion_admin, contexte_a, contexte_b, config
):
    client_a = _client_api(connexion, contexte_a, config, identifiant=_identifiant_unique("a"))
    client_b = _client_api(connexion, contexte_b, config, identifiant=_identifiant_unique("b"))
    try:
        cree = client_a.post(
            "/api/v1/entreprises", json={"libelle_court": f"Entreprise de A — {MENTION}"}
        )
        assert cree.status_code == 201, cree.text
        entreprise_id = cree.json()["entreprise_id"]

        avant = _compter(
            connexion_admin,
            "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
            (entreprise_id,),
        )
        assert avant == 1

        # B tente d'ouvrir une fiche sur l'entreprise de A → 404, jamais 403.
        refus = client_b.post(f"/api/v1/entreprises/{entreprise_id}/fiches", json={})
        assert refus.status_code == 404, refus.text

        # Aucune ligne n'a été écrite dans `fiche_version`.
        apres = _compter(
            connexion_admin,
            "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
            (entreprise_id,),
        )
        assert apres == 1

        # Et B ne voit aucune entreprise : le cloisonnement tient aussi en lecture.
        assert client_b.get("/api/v1/entreprises").json()["entreprises"] == []
    finally:
        client_a.__exit__(None, None, None)
        client_b.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 5. `client_id` du corps de requête ignoré
# --------------------------------------------------------------------------- #


def test_client_id_du_corps_est_ignore(connexion, connexion_admin, contexte_a, client_b, config):
    client = _client_api(connexion, contexte_a, config)
    try:
        reponse = client.post(
            "/api/v1/entreprises",
            json={
                "libelle_court": f"Entreprise fictive — {MENTION}",
                # Champ étranger au contrat : il doit être ignoré, pas pris en compte.
                "client_id": client_b,
            },
        )
        assert reponse.status_code == 201, reponse.text
        entreprise_id = reponse.json()["entreprise_id"]

        lignes = connexion_admin.lire(
            "SELECT client_id FROM entreprise WHERE id = %s;", (entreprise_id,)
        )
        assert len(lignes) == 1
        assert str(lignes[0][0]) == contexte_a.client_id  # le client de la session
        assert str(lignes[0][0]) != client_b  # jamais le client_id du corps
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 6. Script d'exploitant
# --------------------------------------------------------------------------- #


def test_script_refuse_un_mot_de_passe_en_argument(connexion_admin):
    module = _charger_script()
    avant = _compter(connexion_admin, "SELECT count(*) FROM client;", ())

    sortie_erreur = io.StringIO()
    with redirect_stderr(sortie_erreur):
        code = module.main(
            [
                "--libelle-client",
                "Client refusé — DÉMONSTRATION",
                "--identifiant",
                _identifiant_unique("refus"),
                "--mot-de-passe",
                "UnMotDePasseVisibleParPs123",
            ]
        )

    assert code == 2
    assert "REFUSÉ" in sortie_erreur.getvalue()
    assert "ps" in sortie_erreur.getvalue()
    # Rien n'a été créé : la base est inchangée.
    apres = _compter(connexion_admin, "SELECT count(*) FROM client;", ())
    assert apres == avant


def test_script_provisionne_un_compte_qui_se_connecte(connexion_admin, monkeypatch):
    module = _charger_script()
    identifiant = _identifiant_unique("script")
    libelle = f"Client du script fictif — {MENTION} {uuid.uuid4().hex[:6]}"

    # Saisie clavier masquée simulée : deux saisies concordantes.
    saisies = iter([MOT_DE_PASSE_FICTIF, MOT_DE_PASSE_FICTIF])
    monkeypatch.setattr(getpass, "getpass", lambda *a, **k: next(saisies))

    sortie = io.StringIO()
    with redirect_stdout(sortie):
        code = module.main(
            [
                "--libelle-client",
                libelle,
                "--identifiant",
                identifiant,
                "--nom-affichage",
                "Compte Fictif — DÉMONSTRATION",
            ]
        )

    assert code == 0
    texte = sortie.getvalue()
    assert "OK — provisionnement effectué." in texte
    # Le mot de passe n'apparaît nulle part dans la sortie.
    assert MOT_DE_PASSE_FICTIF not in texte

    # Le `client` existe en base.
    lignes = connexion_admin.lire("SELECT id FROM client WHERE libelle = %s;", (libelle,))
    assert len(lignes) == 1
    client_id = str(lignes[0][0])

    # Le compte est réellement utilisable : connexion par la route gelée → 200.
    from app.main import app

    with TestClient(app) as api:
        reponse = api.post(
            "/api/v1/connexion",
            json={"identifiant": identifiant, "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["client_id"] == client_id


def test_script_refuse_des_saisies_differentes(connexion_admin, monkeypatch):
    module = _charger_script()
    avant = _compter(connexion_admin, "SELECT count(*) FROM client;", ())
    saisies = iter([MOT_DE_PASSE_FICTIF, "AutreMotDePasseFictif!99"])
    monkeypatch.setattr(getpass, "getpass", lambda *a, **k: next(saisies))

    sortie_erreur = io.StringIO()
    with redirect_stderr(sortie_erreur):
        code = module.main(
            [
                "--libelle-client",
                "Client refusé 2 — DÉMONSTRATION",
                "--identifiant",
                _identifiant_unique("refus2"),
            ]
        )

    assert code == 2
    assert "REFUSÉ" in sortie_erreur.getvalue()
    assert _compter(connexion_admin, "SELECT count(*) FROM client;", ()) == avant


# --------------------------------------------------------------------------- #
# 7. Les quatre routes gelées de la bibliothèque ne bougent pas
# --------------------------------------------------------------------------- #

ROUTES_BIBLIOTHEQUE = (
    "/api/v1/bibliotheque",
    "/api/v1/bibliotheque/{famille}",
    "/api/v1/bibliotheque/validation",
)


def test_contrat_openapi_inchange_pour_la_bibliotheque():
    from app.main import app

    chemins = app.openapi()["paths"]

    # Les quatre routes de la bibliothèque, mêmes chemins, mêmes méthodes.
    assert "get" in chemins["/api/v1/bibliotheque"]
    assert "get" in chemins["/api/v1/bibliotheque/{famille}"]
    assert "post" in chemins["/api/v1/bibliotheque/{famille}"]
    assert "post" in chemins["/api/v1/bibliotheque/validation"]

    # Les trois routes de provisionnement sont bien montées.
    assert "post" in chemins["/api/v1/entreprises"]
    assert "get" in chemins["/api/v1/entreprises"]
    assert "post" in chemins["/api/v1/entreprises/{entreprise_id}/fiches"]

    # Aucune route de création de `client` n'est exposée (annexe C § C2, volet 2).
    assert "/api/v1/clients" not in chemins


def test_bibliotheque_404_puis_parcours_complet_apres_provisionnement(
    connexion, contexte_a, config
):
    """Le `404` de § C2 devient franchissable, sans que la route ne change."""
    client = _client_api(connexion, contexte_a, config)
    try:
        # Sans aucune fiche : 404 explicite, message inchangé.
        avant = client.get("/api/v1/bibliotheque")
        assert avant.status_code == 404
        assert "Provisionnez une entreprise" in avant.json()["detail"]

        # Provisionnement par l'API : entreprise + première fiche.
        creation = client.post(
            "/api/v1/entreprises", json={"libelle_court": f"Entreprise fictive — {MENTION}"}
        )
        assert creation.status_code == 201, creation.text

        # Le même appel ne renvoie plus 404 — le cul-de-sac est ouvert.
        apres = client.get("/api/v1/bibliotheque")
        assert apres.status_code == 200, apres.text
        assert apres.json()["statut"] == "vierge"

        # Les trois autres routes gelées répondent toujours.
        assert client.get("/api/v1/bibliotheque/assurances").status_code == 200
        assert (
            client.post(
                "/api/v1/bibliotheque/assurances",
                json={"entite": "assurance", "donnees": {}},
            ).status_code
            == 400  # aucune valeur sans origine : refus explicite, pas 401/404
        )
    finally:
        client.__exit__(None, None, None)


def test_routes_bibliotheque_refusent_toujours_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/bibliotheque").status_code == 401
        assert client.get("/api/v1/bibliotheque/assurances").status_code == 401
        assert (
            client.post(
                "/api/v1/bibliotheque/assurances", json={"entite": "x", "donnees": {}}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/bibliotheque/validation",
                json={"fiche_version_id": "x", "relecteur_nom": "y", "attestation_cochee": True},
            ).status_code
            == 401
        )


def test_libelle_vide_refuse_par_la_route(connexion, contexte_a, config):
    """Un libellé blanc est refusé (`400`), jamais créé."""
    client = _client_api(connexion, contexte_a, config)
    try:
        assert (
            client.post("/api/v1/entreprises", json={"libelle_court": "   "}).status_code == 400
        )
        assert client.post("/api/v1/entreprises", json={}).status_code == 422
    finally:
        client.__exit__(None, None, None)


@pytest.mark.parametrize("chemin", ROUTES_BIBLIOTHEQUE)
def test_aucune_route_bibliotheque_renommee(chemin):
    from app.main import app

    assert chemin in app.openapi()["paths"]
