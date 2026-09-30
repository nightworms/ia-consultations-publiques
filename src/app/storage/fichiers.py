"""Stockage des pièces justificatives — hors dépôt, cloisonné, chiffré (annexe A § A6).

Règles tenues ici :

* Les fichiers vivent **hors du dépôt**, sous la racine `data/` (ignorée par git).
* Le chemin est **préfixé par le `client_id`** : `clients/<client_id>/<document_id>.bin`.
* **Aucun nom de fichier fourni par l'utilisateur** n'est utilisé tel quel.
* Le contenu est **chiffré sur disque** avec la clé dérivée du client : un client ne
  peut pas lire le fichier d'un autre.

`document_id` sert de nom de fichier : c'est la clé opaque de la table `document`.
"""

from __future__ import annotations

import base64
import hashlib
import os
import uuid
from pathlib import Path

from app.securite.chiffrement import ErreurChiffrement, chiffrer, dechiffrer


class ErreurStockage(RuntimeError):
    """Opération de stockage refusée ou impossible."""


def _uuid_valide(valeur: str, nom: str) -> str:
    try:
        return str(uuid.UUID(str(valeur)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ErreurStockage(f"{nom} invalide (UUID attendu) : {valeur!r}") from exc


def empreinte_sha256(contenu: bytes) -> str:
    """Empreinte d'intégrité d'un fichier, pour la colonne `empreinte_sha256`."""
    return hashlib.sha256(contenu).hexdigest()


class StockageFichiers:
    """Écrit et relit les pièces d'un client, chiffrées au repos."""

    def __init__(self, racine: str | os.PathLike[str], cle_maitresse: bytes) -> None:
        self._racine = Path(racine).expanduser().resolve()
        self._cle_maitresse = cle_maitresse

    @property
    def racine(self) -> Path:
        return self._racine

    # -- chemins -----------------------------------------------------------
    def chemin_relatif(self, client_id: str, document_id: str) -> str:
        """Chemin relatif cloisonné, construit par le code — jamais par l'utilisateur."""
        client = _uuid_valide(client_id, "client_id")
        document = _uuid_valide(document_id, "document_id")
        return f"clients/{client}/{document}.bin"

    def _chemin_absolu(self, client_id: str, document_id: str) -> Path:
        relatif = self.chemin_relatif(client_id, document_id)
        absolu = (self._racine / relatif).resolve()
        # Garde-fou : le chemin calculé doit rester sous la racine.
        if not str(absolu).startswith(str(self._racine) + os.sep):
            raise ErreurStockage("Chemin de stockage hors de la racine autorisée.")
        return absolu

    # -- écriture / lecture -----------------------------------------------
    def ecrire(self, client_id: str, document_id: str, contenu: bytes) -> str:
        """Chiffre et écrit un fichier. Renvoie le chemin relatif (colonne `chemin_stockage`)."""
        if not isinstance(contenu, (bytes, bytearray)):
            raise ErreurStockage("Le contenu à écrire doit être binaire (bytes).")
        chemin = self._chemin_absolu(client_id, document_id)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        charge = base64.b64encode(bytes(contenu)).decode("ascii")
        chiffre = chiffrer(self._cle_maitresse, client_id, charge)
        # Écriture atomique : fichier temporaire puis renommage.
        temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
        temporaire.write_text(chiffre, encoding="ascii")
        temporaire.replace(chemin)
        return self.chemin_relatif(client_id, document_id)

    def lire(self, client_id: str, document_id: str) -> bytes:
        """Relit et déchiffre un fichier. Refuse le fichier d'un autre client."""
        chemin = self._chemin_absolu(client_id, document_id)
        if not chemin.is_file():
            raise ErreurStockage(f"Fichier introuvable pour ce client : {document_id}.")
        charge = dechiffrer(self._cle_maitresse, client_id, chemin.read_text(encoding="ascii"))
        return base64.b64decode(charge.encode("ascii"))

    def existe(self, client_id: str, document_id: str) -> bool:
        return self._chemin_absolu(client_id, document_id).is_file()

    def supprimer(self, client_id: str, document_id: str) -> bool:
        chemin = self._chemin_absolu(client_id, document_id)
        if chemin.is_file():
            chemin.unlink()
            return True
        return False


def verifier_cle(cle_maitresse: bytes) -> None:
    """Contrôle de forme de la clé, pour échouer tôt."""
    if not cle_maitresse or len(cle_maitresse) != 32:
        raise ErreurChiffrement("Clé maîtresse invalide pour le stockage des fichiers.")
