"""Garde d'isolation de la suite de tests — correctif C2.

Deux propriétés sont garanties ici, pour **tous** les tests du dépôt :

1. **Le fournisseur de modèle est imposé** : `MODELE_FOURNISSEUR` vaut
   `factice` pendant toute la suite, quelle que soit la valeur du `.env`
   local ou de l'environnement du développeur. La valeur réellement
   demandée avant forçage est conservée (`etat_fournisseur()["demande"]`)
   pour la traçabilité — elle n'est jamais utilisée.
2. **Aucun appel réseau sortant** : toute connexion, résolution de nom ou
   envoi UDP vers une adresse **non locale** échoue bruyamment
   (`ReseauInterdit`). Le bouclage (`127.0.0.0/8`, `::1`, `localhost`) et
   les sockets locales (UNIX) restent autorisés, car PostgreSQL tourne sur
   la machine (voir la limite documentée plus bas).

Pourquoi c'est nécessaire : sans cela, deux machines avec deux `.env`
donnaient deux verdicts (`factice` vert, `ue` rouge), et un test pouvait,
par accident, joindre un vrai fournisseur de modèle — donc envoyer un
document d'achat et consommer une clé.

Limite assumée et écrite franchement : `psycopg` parle à PostgreSQL par
`libpq` (bibliothèque C), dont les connexions ne passent pas par le module
`socket` de Python. La garde ci-dessous protège donc les clients HTTP
Python (`httpx`), pas une éventuelle sortie réseau faite en C.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import threading
from typing import Any, Mapping

import pytest

#: Verrou de pose de la garde (un seul fil à la fois).
_verrou = threading.Lock()

# --------------------------------------------------------------------------- #
# 1. Fournisseur imposé
# --------------------------------------------------------------------------- #

#: Fournisseur déterministe, sans réseau, imposé à toute la suite.
FOURNISSEUR_IMPOSE = "factice"

#: Variable lue par `app.services.fournisseur_modele.creer_fournisseur`.
NOM_VARIABLE_FOURNISSEUR = "MODELE_FOURNISSEUR"

#: Variables du fournisseur **réel** — neutralisées pendant les tests, pour
#: qu'une clé présente dans le `.env` local n'entre jamais dans le processus.
VARIABLES_FOURNISSEUR_REEL = (
    "MODELE_FOURNISSEUR_URL",
    "MODELE_FOURNISSEUR_CLE",
    "MODELE_FOURNISSEUR_NOM",
    "MODELE_FOURNISSEUR_ORGANISME",
    "MODELE_FOURNISSEUR_DELAI",
)

_etat: dict[str, Any] = {
    "demande": None,  # valeur présente dans l'environnement avant forçage
    "applique": False,  # le forçage a-t-il bien eu lieu ?
    "neutralisees": (),  # variables du fournisseur réel retirées
}


def forcer_fournisseur_factice() -> Mapping[str, Any]:
    """Impose `MODELE_FOURNISSEUR=factice` et neutralise le fournisseur réel.

    Idempotent : un second appel ne modifie pas l'état enregistré.
    """
    if not _etat["applique"]:
        _etat["demande"] = os.environ.get(NOM_VARIABLE_FOURNISSEUR)
        _etat["neutralisees"] = tuple(
            nom for nom in VARIABLES_FOURNISSEUR_REEL if nom in os.environ
        )
        for nom in VARIABLES_FOURNISSEUR_REEL:
            os.environ.pop(nom, None)
    os.environ[NOM_VARIABLE_FOURNISSEUR] = FOURNISSEUR_IMPOSE
    _etat["applique"] = True
    return dict(_etat)


def etat_fournisseur() -> dict[str, Any]:
    """État du forçage (valeur demandée, application, variables retirées)."""
    return dict(_etat)


# --------------------------------------------------------------------------- #
# 2. Garde réseau
# --------------------------------------------------------------------------- #


class ReseauInterdit(RuntimeError):
    """Un test a tenté une connexion réseau hors de la machine. C'est interdit."""


MESSAGE_RESEAU = (
    "Appel réseau sortant interdit pendant les tests (correctif C2) : cible "
    "{cible!r} via {operation}. La suite doit donner le même verdict sur toute "
    "machine, sans joindre de service extérieur et sans consommer de clé. "
    "Utilisez un transport simulé en mémoire (`httpx.MockTransport`) ou le "
    "fournisseur `factice`. Seul le bouclage (127.0.0.0/8, ::1, localhost) est "
    "autorisé, pour PostgreSQL local."
)


def _est_locale(hote: object) -> bool:
    """Vrai si la cible est la machine elle-même (bouclage, locale, ou vide)."""
    if hote is None:
        return True
    if isinstance(hote, (bytes, bytearray)):
        try:
            hote = bytes(hote).decode("ascii")
        except UnicodeDecodeError:
            return False
    if not isinstance(hote, str):
        return False
    nom = hote.strip().strip("[]")
    if nom in ("", "localhost") or nom.endswith(".localhost"):
        return True
    try:
        adresse = ipaddress.ip_address(nom.split("%", 1)[0])
    except ValueError:
        return False  # un nom : sa résolution sortirait de la machine
    return adresse.is_loopback or adresse.is_unspecified


def _verifier(cible: object, operation: str) -> None:
    if _est_locale(cible):
        return
    raise ReseauInterdit(MESSAGE_RESEAU.format(cible=cible, operation=operation))


_garde: dict[str, Any] = {"installee": False, "originaux": {}}


