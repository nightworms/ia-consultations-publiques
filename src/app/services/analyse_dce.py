"""Orchestration de la brique B — analyse d'un DCE déposé par l'utilisateur.

Parcours, dans cet ordre et jamais autrement :

1. **dépôt** — l'utilisateur dépose son fichier ; l'outil ne va rien chercher
   (SPEC-MVP-V2 § 1.4). Le fichier est stocké hors dépôt, chiffré, préfixé par le
   `client_id` (`storage.fichiers`).
2. **extraction** — texte page par page, repli OCR si la page est scannée ; une page
   illisible est signalée « non analysable », jamais devinée (`extraction_pdf`).
3. **appel du modèle** — derrière la couche d'abstraction (D8, `fournisseur_modele`).
   Le fournisseur ne voit que le texte extrait et rend des propositions **sourcées**.
4. **restitution** — chaque élément est enregistré avec `source_document_id`,
   `source_emplacement`, `source_extrait`, `confiance = a_verifier` et
   `statut_verification = propose`. Rien n'est présenté comme un fait.

Ligne rouge (SPEC-MVP-V2 § 2), appliquée ici par du code :

* aucune valeur n'est écrite sans `source_document_id` **et** `source_emplacement` ;
* une proposition dont l'extrait ne se retrouve pas dans le document est **rejetée**
  (`fournisseur_modele.base.verifier_propositions`) ;
* une catégorie attendue sans résultat est restituée « non trouvé dans le document » :
  le vide n'est pas comblé, et un « non trouvé » n'est **pas** enregistré comme
  élément (il n'aurait pas de source, donc pas le droit d'exister) ;
* seul un élément `statut_verification = valide` est utilisable par la brique C
  (`elements_valides`) : un élément encore `propose` ne l'est pas.

Tout le SQL passe par `storage.connexion.Connexion`, donc par le filtre `client_id`
imposé par le contexte de session (annexe A § A1).
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from app.services import extraction_pdf
from app.services.extraction_pdf import ExtractionPdf
from app.services.fournisseur_modele import (
    MENTION_NON_TROUVE,
    MENTION_NON_VERIFIE,
    FournisseurModele,
    ReponseModeleInvalide,
    creer_fournisseur,
)
from app.services.fournisseur_modele.base import CATEGORIES_ATTENDUES, verifier_propositions
from app.storage.connexion import Connexion, ContexteClient
from app.storage.fichiers import StockageFichiers, empreinte_sha256

#: Actions admises sur un élément extrait (annexe B § B3).
ACTIONS_VERIFICATION = ("valider", "corriger", "supprimer")

#: Journal du module — sert notamment à tracer les nettoyages qui échouent.
LOGGER = logging.getLogger(__name__)

#: Libellés génériques des catégories, pour signaler proprement une absence.
LIBELLES_CATEGORIES = {
    "piece_exigee": "Pièces exigées",
    "critere": "Critères d'attribution",
    "date_limite": "Date limite de remise",
}

#: Extensions et types acceptés. Les formats bureautiques sont refusés explicitement
#: plutôt qu'acceptés sans traitement (question ouverte n° 2 du plan, défaut retenu).
EXTENSIONS_ACCEPTEES = (".pdf", ".txt")
TYPES_ACCEPTES = ("application/pdf", "text/plain")


class ErreurAnalyseDce(RuntimeError):
    """Le dépôt ou l'analyse ne peut pas aboutir. Toujours explicite."""


class ConsultationIntrouvable(ErreurAnalyseDce):
    """Consultation ou élément inexistant **pour ce client** (jamais d'indice)."""


#: Première phrase de tout refus d'analyse : le document est bien arrivé, c'est la
#: validation de l'analyse qui a échoué. Le client doit pouvoir faire la différence
#: avec un format refusé ou un dépôt perdu.
MENTION_DOCUMENT_RECU = "Le document a bien été reçu, mais l'analyse n'a pas pu être validée."


