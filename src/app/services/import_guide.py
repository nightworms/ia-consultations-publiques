"""Service — import guidé de documents existants dans la bibliothèque (lot L3, phase 4).

Objectif (chantier B du plan de phase 4) : **remplir la bibliothèque sans saisie
champ par champ**, à partir des documents que l'entreprise possède déjà (ancien
mémoire technique, plaquette, attestations, CV, attestations d'assurance, fiches
produits).

Parcours, dans cet ordre et jamais autrement :

1. **dépôt** — l'utilisateur dépose un fichier `.pdf` ou `.txt` (formats de la
   phase 3 ; tout autre format est **refusé explicitement**, avec la marche à
   suivre). Le fichier est chiffré hors dépôt, préfixé par le `client_id`.
2. **extraction** — texte page par page (`analyse_dce.extraire_document`), repli OCR
   compris ; une page illisible est signalée, jamais devinée.
3. **appel du fournisseur** — derrière la couche d'abstraction (D8). Le fournisseur
   ne voit **que le texte extrait**, jamais le fichier, et rend des propositions
   **sourcées** (`PropositionImport`).
4. **garde-fou de source** — mécanique de la phase 3 réutilisée : `source_presente`
   est appliqué tel quel, et une proposition sans source vérifiable est refusée
   explicitement (`ImportNonValidable`). Rien n'est enregistré « à vérifier » sans
   source.
5. **propositions en attente** — chaque proposition vit dans `import_proposition`
   jusqu'à une **décision humaine nommée** (`propose` -> `acceptee` / `refusee`).
6. **écriture en bibliothèque** — une proposition acceptée écrit un élément via
   `app.services.bibliotheque` (`origine = document_extrait`,
   `confiance = a_verifier`, `source_document_id` renseigné), **jamais** par un INSERT
   direct qui contournerait ses règles.

Tout le SQL passe par `storage.connexion.Connexion`, donc par le filtre `client_id`
imposé par le contexte de session (annexe A § A1) : aucune proposition d'un client
n'est visible d'un autre.
"""

from __future__ import annotations

import json
import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from psycopg.types.json import Jsonb

from app.domain.familles import (
    FAMILLE_VERS_ENTITES,
    LIBELLES_FAMILLES,
    DefinitionEntite,
    definition_entite,
)
from app.services.analyse_dce import (
    ErreurAnalyseDce,
    controler_fichier,
    extraire_document,
)
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.fournisseur_modele import (
    FournisseurModele,
    ReponseModeleInvalide,
    creer_fournisseur,
)
from app.services.fournisseur_modele.base import (
    PropositionImport,
    verifier_propositions_import,
)
from app.services.versionnement import CibleInconnue
from app.storage.connexion import Connexion, ContexteClient
from app.storage.fichiers import StockageFichiers, empreinte_sha256

#: Journal du module — trace les nettoyages qui échouent, jamais en silence.
LOGGER = logging.getLogger(__name__)

#: Décisions humaines admises sur une proposition.
DECISIONS = ("accepter", "refuser")

#: Statuts de `import_proposition` qu'une décision peut produire.
STATUT_ACCEPTEE = "acceptee"
STATUT_REFUSEE = "refusee"

#: Champs de contenu qui référencent un **document** (`document.id`). Quand une
#: proposition ne les fournit pas, l'élément accepté pointe le **document importé** :
#: c'est lui qui justifie l'élément, et son identifiant est réel (jamais inventé).
CHAMPS_LIEN_DOCUMENT = (
    "piece",
    "piece_rib",
    "cv_piece",
    "fiche_technique",
    "avis_technique",
    "justificatif",
    "attestation_bonne_execution",
)

#: Mention portée par toute proposition non encore décidée.
MENTION_PROPOSE = "proposition de la machine — à valider ou refuser par un humain nommé"


class ErreurImportGuide(RuntimeError):
    """L'import guidé ne peut pas aboutir (format, décision, écriture). Toujours explicite."""


class ImportIntrouvable(ErreurImportGuide):
    """Import, proposition ou fiche inexistant **pour ce client** (jamais d'indice)."""


