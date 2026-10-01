"""Service — moteur de génération du mémoire technique (lot L2, phase 4).

Objectif : **aider à écrire ce qui convaincra le jury**. Le moteur structure un
mémoire technique à partir de deux matières : les **critères d'attribution du DCE**
(déjà extraits et validés par la brique B) et la **bibliothèque d'entreprise** du client.

Règle centrale de la phase (`docs/PLAN-PHASE-4.md` § 2.B), tenue par du code ici :

* le plan suit les critères du DCE **dans l'ordre de pondération décroissante** ; le
  critère le plus lourd ouvre le mémoire et reçoit le développement le plus long ;
  un critère **sans pondération connue** passe en fin, avec sa raison affichée ;
* une section n'existe **que** si elle porte au moins une source pointant un élément de
  bibliothèque **du même `client_id`** ; sinon elle devient un **manque** (constat +
  action à mener) — les manques sont un **résultat**, pas une erreur ;
* **le contrôle de source existant est réutilisé, jamais réécrit** :
  `app.services.fournisseur_modele.base.source_presente` est appliqué tel quel, avec
  `memoire_section_source` comme support. Une source non vérifiable est **refusée
  explicitement** (`SourceMemoireInvalide`) et la section est transformée en manque ;
* **aucun prix, aucun chiffre inventé, aucune conformité promise** : le critère de prix
  ne produit jamais de section (il est hors périmètre du mémoire) ; aucune valeur de prix
  n'y figure ;
* **tout sort en `brouillon`** ; aucun statut validé (section ou dossier) n'est posé par
  du code sans une action humaine **nommée et horodatée** ; la validation finale écrit une
  ligne `memoire_validation` avec l'empreinte SHA-256 du contenu validé ;
* **isolation par client** : tout le SQL passe par `storage.connexion.Connexion` (filtre
  `client_id` imposé par le contexte de session) et aucune source d'un autre client
  n'alimente un mémoire.

La composition du texte est **déterministe et sans réseau** : elle n'écrit que des phrases
dont chaque valeur vient d'un champ réel de la bibliothèque. Le fournisseur de modèle
(décision D8) n'est **pas** appelé pour rédiger — un fournisseur factice ne sait pas
argumenter, et un modèle réel reste derrière l'adaptateur, hors de ce chemin. Les limites
assumées sont écrites dans `docs/MEMOIRE-TECHNIQUE.md`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import uuid
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.domain.commun import confiance_la_plus_faible
from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    definition_entite,
)
from app.domain.memoire_technique_genere import (
    ACTION_PRIX_HORS_MEMOIRE,
    ACTIONS_MANQUE,
    AVERTISSEMENT_GENERATION,
    CONSTAT_MANQUE_AUCUNE_REFERENCE,
    CONSTAT_PRIX_HORS_MEMOIRE,
    FAMILLES_MEMOIRE,
    MENTION_BROUILLON,
    STATUTS_SECTION,
    TRANSITIONS_SECTION,
    ManqueMemoire,
    SectionMemoire,
    SourceMemoire,
    constat_manque_sujet,
    correspondance_pour_critere,
    couverture_sujet,
    est_critere_prix,
    familles_pour_critere,
    poids_depuis_valeur,
)
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.extraction_pdf import PageExtraite
from app.services.fournisseur_modele.base import PropositionElement, source_presente
from app.storage.connexion import Connexion, ContexteClient

#: Journal du module.
LOGGER = logging.getLogger(__name__)

#: Colonnes techniques qui ne sont **jamais** citées comme contenu (elles ne portent pas
#: d'affirmation métier et pourraient exposer un identifiant interne).
COLONNES_TECHNIQUES: frozenset[str] = frozenset(
    {
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
    }
)

#: Seuils de développement d'une section, **dérivés de la pondération** (défaut retenu en
#: § 6 question 1 : développement proportionnel au poids, chaque section portant sa
#: longueur visible). Un poids inconnu donne un développement « essentiel ».
SEUIL_DEVELOPPEMENT_COMPLET = Decimal("30")
SEUIL_DEVELOPPEMENT_ESSENTIEL = Decimal("10")

#: Nombre maximal de caractères repris d'un chapitre de mémoire type cité comme source.
LONGUEUR_EXTRAIT_CHAPITRE = 800


class ErreurMemoire(RuntimeError):
    """La génération ou la gestion du mémoire ne peut pas aboutir. Toujours explicite."""


class MemoireIntrouvable(ErreurMemoire):
    """Consultation, dossier ou section inexistant **pour ce client** (jamais d'indice)."""


class SourceMemoireInvalide(ErreurMemoire):
    """Une source de section n'est pas vérifiable dans la bibliothèque du client.

    Ce **n'est pas** un incident : c'est le résultat attendu du garde-fou anti-invention
    (`source_presente`, réutilisé tel quel). La section concernée ne doit **jamais** être
    produite : elle est transformée en manque. `table_source` et `element_id` portent,
    quand ils sont connus, l'élément mis en cause.
    """

    def __init__(
        self,
        message: str,
        *,
        table_source: Optional[str] = None,
        element_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.table_source = table_source
        self.element_id = element_id


# --------------------------------------------------------------------------- #
# Lecture des entrées
# --------------------------------------------------------------------------- #
def _lire_consultation(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> dict[str, Any]:
    consultation = connexion.executer_une(
        contexte,
        "SELECT * FROM consultation WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": consultation_id},
    )
    if consultation is None:
        raise MemoireIntrouvable("Consultation introuvable pour ce client.")
    return consultation


def _lire_fiche(
    connexion: Connexion, contexte: ContexteClient, fiche_version_id: Optional[str]
) -> dict[str, Any]:
    """La fiche demandée, ou la plus récente du client. Jamais celle d'un autre."""
    if fiche_version_id:
        fiche = connexion.executer_une(
            contexte,
            "SELECT * FROM fiche_version WHERE client_id = %(client_id)s AND id = %(id)s;",
            {"id": fiche_version_id},
        )
        if fiche is None:
            raise MemoireIntrouvable(
                "Version de fiche introuvable pour ce client : un mémoire ne s'adosse "
                "qu'à la bibliothèque du client de la session."
            )
        return fiche
    fiche = connexion.executer_une(
        contexte,
        "SELECT * FROM fiche_version WHERE client_id = %(client_id)s "
        "ORDER BY numero_version DESC, date_creation DESC LIMIT 1;",
    )
    if fiche is None:
        raise ErreurMemoire(
            "Aucune version de fiche pour ce client : le mémoire s'adosse à votre "
            "bibliothèque ; sans fiche, il n'y a rien à citer."
        )
    return fiche


def _criteres_valides(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> list[dict[str, Any]]:
    """Les **critères d'attribution validés** du DCE — seuls les `valide` font le plan.

    Même verrou que la checklist (`docs/SPEC-MVP-V2.md` § 2, verrou n° 2) : un critère
    encore `propose` n'est pas utilisable. Le plan suit la notation du DCE, pas une
    lecture automatique non contrôlée.
    """
    return connexion.executer(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s AND categorie = 'critere' "
        "AND statut_verification = 'valide' "
        "ORDER BY date_verification, date_extraction, id;",
        {"consultation_id": consultation_id},
    )


# --------------------------------------------------------------------------- #
# Rendus d'un élément de bibliothèque — la « page » adossée à chaque source
# --------------------------------------------------------------------------- #
def _valeur_lisible(valeur: Any) -> str:
    """Rend une valeur de bibliothèque en texte — **jamais un identifiant interne**.

    Les valeurs de type UUID (clés étrangères : pièces jointes, avis technique, photos)
    et les listes de UUID sont **écartées** : un mémoire technique ne contient aucun
    identifiant technique. Ce sont des références à des documents, pas du contenu.
    """
    if valeur is None:
        return ""
    if isinstance(valeur, uuid.UUID):
        return ""
    if isinstance(valeur, (list, tuple)):
        morceaux = [
            _valeur_lisible(v)
            for v in valeur
            if not isinstance(v, uuid.UUID) and v not in (None, "")
        ]
        return ", ".join(m for m in morceaux if m)
    if isinstance(valeur, _dt.datetime):
        return valeur.strftime("%d/%m/%Y")
    if isinstance(valeur, _dt.date):
        return valeur.strftime("%d/%m/%Y")
    return str(valeur)


#: Champs qui portent un **code de nomenclature** (jamais un libellé saisi par le client).
#: Leur valeur ne sort **jamais telle quelle** du générateur : elle est rendue lisible par
#: `_code_lisible`. Source : `app.domain.familles.JEUX_PAR_CHAMP` (colonnes `code_reference`)
#: et les champs `*_code` du modèle. Un code de nomenclature n'est ni un mot, ni un libellé.
CHAMPS_CODE: frozenset[str] = frozenset(
    {
        "categorie_code",
        "metier_code",
        "forme_juridique_code",
        "effectif_source_code",
        "famille_code",
        "nature_travaux_code",
        "domaine_code",
        "type_assurance",
        "type_attestation",
        "type_document",
        "propriete",
        "statut",
    }
)

#: Libellés métier des statuts de validité calculés (`app.domain.commun.StatutValidite`).
#: Un mémoire dit « échéance dépassée », jamais `[expire]` : le code ne sort pas du
#: générateur, il est traduit.
LIBELLES_VALIDITE: dict[str, str] = {
    "valide": "valide",
    "echeance_proche": "échéance proche",
    "expire": "échéance dépassée",
    "non_renseigne": "validité non renseignée",
}


def _code_lisible(valeur: Any) -> str:
    """Rend un **code de nomenclature** lisible — jamais en tirets bas ni en points.

    `materiel_mise_en_oeuvre` → « materiel mise en oeuvre », `metier.etancheite` →
    « metier etancheite » : un code sans libellé disponible ne sort donc jamais tel quel
    du générateur. Une valeur qui n'est pas un code est rendue inchangée (aucune valeur
    n'est inventée ni complétée).
    """
    texte = _valeur_lisible(valeur).strip()
    if not texte or ("_" not in texte and "." not in texte):
        return texte
    return " ".join(texte.replace("_", " ").replace(".", " ").split())


def _libelle_validite(valeur: Any) -> str:
    """Le statut de validité **dit en métier** (« échéance dépassée »), jamais en code."""
    code = str(valeur or "").strip()
    if not code:
        return ""
    return LIBELLES_VALIDITE.get(code, _code_lisible(code))


def _valeur_champ(champ: str, valeur: Any) -> str:
    """Rend la valeur d'un champ : code de nomenclature → lisible, sinon tel quel."""
    if champ in CHAMPS_CODE:
        return _code_lisible(valeur)
    return _valeur_lisible(valeur)


def _champs_libelle(table: str) -> tuple[str, ...]:
    """Champs servant de libellé lisible, par table, du plus parlant au moins parlant."""
    return _CHAMPS_LIBELLE.get(table, ())


_CHAMPS_LIBELLE: dict[str, tuple[str, ...]] = {
    "entreprise_version": ("raison_sociale", "siren"),
    "representant_legal": ("nom", "prenom", "fonction"),
    "exercice_comptable": ("annee_exercice",),
    "attestation": ("type_attestation", "emetteur"),
    "capacite_production": ("description",),
    "assurance": ("type_assurance", "assureur"),
    "certification": ("intitule", "organisme"),
    "reference_chantier": ("intitule_operation", "maitre_ouvrage"),
    "effectif_metier": ("metier_libelle", "metier_code"),
    "organigramme": ("description", "piece"),
    "cv": ("nom", "prenom", "fonction"),
    "moyen_materiel": ("designation", "categorie_code"),
    "produit": ("designation", "reference_produit", "fournisseur"),
    "chapitre_memoire": ("titre",),
}

#: Libellé d'une table, pour un rendu lisible (jamais un nom de code à l'écran).
_LIBELLE_TABLE: dict[str, str] = {
    "entreprise_version": "identité de l'entreprise",
    "representant_legal": "représentant légal",
    "exercice_comptable": "exercice comptable",
    "attestation": "attestation justificative",
    "capacite_production": "capacité de production",
    "assurance": "contrat d'assurance",
    "certification": "certification",
    "reference_chantier": "référence de chantier",
    "effectif_metier": "effectif par métier",
    "organigramme": "organigramme",
    "cv": "profil clé (CV)",
    "moyen_materiel": "moyen matériel",
    "produit": "produit / fiche technique",
    "chapitre_memoire": "chapitre de mémoire type",
}


def _lignes_element(table: str, element: Mapping[str, Any]) -> list[str]:
    """Rend un élément de bibliothèque en lignes « champ : valeur » (jamais inventées).

    Un champ de **code de nomenclature** y est rendu lisible (`_code_lisible`) : ces
    lignes servent de « page » au générateur et à la vérification de source, un code
    n'y a donc pas sa place en tirets bas.
    """
    lignes: list[str] = []
    for champ, valeur in element.items():
        if champ in COLONNES_TECHNIQUES:
            continue
        rendu = _valeur_champ(champ, valeur)
        if rendu:
            lignes.append(f"{champ} : {rendu}")
    return lignes


def libelle_source(table: str, element: Mapping[str, Any]) -> str:
    """Libellé lisible d'un élément, tiré d'un de ses champs réels (jamais inventé).

    Les champs de **libellé métier** (`designation`, `metier_libelle`, `intitule`, …) sont
    utilisés en priorité : un code de nomenclature n'a rien à faire dans le libellé d'une
    source. Les champs de **code** (`categorie_code`, `metier_code`, …) ne servent que de
    repli — quand aucun libellé n'est disponible — et sont alors rendus lisibles
    (`materiel_mise_en_oeuvre` → « materiel mise en oeuvre »).
    """
    champs = _champs_libelle(table)
    libelles = [c for c in champs if c not in CHAMPS_CODE]
    codes = [c for c in champs if c in CHAMPS_CODE]
    morceaux = [v for v in (_valeur_lisible(element.get(c)) for c in libelles) if v]
    if not morceaux:
        morceaux = [v for v in (_code_lisible(element.get(c)) for c in codes) if v]
    base = " ".join(morceaux) if morceaux else _LIBELLE_TABLE.get(table, table)
    return base[:255]


def _m(*pieces: str) -> str:
    """Assemble des morceaux non vides par une virgule — n'invente aucun segment."""
    return ", ".join(p for p in pieces if p)


def _phrase_element(table: str, element: Mapping[str, Any], niveau: str) -> str:
    """Une phrase **factuelle** par élément, construite uniquement de champs réels.

    `niveau` (`complet`, `essentiel`, `mention`) règle le développement, conformément au
    défaut « proportionnel au poids » du plan : plus le critère est lourd, plus la phrase
    mobilise de champs réels. Aucune valeur n'est ajoutée, complétée ni estimée.
    """
    if niveau == "mention":
        return (
            f"{_LIBELLE_TABLE.get(table, table)} « {libelle_source(table, element)} » "
            "— élément de votre bibliothèque."
        )
    complet = niveau == "complet"
    g = lambda c: _valeur_champ(c, element.get(c))  # noqa: E731 — raccourci de lecture

    def _bloc(entete: str, *details: str) -> str:
        morceaux = _m(*details).rstrip()
        if not morceaux:
            return f"{entete}."
        # On n'ajoute pas de point si le dernier morceau en porte déjà un (valeur réelle).
        fin = "" if morceaux.endswith((".", "!", "?")) else "."
        return f"{entete} — {morceaux}{fin}"

    if table == "entreprise_version":
        return _bloc(
            f"Entreprise {g('raison_sociale')}",
            g("forme_juridique_code"),
            f"SIREN {g('siren')}" if g("siren") else "",
            g("adresse_siege"),
            f"effectif {g('effectif')}" if g("effectif") else "",
            f"site {g('site_web')}" if complet and g("site_web") else "",
        )
    if table == "representant_legal":
        return f"Représentant légal : {_m(g('prenom'), g('nom'))}, {g('fonction')}."
    if table == "exercice_comptable":
        return _bloc(
            f"Exercice {g('annee_exercice')}",
            f"chiffre d'affaires {g('chiffre_affaires_montant')} "
            f"{g('chiffre_affaires_devise')}".strip()
            if g("chiffre_affaires_montant")
            else "",
            f"résultat net {g('resultat_net_montant')} {g('resultat_net_devise')}".strip()
            if g("resultat_net_montant")
            else "",
            f"capitaux propres {g('capitaux_propres_montant')}".strip()
            if complet and g("capitaux_propres_montant")
            else "",
            f"effectif moyen {g('effectif_moyen')}"
            if complet and g("effectif_moyen")
            else "",
        )
    if table == "attestation":
        return _bloc(
            f"Attestation {g('type_attestation')}"
            + (f" ({g('emetteur')})" if g("emetteur") else ""),
            f"émise le {g('date_emission')}" if g("date_emission") else "",
            f"valide jusqu'au {g('date_validite_fin')}" if g("date_validite_fin") else "",
            f"montant engagé {g('montant_engage_montant')} {g('montant_engage_devise')}".strip()
            if complet and g("montant_engage_montant")
            else "",
        )
    if table == "capacite_production":
        return _bloc(
            f"Capacité de production : {g('description')}",
            f"valeur {g('valeur')} {g('unite')}".strip() if g("valeur") else "",
        )
    if table == "assurance":
        return _bloc(
            f"Assurance {g('type_assurance')}",
            f"assureur {g('assureur')}" if g("assureur") else "",
            f"contrat {g('numero_contrat')}" if g("numero_contrat") else "",
            f"garantie {g('montant_garantie_montant')} {g('montant_garantie_devise')}".strip()
            if g("montant_garantie_montant")
            else "",
            f"franchise {g('franchise_montant')} {g('franchise_devise')}".strip()
            if complet and g("franchise_montant")
            else "",
            f"échéance {g('date_echeance')}" if g("date_echeance") else "",
            f"activités couvertes : {g('activites_couvertes')}"
            if g("activites_couvertes")
            else "",
        )
    if table == "certification":
        return _bloc(
            f"Certification {g('intitule')}"
            + (f" ({g('organisme')})" if g("organisme") else ""),
            f"numéro {g('numero_certificat')}" if complet and g("numero_certificat") else "",
            f"obtenue le {g('date_obtention')}" if g("date_obtention") else "",
            f"valide jusqu'au {g('date_echeance')}" if g("date_echeance") else "",
        )
    if table == "reference_chantier":
        return _bloc(
            f"Référence « {g('intitule_operation')} »",
            f"maître d'ouvrage {g('maitre_ouvrage')}" if g("maitre_ouvrage") else "",
            f"lieu {g('lieu_commune')}" if g("lieu_commune") else "",
            g("nature_travaux_libelle"),
            f"montant {g('montant_montant')} {g('montant_devise')} HT".strip()
            if g("montant_montant")
            else "",
            f"surface {g('surface_traitee')} {g('surface_unite')}".strip()
            if g("surface_traitee")
            else "",
            f"durée {g('duree_mois')} mois" if g("duree_mois") else "",
            f"réception {g('date_fin')}" if g("date_fin") else "",
            f"difficulté traitée : {g('description')}"
            if g("description") and complet
            else "",
        )
    if table == "effectif_metier":
        # Le libellé métier d'abord ; à défaut seulement, le code, rendu lisible.
        return f"Effectif {g('metier_libelle') or g('metier_code') or 'métier'} : {g('nombre')}."
    if table == "organigramme":
        return _bloc(
            "Organigramme de l'entreprise",
            g("description"),
            f"mise à jour {g('date_maj')}" if g("date_maj") else "",
        )
    if table == "cv":
        return _bloc(
            f"Profil clé {_m(g('prenom'), g('nom'))}, {g('fonction')}",
            f"diplômes {g('diplomes')}" if g("diplomes") else "",
            f"{g('annees_experience')} ans d'expérience" if g("annees_experience") else "",
        )
    if table == "moyen_materiel":
        # La catégorie est un code de nomenclature : elle est dite lisible, jamais brute.
        return _bloc(
            f"Moyen matériel {g('designation')}"
            + (f" ({g('categorie_code')})" if g("categorie_code") else ""),
            f"quantité {g('quantite')}" if g("quantite") else "",
            f"marque {g('marque_modele')}" if complet and g("marque_modele") else "",
            g("propriete") if complet else "",
            f"disponibilité {g('disponibilite')}" if complet and g("disponibilite") else "",
        )
    if table == "produit":
        return _bloc(
            f"Produit {g('designation')}"
            + (f" ({g('reference_produit')})" if g("reference_produit") else ""),
            f"fournisseur {g('fournisseur')}" if g("fournisseur") else "",
            f"avis technique {g('avis_technique')}" if g("avis_technique") else "",
            f"domaine d'application {g('domaine_application')}"
            if g("domaine_application")
            else "",
            f"valide jusqu'au {g('date_validite_document')}"
            if g("date_validite_document")
            else "",
        )
    if table == "chapitre_memoire":
        contenu = g("contenu_texte")
        if len(contenu) > LONGUEUR_EXTRAIT_CHAPITRE:
            contenu = contenu[:LONGUEUR_EXTRAIT_CHAPITRE].rstrip() + " […]"
        if contenu:
            return f"Chapitre réutilisable « {g('titre')} » : {contenu}"
        return f"Chapitre réutilisable « {g('titre')} » (source citée)."

    # Repli neutre : aucune phrase inventée, seulement le libellé réel.
    return f"{_LIBELLE_TABLE.get(table, table)} « {libelle_source(table, element)} »."


def _niveau_detail(poids: Optional[Decimal]) -> str:
    """Développement d'une section selon sa pondération (défaut « proportionnel »)."""
    if poids is None:
        return "essentiel"
    if poids >= SEUIL_DEVELOPPEMENT_COMPLET:
        return "complet"
    if poids >= SEUIL_DEVELOPPEMENT_ESSENTIEL:
        return "essentiel"
    return "mention"


# --------------------------------------------------------------------------- #
# Garde-fou de source — réutilisation de `source_presente`, jamais réécrit
# --------------------------------------------------------------------------- #
def verifier_sources(
    candidats: Sequence[Mapping[str, Any]],
    pages: Sequence[PageExtraite],
    *,
    identifiants_autorises: Optional[Iterable[str]] = None,
) -> tuple[SourceMemoire, ...]:
    """Applique aux sources du mémoire la **même exigence** qu'à une proposition de DCE.

    Chaque candidat porte l'extrait littéral invoqué (`extrait`) ; l'extrait doit se
    retrouver **littéralement** dans le texte rendu de son élément (`pages`) — c'est
    exactement `source_presente`, réutilisé tel quel. Un candidat qui cite un élément hors
    de `identifiants_autorises` (donc d'un autre client) est refusé : rien sans source
    vérifiable, refus explicite sinon. Aucune source n'est « réparée ».
    """
    autorises = set(identifiants_autorises) if identifiants_autorises is not None else None
    retenues: list[SourceMemoire] = []
    for candidat in candidats:
        table_source = str(candidat.get("table_source") or "")
        element_id = str(candidat.get("element_id") or "")
        if autorises is not None and element_id not in autorises:
            raise SourceMemoireInvalide(
                f"Source refusée : l'élément {element_id!r} n'appartient pas à la "
                "bibliothèque du client de la session (aucun mémoire croisé).",
                table_source=table_source,
                element_id=element_id,
            )
        proposition = PropositionElement(
            categorie=table_source,
            libelle=str(candidat.get("libelle_source") or table_source),
            source_emplacement=str(candidat.get("emplacement_source") or "bibliothèque"),
            source_extrait=str(candidat.get("extrait") or ""),
        )
        if not source_presente(proposition, pages):
            raise SourceMemoireInvalide(
                "Source refusée : l'extrait invoqué est introuvable dans l'élément cité "
                f"({table_source!r}). Aucune affirmation sans source vérifiable n'est "
                "acceptée dans un mémoire.",
                table_source=table_source,
                element_id=element_id,
            )
        retenues.append(
            SourceMemoire(
                table_source=table_source,
                element_id=element_id,
                libelle_source=str(candidat.get("libelle_source") or "")[:255],
                emplacement_source=str(candidat.get("emplacement_source") or "")[:255],
            )
        )
    return tuple(retenues)


# --------------------------------------------------------------------------- #
# Construction d'une section (ou d'un manque)
# --------------------------------------------------------------------------- #
def _candidats_pour_familles(
    familles: Sequence[str],
    elements_par_famille: Mapping[str, Mapping[str, list[dict[str, Any]]]],
) -> tuple[list[dict[str, Any]], list[PageExtraite], list[str]]:
    """Collecte, dans l'ordre des familles, les éléments réels mobilisables.

    Renvoie (candidats, pages, confiances) : un candidat et une page par élément, dans le
    même ordre. Aucune valeur n'est produite ici : on ne fait que **lire** la bibliothèque.
    """
    candidats: list[dict[str, Any]] = []
    pages: list[PageExtraite] = []
    confiances: list[str] = []
    for famille in familles:
        contenu = elements_par_famille.get(famille, {})
        for entite in FAMILLE_VERS_ENTITES.get(famille, ()):
            definition = definition_entite(entite)
            for element in contenu.get(entite, []):
                lignes = _lignes_element(definition.table, element)
                if not lignes:
                    continue
                page = PageExtraite(
                    numero=len(pages) + 1,
                    texte="\n".join(lignes),
                    methode="bibliotheque",
                    analyseable=True,
                    message=None,
                )
                pages.append(page)
                agg = element.get("statut_validite")
                candidats.append(
                    {
                        "table_source": definition.table,
                        "element_id": str(element.get("id")),
                        "libelle_source": libelle_source(definition.table, element),
                        "emplacement_source": (
                            # Le nom d'entité et le statut de validité sont dits en
                            # français : aucun code de nomenclature ne sort d'ici
                            # (ils sont persistés et exportés tels quels).
                            f"bibliothèque — {LIBELLES_FAMILLES.get(famille, famille)} / "
                            f"{definition.libelle}"
                            + (
                                f" — validité : {_libelle_validite(agg)}"
                                if agg
                                else ""
                            )
                        ),
                        "extrait": lignes[0],
                        "famille": famille,
                        # Élément brut conservé pour composer la phrase : il n'est ni
                        # persisté ni transmis, il sert uniquement à lire des champs réels.
                        "element": element,
                    }
                )
                confiances.append(str(element.get("confiance") or "a_verifier"))
    return candidats, pages, confiances


def _composer_contenu(
    *,
    critere_libelle: str,
    poids: Optional[Decimal],
    familles: Sequence[str],
    phrases: Sequence[str],
    non_pondere: bool,
    justification: str = "",
) -> str:
    """Assemble le texte d'une section : cadrage du critère + phrases factuelles citées.

    `justification` est la **trace** de la correspondance critère → bibliothèque
    (`CouvertureSujet.justification`) : elle dit sur quels termes du sujet la section
    s'appuie. Une section n'est jamais produite sans cette phrase.
    """
    if poids is None:
        entete = f"Critère « {critere_libelle} » — pondération non connue du DCE."
    else:
        entete = f"Critère « {critere_libelle} » — pondération {_format_poids(poids)} %."
    morceaux = [entete]
    if non_pondere:
        morceaux.append(
            "Pondération non connue : ce critère est traité en fin de mémoire et sa "
            "raison est affichée ici, conformément à la règle de classement."
        )
    libelles = ", ".join(LIBELLES_FAMILLES.get(f, f) for f in familles)
    morceaux.append(
        f"Éléments de votre bibliothèque mobilisés : {len(phrases)} (familles : "
        f"{libelles}). Chaque phrase ci-dessous renvoie à un élément réel et vérifiable ; "
        "aucune valeur n'est ajoutée, aucun prix n'est fixé, aucune conformité n'est promise."
    )
    if justification:
        morceaux.append(justification)
    for phrase in phrases:
        morceaux.append(f"- {phrase}")
    return "\n".join(morceaux)


def _format_poids(poids: Decimal) -> str:
    """Pondération affichée sans zéro inutile (40 au lieu de 40.00)."""
    normalise = poids.normalize()
    texte = format(normalise, "f")
    return texte


def composer_section(
    *,
    critere: Mapping[str, Any],
    familles: Sequence[str],
    candidats: Sequence[Mapping[str, Any]],
    pages: Sequence[PageExtraite],
    confiances: Sequence[str],
    ordre: int,
    identifiants_autorises: Optional[Iterable[str]] = None,
    sources: Optional[Sequence[SourceMemoire]] = None,
    justification: str = "",
) -> SectionMemoire:
    """Construit une section **sourcée**. Refuse explicitement toute source invérifiable.

    Lève `SourceMemoireInvalide` (jamais un succès partiel) si une source ne passe pas le
    garde-fou. La conversion en manque est faite par `section_ou_manque`, jamais ici.

    `sources`, quand il est fourni, est le résultat **déjà vérifié** de `verifier_sources` :
    il évite une seconde vérification identique. Il n'est alors **pas** revérifié (le
    garde-fou a déjà parlé). `justification` est la trace de la couverture du sujet.
    """
    libelle = str(critere.get("libelle") or "").strip()
    poids = poids_depuis_valeur(critere.get("valeur"))
    if sources is None:
        sources = verifier_sources(
            candidats, pages, identifiants_autorises=identifiants_autorises
        )
    else:
        sources = tuple(sources)
    niveau = _niveau_detail(poids)
    phrases = [
        _phrase_element(
            str(candidat["table_source"]),
            candidat.get("element") or {},
            niveau,
        )
        for candidat in candidats
    ]
    contenu = _composer_contenu(
        critere_libelle=libelle,
        poids=poids,
        familles=familles,
        phrases=phrases,
        non_pondere=poids is None,
        justification=justification,
    )
    return SectionMemoire(
        ordre=ordre,
        critere_code=str(critere.get("id")),
        critere_libelle=libelle,
        critere_poids=poids,
        titre=libelle or "Critère du DCE",
        contenu=contenu,
        sources=sources,
        statut="brouillon",
        origine="mixte",
        confiance=confiance_la_plus_faible(list(confiances)) if confiances else "a_verifier",
    )


def section_ou_manque(
    *,
    critere: Mapping[str, Any],
    familles: Sequence[str],
    candidats: Sequence[Mapping[str, Any]],
    pages: Sequence[PageExtraite],
    confiances: Sequence[str],
    ordre: int,
    identifiants_autorises: Optional[Iterable[str]] = None,
) -> SectionMemoire | ManqueMemoire:
    """Produit une section sourcée **ou** un manque — jamais une section sans preuve.

    C'est le point où la ligne rouge est tenue. Trois refus, tous transformés en manque
    (constat + action), jamais contournés :

    1. une source invérifiable (garde-fou `source_presente`, réutilisé tel quel) ;
    2. **le sujet du critère n'est pas couvert** par les éléments cités : « la source
       existe » ne suffit pas, il faut qu'elle **parle du critère**. C'est la correction
       du défaut B2 (section produite pour un critère que rien ne documentait) — sans
       elle, le repli `FAMILLES_DEFAUT` fabriquait un développement dès qu'une source
       du lot existait.
    """
    libelle = str(critere.get("libelle") or "").strip()
    poids = poids_depuis_valeur(critere.get("valeur"))
    # Raison affichée quand la pondération est inconnue : le critère est classé en fin.
    raison = (
        "Pondération non connue du DCE : critère classé en fin de mémoire. "
        if poids is None
        else ""
    )
    if est_critere_prix(libelle):
        return ManqueMemoire(
            critere_code=str(critere.get("id")),
            critere_libelle=libelle,
            critere_poids=poids,
            constat=raison + CONSTAT_PRIX_HORS_MEMOIRE,
            action_attendue=ACTION_PRIX_HORS_MEMOIRE,
        )
    if not candidats:
        return ManqueMemoire(
            critere_code=str(critere.get("id")),
            critere_libelle=libelle,
            critere_poids=poids,
            constat=raison + CONSTAT_MANQUE_AUCUNE_REFERENCE,
            action_attendue=_action_manque(familles),
        )
    try:
        sources = verifier_sources(
            candidats, pages, identifiants_autorises=identifiants_autorises
        )
    except SourceMemoireInvalide as exc:
        # Refus attendu du garde-fou : la section n'est **pas** produite, elle devient
        # un manque lisible. L'incident est journalisé (jamais avalé en silence).
        LOGGER.warning("Section refusée faute de source vérifiable : %s", exc)
        return ManqueMemoire(
            critere_code=str(critere.get("id")),
            critere_libelle=libelle,
            critere_poids=poids,
            constat=raison + f"Source invérifiable, section non produite : {exc}",
            action_attendue=_action_manque(familles),
        )
    # Les sources sont vérifiées ; reste à savoir si elles **portent le sujet** du
    # critère. À défaut, aucune section : le manque est écrit, avec ses termes absents.
    couverture = couverture_sujet(
        libelle,
        correspondance_pour_critere(libelle).mots_cles,
        [page.texte for page in pages],
    )
    if not couverture.etablie:
        LOGGER.info(
            "Critère %r non couvert par la bibliothèque (termes absents : %s) : manque.",
            libelle,
            ", ".join(couverture.termes_absents),
        )
        return ManqueMemoire(
            critere_code=str(critere.get("id")),
            critere_libelle=libelle,
            critere_poids=poids,
            constat=raison + constat_manque_sujet(couverture.termes_absents),
            action_attendue=_action_manque(familles),
        )
    return composer_section(
        critere=critere,
        familles=familles,
        candidats=candidats,
        pages=pages,
        confiances=confiances,
        ordre=ordre,
        identifiants_autorises=identifiants_autorises,
        sources=sources,
        justification=couverture.justification(),
    )


#: Priorité des familles pour choisir l'action à mener d'un manque : la **preuve la plus
#: parlante** d'abord (une référence de chantier comparable), et non l'ordre de lecture du
#: critère. C'est ce qui rend le manque actionnable (« ajoutez un chantier de ce type »).
ORDRE_ACTION_MANQUE: tuple[str, ...] = (
    "references_chantiers",
    "certifications",
    "moyens_humains",
    "moyens_materiels",
    "fiches_produits",
    "capacites_financieres",
    "assurances",
    "memoire_technique",
    "identite",
)


def _action_manque(familles: Sequence[str]) -> str:
    """Action à mener quand aucune source ne répond au critère (preuve la plus parlante)."""
    visees = set(familles)
    for famille in ORDRE_ACTION_MANQUE:
        if famille in visees and famille in ACTIONS_MANQUE:
            return ACTIONS_MANQUE[famille]
    for famille in familles:
        action = ACTIONS_MANQUE.get(famille)
        if action:
            return action
    return (
        "Compléter votre bibliothèque sur ce point (référence, certification, moyen ou "
        "produit) : le mémoire ne peut rien écrire sans élément réel correspondant."
    )


# --------------------------------------------------------------------------- #
# Tri des critères — l'ordre de la notation
# --------------------------------------------------------------------------- #
def trier_criteres(criteres: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Trie les critères par pondération décroissante, sans pondération en fin.

    Stable : à poids égal (ou absent), l'ordre du DCE est conservé. Aucun poids n'est
    inventé — un critère sans pourcentage connu garde sa position finale et sa raison.
    """

    def cle(element: tuple[int, Mapping[str, Any]]) -> tuple[int, float, int]:
        index, critere = element
        poids = poids_depuis_valeur(critere.get("valeur"))
        if poids is None:
            return (1, 0.0, index)
        return (0, -float(poids), index)

    indexes = list(enumerate(criteres))
    indexes.sort(key=cle)
    return [dict(critere) for _, critere in indexes]


# --------------------------------------------------------------------------- #
# Génération
# --------------------------------------------------------------------------- #
def generer_memoire(
    connexion: Connexion,
    cle_maitresse: bytes,
    contexte: ContexteClient,
    *,
    consultation_id: str,
    fiche_version_id: Optional[str] = None,
    titre: Optional[str] = None,
    fournisseur: Optional[Any] = None,
) -> dict[str, Any]:
    """Génère un mémoire structuré : sections sourcées + manques, en une transaction.

    Les écritures intermédiaires ne sont **pas** validées : si la génération échoue, tout
    est annulé (`connexion.annuler()` par l'appelant) et aucun dossier orphelin ne
    subsiste. Le dossier sort **`brouillon`** : aucun statut validé n'est posé ici.
    """
    consultation = _lire_consultation(connexion, contexte, consultation_id)
    fiche = _lire_fiche(connexion, contexte, fiche_version_id)
    fiche_id = str(fiche["id"])
    criteres = _criteres_valides(connexion, contexte, consultation_id)
    if not criteres:
        raise ErreurMemoire(
            "Aucun critère d'attribution validé pour cette consultation : le plan du "
            "mémoire suit les critères du DCE. Validez les critères extraits (brique B) "
            "avant de générer le mémoire."
        )

    service = ServiceBibliotheque(connexion, cle_maitresse, contexte)
    cache: dict[str, Mapping[str, list[dict[str, Any]]]] = {}

    def elements_famille(famille: str) -> Mapping[str, list[dict[str, Any]]]:
        if famille not in cache:
            try:
                cache[famille] = service.consulter_famille(famille, fiche_id)["elements"]
            except ErreurBibliotheque as exc:  # pragma: no cover — famille connue
                raise ErreurMemoire(str(exc)) from exc
        return cache[famille]

    fournisseur_effectif = fournisseur
    moteur = getattr(fournisseur_effectif, "nom", None)
    modele = getattr(fournisseur_effectif, "modele", None)

    titre_dossier = (titre or "").strip() or (
        f"Mémoire technique — {consultation['libelle']}"
    )[:255]

    dossier = connexion.executer_une(
        contexte,
        "INSERT INTO memoire_dossier (client_id, consultation_id, fiche_version_id, "
        "titre, statut, moteur_fournisseur, moteur_modele, avertissement) "
        "VALUES (%(client_id)s, %(consultation_id)s, %(fiche)s, %(titre)s, 'brouillon', "
        "%(moteur)s, %(modele)s, %(avertissement)s) RETURNING *;",
        {
            "consultation_id": consultation_id,
            "fiche": fiche_id,
            "titre": titre_dossier,
            "moteur": moteur,
            "modele": modele,
            "avertissement": AVERTISSEMENT_GENERATION,
        },
    )
    if dossier is None:  # pragma: no cover — RETURNING garantit une ligne
        raise ErreurMemoire("Création du dossier de mémoire impossible.")
    dossier_id = str(dossier["id"])

    sections: list[SectionMemoire] = []
    manques: list[ManqueMemoire] = []
    for ordre, critere in enumerate(trier_criteres(criteres)):
        libelle = str(critere.get("libelle") or "").strip()
        familles = familles_pour_critere(libelle)
        elements_par_famille = {famille: elements_famille(famille) for famille in familles}
        candidats, pages, confiances = _candidats_pour_familles(
            familles, elements_par_famille
        )
        identifiants = {c["element_id"] for c in candidats}
        resultat = section_ou_manque(
            critere=critere,
            familles=familles,
            candidats=candidats,
            pages=pages,
            confiances=confiances,
            ordre=ordre,
            identifiants_autorises=identifiants,
        )
        if isinstance(resultat, ManqueMemoire):
            manques.append(resultat)
            continue
        sections.append(resultat)
        section_id = _ecrire_section(connexion, contexte, dossier_id, resultat)
        for source in resultat.sources:
            _ecrire_source(connexion, contexte, section_id, source)

    for manque in manques:
        _ecrire_manque(connexion, contexte, dossier_id, manque)

    connexion.valider()
    return lire_memoire(connexion, contexte, consultation_id)


def _ecrire_section(
    connexion: Connexion,
    contexte: ContexteClient,
    dossier_id: str,
    section: SectionMemoire,
) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO memoire_section (client_id, memoire_dossier_id, ordre, "
        "critere_code, critere_libelle, critere_poids, titre, contenu, statut, origine, "
        "confiance) VALUES (%(client_id)s, %(dossier)s, %(ordre)s, %(code)s, %(libelle)s, "
        "%(poids)s, %(titre)s, %(contenu)s, 'brouillon', %(origine)s, %(confiance)s) "
        "RETURNING *;",
        {
            "dossier": dossier_id,
            "ordre": section.ordre,
            "code": section.critere_code,
            "libelle": section.critere_libelle,
            "poids": section.critere_poids,
            "titre": section.titre[:255],
            "contenu": section.contenu,
            "origine": section.origine,
            "confiance": section.confiance,
        },
    )
    if ligne is None:  # pragma: no cover
        raise ErreurMemoire("Enregistrement de la section impossible.")
    return str(ligne["id"])


def _ecrire_source(
    connexion: Connexion,
    contexte: ContexteClient,
    section_id: str,
    source: SourceMemoire,
) -> None:
    connexion.executer_une(
        contexte,
        "INSERT INTO memoire_section_source (client_id, memoire_section_id, table_source, "
        "element_id, libelle_source, emplacement_source) "
        "VALUES (%(client_id)s, %(section)s, %(table)s, %(element)s, %(libelle)s, "
        "%(emplacement)s) RETURNING id;",
        {
            "section": section_id,
            "table": source.table_source,
            "element": source.element_id,
            "libelle": source.libelle_source,
            "emplacement": source.emplacement_source,
        },
    )


def _ecrire_manque(
    connexion: Connexion,
    contexte: ContexteClient,
    dossier_id: str,
    manque: ManqueMemoire,
) -> None:
    connexion.executer_une(
        contexte,
        "INSERT INTO memoire_manque (client_id, memoire_dossier_id, critere_code, "
        "critere_libelle, critere_poids, constat, action_attendue) "
        "VALUES (%(client_id)s, %(dossier)s, %(code)s, %(libelle)s, %(poids)s, "
        "%(constat)s, %(action)s) RETURNING id;",
        {
            "dossier": dossier_id,
            "code": manque.critere_code,
            "libelle": manque.critere_libelle,
            "poids": manque.critere_poids,
            "constat": manque.constat,
            "action": manque.action_attendue,
        },
    )


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def lire_memoire(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> dict[str, Any]:
    """Le **dernier** mémoire de la consultation, avec ses sections, sources et manques."""
    consultation = _lire_consultation(connexion, contexte, consultation_id)
    dossier = connexion.executer_une(
        contexte,
        "SELECT * FROM memoire_dossier WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s "
        "ORDER BY date_creation DESC, id DESC LIMIT 1;",
        {"consultation_id": consultation_id},
    )
    if dossier is None:
        raise MemoireIntrouvable(
            "Aucun mémoire n'a encore été généré pour cette consultation."
        )
    return _assembler(connexion, contexte, consultation, dossier)


def _assembler(
    connexion: Connexion,
    contexte: ContexteClient,
    consultation: Mapping[str, Any],
    dossier: Mapping[str, Any],
) -> dict[str, Any]:
    dossier_id = str(dossier["id"])
    sections = connexion.executer(
        contexte,
        "SELECT * FROM memoire_section WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY ordre, id;",
        {"dossier": dossier_id},
    )
    for section in sections:
        section["sources"] = connexion.executer(
            contexte,
            "SELECT * FROM memoire_section_source WHERE client_id = %(client_id)s "
            "AND memoire_section_id = %(section)s ORDER BY date_creation, id;",
            {"section": str(section["id"])},
        )
    manques = connexion.executer(
        contexte,
        "SELECT * FROM memoire_manque WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY critere_poids DESC NULLS LAST, id;",
        {"dossier": dossier_id},
    )
    validations = connexion.executer(
        contexte,
        "SELECT * FROM memoire_validation WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY horodatage DESC, id;",
        {"dossier": dossier_id},
    )
    nb_sections = len(sections)
    nb_validees = sum(1 for s in sections if str(s["statut"]) == "validee")
    nb_relues = sum(1 for s in sections if str(s["statut"]) == "relue")
    return {
        "consultation": consultation,
        "dossier": dossier,
        "sections": sections,
        "manques": manques,
        "validations": validations,
        "resume": {
            "nb_sections": nb_sections,
            "nb_sections_validees": nb_validees,
            "nb_sections_relues": nb_relues,
            "nb_manques": len(manques),
            "statut": str(dossier["statut"]),
            "longueurs": [
                {"ordre": s["ordre"], "titre": s["titre"], "longueur": len(str(s["contenu"]))}
                for s in sections
            ],
        },
        "avertissement": dossier.get("avertissement") or AVERTISSEMENT_GENERATION,
        "mention": MENTION_BROUILLON,
    }


# --------------------------------------------------------------------------- #
# Gestion des statuts — toujours par une action humaine nommée et horodatée
# --------------------------------------------------------------------------- #
def changer_statut_section(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    section_id: str,
    statut: str,
    par: str,
) -> dict[str, Any]:
    """Passe une section à `relue` ou `validee` — action humaine **nommée**.

    Le nom est obligatoire : aucun chemin de ce lot ne pose un statut relu ou validé sans
    un humain. Une modification ramène le dossier à `en_relecture` (une validation
    antérieure ne vaut plus pour le contenu modifié).
    """
    cible = (statut or "").strip().casefold()
    if cible not in STATUTS_SECTION:
        raise ErreurMemoire(
            f"Statut inconnu : {statut!r}. Valeurs admises : {', '.join(STATUTS_SECTION)}."
        )
    nom = (par or "").strip()
    if not nom:
        raise ErreurMemoire(
            "`par` est obligatoire : aucun statut de section n'est posé sans une action "
            "humaine nommée (ligne rouge)."
        )
    section = connexion.executer_une(
        contexte,
        "SELECT * FROM memoire_section WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": section_id},
    )
    if section is None:
        raise MemoireIntrouvable("Section introuvable pour ce client.")
    actuel = str(section["statut"])
    if cible != actuel and cible not in TRANSITIONS_SECTION.get(actuel, ()):
        raise ErreurMemoire(
            f"Transition refusée : {actuel!r} → {cible!r}. Chemin attendu : "
            "brouillon → relue → validee."
        )
    ligne = connexion.executer_une(
        contexte,
        "UPDATE memoire_section SET statut = %(statut)s, statut_par = %(nom)s, "
        "statut_le = now(), date_modification = now() "
        "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING *;",
        {"statut": cible, "nom": nom, "id": section_id},
    )
    if ligne is None:  # pragma: no cover
        raise ErreurMemoire("Mise à jour de la section impossible.")
    dossier = connexion.executer_une(
        contexte,
        "UPDATE memoire_dossier SET statut = 'en_relecture', date_modification = now() "
        "WHERE client_id = %(client_id)s AND id = %(dossier)s "
        "AND statut <> 'en_relecture' RETURNING *;",
        {"dossier": str(section["memoire_dossier_id"])},
    )
    connexion.valider()
    return {
        "section": ligne,
        "dossier": dossier,
        "mention": MENTION_BROUILLON,
    }


def valider_dossier(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    dossier_id: str,
    nom_validateur: str,
    fonction_validateur: str,
    format_export: Optional[str] = None,
    nom_fichier: Optional[str] = None,
) -> dict[str, Any]:
    """Valide le mémoire **entier** : ligne `memoire_validation` nommée et horodatée.

    Exige un nom, une fonction, et **aucune section restée `brouillon`** : on ne valide pas
    un mémoire non relu. Écrit l'empreinte SHA-256 du contenu validé. Aucun chemin de code
    n'atteint `valide` sans passer par ici.
    """
    nom = (nom_validateur or "").strip()
    fonction = (fonction_validateur or "").strip()
    if not nom or not fonction:
        raise ErreurMemoire(
            "La validation finale exige un nom **et** une fonction : elle est nommée et "
            "horodatée, jamais anonyme."
        )
    dossier = connexion.executer_une(
        contexte,
        "SELECT * FROM memoire_dossier WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": dossier_id},
    )
    if dossier is None:
        raise MemoireIntrouvable("Dossier de mémoire introuvable pour ce client.")
    if str(dossier["statut"]) == "valide":
        raise ErreurMemoire(
            "Ce mémoire est déjà validé : une validation ne se rejoue pas."
        )
    sections = connexion.executer(
        contexte,
        "SELECT * FROM memoire_section WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY ordre, id;",
        {"dossier": dossier_id},
    )
    if not sections:
        raise ErreurMemoire(
            "Ce mémoire n'a aucune section : il n'y a rien à valider. Générez d'abord un "
            "mémoire à partir de vos critères et de votre bibliothèque."
        )
    restees = [str(s["id"]) for s in sections if str(s["statut"]) == "brouillon"]
    if restees:
        raise ErreurMemoire(
            f"{len(restees)} section(s) encore en brouillon : relisez chaque section "
            "avant de valider le mémoire (brouillon → relue → validee)."
        )
    # Les sources sont chargées pour que l'empreinte couvre **tout** le contenu validé.
    for section in sections:
        section["sources"] = connexion.executer(
            contexte,
            "SELECT * FROM memoire_section_source WHERE client_id = %(client_id)s "
            "AND memoire_section_id = %(section)s ORDER BY date_creation, id;",
            {"section": str(section["id"])},
        )
    manques = connexion.executer(
        contexte,
        "SELECT * FROM memoire_manque WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY id;",
        {"dossier": dossier_id},
    )
    empreinte = empreinte_contenu(dossier, sections, manques)
    validation = connexion.executer_une(
        contexte,
        "INSERT INTO memoire_validation (client_id, memoire_dossier_id, nom_validateur, "
        "fonction_validateur, empreinte_contenu, format_export, nom_fichier) "
        "VALUES (%(client_id)s, %(dossier)s, %(nom)s, %(fonction)s, %(empreinte)s, "
        "%(format)s, %(fichier)s) RETURNING *;",
        {
            "dossier": dossier_id,
            "nom": nom,
            "fonction": fonction,
            "empreinte": empreinte,
            "format": format_export,
            "fichier": nom_fichier,
        },
    )
    dossier = connexion.executer_une(
        contexte,
        "UPDATE memoire_dossier SET statut = 'valide', date_modification = now() "
        "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING *;",
        {"id": dossier_id},
    )
    connexion.valider()
    return {
        "validation": validation,
        "dossier": dossier,
        "empreinte_contenu": empreinte,
        "mention": (
            "Mémoire validé par un humain nommé — horodaté et empreinté. Aucune "
            "conformité n'est pour autant garantie."
        ),
    }


# --------------------------------------------------------------------------- #
# Empreinte du contenu validé
# --------------------------------------------------------------------------- #
def contenu_canonique(
    dossier: Mapping[str, Any],
    sections: Sequence[Mapping[str, Any]],
    manques: Sequence[Mapping[str, Any]],
) -> str:
    """Représentation **déterministe** du contenu d'un mémoire (base de l'empreinte).

    Sérialisation stable : elle ne dépend que du contenu métier (titre, critère, texte,
    sources, manques), jamais d'un identifiant interne ni d'un horodatage. Deux contenus
    identiques donnent deux empreintes identiques.
    """
    lignes: list[str] = [f"titre: {dossier.get('titre') or ''}"]
    for section in sections:
        lignes.append(f"section: {section.get('ordre')}|{section.get('critere_libelle')}")
        lignes.append(f"titre: {section.get('titre')}")
        lignes.append(f"statut: {section.get('statut')}")
        lignes.append(f"contenu: {section.get('contenu')}")
        for source in section.get("sources", []) or []:
            lignes.append(
                f"source: {source.get('table_source')}|{source.get('libelle_source')}|"
                f"{source.get('emplacement_source')}"
            )
    for manque in manques:
        lignes.append(f"manque: {manque.get('critere_libelle')}")
        lignes.append(f"constat: {manque.get('constat')}")
        lignes.append(f"action: {manque.get('action_attendue')}")
    return "\n".join(lignes)


def empreinte_contenu(
    dossier: Mapping[str, Any],
    sections: Sequence[Mapping[str, Any]],
    manques: Sequence[Mapping[str, Any]],
) -> str:
    """Empreinte SHA-256 (hexadécimal) du contenu validé d'un mémoire."""
    canonique = contenu_canonique(dossier, sections, manques)
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()


__all__ = [
    "ErreurMemoire",
    "MemoireIntrouvable",
    "SourceMemoireInvalide",
    "changer_statut_section",
    "composer_section",
    "contenu_canonique",
    "empreinte_contenu",
    "familles_pour_critere",
    "generer_memoire",
    "libelle_source",
    "lire_memoire",
    "section_ou_manque",
    "verifier_sources",
]
