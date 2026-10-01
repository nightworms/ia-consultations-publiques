"""Routes JSON du mémoire technique — `/api/v1/.../memoire` (lot L2, phase 4).

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/consultations/{id}/memoire` | générer un mémoire structuré (critères + bibliothèque) |
| `GET`  | `/api/v1/consultations/{id}/memoire` | lire le dernier mémoire : sections, sources, manques |
| `POST` | `/api/v1/memoire/sections/{id}` | relire / valider **une section** (humain nommé) |
| `POST` | `/api/v1/memoire/{id}/validation` | valider le mémoire **entier** (nom, fonction, empreinte) |

Règles tenues ici :

* le `client_id` vient **exclusivement de la session** (`exiger_contexte_client`) ;
* une source non vérifiable donne un **422 explicite** (jamais un succès partiel, jamais
  un 500) ; les manques, eux, sont un **résultat** normal (200) ;
* aucun statut validé n'est posé sans un humain nommé dans le corps de la requête ;
* aucune route `/api/v1` existante n'est renommée ni modifiée : ce module n'ajoute que la
  surface du mémoire.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.cloisonnement import exiger_contexte_client, obtenir_config, obtenir_connexion
from app.services import memoire_technique
from app.services.memoire_technique import (
    ErreurMemoire,
    MemoireIntrouvable,
    SourceMemoireInvalide,
)
from app.storage.connexion import Connexion, ContexteClient

router = APIRouter(prefix="/api/v1", tags=["mémoire technique"])

MENTION_BROUILLON = "brouillon — à relire et à valider par un humain nommé"


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #
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


async def _lire_corps(request: Request) -> dict[str, Any]:
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
    return donnees


def _erreur(exc: Exception) -> HTTPException:
    if isinstance(exc, MemoireIntrouvable):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SourceMemoireInvalide):
        # Refus attendu du garde-fou de source : un résultat explicite, pas un incident.
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _reponse_memoire(resultat: dict[str, Any]) -> dict[str, Any]:
    return {
        "consultation": _serialiser(resultat["consultation"]),
        "dossier": _serialiser(resultat["dossier"]),
        "sections": _serialiser(resultat["sections"]),
        "manques": _serialiser(resultat["manques"]),
        "validations": _serialiser(resultat.get("validations") or []),
        "resume": _serialiser(resultat["resume"]),
        "avertissement": resultat.get("avertissement"),
        "mention": resultat.get("mention", MENTION_BROUILLON),
    }


# --------------------------------------------------------------------------- #
# POST /api/v1/consultations/{id}/memoire — générer
# --------------------------------------------------------------------------- #
@router.post("/consultations/{consultation_id}/memoire", status_code=status.HTTP_201_CREATED)
async def generer(
    consultation_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Génère un mémoire : plan = critères du DCE, sections adossées à la bibliothèque.

    Tout sort en `brouillon`. Les manques sont renvoyés **normalement** (200/201) : ce ne
    sont pas des erreurs. Seul un critère sans critère validé est un refus explicite.
    """
    config = obtenir_config(request)
    corps = await _lire_corps(request)
    try:
        resultat = memoire_technique.generer_memoire(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte,
            consultation_id=consultation_id,
            fiche_version_id=(str(corps["fiche_version_id"]) if corps.get("fiche_version_id") else None),
            titre=(str(corps["titre"]) if corps.get("titre") else None),
        )
    except MemoireIntrouvable as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    except ErreurMemoire as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return _reponse_memoire(resultat)


# --------------------------------------------------------------------------- #
# GET /api/v1/consultations/{id}/memoire — lire
# --------------------------------------------------------------------------- #
@router.get("/consultations/{consultation_id}/memoire")
def lire(
    consultation_id: str,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Le dernier mémoire de la consultation, avec ses sources et ses manques."""
    try:
        resultat = memoire_technique.lire_memoire(connexion, contexte, consultation_id)
    except MemoireIntrouvable as exc:
        raise _erreur(exc) from exc
    return _reponse_memoire(resultat)


# --------------------------------------------------------------------------- #
# POST /api/v1/memoire/sections/{id} — relire / valider une section
# --------------------------------------------------------------------------- #
@router.post("/memoire/sections/{section_id}")
async def changer_statut(
    section_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Passe une section à `relue` ou `validee` — action humaine nommée et horodatée."""
    corps = await _lire_corps(request)
    try:
        resultat = memoire_technique.changer_statut_section(
            connexion,
            contexte,
            section_id=section_id,
            statut=str(corps.get("statut") or corps.get("action") or ""),
            par=str(corps.get("par") or corps.get("relu_par") or ""),
        )
    except MemoireIntrouvable as exc:
        raise _erreur(exc) from exc
    except ErreurMemoire as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "section": _serialiser(resultat["section"]),
        "dossier": _serialiser(resultat["dossier"]),
        "brouillon": MENTION_BROUILLON,
    }


# --------------------------------------------------------------------------- #
# POST /api/v1/memoire/{id}/validation — valider le mémoire entier
# --------------------------------------------------------------------------- #
@router.post("/memoire/{dossier_id}/validation")
async def valider(
    dossier_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Valide le mémoire : nom + fonction obligatoires ; empreinte SHA-256 enregistrée."""
    corps = await _lire_corps(request)
    try:
        resultat = memoire_technique.valider_dossier(
            connexion,
            contexte,
            dossier_id=dossier_id,
            nom_validateur=str(corps.get("nom_validateur") or corps.get("nom") or ""),
            fonction_validateur=str(
                corps.get("fonction_validateur") or corps.get("fonction") or ""
            ),
            format_export=(str(corps["format_export"]) if corps.get("format_export") else None),
            nom_fichier=(str(corps["nom_fichier"]) if corps.get("nom_fichier") else None),
        )
    except MemoireIntrouvable as exc:
        raise _erreur(exc) from exc
    except ErreurMemoire as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "validation": _serialiser(resultat["validation"]),
        "dossier": _serialiser(resultat["dossier"]),
        "empreinte_contenu": resultat["empreinte_contenu"],
        "mention": resultat["mention"],
    }
