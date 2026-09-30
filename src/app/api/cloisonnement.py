"""Cloisonnement par client — dépendance obligatoire (annexe A § A1).

`exiger_contexte_client` est la dépendance que **toute** route lisant ou écrivant
des données doit déclarer. Elle :

1. lit le cookie de session signé ;
2. en extrait l'identité (et donc le `client_id` de l'utilisateur) ;
3. pose ce `client_id` dans l'état de la requête (`request.state`), d'où `storage`
   le lit pour filtrer chaque requête.

Sans session valide, la dépendance lève 401 : aucune lecture par défaut, aucune
route « publique » sur les données. Le client n'est jamais choisi par le client
HTTP : il vient de la session.
"""

from __future__ import annotations

from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Request, status

from app.config import Config
from app.services.authentification import (
    ErreurAuthentification,
    IdentiteSession,
    ServiceAuthentification,
)
from app.storage.connexion import Connexion, ContexteClient

NOM_COOKIE_SESSION = "session"


def obtenir_config(request: Request) -> Config:
    config = getattr(request.app.state, "config", None)
    if config is None:  # pragma: no cover — configuration incomplète
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration non initialisée.",
        )
    return config


def obtenir_connexion(request: Request) -> Iterator[Connexion]:
    """Ouvre une connexion à la base pour la durée de la requête, puis la ferme."""
    config = obtenir_config(request)
    connexion = Connexion(config.database_url).ouvrir()
    try:
        yield connexion
    finally:
        connexion.fermer()


def obtenir_service_authentification(
    request: Request,
    connexion: Connexion = Depends(obtenir_connexion),
) -> ServiceAuthentification:
    """Service d'authentification lié à la connexion de la requête (sans état global)."""
    config = obtenir_config(request)
    return ServiceAuthentification(
        connexion=connexion,
        cle_session=config.cle_session,
        duree_session_secondes=config.duree_session_secondes,
    )


def exiger_identite(
    request: Request,
    service: ServiceAuthentification = Depends(obtenir_service_authentification),
) -> IdentiteSession:
    """Extrait l'identité de la session. 401 si absente ou invalide."""
    jeton: Optional[str] = request.cookies.get(NOM_COOKIE_SESSION)
    try:
        identite = service.lire_session(jeton)
    except ErreurAuthentification as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session requise.",
            headers={"WWW-Authenticate": "Cookie"},
        ) from exc
    request.state.identite = identite
    return identite


def exiger_contexte_client(
    request: Request,
    identite: IdentiteSession = Depends(exiger_identite),
) -> ContexteClient:
    """Contexte client obligatoire : c'est lui que `storage` exige pour tout SQL."""
    contexte = ContexteClient(identite.client_id)
    request.state.contexte_client = contexte
    return contexte
