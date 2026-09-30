"""Routes JSON de la bibliothèque d'entreprise — contrat gelé (annexe C).

Routes exposées, **telles quelles** (aucune n'est renommée) :

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET`  | `/api/v1/bibliotheque` | état d'avancement, par famille |
| `GET`  | `/api/v1/bibliotheque/{famille}` | contenu d'une famille |
| `POST` | `/api/v1/bibliotheque/{famille}` | création / modification d'un élément |
| `POST` | `/api/v1/bibliotheque/validation` | `validation_relecture` (nom du relecteur + attestation cochée) |

Règles de réponse (annexe C) : toute valeur renvoyée porte `origine`, `confiance` et,
si elle est extraite, `source_document_id`. Une valeur sans source est renvoyée avec
`confiance = a_verifier` — jamais présentée comme vérifiée.

Toutes ces routes passent par `exiger_contexte_client` : sans session valide, 401 ;
le `client_id` vient de la session, jamais de la requête (cloisonnement, annexe A § A1).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.cloisonnement import (
    obtenir_config,
    obtenir_connexion,
    exiger_contexte_client,
)
from app.domain.familles import FAMILLE_VERS_ENTITES
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.versionnement import CibleInconnue, ErreurVersionnement
from app.storage.connexion import Connexion, ContexteClient

router = APIRouter(prefix="/api/v1", tags=["bibliothèque"])


# --------------------------------------------------------------------------- #
# Corps de requête
# --------------------------------------------------------------------------- #


class DemandeSaisie(BaseModel):
    """Saisie (ou modification) d'un élément d'une famille."""

    fiche_version_id: Optional[str] = Field(
        default=None,
        description="Version de fiche visée ; à défaut, la plus récente du client.",
    )
    entite: str = Field(
        min_length=1,
        description="Nom logique de l'entité (ex. `assurance`, `reference_chantier`).",
    )
    donnees: dict[str, Any] = Field(
        description="Champs de l'élément ; `origine` est obligatoire."
    )
    element_id: Optional[str] = Field(
        default=None, description="Renseigné pour modifier un élément existant."
    )
    controle_humain_par: Optional[str] = Field(
        default=None,
        description=(
            "Nom de l'humain ayant contrôlé la valeur. Exigé uniquement pour "
            "`confiance = verifie` : aucun chemin automatique ne pose cette confiance."
        ),
    )


class DemandeValidation(BaseModel):
    """Validation de relecture — le verrou humain (§ 6.4)."""

    fiche_version_id: str
    relecteur_nom: str = Field(min_length=1, description="Saisi par l'humain.")
    attestation_cochee: bool = Field(
        description="« j'ai relu et corrigé les informations ci-dessus »."
    )
    cible_type: Literal["fiche", "famille"] = "fiche"
    famille_code: Optional[str] = Field(
        default=None, description="Obligatoire si `cible_type = famille`."
    )
    commentaire: Optional[str] = None


# --------------------------------------------------------------------------- #
# Dépendances
# --------------------------------------------------------------------------- #


def obtenir_service_bibliotheque(
    request: Request,
    connexion: Connexion = Depends(obtenir_connexion),
    contexte: ContexteClient = Depends(exiger_contexte_client),
) -> ServiceBibliotheque:
    """Service de bibliothèque lié à la session (donc au `client_id` de la session)."""
    config = obtenir_config(request)
    return ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)


def _erreur(exc: Exception) -> HTTPException:
    if isinstance(exc, CibleInconnue):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _resoudre_fiche(service: ServiceBibliotheque, fiche_version_id: Optional[str]) -> str:
    """Fiche demandée, ou la plus récente du client. 404 si aucune."""
    if fiche_version_id:
        return fiche_version_id
    courante = service.fiche_courante()
    if courante is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Aucune fiche de bibliothèque pour ce client. Provisionnez une "
                "entreprise et une version de fiche avant d'appeler ces routes."
            ),
        )
    return str(courante["id"])


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


# Déclarée AVANT `/{famille}` : sinon « validation » serait pris pour une famille.
@router.post("/bibliotheque/validation", summary="Validation de relecture (humaine)")
def valider(
    demande: DemandeValidation,
    connexion: Connexion = Depends(obtenir_connexion),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Enregistre une validation : relecteur nommé + attestation cochée + horodatage.

    Aucun chemin de cette API ne mène à `validee` sans cette action humaine.
    """
    try:
        resultat = service.valider_fiche(
            demande.fiche_version_id,
            relecteur_nom=demande.relecteur_nom,
            attestation_cochee=demande.attestation_cochee,
            cible_type=demande.cible_type,
            famille_code=demande.famille_code,
            commentaire=demande.commentaire,
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "statut": resultat["statut"],
        "validation_id": resultat["validation_id"],
        "cible_type": resultat["cible_type"],
        "famille_code": resultat["famille_code"],
        "empreinte_algorithme": resultat["empreinte_algorithme"],
        "mention": "Relecture humaine enregistrée — le libellé produit reste "
        "« relue et validée par humain », jamais « conforme » ni « certifiée ».",
    }


@router.get("/bibliotheque", summary="État d'avancement de la bibliothèque")
def etat_bibliotheque(
    fiche_version_id: Optional[str] = Query(default=None),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """État par famille, plus les validations et le contrôle d'empreinte (I6)."""
    try:
        fiche = _resoudre_fiche(service, fiche_version_id)
        return service.etat_avancement(fiche)
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        raise _erreur(exc) from exc


@router.get("/bibliotheque/{famille}", summary="Contenu d'une famille")
def lire_famille(
    famille: str,
    fiche_version_id: Optional[str] = Query(default=None),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Éléments d'une famille, chacun portant son `origine` et sa `confiance`."""
    if famille not in FAMILLE_VERS_ENTITES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Famille inconnue : {famille!r}. Connues : {sorted(FAMILLE_VERS_ENTITES)}",
        )
    try:
        fiche = _resoudre_fiche(service, fiche_version_id)
        return service.consulter_famille(famille, fiche)
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        raise _erreur(exc) from exc


@router.post("/bibliotheque/{famille}", summary="Créer ou modifier un élément")
def ecrire_element(
    famille: str,
    demande: DemandeSaisie,
    connexion: Connexion = Depends(obtenir_connexion),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Crée ou modifie un élément. Toute écriture **révoque** la validation (§ 6.5)."""
    if famille not in FAMILLE_VERS_ENTITES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Famille inconnue : {famille!r}. Connues : {sorted(FAMILLE_VERS_ENTITES)}",
        )
    try:
        fiche = _resoudre_fiche(service, demande.fiche_version_id)
        resultat = service.saisir(
            famille,
            demande.entite,
            fiche,
            demande.donnees,
            element_id=demande.element_id,
            controle_humain_par=demande.controle_humain_par,
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement) as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return resultat
