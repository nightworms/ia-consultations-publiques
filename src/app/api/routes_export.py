"""Routes de l'export téléchargeable du mémoire — lot L6, phase 4.

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/consultations/{id}/memoire/export?format=md\\|docx` | télécharger le mémoire validé |

Fichier **dédié** : `routes_web.py` n'est pas modifié pour l'export (règle § 2.C/§ 2.E du
plan de phase 4). Le routeur est monté par l'agrégateur `app.api.routes` (une ligne).

Règles tenues ici :

* le `client_id` vient **exclusivement de la session** : le mémoire d'un autre client
  est **introuvable** (`404`), jamais `403`, jamais servi ;
* le fichier porte le contenu **validé** ; sans validation humaine nommée et horodatée,
  ou si le contenu a changé depuis, l'export est **refusé** avec un message qui dit quoi
  faire — pas une erreur technique ;
* le format **Markdown** est canonique ; le **DOCX** est un confort, dégradé proprement
  s'il n'est pas installé ;
* aucun prix, aucun chiffre inventé, aucune conformité garantie ; **aucun bouton** de
  dépôt, d'envoi ou de signature — l'export ne transmet rien à personne.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from app.api.cloisonnement import NOM_COOKIE_SESSION, obtenir_config, obtenir_connexion
from app.services import export_memoire
from app.services.authentification import ErreurAuthentification, ServiceAuthentification
from app.services.memoire_technique import MemoireIntrouvable
from app.storage.connexion import Connexion, ContexteClient

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["export du mémoire"])


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #
def _contexte_session(
    request: Request, connexion: Connexion
) -> Optional[ContexteClient]:
    """Contexte client de la session, ou `None`. Le client ne vient **jamais** de l'URL."""
    config = obtenir_config(request)
    service = ServiceAuthentification(
        connexion=connexion,
        cle_session=config.cle_session,
        duree_session_secondes=config.duree_session_secondes,
    )
    try:
        identite = service.lire_session(request.cookies.get(NOM_COOKIE_SESSION))
    except ErreurAuthentification:
        return None
    return ContexteClient(identite.client_id)


def _redirection_connexion(request: Request) -> RedirectResponse:
    """Sans session : on renvoie vers la connexion (jamais de données, jamais un 403)."""
    cible = str(request.url.path)
    if request.url.query:
        cible = f"{cible}?{request.url.query}"
    return RedirectResponse(
        f"/connexion?suivant={quote(cible)}", status_code=303
    )


# --------------------------------------------------------------------------- #
# Réponse lisible (refus) — un message qui dit quoi faire
# --------------------------------------------------------------------------- #
def _message_refus(code: int, titre: str, message: str) -> PlainTextResponse:
    """Message humain, en français, en **texte brut** — jamais une trace technique.

    Choix assumé : le corps des refus est du texte lisible, pas du HTML. Un endpoint de
    téléchargement ne rend pas d'écran ; le message doit rester compréhensible tel quel
    (il peut être lu par un outil comme par un humain) et ne comporte donc **aucun bouton**
    de dépôt, d'envoi ou de signature.
    """
    corps = (
        f"{titre}\n"
        f"{'=' * len(titre)}\n\n"
        f"{message}\n\n"
        "Revenir à la liste de vos consultations : /consultations\n"
    )
    return PlainTextResponse(content=corps, status_code=code)


def _entete_telechargement(nom_fichier: str) -> str:
    """`Content-Disposition` d'un téléchargement, compatible nom accentué."""
    repli = nom_fichier.encode("ascii", "ignore").decode("ascii") or "memoire-technique"
    return f"attachment; filename=\"{repli}\"; filename*=UTF-8''{quote(nom_fichier)}"


# --------------------------------------------------------------------------- #
# GET /consultations/{id}/memoire/export?format=md|docx
# --------------------------------------------------------------------------- #
@router.get("/consultations/{consultation_id}/memoire/export")
def exporter(
    consultation_id: str,
    request: Request,
    format: str = Query(export_memoire.FORMAT_CANONIQUE),
    connexion: Connexion = Depends(obtenir_connexion),
) -> Response:
    """Télécharge le mémoire **du client de la session**, dans le format demandé.

    Codes : `200` fichier (`Content-Disposition: attachment`) ; `303` vers la connexion
    sans session ; `404` mémoire introuvable pour ce client (jamais `403`) ; `400` format
    inconnu ; `409` refus métier lisible (validation manquante, contenu modifié depuis la
    validation, format DOCX non disponible).
    """
    contexte = _contexte_session(request, connexion)
    if contexte is None:
        return _redirection_connexion(request)

    try:
        resultat = export_memoire.preparer_export(
            connexion,
            contexte,
            consultation_id=consultation_id,
            format=format,
        )
    except MemoireIntrouvable as exc:
        # Aucun indice sur l'existence du mémoire d'un autre client : 404 net.
        return _message_refus(404, "Mémoire introuvable", str(exc))
    except export_memoire.FormatInconnu as exc:
        return _message_refus(400, "Format d'export inconnu", str(exc))
    except export_memoire.ValidationManquante as exc:
        return _message_refus(409, "Le mémoire doit d'abord être validé", str(exc))
    except export_memoire.ContenuDivergent as exc:
        return _message_refus(409, "Le mémoire a changé depuis sa validation", str(exc))
    except export_memoire.FormatNonDisponible as exc:
        return _message_refus(409, "Format indisponible", str(exc))

    return Response(
        content=resultat["contenu"],
        media_type=resultat["type_mime"],
        headers={
            "Content-Disposition": _entete_telechargement(resultat["nom_fichier"]),
            # L'empreinte du contenu servi est exposée à titre de contrôle, jamais un secret.
            "X-Empreinte-Contenu": resultat["empreinte_contenu"],
        },
    )


__all__ = ["router"]