class AnalyseNonValidable(ErreurAnalyseDce):
    """Le document a été reçu, mais l'analyse n'a pas pu être validée (modèle refusé).

    Ce **n'est pas** un incident technique : c'est le résultat attendu du garde-fou
    anti-invention (`fournisseur_modele.base.verifier_propositions`). Le refus est
    explicite et porte la raison exacte ; il n'est **jamais** converti en succès ni en
    proposition partielle, et le dépôt est annulé (`connexion.annuler()`).

    `categorie` et `extrait_invoque` reprennent, quand ils sont connus, l'élément mis
    en cause par le fournisseur.
    """

    def __init__(
        self,
        message: str,
        *,
        categorie: Optional[str] = None,
        extrait_invoque: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.categorie = categorie
        self.extrait_invoque = extrait_invoque


def _refus_modele(exc: ReponseModeleInvalide) -> AnalyseNonValidable:
    """Traduit un refus du garde-fou en erreur applicative lisible par le client.

    Le message d'origine est conservé mot pour mot : on ne rattrape pas le refus, on
    l'explique. La catégorie et l'extrait invoqué sont joints quand le contrôle les a
    transmis, car c'est ce qui permet à l'utilisateur de corriger le document.
    """
    morceaux = [MENTION_DOCUMENT_RECU, str(exc)]
    if exc.categorie:
        morceaux.append(f"Catégorie mise en cause : {exc.categorie}.")
    if exc.extrait:
        morceaux.append(
            f'Extrait invoqué, introuvable dans le document : « {" ".join(exc.extrait.split())} ».'
        )
    morceaux.append("Aucun élément n'a été enregistré : le dépôt a été annulé.")
    return AnalyseNonValidable(
        " ".join(morceaux), categorie=exc.categorie, extrait_invoque=exc.extrait
    )


@dataclass(frozen=True)
class ResultatDepot:
    """Ce qui sort du dépôt : la consultation, son document, l'analyse."""

    consultation: dict[str, Any]
    document: dict[str, Any]
    elements: tuple[dict[str, Any], ...]
    elements_non_trouves: tuple[dict[str, Any], ...]
    pages: tuple[dict[str, Any], ...]
    fournisseur: str
    modele: Optional[str]
    avertissement_fournisseur: Optional[str]
    fichier_illisible: bool

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "consultation": self.consultation,
            "document": self.document,
            "elements": list(self.elements),
            "elements_non_trouves": list(self.elements_non_trouves),
            "pages": list(self.pages),
            "fournisseur": self.fournisseur,
            "modele": self.modele,
            "avertissement_fournisseur": self.avertissement_fournisseur,
            "fichier_illisible": self.fichier_illisible,
            "brouillon": "brouillon — à relire et à vérifier par un humain",
        }


