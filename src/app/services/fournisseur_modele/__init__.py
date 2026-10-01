"""Couche d'abstraction du fournisseur de modèle (D8, annexe A § A7).

Point d'entrée unique : `creer_fournisseur()`. Le reste du produit ne connaît que
`FournisseurModele` et ne sait jamais quel fournisseur est derrière.

Sélection par la variable d'environnement `MODELE_FOURNISSEUR` :

* `factice` (défaut) — le fournisseur déterministe, sans réseau, **non-IQ réel** ;
* `ue` — le fournisseur réel France/UE, configuré par variables d'environnement.

Le défaut est `factice` : un produit livré ne doit jamais appeler un service externe
sans que quelqu'un l'ait explicitement demandé, et les tests ne doivent jamais
pouvoir sortir sur le réseau par accident.
"""

from __future__ import annotations

import os
from typing import Optional

from app.services.fournisseur_modele.base import (
    CATEGORIES_ELEMENTS,
    CATEGORIES_ATTENDUES,
    MENTION_NON_TROUVE,
    MENTION_NON_VERIFIE,
    ErreurFournisseurModele,
    FournisseurModele,
    PropositionElement,
    PropositionImport,
    ReponseModeleInvalide,
    ResultatAnalyse,
    source_presente,
    verifier_propositions,
    verifier_propositions_import,
)
from app.services.fournisseur_modele.fournisseur_factice import FournisseurFactice

NOM_VARIABLE_FOURNISSEUR = "MODELE_FOURNISSEUR"
FOURNISSEUR_DEFAUT = "factice"

__all__ = [
    "CATEGORIES_ELEMENTS",
    "CATEGORIES_ATTENDUES",
    "MENTION_NON_TROUVE",
    "MENTION_NON_VERIFIE",
    "ErreurFournisseurModele",
    "FournisseurFactice",
    "FournisseurModele",
    "PropositionElement",
    "PropositionImport",
    "ReponseModeleInvalide",
    "ResultatAnalyse",
    "source_presente",
    "verifier_propositions",
    "verifier_propositions_import",
    "creer_fournisseur",
    "fournisseurs_disponibles",
]


def fournisseurs_disponibles() -> tuple[str, ...]:
    """Noms de fournisseurs sélectionnables par variable d'environnement."""
    return (FOURNISSEUR_DEFAUT, "ue")


def creer_fournisseur(nom: Optional[str] = None) -> FournisseurModele:
    """Instancie le fournisseur demandé (par défaut : le factice).

    Le fournisseur réel n'est instancié qu'à la demande explicite : il exige alors
    ses variables d'environnement, sinon l'erreur est explicite.
    """
    choisi = (nom or os.environ.get(NOM_VARIABLE_FOURNISSEUR, FOURNISSEUR_DEFAUT)).strip()
    choisi = choisi.casefold() or FOURNISSEUR_DEFAUT

    if choisi == FOURNISSEUR_DEFAUT:
        return FournisseurFactice()
    if choisi in {"ue", "france", "mistral", "ovh"}:
        # Import paresseux : importer le module ne suffit pas à déclencher un appel,
        # mais garder `httpx` hors du chemin des tests évite tout malentendu.
        from app.services.fournisseur_modele.fournisseur_ue import FournisseurUe

        return FournisseurUe()
    raise ErreurFournisseurModele(
        f"Fournisseur de modèle inconnu : {choisi!r}. Valeurs admises : "
        f"{', '.join(fournisseurs_disponibles())}."
    )
