"""Service — analyse d'un DCE. Squelette (phase 1).

Extraction des pièces exigées, des critères et de la date limite depuis un DCE
déposé par l'utilisateur. Aucun appel réseau, aucun appel à un modèle réel en phase 1.
"""

from __future__ import annotations

from typing import Any


def analyser_dce(chemin_fichier: str) -> dict[str, Any]:
    """Analyse un DCE : pièces exigées, critères, date limite.

    Chaque élément extrait doit pointer vers l'emplacement source dans le document.
    Squelette — aucun appel réseau, aucun modèle réel.
    """
    raise NotImplementedError
