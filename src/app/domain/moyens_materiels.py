"""Famille 7 — Moyens matériels. Voir ``docs/DATA-MODEL.md`` § 12."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CategorieMateriel(str, Enum):
    """Liste indicative — à compléter."""

    ENGINS = "engins"
    ECHAFAUDAGES = "echafaudages"
    OUTILLAGE_SPECIFIQUE = "outillage_specifique"
    VEHICULES = "vehicules"
    AUTRE = "autre"


class Propriete(str, Enum):
    PROPRE = "propre"
    LOCATION = "location"


@dataclass
class MoyenMateriel:
    """Un moyen matériel de l'entreprise."""

    id: str
    entreprise_id: str
    categorie: CategorieMateriel
    designation: str
    quantite: int
    marque_modele: Optional[str] = None
    annee: Optional[int] = None
    propriete: Optional[Propriete] = None
    disponibilite: Optional[str] = None
    justificatif_document_id: Optional[str] = None
    source_document_id: Optional[str] = None
