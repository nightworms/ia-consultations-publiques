"""Document source — la brique de traçabilité. Voir `docs/DATA-MODEL-V2.md` § 9.1.

Toute valeur extraite pointe vers un document de cette entité (invariant I4 : le
document doit appartenir au même client). Deux points tenus ici :

* `chemin_stockage` est **préfixé par le client** et vit **hors dépôt** (§ 4.3) ;
* `type_document` est un `code_reference` d'un **jeu de référence unique**
  (`document.type_document`, constat C4) — jamais une énumération en dur dans ce
  module : le contenu de la liste appartient à `docs/NOMENCLATURE-REFERENCE.md`.

La nature `dce` et le rattachement à une consultation (annexe B § B1) appartiennent
au lot L3 : ils ne sont pas décidés ici.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .commun import Sensibilite


@dataclass
class Document:
    """Document source rattaché à une entreprise et à une version de fiche."""

    type_document: str  # code_reference document.type_document
    libelle: str
    chemin_stockage: str  # hors dépôt, préfixé par le client
    deposant: str  # code_reference document.deposant : entreprise | service
    id: Optional[str] = None
    emetteur: Optional[str] = None
    date_emission: Optional[date] = None
    date_validite_debut: Optional[date] = None
    date_validite_fin: Optional[date] = None  # échéance à surveiller
    reference_document: Optional[str] = None
    empreinte_sha256: Optional[str] = None
    taille_octets: Optional[int] = None
    mime_type: Optional[str] = None
    stockage_client_seulement: bool = False
    sensibilite: Sensibilite = Sensibilite.INTERNE

    def vers_colonnes(self) -> dict[str, object]:
        return {
            "type_document": self.type_document,
            "libelle": self.libelle,
            "emetteur": self.emetteur,
            "date_emission": self.date_emission,
            "date_validite_debut": self.date_validite_debut,
            "date_validite_fin": self.date_validite_fin,
            "reference_document": self.reference_document,
            "chemin_stockage": self.chemin_stockage,
            "deposant": self.deposant,
            "empreinte_sha256": self.empreinte_sha256,
            "taille_octets": self.taille_octets,
            "mime_type": self.mime_type,
            "stockage_client_seulement": 1 if self.stockage_client_seulement else 0,
        }
