"""Routes de provisionnement — `entreprise` et `fiche_version` (annexe C § C2).

Ce module implémente **le volet 1** de la décision d'annexe C § C2, telle quelle :

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/entreprises` | crée l'`entreprise` (`libelle_court`) **et** sa première `fiche_version`, dans **une seule transaction** |
| `GET`  | `/api/v1/entreprises` | les `entreprise` du client de la session, avec leur dernière `fiche_version` |
| `POST` | `/api/v1/entreprises/{entreprise_id}/fiches` | ouvre une **nouvelle** version (`ouvrir_fiche`) ; numéro croissant par entreprise |

**Le volet 2 de § C2 (création d'un `client` et de son compte d'accès) n'est pas ici, et
c'est voulu** : un utilisateur appartient à un seul client (annexe A § A5), donc aucune
session ne peut exister avant que le `client` existe. Ce provisionnement est un geste
d'exploitant, hors API (`scripts/provisionnement.py`). Aucune route de création de
`client` n'est ajoutée ici — ce n'est pas un oubli.

Règles opposables tenues par ce module
--------------------------------------

* `client_id` provient **exclusivement de la session** (`exiger_contexte_client`) ; il n'est
  jamais lu dans le corps de la requête ni dans le chemin. Un `client_id` envoyé dans le
  corps de la requête est **ignoré** (Pydantic `extra="ignore"`).
* **Contrôle d'appartenance avant toute écriture** dans
  `POST /api/v1/entreprises/{entreprise_id}/fiches` : l'`entreprise` est relue via
  `DepotEntreprise.obtenir` dans le contexte de la session **avant** d'appeler
  `ouvrir_fiche`. Sinon `404`, **jamais `403`** — ne pas révéler qu'une cible existe.
  Nécessaire parce que `fiche_version` ne porte **aucune** contrainte croisée
  `(client_id, entreprise_id)` en base (risque R14 du plan) : sans ce contrôle,
  `ServiceVersionnement.creer_version(entreprise_id)` écrirait un `client_id` de session
  avec un `entreprise_id` étranger qui passerait la clé étrangère.
* **Aucun SQL nouveau**, aucune migration : les routes appellent les fonctions existantes
  `ServiceBibliotheque.creer_entreprise()`, `ouvrir_fiche()`, `dernieres_fiches()` et
  `DepotEntreprise.lister/obtenir`. Aucun SQL hors de `storage/`.
* **Aucune** des quatre routes gelées de la bibliothèque n'est renommée ni modifiée : le
  `404` « Provisionnez une entreprise et une version de fiche » de
  `GET /api/v1/bibliotheque` reste inchangé, mais cesse d'être un cul-de-sac.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.cloisonnement import obtenir_connexion, exiger_contexte_client
from app.api.routes_bibliotheque import obtenir_service_bibliotheque
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.versionnement import ErreurVersionnement
from app.storage.connexion import Connexion, ContexteClient
from app.storage.repositories import ErreurDepot

router = APIRouter(prefix="/api/v1", tags=["provisionnement"])


# --------------------------------------------------------------------------- #
# Corps de requête
# --------------------------------------------------------------------------- #


class DemandeCreationEntreprise(BaseModel):
    """Création d'une `entreprise` et de sa première version de fiche.

    `extra="ignore"` est **délibéré** : un `client_id` (ou tout autre champ) envoyé dans
    le corps ne change rien à la ligne créée — le `client_id` vient de la session.
    """

    model_config = ConfigDict(extra="ignore")

    libelle_court: str = Field(
        min_length=1,
        max_length=255,
        description="Libellé court de l'entreprise (ancre stable `entreprise`).",
    )


class DemandeOuvertureFiche(BaseModel):
    """Ouverture d'une nouvelle version de fiche sur une entreprise existante."""

    model_config = ConfigDict(extra="ignore")

    commentaire: Optional[str] = Field(
        default=None, max_length=2000, description="Commentaire libre sur la version."
    )


# --------------------------------------------------------------------------- #
# Internes
# --------------------------------------------------------------------------- #