class ImportNonValidable(ErreurImportGuide):
    """Le document est bien reçu, mais une proposition n'a pas de source vérifiable.

    Ce **n'est pas** un incident technique : c'est le résultat attendu du garde-fou
    anti-invention. `entite` et `extrait_invoque` portent, quand ils sont connus,
    l'élément mis en cause.
    """

    def __init__(
        self,
        message: str,
        *,
        entite: Optional[str] = None,
        extrait_invoque: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.entite = entite
        self.extrait_invoque = extrait_invoque


@dataclass(frozen=True)
class ResultatImport:
    """Ce qui sort d'un dépôt importé : le document, le suivi, les propositions."""

    import_document: dict[str, Any]
    document: dict[str, Any]
    propositions: tuple[dict[str, Any], ...]
    pages: tuple[dict[str, Any], ...]
    fournisseur: str
    modele: Optional[str]
    avertissement_fournisseur: Optional[str]
    fichier_illisible: bool

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "import_document": _serialiser(self.import_document),
            "document": _serialiser(self.document),
            "propositions": [_enrichir_proposition(p) for p in self.propositions],
            "pages": list(self.pages),
            "fournisseur": self.fournisseur,
            "modele": self.modele,
            "avertissement_fournisseur": self.avertissement_fournisseur,
            "fichier_illisible": self.fichier_illisible,
            "mention": MENTION_PROPOSE,
        }


