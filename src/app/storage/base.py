"""Interfaces de persistance (protocoles). Aucune implémentation réelle.

Cible proposée : SQLite via migrations versionnées (``src/migrations/``). Voir
``src/README.md`` — proposition à valider par Anthony.
"""

from __future__ import annotations

from typing import Any, Protocol


class UnitOfWork(Protocol):
    """Frontière transactionnelle. Squelette : rien n'est implémenté en phase 1."""

    def begin(self) -> None:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError


class Repository(Protocol):
    """Dépôt générique d'une entité du domaine. Squelette."""

    def add(self, entity: Any) -> str:
        raise NotImplementedError

    def get(self, entity_id: str) -> Any:
        raise NotImplementedError

    def list_for_entreprise(self, entreprise_id: str) -> list[Any]:
        raise NotImplementedError
