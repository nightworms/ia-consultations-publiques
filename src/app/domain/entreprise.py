"""Famille 1 — Identité. Voir ``docs/DATA-MODEL.md`` § 3.1 et § 6.

Structure seule. EXEMPLE FICTIF à ne pas confondre avec une donnée réelle :

    Entreprise(id="00000000-0000-0000-0000-000000000000",
               raison_sociale="Étanchéité Exemple SARL",
               siren="000000000", siret_siege="00000000000000", ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class RepresentantLegal:
    """Représentant légal en exercice (KBIS / statuts / PV de nomination)."""

    id: str
    nom: str
    prenom: str
    fonction: str
    date_nomination: Optional[date] = None
    piece_document_id: Optional[str] = None


@dataclass
class Entreprise:
    """Identité de l'entreprise propriétaire de la bibliothèque."""

    id: str
    raison_sociale: str
    siren: str
    siret_siege: str  # donnée d'identification
    forme_juridique: str
    adresse_siege: str
    sensibilite: Sensibilite = Sensibilite.INTERNE
    capital_social: Optional[str] = None
    date_creation_entreprise: Optional[date] = None
    code_ape_naf: Optional[str] = None
    numero_tva_intracommunautaire: Optional[str] = None
    adresse_etablissement_principal: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    representants_legaux: list[RepresentantLegal] = field(default_factory=list)
