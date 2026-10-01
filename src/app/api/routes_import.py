"""Routes JSON de l'import guidé — `/api/v1/import/...` (lot L3, phase 4).

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/import/documents` | déposer un document existant et obtenir des propositions sourcées |
| `GET`  | `/api/v1/import/documents` | les imports du client, du plus récent au plus ancien |
| `GET`  | `/api/v1/import/documents/{id}` | un import et ses propositions |
| `POST` | `/api/v1/import/propositions/{id}` | accepter ou refuser une proposition (humain nommé) |
| `GET`  | `/api/v1/import/avancement` | ce qui manque, famille par famille, pour être prêt à concourir |

Règles tenues ici :

* le fournisseur ne voit **que le texte extrait** (dépendance `obtenir_fournisseur`) ;
* une proposition sans source vérifiable est refusée en **422** (jamais un succès
  partiel, jamais un 500) ;
* rien n'entre dans la bibliothèque sans une décision humaine nommée ;
* `client_id` provient **exclusivement de la session** (`exiger_contexte_client`).

Aucune route `/api/v1` existante n'est renommée ni modifiée : ce module n'ajoute que
le préfixe `/import`.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.cloisonnement import (
    exiger_contexte_client,
    obtenir_config,
    obtenir_connexion,
)
from app.api.routes_analyse import TAILLE_MAX_DEPOT, obtenir_fournisseur, obtenir_stockage
from app.services import import_guide
from app.services.import_guide import (
    ErreurImportGuide,
    ImportIntrouvable,
    ImportNonValidable,
)
from app.services.fournisseur_modele import FournisseurModele
from app.storage.connexion import Connexion, ContexteClient
from app.storage.fichiers import StockageFichiers

router = APIRouter(prefix="/api/v1", tags=["import guidé"])

MENTION_BROUILLON = "brouillon — à relire et à vérifier par un humain"


def _erreur(exc: Exception) -> HTTPException:
    if isinstance(exc, ImportIntrouvable):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ImportNonValidable):
        # Refus attendu du garde-fou de source : pas un incident, un résultat explicite.
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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


# --------------------------------------------------------------------------- #
# POST /api/v1/import/documents — déposer un document existant
# --------------------------------------------------------------------------- #
@router.post("/import/documents", status_code=status.HTTP_201_CREATED)
async def deposer_document(
    request: Request,
    famille_cible: str = Form(..., min_length=1, max_length=100),
    fiche_version_id: str = Form(..., min_length=1),
    fichier: UploadFile = File(...),
    libelle: Optional[str] = Form(None),
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
    stockage: StockageFichiers = Depends(obtenir_stockage),
    fournisseur: FournisseurModele = Depends(obtenir_fournisseur),
) -> dict[str, Any]:
    """Dépose un document (`.pdf` / `.txt`) et rend les propositions **sourcées**.

    Le format est refusé explicitement s'il n'est pas accepté. Une proposition non
    adossée au document fait échouer l'import en **422** : le dépôt est annulé, rien
    n'est enregistré — jamais une proposition partielle.
    """
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_DEPOT:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dépôt refusé : fichier supérieur à {TAILLE_MAX_DEPOT // (1024 * 1024)} Mo.",
        )
    try:
        resultat = import_guide.importer_document(
            connexion,
            contexte,
            stockage,
            fiche_version_id=fiche_version_id,
            famille_cible=famille_cible,
            nom_fichier=(fichier.filename or libelle or "document.pdf"),
            contenu=contenu,
            type_mime=fichier.content_type,
            fournisseur=fournisseur,
        )
    except ImportNonValidable as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    except ErreurImportGuide as exc:
        connexion.annuler()
        raise _erreur(exc) from exc

    reponse = resultat.en_dictionnaire()
    reponse["brouillon"] = MENTION_BROUILLON
    return reponse


# --------------------------------------------------------------------------- #
# GET /api/v1/import/documents — les imports du client
# --------------------------------------------------------------------------- #
@router.get("/import/documents")
def lister_documents(
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Les imports du client de la session, du plus récent au plus ancien."""
    try:
        imports = import_guide.lister_imports(connexion, contexte)
    except ErreurImportGuide as exc:
        raise _erreur(exc) from exc
    return {"imports": imports, "mention": MENTION_BROUILLON}


# --------------------------------------------------------------------------- #
# GET /api/v1/import/avancement — ce qui manque pour concourir
# --------------------------------------------------------------------------- #
@router.get("/import/avancement")
def avancement(
    request: Request,
    fiche_version_id: Optional[str] = None,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """État d'avancement **utile** : famille par famille, ce qui manque concrètement."""
    config = obtenir_config(request)
    try:
        cible = fiche_version_id
        if not cible:
            from app.services.bibliotheque import ServiceBibliotheque

            courante = ServiceBibliotheque(
                connexion, config.cle_chiffrement_maitresse, contexte
            ).fiche_courante()
            if courante is None:
                raise ImportIntrouvable(
                    "Aucune fiche de bibliothèque pour ce client : provisionnez une "
                    "entreprise et une version de fiche."
                )
            cible = str(courante["id"])
        return import_guide.etat_avancement_utile(
            connexion, config.cle_chiffrement_maitresse, contexte, cible
        )
    except ErreurImportGuide as exc:
        raise _erreur(exc) from exc


# --------------------------------------------------------------------------- #
# GET /api/v1/import/documents/{id} — un import et ses propositions
# --------------------------------------------------------------------------- #
@router.get("/import/documents/{import_document_id}")
def lire_document(
    import_document_id: str,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Un import du client : le document, ses propositions et leur source."""
    try:
        lecture = import_guide.lire_import_document(connexion, contexte, import_document_id)
    except ImportIntrouvable as exc:
        raise _erreur(exc) from exc
    return {
        "import_document": import_guide._serialiser(lecture["import_document"]),
        "document": import_guide._serialiser(lecture["document"]),
        "propositions": [import_guide._enrichir_proposition(p) for p in lecture["propositions"]],
        "mention": MENTION_BROUILLON,
    }


# --------------------------------------------------------------------------- #
# POST /api/v1/import/propositions/{id} — accepter ou refuser
# --------------------------------------------------------------------------- #
@router.post("/import/propositions/{proposition_id}")
async def decider(
    proposition_id: str,
    request: Request,
    contexte: ContexteClient = Depends(exiger_contexte_client),
    connexion: Connexion = Depends(obtenir_connexion),
) -> dict[str, Any]:
    """Accepte ou refuse une proposition — décision humaine **nommée**.

    Une proposition acceptée écrit un élément de bibliothèque via
    `app.services.bibliotheque` (`origine = document_extrait`, `confiance = a_verifier`,
    `source_document_id`), jamais par un INSERT direct.
    """
    config = obtenir_config(request)
    corps = await _lire_corps(request)
    try:
        corrections = import_guide._charger_corrections(corps.get("corrections"))
        resultat = import_guide.decider_proposition(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte,
            proposition_id=proposition_id,
            decision=str(corps.get("decision") or corps.get("action") or ""),
            decide_par=str(corps.get("decide_par") or ""),
            element_id=(str(corps["element_id"]) if corps.get("element_id") else None),
            corrections=corrections,
        )
    except ImportIntrouvable as exc:
        raise _erreur(exc) from exc
    except ErreurImportGuide as exc:
        connexion.annuler()
        raise _erreur(exc) from exc
    return {
        "proposition": resultat["proposition"],
        "element_id": resultat["element_id"],
        "validations_revoquees": resultat.get("validations_revoquees", []),
        "statut_fiche": resultat.get("statut_fiche"),
        "brouillon": MENTION_BROUILLON,
    }
