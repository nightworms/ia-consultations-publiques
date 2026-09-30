"""Dépôts de persistance — **filtrés par `client_id`, sans exception**.

Règles tenues par ce module (annexe A § A1 et § A3) :

* **aucune requête SQL hors de la couche `storage/`** : ce fichier est le seul lieu
  où le SQL de la bibliothèque est écrit ;
* **tout** passe par `Connexion`, qui exige un `ContexteClient` et impose le filtre
  `%(client_id)s` : un dépôt ne peut pas lire ni écrire la ligne d'un autre client,
  même si on le lui demandait ;
* les **noms de tables et de colonnes** viennent du registre `app/domain/familles.py`
  (liste blanche). Aucun nom de colonne n'est jamais construit à partir d'une entrée
  utilisateur — les identifiants SQL ne sont pas paramétrables ;
* les **champs du registre sensible** (annexe A § A6) sont chiffrés **par client** au
  moment de l'écriture et déchiffrés à la lecture, via le module livré par L1
  (`app/securite/chiffrement.py`). Le chiffrement n'est pas réécrit ici : il est
  appliqué.

**Troisième exception nommée et bornée** (les deux premières appartiennent à L1) : les
tables `jeu_reference` et `valeur_reference` sont **globales** — elles ne portent aucun
`client_id` (invariant I5) et ne contiennent aucune donnée d'entreprise. `DepotReference`
les lit donc par un SQL **figé**, sur ces deux tables uniquement, sans contexte client.
Aucun SQL arbitraire n'est admis par cette porte.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Optional

from app.securite.chiffrement import chiffrer, dechiffrer
from app.storage.connexion import Connexion, ContexteClient
from app.domain.familles import (
    COLONNES_COMMUNES_ACCEPTEES,
    DefinitionEntite,
    definition_entite,
    type_champ,
)


class ErreurDepot(RuntimeError):
    """Opération de persistance refusée (donnée invalide, colonne inconnue…)."""


# --------------------------------------------------------------------------- #
# Conversions
# --------------------------------------------------------------------------- #

_TYPES_ACCEPTES = {"texte", "date", "entier", "decimal"}


def _coercer(champ: str, valeur: Any, type_declare: str) -> Any:
    """Convertit une valeur d'entrée (JSON) vers le type attendu par la colonne."""
    if valeur is None or valeur == "":
        return None if type_declare != "texte" else valeur
    if type_declare not in _TYPES_ACCEPTES:
        raise ErreurDepot(f"Type de champ inconnu pour {champ!r} : {type_declare!r}")
    try:
        if type_declare == "date":
            if isinstance(valeur, _dt.date) and not isinstance(valeur, _dt.datetime):
                return valeur
            if isinstance(valeur, _dt.datetime):
                return valeur.date()
            return _dt.date.fromisoformat(str(valeur))
        if type_declare == "entier":
            return int(valeur)
        if type_declare == "decimal":
            return Decimal(str(valeur))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ErreurDepot(
            f"Valeur invalide pour le champ {champ!r} (type {type_declare}) : {valeur!r}"
        ) from exc
    return str(valeur)


def _texte_iso(valeur: Any) -> str:
    if isinstance(valeur, _dt.datetime):
        return valeur.isoformat()
    if isinstance(valeur, _dt.date):
        return valeur.isoformat()
    return str(valeur)


# --------------------------------------------------------------------------- #
# Base commune
# --------------------------------------------------------------------------- #


class DepotBase:
    """Ce dont tout dépôt a besoin : une connexion cloisonnée et la clé maîtresse."""

    def __init__(self, connexion: Connexion, cle_maitresse: bytes) -> None:
        if not isinstance(connexion, Connexion):
            raise ErreurDepot("Un dépôt exige une `Connexion`.")
        if not cle_maitresse or len(cle_maitresse) != 32:
            raise ErreurDepot("Clé maîtresse absente ou invalide (32 octets attendus).")
        self._connexion = connexion
        self._cle_maitresse = cle_maitresse

    @property
    def connexion(self) -> Connexion:
        return self._connexion


# --------------------------------------------------------------------------- #
# Dépôt générique d'une entité de contenu (une par famille)
# --------------------------------------------------------------------------- #

_COLONNES_TECHNIQUES = (
    "id",
    "client_id",
    "entreprise_id",
    "fiche_version_id",
    "date_creation",
    "date_modification",
    "sensibilite",
    "statut_enregistrement",
    "origine",
    "confiance",
    "source_document_id",
)


