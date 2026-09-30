"""Famille 6 — Moyens humains : `effectif_metier`, `organigramme`, `cv`.

Voir `docs/DATA-MODEL-V2.md` § 10 F6. Les CV et l'organigramme portent des **données
personnelles** : cadrage RGPD hors modèle (point ouvert § 15 point 6) ; en attendant,
le registre sensible (annexe A § A6) impose le chiffrement par client de `nom`,
`prenom`, `diplomes` et `cv_piece`.

`annees_experience` est **saisi ou lu**, jamais déduit d'une date par l'outil.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class EffectifMetier:
    """Effectif **par métier** — troisième grandeur d'effectif, distincte des deux autres."""

    metier_code: str  # code_reference metier.* ou rh.metier
    nombre: int
    id: Optional[str] = None
    metier_libelle: Optional[str] = None  # libellé tel que saisi
    commentaire: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "metier_code": self.metier_code,
            "metier_libelle": self.metier_libelle,
            "nombre": self.nombre,
            "commentaire": self.commentaire,
        }


@dataclass
class Organigramme:
    """Organigramme de l'entreprise (pièce + description + date de mise à jour)."""

    id: Optional[str] = None
    piece: Optional[str] = None
    description: Optional[str] = None
    date_maj: Optional[date] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "piece": self.piece,
            "description": self.description,
            "date_maj": self.date_maj,
        }


@dataclass
class Cv:
    """CV d'un profil clé — **données personnelles**, confidentielles."""

    nom: str
    prenom: str
    fonction: str
    cv_piece: str
    id: Optional[str] = None
    diplomes: Optional[str] = None
    annees_experience: Optional[int] = None
    sensibilite: Sensibilite = Sensibilite.CONFIDENTIEL

    CHAMPS_CONFIDENTIELS = ("nom", "prenom", "diplomes", "cv_piece")

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "nom": self.nom,
            "prenom": self.prenom,
            "fonction": self.fonction,
            "diplomes": self.diplomes,
            "annees_experience": self.annees_experience,
            "cv_piece": self.cv_piece,
        }
