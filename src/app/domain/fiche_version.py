"""Versionnement, états et relecture humaine — `docs/DATA-MODEL-V2.md` § 6.

Ce module porte :

* `fiche_version` — l'**axe de versionnement** (§ 6.1). Elle porte `client_id` et
  `entreprise_id` mais **pas** `fiche_version_id` : elle **est** l'axe (constat C10) ;
* les **7 états** de `fiche.statut_version` (§ 6.2), avec leur libellé d'interface ;
* les **4 états** de `fiche.statut_famille` (§ 6.3) ;
* `validation_relecture` — le **verrou de relecture humaine** (§ 6.4) : nom du
  relecteur, horodatage posé automatiquement, attestation cochée, empreinte du
  contenu validé, révocation.

**Ligne rouge traduite ici.** Aucun chemin de ce module ne pose `validee` sans une
action humaine nommée et horodatée, et l'IA ne signe rien. Le libellé de l'état est
« relue et validée par humain » — jamais « conforme » ni « certifiée ».
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .commun import Sensibilite

# --------------------------------------------------------------------------- #
# États — § 6.2 (7 valeurs) et § 6.3 (4 valeurs)
# --------------------------------------------------------------------------- #


class StatutVersion(str, Enum):
    """Les 7 états de `fiche.statut_version` (§ 6.2)."""

    VIERGE = "vierge"
    EN_SAISIE = "en_saisie"
    SOCLE_COMPLET = "socle_complet"
    EN_RELECTURE = "en_relecture"
    VALIDEE = "validee"
    VALIDEE_PUIS_MODIFIEE = "validee_puis_modifiee"
    ARCHIVEE = "archivee"


#: Libellés affichés par l'interface (E0, `docs/UI-SAISIE.md`).
LIBELLES_STATUT_VERSION: dict[str, str] = {
    StatutVersion.VIERGE.value: "Vierge",
    StatutVersion.EN_SAISIE.value: "En cours de saisie",
    StatutVersion.SOCLE_COMPLET.value: "Socle complet (non relue)",
    StatutVersion.EN_RELECTURE.value: "En relecture",
    StatutVersion.VALIDEE.value: "Relue et validée par humain",
    StatutVersion.VALIDEE_PUIS_MODIFIEE.value: "Validée puis modifiée (à relire)",
    StatutVersion.ARCHIVEE.value: "Archivée",
}

#: États dans lesquels une fiche est encore modifiable « en place » (§ 6.5 point 3).
STATUTS_MODIFIABLES: frozenset[str] = frozenset(
    {
        StatutVersion.VIERGE.value,
        StatutVersion.EN_SAISIE.value,
        StatutVersion.SOCLE_COMPLET.value,
        StatutVersion.EN_RELECTURE.value,
        StatutVersion.VALIDEE_PUIS_MODIFIEE.value,
    }
)


class StatutFamille(str, Enum):
    """Les 4 états de `fiche.statut_famille` (§ 6.3)."""

    NON_COMMENCEE = "non_commencee"
    DEMARREE = "demarree"
    SOCLE_COMPLET = "socle_complet"
    VALIDEE = "validee"


class CibleValidation(str, Enum):
    """`validation.cible` (§ 6.4) : la validation est représentée à deux niveaux."""

    FICHE = "fiche"
    FAMILLE = "famille"


class StatutValidation(str, Enum):
    """`validation.statut` (§ 6.4)."""

    VALIDEE = "validee"
    REVOQUEE = "revoquee"


# --------------------------------------------------------------------------- #
# Entités
# --------------------------------------------------------------------------- #


@dataclass
class FicheVersion:
    """Une version de fiche. Une version `validee` est **immuable** (§ 6.1 règle 1)."""

    numero_version: int
    statut: str = StatutVersion.VIERGE.value
    id: Optional[str] = None
    client_id: Optional[str] = None
    entreprise_id: Optional[str] = None
    version_parente_id: Optional[str] = None
    date_creation: Optional[datetime] = None
    date_derniere_ecriture: Optional[datetime] = None
    commentaire: Optional[str] = None

    def est_immuable(self) -> bool:
        """Vrai si la version est figée : la correction passe par une nouvelle version."""
        return self.statut == StatutVersion.ARCHIVEE.value or self.statut == StatutVersion.VALIDEE.value


@dataclass
class FicheFamille:
    """L'avancement par famille (§ 6.3) — une ligne par (fiche_version, famille)."""

    famille_code: str
    statut: str = StatutFamille.NON_COMMENCEE.value
    id: Optional[str] = None
    client_id: Optional[str] = None
    entreprise_id: Optional[str] = None
    fiche_version_id: Optional[str] = None
    date_maj: Optional[datetime] = None
    sensibilite: Sensibilite = Sensibilite.INTERNE
    statut_enregistrement: str = "actif"


@dataclass
class ValidationRelecture:
    """Le **verrou de relecture humaine** (§ 6.4).

    `relecteur_nom` est **obligatoire en toutes circonstances** : c'est la trace
    exigée par la ligne rouge. `date_validation` est posée **automatiquement** au
    moment de l'action humaine, jamais saisie à la main. `attestation_cochee` est la
    case « j'ai relu et corrigé les informations ci-dessus ».
    """

    relecteur_nom: str
    attestation_cochee: bool
    empreinte_contenu: str
    empreinte_algorithme: str
    cible_type: str = CibleValidation.FICHE.value
    famille_code: Optional[str] = None
    id: Optional[str] = None
    client_id: Optional[str] = None
    entreprise_id: Optional[str] = None
    fiche_version_id: Optional[str] = None
    relecteur_utilisateur_id: Optional[str] = None
    date_validation: Optional[datetime] = None
    statut: str = StatutValidation.VALIDEE.value
    date_revocation: Optional[datetime] = None
    motif_revocation: Optional[str] = None
    commentaire: Optional[str] = None

    def __post_init__(self) -> None:
        if not (self.relecteur_nom or "").strip():
            raise ValueError(
                "`relecteur_nom` est obligatoire : aucune validation sans action "
                "humaine nommée (§ 6.4, ligne rouge)."
            )
        if not self.attestation_cochee:
            raise ValueError(
                "`attestation_cochee` doit être vraie : la relecture humaine est un "
                "verrou qui ne se court-circuite pas (§ 6.4)."
            )
        if self.cible_type not in {c.value for c in CibleValidation}:
            raise ValueError(f"`cible_type` invalide : {self.cible_type!r}")
        if self.cible_type == CibleValidation.FAMILLE.value and not self.famille_code:
            raise ValueError(
                "`famille_code` est obligatoire quand `cible_type = famille` (§ 6.4)."
            )
        if not self.empreinte_contenu or not self.empreinte_algorithme:
            raise ValueError(
                "`empreinte_contenu` et `empreinte_algorithme` sont obligatoires : "
                "sans empreinte, la validation n'est pas contrôlable (invariant I6)."
            )

    def couvre(self, famille_code: Optional[str]) -> bool:
        """Vrai si cette validation couvre une écriture sur `famille_code`.

        Une validation de **fiche** couvre toutes les familles ; une validation de
        famille ne couvre que la sienne (§ 6.4).
        """
        if self.statut != StatutValidation.VALIDEE.value:
            return False
        if self.cible_type == CibleValidation.FICHE.value:
            return True
        return self.famille_code == famille_code