class DepotContenu(DepotBase):
    """Dépôt d'une entité de contenu : création, lecture, modification, archivage."""

    def __init__(
        self, connexion: Connexion, cle_maitresse: bytes, entite: str
    ) -> None:
        super().__init__(connexion, cle_maitresse)
        self._definition: DefinitionEntite = definition_entite(entite)

    @property
    def definition(self) -> DefinitionEntite:
        return self._definition

    @property
    def table(self) -> str:
        return self._definition.table

    # -- chiffrement ------------------------------------------------------- #
    def _chiffrer(self, client_id: str, valeurs: Mapping[str, Any]) -> dict[str, Any]:
        sortie = dict(valeurs)
        for champ in self._definition.champs_chiffres:
            if champ in sortie and sortie[champ] is not None:
                sortie[champ] = chiffrer(
                    self._cle_maitresse, client_id, _texte_iso(sortie[champ])
                )
        return sortie

    def _dechiffrer(self, client_id: str, lignes: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        sortie: list[dict[str, Any]] = []
        for ligne in lignes:
            valeurs = dict(ligne)
            for champ in self._definition.champs_chiffres:
                if champ in valeurs and valeurs[champ] is not None:
                    valeurs[champ] = dechiffrer(
                        self._cle_maitresse, client_id, str(valeurs[champ])
                    )
            sortie.append(valeurs)
        return sortie

    # -- validation des colonnes ------------------------------------------- #
    def _verifier_colonnes(self, valeurs: Mapping[str, Any]) -> None:
        autorisees = set(self._definition.champs) | set(COLONNES_COMMUNES_ACCEPTEES)
        inconnues = sorted(set(valeurs) - autorisees)
        if inconnues:
            raise ErreurDepot(
                f"Colonnes inconnues pour l'entité {self._definition.entite!r} : "
                f"{inconnues}. Champs acceptés : {sorted(autorisees)}"
            )

    def _normaliser(self, valeurs: Mapping[str, Any]) -> dict[str, Any]:
        self._verifier_colonnes(valeurs)
        normalisees: dict[str, Any] = {}
        for champ, valeur in valeurs.items():
            if champ in self._definition.champs:
                normalisees[champ] = _coercer(
                    champ, valeur, type_champ(self._definition.entite, champ)
                )
            else:
                normalisees[champ] = valeur
        return normalisees

    # -- lecture ----------------------------------------------------------- #
    @property
    def colonnes_lisibles(self) -> tuple[str, ...]:
        return _COLONNES_TECHNIQUES + tuple(self._definition.champs)

    def lister(
        self,
        contexte: ContexteClient,
        fiche_version_id: str,
        *,
        statut_enregistrement: Optional[str] = "actif",
    ) -> list[dict[str, Any]]:
        """Enregistrements d'une fiche pour ce client. Jamais ceux d'un autre."""
        colonnes = ", ".join(self.colonnes_lisibles)
        sql = (
            f"SELECT {colonnes} FROM {self.table} "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s"
        )
        params: dict[str, Any] = {"fiche": fiche_version_id}
        if statut_enregistrement is not None:
            sql += " AND statut_enregistrement = %(statut)s"
            params["statut"] = statut_enregistrement
        sql += " ORDER BY date_creation, id"
        lignes = self._connexion.executer(contexte, sql, params)
        return self._dechiffrer(contexte.client_id, lignes)

    def obtenir(self, contexte: ContexteClient, element_id: str) -> Optional[dict[str, Any]]:
        colonnes = ", ".join(self.colonnes_lisibles)
        ligne = self._connexion.executer_une(
            contexte,
            f"SELECT {colonnes} FROM {self.table} "
            "WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": element_id},
        )
        if ligne is None:
            return None
        return self._dechiffrer(contexte.client_id, [ligne])[0]

    def compter(self, contexte: ContexteClient, fiche_version_id: str) -> int:
        ligne = self._connexion.executer_une(
            contexte,
            f"SELECT count(*) AS n FROM {self.table} "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
            "AND statut_enregistrement = 'actif'",
            {"fiche": fiche_version_id},
        )
        return int(ligne["n"]) if ligne else 0

    # -- écriture ---------------------------------------------------------- #
    def creer(
        self,
        contexte: ContexteClient,
        *,
        entreprise_id: str,
        fiche_version_id: str,
        valeurs: Mapping[str, Any],
    ) -> str:
        """Insère un enregistrement pour ce client. Renvoie son identifiant."""
        donnees = self._normaliser(valeurs)
        donnees = self._chiffrer(contexte.client_id, donnees)
        colonnes = sorted(donnees)
        liste_colonnes = ", ".join(colonnes)
        placeholders = ", ".join(f"%({c})s" for c in colonnes)
        sql = (
            f"INSERT INTO {self.table} "
            f"({liste_colonnes}, client_id, entreprise_id, fiche_version_id, "
            "date_creation, date_modification) "
            f"VALUES ({placeholders}, %(client_id)s, %(entreprise_id)s, "
            "%(fiche_version_id)s, now(), now()) "
            "RETURNING id"
        )
        params = dict(donnees)
        params["entreprise_id"] = entreprise_id
        params["fiche_version_id"] = fiche_version_id
        ligne = self._connexion.executer_une(contexte, sql, params)
        if ligne is None:  # pragma: no cover — RETURNING garantit une ligne
            raise ErreurDepot("Création impossible : aucune ligne retournée.")
        return str(ligne["id"])

    def modifier(
        self, contexte: ContexteClient, element_id: str, valeurs: Mapping[str, Any]
    ) -> None:
        """Modifie un enregistrement **du client courant** (aucune autre ligne)."""
        if not valeurs:
            raise ErreurDepot("Aucune valeur à modifier.")
        donnees = self._normaliser(valeurs)
        donnees = self._chiffrer(contexte.client_id, donnees)
        affectations = ", ".join(f"{c} = %({c})s" for c in sorted(donnees))
        sql = (
            f"UPDATE {self.table} SET {affectations}, date_modification = now() "
            "WHERE client_id = %(client_id)s AND id = %(id)s"
        )
        params = dict(donnees)
        params["id"] = element_id
        self._connexion.executer(contexte, sql, params)

    def archiver(self, contexte: ContexteClient, element_id: str) -> None:
        """Archive : un enregistrement n'est **jamais** supprimé en dur (§ 3.2)."""
        self._connexion.executer(
            contexte,
            f"UPDATE {self.table} SET statut_enregistrement = 'archive', "
            "date_modification = now() "
            "WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": element_id},
        )

    # -- liaisons (champs de type `liste`, § 3.1) -------------------------- #
    def remplacer_liaisons(
        self,
        contexte: ContexteClient,
        element_id: str,
        champ: str,
        ids: Iterable[str],
    ) -> None:
        liaison = next((l for l in self._definition.liaisons if l.champ == champ), None)
        if liaison is None:
            raise ErreurDepot(
                f"Champ de liste inconnu pour {self._definition.entite!r} : {champ!r}"
            )
        self._connexion.executer(
            contexte,
            f"DELETE FROM {liaison.table} "
            f"WHERE client_id = %(client_id)s AND {liaison.colonne_proprietaire} = %(proprietaire)s",
            {"proprietaire": element_id},
        )
        for cible in ids:
            self._connexion.executer(
                contexte,
                f"INSERT INTO {liaison.table} "
                f"({liaison.colonne_proprietaire}, {liaison.colonne_cible}, client_id) "
                "VALUES (%(proprietaire)s, %(cible)s, %(client_id)s)",
                {"proprietaire": element_id, "cible": cible},
            )

    def lire_liaisons(
        self, contexte: ContexteClient, element_id: str, champ: str
    ) -> list[str]:
        liaison = next((l for l in self._definition.liaisons if l.champ == champ), None)
        if liaison is None:
            raise ErreurDepot(f"Champ de liste inconnu : {champ!r}")
        lignes = self._connexion.executer(
            contexte,
            f"SELECT {liaison.colonne_cible} AS cible FROM {liaison.table} "
            f"WHERE client_id = %(client_id)s AND {liaison.colonne_proprietaire} = %(proprietaire)s "
            "ORDER BY date_creation, "
            f"{liaison.colonne_cible}",
            {"proprietaire": element_id},
        )
        return [str(ligne["cible"]) for ligne in lignes]