# --------------------------------------------------------------------------- #
# Sérialisation et enrichissement
# --------------------------------------------------------------------------- #
def _serialiser(valeur: Any) -> Any:
    """Rend une ligne SQL sérialisable en JSON, sans rien inventer."""
    if isinstance(valeur, dict):
        return {cle: _serialiser(contenu) for cle, contenu in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [_serialiser(contenu) for contenu in valeur]
    if isinstance(valeur, (uuid.UUID,)):
        return str(valeur)
    if isinstance(valeur, (date,)):
        return valeur.isoformat()
    if hasattr(valeur, "isoformat"):
        return valeur.isoformat()
    return valeur


def _enrichir_proposition(ligne: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Ajoute, à la lecture, ce qui manque à la proposition pour être enregistrable.

    Aucune de ces informations n'est stockée : elles se recalculent depuis le
    registre des familles (`app.domain.familles`), seule source des champs valides.
    """
    if ligne is None:  # pragma: no cover — un appelant ne passe jamais None
        raise ErreurImportGuide("Proposition introuvable pour ce client.")
    proposition = _serialiser(dict(ligne))
    champs = proposition.get("champs_proposes") or {}
    try:
        definition = definition_entite(str(proposition.get("entite_cible")))
    except KeyError:
        proposition["champs_manquants"] = []
        proposition["complet"] = False
        proposition["famille_libelle"] = LIBELLES_FAMILLES.get(str(proposition.get("famille")))
        return proposition
    manquants = [champ for champ in definition.champs_obligatoires if not champs.get(champ)]
    proposition["champs_manquants"] = manquants
    proposition["complet"] = not manquants
    proposition["famille_libelle"] = LIBELLES_FAMILLES.get(definition.famille)
    proposition["entite_libelle"] = definition.libelle
    return proposition


# --------------------------------------------------------------------------- #
# Dépôt d'un document
# --------------------------------------------------------------------------- #
def _exiger_fiche(
    connexion: Connexion, contexte: ContexteClient, fiche_version_id: str
) -> dict[str, Any]:
    """Vérifie que la fiche visée appartient bien au client de la session."""
    ligne = connexion.executer_une(
        contexte,
        "SELECT id, entreprise_id FROM fiche_version "
        "WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": fiche_version_id},
    )
    if ligne is None:
        raise ImportIntrouvable(
            "Fiche de bibliothèque introuvable pour ce client : un client ne peut "
            "importer que dans sa propre bibliothèque."
        )
    return ligne


def _enregistrer_document_import(
    connexion: Connexion,
    contexte: ContexteClient,
    stockage: StockageFichiers,
    *,
    document_id: str,
    entreprise_id: str,
    fiche_version_id: str,
    famille_cible: str,
    nom_fichier: str,
    contenu: bytes,
    type_mime: Optional[str],
    fournisseur: FournisseurModele,
    valider: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Écrit le document (chiffré) et sa ligne de suivi d'import. Aucun nom fourni
    par l'utilisateur n'est utilisé comme nom de fichier (annexe A § A6)."""
    chemin = stockage.ecrire(contexte.client_id, document_id, contenu)
    document = connexion.executer_une(
        contexte,
        "INSERT INTO document (id, client_id, entreprise_id, fiche_version_id, nature, "
        "type_document, libelle, chemin_stockage, deposant, empreinte_sha256, "
        "taille_octets, mime_type, sensibilite) "
        "VALUES (%(id)s, %(client_id)s, %(entreprise_id)s, %(fiche)s, "
        "'piece_bibliotheque', %(type_document)s, %(libelle)s, %(chemin)s, 'entreprise', "
        "%(empreinte)s, %(taille)s, %(mime)s, 'interne') RETURNING *;",
        {
            "id": document_id,
            "entreprise_id": entreprise_id,
            "fiche": fiche_version_id,
            # Jeu `document.type_document` non semé : la famille cible sert de code, à
            # vérifier ; aucune valeur n'est inventée (D2).
            "type_document": famille_cible,
            "libelle": (Path(nom_fichier or "").name or "Document importé")[:255],
            "chemin": chemin,
            "empreinte": empreinte_sha256(contenu),
            "taille": len(contenu),
            "mime": type_mime or "application/octet-stream",
        },
    )
    if document is None:  # pragma: no cover — RETURNING garantit une ligne
        raise ErreurImportGuide("Enregistrement du document impossible.")

    import_document = connexion.executer_une(
        contexte,
        "INSERT INTO import_document (client_id, document_id, famille_cible, statut, "
        "moteur_fournisseur, moteur_modele) "
        "VALUES (%(client_id)s, %(document_id)s, %(famille)s, 'en_attente', "
        "%(moteur)s, %(modele)s) RETURNING *;",
        {
            "document_id": str(document["id"]),
            "famille": famille_cible,
            "moteur": fournisseur.nom,
            "modele": fournisseur.modele,
        },
    )
    if import_document is None:  # pragma: no cover
        raise ErreurImportGuide("Enregistrement du suivi d'import impossible.")
    if valider:
        connexion.valider()
    return document, import_document


def _extraire(contenu: bytes, nom_fichier: str, *, ocr: bool):
    """Écrit le contenu dans un fichier temporaire et l'extrait (page par page)."""
    extension = Path(nom_fichier or "").suffix.casefold() or ".pdf"
    with tempfile.TemporaryDirectory(prefix="import_guide_") as dossier:
        chemin_local = Path(dossier) / f"document{extension}"
        chemin_local.write_bytes(contenu)
        return extraire_document(chemin_local, ocr=ocr)


def importer_document(
    connexion: Connexion,
    contexte: ContexteClient,
    stockage: StockageFichiers,
    *,
    fiche_version_id: str,
    famille_cible: str,
    nom_fichier: str,
    contenu: bytes,
    type_mime: Optional[str] = None,
    fournisseur: Optional[FournisseurModele] = None,
    ocr: bool = True,
) -> ResultatImport:
    """Dépôt → extraction → appel → propositions en attente, en une transaction.

    Les écritures intermédiaires ne sont **pas** validées : le seul point de
    validation est la fin. Si une proposition est refusée par le garde-fou de source,
    tout est annulé (aucun document, aucun suivi, aucune proposition) et le fichier
    chiffré est supprimé.
    """
    if famille_cible not in FAMILLE_VERS_ENTITES:
        raise ErreurImportGuide(
            f"Famille cible inconnue : {famille_cible!r}. Familles connues : "
            f"{sorted(FAMILLE_VERS_ENTITES)}"
        )
    try:
        controler_fichier(nom_fichier, type_mime)
    except ErreurAnalyseDce as exc:
        # Reformatage sans perte : c'est le même refus explicite de format.
        raise ErreurImportGuide(str(exc)) from exc
    if not contenu:
        raise ErreurImportGuide("Fichier vide : rien à lire.")

    fournisseur_effectif = fournisseur or creer_fournisseur()
    fiche = _exiger_fiche(connexion, contexte, fiche_version_id)
    document_id = str(uuid.uuid4())
    document: Optional[dict[str, Any]] = None
    try:
        document, import_document = _enregistrer_document_import(
            connexion,
            contexte,
            stockage,
            document_id=document_id,
            entreprise_id=str(fiche["entreprise_id"]),
            fiche_version_id=fiche_version_id,
            famille_cible=famille_cible,
            nom_fichier=nom_fichier,
            contenu=contenu,
            type_mime=type_mime,
            fournisseur=fournisseur_effectif,
            valider=False,
        )
        extraction = _extraire(contenu, nom_fichier, ocr=ocr)
        try:
            propositions = verifier_propositions_import(
                fournisseur_effectif.proposer_elements(extraction, famille_cible=famille_cible),
                extraction.pages,
                entites_admises=FAMILLE_VERS_ENTITES[famille_cible],
            )
        except ReponseModeleInvalide as exc:
            raise ImportNonValidable(
                "Le document a bien été reçu, mais une proposition n'a pas pu être "
                f"validée. {exc}",
                entite=exc.categorie,
                extrait_invoque=exc.extrait,
            ) from exc

        lignes: list[dict[str, Any]] = []
        for proposition in propositions:
            ligne = _enregistrer_proposition(
                connexion,
                contexte,
                import_document_id=str(import_document["id"]),
                famille=famille_cible,
                proposition=proposition,
            )
            lignes.append(ligne)

        import_document = connexion.executer_une(
            contexte,
            "UPDATE import_document SET statut = 'traite', date_modification = now() "
            "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING *;",
            {"id": str(import_document["id"])},
        )
        connexion.valider()
    except Exception:
        connexion.annuler()
        if document is not None:
            try:
                stockage.supprimer(contexte.client_id, str(document["id"]))
            except Exception:  # noqa: BLE001 — nettoyage au mieux, toujours tracé
                LOGGER.warning(
                    "Import annulé : le fichier du document %s n'a pas pu être supprimé.",
                    document.get("id"),
                    exc_info=True,
                )
        raise

    assert import_document is not None  # garanti par le chemin nominal
    return ResultatImport(
        import_document=import_document,
        document=document,
        propositions=tuple(lignes),
        pages=tuple(extraction.resume()),
        fournisseur=fournisseur_effectif.nom,
        modele=fournisseur_effectif.modele,
        avertissement_fournisseur=fournisseur_effectif.avertissement,
        fichier_illisible=bool(extraction.pages)
        and not any(page.analyseable for page in extraction.pages),
    )


def _enregistrer_proposition(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    import_document_id: str,
    famille: str,
    proposition: PropositionImport,
) -> dict[str, Any]:
    """Enregistre une proposition sourcée. Refuse un champ hors du registre."""
    definition = definition_entite(proposition.entite_cible)
    inconnus = [c for c in proposition.champs_proposes if not definition.champ_autorise(c)]
    if inconnus:
        raise ImportNonValidable(
            f"Champ hors du registre pour l'entité {proposition.entite_cible!r} : "
            f"{sorted(inconnus)}. Champs acceptés : {sorted(definition.champs)}.",
            entite=proposition.entite_cible,
        )
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO import_proposition (client_id, import_document_id, famille, "
        "entite_cible, champs_proposes, source_emplacement, source_extrait, statut) "
        "VALUES (%(client_id)s, %(import_document_id)s, %(famille)s, %(entite)s, "
        "%(champs)s, %(emplacement)s, %(extrait)s, 'propose') RETURNING *;",
        {
            "import_document_id": import_document_id,
            "famille": famille,
            "entite": proposition.entite_cible,
            "champs": Jsonb(dict(proposition.champs_proposes)),
            "emplacement": proposition.source_emplacement[:255],
            "extrait": proposition.source_extrait,
        },
    )
    if ligne is None:  # pragma: no cover
        raise ErreurImportGuide("Enregistrement de la proposition impossible.")
    return ligne


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def lire_import_document(
    connexion: Connexion, contexte: ContexteClient, import_document_id: str
) -> dict[str, Any]:
    """Import + document + propositions, filtrés par le client de la session."""
    entree = connexion.executer_une(
        contexte,
        "SELECT * FROM import_document WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": import_document_id},
    )
    if entree is None:
        raise ImportIntrouvable("Import introuvable pour ce client.")
    document = connexion.executer_une(
        contexte,
        "SELECT * FROM document WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": str(entree["document_id"])},
    )
    propositions = connexion.executer(
        contexte,
        "SELECT * FROM import_proposition WHERE client_id = %(client_id)s "
        "AND import_document_id = %(id)s ORDER BY date_creation, id;",
        {"id": import_document_id},
    )
    return {
        "import_document": entree,
        "document": document,
        "propositions": propositions,
    }


