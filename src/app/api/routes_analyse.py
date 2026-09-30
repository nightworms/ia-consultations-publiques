"""Routes JSON de la brique B — contrat **gelé** en annexe C du plan de phase 3.

Trois routes, pas une de plus :

======================================================  ==================================
`POST /api/v1/consultations`                            dépôt d'un DCE (multipart)
`GET  /api/v1/consultations/{id}`                       consultation et éléments, **avec leur source**
`POST /api/v1/consultations/{id}/elements/{element_id}` valider / corriger / supprimer un élément
======================================================  ==================================

Règles de réponse (annexe C) : toute valeur extraite est renvoyée avec `origine`,
`confiance`, `source_document_id` et `source_emplacement` ; une catégorie sans
résultat est renvoyée avec la mention explicite « non trouvé dans le document »,
jamais comblée.

Aucune donnée n'est lisible sans session : `exiger_contexte_client` refuse en 401, et
le `client_id` vient de la session, jamais de l'appelant (annexe A § A1).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.cloisonnement import (
    exiger_contexte_client,
    obtenir_config,
    obtenir_connexion,
)
from app.services import analyse_dce
from app.services.analyse_dce import (
    AnalyseNonValidable,
    ConsultationIntrouvable,
    ErreurAnalyseDce,
)
from app.services.fournisseur_modele import FournisseurModele, creer_fournisseur
from app.storage.connexion import Connexion, ContexteClient
from app.storage.fichiers import StockageFichiers

#: Taille maximale acceptée pour un dépôt (au-delà : refus explicite).
TAILLE_MAX_DEPOT = 25 * 1024 * 1024

router = APIRouter(prefix="/api/v1", tags=["analyse"])

MENTION_BROUILLON = "brouillon — à relire et à vérifier par un humain"


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #
def obtenir_stockage(request: Request) -> StockageFichiers:
    """Stockage des pièces, hors dépôt, chiffré par client (annexe A § A6)."""
    config = obtenir_config(request)
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def obtenir_fournisseur() -> FournisseurModele:
    """Fournisseur de modèle de la requête (décision D8).

    Dépendance explicite plutôt qu'appel direct : elle se remplace en test
    (`app.dependency_overrides`) sans réseau, et elle rend visible dans le contrat
    de la route que l'analyse passe bien par la couche d'abstraction.
    """
    return creer_fournisseur()


def _serialiser(valeur: Any) -> Any:
    """Rend une ligne SQL sérialisable en JSON, sans rien inventer."""
    if isinstance(valeur, dict):
        return {cle: _serialiser(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [_serialiser(v) for v in valeur]
    if isinstance(valeur, uuid.UUID):
        return str(valeur)
    if isinstance(valeur, (_dt.datetime, _dt.date)):
        return valeur.isoformat()
    return valeur


def _serialiser_element(ligne: dict[str, Any]) -> dict[str, Any]:
    """Élément renvoyé avec sa source et son statut de vérification (annexe C)."""
    element = _serialiser(ligne)
    element["origine"] = "document_extrait"
    element["mention"] = analyse_dce.MENTION_NON_VERIFIE if (
        element.get("statut_verification") == "propose"
    ) else None
    return element


def _erreur(exc: Exception, code: int) -> HTTPException:
    return HTTPException(status_code=code, detail=str(exc))


async def _lire_corps(request: Request) -> dict[str, str]:
    """Lit le corps d'une requête, en formulaire ou en JSON. Refus explicite sinon."""
    type_contenu = (request.headers.get("content-type") or "").split(";")[0].strip().casefold()
    try:
        if type_contenu == "application/json":
            donnees = await request.json()
        else:
            formulaire = await request.form()
            donnees = {cle: valeur for cle, valeur in formulaire.items()}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corps de requête illisible ({type_contenu or 'type inconnu'}).",
        ) from exc
    if not isinstance(donnees, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corps de requête attendu : objet JSON ou formulaire.",
        )
    return {
        str(cle): ("" if valeur is None else str(valeur))
        for cle, valeur in donnees.items()
        if valeur is None or isinstance(valeur, (str, int, float, bool))
    }


