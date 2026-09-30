"""Versionnement de la fiche entreprise. Voir ``docs/DATA-MODEL.md`` § 5.

Une version « publiée » est immuable : toute correction crée une nouvelle version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class StatutFiche(str, Enum):
    BROUILLON = "brouillon"
    PUBLIEE = "publiee"
    ARCHIVEE = "archivee"


@dataclass
class FicheVersion:
    """Une version de la fiche entreprise."""

    id: str
    entreprise_id: str
    numero_version: int
    statut: StatutFiche
    date_creation: date
    version_parente_id: Optional[str] = None
    date_publication: Optional[date] = None
    commentaire: Optional[str] = None