def depot_contenu(
    connexion: Connexion, cle_maitresse: bytes, entite: str
) -> DepotContenu:
    """Fabrique le dépôt d'une entité de contenu."""
    return DepotContenu(connexion, cle_maitresse, entite)


# --------------------------------------------------------------------------- #
# Racines et tables transverses
# --------------------------------------------------------------------------- #


class DepotEntreprise(DepotBase):
    """L'ancre stable `entreprise` (§ 5.3) — aucun contenu métier."""

    def creer(self, contexte: ContexteClient, libelle_court: str) -> str:
        if not (libelle_court or "").strip():
            raise ErreurDepot("Le libellé court d'une entreprise est obligatoire.")
        ligne = self._connexion.executer_une(
            contexte,
            "INSERT INTO entreprise (client_id, libelle_court) "
            "VALUES (%(client_id)s, %(libelle)s) RETURNING id",
            {"libelle": libelle_court.strip()},
        )
        if ligne is None:  # pragma: no cover
            raise ErreurDepot("Création de l'entreprise impossible.")
        return str(ligne["id"])

    def obtenir(self, contexte: ContexteClient, entreprise_id: str) -> Optional[dict[str, Any]]:
        return self._connexion.executer_une(
            contexte,
            "SELECT id, client_id, libelle_court, statut, date_creation "
            "FROM entreprise WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": entreprise_id},
        )

    def lister(self, contexte: ContexteClient) -> list[dict[str, Any]]:
        return self._connexion.executer(
            contexte,
            "SELECT id, client_id, libelle_court, statut FROM entreprise "
            "WHERE client_id = %(client_id)s ORDER BY date_creation, id",
        )


