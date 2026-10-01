"""Écrans HTML rendus côté serveur — brique d'interface du MVP (annexe A § A8).

Décisions de structure tenues ici
---------------------------------

* **HTML rendu côté serveur, Jinja2, aucun JavaScript, aucun build Node.** Les
  formulaires sont des `<form method="post">` sans script : chaque écran est
  atteignable et utilisable au clavier.
* **Aucune route `/api/v1` n'est créée, renommée ni modifiée.** Le contrat de
  l'annexe C est gelé ; les écrans appellent les **services** (`app.services`)
  directement, dans le processus, comme le font les routes JSON — pas de
  requête HTTP en boucle sur soi-même. Les seuls chemins ajoutés sont les
  écrans HTML de la liste gelée (`/connexion`, `/bibliotheque`,
  `/bibliotheque/{famille}`, `/consultations`, `/consultations/{id}`,
  `/consultations/{id}/checklist`), plus les quelques POST de formulaire sur ces
  mêmes chemins et `/deconnexion`, `/entreprises`, `/entreprises/{id}/fiches`.
* **Deux verrous humains distincts**, jamais fusionnés : la validation de la
  bibliothèque (`POST /bibliotheque/validation`) et la validation des éléments
  extraits d'un DCE (`POST /consultations/{id}/elements/{element_id}`). Aucun
  chemin de ce module ne pose un état validé sans action humaine nommée.
* **Ligne rouge.** Toute valeur affichée porte `origine`, `confiance` et, si
  elle est extraite, sa source. Une valeur sans source s'affiche **non
  vérifiée** ; une exigence introuvable s'affiche « non trouvé dans le
  document », jamais comblée. Aucun prix, aucune marge, aucune conformité
  garantie, aucun bouton de dépôt, d'envoi ou de signature.
* **Session.** Le cookie de session est celui de `app.api.cloisonnement`
  (`NOM_COOKIE_SESSION`) : une session ouverte ici vaut pour l'API et
  réciproquement. Le `client_id` vient **exclusivement** de la session ; un
  écran sans session redirige (303) vers `/connexion`, et une cible d'un autre
  client répond `404` — jamais `403`, et jamais ses données.

Écarts assumés, signalés dans `docs/RAPPORTS/L5-interface-web.md`
----------------------------------------------------------------

* « Créer une valeur de référence manquante sans quitter le formulaire » (D2)
  est rendu **sur l'élément** : le champ « valeur absente de la liste » n'écrit
  **jamais** dans la table globale `valeur_reference` (I5) — une écriture
  globale depuis une session d'entreprise croiserait les locataires, et une
  nomenclature par client est explicitement réservée au MVP
  (`docs/DATA-MODEL-V2.md` § 8.4). Une valeur créée ici reste donc portée par
  l'élément, marquée à vérifier. Décision signalée en commentaire de carte.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.cloisonnement import (
    NOM_COOKIE_SESSION,
    obtenir_config,
    obtenir_connexion,
)
from app.domain.fiche_version import LIBELLES_STATUT_VERSION, StatutFamille
from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    definition_entite,
    definition_famille,
    reference_attendue,
    type_champ,
)
from app.domain.memoire_technique_genere import familles_pour_critere
from app.services import analyse_dce, checklist, import_guide, memoire_technique
from app.services.analyse_dce import ConsultationIntrouvable, ErreurAnalyseDce
from app.services.import_guide import (
    ErreurImportGuide,
    ImportIntrouvable,
    ImportNonValidable,
)
from app.services.fournisseur_modele import ErreurFournisseurModele
from app.services.memoire_technique import ErreurMemoire, MemoireIntrouvable
from app.services.authentification import (
    ErreurAuthentification,
    ServiceAuthentification,
)
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.checklist import ChecklistIntrouvable, ErreurChecklist
from app.services.versionnement import ErreurVersionnement
from app.storage.connexion import Connexion, ContexteClient
from app.storage.depot_consultations import DepotConsultation
from app.storage.fichiers import StockageFichiers
from app.storage.repositories import DepotDocument, ErreurDepot

# --------------------------------------------------------------------------- #
# Constantes d'écran
# --------------------------------------------------------------------------- #

#: Mention obligatoire de toute sortie de nature à engager l'entreprise
#: (annexe A § A8, `docs/PLAN-PHASE-3.md` § 3 lot L5).
MENTION_BROUILLON = "brouillon — à relire et à signer"

#: Taille maximale acceptée pour un document fourni (identical to the JSON route).
TAILLE_MAX_DOCUMENT = 25 * 1024 * 1024

REPERTOIRE_GABARITS = Path(__file__).resolve().parent / "templates"
REPERTOIRE_STATIQUE = Path(__file__).resolve().parent / "static"

GABARITS = Jinja2Templates(directory=str(REPERTOIRE_GABARITS))

router = APIRouter(tags=["écrans web"])

#: Libellés français des champs les plus courants, pour les formulaires.
#: Un champ absent de cette table s'affiche par son nom technique (le fond est
#: respecté : aucun libellé métier n'est inventé).
LIBELLES_CHAMPS: dict[str, str] = {
    "raison_sociale": "Raison sociale",
    "siren": "SIREN",
    "siret_siege": "SIRET du siège",
    "forme_juridique_code": "Forme juridique (référence)",
    "capital_social_montant": "Capital social (montant)",
    "capital_social_devise": "Capital social (devise ISO)",
    "date_creation_entreprise": "Date de création de l'entreprise",
    "code_ape_naf": "Code APE/NAF",
    "numero_tva_intracommunautaire": "N° TVA intracommunautaire",
    "adresse_siege": "Adresse du siège",
    "adresse_etablissement_principal": "Adresse de l'établissement principal",
    "telephone": "Téléphone",
    "email": "Courriel",
    "site_web": "Site web",
    "effectif": "Effectif",
    "date_effectif": "Date de l'effectif",
    "effectif_source_code": "Origine de l'effectif",
    "iban": "IBAN (donnée sensible)",
    "bic": "BIC (donnée sensible)",
    "piece_rib": "Pièce RIB",
    "nom": "Nom",
    "prenom": "Prénom",
    "fonction": "Fonction",
    "qualite_engagement": "Qualité pour engager l'entreprise",
    "date_nomination": "Date de nomination",
    "date_cessation": "Date de cessation",
    "statut": "Statut",
    "piece": "Justificatif",
    "annee_exercice": "Année de l'exercice",
    "date_cloture": "Date de clôture",
    "chiffre_affaires_montant": "Chiffre d'affaires (montant)",
    "chiffre_affaires_devise": "Chiffre d'affaires (devise ISO)",
    "resultat_net_montant": "Résultat net (montant)",
    "resultat_net_devise": "Résultat net (devise ISO)",
    "capitaux_propres_montant": "Capitaux propres (montant)",
    "capitaux_propres_devise": "Capitaux propres (devise ISO)",
    "total_bilan_montant": "Total du bilan (montant)",
    "total_bilan_devise": "Total du bilan (devise ISO)",
    "effectif_moyen": "Effectif moyen",
    "type_attestation": "Type d'attestation",
    "emetteur": "Émetteur",
    "date_emission": "Date d'émission",
    "date_validite_fin": "Date de fin de validité",
    "montant_engage_montant": "Montant engagé",
    "montant_engage_devise": "Devise",
    "description": "Description",
    "unite": "Unité",
    "valeur": "Valeur",
    "commentaire": "Commentaire",
    "type_assurance": "Type d'assurance",
    "assureur": "Assureur",
    "numero_contrat": "Numéro de contrat",
    "montant_garantie_montant": "Montant de garantie",
    "montant_garantie_devise": "Devise de la garantie",
    "franchise_montant": "Franchise",
    "franchise_devise": "Devise de la franchise",
    "date_debut": "Date de début",
    "date_echeance": "Date d'échéance",
    "activites_couvertes": "Activités couvertes",
    "intitule": "Intitulé",
    "organisme": "Organisme",
    "domaine_code": "Domaine (référence)",
    "numero_certificat": "Numéro de certificat",
    "date_obtention": "Date d'obtention",
    "intitule_operation": "Intitulé de l'opération",
    "maitre_ouvrage": "Maître d'ouvrage",
    "nature_travaux_code": "Nature des travaux (référence)",
    "nature_travaux_libelle": "Nature des travaux",
    "lieu_commune": "Commune",
    "lieu_departement": "Département",
    "date_fin": "Date de fin",
    "montant_montant": "Montant du chantier",
    "montant_devise": "Devise du montant",
    "duree_mois": "Durée (mois)",
    "surface_traitee": "Surface traitée",
    "surface_unite": "Unité de surface",
    "competences_appliquees": "Compétences appliquées",
    "attestation_bonne_execution": "Attestation de bonne exécution",
    "contact_reference": "Contact de référence",
    "photos": "Photos",
    "metier_code": "Métier (référence)",
    "metier_libelle": "Métier",
    "nombre": "Nombre",
    "date_maj": "Date de mise à jour",
    "diplomes": "Diplômes",
    "annees_experience": "Années d'expérience",
    "cv_piece": "Pièce CV",
    "categorie_code": "Catégorie (référence)",
    "designation": "Désignation",
    "quantite": "Quantité",
    "marque_modele": "Marque et modèle",
    "annee": "Année",
    "propriete": "Propriété",
    "disponibilite": "Disponibilité",
    "justificatif": "Justificatif",
    "fournisseur": "Fournisseur",
    "reference_produit": "Référence produit",
    "famille_code": "Famille de produit (référence)",
    "domaine_application": "Domaine d'application",
    "fiche_technique": "Fiche technique",
    "avis_technique": "Avis technique",
    "date_validite_document": "Date de validité du document",
    "certificats": "Certificats",
    "titre": "Titre",
    "ordre": "Ordre",
    "contenu_texte": "Contenu",
    "date_redaction": "Date de rédaction",
    "references_liees": "Références liées",
    "documents_associes": "Documents associés",
}

#: Messages affichés après une action réussie (paramètre `ok` de l'URL).
MESSAGES_OK: dict[str, str] = {
    "entreprise_creee": "Entreprise créée avec sa première version de fiche (aucune donnée déduite : le libellé vient de la saisie).",
    "fiche_ouverte": "Nouvelle version de fiche ouverte (numéro croissant par entreprise).",
    "element_enregistre": "Élément enregistré. Toute validation de relecture qui couvrait cette famille a été révoquée : la fiche repasse en relecture.",
    "validation_enregistree": "Relecture humaine enregistrée : nom du relecteur et horodatage posés au moment de l'action.",
    "document_analyse": "Document lu et analysé. Chaque élément proposé porte sa source ; aucun n'est un fait avant validation humaine.",
    "element_verifie": "Action humaine enregistrée sur l'élément.",
    "checklist_executee": "Vérification exécutée : elle croise les pièces exigées validées avec la bibliothèque.",
    # Import guidé (lot L5b)
    "import_depose": "Document lu. Chaque proposition porte le passage exact dont elle vient ; rien n'entre dans votre bibliothèque sans votre décision.",
    "proposition_acceptee": "Proposition acceptée : l'information est entrée dans votre bibliothèque, marquée « extrait d'un document — à vérifier ».",
    "proposition_refusee": "Proposition refusée : rien n'a été écrit dans votre bibliothèque.",
    # Mémoire technique (lot L5b)
    "memoire_genere": "Mémoire monté à partir des critères du dossier et de votre bibliothèque. Chaque section porte ses sources.",
    "memoire_valide": "Validation enregistrée : elle porte le nom de la personne qui a relu, la date, et l'empreinte du contenu validé.",
    "section_relue": "Relecture de section enregistrée : elle porte le nom de la personne qui l'a faite.",
    "section_validee": "Section validée : elle porte le nom de la personne qui l'a validée.",
    "section_a_corriger": "Section marquée à corriger : elle repasse avant relecture.",
}

#: Vocabulaire **métier** des états d'une famille (règle § 2 du lot L5a :
#: aucun état de code à l'écran). La traduction se fait au rendu, jamais dans
#: le gabarit.
LIBELLES_STATUT_FAMILLE: dict[str, str] = {
    StatutFamille.NON_COMMENCEE.value: "À compléter",
    StatutFamille.DEMARREE.value: "En cours",
    StatutFamille.SOCLE_COMPLET.value: "À relire",
    StatutFamille.VALIDEE.value: "Validée",
}

#: Classe CSS de pastille associée à chaque état de famille.
CLASSES_STATUT_FAMILLE: dict[str, str] = {
    StatutFamille.NON_COMMENCEE.value: "attente",
    StatutFamille.DEMARREE.value: "attente",
    StatutFamille.SOCLE_COMPLET.value: "info",
    StatutFamille.VALIDEE.value: "ok",
}

#: Vocabulaire métier du statut d'une consultation déposée.
LIBELLES_STATUT_CONSULTATION: dict[str, str] = {
    "deposee": "Déposé",
    "nouvelle": "Déposé",
    "en_cours": "Analyse en cours",
    "analyse_en_cours": "Analyse en cours",
    "analysee": "Analysé",
    "analyse": "Analysé",
}

#: Familles dans lesquelles l'import guidé peut déposer un document (lot L3).
#: L'identité de l'entreprise n'y est pas : elle se saisit ou se reprend du dossier.
FAMILLES_IMPORT: tuple[str, ...] = (
    "references_chantiers",
    "certifications",
    "assurances",
    "moyens_humains",
    "moyens_materiels",
    "fiches_produits",
    "capacites_financieres",
    "memoire_technique",
)

#: Vocabulaire **métier** des états du mémoire et de ses sections — jamais un état de
#: code à l'écran (règle de la carte L5b).
LIBELLES_STATUT_DOSSIER_MEMOIRE: dict[str, str] = {
    "brouillon": "À compléter",
    "en_relecture": "En relecture",
    "valide": "Validé",
}
CLASSES_STATUT_DOSSIER_MEMOIRE: dict[str, str] = {
    "brouillon": "attente",
    "en_relecture": "info",
    "valide": "ok",
}
LIBELLES_STATUT_SECTION_MEMOIRE: dict[str, str] = {
    "brouillon": "À relire",
    "relue": "Relue",
    "validee": "Validée",
}
CLASSES_STATUT_SECTION_MEMOIRE: dict[str, str] = {
    "brouillon": "attente",
    "relue": "info",
    "validee": "ok",
}

#: Libellé métier des décisions humaines sur une proposition d'import.
LIBELLES_DECISION_PROPOSITION: dict[str, str] = {
    "acceptee": "Acceptée",
    "refusee": "Refusée",
}

#: Entité → famille, construit depuis le registre : sert au rendu des sources du
#: mémoire, pour nommer la famille en français sans exposer de nom de table.
_ENTITE_VERS_FAMILLE: dict[str, str] = {
    entite: famille
    for famille, entites in FAMILLE_VERS_ENTITES.items()
    for entite in entites
}


# --------------------------------------------------------------------------- #
# Session d'écran
# --------------------------------------------------------------------------- #
def _service_authentification(
    request: Request, connexion: Connexion
) -> ServiceAuthentification:
    config = obtenir_config(request)
    return ServiceAuthentification(
        connexion=connexion,
        cle_session=config.cle_session,
        duree_session_secondes=config.duree_session_secondes,
    )


def _ouvrir_session(request: Request, connexion: Connexion):
    """Identité de session, ou `None`. Pose le contexte client de l'écran."""
    service = _service_authentification(request, connexion)
    try:
        identite = service.lire_session(request.cookies.get(NOM_COOKIE_SESSION))
    except ErreurAuthentification:
        return None
    request.state.identite = identite
    request.state.contexte_client = ContexteClient(identite.client_id)
    return identite


