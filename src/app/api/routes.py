"""Routes HTTP — squelettes. Aucun framework importé en phase 1.

La cible est FastAPI ; ces fonctions montrent la surface d'exposition attendue du MVP.
Elles délèguent aux services et ne contiennent aucune logique.
"""

from __future__ import annotations

from typing import Any


def lister_bibliotheque(entreprise_id: str) -> dict[str, Any]:
    """GET — bibliothèque d'entreprise. Squelette."""
    raise NotImplementedError


def creer_entreprise(payload: dict[str, Any]) -> dict[str, Any]:
    """POST — créer une fiche entreprise. Squelette."""
    raise NotImplementedError


def analyser_dce(chemin_fichier: str) -> dict[str, Any]:
    """POST — analyse d'un DCE déposé. Squelette."""
    raise NotImplementedError


def get_checklist(entreprise_id: str, consultation_id: str) -> dict[str, Any]:
    """GET — checklist de conformité. Squelette."""
    raise NotImplementedError
