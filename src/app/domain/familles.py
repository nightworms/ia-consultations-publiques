"""Registre des entités de contenu — les familles F1 à F9 du modèle v2.

Ce module est la **table de correspondance unique** entre :

* le code de famille de `fiche.famille` (`docs/DATA-MODEL-V2.md` § 6.3) ;
* le nom logique d'entité de `tracabilite.entite` (§ 8.6) ;
* la table SQL correspondante (`src/migrations/0002_bibliotheque.sql`) ;
* les **champs saisissables** (liste blanche : aucun nom de colonne ne vient jamais
  de l'utilisateur — les noms de colonnes ne peuvent pas être paramétrés en SQL) ;
* le **champ d'échéance** à partir duquel `statut_validite` est **calculé** (§ 3.3) ;
* les **tables de liaison** des champs de type `liste` (§ 3.1).

Il ne dépend que de la bibliothèque standard (annexe A § A3) et ne contient aucune
règle de gestion : c'est un annuaire.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .securite import champs_chiffres

# --------------------------------------------------------------------------- #
# Les neuf familles de l'interface (§ 6.3)
# --------------------------------------------------------------------------- #

FAMILLE_IDENTITE = "identite"
FAMILLE_CAPACITES_FINANCIERES = "capacites_financieres"
FAMILLE_ASSURANCES = "assurances"
FAMILLE_CERTIFICATIONS = "certifications"
FAMILLE_REFERENCES_CHANTIERS = "references_chantiers"
FAMILLE_MOYENS_HUMAINS = "moyens_humains"
FAMILLE_MOYENS_MATERIELS = "moyens_materiels"
FAMILLE_FICHES_PRODUITS = "fiches_produits"
FAMILLE_MEMOIRE_TECHNIQUE = "memoire_technique"

LIBELLES_FAMILLES: dict[str, str] = {
    FAMILLE_IDENTITE: "Identité",
    FAMILLE_CAPACITES_FINANCIERES: "Capacités financières",
    FAMILLE_ASSURANCES: "Assurances",
    FAMILLE_CERTIFICATIONS: "Certifications et qualifications",
    FAMILLE_REFERENCES_CHANTIERS: "Références de chantiers",
    FAMILLE_MOYENS_HUMAINS: "Moyens humains",
    FAMILLE_MOYENS_MATERIELS: "Moyens matériels",
    FAMILLE_FICHES_PRODUITS: "Fiches techniques produits",
    FAMILLE_MEMOIRE_TECHNIQUE: "Mémoire technique type",
}


# --------------------------------------------------------------------------- #
# Définitions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Liaison:
    """Table de liaison d'un champ de type `liste` (§ 3.1)."""

    champ: str
    """Nom du champ côté saisie (ex. `photos`)."""

    table: str
    """Table de liaison (ex. `reference_chantier_photo`)."""

    colonne_proprietaire: str
    """Colonne pointant l'enregistrement propriétaire."""

    colonne_cible: str
    """Colonne pointant l'enregistrement listé."""


@dataclass(frozen=True)
class DefinitionEntite:
    """Une entité de contenu : sa famille, sa table, ses champs saisissables."""

    entite: str
    famille: str
    table: str
    libelle: str
    champs: tuple[str, ...]
    liaisons: tuple[Liaison, ...] = ()
    champ_echeance: Optional[str] = None
    """Champ (`date`) dont découle `statut_validite`, calculé à la lecture."""

    un_seul_par_fiche: bool = False
    """Vrai quand la fiche ne peut porter qu'un enregistrement de cette entité."""

    sensibilite_defaut: str = "interne"

    champs_obligatoires: tuple[str, ...] = ()

    @property
    def champs_chiffres(self) -> frozenset[str]:
        """Colonnes du registre sensible (annexe A § A6) — chiffrées par client."""
        return champs_chiffres(self.entite)

    def champ_autorise(self, champ: str) -> bool:
        return champ in self.champs or any(l.champ == champ for l in self.liaisons)


