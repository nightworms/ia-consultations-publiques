"""Famille 9 — Mémoire technique type : `chapitre_memoire`.

Voir `docs/DATA-MODEL-V2.md` § 10 F9. **Périmètre strict** : ce module **stocke** un
mémoire technique type réutilisable. Il ne décrit et ne réalise **aucune rédaction
automatique** (hors périmètre de la phase 3), et **la signature n'est jamais
automatisée** : un chapitre réutilisé dans un dossier exige la relecture humaine
(§ 6.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class ChapitreMemoire:
    """Un chapitre réutilisable du mémoire technique type."""

    titre: str
    ordre: int
    id: Optional[str] = None
    contenu_texte: Optional[str] = None
    statut: str = "brouillon"  # code_reference memoire.statut_chapitre
    date_redaction: Optional[date] = None
    references_liees: list[str] = field(default_factory=list)
    documents_associes: list[str] = field(default_factory=list)
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "titre": self.titre,
            "ordre": self.ordre,
            "contenu_texte": self.contenu_texte,
            "statut": self.statut,
            "date_redaction": self.date_redaction,
        }
