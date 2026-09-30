"""Service — bibliothèque d'entreprise. Squelette (phase 1).

Saisie et lecture des informations de l'entreprise, structurées selon
``docs/DATA-MODEL.md``. Aucune logique complète ici.
"""

from __future__ import annotations

from typing import Any


def creer_fiche_entreprise(donnees: dict[str, Any]) -> str:
    """Crée une fiche entreprise (version brouillon n° 1). Squelette."""
    raise NotImplementedError


def ajouter_information(
    entreprise_id: str,
    famille: str,
    donnees: dict[str, Any],
) -> str:
    """Ajoute une information à une famille (assurance, référence, etc.).

    Doit refuser toute information ``origine=document_extrait`` sans
    ``source_document_id`` (traçabilité, ``docs/DATA-MODEL.md`` § 4). Squelette.
    """
    raise NotImplementedError


def publier_version(entreprise_id: str) -> str:
    """Fige la fiche courante en une version publiée immuable.

    Voir ``docs/DATA-MODEL.md`` § 5. Squelette.
    """
    raise NotImplementedError


def lister_echeances(entreprise_id: str) -> list[Any]:
    """Liste les éléments à échéance (assurances, certifications, attestations).

    Squelette. Le seuil « échéance proche » n'est pas fixé (point ouvert).
    """
    raise NotImplementedError