_ENTITES: tuple[DefinitionEntite, ...] = (
    # -- F1 : identité ------------------------------------------------------ #
    DefinitionEntite(
        entite="entreprise_version",
        famille=FAMILLE_IDENTITE,
        table="entreprise_version",
        libelle="Identité de l'entreprise (contenu versionné)",
        champs=(
            "raison_sociale",
            "siren",
            "siret_siege",
            "forme_juridique_code",
            "capital_social_montant",
            "capital_social_devise",
            "date_creation_entreprise",
            "code_ape_naf",
            "numero_tva_intracommunautaire",
            "adresse_siege",
            "adresse_etablissement_principal",
            "telephone",
            "email",
            "site_web",
            "effectif",
            "date_effectif",
            "effectif_source_code",
            "iban",
            "bic",
            "piece_rib",
        ),
        champ_echeance=None,
        un_seul_par_fiche=True,
        champs_obligatoires=("raison_sociale", "siren", "siret_siege", "forme_juridique_code", "adresse_siege"),
    ),
    DefinitionEntite(
        entite="representant_legal",
        famille=FAMILLE_IDENTITE,
        table="representant_legal",
        libelle="Représentant légal",
        champs=(
            "nom",
            "prenom",
            "fonction",
            "qualite_engagement",
            "date_nomination",
            "date_cessation",
            "statut",
            "piece",
        ),
        sensibilite_defaut="confidentiel",
        champs_obligatoires=("nom", "prenom", "fonction"),
    ),
    # -- F2 : capacités financières ----------------------------------------- #
    DefinitionEntite(
        entite="exercice_comptable",
        famille=FAMILLE_CAPACITES_FINANCIERES,
        table="exercice_comptable",
        libelle="Exercice comptable",
        champs=(
            "annee_exercice",
            "date_cloture",
            "chiffre_affaires_montant",
            "chiffre_affaires_devise",
            "resultat_net_montant",
            "resultat_net_devise",
            "capitaux_propres_montant",
            "capitaux_propres_devise",
            "total_bilan_montant",
            "total_bilan_devise",
            "effectif_moyen",
            "piece",
        ),
        champ_echeance=None,
        sensibilite_defaut="confidentiel",
        champs_obligatoires=("annee_exercice", "chiffre_affaires_montant", "chiffre_affaires_devise"),
    ),
    DefinitionEntite(
        entite="attestation",
        famille=FAMILLE_CAPACITES_FINANCIERES,
        table="attestation",
        libelle="Attestation justificative",
        champs=(
            "type_attestation",
            "emetteur",
            "date_emission",
            "date_validite_fin",
            "montant_engage_montant",
            "montant_engage_devise",
            "piece",
        ),
        champ_echeance="date_validite_fin",
        champs_obligatoires=("type_attestation", "emetteur", "date_emission", "piece"),
    ),
    DefinitionEntite(
        entite="capacite_production",
        famille=FAMILLE_CAPACITES_FINANCIERES,
        table="capacite_production",
        libelle="Capacité de production",
        champs=("description", "unite", "valeur", "commentaire"),
        champs_obligatoires=("description",),
    ),
    # -- F3 : assurances ---------------------------------------------------- #
    DefinitionEntite(
        entite="assurance",
        famille=FAMILLE_ASSURANCES,
        table="assurance",
        libelle="Contrat d'assurance",
        champs=(
            "type_assurance",
            "assureur",
            "numero_contrat",
            "montant_garantie_montant",
            "montant_garantie_devise",
            "franchise_montant",
            "franchise_devise",
            "date_debut",
            "date_echeance",
            "activites_couvertes",
            "piece",
        ),
        champ_echeance="date_echeance",
        champs_obligatoires=("type_assurance", "assureur", "date_debut", "date_echeance", "piece"),
    ),
    # -- F4 : certifications ------------------------------------------------ #
    DefinitionEntite(
        entite="certification",
        famille=FAMILLE_CERTIFICATIONS,
        table="certification",
        libelle="Certification ou qualification",
        champs=(
            "intitule",
            "organisme",
            "domaine_code",
            "numero_certificat",
            "date_obtention",
            "date_echeance",
            "piece",
        ),
        champ_echeance="date_echeance",
        champs_obligatoires=("intitule", "organisme", "domaine_code", "piece"),
    ),
    # -- F5 : références de chantiers --------------------------------------- #
    DefinitionEntite(
        entite="reference_chantier",
        famille=FAMILLE_REFERENCES_CHANTIERS,
        table="reference_chantier",
        libelle="Référence de chantier",
        champs=(
            "intitule_operation",
            "maitre_ouvrage",
            "nature_travaux_code",
            "nature_travaux_libelle",
            "lieu_commune",
            "lieu_departement",
            "date_debut",
            "date_fin",
            "montant_montant",
            "montant_devise",
            "duree_mois",
            "surface_traitee",
            "surface_unite",
            "description",
            "competences_appliquees",
            "attestation_bonne_execution",
            "contact_reference",
        ),
        liaisons=(
            Liaison("photos", "reference_chantier_photo", "reference_chantier_id", "document_id"),
        ),
        champs_obligatoires=("intitule_operation", "maitre_ouvrage"),
    ),
    # -- F6 : moyens humains ------------------------------------------------ #
    DefinitionEntite(
        entite="effectif_metier",
        famille=FAMILLE_MOYENS_HUMAINS,
        table="effectif_metier",
        libelle="Effectif par métier",
        champs=("metier_code", "metier_libelle", "nombre", "commentaire"),
        champs_obligatoires=("metier_code", "nombre"),
    ),
    DefinitionEntite(
        entite="organigramme",
        famille=FAMILLE_MOYENS_HUMAINS,
        table="organigramme",
        libelle="Organigramme",
        champs=("piece", "description", "date_maj"),
        un_seul_par_fiche=True,
    ),
    DefinitionEntite(
        entite="cv",
        famille=FAMILLE_MOYENS_HUMAINS,
        table="cv",
        libelle="CV d'un profil clé",
        champs=("nom", "prenom", "fonction", "diplomes", "annees_experience", "cv_piece"),
        sensibilite_defaut="confidentiel",
        champs_obligatoires=("nom", "prenom", "fonction", "cv_piece"),
    ),
    # -- F7 : moyens matériels ---------------------------------------------- #
    DefinitionEntite(
        entite="moyen_materiel",
        famille=FAMILLE_MOYENS_MATERIELS,
        table="moyen_materiel",
        libelle="Moyen matériel",
        champs=(
            "categorie_code",
            "designation",
            "quantite",
            "marque_modele",
            "annee",
            "propriete",
            "disponibilite",
            "justificatif",
        ),
        champs_obligatoires=("categorie_code", "designation", "quantite"),
    ),
    # -- F8 : fiches techniques produits ------------------------------------ #
    DefinitionEntite(
        entite="produit",
        famille=FAMILLE_FICHES_PRODUITS,
        table="produit",
        libelle="Produit et fiche technique",
        champs=(
            "fournisseur",
            "reference_produit",
            "designation",
            "famille_code",
            "domaine_application",
            "fiche_technique",
            "avis_technique",
            "date_validite_document",
        ),
        liaisons=(
            Liaison("certificats", "produit_certificat", "produit_id", "document_id"),
        ),
        champ_echeance="date_validite_document",
        champs_obligatoires=("fournisseur", "reference_produit", "designation"),
    ),
    # -- F9 : mémoire technique type ---------------------------------------- #
    DefinitionEntite(
        entite="chapitre_memoire",
        famille=FAMILLE_MEMOIRE_TECHNIQUE,
        table="chapitre_memoire",
        libelle="Chapitre du mémoire technique type",
        champs=("titre", "ordre", "contenu_texte", "statut", "date_redaction"),
        liaisons=(
            Liaison(
                "references_liees",
                "chapitre_memoire_reference",
                "chapitre_memoire_id",
                "reference_chantier_id",
            ),
            Liaison(
                "documents_associes",
                "chapitre_memoire_document",
                "chapitre_memoire_id",
                "document_id",
            ),
        ),
        champs_obligatoires=("titre", "ordre"),
    ),
)

