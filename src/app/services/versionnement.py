"""Service — versionnement, états de fiche et relecture humaine.

Implémente `docs/DATA-MODEL-V2.md` § 6 :

* `fiche_version` : l'axe de versionnement (§ 6.1) ;
* les **7 états** de `fiche.statut_version` (§ 6.2) — l'état est **calculé** (le
  modèle rappelle que stocker un statut que le temps rendrait faux est une faute ;
  la colonne n'est qu'un **cache** de transition, et `archivee` reste explicite) ;
* les **4 états** de `fiche.statut_famille` (§ 6.3) ;
* `validation_relecture` (§ 6.4) : relecteur nommé, attestation cochée, horodatage
  posé par la base, empreinte du contenu validé ;
* la **révocation à la première modification** (§ 6.5) ;
* le **contrôle par empreinte** (invariant I6) : recalculer l'empreinte d'un
  périmètre validé suffit à savoir si la validation est encore valable. Un défaut du
  code d'écriture ne suffit donc **pas** à produire une validation indûment valable.

**Ce que ce module ne fait pas** : il ne choisit pas l'algorithme d'empreinte du
projet (point ouvert § 15 point 12) — il en **nomme un** (`sha256-canonique-v1`) et
l'enregistre dans `validation_relecture.empreinte_algorithme`, ce qui est exactement
ce que le modèle prévoit pour rester réversible.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Iterable, Mapping, Optional

from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    TABLES_CONTENU,
)
from app.domain.fiche_version import (
    CibleValidation,
    LIBELLES_STATUT_VERSION,
    StatutFamille,
    StatutValidation,
    StatutVersion,
)
from app.storage.connexion import Connexion, ContexteClient
from app.storage.repositories import (
    DepotContenu,
    DepotFicheFamille,
    DepotFicheVersion,
    DepotValidationRelecture,
    depot_contenu,
)

#: Algorithme d'empreinte **nommé** (pas imposé par le modèle) : JSON canonique,
#: clés triées, valeurs sérialisées de façon déterministe, puis SHA-256.
ALGORITHME_EMPREINTE = "sha256-canonique-v1"


class ErreurVersionnement(RuntimeError):
    """Opération de versionnement refusée (état incompatible, cible inconnue…)."""


class CibleInconnue(ErreurVersionnement):
    """La fiche visée n'existe pas pour ce client."""


def _serialiser_valeur(valeur: Any) -> Any:
    """Sérialisation **déterministe** d'une valeur pour l'empreinte."""
    if valeur is None or isinstance(valeur, (str, int, float, bool)):
        return valeur
    return str(valeur)  # date, datetime, Decimal, uuid…


def _canoniser(contenu: Any) -> str:
    return json.dumps(
        contenu, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_serialiser_valeur
    )


