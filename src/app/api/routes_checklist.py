"""Routes JSON de la brique C — contrat **gelé** en annexe C du plan de phase 3.

Deux routes, pas une de plus :

==================================================================  =========================
`POST /api/v1/consultations/{id}/checklist`                         exécuter la checklist
`GET  /api/v1/consultations/{id}/checklist`                         lignes et résumé des manques
==================================================================  =========================

Règles de réponse (annexe C) : chaque ligne porte `origine`, `confiance` et, pour
l'exigence comparée, `source_document_id` et `source_emplacement`. Aucune sortie ne
dit « conforme » : la réponse rappelle que la checklist est un **outil d'aide à la
relecture**, pas un certificat.

Aucune donnée n'est lisible sans session : `exiger_contexte_client` refuse en 401, et
le `client_id` vient de la session, jamais de l'appelant (annexe A § A1).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.cloisonnement import exiger_contexte_client, obtenir_connexion
from app.services import checklist
from app.services.analyse_dce import ConsultationIntrouvable
from app.services.checklist import ChecklistIntrouvable, ErreurChecklist
from app.storage.connexion import Connexion, ContexteClient

router = APIRouter(prefix="/api/v1", tags=["checklist"])

MENTION_BROUILLON = "brouillon — à relire et à vérifier par un humain"


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


async def _lire_corps(request: Request) -> dict[str, str]:
    """Lit le corps d'une requête, en formulaire ou en JSON. Refus explicite sinon.

    L'interface web rendue côté serveur de L5 n'utilise aucun JavaScript (annexe A
    § A8) : un formulaire doit donc être accepté, comme un client d'API qui envoie
    du JSON.
    """
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


def _erreur(exc: Exception, code: int) -> HTTPException:
    return HTTPException(status_code=code, detail=str(exc))


# --------------------------------------------------------------------------- #
# POST /api/v1/consultations/{id}/checklist — exécuter
# --------------------------------------------------------------------------- #
@router.post("/consultations/{consultation_id}/checklist")
async def executer_checklist(
    consultation_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Exécute la checklist et renvoie une ligne par pièce exigée **validée**.

    Le corps porte `execute_par` (nom de l'humain, obligatoire) et, en option,
    `fiche_version_id` (la version de bibliothèque à croiser ; à défaut la plus
    récente du client). Accepté en formulaire ou en JSON.
    """
    corps = await _lire_corps(request)
    try:
        resultat = checklist.executer_checklist(
            connexion,
            contexte,
            consultation_id=consultation_id,
            execute_par=corps.get("execute_par", ""),
            fiche_version_id=corps.get("fiche_version_id") or None,
        )
    except ConsultationIntrouvable as exc:
        raise _erreur(exc, status.HTTP_404_NOT_FOUND) from exc
    except ErreurChecklist as exc:
        connexion.annuler()
        raise _erreur(exc, status.HTTP_400_BAD_REQUEST) from exc

    reponse = _reponse_serialisee(resultat)
    return reponse


# --------------------------------------------------------------------------- #
# GET /api/v1/consultations/{id}/checklist — lire
# --------------------------------------------------------------------------- #
@router.get("/consultations/{consultation_id}/checklist")
def lire_checklist(
    consultation_id: str,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Dernière exécution de checklist : lignes, résumé des manques, avertissements."""
    try:
        resultat = checklist.lire_checklist(connexion, contexte, consultation_id)
    except ConsultationIntrouvable as exc:
        raise _erreur(exc, status.HTTP_404_NOT_FOUND) from exc
    except ChecklistIntrouvable as exc:
        raise _erreur(exc, status.HTTP_404_NOT_FOUND) from exc
    return _reponse_serialisee(resultat)


def _reponse_serialisee(resultat: dict[str, Any]) -> dict[str, Any]:
    return {
        "consultation": _serialiser(resultat["consultation"]),
        "execution": _serialiser(resultat["execution"]),
        "lignes": _serialiser(resultat["lignes"]),
        "contradictions": _serialiser(resultat.get("contradictions") or []),
        "resume": _serialiser(resultat["resume"]),
        "avertissements": list(resultat["avertissements"]),
        "mention": checklist.MENTION_AIDE_RELECTURE,
        "brouillon": MENTION_BROUILLON,
    }
