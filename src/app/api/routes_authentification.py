"""Routes d'authentification (`/api/v1/connexion`, `/api/v1/deconnexion`).

Contrat gelé (annexe C) : JSON, préfixe `/api/v1`. La session est un **cookie
signé** posé par le serveur ; aucune donnée de contenu n'est exposée ici.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.api.cloisonnement import (
    NOM_COOKIE_SESSION,
    obtenir_config,
    obtenir_service_authentification,
)
from app.services.authentification import ServiceAuthentification

router = APIRouter(prefix="/api/v1", tags=["authentification"])


class DemandeConnexion(BaseModel):
    """Corps de la requête de connexion."""

    identifiant: str = Field(min_length=1, max_length=255)
    mot_de_passe: str = Field(min_length=1, max_length=1024)


class ReponseConnexion(BaseModel):
    """Réponse minimale : ni mot de passe, ni empreinte."""

    utilisateur_id: str
    client_id: str
    nom_affichage: str


@router.post("/connexion", response_model=ReponseConnexion)
def connexion(
    demande: DemandeConnexion,
    request: Request,
    reponse: Response,
    service: ServiceAuthentification = Depends(obtenir_service_authentification),
) -> ReponseConnexion:
    identite = service.authentifier(demande.identifiant, demande.mot_de_passe)
    if identite is None:
        # Message volontairement générique : ne révèle pas si l'identifiant existe.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
        )
    jeton = service.creer_cookie_session(identite)
    config = obtenir_config(request)
    reponse.set_cookie(
        key=NOM_COOKIE_SESSION,
        value=jeton,
        max_age=config.duree_session_secondes,
        httponly=True,
        samesite="lax",
        secure=False,  # localhost sans TLS : à passer à True derrière HTTPS
        path="/",
    )
    return ReponseConnexion(
        utilisateur_id=identite.utilisateur_id,
        client_id=identite.client_id,
        nom_affichage=identite.nom_affichage,
    )


@router.post("/deconnexion")
def deconnexion(reponse: Response) -> dict[str, str]:
    reponse.delete_cookie(NOM_COOKIE_SESSION, path="/")
    return {"statut": "deconnecte"}
