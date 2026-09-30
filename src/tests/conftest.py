"""Fixtures de test — socle L1.

Rappels projet appliqués ici :

* **Aucune donnée réelle.** Les clients, entreprises, identifiants et mots de passe
  de ces tests sont **fictifs et signalés** comme tels.
* **Aucun secret réel.** Les valeurs d'environnement posées ci-dessous sont des
  valeurs de test, sans valeur en production.
* Les tests s'exécutent réellement contre une base PostgreSQL **locale dédiée**,
  migrations appliquées (`up`) puis annulées (`down`) par la suite.
"""

from __future__ import annotations

import base64
import getpass
import os
import sys
from pathlib import Path

import pytest

# --- chemin : rendre `app` importable quand pytest est lancé depuis src/ ---------
RACINE_SRC = Path(__file__).resolve().parents[1]
if str(RACINE_SRC) not in sys.path:
    sys.path.insert(0, str(RACINE_SRC))

RACINE_PROJET = RACINE_SRC.parent

RACINE_TESTS = Path(__file__).resolve().parent
if str(RACINE_TESTS) not in sys.path:
    sys.path.insert(0, str(RACINE_TESTS))

# --- correctif C2 : la suite impose son fournisseur et interdit le réseau ---------
# Fait **avant** tout import du produit : la valeur du `.env` local (par exemple
# `MODELE_FOURNISSEUR=ue`) ne doit jamais atteindre le code exercé par les tests.
# Motif complet : `src/tests/garde_isolation.py` et `docs/RAPPORTS/C2-*.md`.
import garde_isolation  # noqa: E402  (doit suivre l'insertion de sys.path)

garde_isolation.forcer_fournisseur_factice()
garde_isolation.installer_garde_reseau()


def pytest_sessionstart(session) -> None:  # noqa: ARG001 — signature imposée
    """Refuse de démarrer la suite si l'isolation des tests n'est pas en place.

    Voir `garde_isolation.verifier_isolation` : la propriété est verrouillée,
    pas seulement souhaitée. Un `.env` local ne peut plus décider du verdict.
    """
    garde_isolation.verifier_isolation()


# --- environnement de test (valeurs fictives, jamais de production) --------------
UTILISATEUR_PG = getpass.getuser()
BASE_DE_TEST = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql://{UTILISATEUR_PG}@127.0.0.1:5432/ia_consultations_test",
)
os.environ["DATABASE_URL"] = BASE_DE_TEST
os.environ["CLE_CHIFFREMENT_MAITRESSE"] = base64.b64encode(
    b"0123456789abcdef0123456789abcdef"  # 32 octets — clé FICTIVE de test
).decode("ascii")
os.environ["CLE_SESSION"] = "secret-de-session-de-test-fictif-non-produit"
os.environ["REPERTOIRE_DOCUMENTS"] = str(RACINE_PROJET / "data" / "tests")
os.environ["DUREE_SESSION_SECONDES"] = "3600"

from app.config import charger_config  # noqa: E402
from app.storage.connexion import (  # noqa: E402
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.migrations import ExecuteurMigrations  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def base_migree():
    """Applique puis annule toutes les migrations autour de la session de tests."""
    executeur = ExecuteurMigrations(BASE_DE_TEST)
    executeur.down(999)  # repartir d'une base propre
    executeur.up()
    yield executeur
    executeur.down(999)


@pytest.fixture
def config():
    return charger_config()


@pytest.fixture
def cle_maitresse(config) -> bytes:
    return config.cle_chiffrement_maitresse


@pytest.fixture
def connexion():
    """Connexion applicative (SQL cloisonné) pour un test."""
    conn = Connexion(charger_config().database_url).ouvrir()
    try:
        yield conn
    finally:
        conn.annuler()
        conn.fermer()


@pytest.fixture
def connexion_admin():
    conn = ConnexionAdministration(charger_config().database_url).ouvrir()
    try:
        yield conn
    finally:
        conn.fermer()


def _creer_client(connexion: Connexion, libelle: str) -> str:
    client_id = connexion.creer_client(libelle)
    connexion.valider()
    return client_id


@pytest.fixture
def client_a(connexion) -> str:
    """Client fictif A — DÉMONSTRATION."""
    return _creer_client(connexion, "Client fictif A — DÉMONSTRATION")


@pytest.fixture
def client_b(connexion) -> str:
    """Client fictif B — DÉMONSTRATION."""
    return _creer_client(connexion, "Client fictif B — DÉMONSTRATION")


@pytest.fixture
def contexte_a(client_a) -> ContexteClient:
    return ContexteClient(client_a)


@pytest.fixture
def contexte_b(client_b) -> ContexteClient:
    return ContexteClient(client_b)