class DepotFicheVersion(DepotBase):
    """L'axe de versionnement `fiche_version` (§ 6.1)."""

    def creer(
        self,
        contexte: ContexteClient,
        *,
        entreprise_id: str,
        commentaire: Optional[str] = None,
        version_parente_id: Optional[str] = None,
        statut: str = "vierge",
    ) -> dict[str, Any]:
        ligne = self._connexion.executer_une(
            contexte,
            "INSERT INTO fiche_version "
            "(client_id, entreprise_id, numero_version, statut, version_parente_id, commentaire) "
            "VALUES (%(client_id)s, %(entreprise_id)s, "
            "(SELECT COALESCE(max(numero_version), 0) + 1 FROM fiche_version "
            " WHERE client_id = %(client_id)s AND entreprise_id = %(entreprise_id)s), "
            "%(statut)s, %(parent)s, %(commentaire)s) "
            "RETURNING id, numero_version, statut",
            {
                "entreprise_id": entreprise_id,
                "statut": statut,
                "parent": version_parente_id,
                "commentaire": commentaire,
            },
        )
        if ligne is None:  # pragma: no cover
            raise ErreurDepot("Création de la version impossible.")
        return dict(ligne)

    def obtenir(self, contexte: ContexteClient, fiche_version_id: str) -> Optional[dict[str, Any]]:
        return self._connexion.executer_une(
            contexte,
            "SELECT id, client_id, entreprise_id, numero_version, statut, "
            "version_parente_id, date_creation, date_derniere_ecriture, commentaire "
            "FROM fiche_version WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": fiche_version_id},
        )

    def lister_pour_entreprise(
        self, contexte: ContexteClient, entreprise_id: str
    ) -> list[dict[str, Any]]:
        return self._connexion.executer(
            contexte,
            "SELECT id, entreprise_id, numero_version, statut, date_creation "
            "FROM fiche_version "
            "WHERE client_id = %(client_id)s AND entreprise_id = %(entreprise_id)s "
            "ORDER BY numero_version DESC",
            {"entreprise_id": entreprise_id},
        )

    def derniere_pour_client(self, contexte: ContexteClient) -> Optional[dict[str, Any]]:
        """Version la plus récente du client — sert de point d'entrée par défaut."""
        return self._connexion.executer_une(
            contexte,
            "SELECT id, entreprise_id, numero_version, statut FROM fiche_version "
            "WHERE client_id = %(client_id)s "
            "ORDER BY date_creation DESC, numero_version DESC LIMIT 1",
        )

    def maj_statut(self, contexte: ContexteClient, fiche_version_id: str, statut: str) -> None:
        self._connexion.executer(
            contexte,
            "UPDATE fiche_version SET statut = %(statut)s "
            "WHERE client_id = %(client_id)s AND id = %(id)s",
            {"statut": statut, "id": fiche_version_id},
        )

    def marquer_ecriture(self, contexte: ContexteClient, fiche_version_id: str) -> None:
        self._connexion.executer(
            contexte,
            "UPDATE fiche_version SET date_derniere_ecriture = now() "
            "WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": fiche_version_id},
        )


