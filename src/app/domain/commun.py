"""Types transverses du modèle de domaine — conformes à `docs/DATA-MODEL-V2.md`.

Ce module ne dépend **que** de la bibliothèque standard (annexe A § A3). Il porte :

* les **énumérations fermées** du modèle : origine, confiance, sensibilité, validité ;
* `Montant` (valeur + devise ISO 4217 obligatoire) ;
* la **traçabilité** : au niveau de la valeur (`TraceabiliteValeur`, § 7.2) et le
  **résumé** porté par l'enregistrement (`Traceabilite` = colonnes de synthèse, § 7.4) ;
* le **calcul** de `statut_validite` (§ 3.3) : jamais stocké, et **aucun seuil n'est
  écrit en dur** — la fenêtre d'alerte est un réglage passé en paramètre.

Ligne rouge (annexe A § A9) : `origine` ne prend jamais la valeur « générée par
l'IA ». Il n'existe aucune énumération pour cela, et aucune fonction de ce module ne
peut en produire.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional

# --------------------------------------------------------------------------- #
# Énumérations fermées (jeux de référence définis par le modèle)
# --------------------------------------------------------------------------- #


class Origine(str, Enum):
    """D'où vient une valeur. § 7.5 — jamais « généré par l'IA »."""

    DOCUMENT_EXTRAIT = "document_extrait"
    SAISIE_ENTREPRISE = "saisie_entreprise"


class OrigineSynthese(str, Enum):
    """`origine` d'un enregistrement : les deux origines, plus `mixte` (§ 7.4)."""

    DOCUMENT_EXTRAIT = "document_extrait"
    SAISIE_ENTREPRISE = "saisie_entreprise"
    MIXTE = "mixte"


class Confiance(str, Enum):
    """Niveau de confiance d'une valeur (§ 7.2)."""

    VERIFIE = "verifie"
    DECLARE_NON_VERIFIE = "declare_non_verifie"
    A_VERIFIER = "a_verifier"


#: Ordre de faiblesse des confiances, du plus faible au plus fort : la plus faible
#: gagne pour un enregistrement entier (§ 7.4, « règle du maillon faible »).
ORDRE_CONFIANCE: tuple[str, ...] = (
    Confiance.A_VERIFIER.value,
    Confiance.DECLARE_NON_VERIFIE.value,
    Confiance.VERIFIE.value,
)


def confiance_la_plus_faible(confiances: list[str]) -> str:
    """Renvoie la plus faible des confiances (§ 7.4)."""
    if not confiances:
        return Confiance.A_VERIFIER.value
    inconnues = [c for c in confiances if c not in ORDRE_CONFIANCE]
    if inconnues:
        raise ValueError(f"Confiance inconnue : {inconnues!r}")
    return min(confiances, key=ORDRE_CONFIANCE.index)


class Sensibilite(str, Enum):
    """Sensibilité d'une donnée (§ 3.2)."""

    PUBLIQUE = "publique"
    INTERNE = "interne"
    CONFIDENTIEL = "confidentiel"


class StatutEnregistrement(str, Enum):
    """Un enregistrement n'est jamais supprimé en dur : il est archivé (§ 3.2)."""

    ACTIF = "actif"
    ARCHIVE = "archive"


class StatutValidite(str, Enum):
    """Validité **calculée** à la lecture (§ 3.3) — jamais stockée."""

    VALIDE = "valide"
    ECHEANCE_PROCHE = "echeance_proche"
    EXPIRE = "expire"
    NON_RENSEIGNE = "non_renseigne"


class ErreurTracabilite(ValueError):
    """Une règle de traçabilité opposable (§ 7.5) n'est pas respectée."""


# --------------------------------------------------------------------------- #
# Montant
# --------------------------------------------------------------------------- #

