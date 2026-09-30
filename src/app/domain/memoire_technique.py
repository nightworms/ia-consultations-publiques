"""Famille 9 — Mémoire technique type. Voir ``docs/DATA-MODEL.md`` § 14.

Ce module stocke un mémoire type réutilisable ; il ne rédige rien automatiquement
(hors périmètre phase 1) et n'automatise aucune signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class StatutChapitre(str, Enum):
    BROUILLON = "brouillon"
    ACCEPTE = "accepte"
    ARCHIVE = "archive"


@dataclass
class ChapitreMemoire:
    """Un chapitre réutilisable du mémoire technique type."""

    id: str
    entreprise_id: str
    titre: str
    ordre: int
    contenu_texte: str
    statut: StatutChapitre = StatutChapitre.BROUILLON
    date_redaction: Optional[date] = None
    references_liees_ids: list[str] = field(default_factory=list)
    documents_associes_ids: list[str] = field(default_factory=list)
    source_document_id: Optional[str] = None
