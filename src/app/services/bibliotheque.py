"""Service — bibliothèque d'entreprise : saisie et consultation.

Implémente les points d'entrée de la brique A : saisir un élément dans une famille,
consulter une famille, connaître l'avancement de la fiche, et déposer une pièce.

Règles appliquées **à l'écriture** (aucune n'est optionnelle) :

* **aucune valeur sans origine** : `origine` est exigée, et n'accepte que
  `document_extrait` ou `saisie_entreprise` (§ 7.5 règle 4, ligne rouge annexe A § A9) ;
* `origine = document_extrait` **exige** un `source_document_id` ;
* `confiance = verifie` exige une source **et** un contrôle humain nommé : aucune
  valeur sans source n'est « vérifiée », elle est au mieux `a_verifier` ;
* un `code_reference` n'est accepté que s'il existe et est **actif** dans son jeu —
  et seulement si ce jeu est chargé dans la base (sinon aucun contrôle n'est
  possible, et aucune valeur n'est inventée pour le remplir) ;
* **toute écriture révoque** les validations qui couvrent la famille écrite (§ 6.5) ;
* aucun prix, aucune marge, aucune garantie de conformité nulle part.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from app.domain.commun import (
    Confiance,
    ErreurTracabilite,
    Origine,
    Sensibilite,
    StatutEnregistrement,
    appliquer_regles_tracabilite,
    calculer_statut_validite,
    confiance_recevable,
)
from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    DefinitionEntite,
    definition_entite,
    reference_attendue,
)
from app.services.versionnement import (
    ServiceVersionnement,
    fenetre_alerte_jours_depuis_environnement,
)
from app.storage.connexion import Connexion, ContexteClient
from app.storage.repositories import (
    DepotEntreprise,
    DepotReference,
    ErreurDepot,
    depot_contenu,
)


class ErreurBibliotheque(RuntimeError):
    """Saisie ou consultation refusée (règle de traçabilité, code inconnu…)."""


def _champs_montant(definition: DefinitionEntite) -> dict[str, tuple[str, str]]:
    """Champs de type `montant`, repérés par convention `<nom>_montant`/`<nom>_devise`."""
    montants: dict[str, tuple[str, str]] = {}
    for champ in definition.champs:
        if champ.endswith("_montant"):
            base = champ[: -len("_montant")]
            if f"{base}_devise" in definition.champs:
                montants[base] = (champ, f"{base}_devise")
    return montants


class ServiceBibliotheque:
    """Saisie et consultation de la bibliothèque d'entreprise, cloisonnées par client."""

    def __init__(
        self,
        connexion: Connexion,
        cle_maitresse: bytes,
        contexte: ContexteClient,
        fenetre_alerte_jours: Optional[int] = None,
    ) -> None:
        self._connexion = connexion
        self._cle = cle_maitresse
        self._contexte = contexte
        self.versionnement = ServiceVersionnement(connexion, cle_maitresse, contexte)
        self.entreprises = DepotEntreprise(connexion, cle_maitresse)
        self.references = DepotReference(connexion, cle_maitresse)
        self._fenetre = (
            fenetre_alerte_jours
            if fenetre_alerte_jours is not None
            else fenetre_alerte_jours_depuis_environnement()
        )

    # -- provisionnement (racines) ------------------------------------------ #
    def creer_entreprise(self, libelle_court: str) -> str:
        """Crée l'ancre stable `entreprise` du client courant (§ 5.3)."""
        return self.entreprises.creer(self._contexte, libelle_court)

    def ouvrir_fiche(self, entreprise_id: str, *, commentaire: Optional[str] = None) -> dict[str, Any]:
        """Ouvre une nouvelle `fiche_version` (numéro croissant par entreprise)."""
        return self.versionnement.creer_version(entreprise_id, commentaire=commentaire)

    def dernieres_fiches(self, entreprise_id: str) -> list[dict[str, Any]]:
        return self.versionnement.fiches.lister_pour_entreprise(self._contexte, entreprise_id)

    def fiche_courante(self) -> Optional[dict[str, Any]]:
        """Version la plus récente du client, ou `None` (jamais celle d'un autre)."""
        return self.versionnement.fiches.derniere_pour_client(self._contexte)

    # -- consultation ------------------------------------------------------- #
    def etat_avancement(self, fiche_version_id: str) -> dict[str, Any]:
        """État d'avancement par famille (§ 6.2, § 6.3), plus le contrôle I6."""
        return self.versionnement.etat_fiche(fiche_version_id)

    def consulter_famille(self, famille: str, fiche_version_id: str) -> dict[str, Any]:
        """Contenu d'une famille, avec traçabilité de chaque enregistrement."""
        if famille not in FAMILLE_VERS_ENTITES:
            raise ErreurBibliotheque(
                f"Famille inconnue : {famille!r}. Connues : {sorted(FAMILLE_VERS_ENTITES)}"
            )
        fiche = self.versionnement.fiche(fiche_version_id)
        elements: dict[str, list[dict[str, Any]]] = {}
        for entite in FAMILLE_VERS_ENTITES[famille]:
            definition = definition_entite(entite)
            depot = depot_contenu(self._connexion, self._cle, entite)
            lignes = depot.lister(self._contexte, fiche_version_id)
            for ligne in lignes:
                for liaison in definition.liaisons:
                    ligne[liaison.champ] = depot.lire_liaisons(
                        self._contexte, str(ligne["id"]), liaison.champ
                    )
                if definition.champ_echeance:
                    ligne["statut_validite"] = calculer_statut_validite(
                        ligne.get(definition.champ_echeance),
                        fenetre_alerte_jours=self._fenetre,
                    ).value
            elements[entite] = lignes
        return {
            "fiche_version_id": fiche_version_id,
            "famille": famille,
            "libelle": LIBELLES_FAMILLES[famille],
            "entites": list(FAMILLE_VERS_ENTITES[famille]),
            "elements": elements,
            "fenetre_alerte_jours": self._fenetre,
            "statut_fiche": self.versionnement.statut_fiche(fiche_version_id),
        }

    # -- écriture ----------------------------------------------------------- #
    def saisir(
        self,
        famille: str,
        entite: str,
        fiche_version_id: str,
        donnees: Mapping[str, Any],
        *,
        element_id: Optional[str] = None,
        controle_humain_par: Optional[str] = None,
    ) -> dict[str, Any]:
        """Saisit (ou modifie) un élément d'une famille. Révoque toute validation.

        `controle_humain_par` est le **nom de l'humain** qui a contrôlé la valeur :
        il n'est exigé que pour `confiance = verifie`, et il n'existe aucun chemin
        automatique qui pose cette confiance.
        """
        definition = definition_entite(entite)
        if definition.famille != famille:
            raise ErreurBibliotheque(
                f"L'entité {entite!r} appartient à la famille {definition.famille!r}, "
                f"pas à {famille!r}."
            )
        if not isinstance(donnees, Mapping) or not donnees:
            raise ErreurBibliotheque("Aucune donnée à saisir.")

        fiche = self.versionnement.fiche(fiche_version_id)
        if fiche["statut"] == "archivee":
            raise ErreurBibliotheque(
                "Version archivée : une correction passe par une **nouvelle** version "
                "(§ 6.1 règle 1). Aucune écriture n'est acceptée ici."
            )

        valeurs = dict(donnees)
        valeurs = self._eclater_montants(definition, valeurs)
        valeurs = self._normaliser_tracabilite(valeurs, controle_humain_par)
        self._verifier_codes_reference(entite, valeurs)
        self._verifier_champs_obligatoires(definition, valeurs, modification=element_id is not None)

        valeurs, liaisons = self._separer_liaisons(definition, valeurs)

        depot = depot_contenu(self._connexion, self._cle, entite)
        try:
            if element_id is not None:
                if depot.obtenir(self._contexte, element_id) is None:
                    raise ErreurBibliotheque(
                        f"Élément introuvable pour ce client : {element_id!r} (lecture refusée)."
                    )
                depot.modifier(self._contexte, element_id, valeurs)
                cible = element_id
            else:
                existant = self._element_unique(definition, fiche_version_id)
                if definition.un_seul_par_fiche and existant is not None:
                    # Un enregistrement par fiche (ex. l'identité) : on le met à jour
                    # plutôt que d'en créer un second.
                    depot.modifier(self._contexte, str(existant["id"]), valeurs)
                    cible = str(existant["id"])
                else:
                    cible = depot.creer(
                        self._contexte,
                        entreprise_id=str(fiche["entreprise_id"]),
                        fiche_version_id=fiche_version_id,
                        valeurs=valeurs,
                    )
            for champ, ids in liaisons.items():
                depot.remplacer_liaisons(self._contexte, cible, champ, ids)
        except ErreurDepot as exc:
            raise ErreurBibliotheque(str(exc)) from exc

        ecriture = self.versionnement.enregistrer_ecriture(
            fiche_version_id, famille_code=famille
        )
        return {
            "element_id": cible,
            "entite": entite,
            "famille": famille,
            "fiche_version_id": fiche_version_id,
            "validations_revoquees": ecriture["validations_revoquees"],
            "statut_fiche": ecriture["statut"],
        }

    def archiver_element(self, entite: str, element_id: str, fiche_version_id: str) -> dict[str, Any]:
        """Archive un élément (jamais de suppression en dur, § 3.2)."""
        definition = definition_entite(entite)
        depot = depot_contenu(self._connexion, self._cle, entite)
        if depot.obtenir(self._contexte, element_id) is None:
            raise ErreurBibliotheque(
                f"Élément introuvable pour ce client : {element_id!r} (lecture refusée)."
            )
        depot.archiver(self._contexte, element_id)
        ecriture = self.versionnement.enregistrer_ecriture(
            fiche_version_id, famille_code=definition.famille
        )
        return {
            "element_id": element_id,
            "entite": entite,
            "archive": True,
            "validations_revoquees": ecriture["validations_revoquees"],
            "statut_fiche": ecriture["statut"],
        }

    # -- validation humaine -------------------------------------------------- #
    def valider_fiche(
        self,
        fiche_version_id: str,
        *,
        relecteur_nom: str,
        attestation_cochee: bool,
        cible_type: str = "fiche",
        famille_code: Optional[str] = None,
        commentaire: Optional[str] = None,
    ) -> dict[str, Any]:
        """Le verrou humain (§ 6.4) — nom du relecteur + attestation cochée (§ 7)."""
        return self.versionnement.valider(
            fiche_version_id,
            relecteur_nom=relecteur_nom,
            attestation_cochee=attestation_cochee,
            cible_type=cible_type,
            famille_code=famille_code,
            commentaire=commentaire,
        )

    # -- internes ----------------------------------------------------------- #
    def _element_unique(
        self, definition: DefinitionEntite, fiche_version_id: str
    ) -> Optional[dict[str, Any]]:
        if not definition.un_seul_par_fiche:
            return None
        depot = depot_contenu(self._connexion, self._cle, definition.entite)
        lignes = depot.lister(self._contexte, fiche_version_id)
        return lignes[0] if lignes else None

    @staticmethod
    def _separer_liaisons(
        definition: DefinitionEntite, valeurs: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[str]]]:
        """Sort les champs de type `liste` : ils vivent dans une table de liaison."""
        restant: dict[str, Any] = {}
        liaisons: dict[str, list[str]] = {}
        noms = {liaison.champ for liaison in definition.liaisons}
        for champ, valeur in valeurs.items():
            if champ in noms:
                if valeur is None:
                    liaisons[champ] = []
                elif isinstance(valeur, (list, tuple)):
                    liaisons[champ] = [str(v) for v in valeur]
                else:
                    raise ErreurBibliotheque(
                        f"Le champ {champ!r} attend une liste d'identifiants."
                    )
            else:
                restant[champ] = valeur
        return restant, liaisons

    @staticmethod
    def _eclater_montants(
        definition: DefinitionEntite, valeurs: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Accepte `{'montant': {'valeur':…, 'devise':…}}` et l'éclate en deux colonnes."""
        sortie = dict(valeurs)
        for base, (col_montant, col_devise) in _champs_montant(definition).items():
            charge = sortie.get(base)
            if isinstance(charge, Mapping):
                sortie.pop(base)
                sortie[col_montant] = charge.get("valeur")
                sortie[col_devise] = charge.get("devise")
        return sortie

    @staticmethod
    def _normaliser_tracabilite(
        valeurs: Mapping[str, Any], controle_humain_par: Optional[str]
    ) -> dict[str, Any]:
        """Applique les règles de traçabilité : origine obligatoire, confiance bornée."""
        sortie = dict(valeurs)
        origine = sortie.get("origine")
        if origine in (None, ""):
            raise ErreurBibliotheque(
                "Aucune valeur n'est enregistrée sans `origine` (§ 7.5 règle 4). "
                "Valeurs acceptées : 'document_extrait' ou 'saisie_entreprise'."
            )
        origine = str(origine)
        if origine not in {o.value for o in Origine}:
            raise ErreurBibliotheque(
                f"Origine refusée : {origine!r}. Seules "
                f"{sorted(o.value for o in Origine)} sont acceptées — jamais une valeur "
                "« générée par l'IA » (ligne rouge, annexe A § A9). L'origine « mixte » "
                "est un résumé **calculé** (§ 7.4), jamais une valeur saisie."
            )
        source = sortie.get("source_document_id") or None
        confiance = str(sortie.get("confiance") or Confiance.A_VERIFIER.value)
        try:
            appliquer_regles_tracabilite(
                origine=origine, confiance=confiance, source_document_id=source
            )
            confiance = confiance_recevable(
                origine=origine,
                confiance=confiance,
                source_document_id=source,
                controle_humain_par=controle_humain_par,
            )
        except ErreurTracabilite as exc:
            raise ErreurBibliotheque(str(exc)) from exc
        sortie["origine"] = origine
        sortie["confiance"] = confiance
        sortie["source_document_id"] = source
        if "sensibilite" in sortie and sortie["sensibilite"] is not None:
            if sortie["sensibilite"] not in {s.value for s in Sensibilite}:
                raise ErreurBibliotheque(
                    f"Sensibilité invalide : {sortie['sensibilite']!r} — attendu "
                    f"{sorted(s.value for s in Sensibilite)}"
                )
        if "statut_enregistrement" in sortie and sortie["statut_enregistrement"] is not None:
            if sortie["statut_enregistrement"] not in {s.value for s in StatutEnregistrement}:
                raise ErreurBibliotheque(
                    f"Statut d'enregistrement invalide : {sortie['statut_enregistrement']!r}"
                )
        return sortie

    def _verifier_codes_reference(self, entite: str, valeurs: Mapping[str, Any]) -> None:
        """Un `code_reference` doit exister et être actif — si son jeu est chargé."""
        for champ, valeur in valeurs.items():
            if valeur is None:
                continue
            namespace = reference_attendue(entite, champ)
            if not namespace:
                continue
            if not self.references.namespace_charge(namespace):
                # Jeu non chargé : contenu d'un autre lot ou d'une source externe.
                # Aucune valeur n'est inventée pour le remplir (D2) ; on ne peut donc
                # pas contrôler le code, et on l'accepte tel quel.
                continue
            if not self.references.code_actif(namespace, str(valeur)):
                raise ErreurBibliotheque(
                    f"Valeur {valeur!r} refusée pour le champ {champ!r} : code inconnu "
                    f"ou déprécié dans le jeu {namespace!r}."
                )

    @staticmethod
    def _verifier_champs_obligatoires(
        definition: DefinitionEntite, valeurs: Mapping[str, Any], *, modification: bool
    ) -> None:
        if modification:
            vides = [
                champ
                for champ in definition.champs_obligatoires
                if champ in valeurs and valeurs[champ] in (None, "")
            ]
        else:
            vides = [
                champ
                for champ in definition.champs_obligatoires
                if valeurs.get(champ) in (None, "")
            ]
        if vides:
            raise ErreurBibliotheque(
                f"Champs obligatoires manquants pour {definition.entite!r} : {vides}"
            )


def fenetre_alerte_jours_depuis_env() -> Optional[int]:
    """Alias public de la lecture de `FENETRE_ALERTE_JOURS` (réglage, pas un seuil)."""
    return fenetre_alerte_jours_depuis_environnement()
