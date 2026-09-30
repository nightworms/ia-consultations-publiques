"""Famille 4 — Certifications et qualifications : `certification`.

Voir `docs/DATA-MODEL-V2.md` § 10 F4. L'intitulé et l'organisme sont **repris du
certificat, jamais reconstitués** ; le domaine de certification est un
`code_reference` (jeu de référence, jamais une colonne métier — décision D2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class Certification:
    """Une certification ou qualification de l'entreprise."""

    intitule: str  # repris du certificat
    organisme: str  # repris du certificat
    domaine_code: str  # code_reference certification.domaine
    piece: str
    id: Optional[str] = None
    numero_certificat: Optional[str] = None
    date_obtention: Optional[date] = None
    date_echeance: Optional[date] = None  # échéance à surveiller
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "intitule": self.intitule,
            "organisme": self.organisme,
            "domaine_code": self.domaine_code,
            "numero_certificat": self.numero_certificat,
            "date_obtention": self.date_obtention,
            "date_echeance": self.date_echeance,
            "piece": self.piece,
        }