_MOTIF_DEVISE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class Montant:
    """Un montant porte **toujours** sa devise (code ISO 4217, ex. « EUR »)."""

    valeur: Decimal
    devise: str

    def __post_init__(self) -> None:
        if not isinstance(self.valeur, Decimal):
            try:
                object.__setattr__(self, "valeur", Decimal(str(self.valeur)))
            except (InvalidOperation, TypeError) as exc:
                raise ValueError(f"Montant illisible : {self.valeur!r}") from exc
        if not _MOTIF_DEVISE.match(self.devise or ""):
            raise ValueError(
                "La devise d'un montant est obligatoire et doit être un code "
                f"ISO 4217 (3 majuscules), reçu : {self.devise!r}"
            )

    def vers_chaine(self) -> str:
        """Représentation stockable (le montant chiffré est du texte)."""
        return format(self.valeur, "f")


# --------------------------------------------------------------------------- #
# Traçabilité — règles opposables (§ 7.5)
# --------------------------------------------------------------------------- #


def appliquer_regles_tracabilite(
    *,
    origine: str,
    confiance: str,
    source_document_id: Optional[str],
) -> None:
    """Fait respecter les règles opposables de traçabilité (§ 7.5).

    1. `document_extrait` **exige** un document source ;
    2. `saisie_entreprise` sans document plafonne la confiance à `declare_non_verifie` ;
    3. `verifie` n'est recevable qu'avec une source.

    Aucune de ces fonctions ne fabrique de valeur : elle refuse, ou elle plafonne.
    """
    if origine == OrigineSynthese.MIXTE.value:
        if confiance == Confiance.VERIFIE.value:
            raise ErreurTracabilite(
                "Une origine « mixte » ne peut pas porter la confiance « verifie »."
            )
        return
    if origine == Origine.DOCUMENT_EXTRAIT.value and not source_document_id:
        raise ErreurTracabilite(
            "Origine « document_extrait » sans document source : refusé "
            "(règle 1 de docs/DATA-MODEL-V2.md § 7.5)."
        )
    if origine == Origine.SAISIE_ENTREPRISE.value and not source_document_id:
        if confiance == Confiance.VERIFIE.value:
            raise ErreurTracabilite(
                "Confiance « verifie » sans source : refusé (règle 3). Une valeur "
                "sans source est au plus « declare_non_verifie »."
            )


def confiance_recevable(
    *,
    origine: str,
    confiance: str,
    source_document_id: Optional[str],
    controle_humain_par: Optional[str] = None,
) -> str:
    """Renvoie la confiance recevable pour une valeur, ou refuse (lève).

    * sans source : au plus `a_verifier` — **jamais** `verifie` ;
    * `saisie_entreprise` sans document : plafonnée à `declare_non_verifie` ;
    * `verifie` : exige une source **et** un contrôle humain nommé.
    """
    if confiance not in ORDRE_CONFIANCE:
        raise ErreurTracabilite(
            f"Confiance invalide : {confiance!r} — attendu {list(ORDRE_CONFIANCE)}"
        )
    if confiance == Confiance.VERIFIE.value:
        if not source_document_id:
            raise ErreurTracabilite(
                "Confiance « verifie » sans source : refusé. Une valeur sans source "
                "est « a_verifier », jamais « verifie »."
            )
        if not controle_humain_par:
            raise ErreurTracabilite(
                "Confiance « verifie » : un contrôle humain nommé est requis — aucun "
                "chemin automatique ne pose « verifie »."
            )
        return Confiance.VERIFIE.value
    if confiance == Confiance.DECLARE_NON_VERIFIE.value:
        if not source_document_id and origine != Origine.SAISIE_ENTREPRISE.value:
            raise ErreurTracabilite(
                "`declare_non_verifie` n'est recevable que pour une saisie de "
                "l'entreprise ; une valeur extraite d'un document suit la règle 1."
            )
        return Confiance.DECLARE_NON_VERIFIE.value
    return Confiance.A_VERIFIER.value


