"""Famille 8 — Fiches techniques produits. Voir ``docs/DATA-MODEL.md`` § 13.

La référence produit est recopiée du document fournisseur, jamais reconstituée.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class FamilleProduit(str, Enum):
    ETANCHEITE = "etancheite"
    ISOLATION = "isolation"
    AUTRE = "autre"  # à compléter par le lot L5


@dataclass
class Produit:
    """Un produit de fournisseur et ses documents associés."""

    id: str
    entreprise_id: str
    fournisseur: str
    reference_produit: str  # référence exacte du fournisseur
    designation: str
    famille: Optional[FamilleProduit] = None
    domaine_application: Optional[str] = None
    fiche_technique_document_id: Optional[str] = None
    certificats_document_ids: list[str] = field(default_factory=list)
    avis_technique_document_id: Optional[str] = None
    date_validite_document: Optional[date] = None  # échéance à surveiller
    source_document_id: Optional[str] = None
