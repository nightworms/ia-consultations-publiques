"""Migrations 0001 à 0004 : `up` puis `down`, sur une base de **test dédiée**.

Exigence du lot L8 : la séquence `up` puis `down` est rejouée pour **chaque**
migration, sur une base dédiée (`ia_consultations_qa_migrations`), distincte de la
base des tests applicatifs — pour qu'un `down` de ce test ne détruise pas les
migrations d'une autre suite. La base dédiée est créée puis supprimée par le test.

Aucune donnée réelle n'est créée ici : le test ne manipule que le **schéma**.
"""

from __future__ import annotations

import pytest

from app.storage.connexion import ConnexionAdministration
from app.storage.migrations import ExecuteurMigrations

from .conftest import URL_MAINTENANCE, URL_MIGRATIONS

NOM_BASE = URL_MIGRATIONS.rsplit("/", 1)[-1]


def _table_existe(admin: ConnexionAdministration, table: str) -> bool:
    return bool(
        admin.lire(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table,),
        )
    )


def _colonne_existe(admin: ConnexionAdministration, table: str, colonne: str) -> bool:
    return bool(
        admin.lire(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s;",
            (table, colonne),
        )
    )


def _nb_tables(admin: ConnexionAdministration) -> int:
    return int(
        admin.lire(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
        )[0][0]
    )


@pytest.fixture(scope="module")
def base_dediee():
    """Crée une base vierge dédiée, la rend, puis la supprime."""
    maintenance = ConnexionAdministration(URL_MAINTENANCE).ouvrir()
    try:
        maintenance.executer_script(f'DROP DATABASE IF EXISTS "{NOM_BASE}";')
        maintenance.executer_script(f'CREATE DATABASE "{NOM_BASE}";')
    finally:
        maintenance.fermer()
    try:
        yield URL_MIGRATIONS
    finally:
        maintenance = ConnexionAdministration(URL_MAINTENANCE).ouvrir()
        try:
            maintenance.executer_script(f'DROP DATABASE IF EXISTS "{NOM_BASE}";')
        finally:
            maintenance.fermer()


def test_up_puis_down_de_chaque_migration(base_dediee):
    executeur = ExecuteurMigrations(base_dediee)
    admin = ConnexionAdministration(base_dediee).ouvrir()
    try:
        # -- up ------------------------------------------------------------ #
        appliquees = executeur.up()
        assert appliquees == ["0001", "0002", "0003", "0004"], appliquees
        n_plein = _nb_tables(admin)
        assert _table_existe(admin, "client")
        assert _table_existe(admin, "entreprise")
        assert _table_existe(admin, "fiche_version")
        assert _table_existe(admin, "assurance")  # 0002
        assert _nb_tables(admin) > 20
        assert _colonne_existe(admin, "document", "nature")  # 0003
        assert _table_existe(admin, "consultation")  # 0003
        assert _table_existe(admin, "extraction_element")  # 0003
        assert _table_existe(admin, "checklist_execution")  # 0004
        assert _table_existe(admin, "checklist_ligne")  # 0004

        # -- 0004 : down puis structure retirée ---------------------------- #
        assert executeur.down(1) == ["0004"]
        assert not _table_existe(admin, "checklist_ligne")
        assert not _table_existe(admin, "checklist_execution")
        assert _table_existe(admin, "consultation")  # 0003 encore là

        # -- 0003 : down --------------------------------------------------- #
        assert executeur.down(1) == ["0003"]
        assert not _table_existe(admin, "extraction_element")
        assert not _table_existe(admin, "consultation")
        assert not _colonne_existe(admin, "document", "nature")
        assert _table_existe(admin, "fiche_version")  # 0001 encore là

        # -- 0002 : down --------------------------------------------------- #
        assert executeur.down(1) == ["0002"]
        assert not _table_existe(admin, "assurance")
        assert _table_existe(admin, "entreprise")  # 0001 encore là

        # -- 0001 : down --------------------------------------------------- #
        assert executeur.down(1) == ["0001"]
        assert not _table_existe(admin, "client")
        assert _nb_tables(admin) == 1  # seul reste `schema_migration`

        # -- remontée complète : la base revient à l'état plein ------------- #
        remontees = executeur.up()
        assert remontees == ["0001", "0002", "0003", "0004"], remontees
        assert _nb_tables(admin) == n_plein
        assert _table_existe(admin, "client")
        assert _table_existe(admin, "checklist_ligne")
        assert _colonne_existe(admin, "document", "nature")

        print(f"\n[migrations] tables après up complet : {n_plein}")
        print("[migrations] séquence up/down rejouée : 0001, 0002, 0003, 0004")
    finally:
        admin.fermer()
