"""Famille 8 — Fiches techniques produits : `produit`.

Voir `docs/DATA-MODEL-V2.md` § 10 F8. **Ligne rouge** : un avis technique ou un
certificat est stocké **tel quel** ; la référence produit est recopiée du document
fournisseur, jamais reconstituée. Le modèle ne présume ni la validité ni la portée
d'un document fournisseur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class Produit:
    """Un produit de fournisseur et ses documents associés."""

    fournisseur: str
    reference_produit: str  # référence exacte du fournisseur, jamais reconstituée
    designation: str
    id: Optional[str] = None
    famille_code: Optional[str] = None  # code_reference produit.famille
    domaine_application: Optional[str] = None
    fiche_technique: Optional[str] = None
    certificats: list[str] = field(default_factory=list)
    avis_technique: Optional[str] = None
    date_validite_document: Optional[date] = None  # échéance à surveiller
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "fournisseur": self.fournisseur,
            "reference_produit": self.reference_produit,
            "designation": self.designation,
            "famille_code": self.famille_code,
            "domaine_application": self.domaine_application,
            "fiche_technique": self.fiche_technique,
            "avis_technique": self.avis_technique,
            "date_validite_document": self.date_validite_document,
        }
