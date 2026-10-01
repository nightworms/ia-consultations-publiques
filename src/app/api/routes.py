"""Routes HTTP — agrégateur des routeurs JSON de `/api/v1`.

Ce module ne contient **aucune logique** : il nomme les routeurs montés par
`app.main`, dans leur ordre d'enregistrement. C'est le point de rendez-vous des
lots qui ajoutent une surface d'API : **un seul écrivain à la fois** y pose sa
ligne (phase 4 : lot L3 puis lot L6 — `docs/PLAN-PHASE-4.md` § 2.E).

Les trois fonctions « squelettes » de la phase 1 sont conservées telles quelles :
elles décrivent la surface d'exposition attendue et ne sont appelées par aucun
routeur ni par aucun test — les retirer serait un changement sans bénéfice.
"""

from __future__ import annotations

from typing import Any

from app.api import (
    routes_analyse,
    routes_authentification,
    routes_bibliotheque,
    routes_checklist,
    routes_export,
    routes_import,
    routes_memoire,
    routes_provisionnement,
)

#: Routeurs JSON de l'API `/api/v1`, dans l'ordre historique, plus les ajouts de la
#: phase 4 (import guidé, mémoire technique, export téléchargeable). `app.main` les monte
#: dans cet ordre : pour ajouter une surface, on ajoute **une ligne** ici, jamais dans
#: `app.main`. `routes_export` n'a pas de préfixe : il sert le téléchargement sur le
#: chemin d'écran `/consultations/{id}/memoire/export` (lot L6).
ROUTEURS_API = (
    routes_authentification.router,
    routes_analyse.router,
    routes_bibliotheque.router,
    routes_provisionnement.router,
    routes_checklist.router,
    routes_import.router,
    routes_memoire.router,
    routes_export.router,
)


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
