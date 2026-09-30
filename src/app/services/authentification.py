"""Authentification — compte local, session par cookie signé (annexe A § A5).

* Un utilisateur appartient à **un seul `client`** au MVP.
* Le mot de passe est haché (Argon2id) et stocké dans `authentification`, table
  dédiée — jamais dans les tables de contenu.
* La session est un **cookie signé** (itsdangerous), sans état serveur ; le
  `client_id` est porté par le jeton et devient le contexte de requête.
* Aucune clé n'est en dur : `CLE_SESSION` vient de l'environnement.

Un utilisateur = un client : à la connexion, le `client_id` découvert est celui
de l'utilisateur, jamais choisi par l'appelant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.securite import mots_de_passe
from app.storage.connexion import Connexion, ContexteClient

SEL_SESSION = "ia-consultations-publiques.session"


class ErreurAuthentification(RuntimeError):
    """Échec d'authentification (identifiants invalides, session absente ou expirée)."""


@dataclass(frozen=True)
class IdentiteSession:
    """Identité portée par une session ouverte."""

    utilisateur_id: str
    client_id: str
    nom_affichage: str


class ServiceAuthentification:
    """Compte local + sessions signées."""

    def __init__(
        self,
        connexion: Connexion,
        cle_session: str,
        duree_session_secondes: int = 86400,
    ) -> None:
        if not cle_session:
            raise ErreurAuthentification("CLE_SESSION absente : session impossible.")
        self._connexion = connexion
        self._serialiseur = URLSafeTimedSerializer(cle_session, salt=SEL_SESSION)
        self._duree = duree_session_secondes

    # -- comptes -----------------------------------------------------------
    def creer_utilisateur(
        self,
        contexte: ContexteClient,
        identifiant_connexion: str,
        nom_affichage: str,
        mot_de_passe: str,
    ) -> str:
        """Crée un compte local rattaché au client du contexte. Renvoie l'id utilisateur."""
        if not identifiant_connexion or not nom_affichage:
            raise ErreurAuthentification("Identifiant et nom d'affichage obligatoires.")
        empreinte = mots_de_passe.hacher(mot_de_passe)  # lève si trop faible

        ligne = self._connexion.executer_une(
            contexte,
            "INSERT INTO utilisateur (client_id, identifiant_connexion, nom_affichage) "
            "VALUES (%(client_id)s, %(identifiant)s, %(nom)s) RETURNING id;",
            {"identifiant": identifiant_connexion, "nom": nom_affichage},
        )
        if ligne is None:
            raise ErreurAuthentification("Création du compte impossible (aucune ligne retournée).")
        utilisateur_id = str(ligne["id"])

        self._connexion.executer(
            contexte,
            "INSERT INTO authentification (client_id, utilisateur_id, mot_de_passe_empreinte) "
            "VALUES (%(client_id)s, %(utilisateur_id)s, %(empreinte)s);",
            {"utilisateur_id": utilisateur_id, "empreinte": empreinte},
        )
        return utilisateur_id

    def changer_mot_de_passe(
        self, contexte: ContexteClient, utilisateur_id: str, nouveau_mot_de_passe: str
    ) -> None:
        empreinte = mots_de_passe.hacher(nouveau_mot_de_passe)
        self._connexion.executer(
            contexte,
            "UPDATE authentification SET mot_de_passe_empreinte = %(empreinte)s, "
            "date_modification = now() "
            "WHERE client_id = %(client_id)s AND utilisateur_id = %(utilisateur_id)s;",
            {"utilisateur_id": utilisateur_id, "empreinte": empreinte},
        )

    # -- connexion ---------------------------------------------------------
    def authentifier(self, identifiant_connexion: str, mot_de_passe: str) -> Optional[IdentiteSession]:
        """Vérifie les identifiants. Renvoie l'identité ou None (jamais d'erreur détaillée)."""
        identite = self._connexion.rechercher_identite_connexion(identifiant_connexion)
        if identite is None:
            return None
        if identite.get("statut") != "actif":
            return None
        if not mots_de_passe.verifier(mot_de_passe, identite["mot_de_passe_empreinte"]):
            return None
        return IdentiteSession(
            utilisateur_id=str(identite["utilisateur_id"]),
            client_id=str(identite["client_id"]),
            nom_affichage=identite["nom_affichage"],
        )

    # -- sessions ----------------------------------------------------------
    def creer_cookie_session(self, identite: IdentiteSession) -> str:
        """Signe un jeton de session portant le client_id de l'utilisateur."""
        return self._serialiseur.dumps(
            {
                "u": identite.utilisateur_id,
                "c": identite.client_id,
                "n": identite.nom_affichage,
            }
        )

    def lire_session(self, jeton: Optional[str]) -> IdentiteSession:
        """Valide un jeton de session. Lève `ErreurAuthentification` si invalide/expiré."""
        if not jeton:
            raise ErreurAuthentification("Session absente.")
        try:
            charge: dict[str, Any] = self._serialiseur.loads(jeton, max_age=self._duree)
        except SignatureExpired as exc:
            raise ErreurAuthentification("Session expirée.") from exc
        except BadSignature as exc:
            raise ErreurAuthentification("Session invalide (signature).") from exc
        try:
            return IdentiteSession(
                utilisateur_id=str(charge["u"]),
                client_id=str(charge["c"]),
                nom_affichage=str(charge["n"]),
            )
        except (KeyError, TypeError) as exc:
            raise ErreurAuthentification("Session incomplète.") from exc
