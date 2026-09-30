"""Famille 2 — Capacités financières : `exercice_comptable`, `attestation`,
`capacite_production`. Voir `docs/DATA-MODEL-V2.md` § 10 F2.

Contraintes tenues ici :

* **aucun montant sans devise** (`Montant`) ;
* **aucune durée de validité en dur** : `date_validite_fin` est lue sur le document,
  et à défaut la valeur reste `non_renseigne` (`statut_validite` est *calculé*) ;
* `effectif_moyen` (ici) n'est **pas** `effectif` (F1) : moyenne d'un exercice clos
  contre instantané daté (§ 5.4) ;
* les montants et les pièces sont **confidentiels** (annexe A § A6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Montant, Sensibilite


@dataclass
class ExerciceComptable:
    """Un exercice comptable (au moins les trois derniers)."""

    annee_exercice: int
    chiffre_affaires: Montant
    id: Optional[str] = None
    date_cloture: Optional[date] = None
    resultat_net: Optional[Montant] = None
    capitaux_propres: Optional[Montant] = None
    total_bilan: Optional[Montant] = None
    effectif_moyen: Optional[int] = None
    piece: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.CONFIDENTIEL

    CHAMPS_CONFIDENTIELS = (
        "chiffre_affaires_montant",
        "resultat_net_montant",
        "capitaux_propres_montant",
        "total_bilan_montant",
        "piece",
    )

    def vers_colonnes(self) -> dict[str, object]:
        colonnes: dict[str, object] = {
            "annee_exercice": self.annee_exercice,
            "date_cloture": self.date_cloture,
            "effectif_moyen": self.effectif_moyen,
            "piece": self.piece,
            "chiffre_affaires_montant": self.chiffre_affaires.vers_chaine(),
            "chiffre_affaires_devise": self.chiffre_affaires.devise,
        }
        for nom, montant in (
            ("resultat_net", self.resultat_net),
            ("capitaux_propres", self.capitaux_propres),
            ("total_bilan", self.total_bilan),
        ):
            if montant is not None:
                colonnes[f"{nom}_montant"] = montant.vers_chaine()
                colonnes[f"{nom}_devise"] = montant.devise
        return colonnes


@dataclass
class Attestation:
    """Attestation justificative à durée de validité (fiscale, sociale…)."""

    type_attestation: str  # code_reference attestation.type (contenu : L5 / source)
    emetteur: str
    date_emission: date
    piece: str
    id: Optional[str] = None
    date_validite_fin: Optional[date] = None  # échéance à surveiller, jamais déduite
    montant_engage: Optional[Montant] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    CHAMPS_CONFIDENTIELS = ("piece", "montant_engage_montant")

    def vers_colonnes(self) -> dict[str, object]:
        colonnes: dict[str, object] = {
            "type_attestation": self.type_attestation,
            "emetteur": self.emetteur,
            "date_emission": self.date_emission,
            "date_validite_fin": self.date_validite_fin,
            "piece": self.piece,
        }
        if self.montant_engage is not None:
            colonnes["montant_engage_montant"] = self.montant_engage.vers_chaine()
            colonnes["montant_engage_devise"] = self.montant_engage.devise
        return colonnes


@dataclass
class CapaciteProduction:
    """Capacité de production déclarée (texte + unité + valeur)."""

    description: str
    id: Optional[str] = None
    unite: Optional[str] = None
    valeur: Optional[float] = None
    commentaire: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "description": self.description,
            "unite": self.unite,
            "valeur": self.valeur,
            "commentaire": self.commentaire,
        }
