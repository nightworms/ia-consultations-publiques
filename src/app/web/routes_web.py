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

import os
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.cloisonnement import (
    NOM_COOKIE_SESSION,
    obtenir_config,
    obtenir_connexion,
)
from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    definition_entite,
    definition_famille,
    reference_attendue,
    type_champ,
)
from app.services import analyse_dce, checklist
from app.services.analyse_dce import ConsultationIntrouvable, ErreurAnalyseDce
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
from app.storage.repositories import ErreurDepot

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
    "forme_juridique_code": "Forme juridique (code)",
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
    "domaine_code": "Domaine (code)",
    "numero_certificat": "Numéro de certificat",
    "date_obtention": "Date d'obtention",
    "intitule_operation": "Intitulé de l'opération",
    "maitre_ouvrage": "Maître d'ouvrage",
    "nature_travaux_code": "Nature des travaux (code)",
    "nature_travaux_libelle": "Nature des travaux (libellé)",
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
    "photos": "Photos (identifiants de documents)",
    "metier_code": "Métier (code)",
    "metier_libelle": "Métier (libellé)",
    "nombre": "Nombre",
    "date_maj": "Date de mise à jour",
    "diplomes": "Diplômes",
    "annees_experience": "Années d'expérience",
    "cv_piece": "Pièce CV",
    "categorie_code": "Catégorie (code)",
    "designation": "Désignation",
    "quantite": "Quantité",
    "marque_modele": "Marque et modèle",
    "annee": "Année",
    "propriete": "Propriété",
    "disponibilite": "Disponibilité",
    "justificatif": "Justificatif",
    "fournisseur": "Fournisseur",
    "reference_produit": "Référence produit",
    "famille_code": "Famille de produit (code)",
    "domaine_application": "Domaine d'application",
    "fiche_technique": "Fiche technique",
    "avis_technique": "Avis technique",
    "date_validite_document": "Date de validité du document",
    "certificats": "Certificats (identifiants de documents)",
    "titre": "Titre",
    "ordre": "Ordre",
    "contenu_texte": "Contenu",
    "date_redaction": "Date de rédaction",
    "references_liees": "Références liées (identifiants)",
    "documents_associes": "Documents associés (identifiants)",
}

#: Messages affichés après une action réussie (paramètre `ok` de l'URL).
MESSAGES_OK: dict[str, str] = {
    "entreprise_creee": "Entreprise créée avec sa première version de fiche (aucune donnée déduite : le libellé vient de la saisie).",
    "fiche_ouverte": "Nouvelle version de fiche ouverte (numéro croissant par entreprise).",
    "element_enregistre": "Élément enregistré. Toute validation de relecture qui couvrait cette famille a été révoquée : la fiche repasse en relecture.",
    "validation_enregistree": "Relecture humaine enregistrée : nom du relecteur et horodatage posés au moment de l'action.",
    "document_analyse": "Document lu et analysé. Chaque élément proposé porte sa source ; aucun n'est un fait avant validation humaine.",
    "element_verifie": "Action humaine enregistrée sur l'élément.",
    "checklist_executee": "Checklist exécutée : elle croise les pièces exigées validées avec la bibliothèque.",
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
    return GABARITS.TemplateResponse(
        request=request, name=gabarit, context=donnees, status_code=code
    )


def _erreur_html(request: Request, code: int, message: str) -> Response:
    return _rendre(request, "erreur.html", {"code": code, "message": message}, code)


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
                    }
                    if versions
                    else None
                ),
            }
        )
    return resultat


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
        return RedirectResponse("/bibliotheque", status_code=303)
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
    reponse = RedirectResponse("/bibliotheque", status_code=303)
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
    return _rendre(
        request,
        "bibliotheque.html",
        {
            "entreprises": entreprises,
            "fiche": fiche,
            "etat": etat,
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
    return _rendre(
        request,
        "famille.html",
        {
            "famille": famille,
            "libelle": LIBELLES_FAMILLES.get(famille, famille),
            "fiche_version_id": fiche_version_id,
            "contenu": contenu,
            "statut_fiche": statut_fiche,
            "definitions": _definitions_pour_gabarit(service, famille),
            "saisie": {},
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
            "entreprises": _entreprises_avec_fiche(service, contexte),
            "consultations": DepotConsultation(connexion).lister_pour_client(contexte),
            "fournisseur": os.environ.get("MODELE_FOURNISSEUR", "factice"),
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
                "entreprises": _entreprises_avec_fiche(service, contexte),
                "consultations": DepotConsultation(connexion).lister_pour_client(
                    contexte
                ),
                "fournisseur": os.environ.get("MODELE_FOURNISSEUR", "factice"),
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
    return _rendre(
        request,
        "consultation.html",
        {
            "consultation": lecture["consultation"],
            "document": lecture["document"],
            "elements": lecture["elements"],
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
                "consultation": lecture["consultation"],
                "pas_de_checklist": True,
                "message_ok": _message_ok(request),
            },
        )
    return _rendre(
        request,
        "checklist.html",
        {
            "consultation": resultat["consultation"],
            "execution": resultat["execution"],
            "lignes": resultat["lignes"],
            "contradictions": resultat["contradictions"],
            "resume": resultat["resume"],
            "avertissements": resultat["avertissements"],
            "mention": resultat["mention"],
            "pas_de_checklist": False,
            "message_ok": _message_ok(request),
        },
    )
