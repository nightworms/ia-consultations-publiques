"""Famille 3 — Assurances : `assurance`. Voir `docs/DATA-MODEL-V2.md` § 10 F3.

`date_echeance` est l'échéance **critique** de cette famille. `statut_validite` est
**calculé** à la lecture (§ 3.3) : aucun seuil, aucune durée n'est écrite ici.
`assurance` ne figure pas au registre des champs chiffrés (annexe A § A6) : la pièce
justificative reste une référence ordinaire, et c'est le **fichier** qui est chiffré
sur disque lorsque sa sensibilité est `confidentiel`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Montant, Sensibilite


@dataclass
class Assurance:
    """Contrat d'assurance et son attestation rattachée."""

    type_assurance: str  # code_reference assurance.type (contenu : L5)
    assureur: str
    date_debut: date
    date_echeance: date
    piece: str
    id: Optional[str] = None
    numero_contrat: Optional[str] = None
    montant_garantie: Optional[Montant] = None
    franchise: Optional[Montant] = None
    activites_couvertes: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        colonnes: dict[str, object] = {
            "type_assurance": self.type_assurance,
            "assureur": self.assureur,
            "numero_contrat": self.numero_contrat,
            "date_debut": self.date_debut,
            "date_echeance": self.date_echeance,
            "activites_couvertes": self.activites_couvertes,
            "piece": self.piece,
        }
        for nom, montant in (
            ("montant_garantie", self.montant_garantie),
            ("franchise", self.franchise),
        ):
            if montant is not None:
                colonnes[f"{nom}_montant"] = montant.vers_chaine()
                colonnes[f"{nom}_devise"] = montant.devise
        return colonnes