class ServiceVersionnement:
    """Versionnement, états et relecture humaine d'une fiche."""

    def __init__(
        self,
        connexion: Connexion,
        cle_maitresse: bytes,
        contexte: ContexteClient,
    ) -> None:
        self._connexion = connexion
        self._cle = cle_maitresse
        self._contexte = contexte
        self.fiches = DepotFicheVersion(connexion, cle_maitresse)
        self.familles = DepotFicheFamille(connexion, cle_maitresse)
        self.validations = DepotValidationRelecture(connexion, cle_maitresse)
        self._depots: dict[str, DepotContenu] = {}

    # -- accès -------------------------------------------------------------- #
    def depot(self, entite: str) -> DepotContenu:
        if entite not in self._depots:
            self._depots[entite] = depot_contenu(self._connexion, self._cle, entite)
        return self._depots[entite]

    def fiche(self, fiche_version_id: str) -> dict[str, Any]:
        """La fiche du client courant — jamais celle d'un autre (filtre `client_id`)."""
        fiche = self.fiches.obtenir(self._contexte, fiche_version_id)
        if fiche is None:
            raise CibleInconnue(
                f"Aucune fiche {fiche_version_id!r} pour ce client : lecture refusée."
            )
        return fiche

    # -- création ----------------------------------------------------------- #
    def creer_version(
        self,
        entreprise_id: str,
        *,
        commentaire: Optional[str] = None,
        version_parente_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Ouvre une nouvelle version. Le numéro est croissant par entreprise (§ 6.1)."""
        fiche = self.fiches.creer(
            self._contexte,
            entreprise_id=entreprise_id,
            commentaire=commentaire,
            version_parente_id=version_parente_id,
        )
        for famille in LIBELLES_FAMILLES:
            self.familles.assurer(
                self._contexte,
                entreprise_id=entreprise_id,
                fiche_version_id=str(fiche["id"]),
                famille_code=famille,
            )
        return {"id": str(fiche["id"]), "numero_version": int(fiche["numero_version"]), "statut": fiche["statut"]}

    # -- empreinte du périmètre validé (I6) --------------------------------- #
    def contenu_canonique(
        self,
        fiche_version_id: str,
        *,
        cible_type: str = CibleValidation.FICHE.value,
        famille_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Contenu **canonique** du périmètre : tout ce qui est validé, rien d'autre."""
        self.fiche(fiche_version_id)  # cloisonnement : la fiche doit être du client
        if cible_type == CibleValidation.FICHE.value:
            entites: tuple[str, ...] = tuple(TABLES_CONTENU)
        elif cible_type == CibleValidation.FAMILLE.value:
            if famille_code not in FAMILLE_VERS_ENTITES:
                raise ErreurVersionnement(f"Famille inconnue : {famille_code!r}")
            entites = FAMILLE_VERS_ENTITES[famille_code]
        else:
            raise ErreurVersionnement(f"`cible_type` invalide : {cible_type!r}")

        contenu: dict[str, Any] = {}
        for table in entites:
            depot = self.depot(table)
            lignes = depot.lister(
                self._contexte, fiche_version_id, statut_enregistrement=None
            )
            enrichies: list[dict[str, Any]] = []
            for ligne in lignes:
                valeur = dict(ligne)
                for liaison in depot.definition.liaisons:
                    valeur[f"_{liaison.champ}"] = sorted(
                        depot.lire_liaisons(self._contexte, str(ligne["id"]), liaison.champ)
                    )
                enrichies.append(valeur)
            contenu[table] = sorted(enrichies, key=lambda l: str(l["id"]))
        return contenu

    def empreinte(
        self,
        fiche_version_id: str,
        *,
        cible_type: str = CibleValidation.FICHE.value,
        famille_code: Optional[str] = None,
    ) -> str:
        """Empreinte du périmètre : recalculable à tout moment, donc opposable."""
        canonique = _canoniser(
            self.contenu_canonique(
                fiche_version_id, cible_type=cible_type, famille_code=famille_code
            )
        )
        return hashlib.sha256(canonique.encode("utf-8")).hexdigest()

    # -- états -------------------------------------------------------------- #
    def statut_fiche(self, fiche_version_id: str) -> str:
        """**Calcule** l'état de la fiche (§ 6.2), à la lecture.

        L'état calculé fait foi ; la colonne `fiche_version.statut` n'en est qu'un
        cache, mis à jour aux transitions, plus la valeur explicite `archivee`.
        """
        fiche = self.fiche(fiche_version_id)
        if fiche["statut"] == StatutVersion.ARCHIVEE.value:
            return StatutVersion.ARCHIVEE.value

        remplies: list[str] = []
        for famille, entites in FAMILLE_VERS_ENTITES.items():
            if any(
                self.depot(entite).compter(self._contexte, fiche_version_id) > 0
                for entite in entites
            ):
                remplies.append(famille)
        if not remplies:
            return StatutVersion.VIERGE.value

        validations = self.validations.lister_pour_fiche(self._contexte, fiche_version_id)
        validees_fiche = [
            v
            for v in validations
            if v["statut"] == StatutValidation.VALIDEE.value
            and v["cible_type"] == CibleValidation.FICHE.value
        ]
        if validees_fiche:
            courante = self.empreinte(fiche_version_id)
            if any(str(v["empreinte_contenu"]) == courante for v in validees_fiche):
                return StatutVersion.VALIDEE.value
            return StatutVersion.VALIDEE_PUIS_MODIFIEE.value

        if fiche["statut"] == StatutVersion.EN_RELECTURE.value or any(
            v["statut"] == StatutValidation.REVOQUEE.value for v in validations
        ):
            return StatutVersion.EN_RELECTURE.value

        if len(remplies) == len(FAMILLE_VERS_ENTITES):
            return StatutVersion.SOCLE_COMPLET.value
        return StatutVersion.EN_SAISIE.value

    def synchroniser_statut(self, fiche_version_id: str) -> str:
        """Écrit l'état calculé dans la colonne-cache `fiche_version.statut`."""
        statut = self.statut_fiche(fiche_version_id)
        self.fiches.maj_statut(self._contexte, fiche_version_id, statut)
        return statut

    def etat_fiche(self, fiche_version_id: str) -> dict[str, Any]:
        """État complet : statut, libellé, avancement par famille, validations, I6."""
        statut = self.statut_fiche(fiche_version_id)
        avancement = {ligne["famille_code"]: ligne["statut"] for ligne in self.familles.lister(self._contexte, fiche_version_id)}
        par_famille = []
        for famille, libelle in LIBELLES_FAMILLES.items():
            entites = FAMILLE_VERS_ENTITES[famille]
            nb = sum(
                self.depot(entite).compter(self._contexte, fiche_version_id)
                for entite in entites
            )
            par_famille.append(
                {
                    "famille": famille,
                    "libelle": libelle,
                    "entites": list(entites),
                    "nb_elements": nb,
                    "statut": avancement.get(famille, StatutFamille.NON_COMMENCEE.value),
                    # Complétude **structurelle** : une famille sans aucun élément est
                    # incomplète. Les niveaux d'exigence N1/N2/N3 restent propres à
                    # l'interface (docs/DATA-MODEL-V2.md § 3.3) : ils ne sont pas
                    # décidés ici.
                    "completude_famille": "complete" if nb > 0 else "incomplete",
                }
            )
        return {
            "fiche_version_id": fiche_version_id,
            "statut": statut,
            "statut_libelle": LIBELLES_STATUT_VERSION[statut],
            "familles": par_famille,
            "validations": self.validations.lister_pour_fiche(self._contexte, fiche_version_id),
            "anomalies_empreinte": self.controler_validations(fiche_version_id),
        }

    # -- écriture : révocation à la première modification (§ 6.5) ----------- #
    def enregistrer_ecriture(
        self, fiche_version_id: str, *, famille_code: str, motif: Optional[str] = None
    ) -> dict[str, Any]:
        """À appeler après **toute** écriture sur un champ d'une famille.

        1. révoque les validations `validee` couvrant le périmètre écrit ;
        2. fait passer la famille à `demarree` ;
        3. met à jour le cache d'état de la fiche (→ `en_relecture` si révocation).
        """
        self.fiche(fiche_version_id)
        motif_effectif = motif or f"écriture sur un champ de la famille {famille_code}"
        revoquees = self.validations.revoquer(
            self._contexte,
            fiche_version_id,
            famille_code=famille_code,
            motif=motif_effectif,
        )
        self.familles.maj_statut(
            self._contexte, fiche_version_id, famille_code, StatutFamille.DEMARREE.value
        )
        self.fiches.marquer_ecriture(self._contexte, fiche_version_id)
        if revoquees:
            self.fiches.maj_statut(
                self._contexte, fiche_version_id, StatutVersion.EN_RELECTURE.value
            )
        statut = self.statut_fiche(fiche_version_id)
        self.fiches.maj_statut(self._contexte, fiche_version_id, statut)
        return {"validations_revoquees": revoquees, "statut": statut}

    # -- validation humaine (§ 6.4) ----------------------------------------- #
    def valider(
        self,
        fiche_version_id: str,
        *,
        relecteur_nom: str,
        attestation_cochee: bool,
        cible_type: str = CibleValidation.FICHE.value,
        famille_code: Optional[str] = None,
        commentaire: Optional[str] = None,
    ) -> dict[str, Any]:
        """Enregistre une validation. **Aucun chemin automatique ne mène à `validee`.**

        Le nom du relecteur et l'attestation cochée sont exigés ; l'horodatage est
        posé par la base au moment de l'action humaine.
        """
        fiche = self.fiche(fiche_version_id)
        if fiche["statut"] == StatutVersion.ARCHIVEE.value and cible_type == CibleValidation.FICHE.value:
            raise ErreurVersionnement(
                "Une version archivée n'est pas validée : elle prouve ce qui a été fourni."
            )
        if not (relecteur_nom or "").strip():
            raise ErreurVersionnement(
                "Le nom du relecteur est obligatoire : la relecture humaine est la "
                "seule source de l'état « relue et validée »."
            )
        if not attestation_cochee:
            raise ErreurVersionnement(
                "L'attestation « j'ai relu et corrigé les informations ci-dessus » "
                "doit être cochée : la validation ne se court-circuite pas."
            )
        if cible_type == CibleValidation.FAMILLE.value:
            if famille_code not in FAMILLE_VERS_ENTITES:
                raise ErreurVersionnement(f"Famille inconnue : {famille_code!r}")
            if any(
                self.depot(entite).compter(self._contexte, fiche_version_id) == 0
                for entite in FAMILLE_VERS_ENTITES[famille_code]
            ):
                # Une famille peut n'avoir aucun élément : on ne « valide » pas du vide.
                pass
        empreinte = self.empreinte(
            fiche_version_id, cible_type=cible_type, famille_code=famille_code
        )
        validation_id = self.validations.creer(
            self._contexte,
            entreprise_id=str(fiche["entreprise_id"]),
            fiche_version_id=fiche_version_id,
            cible_type=cible_type,
            famille_code=famille_code,
            relecteur_nom=relecteur_nom,
            attestation_cochee=attestation_cochee,
            empreinte_contenu=empreinte,
            empreinte_algorithme=ALGORITHME_EMPREINTE,
            commentaire=commentaire,
        )
        if cible_type == CibleValidation.FAMILLE.value and famille_code:
            self.familles.maj_statut(
                self._contexte, fiche_version_id, famille_code, StatutFamille.VALIDEE.value
            )
        statut = self.synchroniser_statut(fiche_version_id)
        return {
            "validation_id": validation_id,
            "cible_type": cible_type,
            "famille_code": famille_code,
            "empreinte_contenu": empreinte,
            "empreinte_algorithme": ALGORITHME_EMPREINTE,
            "statut": statut,
        }

    def archiver(self, fiche_version_id: str) -> None:
        """Archive une version : elle reste **lisible** (§ 6.1 règle 3)."""
        self.fiche(fiche_version_id)
        self.fiches.maj_statut(self._contexte, fiche_version_id, StatutVersion.ARCHIVEE.value)

    # -- contrôle indépendant par empreinte (I6) ---------------------------- #
    def controler_validations(self, fiche_version_id: str) -> list[dict[str, Any]]:
        """Recalcule l'empreinte de chaque périmètre validé et compte les écarts.

        C'est le contrôle **indépendant de l'écriture** de l'invariant I6 : il
        détecte une validation qui se prétend valable alors que le contenu a bougé,
        même si le code d'écriture a oublié de la révoquer.
        """
        self.fiche(fiche_version_id)
        anomalies: list[dict[str, Any]] = []
        for validation in self.validations.lister_pour_fiche(self._contexte, fiche_version_id):
            if validation["statut"] != StatutValidation.VALIDEE.value:
                continue
            try:
                recalcul = self.empreinte(
                    fiche_version_id,
                    cible_type=str(validation["cible_type"]),
                    famille_code=(
                        str(validation["famille_code"])
                        if validation["famille_code"] is not None
                        else None
                    ),
                )
            except ErreurVersionnement as exc:  # pragma: no cover — cible devenue invalide
                anomalies.append(
                    {
                        "validation_id": str(validation["id"]),
                        "motif": f"empreinte incalculable : {exc}",
                    }
                )
                continue
            if recalcul != str(validation["empreinte_contenu"]):
                anomalies.append(
                    {
                        "validation_id": str(validation["id"]),
                        "cible_type": validation["cible_type"],
                        "famille_code": validation["famille_code"],
                        "relecteur_nom": validation["relecteur_nom"],
                        "empreinte_enregistree": str(validation["empreinte_contenu"]),
                        "empreinte_recalculee": recalcul,
                        "motif": (
                            "validation indûment valable : le contenu du périmètre a "
                            "changé depuis la validation (invariant I6)"
                        ),
                    }
                )
        return anomalies


def fenetre_alerte_jours_depuis_environnement() -> Optional[int]:
    """Lit la fenêtre d'alerte d'échéance — **réglage**, jamais un seuil en dur.

    Variable optionnelle `FENETRE_ALERTE_JOURS`. Absente ou invalide → `None`, ce
    qui signifie « pas de fenêtre réglée » : l'état `echeance_proche` n'est alors
    jamais produit (`docs/DATA-MODEL-V2.md` § 3.3 et § 15 point 3).
    """
    brut = os.environ.get("FENETRE_ALERTE_JOURS")
    if brut is None or not str(brut).strip():
        return None
    try:
        valeur = int(str(brut).strip())
    except ValueError:
        return None
    return valeur if valeur >= 0 else None


def familles_connues() -> Iterable[str]:
    """Les neuf codes de famille, dans l'ordre du modèle."""
    return tuple(LIBELLES_FAMILLES)
