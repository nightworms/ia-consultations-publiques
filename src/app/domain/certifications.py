"""Famille 4 — Certifications et qualifications. Voir ``docs/DATA-MODEL.md`` § 9.

Les intitulés et numéros sont lus sur le certificat, jamais reconstitués.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Certification:
    """Une certification ou qualification de l'entreprise."""

    id: str
    entreprise_id: str
    intitule: str  # repris du certificat
    organisme: str  # repris du certificat
    piece_document_id: str
    numero_certificat: Optional[str] = None
    domaine_metier: Optional[str] = None
    date_obtention: Optional[date] = None
    date_echeance: Optional[date] = None  # échéance à surveiller
    source_document_id: Optional[str] = None
