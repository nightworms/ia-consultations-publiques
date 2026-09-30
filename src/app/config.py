"""Configuration de l'application — lecture stricte des variables d'environnement.

Règle projet : aucun secret en dur. Toutes les valeurs sensibles (chaîne de
connexion, clé maîtresse de chiffrement, clé de session) proviennent de
l'environnement. Une variable obligatoire absente provoque un échec explicite
(`ErreurConfiguration`), jamais une valeur par défaut silencieuse.

Variables lues (voir `.env.example` à la racine du projet) :

Obligatoires
    DATABASE_URL                 chaîne de connexion PostgreSQL
    CLE_CHIFFREMENT_MAITRESSE    clé maîtresse AES-256, 32 octets en base64
    CLE_SESSION                  secret de signature du cookie de session

Optionnelles (valeurs par défaut sûres)
    HOTE_API                     défaut 127.0.0.1 (jamais 0.0.0.0 : rien d'exposé)
    PORT_API                     défaut 8000
    REPERTOIRE_DOCUMENTS         défaut `data` (hors dépôt, ignoré par git)
    DUREE_SESSION_SECONDES       défaut 86400 (24 h)
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from functools import lru_cache


class ErreurConfiguration(RuntimeError):
    """Configuration invalide ou incomplète. Échouer tôt, échouer fort."""


#: Variables obligatoires.
_VARIABLES_OBLIGATOIRES = (
    "DATABASE_URL",
    "CLE_CHIFFREMENT_MAITRESSE",
    "CLE_SESSION",
)


def _lire_obligatoire(nom: str) -> str:
    valeur = os.environ.get(nom)
    if valeur is None or valeur.strip() == "":
        raise ErreurConfiguration(
            f"Variable d'environnement obligatoire absente : {nom}. "
            "Voir `.env.example` ; n'écrivez jamais de valeur réelle dans le dépôt."
        )
    return valeur.strip()


def _lire_entier(nom: str, defaut: int) -> int:
    brut = os.environ.get(nom)
    if brut is None or brut.strip() == "":
        return defaut
    try:
        return int(brut.strip())
    except ValueError as exc:
        raise ErreurConfiguration(
            f"Variable {nom} doit être un entier, reçu : {brut!r}"
        ) from exc


def _verifier_cle_maitresse(base64_valeur: str) -> bytes:
    """Décode la clé maîtresse et vérifie qu'elle fait exactement 32 octets."""
    try:
        brut = base64.b64decode(base64_valeur, validate=True)
    except (ValueError, TypeError) as exc:
        raise ErreurConfiguration(
            "CLE_CHIFFREMENT_MAITRESSE doit être une chaîne base64 valide "
            "(32 octets encodés)."
        ) from exc
    if len(brut) != 32:
        raise ErreurConfiguration(
            "CLE_CHIFFREMENT_MAITRESSE doit décoder exactement 32 octets "
            f"(AES-256) ; reçu {len(brut)} octets."
        )
    return brut


@dataclass(frozen=True)
class Config:
    """Configuration validée de l'application."""

    database_url: str
    cle_chiffrement_maitresse: bytes
    cle_session: str
    hote_api: str = "127.0.0.1"
    port_api: int = 8000
    repertoire_documents: str = "data"
    duree_session_secondes: int = 86400


def charger_config() -> Config:
    """Lit et valide la configuration depuis l'environnement.

    Lève `ErreurConfiguration` si une variable obligatoire manque ou est
    invalide. Aucune valeur par défaut n'est inventée pour un secret.
    """
    manquantes = [n for n in _VARIABLES_OBLIGATOIRES if not os.environ.get(n, "").strip()]
    if manquantes:
        raise ErreurConfiguration(
            "Variables d'environnement obligatoires absentes : "
            + ", ".join(manquantes)
            + ". Copiez `.env.example` vers `.env` et renseignez-les localement."
        )

    cle_maitresse = _verifier_cle_maitresse(_lire_obligatoire("CLE_CHIFFREMENT_MAITRESSE"))

    return Config(
        database_url=_lire_obligatoire("DATABASE_URL"),
        cle_chiffrement_maitresse=cle_maitresse,
        cle_session=_lire_obligatoire("CLE_SESSION"),
        hote_api=os.environ.get("HOTE_API", "127.0.0.1").strip() or "127.0.0.1",
        port_api=_lire_entier("PORT_API", 8000),
        repertoire_documents=os.environ.get("REPERTOIRE_DOCUMENTS", "data").strip() or "data",
        duree_session_secondes=_lire_entier("DUREE_SESSION_SECONDES", 86400),
    )


@lru_cache(maxsize=1)
def config() -> Config:
    """Configuration mise en cache pour le processus courant."""
    return charger_config()


def reinitialiser_cache() -> None:
    """Vide le cache de configuration (utile aux tests)."""
    config.cache_clear()


def generer_cle_maitresse() -> str:
    """Génère une clé maîtresse AES-256 encodée en base64.

    Outil de confort : la valeur produite n'est **jamais** écrite dans le dépôt,
    seulement affichée pour être collée dans un `.env` local.
    """
    return base64.b64encode(os.urandom(32)).decode("ascii")


if __name__ == "__main__":  # pragma: no cover — outil manuel
    print(generer_cle_maitresse())