# --------------------------------------------------------------------------- #
# POST /api/v1/consultations — dépôt d'un DCE
# --------------------------------------------------------------------------- #
@router.post("/consultations", status_code=status.HTTP_201_CREATED)
async def deposer_consultation(
    request: Request,
    libelle: str = Form(..., min_length=1, max_length=255),
    entreprise_id: str = Form(...),
    fichier: UploadFile = File(...),
    reference_consultation: Optional[str] = Form(None),
    maitre_ouvrage_declare: Optional[str] = Form(None),
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
    stockage: StockageFichiers = Depends(obtenir_stockage),
    fournisseur: FournisseurModele = Depends(obtenir_fournisseur),
) -> dict[str, Any]:
    """Dépose un DCE, l'analyse et restitue les éléments **avec leur source**.

    Le dépôt est refusé explicitement si le format n'est pas accepté (PDF ou texte).

    Une analyse **refusée** par le garde-fou anti-invention (proposition non adossée
    au document) n'est pas une panne : le document a bien été reçu, l'analyse n'a pas
    pu être validée. La réponse est alors un `422` explicite (catégorie et extrait mis
    en cause), et le dépôt est annulé — jamais un `500`, jamais un succès partiel.
    """
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_DEPOT:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dépôt refusé : fichier supérieur à {TAILLE_MAX_DEPOT // (1024 * 1024)} Mo.",
        )
    try:
        resultat = analyse_dce.deposer_et_analyser(
            connexion,
            contexte,
            stockage,
            entreprise_id=entreprise_id,
            libelle=libelle,
            nom_fichier=fichier.filename or "depot.pdf",
            contenu=contenu,
            type_mime=fichier.content_type,
            reference_consultation=reference_consultation,
            maitre_ouvrage_declare=maitre_ouvrage_declare,
            fournisseur=fournisseur,
        )
    except AnalyseNonValidable as exc:
        # Refus attendu du garde-fou, pas un incident : 422 explicite, dépôt annulé.
        # (À déclarer **avant** `ErreurAnalyseDce`, dont cette erreur hérite.)
        connexion.annuler()
        raise _erreur(exc, status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    except ErreurAnalyseDce as exc:
        connexion.annuler()
        raise _erreur(exc, status.HTTP_400_BAD_REQUEST) from exc

    reponse = resultat.en_dictionnaire()
    reponse["elements"] = [_serialiser_element(e) for e in reponse["elements"]]
    reponse["document"] = _serialiser(reponse["document"])
    reponse["consultation"] = _serialiser(reponse["consultation"])
    reponse["brouillon"] = MENTION_BROUILLON
    return reponse


# --------------------------------------------------------------------------- #
# GET /api/v1/consultations/{id}
# --------------------------------------------------------------------------- #
@router.get("/consultations/{consultation_id}")
def lire_consultation(
    consultation_id: str,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Consultation, éléments extraits **avec leur source**, et absences déclarées."""
    try:
        lecture = analyse_dce.lire_consultation(connexion, contexte, consultation_id)
    except ConsultationIntrouvable as exc:
        raise _erreur(exc, status.HTTP_404_NOT_FOUND) from exc
    return {
        "consultation": _serialiser(lecture["consultation"]),
        "document": _serialiser(lecture["document"]),
        "elements": [_serialiser_element(e) for e in lecture["elements"]],
        "elements_non_trouves": _serialiser(lecture["elements_non_trouves"]),
        "brouillon": MENTION_BROUILLON,
    }


# --------------------------------------------------------------------------- #
# POST /api/v1/consultations/{id}/elements/{element_id}
# --------------------------------------------------------------------------- #
@router.post("/consultations/{consultation_id}/elements/{element_id}")
async def verifier_element(
    consultation_id: str,
    element_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Valide, corrige ou supprime un élément — action humaine nommée et horodatée.

    `verificateur_nom` est obligatoire pour `valider` et `corriger` : aucune
    validation sans action humaine nommée (ligne rouge, SPEC-MVP-V2 § 2).

    Le corps est accepté en **formulaire** (`application/x-www-form-urlencoded` ou
    `multipart/form-data`) comme en **JSON** : l'interface web rendue côté serveur de
    L5 n'utilise aucun JavaScript, un client d'API envoie du JSON.
    """
    corps = await _lire_corps(request)
    try:
        ligne = analyse_dce.verifier_element(
            connexion,
            contexte,
            consultation_id=consultation_id,
            element_id=element_id,
            action=corps.get("action", ""),
            verificateur_nom=corps.get("verificateur_nom"),
            libelle=corps.get("libelle"),
            valeur=corps.get("valeur"),
        )
    except ConsultationIntrouvable as exc:
        raise _erreur(exc, status.HTTP_404_NOT_FOUND) from exc
    except ErreurAnalyseDce as exc:
        connexion.annuler()
        raise _erreur(exc, status.HTTP_400_BAD_REQUEST) from exc
    return {"element": _serialiser_element(ligne), "brouillon": MENTION_BROUILLON}
