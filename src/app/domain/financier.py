"""Famille 2 — Capacités financières. Voir ``docs/DATA-MODEL.md`` § 7."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from .commun import Montant, Sensibilite


class TypeAttestation(str, Enum):
    """Liste indicative — à compléter."""

    REGULARITE_FISCALE = "regularite_fiscale"
    VIGILANCE_URSSAF = "vigilance_urssaf"
    CAPACITE_FINANCIERE = "capacite_financiere"
    AUTRE = "autre"


@dataclass
class ExerciceComptable:
    """Un exercice comptable (au moins les trois derniers)."""

    id: str
    entreprise_id: str
    annee_exercice: int
    chiffre_affaires: Montant
    resultat_net: Optional[Montant] = None
    capitaux_propres: Optional[Montant] = None
    total_bilan: Optional[Montant] = None
    effectif_moyen: Optional[int] = None
    date_cloture: Optional[date] = None
    source_document_id: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.CONFIDENTIEL


@dataclass
class Attestation:
    """Attestation justificative à durée de validité (fiscale, URSSAF...)."""

    id: str
    entreprise_id: str
    type_attestation: TypeAttestation
    emetteur: str
    date_emission: date
    piece_document_id: str
    date_validite_fin: Optional[date] = None  # échéance à surveiller
    montant_engage: Optional[Montant] = None
    source_document_id: Optional[str] = None
