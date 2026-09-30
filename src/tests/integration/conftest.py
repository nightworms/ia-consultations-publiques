"""Fixtures et outils communs aux tests d'intégration (lot L8).

Ces tests sont **indépendants** des lots d'implémentation : ils exercent le
système par l'API HTTP et par SQL, et cherchent à le faire échouer.

Rappels projet appliqués ici :

* **Aucune donnée réelle.** Tous les clients, entreprises, pièces, consultants et
  identifiants sont **fictifs et signalés** (« DÉMONSTRATION ») — décision D10.
* **Aucun secret réel.** Le mot de passe ci-dessous est une valeur de test, sans
  valeur en production.
* **PostgreSQL local uniquement**, base de test dédiée (`ia_consultations_test`
  pour l'application, `ia_consultations_qa_migrations` pour le test de migrations).
"""

from __future__ import annotations

import os
import uuid
from typing import Iterator, Optional

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.services.authentification import ServiceAuthentification
from app.storage.connexion import Connexion, ContexteClient

MENTION = "DÉMONSTRATION"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # FICTIF — jamais un mot de passe réel

#: Base de données dédiée au test de migrations (créée et supprimée par le test).
BASE_TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://pause@127.0.0.1:5432/ia_consultations_test",
)
URL_MIGRATIONS = BASE_TEST_URL.rsplit("/", 1)[0] + "/ia_consultations_qa_migrations"
URL_MAINTENANCE = BASE_TEST_URL.rsplit("/", 1)[0] + "/postgres"


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #
def identifiant_unique(prefixe: str) -> str:
    """Identifiant de compte fictif — unique (la colonne est UNIQUE)."""
    return f"{prefixe}-{uuid.uuid4().hex[:12]}@demo.test"


def creer_client_fictif(connexion: Connexion, prefixe: str) -> str:
    """Crée un `client` fictif et renvoie son UUID."""
    client_id = connexion.creer_client(f"{prefixe} — {MENTION}")
    connexion.valider()
    return client_id


def ouvrir_session_api(
    connexion: Connexion,
    contexte: ContexteClient,
    config,
    *,
    identifiant: Optional[str] = None,
    nom: str = "Compte fictif QA (démonstration)",
) -> TestClient:
    """Crée un compte fictif pour ce client et renvoie un client HTTP authentifié."""
    identifiant = identifiant or identifiant_unique("qa")
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, nom, MOT_DE_PASSE_FICTIF)
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def fermer(client: TestClient) -> None:
    client.__exit__(None, None, None)


def tables_avec_client_id(connexion_admin) -> list[str]:
    """Toutes les tables du schéma public qui portent une colonne `client_id`."""
    lignes = connexion_admin.lire(
        "SELECT table_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND column_name = 'client_id' "
        "ORDER BY table_name;"
    )
    return [ligne[0] for ligne in lignes]


def compter_admin(connexion_admin, sql: str, params: tuple = ()) -> int:
    return int(connexion_admin.lire(sql, params)[0][0])


@pytest.fixture
def api_a(connexion, contexte_a, config) -> Iterator[TestClient]:
    client = ouvrir_session_api(connexion, contexte_a, config, identifiant=identifiant_unique("a"))
    try:
        yield client
    finally:
        fermer(client)


@pytest.fixture
def api_b(connexion, contexte_b, config) -> Iterator[TestClient]:
    client = ouvrir_session_api(connexion, contexte_b, config, identifiant=identifiant_unique("b"))
    try:
        yield client
    finally:
        fermer(client)
