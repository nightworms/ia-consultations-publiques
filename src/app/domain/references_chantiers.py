"""Famille 5 — Références de chantiers : `reference_chantier`.

Voir `docs/DATA-MODEL-V2.md` § 10 F5. Le vocabulaire de la nature des travaux est un
jeu de référence (`nat*`) ; le texte libre est **conservé en plus**
(`nature_travaux_libelle`) pour ne rien perdre. `contact_reference` est une **donnée
personnelle** : elle est chiffrée par client (annexe A § A6), comme le montant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .commun import Montant, Sensibilite


@dataclass
class ReferenceChantier:
    """Une référence de chantier réalisée."""

    intitule_operation: str
    maitre_ouvrage: str
    id: Optional[str] = None
    nature_travaux_code: Optional[str] = None  # code_reference reference.nature_travaux
    nature_travaux_libelle: Optional[str] = None  # texte libre conservé en plus
    lieu_commune: Optional[str] = None
    lieu_departement: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    montant: Optional[Montant] = None
    duree_mois: Optional[int] = None
    surface_traitee: Optional[float] = None
    surface_unite: Optional[str] = None
    description: Optional[str] = None
    competences_appliquees: Optional[str] = None
    attestation_bonne_execution: Optional[str] = None
    photos: list[str] = field(default_factory=list)
    contact_reference: Optional[str] = None  # donnée personnelle
    sensibilite: Sensibilite = Sensibilite.INTERNE

    CHAMPS_CONFIDENTIELS = ("contact_reference", "montant_montant")

    def vers_colonnes(self) -> dict[str, object]:
        colonnes: dict[str, object] = {
            "intitule_operation": self.intitule_operation,
            "maitre_ouvrage": self.maitre_ouvrage,
            "nature_travaux_code": self.nature_travaux_code,
            "nature_travaux_libelle": self.nature_travaux_libelle,
            "lieu_commune": self.lieu_commune,
            "lieu_departement": self.lieu_departement,
            "date_debut": self.date_debut,
            "date_fin": self.date_fin,
            "duree_mois": self.duree_mois,
            "surface_traitee": self.surface_traitee,
            "surface_unite": self.surface_unite,
            "description": self.description,
            "competences_appliquees": self.competences_appliquees,
            "attestation_bonne_execution": self.attestation_bonne_execution,
            "contact_reference": self.contact_reference,
        }
        if self.montant is not None:
            colonnes["montant_montant"] = self.montant.vers_chaine()
            colonnes["montant_devise"] = self.montant.devise
        return colonnes