def lister_imports(connexion: Connexion, contexte: ContexteClient) -> list[dict[str, Any]]:
    """Les imports du client, du plus récent au plus ancien, avec leur compte de
    propositions ; jamais ceux d'un autre client."""
    lignes = connexion.executer(
        contexte,
        "SELECT i.*, d.libelle AS document_libelle, d.empreinte_sha256, d.taille_octets, "
        "(SELECT count(*) FROM import_proposition p "
        " WHERE p.client_id = %(client_id)s AND p.import_document_id = i.id) "
        " AS nb_propositions "
        "FROM import_document i "
        "JOIN document d ON d.id = i.document_id AND d.client_id = %(client_id)s "
        "WHERE i.client_id = %(client_id)s ORDER BY i.date_creation DESC, i.id;",
    )
    return [_serialiser(ligne) for ligne in lignes]


# --------------------------------------------------------------------------- #
# Décision humaine
# --------------------------------------------------------------------------- #
def decider_proposition(
    connexion: Connexion,
    cle_maitresse: bytes,
    contexte: ContexteClient,
    *,
    proposition_id: str,
    decision: str,
    decide_par: str,
    element_id: Optional[str] = None,
    corrections: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Accepte ou refuse une proposition — décision humaine nommée et horodatée.

    Une proposition acceptée écrit un élément de bibliothèque **via
    `ServiceBibliotheque.saisir`** (`origine = document_extrait`,
    `confiance = a_verifier`, `source_document_id` renseigné). Aucune valeur n'est
    écrite par un INSERT direct.
    """
    action = (decision or "").strip().casefold()
    if action not in DECISIONS:
        raise ErreurImportGuide(
            f"Décision inconnue : {decision!r}. Valeurs admises : {', '.join(DECISIONS)}."
        )
    nom = (decide_par or "").strip()
    if not nom:
        raise ErreurImportGuide(
            "`decide_par` est obligatoire : aucune proposition n'est acceptée ni refusée "
            "sans un humain nommé (ligne rouge)."
        )

    proposition = connexion.executer_une(
        contexte,
        "SELECT * FROM import_proposition WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": proposition_id},
    )
    if proposition is None:
        raise ImportIntrouvable("Proposition introuvable pour ce client.")
    if proposition["statut"] != "propose":
        raise ErreurImportGuide(
            f"Proposition déjà décidée (statut {proposition['statut']!r}) : "
            "une décision ne se rejoue pas."
        )

    if action == "refuser":
        ligne = connexion.executer_une(
            contexte,
            "UPDATE import_proposition SET statut = %(statut)s, date_decision = now(), "
            "decide_par = %(nom)s, date_modification = now() "
            "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING *;",
            {"statut": STATUT_REFUSEE, "nom": nom, "id": proposition_id},
        )
        connexion.valider()
        return {"proposition": _enrichir_proposition(ligne), "element_id": None}

    # -- accepter : écriture en bibliothèque, par le service dédié -------------- #
    entree = connexion.executer_une(
        contexte,
        "SELECT * FROM import_document WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": str(proposition["import_document_id"])},
    )
    if entree is None:
        raise ImportIntrouvable("Import de la proposition introuvable pour ce client.")
    document = connexion.executer_une(
        contexte,
        "SELECT * FROM document WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": str(entree["document_id"])},
    )
    if document is None or document["fiche_version_id"] is None:
        raise ErreurImportGuide(
            "Document source introuvable pour ce client : écriture refusée."
        )

    champs = dict(proposition["champs_proposes"] or {})
    if corrections:
        champs.update({str(cle): valeur for cle, valeur in corrections.items()})
    donnees = dict(champs)
    donnees["origine"] = "document_extrait"
    donnees["confiance"] = "a_verifier"
    donnees["source_document_id"] = str(document["id"])
    # Les champs qui référencent un document pointent le document importé : c'est la
    # pièce qui justifie l'élément (identifiant réel, jamais inventé).
    definition = definition_entite(str(proposition["entite_cible"]))
    for champ in CHAMPS_LIEN_DOCUMENT:
        if definition.champ_autorise(champ) and not donnees.get(champ):
            donnees[champ] = str(document["id"])

    service = ServiceBibliotheque(connexion, cle_maitresse, contexte)
    try:
        resultat = service.saisir(
            str(proposition["famille"]),
            str(proposition["entite_cible"]),
            str(document["fiche_version_id"]),
            donnees,
            element_id=element_id,
        )
    except (ErreurBibliotheque, CibleInconnue) as exc:
        connexion.annuler()
        raise ErreurImportGuide(str(exc)) from exc

    ligne = connexion.executer_une(
        contexte,
        "UPDATE import_proposition SET statut = %(statut)s, date_decision = now(), "
        "decide_par = %(nom)s, element_cree_id = %(element)s, date_modification = now() "
        "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING *;",
        {
            "statut": STATUT_ACCEPTEE,
            "nom": nom,
            "element": str(resultat["element_id"]),
            "id": proposition_id,
        },
    )
    connexion.valider()
    return {
        "proposition": _enrichir_proposition(ligne),
        "element_id": str(resultat["element_id"]),
        "validations_revoquees": resultat["validations_revoquees"],
        "statut_fiche": resultat["statut_fiche"],
    }


# --------------------------------------------------------------------------- #
# État d'avancement utile — « ce qui manque pour être prêt à concourir »
# --------------------------------------------------------------------------- #
def _jours_restants(date_fin: date) -> int:
    return (date_fin - date.today()).days


def _libelle_echeance(entite: str, ligne: Mapping[str, Any]) -> str:
    for champ in ("type_assurance", "type_attestation", "intitule", "designation", "raison_sociale"):
        valeur = ligne.get(champ)
        if valeur:
            return f"« {valeur} »"
    return f"élément {entite}"


def _manques_echeances(definition: DefinitionEntite, lignes: Sequence[Mapping[str, Any]]) -> list[str]:
    """Constats d'échéance pour les entités qui en portent une (assurances, etc.)."""
    champ = definition.champ_echeance
    if champ is None:
        return []
    manques: list[str] = []
    for ligne in lignes:
        nom = _libelle_echeance(definition.entite, ligne)
        date_fin = ligne.get(champ)
        if date_fin is None:
            manques.append(
                f"{definition.libelle} {nom} : aucune date d'échéance — le jury ne peut "
                "pas vérifier que la couverture est en cours."
            )
            continue
        statut = ligne.get("statut_validite")
        if statut == "expire":
            manques.append(
                f"{definition.libelle} {nom} : échéance dépassée le "
                f"{date_fin.strftime('%d/%m/%Y')}."
            )
        elif statut == "echeance_proche":
            manques.append(
                f"{definition.libelle} {nom} : expire dans {_jours_restants(date_fin)} "
                f"jour(s), le {date_fin.strftime('%d/%m/%Y')}."
            )
    return manques


def _manques_famille(famille: str, elements: Mapping[str, list[dict[str, Any]]]) -> list[str]:
    """Constats concrets pour une famille — jamais un pourcentage de complétion."""
    def compte(entite: str) -> int:
        return len(elements.get(entite, []))

    if famille == "identite":
        manques: list[str] = []
        if compte("entreprise_version") == 0:
            manques.append(
                "Identité de l'entreprise non renseignée (raison sociale, SIREN, adresse) : "
                "elle est reprise dans chaque dossier."
            )
        if compte("representant_legal") == 0:
            manques.append(
                "Aucun représentant légal identifié : la plupart des dossiers exigent "
                "son nom et sa fonction."
            )
        return manques

    if famille == "capacites_financieres":
        manques = []
        if compte("exercice_comptable") == 0:
            manques.append(
                "Aucun exercice comptable : impossible de démontrer la capacité "
                "financière demandée."
            )
        if compte("attestation") == 0:
            manques.append(
                "Aucune attestation justificative (vigilance sociale, etc.)."
            )
        return manques

    if famille == "assurances":
        manques = []
        if compte("assurance") == 0:
            manques.append(
                "Aucune attestation d'assurance : pièce exigée par tous les acheteurs, "
                "et motif d'élimination si elle manque."
            )
            return manques
        return _manques_echeances(definition_entite("assurance"), elements["assurance"])

    if famille == "certifications":
        manques = []
        if compte("certification") == 0:
            manques.append(
                "Aucune certification ni qualification : un critère de valeur technique "
                "ne peut pas s'appuyer dessus."
            )
            return manques
        return _manques_echeances(definition_entite("certification"), elements["certification"])

    if famille == "references_chantiers":
        manques = []
        references = elements.get("reference_chantier", [])
        if not references:
            manques.append(
                "Aucune référence de chantier comparable : le jury n'a rien à comparer "
                "à l'objet du marché."
            )
            return manques
        if not any(ligne.get("montant_montant") for ligne in references):
            manques.append(
                "Des références existent, mais aucune ne porte de montant : la "
                "comparabilité avec le marché n'est pas démontrable."
            )
        if not any(ligne.get("date_fin") for ligne in references):
            manques.append(
                "Aucune référence ne porte de date de fin : l'ancienneté des travaux "
                "n'est pas vérifiable."
            )
        return manques

    if famille == "moyens_humains":
        if compte("effectif_metier") == 0 and compte("cv") == 0:
            return [
                "Aucun moyen humain décrit (effectif par métier, CV des profils clés) : "
                "le jury ne peut pas évaluer l'équipe affectée."
            ]
        return []

    if famille == "moyens_materiels":
        if compte("moyen_materiel") == 0:
            return [
                "Aucun moyen matériel décrit : le jury ne peut pas vérifier les moyens "
                "réellement affectés."
            ]
        return []

    if famille == "fiches_produits":
        if compte("produit") == 0:
            return [
                "Aucune fiche technique de produit : les solutions proposées ne sont "
                "pas documentées."
            ]
        return []

    if famille == "memoire_technique":
        if compte("chapitre_memoire") == 0:
            return [
                "Aucun chapitre de mémoire technique type : rien à réutiliser comme "
                "source citée (l'import peut en lire depuis un ancien mémoire)."
            ]
        return []

    return []


def etat_avancement_utile(
    connexion: Connexion,
    cle_maitresse: bytes,
    contexte: ContexteClient,
    fiche_version_id: str,
    *,
    fenetre_alerte_jours: Optional[int] = None,
) -> dict[str, Any]:
    """Dit, **famille par famille, ce qui manque pour être prêt à concourir**.

    Ce n'est pas un pourcentage de complétion structurelle : chaque constat nomme un
    manque concret et l'action qu'il appelle (« aucune référence de chantier
    comparable », « assurance qui expire dans 40 jours »). C'est la donnée que l'écran
    L5b affiche.
    """
    service = ServiceBibliotheque(
        connexion, cle_maitresse, contexte, fenetre_alerte_jours=fenetre_alerte_jours
    )
    try:
        service.versionnement.fiche(fiche_version_id)
    except CibleInconnue as exc:
        raise ImportIntrouvable(str(exc)) from exc

    familles: list[dict[str, Any]] = []
    manques_total = 0
    for famille, libelle in LIBELLES_FAMILLES.items():
        contenu = service.consulter_famille(famille, fiche_version_id)
        manques = _manques_famille(famille, contenu["elements"])
        manques_total += len(manques)
        familles.append(
            {
                "famille": famille,
                "libelle": libelle,
                "prete": not manques,
                "manques": manques,
            }
        )
    return {
        "fiche_version_id": fiche_version_id,
        "pret_a_concourir": manques_total == 0,
        "manques_total": manques_total,
        "familles": familles,
        "mention": (
            "Ce qui manque pour concourir, famille par famille. Aucun pourcentage : "
            "chaque ligne est un manque concret et l'action qu'il appelle."
        ),
    }


def _charger_corrections(valeur: Any) -> dict[str, Any]:
    """Normalise l'entrée `corrections` (objet ou chaîne JSON). Refus explicite sinon."""
    if valeur in (None, "", {}):
        return {}
    if isinstance(valeur, Mapping):
        return {str(cle): valeur[cle] for cle in valeur}
    try:
        charge = json.loads(str(valeur))
    except (TypeError, ValueError) as exc:
        raise ErreurImportGuide(
            "`corrections` doit être un objet JSON (ou une chaîne JSON d'objet)."
        ) from exc
    if not isinstance(charge, dict):
        raise ErreurImportGuide("`corrections` doit être un objet JSON.")
    return charge