class DepotFicheFamille(DepotBase):
    """L'avancement par famille `fiche_famille` (§ 6.3)."""

    def assurer(
        self,
        contexte: ContexteClient,
        *,
        entreprise_id: str,
        fiche_version_id: str,
        famille_code: str,
    ) -> None:
        """Crée la ligne d'avancement si elle n'existe pas (ne l'écrase jamais)."""
        self._connexion.executer(
            contexte,
            "INSERT INTO fiche_famille "
            "(client_id, entreprise_id, fiche_version_id, famille_code, statut, date_maj) "
            "VALUES (%(client_id)s, %(entreprise_id)s, %(fiche)s, %(famille)s, "
            "'non_commencee', now()) "
            "ON CONFLICT (fiche_version_id, famille_code) DO NOTHING",
            {
                "entreprise_id": entreprise_id,
                "fiche": fiche_version_id,
                "famille": famille_code,
            },
        )

    def maj_statut(
        self,
        contexte: ContexteClient,
        fiche_version_id: str,
        famille_code: str,
        statut: str,
    ) -> None:
        self._connexion.executer(
            contexte,
            "UPDATE fiche_famille SET statut = %(statut)s, date_maj = now() "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
            "AND famille_code = %(famille)s",
            {"statut": statut, "fiche": fiche_version_id, "famille": famille_code},
        )

    def lister(self, contexte: ContexteClient, fiche_version_id: str) -> list[dict[str, Any]]:
        return self._connexion.executer(
            contexte,
            "SELECT famille_code, statut, date_maj FROM fiche_famille "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
            "ORDER BY famille_code",
            {"fiche": fiche_version_id},
        )


class DepotValidationRelecture(DepotBase):
    """Le verrou de relecture humaine `validation_relecture` (§ 6.4)."""

    def creer(
        self,
        contexte: ContexteClient,
        *,
        entreprise_id: str,
        fiche_version_id: str,
        cible_type: str,
        famille_code: Optional[str],
        relecteur_nom: str,
        attestation_cochee: bool,
        empreinte_contenu: str,
        empreinte_algorithme: str,
        commentaire: Optional[str] = None,
    ) -> str:
        """Enregistre une validation. `date_validation` est posée par la base (`now()`)."""
        if not (relecteur_nom or "").strip():
            raise ErreurDepot(
                "`relecteur_nom` est obligatoire : aucune validation sans humain nommé."
            )
        if not attestation_cochee:
            raise ErreurDepot(
                "L'attestation de relecture doit être cochée : le verrou ne se "
                "court-circuite pas."
            )
        ligne = self._connexion.executer_une(
            contexte,
            "INSERT INTO validation_relecture "
            "(client_id, entreprise_id, fiche_version_id, cible_type, famille_code, "
            " relecteur_nom, attestation_cochee, statut, empreinte_contenu, "
            " empreinte_algorithme, commentaire) "
            "VALUES (%(client_id)s, %(entreprise_id)s, %(fiche)s, %(cible)s, %(famille)s, "
            "%(nom)s, 1, 'validee', %(empreinte)s, %(algo)s, %(commentaire)s) "
            "RETURNING id, date_validation",
            {
                "entreprise_id": entreprise_id,
                "fiche": fiche_version_id,
                "cible": cible_type,
                "famille": famille_code,
                "nom": relecteur_nom.strip(),
                "empreinte": empreinte_contenu,
                "algo": empreinte_algorithme,
                "commentaire": commentaire,
            },
        )
        if ligne is None:  # pragma: no cover
            raise ErreurDepot("Enregistrement de la validation impossible.")
        return str(ligne["id"])

    def lister_pour_fiche(
        self, contexte: ContexteClient, fiche_version_id: str
    ) -> list[dict[str, Any]]:
        return self._connexion.executer(
            contexte,
            "SELECT id, cible_type, famille_code, relecteur_nom, date_validation, "
            "attestation_cochee, statut, date_revocation, motif_revocation, "
            "empreinte_contenu, empreinte_algorithme "
            "FROM validation_relecture "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
            "ORDER BY date_creation, id",
            {"fiche": fiche_version_id},
        )

    def revoquer(
        self,
        contexte: ContexteClient,
        fiche_version_id: str,
        *,
        famille_code: Optional[str],
        motif: str,
    ) -> list[str]:
        """Révoque les validations `validee` couvrant le périmètre écrit (§ 6.5).

        Une validation de **fiche** couvre toutes les familles ; une validation de
        famille ne couvre que la sienne.
        """
        lignes = self._connexion.executer(
            contexte,
            "UPDATE validation_relecture "
            "SET statut = 'revoquee', date_revocation = now(), "
            "    motif_revocation = %(motif)s, date_modification = now() "
            "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
            "AND statut = 'validee' "
            "AND (cible_type = 'fiche' OR famille_code = %(famille)s) "
            "RETURNING id",
            {"fiche": fiche_version_id, "famille": famille_code, "motif": motif[:255]},
        )
        return [str(ligne["id"]) for ligne in lignes]


