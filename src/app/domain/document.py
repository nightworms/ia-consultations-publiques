"""Document source — brique de traçabilité. Voir ``docs/DATA-MODEL.md`` § 3.2.

Tout élément de contenu pointe, directement ou indirectement, vers un document.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from .commun import Sensibilite


class TypeDocument(str, Enum):
    """Liste indicative — à compléter (voir points ouverts du modèle)."""

    KBIS = "kbis"
    AVIS_SIRENE = "avis_sirene"
    BILAN = "bilan"
    LIASSE_FISCALE = "liasse_fiscale"
    ATTESTATION_FISCALE = "attestation_fiscale"
    ATTESTATION_SOCIALE = "attestation_sociale"
    ATTESTATION_ASSURANCE = "attestation_assurance"
    CERTIFICAT = "certificat"
    FICHE_TECHNIQUE = "fiche_technique"
    AVIS_TECHNIQUE = "avis_technique"
    CV = "cv"
    ATTESTATION_BONNE_EXECUTION = "attestation_bonne_execution"
    PHOTO = "photo"
    AUTRE = "autre"


@dataclass
class Document:
    """Document source rattaché à une entreprise."""

    id: str
    entreprise_id: str
    type_document: TypeDocument
    libelle: str
    chemin_stockage: str  # hors dépôt : voir .gitignore (data/)
    emetteur: Optional[str] = None
    date_emission: Optional[date] = None
    date_validite_debut: Optional[date] = None
    date_validite_fin: Optional[date] = None  # échéance à surveiller
    reference_document: Optional[str] = None
    empreinte_sha256: Optional[str] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE
