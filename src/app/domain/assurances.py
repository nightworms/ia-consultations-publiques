"""Famille 3 — Assurances. Voir ``docs/DATA-MODEL.md`` § 8.

La date d'échéance est l'information la plus critique de cette famille.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from .commun import Montant


class TypeAssurance(str, Enum):
    """Liste indicative — à compléter."""

    DECENNALE = "decennale"
    RC_PROFESSIONNELLE = "rc_professionnelle"
    RC_EXPLOITATION = "rc_exploitation"
    TOUS_RISQUES_CHANTIER = "tous_risques_chantier"
    AUTRE = "autre"


@dataclass
class Assurance:
    """Contrat d'assurance et son attestation rattachée."""

    id: str
    entreprise_id: str
    type_assurance: TypeAssurance
    assureur: str
    date_debut: date
    date_echeance: date  # échéance à surveiller (critique)
    piece_document_id: str
    numero_contrat: Optional[str] = None
    montant_garantie: Optional[Montant] = None
    franchise: Optional[Montant] = None
    activites_couvertes: Optional[str] = None
    source_document_id: Optional[str] = None
