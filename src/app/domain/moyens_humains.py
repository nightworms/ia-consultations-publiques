"""Famille 6 — Moyens humains. Voir ``docs/DATA-MODEL.md`` § 11.

Les CV sont des données personnelles : cadrage RGPD à faire avant mise en œuvre.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class EffectifMetier:
    """Effectif par métier."""

    id: str
    entreprise_id: str
    metier: str
    nombre: int
    commentaire: Optional[str] = None
    source_document_id: Optional[str] = None


@dataclass
class Organigramme:
    """Organigramme de l'entreprise."""

    id: str
    entreprise_id: str
    date_maj: Optional[date] = None
    description: Optional[str] = None
    piece_document_id: Optional[str] = None


@dataclass
class Cv:
    """CV d'un profil clé — donnée personnelle."""

    id: str
    entreprise_id: str
    nom: str
    prenom: str
    fonction: str
    cv_document_id: str
    diplomes: Optional[str] = None
    annees_experience: Optional[int] = None
    sensibilite: Sensibilite = Sensibilite.CONFIDENTIEL
    source_document_id: Optional[str] = None
