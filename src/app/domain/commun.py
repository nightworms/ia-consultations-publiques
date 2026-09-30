"""Types transverses du modèle de domaine.

Définit les énumérations et le motif de traçabilité communs à toutes les familles
(voir ``docs/DATA-MODEL.md`` § 2 et § 4). Aucune logique métier.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrigineValeur(str, Enum):
    """D'où vient une valeur. Jamais « généré par l'IA » : voir la ligne rouge."""

    DOCUMENT_EXTRAIT = "document_extrait"
    SAISIE_ENTREPRISE = "saisie_entreprise"


class EtatVerification(str, Enum):
    """Niveau de confiance d'une valeur."""

    VERIFIE = "verifie"
    DECLARE_NON_VERIFIE = "declare_non_verifie"
    A_VERIFIER = "a_verifier"


class StatutValidite(str, Enum):
    """Validité calculée d'un élément à échéance (assurance, certification...)."""

    VALIDE = "valide"
    ECHEANCE_PROCHE = "echeance_proche"
    EXPIRE = "expire"
    NON_RENSEIGNE = "non_renseigne"


class Sensibilite(str, Enum):
    """Sensibilité d'une donnée, pour le chiffrement et le cloisonnement."""

    PUBLIQUE = "publique"
    INTERNE = "interne"
    CONFIDENTIEL = "confidentiel"


@dataclass
class Montant:
    """Un montant porte toujours sa devise (code ISO 4217, ex. « EUR »)."""

    valeur: Decimal
    devise: str


@dataclass
class Traceabilite:
    """Lien d'un enregistrement vers son document source.

    Règle (``docs/DATA-MODEL.md`` § 4) : si ``origine`` vaut ``DOCUMENT_EXTRAIT``,
    ``source_document_id`` doit être renseigné. Sinon, la valeur reste au mieux
    ``DECLARE_NON_VERIFIE``.
    """

    origine: OrigineValeur
    source_document_id: Optional[str] = None
    source_emplacement: Optional[str] = None
    source_date_extraction: Optional[date] = None
    source_commentaire: Optional[str] = None