#: Registre, clé = nom logique d'entité (`tracabilite.entite`).
REGISTRE_ENTITES: dict[str, DefinitionEntite] = {e.entite: e for e in _ENTITES}

#: Les entités d'une famille donnée, dans l'ordre du registre.
FAMILLE_VERS_ENTITES: dict[str, tuple[str, ...]] = {
    famille: tuple(e.entite for e in _ENTITES if e.famille == famille)
    for famille in LIBELLES_FAMILLES
}

#: Toutes les tables de contenu portées par une fiche (empreinte de validation).
TABLES_CONTENU: tuple[str, ...] = tuple(e.table for e in _ENTITES)

#: Tables de liaison (§ 3.1), avec leur propriétaire.
TABLES_LIAISON: tuple[tuple[str, str, str], ...] = tuple(
    (l.table, l.colonne_proprietaire, l.colonne_cible) for e in _ENTITES for l in e.liaisons
)

#: Entités regroupées par table (une table = une entité, sauf évolution future).
ENTITE_PAR_TABLE: dict[str, str] = {e.table: e.entite for e in _ENTITES}


#: Type de saisie des champs qui ne sont pas du texte, par entité puis par champ.
#: Absent de cette table = « texte ». Les champs chiffrés (annexe A § A6) sont
#: toujours « texte » : la valeur stockée est une charge `v1:<base64>`, et la
#: coercition de type (date, entier…) se fait dans le domaine, avant chiffrement.
TYPES_CHAMPS: dict[str, dict[str, str]] = {
    "entreprise_version": {
        "date_creation_entreprise": "date",
        "effectif": "entier",
        "date_effectif": "date",
        "capital_social_montant": "texte",  # chiffré
    },
    "representant_legal": {
        "date_cessation": "date",
        "date_nomination": "texte",  # chiffré
    },
    "exercice_comptable": {
        "annee_exercice": "entier",
        "date_cloture": "date",
        "effectif_moyen": "entier",
    },
    "attestation": {
        "date_emission": "date",
        "date_validite_fin": "date",
    },
    "capacite_production": {
        "valeur": "decimal",
    },
    "assurance": {
        "date_debut": "date",
        "date_echeance": "date",
        "montant_garantie_montant": "decimal",
        "franchise_montant": "decimal",
    },
    "certification": {
        "date_obtention": "date",
        "date_echeance": "date",
    },
    "reference_chantier": {
        "date_debut": "date",
        "date_fin": "date",
        "duree_mois": "entier",
        "surface_traitee": "decimal",
        "montant_montant": "texte",  # chiffré
    },
    "effectif_metier": {"nombre": "entier"},
    "organigramme": {"date_maj": "date"},
    "cv": {"annees_experience": "entier"},
    "moyen_materiel": {"quantite": "entier", "annee": "entier"},
    "produit": {"date_validite_document": "date"},
    "chapitre_memoire": {"ordre": "entier", "date_redaction": "date"},
}

