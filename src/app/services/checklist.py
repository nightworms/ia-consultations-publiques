"""Service — checklist de conformité. Squelette (phase 1).

Croise les pièces exigées par un DCE avec les informations présentes dans la
bibliothèque. Signale les manques ; ne garantit jamais la conformité (ligne rouge).
"""

from __future__ import annotations

from typing import Any


def construire_checklist(entreprise_id: str, analyse_dce: dict[str, Any]) -> dict[str, Any]:
    """Produit la liste des pièces présentes, manquantes ou périmées.

    Résultat indicatif : l'absence de signalement ne vaut pas conformité.
    Squelette.
    """
    raise NotImplementedError
