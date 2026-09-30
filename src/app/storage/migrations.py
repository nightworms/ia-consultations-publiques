"""Exécuteur de migrations SQL numérotées et réversibles.

Convention projet (annexe A § A4) : un fichier par changement, nommé
`000N_description.sql`, contenant **deux sections balisées** :

    -- +migrate up
    ... ordres SQL appliquant le changement ...
    -- +migrate down
    ... ordres SQL annulant proprement le changement ...

Aucun ORM, aucun outil de migration externe : le fichier est lu, découpé, puis
exécuté par cette fonction. Les migrations déjà appliquées sont enregistrées dans
`schema_migration` et ne sont jamais rejouées.

Usage en ligne de commande (depuis le dossier `src/`) :

    python -m app.storage.migrations statut
    python -m app.storage.migrations up
    python -m app.storage.migrations down        # annule la dernière
    python -m app.storage.migrations down 2      # annule les deux dernières
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import ErreurConfiguration, charger_config
from app.storage.connexion import ConnexionAdministration

REPERTOIRE_MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"

_BALISE_UP = "-- +migrate up"
_BALISE_DOWN = "-- +migrate down"

TABLE_MIGRATION = """
CREATE TABLE IF NOT EXISTS schema_migration (
    numero      varchar(10)  PRIMARY KEY,
    nom         varchar(255) NOT NULL,
    applique_le timestamptz  NOT NULL DEFAULT now()
);
"""


class ErreurMigration(RuntimeError):
    """Migration illisible, mal formée, ou en échec."""


@dataclass(frozen=True)
class Migration:
    numero: str
    nom: str
    chemin: Path
    sql_up: str
    sql_down: str


def _decouper_sections(contenu: str, chemin: Path) -> tuple[str, str]:
    if _BALISE_UP not in contenu or _BALISE_DOWN not in contenu:
        raise ErreurMigration(
            f"{chemin.name} : les deux sections '{_BALISE_UP}' et '{_BALISE_DOWN}' "
            "sont obligatoires (annexe A § A4)."
        )
    apres_up = contenu.split(_BALISE_UP, 1)[1]
    sql_up, _, apres_down = apres_up.partition(_BALISE_DOWN)
    sql_down = apres_down
    # On retire tout marqueur de section résiduel.
    sql_up = sql_up.strip()
    sql_down = re.sub(r"--\s*\+migrate\s+(up|down).*", "", sql_down).strip()
    if not sql_up:
        raise ErreurMigration(f"{chemin.name} : section « up » vide.")
    if not sql_down:
        raise ErreurMigration(f"{chemin.name} : section « down » vide (réversibilité exigée).")
    return sql_up, sql_down


def lister_migrations(repertoire: Path = REPERTOIRE_MIGRATIONS) -> list[Migration]:
    """Retourne les migrations du dossier, triées par numéro croissant."""
    if not repertoire.is_dir():
        raise ErreurMigration(f"Dossier de migrations introuvable : {repertoire}")
    migrations: list[Migration] = []
    for chemin in sorted(repertoire.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        numero = chemin.name[:4]
        contenu = chemin.read_text(encoding="utf-8")
        sql_up, sql_down = _decouper_sections(contenu, chemin)
        migrations.append(
            Migration(numero=numero, nom=chemin.stem, chemin=chemin, sql_up=sql_up, sql_down=sql_down)
        )
    numeros = [m.numero for m in migrations]
    doublons = {n for n in numeros if numeros.count(n) > 1}
    if doublons:
        raise ErreurMigration(f"Numéros de migration dupliqués : {sorted(doublons)}")
    return migrations


class ExecuteurMigrations:
    """Applique et annule les migrations sur une base PostgreSQL."""

    def __init__(self, dsn: str, repertoire: Path = REPERTOIRE_MIGRATIONS) -> None:
        self._dsn = dsn
        self._repertoire = repertoire

    # -- état --------------------------------------------------------------
    def appliquees(self, conn: ConnexionAdministration) -> list[str]:
        conn.executer_script(TABLE_MIGRATION)
        lignes = conn.lire("SELECT numero FROM schema_migration ORDER BY numero;")
        return [ligne[0] for ligne in lignes]

    def statut(self) -> list[tuple[str, str]]:
        """Renvoie (numero, état) pour chaque migration connue."""
        conn = ConnexionAdministration(self._dsn).ouvrir()
        try:
            appliquees = set(self.appliquees(conn))
            return [
                (m.numero, "appliquée" if m.numero in appliquees else "en attente")
                for m in lister_migrations(self._repertoire)
            ]
        finally:
            conn.fermer()

    # -- actions -----------------------------------------------------------
    def up(self, cible: str | None = None) -> list[str]:
        """Applique toutes les migrations en attente (ou jusqu'à `cible` incluse)."""
        conn = ConnexionAdministration(self._dsn).ouvrir()
        try:
            deja = set(self.appliquees(conn))
            faites: list[str] = []
            for migration in lister_migrations(self._repertoire):
                if migration.numero in deja:
                    continue
                conn.executer_script(migration.sql_up)
                conn.executer_script(
                    "INSERT INTO schema_migration (numero, nom) VALUES (%s, %s);",
                    (migration.numero, migration.nom),
                )
                faites.append(migration.numero)
                if cible is not None and migration.numero == cible:
                    break
            return faites
        finally:
            conn.fermer()

    def down(self, nombre: int = 1) -> list[str]:
        """Annule les `nombre` dernières migrations appliquées (ordre inverse)."""
        if nombre < 1:
            raise ErreurMigration("Le nombre de migrations à annuler doit être ≥ 1.")
        conn = ConnexionAdministration(self._dsn).ouvrir()
        try:
            appliquees = self.appliquees(conn)
            par_numero = {m.numero: m for m in lister_migrations(self._repertoire)}
            annulees: list[str] = []
            for numero in reversed(appliquees):
                if len(annulees) >= nombre:
                    break
                if numero not in par_numero:
                    raise ErreurMigration(
                        f"Migration {numero} enregistrée en base mais absente du dossier "
                        f"{self._repertoire} : annulation impossible."
                    )
                conn.executer_script(par_numero[numero].sql_down)
                conn.executer_script(
                    "DELETE FROM schema_migration WHERE numero = %s;", (numero,)
                )
                annulees.append(numero)
            return annulees
        finally:
            conn.fermer()


def _main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description="Exécuteur de migrations (postgresql).")
    analyseur.add_argument("action", choices=["up", "down", "statut"])
    analyseur.add_argument("nombre", nargs="?", type=int, default=1, help="pour « down »")
    options = analyseur.parse_args(argv)

    try:
        cfg = charger_config()
    except ErreurConfiguration as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2

    executeur = ExecuteurMigrations(cfg.database_url)
    if options.action == "statut":
        for numero, etat in executeur.statut():
            print(f"{numero}  {etat}")
        return 0
    if options.action == "up":
        faites = executeur.up()
        print("Migrations appliquées : " + (", ".join(faites) if faites else "aucune"))
        return 0
    annulees = executeur.down(options.nombre)
    print("Migrations annulées : " + (", ".join(annulees) if annulees else "aucune"))
    return 0


if __name__ == "__main__":  # pragma: no cover — point d'entrée CLI
    raise SystemExit(_main())