class DepotDocument(DepotBase):
    """Le document source `document` (§ 9.1) — brique de traçabilité."""

    def creer(
        self,
        contexte: ContexteClient,
        *,
        entreprise_id: str,
        fiche_version_id: str,
        type_document: str,
        libelle: str,
        chemin_stockage: str,
        deposant: str,
        sensibilite: str = "interne",
        emetteur: Optional[str] = None,
        date_emission: Optional[str] = None,
        date_validite_fin: Optional[str] = None,
        reference_document: Optional[str] = None,
        empreinte_sha256: Optional[str] = None,
        taille_octets: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        ligne = self._connexion.executer_une(
            contexte,
            "INSERT INTO document "
            "(client_id, entreprise_id, fiche_version_id, type_document, libelle, "
            " emetteur, date_emission, date_validite_fin, reference_document, "
            " chemin_stockage, deposant, empreinte_sha256, taille_octets, mime_type, "
            " sensibilite) "
            "VALUES (%(client_id)s, %(entreprise_id)s, %(fiche)s, %(type)s, %(libelle)s, "
            "%(emetteur)s, %(date_emission)s, %(date_validite_fin)s, %(reference)s, "
            "%(chemin)s, %(deposant)s, %(empreinte)s, %(taille)s, %(mime)s, %(sensibilite)s) "
            "RETURNING id",
            {
                "entreprise_id": entreprise_id,
                "fiche": fiche_version_id,
                "type": type_document,
                "libelle": libelle,
                "emetteur": emetteur,
                "date_emission": date_emission,
                "date_validite_fin": date_validite_fin,
                "reference": reference_document,
                "chemin": chemin_stockage,
                "deposant": deposant,
                "empreinte": empreinte_sha256,
                "taille": taille_octets,
                "mime": mime_type,
                "sensibilite": sensibilite,
            },
        )
        if ligne is None:  # pragma: no cover
            raise ErreurDepot("Création du document impossible.")
        return str(ligne["id"])

    def obtenir(self, contexte: ContexteClient, document_id: str) -> Optional[dict[str, Any]]:
        return self._connexion.executer_une(
            contexte,
            "SELECT id, entreprise_id, fiche_version_id, type_document, libelle, "
            "chemin_stockage, sensibilite FROM document "
            "WHERE client_id = %(client_id)s AND id = %(id)s",
            {"id": document_id},
        )


class DepotReference(DepotBase):
    """Accès **en lecture** aux jeux de référence — tables **globales** (I5).

    Ces deux tables ne portent aucun `client_id` : elles ne contiennent aucune donnée
    d'entreprise. Le SQL est figé et borné à ces deux tables ; c'est la troisième
    exception nommée du projet (les deux premières sont documentées par L1).
    """

    def _lire_global(self, sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Lecture d'une table **globale** (sans `client_id`). SQL figé, borné."""
        with self.connexion.brute.cursor() as cur:
            cur.execute(sql, dict(params))  # type: ignore[arg-type]
            if cur.description is None:  # pragma: no cover — lecture seule
                return []
            return [dict(ligne) for ligne in cur.fetchall()]

    def namespace_charge(self, namespace: str) -> bool:
        """Vrai si le jeu de référence est **chargé** dans cette base."""
        lignes = self._lire_global(
            "SELECT 1 AS present FROM jeu_reference "
            "WHERE namespace = %(n)s AND statut = 'actif'",
            {"n": namespace},
        )
        return bool(lignes)

    def code_actif(self, namespace: str, code: str) -> bool:
        """Vrai si le code existe et est actif **dans le jeu chargé**."""
        lignes = self._lire_global(
            "SELECT 1 AS present FROM valeur_reference "
            "WHERE namespace = %(n)s AND code = %(c)s AND statut = 'actif'",
            {"n": namespace, "c": code},
        )
        return bool(lignes)

    def lister_valeurs(self, namespace: str) -> list[dict[str, Any]]:
        return self._lire_global(
            "SELECT code, libelle, parent_code, ordre, domaine, source, statut "
            "FROM valeur_reference WHERE namespace = %(n)s AND statut = 'actif' "
            "ORDER BY ordre, code",
            {"n": namespace},
        )
