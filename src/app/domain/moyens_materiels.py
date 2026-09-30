"""Famille 7 — Moyens matériels : `moyen_materiel`.

Voir `docs/DATA-MODEL-V2.md` § 10 F7. La catégorie est un `code_reference`
(`moyen.categorie`, contenu : L5) — **aucune énumération métier n'est écrite ici** :
le métier est une donnée (décision D2), jamais une colonne.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .commun import Sensibilite


@dataclass
class MoyenMateriel:
    """Un moyen matériel de l'entreprise."""

    categorie_code: str  # code_reference moyen.categorie
    designation: str
    quantite: int
    id: Optional[str] = None
    marque_modele: Optional[str] = None
    annee: Optional[int] = None
    propriete: Optional[str] = None  # code_reference moyen.propriete : propre | location
    disponibilite: Optional[str] = None
    justificatif: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "categorie_code": self.categorie_code,
            "designation": self.designation,
            "quantite": self.quantite,
            "marque_modele": self.marque_modele,
            "annee": self.annee,
            "propriete": self.propriete,
            "disponibilite": self.disponibilite,
            "justificatif": self.justificatif,
        }