# --------------------------------------------------------------------------- #
# 1. Dépôt
# --------------------------------------------------------------------------- #
def _exiger_entreprise(connexion: Connexion, contexte: ContexteClient, entreprise_id: str) -> str:
    """Vérifie que l'entreprise appartient bien au client de la session."""
    try:
        identifiant = str(uuid.UUID(str(entreprise_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ErreurAnalyseDce(f"entreprise_id invalide (UUID attendu) : {entreprise_id!r}") from exc
    ligne = connexion.executer_une(
        contexte,
        "SELECT id FROM entreprise WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": identifiant},
    )
    if ligne is None:
        raise ErreurAnalyseDce(
            "Entreprise inconnue pour ce client : un client ne peut rattacher une "
            "consultation qu'à sa propre entreprise."
        )
    return identifiant


def creer_consultation(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    entreprise_id: str,
    libelle: str,
    reference_consultation: Optional[str] = None,
    maitre_ouvrage_declare: Optional[str] = None,
    valider: bool = True,
) -> dict[str, Any]:
    """Crée une `consultation` (statut initial `deposee`). Ne devine aucun champ.

    `valider=False` permet à un appelant qui enchaîne plusieurs écritures (le dépôt
    d'un DCE) de n'avoir **qu'un seul point de validation** : sans cela, une
    consultation déjà commitée survivrait à l'échec de l'analyse et resterait
    orpheline en base.
    """
    if not libelle or not libelle.strip():
        raise ErreurAnalyseDce("Le libellé de la consultation est obligatoire.")
    entreprise = _exiger_entreprise(connexion, contexte, entreprise_id)
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO consultation (client_id, entreprise_id, libelle, "
        "reference_consultation, maitre_ouvrage_declare) "
        "VALUES (%(client_id)s, %(entreprise_id)s, %(libelle)s, "
        "%(reference_consultation)s, %(maitre_ouvrage_declare)s) RETURNING *;",
        {
            "entreprise_id": entreprise,
            "libelle": libelle.strip(),
            # Saisis par l'humain, jamais déduits du document (annexe B § B2).
            "reference_consultation": (reference_consultation or "").strip() or None,
            "maitre_ouvrage_declare": (maitre_ouvrage_declare or "").strip() or None,
        },
    )
    if ligne is None:  # pragma: no cover — RETURNING garantit une ligne
        raise ErreurAnalyseDce("Création de la consultation impossible.")
    if valider:
        connexion.valider()
    return ligne


def controler_fichier(nom_fichier: str, type_mime: Optional[str]) -> str:
    """Contrôle d'entrée à la frontière du système : format accepté ou refus explicite."""
    nom = (nom_fichier or "").strip()
    if not nom:
        raise ErreurAnalyseDce("Nom de fichier manquant.")
    extension = Path(nom).suffix.casefold()
    if extension not in EXTENSIONS_ACCEPTEES:
        raise ErreurAnalyseDce(
            f"Format refusé : {extension or '(aucune extension)'}. Formats acceptés : "
            + ", ".join(EXTENSIONS_ACCEPTEES)
            + ". Les formats bureautiques ne sont pas acceptés sans traitement."
        )
    type_normalise = (type_mime or "").split(";")[0].strip().casefold()
    if type_normalise and type_normalise not in TYPES_ACCEPTES:
        raise ErreurAnalyseDce(
            f"Type de contenu refusé : {type_normalise}. Types acceptés : "
            + ", ".join(TYPES_ACCEPTES)
            + "."
        )
    return extension


def enregistrer_document_dce(
    connexion: Connexion,
    contexte: ContexteClient,
    stockage: StockageFichiers,
    *,
    consultation_id: str,
    entreprise_id: str,
    contenu: bytes,
    libelle: str,
    type_mime: Optional[str],
    nom_fichier: str = "depot.pdf",
    valider: bool = True,
) -> dict[str, Any]:
    """Enregistre le fichier déposé comme `document` de nature `dce`.

    Le fichier est chiffré sur disque, sous un chemin préfixé par le client ;
    **aucun nom fourni par l'utilisateur** n'est utilisé comme nom de fichier
    (annexe A § A6). L'identifiant du document est un UUID produit par le code.

    `valider=False` : voir `creer_consultation` — le dépôt complet ne valide qu'une
    fois, à la fin.
    """
    if not contenu:
        raise ErreurAnalyseDce("Fichier vide : rien à analyser.")
    document_id = str(uuid.uuid4())
    chemin = stockage.ecrire(contexte.client_id, document_id, contenu)
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO document (id, client_id, entreprise_id, fiche_version_id, "
        "consultation_id, nature, type_document, libelle, chemin_stockage, deposant, "
        "empreinte_sha256, taille_octets, mime_type, sensibilite) "
        "VALUES (%(id)s, %(client_id)s, %(entreprise_id)s, NULL, %(consultation_id)s, "
        "'dce', %(type_document)s, %(libelle)s, %(chemin)s, 'entreprise', "
        "%(empreinte)s, %(taille)s, %(mime)s, 'confidentiel') RETURNING *;",
        {
            "id": document_id,
            "entreprise_id": entreprise_id,
            "consultation_id": consultation_id,
            # Jeu `document.type_document` non semé au MVP : la valeur employée est
            # « dce », non sourcée par un document externe, donc à vérifier (annexe B § B6).
            "type_document": "dce",
            "libelle": (Path(nom_fichier or "").name or libelle or "Dépôt de DCE")[:255],
            "chemin": chemin,
            "empreinte": empreinte_sha256(contenu),
            "taille": len(contenu),
            "mime": type_mime or "application/octet-stream",
        },
    )
    if ligne is None:  # pragma: no cover
        raise ErreurAnalyseDce("Enregistrement du document impossible.")
    if valider:
        connexion.valider()
    return ligne


# --------------------------------------------------------------------------- #
# 2/3/4. Extraction, appel, restitution
# --------------------------------------------------------------------------- #
def lire_consultation(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> dict[str, Any]:
    """Consultation + document + éléments + absences. Filtré par client, sans exception."""
    consultation = connexion.executer_une(
        contexte,
        "SELECT * FROM consultation WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": consultation_id},
    )
    if consultation is None:
        raise ConsultationIntrouvable("Consultation introuvable pour ce client.")
    document = connexion.executer_une(
        contexte,
        "SELECT * FROM document WHERE client_id = %(client_id)s "
        "AND consultation_id = %(id)s AND nature = 'dce' ORDER BY date_creation LIMIT 1;",
        {"id": consultation_id},
    )
    elements = connexion.executer(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(id)s AND statut_verification <> 'supprime' "
        "ORDER BY categorie, date_extraction, id;",
        {"id": consultation_id},
    )
    return {
        "consultation": consultation,
        "document": document,
        "elements": elements,
        "elements_non_trouves": _lister_absences(document, elements),
    }


def _lister_absences(
    document: Optional[dict[str, Any]], elements: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Catégories attendues sans aucun élément : écrites « non trouvé dans le document ».

    Sert la SPEC-MVP-V2 § 3.3 (cas « élément introuvable »). Aucune ligne n'est créée
    en base : un « non trouvé » n'a pas de source, il n'a donc pas à être validé par
    un humain comme s'il était un élément.
    """
    if document is None:
        return []
    presentes = {str(e["categorie"]) for e in elements}
    absences = []
    for categorie in CATEGORIES_ATTENDUES:
        if categorie in presentes:
            continue
        absences.append(
            {
                "categorie": categorie,
                "libelle": LIBELLES_CATEGORIES.get(categorie, categorie),
                "message": MENTION_NON_TROUVE,
                "source_document_id": str(document["id"]),
                "source_emplacement": "absent du document",
                "origine": "document_extrait",
                "confiance": "a_verifier",
            }
        )
    return absences


def extraire_document(chemin: str | Path, *, ocr: bool = True) -> ExtractionPdf:
    """Aiguillage : PDF → extraction page par page ; texte brut → une seule page."""
    fichier = Path(chemin)
    if fichier.suffix.casefold() == ".txt":
        texte = fichier.read_text(encoding="utf-8", errors="replace")
        analysable = len("".join(texte.split())) >= extraction_pdf.SEUIL_TEXTE_EXPLOITABLE
        page = extraction_pdf.PageExtraite(
            numero=1,
            texte=texte if analysable else "",
            methode="texte" if analysable else "non_analysable",
            analyseable=analysable,
            message=None if analysable else "Fichier texte sans contenu exploitable.",
        )
        return ExtractionPdf(source=str(fichier), pages=(page,))
    return extraction_pdf.extraire(fichier, ocr=ocr)


def analyser_consultation(
    connexion: Connexion,
    contexte: ContexteClient,
    stockage: StockageFichiers,
    consultation_id: str,
    *,
    fournisseur: Optional[FournisseurModele] = None,
    ocr: bool = True,
) -> dict[str, Any]:
    """Extrait, appelle le fournisseur, enregistre les éléments proposés.

    Aucun appel réseau si le fournisseur est le factice (défaut).
    """
    lecture = lire_consultation(connexion, contexte, consultation_id)
    document = lecture["document"]
    if document is None:
        raise ErreurAnalyseDce(
            "Aucun document de nature `dce` n'est rattaché à cette consultation."
        )

    contenu = stockage.lire(contexte.client_id, str(document["id"]))
    fournisseur_effectif = fournisseur or creer_fournisseur()

    with tempfile.TemporaryDirectory(prefix="analyse_dce_") as dossier:
        extension = ".txt" if str(document.get("mime_type") or "").startswith("text/") else ".pdf"
        chemin_local = Path(dossier) / f"{document['id']}{extension}"
        chemin_local.write_bytes(contenu)
        extraction = extraire_document(chemin_local, ocr=ocr)

    try:
        propositions = verifier_propositions(
            fournisseur_effectif.analyser(extraction).propositions, extraction.pages
        )
    except ReponseModeleInvalide as exc:
        # Refus attendu du garde-fou anti-invention : on ne l'ignore pas, on le rend
        # lisible. Rien n'a été écrit à ce stade, et le dépôt sera annulé par
        # `deposer_et_analyser` — aucune proposition partielle ne subsiste.
        raise _refus_modele(exc) from exc

    # Une nouvelle analyse remplace les propositions précédentes — jamais les
    # vérifications humaines déjà posées.
    connexion.executer(
        contexte,
        "DELETE FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s AND statut_verification = 'propose';",
        {"consultation_id": consultation_id},
    )

    elements: list[dict[str, Any]] = []
    for proposition in propositions:
        ligne = connexion.executer_une(
            contexte,
            "INSERT INTO extraction_element (client_id, consultation_id, categorie, "
            "libelle, valeur, source_document_id, source_emplacement, source_extrait, "
            "confiance, statut_verification, moteur_fournisseur, moteur_modele) "
            "VALUES (%(client_id)s, %(consultation_id)s, %(categorie)s, %(libelle)s, "
            "%(valeur)s, %(source_document_id)s, %(source_emplacement)s, "
            "%(source_extrait)s, 'a_verifier', 'propose', %(moteur)s, %(modele)s) "
            "RETURNING *;",
            {
                "consultation_id": consultation_id,
                "categorie": proposition.categorie,
                "libelle": proposition.libelle,
                "valeur": proposition.valeur,
                "source_document_id": str(document["id"]),
                "source_emplacement": proposition.source_emplacement[:255],
                "source_extrait": proposition.source_extrait,
                "moteur": fournisseur_effectif.nom,
                "modele": fournisseur_effectif.modele,
            },
        )
        if ligne is not None:
            elements.append(ligne)

    connexion.executer(
        contexte,
        "UPDATE consultation SET statut = 'analysee', date_modification = now() "
        "WHERE client_id = %(client_id)s AND id = %(consultation_id)s;",
        {"consultation_id": consultation_id},
    )
    connexion.valider()

    consultation = connexion.executer_une(
        contexte,
        "SELECT * FROM consultation WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": consultation_id},
    )
    return {
        "consultation": consultation,
        "document": document,
        "elements": elements,
        "elements_non_trouves": _lister_absences(document, elements),
        "pages": extraction.resume(),
        "fichier_illisible": bool(extraction.pages)
        and not any(p.analyseable for p in extraction.pages),
        "fournisseur": fournisseur_effectif.nom,
        "modele": fournisseur_effectif.modele,
        "avertissement_fournisseur": fournisseur_effectif.avertissement,
        "brouillon": "brouillon — à relire et à vérifier par un humain",
    }


# --------------------------------------------------------------------------- #
# Vérification humaine
# --------------------------------------------------------------------------- #
def verifier_element(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    consultation_id: str,
    element_id: str,
    action: str,
    verificateur_nom: Optional[str] = None,
    libelle: Optional[str] = None,
    valeur: Optional[str] = None,
) -> dict[str, Any]:
    """Valide, corrige ou supprime un élément — action humaine nommée et horodatée.

    `verificateur_nom` est **obligatoire** pour `valider` et `corriger` (annexe B § B3).
    Une correction ne touche pas la source : elle reste celle de l'extraction.
    """
    action_normalisee = (action or "").strip().casefold()
    if action_normalisee not in ACTIONS_VERIFICATION:
        raise ErreurAnalyseDce(
            f"Action inconnue : {action!r}. Actions admises : {', '.join(ACTIONS_VERIFICATION)}."
        )
    nom = (verificateur_nom or "").strip()
    if action_normalisee in {"valider", "corriger"} and not nom:
        raise ErreurAnalyseDce(
            "`verificateur_nom` est obligatoire pour valider ou corriger un élément : "
            "aucune validation sans action humaine nommée (ligne rouge)."
        )

    existant = connexion.executer_une(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s AND id = %(id)s;",
        {"consultation_id": consultation_id, "id": element_id},
    )
    if existant is None:
        raise ConsultationIntrouvable("Élément introuvable pour ce client.")

    if action_normalisee == "supprimer":
        ligne = connexion.executer_une(
            contexte,
            "UPDATE extraction_element SET statut_verification = 'supprime', "
            "statut_enregistrement = 'archive', verificateur_nom = %(nom)s, "
            "date_verification = now(), date_modification = now() "
            "WHERE client_id = %(client_id)s AND consultation_id = %(consultation_id)s "
            "AND id = %(id)s RETURNING *;",
            {"consultation_id": consultation_id, "id": element_id, "nom": nom or None},
        )
    else:
        statut = "valide" if action_normalisee == "valider" else "corrige"
        nouveau_libelle = libelle if libelle is not None else existant["libelle"]
        nouvelle_valeur = valeur if valeur is not None else existant["valeur"]
        if not str(nouveau_libelle).strip():
            raise ErreurAnalyseDce("Le libellé d'un élément ne peut pas être vide.")
        ligne = connexion.executer_une(
            contexte,
            "UPDATE extraction_element SET statut_verification = %(statut)s, "
            "libelle = %(libelle)s, valeur = %(valeur)s, verificateur_nom = %(nom)s, "
            "date_verification = now(), date_modification = now() "
            "WHERE client_id = %(client_id)s AND consultation_id = %(consultation_id)s "
            "AND id = %(id)s RETURNING *;",
            {
                "statut": statut,
                "libelle": str(nouveau_libelle).strip(),
                "valeur": nouvelle_valeur,
                "nom": nom,
                "consultation_id": consultation_id,
                "id": element_id,
            },
        )

    if ligne is None:  # pragma: no cover
        raise ErreurAnalyseDce("Mise à jour de l'élément impossible.")
    connexion.valider()
    return ligne


def elements_valides(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> list[dict[str, Any]]:
    """Éléments utilisables par la brique C : **seuls** ceux validés par un humain.

    C'est le verrou n° 2 de SPEC-MVP-V2 § 2. Un élément `propose` (ou `corrige`,
    ou `supprime`) n'est pas utilisable en l'état.
    """
    return connexion.executer(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s "
        "AND statut_verification = 'valide' "
        "ORDER BY categorie, date_verification, id;",
        {"consultation_id": consultation_id},
    )


# --------------------------------------------------------------------------- #
# Dépôt complet (utilisé par la route)
# --------------------------------------------------------------------------- #
def deposer_et_analyser(
    connexion: Connexion,
    contexte: ContexteClient,
    stockage: StockageFichiers,
    *,
    entreprise_id: str,
    libelle: str,
    nom_fichier: str,
    contenu: bytes,
    type_mime: Optional[str] = None,
    reference_consultation: Optional[str] = None,
    maitre_ouvrage_declare: Optional[str] = None,
    fournisseur: Optional[FournisseurModele] = None,
    ocr: bool = True,
) -> ResultatDepot:
    """Dépôt → extraction → appel → restitution, en une seule transaction.

    Les écritures intermédiaires ne sont **pas** validées : le seul point de
    validation est la fin de `analyser_consultation`. Si l'analyse est refusée (par
    exemple par le garde-fou anti-invention), tout est annulé — aucune consultation,
    aucun document, aucun élément orphelin — et le fichier chiffré écrit sur disque
    est supprimé.
    """
    controler_fichier(nom_fichier, type_mime)
    document: Optional[dict[str, Any]] = None
    try:
        consultation = creer_consultation(
            connexion,
            contexte,
            entreprise_id=entreprise_id,
            libelle=libelle,
            reference_consultation=reference_consultation,
            maitre_ouvrage_declare=maitre_ouvrage_declare,
            valider=False,
        )
        document = enregistrer_document_dce(
            connexion,
            contexte,
            stockage,
            consultation_id=str(consultation["id"]),
            entreprise_id=str(consultation["entreprise_id"]),
            contenu=contenu,
            libelle=libelle,
            type_mime=type_mime,
            nom_fichier=nom_fichier,
            valider=False,
        )
        resultat = analyser_consultation(
            connexion,
            contexte,
            stockage,
            str(consultation["id"]),
            fournisseur=fournisseur,
            ocr=ocr,
        )
    except Exception:
        connexion.annuler()
        if document is not None:
            # Le fichier chiffré a été écrit avant l'échec : sans ligne `document`
            # (dépôt annulé), il resterait un déchet sur disque. Son échec de
            # suppression ne doit pas masquer l'erreur d'origine, mais il est
            # journalisé — jamais avalé.
            try:
                stockage.supprimer(contexte.client_id, str(document["id"]))
            except Exception:  # noqa: BLE001 — nettoyage au mieux, toujours tracé
                LOGGER.warning(
                    "Dépôt annulé : le fichier du document %s n'a pas pu être supprimé.",
                    document.get("id"),
                    exc_info=True,
                )
        raise
    return ResultatDepot(
        consultation=resultat["consultation"] or consultation,
        document=document,
        elements=tuple(resultat["elements"]),
        elements_non_trouves=tuple(resultat["elements_non_trouves"]),
        pages=tuple(resultat["pages"]),
        fournisseur=resultat["fournisseur"],
        modele=resultat["modele"],
        avertissement_fournisseur=resultat["avertissement_fournisseur"],
        fichier_illisible=resultat["fichier_illisible"],
    )