def _erreur(exc: Exception) -> HTTPException:
    """Traduit une erreur de service en réponse HTTP — `404` si la cible est hors client."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _exiger_entreprise_du_client(
    service: ServiceBibliotheque,
    contexte: ContexteClient,
    entreprise_id: str,
) -> dict[str, Any]:
    """Contrôle d'appartenance **avant écriture** (§ C2, risque R14).

    Relit l'`entreprise` dans le contexte de la session. Absente (ou appartenant à un
    autre client) → `404`, jamais `403` : la réponse ne révèle pas qu'une cible existe.
    """
    entreprise = service.entreprises.obtenir(contexte, entreprise_id)
    if entreprise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Entreprise inconnue pour ce client. Aucune écriture n'a été effectuée."
            ),
        )
    return entreprise


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post(
    "/entreprises",
    status_code=status.HTTP_201_CREATED,
    summary="Créer une entreprise et sa première fiche",
)
def creer_entreprise(
    demande: DemandeCreationEntreprise,
    connexion: Connexion = Depends(obtenir_connexion),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Crée l'`entreprise` **et** sa première `fiche_version` dans une seule transaction.

    Les deux écritures partagent la transaction de la requête : si l'ouverture de la
    fiche échoue, l'`entreprise` n'est **pas** laissée derrière (`annuler`).
    """
    try:
        entreprise_id = service.creer_entreprise(demande.libelle_court)
        fiche = service.ouvrir_fiche(
            entreprise_id, commentaire="Première version — création de l'entreprise"
        )
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement, ErreurDepot) as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "entreprise_id": str(entreprise_id),
        "fiche_version_id": str(fiche["id"]),
        "numero_version": int(fiche["numero_version"]),
        "statut": str(fiche["statut"]),
    }


@router.get("/entreprises", summary="Entreprises du client de la session")
def lister_entreprises(
    contexte: ContexteClient = Depends(exiger_contexte_client),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Les `entreprise` du client de la session, avec leur dernière `fiche_version`.

    Aucune entreprise d'un autre client n'est visible : le filtre vient du contexte de
    session, côté `storage`.
    """
    entreprises = service.entreprises.lister(contexte)
    resultat: list[dict[str, Any]] = []
    for entreprise in entreprises:
        entreprise_id = str(entreprise["id"])
        versions = service.dernieres_fiches(entreprise_id)
        derniere = versions[0] if versions else None
        resultat.append(
            {
                "entreprise_id": entreprise_id,
                "libelle_court": entreprise["libelle_court"],
                "statut": entreprise["statut"],
                "derniere_fiche": (
                    {
                        "fiche_version_id": str(derniere["id"]),
                        "numero_version": int(derniere["numero_version"]),
                        "statut": str(derniere["statut"]),
                    }
                    if derniere is not None
                    else None
                ),
            }
        )
    return {"entreprises": resultat}


@router.post(
    "/entreprises/{entreprise_id}/fiches",
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir une nouvelle version de fiche",
)
def ouvrir_fiche(
    entreprise_id: str,
    demande: DemandeOuvertureFiche,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
    service: ServiceBibliotheque = Depends(obtenir_service_bibliotheque),
) -> dict[str, Any]:
    """Ouvre une nouvelle `fiche_version` (numéro croissant par entreprise).

    Le contrôle d'appartenance (`_exiger_entreprise_du_client`) est fait **avant** toute
    écriture : une entreprise d'un autre client répond `404` et **aucune** ligne n'est
    écrite dans `fiche_version`.
    """
    _exiger_entreprise_du_client(service, contexte, entreprise_id)
    try:
        fiche = service.ouvrir_fiche(entreprise_id, commentaire=demande.commentaire)
        connexion.valider()
    except (ErreurBibliotheque, ErreurVersionnement, ErreurDepot) as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "fiche_version_id": str(fiche["id"]),
        "numero_version": int(fiche["numero_version"]),
        "statut": str(fiche["statut"]),
    }
