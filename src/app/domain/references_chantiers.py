"""Famille 5 — Références de chantiers. Voir ``docs/DATA-MODEL.md`` § 10.

Poste le plus rentable : nourrit le mémoire technique (famille 9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .commun import Montant, Sensibilite


@dataclass
class ReferenceChantier:
    """Une référence de chantier réalisée."""

    id: str
    entreprise_id: str
    intitule_operation: str
    maitre_ouvrage: str
    nature_travaux: str
    lieu_commune: Optional[str] = None
    lieu_departement: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    montant: Optional[Montant] = None
    duree_mois: Optional[int] = None
    surface_traitee: Optional[str] = None
    description: Optional[str] = None
    competences_appliquees: Optional[str] = None
    attestation_bonne_execution_id: Optional[str] = None
    photos_document_ids: list[str] = field(default_factory=list)
    contact_reference: Optional[str] = None  # donnée personnelle
    sensibilite: Sensibilite = Sensibilite.INTERNE
    source_document_id: Optional[str] = None
