"""Squelettes de dépôts — un par famille du modèle de données.

Aucune connexion à une base, aucune requête écrite. Ces classes montrent la forme
attendue ; le corps sera rempli en phase 2, derrière ``storage``, jamais ailleurs.
"""

from __future__ import annotations

from typing import Any


class EntrepriseRepository:
    def add(self, entreprise: Any) -> str:
        raise NotImplementedError

    def get(self, entreprise_id: str) -> Any:
        raise NotImplementedError


class DocumentRepository:
    def add(self, document: Any) -> str:
        raise NotImplementedError

    def get(self, document_id: str) -> Any:
        raise NotImplementedError

    def list_for_entreprise(self, entreprise_id: str) -> list[Any]:
        raise NotImplementedError


class FicheVersionRepository:
    def create_version(self, entreprise_id: str, parent_id: str | None) -> str:
        raise NotImplementedError

    def publier(self, fiche_version_id: str) -> None:
        raise NotImplementedError

    def list_for_entreprise(self, entreprise_id: str) -> list[Any]:
        raise NotImplementedError


class AssuranceRepository:
    """Dépôt des assurances — famille 3."""

    def list_echeances(self, entreprise_id: str) -> list[Any]:
        """Retourne les assurances par date d'échéance. Squelette."""
        raise NotImplementedError


class CertificationRepository:
    """Dépôt des certifications — famille 4."""

    def list_echeances(self, entreprise_id: str) -> list[Any]:
        raise NotImplementedError


class ReferenceChantierRepository:
    """Dépôt des références de chantiers — famille 5."""

    def list_for_entreprise(self, entreprise_id: str) -> list[Any]:
        raise NotImplementedError