@dataclass(frozen=True)
class Traceabilite:
    """Colonnes de **synthèse** de traçabilité d'un enregistrement (§ 7.4).

    Ce n'est plus la source de vérité mais le **résumé** de la traçabilité des
    valeurs de l'enregistrement : `origine` peut valoir `mixte`, `confiance` est la
    plus faible des valeurs, et `source_document_id` n'est renseigné que si
    l'enregistrement entier vient d'un seul document.
    """

    origine: str
    confiance: str = Confiance.A_VERIFIER.value
    source_document_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.origine not in {o.value for o in OrigineSynthese}:
            raise ErreurTracabilite(
                f"Origine invalide : {self.origine!r} — attendu "
                f"{sorted(o.value for o in OrigineSynthese)}"
            )
        if self.confiance not in ORDRE_CONFIANCE:
            raise ErreurTracabilite(
                f"Confiance invalide : {self.confiance!r} — attendu {list(ORDRE_CONFIANCE)}"
            )
        appliquer_regles_tracabilite(
            origine=self.origine,
            confiance=self.confiance,
            source_document_id=self.source_document_id,
        )


@dataclass(frozen=True)
class TraceabiliteValeur:
    """Traçabilité **au niveau de la valeur** : une ligne par champ tracé (§ 7.2).

    Une ligne n'est écrite que pour les champs qui ne partagent pas la source de
    l'enregistrement (héritage, § 7.3).
    """

    entite: str
    enregistrement_id: str
    champ: str
    origine: str
    confiance: str = Confiance.A_VERIFIER.value
    source_document_id: Optional[str] = None
    source_emplacement: Optional[str] = None
    source_commentaire: Optional[str] = None

    def __post_init__(self) -> None:
        if self.origine not in {o.value for o in Origine}:
            raise ErreurTracabilite(
                f"Origine invalide : {self.origine!r} — attendu "
                f"{sorted(o.value for o in Origine)} "
                "(jamais de valeur « générée par l'IA »)"
            )
        if self.confiance not in ORDRE_CONFIANCE:
            raise ErreurTracabilite(f"Confiance invalide : {self.confiance!r}")
        if not self.entite or not self.enregistrement_id or not self.champ:
            raise ErreurTracabilite(
                "entite, enregistrement_id et champ sont obligatoires (§ 7.2)."
            )
        appliquer_regles_tracabilite(
            origine=self.origine,
            confiance=self.confiance,
            source_document_id=self.source_document_id,
        )


# --------------------------------------------------------------------------- #
# Statut de validité — calculé, jamais stocké (§ 3.3)
# --------------------------------------------------------------------------- #


def calculer_statut_validite(
    date_fin: Optional[date],
    *,
    aujourd_hui: Optional[date] = None,
    fenetre_alerte_jours: Optional[int] = None,
) -> StatutValidite:
    """Calcule `statut_validite` à la lecture.

    **Aucun seuil n'est fixé dans le code** : si `fenetre_alerte_jours` est `None`,
    la fenêtre d'alerte n'est pas réglée et `echeance_proche` ne peut pas être
    produit (réglage produit — `docs/DATA-MODEL-V2.md` § 15 point 3). Aucune durée de
    validité légale n'est écrite ici : la date se lit sur le document ; à défaut, la
    valeur est `non_renseigne`.
    """
    if date_fin is None:
        return StatutValidite.NON_RENSEIGNE
    reference = aujourd_hui or date.today()
    if date_fin < reference:
        return StatutValidite.EXPIRE
    if fenetre_alerte_jours is not None and fenetre_alerte_jours >= 0:
        if (date_fin - reference).days <= fenetre_alerte_jours:
            return StatutValidite.ECHEANCE_PROCHE
    return StatutValidite.VALIDE


def identifiant_technique_valide(valeur: object) -> bool:
    """Un identifiant technique est un UUID, jamais un numéro métier (§ 3.1)."""
    if not isinstance(valeur, str):
        return False
    try:
        uuid.UUID(valeur)
    except (ValueError, AttributeError, TypeError):
        return False
    return True