def garde_reseau_installee() -> bool:
    return bool(_garde["installee"])


def installer_garde_reseau() -> None:
    """Pose la garde sur les points d'entrée socket du module `socket`.

    Idempotent. Couvre : `socket.socket.connect`, `connect_ex`, `sendto`,
    `socket.create_connection` et `socket.getaddrinfo`.
    """
    with _verrou:
        if _garde["installee"]:
            return
        originaux = {
            "connect": socket.socket.connect,
            "connect_ex": socket.socket.connect_ex,
            "sendto": socket.socket.sendto,
            "create_connection": socket.create_connection,
            "getaddrinfo": socket.getaddrinfo,
        }

        def _cible(adresse: object) -> object:
            """Extrait le nom d'hôte d'une adresse socket."""
            if isinstance(adresse, (tuple, list)) and adresse:
                return adresse[0]
            return adresse

        def _locale_par_nature(sock: object) -> bool:
            """Vrai pour un socket local (UNIX) : il ne sort pas de la machine."""
            return getattr(sock, "family", None) == getattr(socket, "AF_UNIX", None)

        def _connect(self, adresse, *args, **kwargs):
            if not _locale_par_nature(self):
                _verifier(_cible(adresse), "socket.socket.connect")
            return originaux["connect"](self, adresse, *args, **kwargs)

        def _connect_ex(self, adresse, *args, **kwargs):
            if not _locale_par_nature(self):
                _verifier(_cible(adresse), "socket.socket.connect_ex")
            return originaux["connect_ex"](self, adresse, *args, **kwargs)

        def _sendto(self, donnees, *args, **kwargs):
            adresse: object = kwargs.get("address")
            if adresse is None and args:
                # sendto(data, address) ou sendto(data, flags, address)
                adresse = args[0] if len(args) == 1 else args[-1]
            if not _locale_par_nature(self):
                _verifier(_cible(adresse), "socket.socket.sendto")
            return originaux["sendto"](self, donnees, *args, **kwargs)

        def _create_connection(adresse, *args, **kwargs):
            _verifier(adresse[0] if isinstance(adresse, (tuple, list)) and adresse else adresse,
                      "socket.create_connection")
            return originaux["create_connection"](adresse, *args, **kwargs)

        def _getaddrinfo(hote, port, *args, **kwargs):
            _verifier(hote, "socket.getaddrinfo")
            return originaux["getaddrinfo"](hote, port, *args, **kwargs)

        socket.socket.connect = _connect
        socket.socket.connect_ex = _connect_ex
        socket.socket.sendto = _sendto
        socket.create_connection = _create_connection
        socket.getaddrinfo = _getaddrinfo

        _garde["originaux"] = originaux
        _garde["installee"] = True


# --------------------------------------------------------------------------- #
# 3. Verrou : la suite s'arrête net si l'isolation n'est pas en place
# --------------------------------------------------------------------------- #


def verifier_isolation() -> None:
    """Abandonne la session de tests si l'isolation n'est pas effective.

    Lève `pytest.UsageError` — la suite ne démarre pas — dès que :

    * `MODELE_FOURNISSEUR` ne vaut pas `factice` (le `.env` local a repris la
      main : les verdicts ne seraient plus reproductibles) ;
    * le forçage du fournisseur n'a pas été appliqué par `conftest.py` ;
    * la garde réseau n'est pas posée (un test pourrait joindre un vrai
      fournisseur et envoyer un document).
    """
    problemes: list[str] = []
    demande = os.environ.get(NOM_VARIABLE_FOURNISSEUR)
    if demande != FOURNISSEUR_IMPOSE:
        problemes.append(
            f"  - {NOM_VARIABLE_FOURNISSEUR} vaut {demande!r} au démarrage des tests "
            f"alors que la suite impose {FOURNISSEUR_IMPOSE!r}."
        )
    if not _etat["applique"]:
        problemes.append(
            "  - le forçage du fournisseur n'a pas été appliqué "
            "(src/tests/conftest.py n'a pas appelé forcer_fournisseur_factice())."
        )
    if not garde_reseau_installee():
        problemes.append(
            "  - la garde réseau n'est pas posée "
            "(src/tests/conftest.py n'a pas appelé installer_garde_reseau())."
        )
    if problemes:
        raise pytest.UsageError(
            "ISOLATION DES TESTS NON APPLIQUÉE — la suite refuse de démarrer.\n"
            + "\n".join(problemes)
            + "\n\nPourquoi : un test qui dépend du fournisseur configuré dans le "
            ".env local n'est pas reproductible — il donne un verdict différent "
            "d'une machine à l'autre (faux négatif chez le développeur, tentation "
            "d'affaiblir les assertions) et peut joindre un vrai fournisseur de "
            "modèle — donc envoyer un document et consommer une clé.\n"
            "Correctif attendu : src/tests/conftest.py doit imposer "
            f"{NOM_VARIABLE_FOURNISSEUR}={FOURNISSEUR_IMPOSE} et poser la garde "
            "réseau (src/tests/garde_isolation.py). Voir docs/RAPPORTS/C2-*.md."
        )


__all__ = [
    "FOURNISSEUR_IMPOSE",
    "NOM_VARIABLE_FOURNISSEUR",
    "VARIABLES_FOURNISSEUR_REEL",
    "ReseauInterdit",
    "etat_fournisseur",
    "forcer_fournisseur_factice",
    "garde_reseau_installee",
    "installer_garde_reseau",
    "verifier_isolation",
]