def _redirection_connexion(request: Request) -> RedirectResponse:
    """Écran HTML sans session : on renvoie vers la connexion (jamais de données)."""
    return RedirectResponse(
        f"/connexion?suivant={quote(request.url.path)}", status_code=303
    )


def _rendre(
    request: Request,
    gabarit: str,
    contexte: Mapping[str, Any] | None = None,
    code: int = 200,
) -> Response:
    donnees: dict[str, Any] = dict(contexte or {})
    donnees.setdefault("identite", getattr(request.state, "identite", None))
    donnees.setdefault("mention_brouillon", MENTION_BROUILLON)
    donnees.setdefault("erreur", None)
    donnees.setdefault("message_ok", None)
    donnees.setdefault("ecran", None)
    donnees.setdefault("documents", {})
    return GABARITS.TemplateResponse(
        request=request, name=gabarit, context=donnees, status_code=code
    )


#: Erreurs d'écran : un titre qui parle, un sous-titre, et le détail technique
#: replié dans « Références techniques » (aucun code de code à l'écran).
ERREURS_ECRAN: dict[int, dict[str, str]] = {
    404: {
        "titre": "Cette page n'existe pas",
        "sous_titre": "L'adresse que vous avez ouverte ne correspond à aucun écran de votre espace.",
        "corps": "Le lien est peut-être incomplet, ou la page a été déplacée depuis que vous l'avez mise en favori.",
    },
    403: {
        "titre": "Cette page ne vous est pas ouverte",
        "sous_titre": "Ce que vous demandez existe, mais n'appartient pas à votre espace.",
        "corps": "Rien ne vous a été montré d'autre que vos propres données.",
    },
}


def _erreur_html(request: Request, code: int, message: str) -> Response:
    gabarit = ERREURS_ECRAN.get(code)
    if gabarit is None:
        gabarit = {
            "titre": "Cette action n'a pas pu aboutir",
            "sous_titre": "Rien n'a été enregistré. Vous pouvez corriger et recommencer.",
            "corps": message,
        }
    return _rendre(
        request,
        "erreur.html",
        {
            "code": code,
            "titre_erreur": gabarit["titre"],
            "sous_titre_erreur": gabarit["sous_titre"],
            "message": gabarit["corps"],
            "message_technique": message,
        },
        code,
    )


def _message_ok(request: Request) -> Optional[str]:
    return MESSAGES_OK.get(request.query_params.get("ok", ""))


def _message_erreur_url(request: Request) -> Optional[str]:
    valeur = request.query_params.get("erreur")
    return valeur or None


