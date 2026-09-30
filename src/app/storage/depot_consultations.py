"""Dépôt de **lecture** de `consultation` — listing pour l'écran de dépôt (L5).

Pourquoi ce module existe
-------------------------

L'écran HTML `/consultations` doit pouvoir rappeler les consultations déjà
enregistrées par le client : sinon, une consultation déposée n'est atteignable
que tant qu'on garde son URL sous les yeux, et l'écran de dépôt est un
cul-de-sac. Aucune route de l'annexe C (contrat gelé) ne liste les
`consultation`, et le web ne contient aucun SQL (annexe A § A3 : « aucune couche
n'accède à la persistance en contournant `storage` »). D'où ce petit dépôt
**de lecture seule**, dont le SQL vit ici, comme le veut la règle R9.

Il ne fait qu'une chose : lire les `consultation` **du client de la session**.
Aucune écriture, aucune jointure avec une autre table, aucune donnée d'un autre
client : le filtre `client_id` est imposé par `Connexion` (annexe A § A1).
"""

from __future__ import annotations

from typing import Any

from app.storage.connexion import Connexion, ContexteClient

#: Colonnes exposées à l'écran — volontairement restreintes.
COLONNES_LISIBLES = (
    "id",
    "libelle",
    "reference_consultation",
    "maitre_ouvrage_declare",
    "statut",
    "date_creation",
    "date_modification",
)


class DepotConsultation:
    """Lecture des consultations d'un client (listing d'écran)."""

    def __init__(self, connexion: Connexion) -> None:
        self._connexion = connexion

    def lister_pour_client(
        self, contexte: ContexteClient, *, limite: int = 100
    ) -> list[dict[str, Any]]:
        """Consultations du client de la session, les plus récentes d'abord."""
        colonnes = ", ".join(COLONNES_LISIBLES)
        return self._connexion.executer(
            contexte,
            f"SELECT {colonnes} FROM consultation "
            "WHERE client_id = %(client_id)s AND statut_enregistrement = 'actif' "
            "ORDER BY date_creation DESC, id LIMIT %(limite)s",
            {"limite": int(limite)},
        )
