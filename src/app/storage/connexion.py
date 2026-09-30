"""Connexion PostgreSQL — point d'entrée unique du SQL applicatif.

Deux usages, deux surfaces, jamais mélangés :

* `Connexion` — **le seul point d'entrée du SQL sur les données**. Chaque requête
  exige un `ContexteClient` (le `client_id` de la session). Le filtre
  `%(client_id)s` est **obligatoire** dans la requête, et la valeur est **imposée
  par le contexte** : un appelant ne peut pas la fournir ni la falsifier. C'est le
  cloisonnement par construction (annexe A § A1), vérifiable requête par requête.
* `ConnexionAdministration` — réservée **aux migrations** (DDL). Elle ne touche
  aucune donnée client et n'est pas exposée à la couche applicative.

Aucune couche n'accède à la persistance sans passer par ici (annexe A § A3).
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Optional, Sequence

import psycopg
from psycopg.rows import dict_row


#: Jeton de filtre client attendu dans toute requête sur les données.
PLACEHOLDER_CLIENT = "%(client_id)s"


class ErreurCloisonnement(RuntimeError):
    """Une requête violerait le cloisonnement par client."""


class ContexteClientManquant(ErreurCloisonnement):
    """Aucun contexte client fourni : refus d'exécuter la requête."""


