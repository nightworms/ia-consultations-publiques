"""Hachage des mots de passe (annexe A § A5).

Un mot de passe n'est **jamais** stocké en clair, jamais journalisé, jamais
renvoyé. Le hachage utilise **Argon2id** (`argon2-cffi`) avec les paramètres par
défaut de la bibliothèque (memoire 64 Mio, 3 passes, parallélisme 1) : c'est
l'algorithme recommandé aujourd'hui pour les mots de passe.

Aucun mot de passe réel n'apparaît dans le code ni dans les tests : les jeux de
test sont fictifs et signalés comme tels.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasheur = PasswordHasher()

LONGUEUR_MINIMALE = 12


class ErreurMotDePasse(RuntimeError):
    """Mot de passe refusé (vide, trop court)."""


def valider_force(mot_de_passe: str) -> None:
    """Contrôle minimal de robustesse. Lève `ErreurMotDePasse` si insuffisant."""
    if not isinstance(mot_de_passe, str) or mot_de_passe.strip() == "":
        raise ErreurMotDePasse("Le mot de passe ne peut pas être vide.")
    if len(mot_de_passe) < LONGUEUR_MINIMALE:
        raise ErreurMotDePasse(
            f"Le mot de passe doit comporter au moins {LONGUEUR_MINIMALE} caractères."
        )


def hacher(mot_de_passe: str) -> str:
    """Renvoie l'empreinte Argon2id d'un mot de passe (jamais le mot de passe)."""
    valider_force(mot_de_passe)
    return _hasheur.hash(mot_de_passe)


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    """Vérifie un mot de passe contre son empreinte. Ne lève pas : renvoie un booléen."""
    if not mot_de_passe or not empreinte:
        return False
    try:
        return _hasheur.verify(empreinte, mot_de_passe)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def a_rehacher(empreinte: str) -> bool:
    """Vrai si l'empreinte a été produite avec des paramètres périmés."""
    try:
        return _hasheur.check_needs_rehash(empreinte)
    except (InvalidHashError, VerificationError):
        return False
