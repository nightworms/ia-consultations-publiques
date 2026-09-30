"""Configuration — lecture des paramètres par variables d'environnement.

Squelette : aucune valeur réelle, aucun secret, aucun fichier lu. Le squelette ne
lit pas encore l'environnement ; il montre où la configuration vivra.

Règle projet : aucun secret en dur dans le code. Les valeurs sensibles
(identifiants de base, clés d'API) vivront dans des variables d'environnement ou un
coffre, jamais dans le dépôt (voir ``.gitignore``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    """Configuration de l'application. Champs à confirmer en phase 2."""

    # Cible proposée : SQLite (chemin local) — à valider.
    chemin_base_donnees: Optional[str] = None
    # Cible proposée : FastAPI.
    hote_api: str = "127.0.0.1"
    port_api: int = 8000
    # Répertoire de stockage des documents (hors dépôt).
    repertoire_documents: Optional[str] = None


def charger_config() -> Config:
    """Charge la configuration depuis l'environnement. Squelette."""
    raise NotImplementedError
