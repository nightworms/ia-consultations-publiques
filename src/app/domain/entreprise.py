"""Famille 1 — Identité : `entreprise_version` et `representant_legal`.

Conforme à `docs/DATA-MODEL-V2.md` § 5.4 et § 5.5 (famille F1, § 10).

Rappels de la ligne rouge :

* `siret_siege`, `iban`, `bic`, `piece_rib` sont **confidentiels** (annexe A § A6) :
  ils sont chiffrés **par client** avant écriture — le domaine ne chiffre pas, il
  porte la structure et la sensibilité ;
* `effectif` (instantané daté, ici) n'est **pas** `effectif_moyen` (exercice
  comptable, F2) ni `effectif_metier.nombre` (F6) : trois grandeurs distinctes,
  aucune n'écrase l'autre (§ 5.4) ;
* `effectif` sans `date_effectif` est ininterprétable : le modèle le dit.

Exemple **FICTIF — DÉMONSTRATION** (jamais une donnée réelle) :

    EntrepriseVersion(raison_sociale="Étanchéité Exemple SARL",
                      siren="000000000", siret_siege="00000000000000", ...)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Montant, Sensibilite


@dataclass
class EntrepriseVersion:
    """Contenu d'identité de l'entreprise (F1) — rattaché à une `fiche_version`."""

    raison_sociale: str
    siren: str
    siret_siege: str
    forme_juridique_code: str
    adresse_siege: str
    id: Optional[str] = None
    capital_social: Optional[Montant] = None
    date_creation_entreprise: Optional[date] = None
    code_ape_naf: Optional[str] = None
    numero_tva_intracommunautaire: Optional[str] = None
    adresse_etablissement_principal: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    effectif: Optional[int] = None
    date_effectif: Optional[date] = None
    effectif_source_code: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    piece_rib: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    #: Champs déclarés confidentiels (annexe A § A6) — chiffrés par client.
    CHAMPS_CONFIDENTIELS = (
        "siret_siege",
        "numero_tva_intracommunautaire",
        "iban",
        "bic",
        "piece_rib",
    )

    def vers_colonnes(self) -> dict[str, object]:
        """Colonnes de la table `entreprise_version` (hors colonnes techniques)."""
        colonnes: dict[str, object] = {
            "raison_sociale": self.raison_sociale,
            "siren": self.siren,
            "siret_siege": self.siret_siege,
            "forme_juridique_code": self.forme_juridique_code,
            "adresse_siege": self.adresse_siege,
            "date_creation_entreprise": self.date_creation_entreprise,
            "code_ape_naf": self.code_ape_naf,
            "numero_tva_intracommunautaire": self.numero_tva_intracommunautaire,
            "adresse_etablissement_principal": self.adresse_etablissement_principal,
            "telephone": self.telephone,
            "email": self.email,
            "site_web": self.site_web,
            "effectif": self.effectif,
            "date_effectif": self.date_effectif,
            "effectif_source_code": self.effectif_source_code,
            "iban": self.iban,
            "bic": self.bic,
            "piece_rib": self.piece_rib,
        }
        if self.capital_social is not None:
            colonnes["capital_social_montant"] = self.capital_social.vers_chaine()
            colonnes["capital_social_devise"] = self.capital_social.devise
        return colonnes


@dataclass
class RepresentantLegal:
    """Représentant légal (F1) — **données personnelles**, confidentielles."""

    nom: str
    prenom: str
    fonction: str
    id: Optional[str] = None
    qualite_engagement: Optional[str] = None
    date_nomination: Optional[date] = None
    date_cessation: Optional[date] = None
    statut: str = "en_exercice"  # jeu rh.statut_mandat
    piece: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.CONFIDENTIEL

    CHAMPS_CONFIDENTIELS = ("nom", "prenom", "date_nomination", "piece")

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "nom": self.nom,
            "prenom": self.prenom,
            "fonction": self.fonction,
            "qualite_engagement": self.qualite_engagement,
            "date_nomination": self.date_nomination,
            "date_cessation": self.date_cessation,
            "statut": self.statut,
            "piece": self.piece,
        }