class ContexteClient:
    """Contexte de requête portant le `client_id` de la session courante.

    Un contexte ne peut être construit qu'avec un UUID valide ; il est immuable.
    """

    __slots__ = ("_client_id",)

    def __init__(self, client_id: str) -> None:
        try:
            valide = str(uuid.UUID(str(client_id)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ErreurCloisonnement(
                f"client_id invalide (UUID attendu) : {client_id!r}"
            ) from exc
        self._client_id = valide

    @property
    def client_id(self) -> str:
        return self._client_id

    def __repr__(self) -> str:  # pragma: no cover — aide au débogage
        return f"ContexteClient({self._client_id})"


def _verifier_filtre_client(sql: str) -> None:
    """Refuse une requête qui ne filtre pas sur le client.

    Le jeton doit être présent. Pour les ordres qui comportent un `WHERE`
    (SELECT / UPDATE / DELETE), il doit apparaître **dans la clause WHERE** :
    un jeton placé ailleurs ne cloisonne rien.
    """
    if PLACEHOLDER_CLIENT not in sql:
        raise ErreurCloisonnement(
            "Requête refusée : aucune mention de "
            f"{PLACEHOLDER_CLIENT!r}. Toute requête sur les données doit filtrer "
            "sur le client. Le filtre est imposé par `Connexion.executer`."
        )
    premier_mot = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    if premier_mot in {"SELECT", "UPDATE", "DELETE", "WITH"}:
        position_where = sql.upper().rfind("WHERE")
        if position_where == -1:
            raise ErreurCloisonnement(
                "Requête refusée : aucune clause WHERE alors que la requête lit ou "
                "modifie des données. Le filtre client est obligatoire."
            )
        if PLACEHOLDER_CLIENT not in sql[position_where:]:
            raise ErreurCloisonnement(
                "Requête refusée : le filtre client doit se trouver dans la clause "
                "WHERE, sinon il ne cloisonne rien."
            )


class Connexion:
    """Connexion unique du SQL sur les données, exigeant un contexte client."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: Any = None

    # -- cycle de vie ------------------------------------------------------
    def ouvrir(self) -> "Connexion":
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._dsn, row_factory=dict_row)  # type: ignore[arg-type]
        return self

    def fermer(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def __enter__(self) -> "Connexion":
        return self.ouvrir()

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.annuler()
        self.fermer()

    @property
    def brute(self) -> psycopg.Connection:
        """Connexion psycopg sous-jacente — usage interne (transactions)."""
        if self._conn is None or self._conn.closed:
            self.ouvrir()
        assert self._conn is not None
        return self._conn

    def valider(self) -> None:
        self.brute.commit()

    def annuler(self) -> None:
        self.brute.rollback()

    # -- exécution cloisonnée ---------------------------------------------
    def executer(
        self,
        contexte: Optional[ContexteClient],
        sql: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Exécute une requête **dans le contexte d'un client**.

        Refuse toute requête sans contexte client (`ContexteClientManquant`) ou
        sans filtre `%(client_id)s` (`ErreurCloisonnement`). Toute valeur de
        `client_id` fournie par l'appelant est **écrasée** par celle du contexte :
        une tentative de lecture des données d'un autre client échoue.
        """
        if not isinstance(contexte, ContexteClient):
            raise ContexteClientManquant(
                "`executer` exige un `ContexteClient`. Aucune requête sur les données "
                "n'est permise sans contexte client."
            )
        _verifier_filtre_client(sql)

        valeurs = dict(params or {})
        # La valeur du contexte prime, systématiquement.
        valeurs["client_id"] = contexte.client_id

        with self.brute.cursor() as cur:
            cur.execute(sql, valeurs)  # type: ignore[arg-type]
            if cur.description is None:
                return []
            return list(cur.fetchall())

    def executer_une(
        self,
        contexte: Optional[ContexteClient],
        sql: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Comme `executer`, mais renvoie au plus une ligne."""
        lignes = self.executer(contexte, sql, params)
        return lignes[0] if lignes else None

    def rechercher_identite_connexion(
        self, identifiant_connexion: str
    ) -> Optional[dict[str, Any]]:
        """Seule requête autorisée **avant** l'ouverture de session.

        À la connexion, le client n'est pas encore connu : il faut bien lire
        l'utilisateur pour le découvrir. Cette méthode est donc une exception
        **nommée et bornée** : SQL figé (aucune concaténation), tables
        `utilisateur` + `authentification` uniquement, aucune donnée de contenu.
        Aucun SQL arbitraire n'est admis hors contexte client.
        """
        if not identifiant_connexion:
            return None
        sql = (
            "SELECT u.id AS utilisateur_id, u.client_id, u.nom_affichage, u.statut, "
            "a.mot_de_passe_empreinte "
            "FROM utilisateur u "
            "JOIN authentification a ON a.utilisateur_id = u.id "
            "WHERE u.identifiant_connexion = %(identifiant)s"
        )
        with self.brute.cursor() as cur:
            cur.execute(sql, {"identifiant": identifiant_connexion})  # type: ignore[arg-type]
            ligne = cur.fetchone()
            return dict(ligne) if ligne is not None else None

    def creer_client(self, libelle: str) -> str:
        """Provisionne un `client` — racine du cloisonnement, sans `client_id`.

        Deuxième exception **nommée et bornée** : la table `client` est la racine
        du cloisonnement et ne peut donc pas être écrite « dans le contexte d'un
        client ». SQL figé, une seule table, aucun contenu métier.
        """
        if not libelle or not libelle.strip():
            raise ErreurCloisonnement("Le libellé d'un client est obligatoire.")
        with self.brute.cursor() as cur:
            cur.execute(  # type: ignore[arg-type]
                "INSERT INTO client (libelle) VALUES (%(libelle)s) RETURNING id;",
                {"libelle": libelle.strip()},
            )
            ligne: Any = cur.fetchone()
            if ligne is None:  # pragma: no cover — RETURNING garantit une ligne
                raise ErreurCloisonnement("Création du client impossible.")
            return str(ligne["id"])


class ConnexionAdministration:
    """Connexion réservée aux migrations (DDL). Aucune donnée client.

    Elle existe pour qu'aucun module applicatif ne contourne `Connexion` : seul
    `storage/migrations.py` l'instancie.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: Optional[psycopg.Connection] = None

    def ouvrir(self) -> "ConnexionAdministration":
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._dsn, autocommit=True)
        return self

    def fermer(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def __enter__(self) -> "ConnexionAdministration":
        return self.ouvrir()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.fermer()

    def executer_script(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        """Exécute un script (plusieurs ordres possibles). Réservé au DDL."""
        if self._conn is None:
            self.ouvrir()
        assert self._conn is not None
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # type: ignore[arg-type]

    def lire(self, sql: str, params: Optional[Sequence[Any]] = None) -> list[tuple]:
        if self._conn is None:
            self.ouvrir()
        assert self._conn is not None
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # type: ignore[arg-type]
            if cur.description is None:
                return []
            return list(cur.fetchall())
