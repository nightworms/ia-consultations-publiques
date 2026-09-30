"""Chiffrement applicatif des champs sensibles (annexe A § A6).

* Algorithme : **AES-256-GCM** (confidentialité **et** intégrité).
* Clé **maîtresse** fournie par variable d'environnement (32 octets).
* Clé de **données dérivée par `client_id`** via **HKDF-SHA256** — le chiffrement
  est **par client, jamais global**. Un client ne peut pas déchiffrer les champs
  d'un autre : la dérivation de clé ne le lui permet pas.
* Format stocké **versionné**, réversible : `v1:<base64(nonce || ciphertext+tag)>`.
  Le préfixe de version autorise une rotation future sans casser les données
  déjà écrites.

Aucune clé n'est écrite dans le code ni dans le dépôt.
"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

VERSION_COURANTE = "v1"
PREFIXE = VERSION_COURANTE + ":"
TAILLE_NONCE = 12  # 96 bits, recommandation GCM
_TAILLE_CLE = 32  # AES-256
_INFO_HKDF = b"ia-consultations-publiques|chiffrement-champs|v1"


class ErreurChiffrement(RuntimeError):
    """Chiffrement impossible (paramètre invalide)."""


class ErreurDechiffrement(RuntimeError):
    """Déchiffrement refusé : mauvaise clé, mauvais client, ou contenu altéré."""


def _verifier_cle_maitresse(cle_maitresse: bytes) -> None:
    if not isinstance(cle_maitresse, (bytes, bytearray)) or len(cle_maitresse) != _TAILLE_CLE:
        raise ErreurChiffrement(
            f"La clé maîtresse doit faire {_TAILLE_CLE} octets, reçu "
            f"{len(cle_maitresse) if cle_maitresse is not None else 'None'}."
        )


def deriver_cle_client(cle_maitresse: bytes, client_id: str) -> bytes:
    """Dérive la clé de données propre à un client (HKDF-SHA256, sel = client_id)."""
    _verifier_cle_maitresse(cle_maitresse)
    if not client_id:
        raise ErreurChiffrement("client_id obligatoire pour dériver une clé.")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_TAILLE_CLE,
        salt=str(client_id).encode("utf-8"),
        info=_INFO_HKDF,
    )
    return hkdf.derive(bytes(cle_maitresse))


def chiffrer(cle_maitresse: bytes, client_id: str, clair: str | bytes) -> str:
    """Chiffre une valeur au nom d'un client. Renvoie une chaîne `v1:...`."""
    cle = deriver_cle_client(cle_maitresse, client_id)
    donnees = clair.encode("utf-8") if isinstance(clair, str) else bytes(clair)
    nonce = os.urandom(TAILLE_NONCE)
    chiffre = AESGCM(cle).encrypt(nonce, donnees, associated_data=str(client_id).encode("utf-8"))
    return PREFIXE + base64.b64encode(nonce + chiffre).decode("ascii")


def dechiffrer(cle_maitresse: bytes, client_id: str, valeur_stockee: str) -> str:
    """Déchiffre une valeur au nom d'un client.

    Lève `ErreurDechiffrement` si la valeur appartient à un autre client, si la
    clé est fausse, ou si le contenu a été altéré — la clé étant dérivée du
    `client_id`, un client ne peut pas lire les champs d'un autre.
    """
    if not isinstance(valeur_stockee, str) or not valeur_stockee.startswith(PREFIXE):
        raise ErreurDechiffrement(
            "Format chiffré non reconnu : préfixe de version "
            f"{PREFIXE!r} attendu."
        )
    try:
        brut = base64.b64decode(valeur_stockee[len(PREFIXE):], validate=True)
    except (ValueError, TypeError) as exc:
        raise ErreurDechiffrement("Charge utile base64 invalide.") from exc
    if len(brut) <= TAILLE_NONCE:
        raise ErreurDechiffrement("Charge utile chiffrée trop courte.")

    cle = deriver_cle_client(cle_maitresse, client_id)
    nonce, chiffre = brut[:TAILLE_NONCE], brut[TAILLE_NONCE:]
    try:
        clair = AESGCM(cle).decrypt(
            nonce, chiffre, associated_data=str(client_id).encode("utf-8")
        )
    except InvalidTag as exc:
        raise ErreurDechiffrement(
            "Déchiffrement refusé : clé incorrecte, client différent, ou donnée "
            "altérée (l'authentification GCM a échoué)."
        ) from exc
    return clair.decode("utf-8")


def version_de(valeur_stockee: str) -> str:
    """Renvoie la version de format d'une valeur stockée (`v1` par défaut)."""
    if isinstance(valeur_stockee, str) and ":" in valeur_stockee:
        return valeur_stockee.split(":", 1)[0]
    return VERSION_COURANTE