# --------------------------------------------------------------------------- #
# Fabriques de services (mêmes dépendances que les routes JSON)
# --------------------------------------------------------------------------- #
def _bibliotheque(
    request: Request, connexion: Connexion, contexte: ContexteClient
) -> ServiceBibliotheque:
    config = obtenir_config(request)
    return ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)


def _stockage(request: Request) -> StockageFichiers:
    config = obtenir_config(request)
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _date_lisible(valeur: Any) -> str:
    """Date au format jour/mois/année, jamais l'horodatage technique complet."""
    if valeur is None:
        return "—"
    if isinstance(valeur, (datetime, date)):
        return valeur.strftime("%d/%m/%Y")
    texte = str(valeur)
    if len(texte) >= 10 and texte[4] == "-" and texte[7] == "-":
        try:
            return datetime.strptime(texte[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:  # pragma: no cover — format inattendu, on rend la valeur lisible telle quelle
            return texte
    return texte


def _nombre_lisible(valeur: Any) -> str:
    """Nombre au format français : 412000.00 → « 412 000 »."""
    texte = str(valeur).strip().replace(" ", "")
    try:
        nombre = float(texte.replace(",", "."))
    except (TypeError, ValueError):
        return str(valeur)
    if nombre == int(nombre):
        return f"{int(nombre):,}".replace(",", " ")
    return f"{nombre:,.2f}".replace(",", " ").replace(".", ",")


#: Une valeur de nomenclature stockée s'écrit avec des tirets bas —
#: `responsabilite_civile_decennale`, `materiel_mise_en_oeuvre`. À l'écran, c'est
#: une écriture de code : elle se lit avec des espaces, comme le titre de l'élément
#: (`_titre_affiche`). Motif étroit : minuscules, chiffres et tirets bas seulement —
#: un code en majuscules (« SIREN », « SAS »), un montant ou une date ne sont pas
#: touchés.
_MOTIF_VALEUR_CODE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def _valeur_lisible(champ: str, valeur: Any, type_connu: Optional[str]) -> str:
    if type_connu == "date":
        return _date_lisible(valeur)
    if type_connu in ("entier", "decimal"):
        return _nombre_lisible(valeur)
    texte = str(valeur)
    if _MOTIF_VALEUR_CODE.match(texte.strip()):
        return texte.strip().replace("_", " ")
    return texte


#: Un identifiant de document n'est jamais montré tel quel : il devient le
#: libellé du document, ou une formule neutre si le libellé est introuvable.
_MOTIF_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _champs_affiches(
    ligne: Mapping[str, Any],
    bloc: Mapping[str, Any],
    documents: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """Ce qu'on montre d'un élément : des libellés métier et des valeurs lisibles.

    Trois retraits volontaires, tenus par la direction de design :
    * les champs de **liaison** (identifiants de documents) sortent du corps et
      vont dans « Références techniques » ;
    * un champ `…_devise` ne s'affiche pas seul : il est **accolé au montant**
      qu'il qualifie (« 412 000 EUR ») ;
    * les dates sont écrites en jour/mois/année, jamais en horodatage technique.
    """
    resultat: list[dict[str, str]] = []
    for champ in bloc["champs"]:
        if champ in bloc.get("liaisons", ()):
            continue
        if str(champ).endswith("_devise"):
            continue
        valeur = ligne.get(champ)
        if valeur in (None, ""):
            continue
        texte = _valeur_lisible(champ, valeur, bloc["types"].get(champ))
        if str(champ).endswith("_montant"):
            texte = _nombre_lisible(valeur)
            devise = str(
                ligne.get(str(champ)[: -len("_montant")] + "_devise") or ""
            ).strip()
            if devise:
                texte = f"{texte} {devise}"
        if _MOTIF_UUID.match(texte):
            texte = (documents or {}).get(texte) or "pièce fournie (document rattaché)"
        resultat.append({"libelle": bloc["libelles"].get(champ, champ), "valeur": texte})
    return resultat


def _titre_affiche(ligne: Mapping[str, Any]) -> str:
    """Titre d'un élément en clair : « responsabilite_civile » → « responsabilite civile ».

    Les tirets bas d'une valeur de nomenclature sont une écriture de code : on
    les rend lisibles dans le titre. La valeur exacte reste affichée, elle, dans
    la ligne du champ correspondant.
    """
    for champ in ("raison_sociale", "intitule_operation", "intitule", "description",
                  "designation", "type_assurance", "nom", "titre"):
        valeur = ligne.get(champ)
        if valeur:
            return str(valeur).replace("_", " ")
    return "Élément"


def _enrichir_lignes(
    contenu: Mapping[str, Any],
    blocs: Sequence[Mapping[str, Any]],
    documents: Mapping[str, str] | None = None,
) -> None:
    """Ajoute à chaque élément ses champs d'affichage et ses dates lisibles."""
    elements: Mapping[str, Any] = contenu.get("elements", {})
    for bloc in blocs:
        for ligne in elements.get(bloc["entite"], []):
            ligne["champs_affiches"] = _champs_affiches(ligne, bloc, documents)
            ligne["titre_affiche"] = _titre_affiche(ligne)
            ligne["date_affichee"] = _date_lisible(
                ligne.get("date_modification") or ligne.get("date_creation")
            )


def _statut_version_libelle(statut: Optional[str]) -> str:
    return LIBELLES_STATUT_VERSION.get(str(statut or ""), str(statut or "—"))


# --------------------------------------------------------------------------- #
# Critère 6 du plan de phase 4 : aucun code interne dans le corps d'un écran
# --------------------------------------------------------------------------- #
#: Un code métier entre crochets — `[attestation_assurance_decennale]` — est une
#: écriture de code produite par `app.services.checklist` (`_decrire_document`).
#: Il ne s'affiche jamais tel quel dans le corps de l'écran : le libellé métier
#: suffit, et le code reste disponible dans le bloc replié « Références
#: techniques » quand il sert au support. Motif volontairement étroit : une
#: crochetée en minuscules, trois caractères minimum — une mention française
#: comme « [FICTIF] » n'est pas touchée.
_MOTIF_CODE_CROCHETS = re.compile(r"\s*\[[a-z][a-z0-9_]{2,}\]")


def _sans_code_technique(texte: Any) -> str:
    """Rend un texte d'écran sans ses codes internes entre crochets."""
    return _MOTIF_CODE_CROCHETS.sub("", str(texte))


def _ligne_checklist_sans_code(ligne: Mapping[str, Any]) -> dict[str, Any]:
    """Une ligne de checklist dont les codes internes ne sortent plus dans le corps."""
    propre = dict(ligne)
    for champ in ("justification", "piece_libelle"):
        if propre.get(champ):
            propre[champ] = _sans_code_technique(propre[champ])
    return propre


def _codes_retenus(lignes: Sequence[Mapping[str, Any]]) -> list[str]:
    """Codes de type de pièce relevés dans les motifs, pour le bloc replié."""
    codes: set[str] = set()
    for ligne in lignes:
        for champ in ("justification", "piece_libelle"):
            for trouve in re.findall(r"\[([a-z][a-z0-9_]{2,})\]", str(ligne.get(champ) or "")):
                codes.add(trouve)
    return sorted(codes)


def _texte_libre_sans_code(valeur: Any) -> Any:
    """Même nettoyage pour une valeur qui peut être une liste ou un dictionnaire."""
    if isinstance(valeur, str):
        return _sans_code_technique(valeur)
    if isinstance(valeur, list):
        return [_texte_libre_sans_code(v) for v in valeur]
    if isinstance(valeur, dict):
        return {cle: _texte_libre_sans_code(v) for cle, v in valeur.items()}
    return valeur


def _entreprises_avec_fiche(service: ServiceBibliotheque, contexte: ContexteClient):
    """Entreprises du client, chacune avec sa dernière version de fiche."""
    resultat = []
    for entreprise in service.entreprises.lister(contexte):
        entreprise_id = str(entreprise["id"])
        versions = service.dernieres_fiches(entreprise_id)
        resultat.append(
            {
                "entreprise_id": entreprise_id,
                "libelle_court": entreprise["libelle_court"],
                "statut": entreprise["statut"],
                "derniere_fiche": (
                    {
                        "fiche_version_id": str(versions[0]["id"]),
                        "numero_version": int(versions[0]["numero_version"]),
                        "statut": str(versions[0]["statut"]),
                        "statut_libelle": _statut_version_libelle(versions[0]["statut"]),
                    }
                    if versions
                    else None
                ),
            }
        )
    return resultat


def _familles_affichees(etat: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Les neuf familles, avec un état **en français** et sa pastille."""
    resultat = []
    for famille in etat.get("familles", []):
        statut = str(famille.get("statut") or StatutFamille.NON_COMMENCEE.value)
        ligne = dict(famille)
        ligne["statut_libelle"] = LIBELLES_STATUT_FAMILLE.get(statut, statut)
        ligne["classe"] = CLASSES_STATUT_FAMILLE.get(statut, "attente")
        resultat.append(ligne)
    return resultat


def _resume_avancement(familles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Avancement dit en métier : « N familles renseignées sur 9 », jamais un taux nu."""
    total = len(familles) or 1
    renseignees = sum(1 for f in familles if int(f.get("nb_elements") or 0) > 0)
    vides = [f for f in familles if int(f.get("nb_elements") or 0) == 0]
    return {
        "nb_familles": len(familles),
        "nb_familles_renseignees": renseignees,
        "nb_familles_vides": len(vides),
        "familles_vides_libelles": [str(f.get("libelle")) for f in vides],
        "pourcentage": round(100 * renseignees / total, 1),
    }


def _consultations_pour_gabarit(
    connexion: Connexion, contexte: ContexteClient
) -> list[dict[str, Any]]:
    """Consultations du client, avec statut et date **lisibles** à l'écran."""
    resultat = []
    for consultation in DepotConsultation(connexion).lister_pour_client(contexte):
        ligne = dict(consultation)
        statut = str(ligne.get("statut") or "")
        ligne["statut_libelle"] = LIBELLES_STATUT_CONSULTATION.get(statut, "Déposé")
        ligne["date_lisible"] = _date_lisible(ligne.get("date_creation"))
        resultat.append(ligne)
    return resultat


def _libelles_documents(
    request: Request, connexion: Connexion, contexte: ContexteClient, lignes
) -> dict[str, str]:
    """Identifiant de document → son libellé humain (aucun UUID à l'écran)."""
    cle = obtenir_config(request).cle_chiffrement_maitresse
    depot = DepotDocument(connexion, cle)
    libelles: dict[str, str] = {}
    for ligne in lignes:
        document_id = str(ligne.get("source_document_id") or "")
        if not document_id or document_id in libelles:
            continue
        document = depot.obtenir(contexte, document_id)
        if document is not None:
            libelles[document_id] = str(document["libelle"])
    return libelles


def _libelle_champ(champ: str) -> str:
    return LIBELLES_CHAMPS.get(champ) or champ.replace("_", " ")


def _decrire_reference(
    service: ServiceBibliotheque, entite: str, champ: str
) -> Optional[dict[str, Any]]:
    """Un champ `code_reference` : son jeu, s'il est chargé, et ses valeurs.

    Un jeu **chargé** est une nomenclature fermée : seules ses valeurs sont
    acceptées par le service. Un jeu **non chargé** est une nomenclature
    ouverte : la valeur manquante peut être créée ici, sans quitter le formulaire.
    """
    namespace = reference_attendue(entite, champ)
    if not namespace:
        return None
    charge = service.references.namespace_charge(namespace)
    return {
        "namespace": namespace,
        "charge": charge,
        "valeurs": service.references.lister_valeurs(namespace) if charge else [],
    }


def _definitions_pour_gabarit(service: ServiceBibliotheque, famille: str):
    """Entités d'une famille, décrites pour le gabarit (champs, types, jeux)."""
    blocs = []
    for definition in definition_famille(famille):
        references = {}
        for champ in definition.champs:
            description = _decrire_reference(service, definition.entite, champ)
            if description:
                references[champ] = description
        blocs.append(
            {
                "entite": definition.entite,
                "libelle": definition.libelle,
                "champs": list(definition.champs),
                "libelles": {c: _libelle_champ(c) for c in definition.champs},
                "types": {
                    c: type_champ(definition.entite, c) for c in definition.champs
                },
                "references": references,
                "champs_obligatoires": list(definition.champs_obligatoires),
                # Champs de **liaison** (identifiants de documents) : ils sortent
                # du formulaire de saisie — un humain ne tape pas un UUID — et
                # restent consultables dans « Références techniques ».
                "liaisons": [liaison.champ for liaison in definition.liaisons],
            }
        )
    return blocs


def _familles_pour_gabarit(etat: Mapping[str, Any]):
    """Familles d'un état d'avancement, pour le gabarit de validation."""
    return list(etat.get("familles", []))


# --------------------------------------------------------------------------- #
# Connexion / déconnexion
# --------------------------------------------------------------------------- #
@router.get("/connexion", response_class=HTMLResponse)
def ecran_connexion(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Écran de connexion. Un compte est provisionné par l'exploitant, pas ici."""
    if _ouvrir_session(request, connexion) is not None:
        return RedirectResponse("/accueil", status_code=303)
    return _rendre(request, "connexion.html")


@router.post("/connexion", response_class=HTMLResponse)
def ouvrir_session(
    request: Request,
    identifiant: str = Form(...),
    mot_de_passe: str = Form(...),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Ouvre la session (même cookie signé que l'API) ou réaffiche l'écran en 401."""
    service = _service_authentification(request, connexion)
    identite = service.authentifier(identifiant, mot_de_passe)
    if identite is None:
        # Message volontairement générique : ne révèle pas si l'identifiant existe.
        return _rendre(
            request,
            "connexion.html",
            {"erreur": "Identifiant ou mot de passe incorrect."},
            401,
        )
    config = obtenir_config(request)
    reponse = RedirectResponse("/accueil", status_code=303)
    reponse.set_cookie(
        key=NOM_COOKIE_SESSION,
        value=service.creer_cookie_session(identite),
        max_age=config.duree_session_secondes,
        httponly=True,
        samesite="lax",
        secure=False,  # localhost sans TLS : à passer à True derrière HTTPS
        path="/",
    )
    return reponse


@router.post("/deconnexion")
def fermer_session() -> RedirectResponse:
    reponse = RedirectResponse("/connexion", status_code=303)
    reponse.delete_cookie(NOM_COOKIE_SESSION, path="/")
    return reponse


# --------------------------------------------------------------------------- #
# Accueil — ce que la plateforme apporte, et où en est l'utilisateur
# --------------------------------------------------------------------------- #
@router.get("/accueil", response_class=HTMLResponse)
def ecran_accueil(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Écran d'accueil : la promesse, l'avancement réel, une action principale."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    entreprises = _entreprises_avec_fiche(service, contexte)

    familles: list[dict[str, Any]] = []
    if entreprises:
        fiche = service.fiche_courante()
        if fiche is not None:
            familles = _familles_affichees(service.etat_avancement(str(fiche["id"])))

    consultations = _consultations_pour_gabarit(connexion, contexte)
    return _rendre(
        request,
        "accueil.html",
        {
            "ecran": "accueil",
            "entreprises": entreprises,
            "resume": {
                **_resume_avancement(familles),
                "nb_consultations": len(consultations),
            },
            "message_ok": _message_ok(request),
        },
    )


# --------------------------------------------------------------------------- #
# Première utilisation / entreprises / fiches
# --------------------------------------------------------------------------- #
@router.get("/entreprises/nouvelle", response_class=HTMLResponse)
def ecran_premiere_utilisation(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Écran de première utilisation : créer l'entreprise et sa première fiche."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    return _rendre(
        request,
        "premiere_utilisation.html",
        {
            "entreprises": _entreprises_avec_fiche(service, contexte),
            "erreur": _message_erreur_url(request),
        },
    )


@router.post("/entreprises", response_class=HTMLResponse)
def creer_entreprise(
    request: Request,
    libelle_court: str = Form(...),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Crée l'entreprise **et** sa première `fiche_version`, dans une transaction."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    try:
        entreprise_id = service.creer_entreprise(libelle_court)
        service.ouvrir_fiche(
            entreprise_id, commentaire="Première version — création de l'entreprise"
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement, ErreurDepot) as exc:
        connexion.annuler()
        return _rendre(
            request,
            "premiere_utilisation.html",
            {
                "entreprises": _entreprises_avec_fiche(service, contexte),
                "erreur": str(exc),
            },
            400,
        )
    return RedirectResponse("/bibliotheque?ok=entreprise_creee", status_code=303)


@router.post("/entreprises/{entreprise_id}/fiches", response_class=HTMLResponse)
def ouvrir_fiche(
    request: Request,
    entreprise_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Ouvre une nouvelle version de fiche — appartenance vérifiée **avant** écriture."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    if service.entreprises.obtenir(contexte, entreprise_id) is None:
        return _erreur_html(
            request,
            404,
            "Entreprise inconnue pour ce client. Aucune écriture n'a été effectuée.",
        )
    try:
        service.ouvrir_fiche(entreprise_id)
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement, ErreurDepot) as exc:
        connexion.annuler()
        return _erreur_html(request, 400, str(exc))
    return RedirectResponse("/bibliotheque?ok=fiche_ouverte", status_code=303)


# --------------------------------------------------------------------------- #
# Bibliothèque : état d'avancement
# --------------------------------------------------------------------------- #
@router.get("/bibliotheque", response_class=HTMLResponse)
def ecran_bibliotheque(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """État d'avancement, ou écran de première utilisation s'il n'y a rien."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    entreprises = _entreprises_avec_fiche(service, contexte)
    if not entreprises:
        return _rendre(
            request,
            "premiere_utilisation.html",
            {"entreprises": entreprises, "erreur": _message_erreur_url(request)},
        )
    fiche = service.fiche_courante()
    etat = service.etat_avancement(str(fiche["id"])) if fiche else None
    familles = _familles_affichees(etat) if etat else []
    return _rendre(
        request,
        "bibliotheque.html",
        {
            "ecran": "bibliotheque",
            "entreprises": entreprises,
            "fiche": fiche,
            "etat": etat,
            "familles": familles,
            "resume": _resume_avancement(familles),
            "message_ok": _message_ok(request),
            "erreur": _message_erreur_url(request),
        },
    )


@router.post("/bibliotheque/validation", response_class=HTMLResponse)
def valider_bibliotheque(
    request: Request,
    fiche_version_id: str = Form(...),
    relecteur_nom: str = Form(...),
    attestation_cochee: Optional[str] = Form(None),
    cible_type: str = Form("fiche"),
    famille_code: Optional[str] = Form(None),
    commentaire: Optional[str] = Form(None),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Verrou humain n° 1 : relecteur nommé **et** attestation cochée.

    La case non cochée est un refus, jamais un avertissement : le service lève,
    et aucun état validé n'est écrit.
    """
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    try:
        service.valider_fiche(
            fiche_version_id,
            relecteur_nom=relecteur_nom,
            attestation_cochee=bool(attestation_cochee),
            cible_type=cible_type,
            famille_code=(famille_code or None),
            commentaire=commentaire,
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/bibliotheque?erreur={quote(str(exc))}", status_code=303
        )
    return RedirectResponse("/bibliotheque?ok=validation_enregistree", status_code=303)


# --------------------------------------------------------------------------- #
# Import guidé — **enregistré avant `/bibliotheque/{famille}`** : Starlette essaie
# les routes dans leur ordre de déclaration, et `/bibliotheque/import` doit être
# reconnu comme un écran à part entière, pas comme le nom d'une famille.
# --------------------------------------------------------------------------- #
@router.get("/bibliotheque/import", response_class=HTMLResponse)
def ecran_import_guide(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Import guidé : dépôt des documents, propositions à valider **une par une**."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    return _rendre(
        request,
        "import_guide.html",
        _contexte_import_guide(
            request,
            connexion,
            contexte,
            erreur=_message_erreur_url(request),
            message_ok=_message_ok(request),
        ),
    )


@router.post("/bibliotheque/import", response_class=HTMLResponse)
async def traiter_import(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Un seul chemin POST : lire un document déposé, ou décider d'une proposition."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    formulaire = await request.form()
    action = str(formulaire.get("action") or "analyser").strip().casefold()
    if action in ("accepter", "refuser"):
        return _decider_proposition_import(
            request, connexion, contexte, formulaire, action
        )
    return await _analyser_document_importe(request, connexion, contexte, formulaire)


# --------------------------------------------------------------------------- #
# Bibliothèque : une famille
# --------------------------------------------------------------------------- #
@router.get("/bibliotheque/{famille}", response_class=HTMLResponse)
def ecran_famille(
    request: Request,
    famille: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Contenu d'une famille + formulaires de saisie (une entité par formulaire)."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    if famille not in FAMILLE_VERS_ENTITES:
        return _erreur_html(request, 404, f"Famille inconnue : {famille}")
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    fiche = service.fiche_courante()
    if fiche is None:
        return _erreur_html(
            request,
            404,
            "Aucune version de fiche pour ce client : créez d'abord une entreprise.",
        )
    fiche_version_id = request.query_params.get("fiche_version_id") or str(fiche["id"])
    try:
        contenu = service.consulter_famille(famille, fiche_version_id)
        statut_fiche = service.versionnement.statut_fiche(fiche_version_id)
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        return _erreur_html(request, 404, str(exc))
    definitions = _definitions_pour_gabarit(service, famille)
    documents = _libelles_documents(
        request,
        connexion,
        contexte,
        [ligne for lignes in contenu["elements"].values() for ligne in lignes],
    )
    _enrichir_lignes(contenu, definitions, documents)
    return _rendre(
        request,
        "famille.html",
        {
            "ecran": "bibliotheque",
            "famille": famille,
            "libelle": LIBELLES_FAMILLES.get(famille, famille),
            "fiche_version_id": fiche_version_id,
            "contenu": contenu,
            "statut_fiche": _statut_version_libelle(statut_fiche),
            "definitions": definitions,
            "saisie": {},
            "documents": documents,
            "message_ok": _message_ok(request),
            "erreur": _message_erreur_url(request),
        },
    )


@router.post("/bibliotheque/{famille}", response_class=HTMLResponse)
async def saisir_element(
    request: Request,
    famille: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Crée ou modifie un élément d'une famille. Toute écriture révoque la validation.

    `origine` est obligatoire (règle de traçabilité) ; une valeur de
    `code_reference` absente de la liste peut être saisie dans le champ
    « valeur absente de la liste », sans quitter le formulaire.
    """
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    if famille not in FAMILLE_VERS_ENTITES:
        return _erreur_html(request, 404, f"Famille inconnue : {famille}")
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)

    formulaire = await request.form()
    entite = str(formulaire.get("entite") or "")
    if entite not in FAMILLE_VERS_ENTITES[famille]:
        return _erreur_html(
            request, 400, f"Entité {entite!r} inconnue dans la famille {famille!r}."
        )

    definition = definition_entite(entite)
    donnees: dict[str, Any] = {}
    for champ in definition.champs:
        nouvelle = str(formulaire.get(f"champ_{champ}__nouvelle") or "").strip()
        valeur = nouvelle or str(formulaire.get(f"champ_{champ}") or "").strip()
        if valeur:
            donnees[champ] = valeur
    for commun in (
        "origine",
        "confiance",
        "source_document_id",
        "sensibilite",
        "statut_enregistrement",
    ):
        valeur = str(formulaire.get(commun) or "").strip()
        if valeur:
            donnees[commun] = valeur

    fiche_version_id = str(formulaire.get("fiche_version_id") or "")
    if not fiche_version_id:
        fiche = service.fiche_courante()
        if fiche is None:
            return _erreur_html(
                request, 404, "Aucune version de fiche pour ce client."
            )
        fiche_version_id = str(fiche["id"])

    element_id = str(formulaire.get("element_id") or "").strip() or None
    controle = str(formulaire.get("controle_humain_par") or "").strip() or None
    try:
        service.saisir(
            famille,
            entite,
            fiche_version_id,
            donnees,
            element_id=element_id,
            controle_humain_par=controle,
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement, ErreurDepot) as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/bibliotheque/{quote(famille)}?erreur={quote(str(exc))}", status_code=303
        )
    return RedirectResponse(
        f"/bibliotheque/{quote(famille)}?ok=element_enregistre", status_code=303
    )


# --------------------------------------------------------------------------- #
# Consultations : dépôt et analyse
# --------------------------------------------------------------------------- #
@router.get("/consultations", response_class=HTMLResponse)
def ecran_consultations(
    request: Request, connexion: Connexion = Depends(obtenir_connexion)
) -> Response:
    """Écran de fourniture d'un DCE et rappel des consultations du client."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    return _rendre(
        request,
        "consultations.html",
        {
            "ecran": "consultations",
            "entreprises": _entreprises_avec_fiche(service, contexte),
            "consultations": _consultations_pour_gabarit(connexion, contexte),
            "message_ok": _message_ok(request),
            "erreur": _message_erreur_url(request),
        },
    )


@router.post("/consultations", response_class=HTMLResponse)
async def fournir_document(
    request: Request,
    libelle: str = Form(...),
    entreprise_id: str = Form(...),
    fichier: UploadFile = File(...),
    reference_consultation: Optional[str] = Form(None),
    maitre_ouvrage_declare: Optional[str] = Form(None),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Enregistre le document fourni, l'analyse et renvoie vers l'analyse.

    L'outil ne va rien chercher : le document vient de l'utilisateur.
    """
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    service = _bibliotheque(request, connexion, contexte)
    contenu = await fichier.read()
    erreur = None
    if len(contenu) > TAILLE_MAX_DOCUMENT:
        erreur = (
            f"Fichier refusé : supérieur à {TAILLE_MAX_DOCUMENT // (1024 * 1024)} Mo."
        )
    resultat = None
    if erreur is None:
        try:
            resultat = analyse_dce.deposer_et_analyser(
                connexion,
                contexte,
                _stockage(request),
                entreprise_id=entreprise_id,
                libelle=libelle,
                nom_fichier=fichier.filename or "document.pdf",
                contenu=contenu,
                type_mime=fichier.content_type,
                reference_consultation=reference_consultation,
                maitre_ouvrage_declare=maitre_ouvrage_declare,
            )
        except (ErreurAnalyseDce, ErreurDepot) as exc:
            connexion.annuler()
            erreur = str(exc)
    if erreur is not None:
        return _rendre(
            request,
            "consultations.html",
            {
                "ecran": "consultations",
                "entreprises": _entreprises_avec_fiche(service, contexte),
                "consultations": _consultations_pour_gabarit(connexion, contexte),
                "erreur": erreur,
            },
            400,
        )
    assert resultat is not None
    return RedirectResponse(
        f"/consultations/{resultat.consultation['id']}?ok=document_analyse",
        status_code=303,
    )


@router.get("/consultations/{consultation_id}", response_class=HTMLResponse)
def ecran_consultation(
    request: Request,
    consultation_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Analyse : éléments extraits, **chacun avec sa source**, et absences déclarées."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    try:
        lecture = analyse_dce.lire_consultation(connexion, contexte, consultation_id)
    except ConsultationIntrouvable as exc:
        return _erreur_html(request, 404, str(exc))
    consultation = dict(lecture["consultation"])
    consultation["date_lisible"] = _date_lisible(consultation.get("date_creation"))
    elements = []
    for element in lecture["elements"]:
        ligne = dict(element)
        ligne["valeur_lisible"] = _date_lisible(ligne.get("valeur"))
        elements.append(ligne)
    return _rendre(
        request,
        "consultation.html",
        {
            "ecran": "consultations",
            "consultation": consultation,
            "document": lecture["document"],
            "elements": elements,
            "elements_non_trouves": lecture["elements_non_trouves"],
            "categories": analyse_dce.LIBELLES_CATEGORIES,
            "message_ok": _message_ok(request),
            "erreur": _message_erreur_url(request),
        },
    )


@router.post(
    "/consultations/{consultation_id}/elements/{element_id}",
    response_class=HTMLResponse,
)
async def verifier_element(
    request: Request,
    consultation_id: str,
    element_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Verrou humain n° 2 : valider / corriger / supprimer un élément extrait.

    `verificateur_nom` est exigé par le service pour `valider` et `corriger` :
    aucun chemin de cet écran ne pose un élément validé sans humain nommé.
    """
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    formulaire = await request.form()
    try:
        analyse_dce.verifier_element(
            connexion,
            contexte,
            consultation_id=consultation_id,
            element_id=element_id,
            action=str(formulaire.get("action") or ""),
            verificateur_nom=(str(formulaire.get("verificateur_nom") or "") or None),
            libelle=(str(formulaire.get("libelle") or "") or None),
            valeur=(str(formulaire.get("valeur") or "") or None),
        )
        connexion.valider()
    except ConsultationIntrouvable as exc:
        connexion.annuler()
        return _erreur_html(request, 404, str(exc))
    except ErreurAnalyseDce as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/consultations/{quote(consultation_id)}?erreur={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(
        f"/consultations/{quote(consultation_id)}?ok=element_verifie", status_code=303
    )


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #
@router.post(
    "/consultations/{consultation_id}/checklist", response_class=HTMLResponse
)
async def executer_checklist(
    request: Request,
    consultation_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Exécute la checklist — action nommée (`execute_par` obligatoire)."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    formulaire = await request.form()
    try:
        checklist.executer_checklist(
            connexion,
            contexte,
            consultation_id=consultation_id,
            execute_par=str(formulaire.get("execute_par") or ""),
            fiche_version_id=(str(formulaire.get("fiche_version_id") or "") or None),
        )
    except ConsultationIntrouvable as exc:
        connexion.annuler()
        return _erreur_html(request, 404, str(exc))
    except ErreurChecklist as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/consultations/{quote(consultation_id)}?erreur={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(
        f"/consultations/{quote(consultation_id)}/checklist?ok=checklist_executee",
        status_code=303,
    )


# --------------------------------------------------------------------------- #
# Lot L5b — import guidé : aides de rendu
# --------------------------------------------------------------------------- #
def _poids_lisible(poids: Any) -> Optional[str]:
    """Pondération affichée à la française, sans zéro inutile (« 40 », pas « 40.00 »)."""
    if poids in (None, ""):
        return None
    try:
        nombre = Decimal(str(poids))
    except (InvalidOperation, ValueError):
        return str(poids)
    return format(nombre.normalize(), "f")


def _proposition_pour_gabarit(ligne: Mapping[str, Any]) -> dict[str, Any]:
    """Une proposition d'import, prête à l'écran : libellés métier, champs saisissables.

    Deux retraits volontaires :
    * un champ dont la valeur est un **identifiant de document** n'est pas montré comme
      une saisie (on ne tape pas d'identifiant interne) — il est rattaché
      automatiquement au document importé à l'acceptation ;
    * les noms d'entité et de famille sont remplacés par leurs libellés français.
    """
    proposition = dict(ligne)
    entite = str(proposition.get("entite_cible") or "")
    champs = dict(proposition.get("champs_proposes") or {})
    try:
        definition = definition_entite(entite)
        libelle_entite = definition.libelle
        famille = definition.famille
        obligatoires = list(definition.champs_obligatoires)
    except KeyError:  # pragma: no cover — le service refuse déjà ces propositions
        libelle_entite = entite.replace("_", " ")
        famille = str(proposition.get("famille") or "")
        obligatoires = []

    champs_affiches = []
    for champ, valeur in champs.items():
        texte = str(valeur)
        est_reference = bool(_MOTIF_UUID.match(texte))
        champs_affiches.append(
            {
                "champ": champ,
                "libelle": _libelle_champ(champ),
                "valeur": "" if est_reference else texte,
                "reference_document": est_reference,
            }
        )
    manquants = [champ for champ in obligatoires if not champs.get(champ)]
    emplacement = str(proposition.get("source_emplacement") or "")
    proposition.update(
        {
            "entite": entite,
            "entite_libelle": libelle_entite,
            "famille_libelle": LIBELLES_FAMILLES.get(famille, famille),
            "champs_affiches": champs_affiches,
            "champs_manquants_libelles": [_libelle_champ(c) for c in manquants],
            "complet": not manquants,
            # L'emplacement vient du document ; le nom d'entité qu'il peut citer est
            # une écriture de code : il est remplacé par son libellé français.
            "source_emplacement_lisible": (
                emplacement.replace(entite, libelle_entite) if entite else emplacement
            ),
        }
    )
    return proposition


def _propositions_import(
    connexion: Connexion, contexte: ContexteClient
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Propositions du client : celles à décider (une par une) et celles déjà décidées."""
    en_attente: list[dict[str, Any]] = []
    decidees: list[dict[str, Any]] = []
    for entree in import_guide.lister_imports(connexion, contexte):
        detail = import_guide.lire_import_document(connexion, contexte, str(entree["id"]))
        document = detail.get("document") or {}
        libelle_document = str(
            document.get("libelle")
            or entree.get("document_libelle")
            or "document importé"
        )
        for proposition in detail.get("propositions") or []:
            statut = str(proposition.get("statut") or "")
            item = {
                "proposition": _proposition_pour_gabarit(proposition),
                "document_libelle": libelle_document,
            }
            if statut == "propose":
                en_attente.append(item)
                continue
            item.update(
                {
                    "statut_libelle": LIBELLES_DECISION_PROPOSITION.get(statut, statut),
                    "classe": "ok" if statut == "acceptee" else "attente",
                    "decision_le": _date_lisible(proposition.get("date_decision")),
                    "decide_par": str(proposition.get("decide_par") or ""),
                }
            )
            decidees.append(item)
    return en_attente, decidees


def _contexte_import_guide(
    request: Request,
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    erreur: Optional[str] = None,
    conseil: Optional[str] = None,
    message_ok: Optional[str] = None,
) -> dict[str, Any]:
    """Tout ce que l'écran d'import affiche : dépôt, propositions, état d'avancement."""
    service = _bibliotheque(request, connexion, contexte)
    entreprises = _entreprises_avec_fiche(service, contexte)
    fiche = service.fiche_courante() if entreprises else None
    donnees: dict[str, Any] = {
        "ecran": "bibliotheque",
        "entreprises": entreprises,
        "familles": [
            {"code": code, "libelle": LIBELLES_FAMILLES.get(code, code)}
            for code in FAMILLES_IMPORT
        ],
        "sans_fiche": fiche is None,
        "en_attente": [],
        "prochain": None,
        "decidees": [],
        "avancement": None,
        "erreur": erreur,
        "conseil": conseil,
        "message_ok": message_ok,
    }
    if fiche is None:
        return donnees
    en_attente, decidees = _propositions_import(connexion, contexte)
    avancement = import_guide.etat_avancement_utile(
        connexion,
        obtenir_config(request).cle_chiffrement_maitresse,
        contexte,
        str(fiche["id"]),
    )
    familles_avancement = []
    for famille in avancement.get("familles", []):
        ligne = dict(famille)
        ligne["classe"] = "ok" if ligne.get("prete") else "attente"
        familles_avancement.append(ligne)
    donnees.update(
        {
            "en_attente": en_attente,
            "prochain": en_attente[0] if en_attente else None,
            "decidees": decidees,
            "avancement": {**avancement, "familles": familles_avancement},
        }
    )
    return donnees


# --------------------------------------------------------------------------- #
# Lot L5b — mémoire technique : aides de rendu
# --------------------------------------------------------------------------- #
def _source_pour_gabarit(source: Mapping[str, Any]) -> dict[str, str]:
    """Une source citée : son libellé lisible, et la famille où elle se trouve.

    Le nom de **table** n'est jamais montré : il est traduit en nom de famille
    française. L'emplacement technique reste disponible dans « Références techniques ».
    """
    table = str(source.get("table_source") or "")
    famille = _ENTITE_VERS_FAMILLE.get(table)
    return {
        "libelle": str(source.get("libelle_source") or ""),
        "famille_libelle": LIBELLES_FAMILLES.get(famille, "") if famille else "",
        "detail": str(source.get("emplacement_source") or ""),
    }


def _sections_pour_gabarit(sections: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Sections du mémoire, avec leur état dit en métier et les actions permises."""
    resultat = []
    for section in sections:
        statut = str(section.get("statut") or "brouillon")
        if statut == "brouillon":
            actions = [
                {"statut": "relue", "libelle": "Relire cette section",
                 "classe": "btn btn--secondaire"},
            ]
        elif statut == "relue":
            actions = [
                {"statut": "validee", "libelle": "Valider cette section",
                 "classe": "btn btn--secondaire"},
                {"statut": "brouillon", "libelle": "Marquer à corriger",
                 "classe": "btn btn--discret"},
            ]
        else:
            actions = [
                {"statut": "relue", "libelle": "Remettre en relecture",
                 "classe": "btn btn--discret"},
            ]
        resultat.append(
            {
                **dict(section),
                "statut_libelle": LIBELLES_STATUT_SECTION_MEMOIRE.get(statut, statut),
                "classe": CLASSES_STATUT_SECTION_MEMOIRE.get(statut, "attente"),
                "poids_lisible": _poids_lisible(section.get("critere_poids")),
                "sources_affichees": [
                    _source_pour_gabarit(s) for s in (section.get("sources") or [])
                ],
                "statut_le_lisible": _date_lisible(section.get("statut_le")),
                "actions": actions,
            }
        )
    return resultat


def _manques_pour_gabarit(manques: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Manques du mémoire : le constat, l'action à mener, et où l'information s'ajoute."""
    resultat = []
    for manque in manques:
        familles = familles_pour_critere(manque.get("critere_libelle"))
        cible = familles[0] if familles else None
        resultat.append(
            {
                **dict(manque),
                "poids_lisible": _poids_lisible(manque.get("critere_poids")),
                "familles_cibles": list(familles),
                "famille_cible": cible,
                "famille_cible_libelle": LIBELLES_FAMILLES.get(cible) if cible else None,
                "hors_perimetre": not familles,
            }
        )
    return resultat


def _contexte_memoire(
    request: Request,
    connexion: Connexion,
    contexte: ContexteClient,
    consultation: Mapping[str, Any],
    elements: Sequence[Mapping[str, Any]],
    *,
    erreur: Optional[str] = None,
    conseil: Optional[str] = None,
    message_ok: Optional[str] = None,
) -> dict[str, Any]:
    """Tout ce que l'écran du mémoire affiche : sections, sources, manques, validation."""
    criteres = [dict(e) for e in elements if str(e.get("categorie")) == "critere"]
    acceptes = [c for c in criteres if str(c.get("statut_verification")) == "valide"]
    donnees: dict[str, Any] = {
        "ecran": "consultations",
        "consultation": dict(consultation),
        "nb_criteres": len(criteres),
        "nb_criteres_acceptes": len(acceptes),
        "memoire": None,
        "sections": [],
        "manques": [],
        "validations": [],
        "sections_a_relire": [],
        "pret_a_valider": False,
        "valide": False,
        "erreur": erreur,
        "conseil": conseil,
        "message_ok": message_ok,
    }
    try:
        memoire = memoire_technique.lire_memoire(
            connexion, contexte, str(consultation["id"])
        )
    except MemoireIntrouvable:
        return donnees

    dossier = dict(memoire["dossier"])
    statut = str(dossier.get("statut") or "brouillon")
    sections = _sections_pour_gabarit(memoire["sections"])
    a_relire = [s for s in sections if str(s.get("statut")) == "brouillon"]
    validations = []
    for validation in memoire.get("validations") or []:
        ligne = dict(validation)
        ligne["horodatage_lisible"] = _date_lisible(ligne.get("horodatage"))
        validations.append(ligne)
    donnees.update(
        {
            "memoire": {
                "dossier": dossier,
                "titre": str(dossier.get("titre") or "Mémoire technique"),
                "statut_libelle": LIBELLES_STATUT_DOSSIER_MEMOIRE.get(statut, statut),
                "classe": CLASSES_STATUT_DOSSIER_MEMOIRE.get(statut, "attente"),
                "genere_le": _date_lisible(dossier.get("date_creation")),
                "avertissement": str(dossier.get("avertissement") or ""),
                "resume": dict(memoire.get("resume") or {}),
            },
            "sections": sections,
            "manques": _manques_pour_gabarit(memoire["manques"]),
            "validations": validations,
            "sections_a_relire": a_relire,
            "pret_a_valider": bool(sections) and not a_relire,
            "valide": statut == "valide",
        }
    )
    return donnees


# --------------------------------------------------------------------------- #
# Import guidé : aides de rendu et corps des routes
# (les deux routes HTTP sont enregistrées plus haut, avant `/bibliotheque/{famille}`)
# --------------------------------------------------------------------------- #
def _decider_proposition_import(
    request: Request,
    connexion: Connexion,
    contexte: ContexteClient,
    formulaire: Mapping[str, Any],
    action: str,
) -> Response:
    """Accepter ou refuser une proposition — décision humaine **nommée** et horodatée."""
    proposition_id = str(formulaire.get("proposition_id") or "").strip()
    decide_par = str(formulaire.get("decide_par") or "").strip()
    corrections = {
        str(cle)[len("champ_"):]: str(valeur)
        for cle, valeur in formulaire.items()
        if isinstance(cle, str) and cle.startswith("champ_") and isinstance(valeur, str)
    }
    try:
        import_guide.decider_proposition(
            connexion,
            obtenir_config(request).cle_chiffrement_maitresse,
            contexte,
            proposition_id=proposition_id,
            decision=action,
            decide_par=decide_par,
            corrections=corrections,
        )
    except ImportIntrouvable as exc:
        connexion.annuler()
        return _erreur_html(request, 404, str(exc))
    except ErreurImportGuide as exc:
        connexion.annuler()
        return _rendre(
            request,
            "import_guide.html",
            _contexte_import_guide(request, connexion, contexte, erreur=str(exc)),
        )
    ok = "proposition_acceptee" if action == "accepter" else "proposition_refusee"
    return RedirectResponse(f"/bibliotheque/import?ok={ok}", status_code=303)


async def _analyser_document_importe(
    request: Request,
    connexion: Connexion,
    contexte: ContexteClient,
    formulaire: Mapping[str, Any],
) -> Response:
    """Dépôt → lecture → propositions sourcées en attente de décision."""

    def _reecran(*, erreur: Optional[str] = None, conseil: Optional[str] = None) -> Response:
        return _rendre(
            request,
            "import_guide.html",
            _contexte_import_guide(
                request, connexion, contexte, erreur=erreur, conseil=conseil
            ),
        )

    famille_cible = str(formulaire.get("famille_cible") or "").strip()
    if famille_cible not in FAMILLES_IMPORT:
        return _reecran(
            erreur="Choisissez la famille dans laquelle ranger ce document : sans "
            "elle, l'outil ne sait pas où écrire."
        )
    fichier = formulaire.get("fichier")
    nom_fichier = str(getattr(fichier, "filename", "") or "")
    if fichier is None or not nom_fichier:
        return _reecran(
            erreur="Aucun fichier reçu. Choisissez un document PDF ou texte, puis "
            "relancez la lecture."
        )
    service = _bibliotheque(request, connexion, contexte)
    fiche = service.fiche_courante()
    if fiche is None:
        return _reecran(
            erreur="Votre bibliothèque n'existe pas encore : créez d'abord votre "
            "entreprise et sa fiche."
        )
    contenu = await fichier.read()
    if not contenu:
        return _reecran(erreur="Fichier vide : il n'y a rien à lire.")
    if len(contenu) > TAILLE_MAX_DOCUMENT:
        return _reecran(
            erreur=f"Fichier refusé : supérieur à {TAILLE_MAX_DOCUMENT // (1024 * 1024)} Mo."
        )
    try:
        import_guide.importer_document(
            connexion,
            contexte,
            _stockage(request),
            fiche_version_id=str(fiche["id"]),
            famille_cible=famille_cible,
            nom_fichier=nom_fichier,
            contenu=contenu,
            type_mime=getattr(fichier, "content_type", None),
        )
    except ImportNonValidable as exc:
        # Refus explicite du garde-fou anti-invention : un résultat, pas une panne.
        connexion.annuler()
        return _reecran(conseil=str(exc))
    except ErreurFournisseurModele:
        # La lecture automatique n'est pas active sur cette installation : on le dit
        # en français, sans jargon d'architecture, et rien n'est enregistré.
        connexion.annuler()
        return _reecran(
            conseil="La lecture automatique de vos documents n'est pas active sur cette "
            "installation : aucun élément ne peut en être tiré pour l'instant. Votre "
            "document n'a pas été enregistré. Vous pouvez saisir les informations à la "
            "main dans votre bibliothèque, ou recommencer plus tard."
        )
    except (ErreurImportGuide, ErreurAnalyseDce, ErreurDepot, ErreurBibliotheque) as exc:
        connexion.annuler()
        return _reecran(erreur=str(exc))
    return RedirectResponse("/bibliotheque/import?ok=import_depose", status_code=303)


# --------------------------------------------------------------------------- #
# Mémoire technique : génération, relecture, validation (chemins gelés § 2.D)
# --------------------------------------------------------------------------- #
def _charger_consultation_ecran(
    request: Request,
    connexion: Connexion,
    contexte: ContexteClient,
    consultation_id: str,
) -> tuple[Optional[dict[str, Any]], Optional[list[dict[str, Any]]], Optional[Response]]:
    """Charge l'analyse de la consultation ; 404 si elle appartient à un autre client."""
    try:
        lecture = analyse_dce.lire_consultation(connexion, contexte, consultation_id)
    except ConsultationIntrouvable as exc:
        return None, None, _erreur_html(request, 404, str(exc))
    consultation = dict(lecture["consultation"])
    consultation["date_lisible"] = _date_lisible(consultation.get("date_creation"))
    return consultation, [dict(e) for e in lecture["elements"]], None


@router.get("/consultations/{consultation_id}/memoire", response_class=HTMLResponse)
def ecran_memoire(
    request: Request,
    consultation_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Mémoire généré : sections dans l'ordre des critères, sources citées, manques."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    consultation, elements, reponse = _charger_consultation_ecran(
        request, connexion, contexte, consultation_id
    )
    if reponse is not None:
        return reponse
    return _rendre(
        request,
        "memoire.html",
        _contexte_memoire(
            request,
            connexion,
            contexte,
            consultation,  # type: ignore[arg-type]
            elements or [],
            erreur=_message_erreur_url(request),
            message_ok=_message_ok(request),
        ),
    )


@router.post("/consultations/{consultation_id}/memoire", response_class=HTMLResponse)
def demander_memoire(
    request: Request,
    consultation_id: str,
    titre: Optional[str] = Form(None),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Demande de génération — le plan suit les critères acceptés du dossier."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    try:
        memoire_technique.generer_memoire(
            connexion,
            obtenir_config(request).cle_chiffrement_maitresse,
            contexte,
            consultation_id=consultation_id,
            titre=(titre or None),
        )
    except MemoireIntrouvable as exc:
        connexion.annuler()
        return _erreur_html(request, 404, str(exc))
    except ErreurMemoire as exc:
        connexion.annuler()
        consultation, elements, reponse = _charger_consultation_ecran(
            request, connexion, contexte, consultation_id
        )
        if reponse is not None:
            return reponse
        return _rendre(
            request,
            "memoire.html",
            _contexte_memoire(
                request,
                connexion,
                contexte,
                consultation,  # type: ignore[arg-type]
                elements or [],
                conseil=str(exc),
            ),
        )
    return RedirectResponse(
        f"/consultations/{quote(consultation_id)}/memoire?ok=memoire_genere",
        status_code=303,
    )


@router.post(
    "/consultations/{consultation_id}/memoire/sections/{section_id}",
    response_class=HTMLResponse,
)
async def statut_section_memoire(
    request: Request,
    consultation_id: str,
    section_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Relire, valider ou remettre à corriger **une section** — humain nommé exigé."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    formulaire = await request.form()
    statut = str(formulaire.get("statut") or "").strip().casefold()
    par = str(formulaire.get("par") or "").strip()
    try:
        memoire = memoire_technique.lire_memoire(connexion, contexte, consultation_id)
    except MemoireIntrouvable as exc:
        return _erreur_html(request, 404, str(exc))
    # La section doit appartenir à un mémoire **de cette consultation** : 404 sinon.
    if section_id not in {str(s["id"]) for s in memoire["sections"]}:
        return _erreur_html(request, 404, "Section introuvable pour ce mémoire.")
    try:
        memoire_technique.changer_statut_section(
            connexion, contexte, section_id=section_id, statut=statut, par=par
        )
    except MemoireIntrouvable as exc:
        connexion.annuler()
        return _erreur_html(request, 404, str(exc))
    except ErreurMemoire as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/consultations/{quote(consultation_id)}/memoire?erreur={quote(str(exc))}",
            status_code=303,
        )
    message = {
        "relue": "section_relue",
        "validee": "section_validee",
        "brouillon": "section_a_corriger",
    }.get(statut, "")
    return RedirectResponse(
        f"/consultations/{quote(consultation_id)}/memoire?ok={message}", status_code=303
    )


@router.post(
    "/consultations/{consultation_id}/memoire/validation",
    response_class=HTMLResponse,
)
async def valider_memoire(
    request: Request,
    consultation_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Validation **nommée et horodatée** du mémoire entier — obligatoire avant export."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    formulaire = await request.form()
    try:
        memoire = memoire_technique.lire_memoire(connexion, contexte, consultation_id)
    except MemoireIntrouvable as exc:
        return _erreur_html(request, 404, str(exc))
    dossier_id = str(memoire["dossier"]["id"])
    try:
        memoire_technique.valider_dossier(
            connexion,
            contexte,
            dossier_id=dossier_id,
            nom_validateur=str(formulaire.get("nom_validateur") or ""),
            fonction_validateur=str(formulaire.get("fonction_validateur") or ""),
            format_export=(str(formulaire.get("format_export") or "") or None),
        )
    except ErreurMemoire as exc:
        connexion.annuler()
        return RedirectResponse(
            f"/consultations/{quote(consultation_id)}/memoire?erreur={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(
        f"/consultations/{quote(consultation_id)}/memoire?ok=memoire_valide",
        status_code=303,
    )


@router.get(
    "/consultations/{consultation_id}/checklist", response_class=HTMLResponse
)
def ecran_checklist(
    request: Request,
    consultation_id: str,
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Checklist : statuts `presente` / `manquante` / `a_verifier` et résumé des manques."""
    if _ouvrir_session(request, connexion) is None:
        return _redirection_connexion(request)
    contexte = request.state.contexte_client
    try:
        resultat = checklist.lire_checklist(connexion, contexte, consultation_id)
    except ConsultationIntrouvable as exc:
        return _erreur_html(request, 404, str(exc))
    except ChecklistIntrouvable:
        lecture = analyse_dce.lire_consultation(connexion, contexte, consultation_id)
        return _rendre(
            request,
            "checklist.html",
            {
                "ecran": "consultations",
                "consultation": lecture["consultation"],
                "pas_de_checklist": True,
                "message_ok": _message_ok(request),
            },
        )
    lignes = [_ligne_checklist_sans_code(ligne) for ligne in resultat["lignes"]]
    return _rendre(
        request,
        "checklist.html",
        {
            "ecran": "consultations",
            "consultation": resultat["consultation"],
            "execution": resultat["execution"],
            "lignes": lignes,
            "codes_retenus": _codes_retenus(resultat["lignes"]),
            "contradictions": _texte_libre_sans_code(resultat["contradictions"]),
            "resume": _texte_libre_sans_code(resultat["resume"]),
            "avertissements": _texte_libre_sans_code(resultat["avertissements"]),
            "mention": resultat["mention"],
            "pas_de_checklist": False,
            "message_ok": _message_ok(request),
        },
    )


# --------------------------------------------------------------------------- #
# Dernier recours : une adresse inconnue montre la page d'erreur du produit
# --------------------------------------------------------------------------- #
async def gestionnaire_404(request: Request, exc: Exception) -> Response:
    """Adresse inconnue : la page d'erreur du produit, pas le JSON de FastAPI.

    Enregistré sur l'application par `app.main` (`add_exception_handler(404, …)`) :
    un gestionnaire d'exception vit sur l'application, pas sur un routeur — c'est le
    seul endroit d'où le `{"detail":"Not Found"}` par défaut peut être remplacé.

    Deux garde-fous : le préfixe d'API et les fichiers statiques gardent **le
    gestionnaire JSON d'origine de FastAPI** (contrats de l'annexe C, et le message
    précis que la route a levé : « Provisionnez une entreprise », par exemple — un
    message générique les effacerait). Et le message d'écran ne reprend ni l'adresse
    demandée ni aucune donnée.
    """
    if request.url.path.startswith(("/api/", "/static/")):
        if isinstance(exc, HTTPException):  # message et en-têtes de la route, intacts
            return await http_exception_handler(request, exc)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    _poser_identite_sans_route(request)
    return _erreur_html(
        request,
        404,
        "Aucune route de l'application ne correspond à cette adresse.",
    )


def _poser_identite_sans_route(request: Request) -> None:
    """Barre de navigation juste, même quand aucune route n'a pu lire la session.

    Aucune route n'a été trouvée, donc aucune dépendance de route n'a posé
    `request.state.identite` : sans ça, la page d'erreur afficherait la navigation
    d'un visiteur déconnecté à un utilisateur connecté. On ouvre une connexion
    **uniquement** si un cookie de session est présent, et toute erreur est sans
    conséquence : la page d'erreur s'affiche de toute façon.
    """
    if not request.cookies.get(NOM_COOKIE_SESSION):
        return
    connexion: Optional[Connexion] = None
    try:
        config = obtenir_config(request)
        connexion = Connexion(config.database_url).ouvrir()
        _ouvrir_session(request, connexion)
    except Exception:  # noqa: BLE001 — une page d'erreur ne doit jamais échouer
        return
    finally:
        if connexion is not None:
            connexion.fermer()