#: Colonnes communes acceptées à l'écriture, en plus des champs métier.
COLONNES_COMMUNES_ACCEPTEES: tuple[str, ...] = (
    "origine",
    "confiance",
    "source_document_id",
    "sensibilite",
    "statut_enregistrement",
)


def type_champ(entite: str, champ: str) -> str:
    """Type de saisie d'un champ : `texte`, `date`, `entier` ou `decimal`."""
    return TYPES_CHAMPS.get(entite, {}).get(champ, "texte")


#: Jeu de référence attendu par un champ `code_reference`, quand il en a un.
#: Clé = (entité, champ). Un champ absent de cette table est du **texte libre**
#: (jamais un code) — c'est le cas des libellés et des identifiants.
#:
#: Règle de contrôle appliquée par le service : un code n'est **vérifié** que si le
#: jeu correspondant est **chargé** dans la base. Un jeu non chargé (contenu d'un
#: autre lot ou d'une source externe : `document.type_document`,
#: `entreprise.forme_juridique`, `assurance.type`, `attestation.type`,
#: `certification.domaine`, `moyen.categorie`, `produit.famille`,
#: `reference.nature_travaux`, `metier.*`…) ne peut pas être contrôlé : sa valeur est
#: acceptée telle quelle, et **aucune valeur n'est inventée** pour le remplir (D2).
JEUX_PAR_CHAMP: dict[tuple[str, str], str] = {
    ("entreprise_version", "forme_juridique_code"): "entreprise.forme_juridique",
    ("entreprise_version", "effectif_source_code"): "rh.origine_effectif",
    ("representant_legal", "statut"): "rh.statut_mandat",
    ("attestation", "type_attestation"): "attestation.type",
    ("assurance", "type_assurance"): "assurance.type",
    ("certification", "domaine_code"): "certification.domaine",
    ("reference_chantier", "nature_travaux_code"): "reference.nature_travaux",
    ("moyen_materiel", "categorie_code"): "moyen.categorie",
    ("moyen_materiel", "propriete"): "moyen.propriete",
    ("produit", "famille_code"): "produit.famille",
    ("chapitre_memoire", "statut"): "memoire.statut_chapitre",
}

#: Jeux fermés applicables à toute entité de contenu, par nom de champ commun.
JEUX_COMMUNS: dict[str, str] = {
    "origine": "tracabilite.origine",
    "confiance": "tracabilite.confiance",
    "sensibilite": "securite.sensibilite",
    "statut_enregistrement": "commun.statut_enregistrement",
}


def reference_attendue(entite: str, champ: str) -> Optional[str]:
    """Namespace du jeu de référence attendu par un champ, ou `None` (texte libre)."""
    return JEUX_PAR_CHAMP.get((entite, champ)) or JEUX_COMMUNS.get(champ)


def definition_entite(entite: str) -> DefinitionEntite:
    """Renvoie la définition d'une entité, ou lève une erreur explicite."""
    try:
        return REGISTRE_ENTITES[entite]
    except KeyError as exc:
        raise KeyError(
            f"Entité inconnue : {entite!r}. Connues : {sorted(REGISTRE_ENTITES)}"
        ) from exc


def definition_famille(famille: str) -> tuple[DefinitionEntite, ...]:
    """Renvoie les définitions des entités d'une famille."""
    if famille not in FAMILLE_VERS_ENTITES:
        raise KeyError(
            f"Famille inconnue : {famille!r}. Connues : {sorted(FAMILLE_VERS_ENTITES)}"
        )
    return tuple(REGISTRE_ENTITES[e] for e in FAMILLE_VERS_ENTITES[famille])


def famille_de_entite(entite: str) -> str:
    return definition_entite(entite).famille
