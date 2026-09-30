"""Registre des champs déclarés sensibles — entrée du chiffrement applicatif.

Ce module porte **la liste, et rien d'autre** : il dit *quoi* protéger. Le
*comment* appartient à `app/securite/chiffrement.py` (livré par le lot L1) : le
chiffrement est appliqué ici, il n'est pas réécrit (annexe A § A6).

Source de la liste : `docs/DATA-MODEL-V2.md` § 13.2 (registre des champs déclarés
`confidentiel`) et annexe A § A6 du plan de phase 3.

Rappels tenus par ce module :

* le chiffrement est **par client** (HKDF, sel = `client_id`) — jamais global ;
* aucun secret ne figure ici : ce module ne contient que des **noms de colonnes** ;
* le registre est **exhaustif à ce jour** et doit être tenu à jour avec le modèle.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Champs chiffrés, par entité de contenu (nom logique de la table).
REGISTRE_CHAMPS_CHIFFRES: dict[str, frozenset[str]] = {
    # F1 — Identité (§ 5.4) : coordonnées bancaires et identification.
    "entreprise_version": frozenset(
        {"iban", "bic", "piece_rib", "siret_siege", "numero_tva_intracommunautaire"}
    ),
    # F1 — Représentant légal (§ 5.5) : données personnelles.
    "representant_legal": frozenset({"nom", "prenom", "date_nomination", "piece"}),
    # F2 — Exercices comptables : « tous les montant, piece » (A6).
    "exercice_comptable": frozenset(
        {
            "chiffre_affaires_montant",
            "resultat_net_montant",
            "capitaux_propres_montant",
            "total_bilan_montant",
            "piece",
        }
    ),
    # F2 — Attestations : pièces fiscales et sociales.
    "attestation": frozenset({"piece", "montant_engage_montant"}),
    # F5 — Références de chantiers : données personnelles, affaires.
    "reference_chantier": frozenset({"contact_reference", "montant_montant"}),
    # F6 — CV : données personnelles.
    "cv": frozenset({"nom", "prenom", "diplomes", "cv_piece"}),
}


@dataclass(frozen=True)
class ChampsSensibles:
    """Vue en lecture du registre pour une entité."""

    entite: str

    @property
    def champs(self) -> frozenset[str]:
        return REGISTRE_CHAMPS_CHIFFRES.get(self.entite, frozenset())

    def est_chiffre(self, champ: str) -> bool:
        return champ in self.champs


def champs_chiffres(entite: str) -> frozenset[str]:
    """Champs chiffrés d'une entité (ensemble vide si l'entité n'en a aucun)."""
    return REGISTRE_CHAMPS_CHIFFRES.get(entite, frozenset())


def entites_concernees() -> tuple[str, ...]:
    """Entités portant au moins un champ chiffré, dans l'ordre du registre."""
    return tuple(REGISTRE_CHAMPS_CHIFFRES)
