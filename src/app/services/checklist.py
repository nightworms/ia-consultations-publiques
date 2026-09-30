"""Service — checklist de conformité (brique C).

Croise les **pièces exigées validées** d'un DCE (sortie de la brique B) avec la
**bibliothèque d'entreprise** (brique A), et produit une ligne par exigence :
`presente`, `manquante` ou `a_verifier`.

Ce module applique, par du code, les règles opposables du projet :

* **verrou n° 2** (`docs/SPEC-MVP-V2.md` § 2) : seuls les éléments
  `extraction_element.statut_verification = valide` alimentent la checklist. Un
  élément encore `propose` (ou `corrige`, ou `supprime`) n'apparaît pas ;
* **invariant I8** (annexe B § B5) : une ligne `presente` référence un `document_id`
  **du même client** ; une ligne `manquante` n'en référence **aucun**. Une
  correspondance incertaine est `a_verifier`, **jamais** `presente` ;
* **ligne rouge** (`docs/SPEC-MVP-V2.md` § 2) : le système **ne fabrique jamais** la
  pièce manquante, **ne tranche pas** une ambiguïté à la place de l'humain et **ne
  garantit aucune conformité**. Aucune sortie de ce module ne dit « conforme » ;
  toute valeur extraite est exposée avec sa **source** (document + emplacement).

Aucun seuil n'est écrit en dur : la fenêtre d'alerte d'échéance vient du réglage
`FENETRE_ALERTE_JOURS` (`app.services.versionnement`), et l'état de validité est
**calculé** (`app.domain.commun.calculer_statut_validite`).

Tout le SQL passe par `storage.connexion.Connexion`, donc par le filtre `client_id`
imposé par le contexte de session (annexe A § A1).
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from typing import Any, Optional, Sequence

from app.domain.commun import StatutValidite, calculer_statut_validite
from app.services.analyse_dce import ConsultationIntrouvable
from app.services.versionnement import fenetre_alerte_jours_depuis_environnement
from app.storage.connexion import Connexion, ContexteClient

#: Les trois statuts d'une ligne de checklist (annexe B § B5, jeu `checklist.statut_ligne`).
STATUTS_LIGNE = ("presente", "manquante", "a_verifier")

#: Phrase d'aide rappelée dans toute réponse : la checklist n'est pas un certificat.
MENTION_AIDE_RELECTURE = (
    "Checklist — outil d'aide à la relecture, pas un certificat de conformité. "
    "Aucune conformité n'est garantie."
)


class ErreurChecklist(RuntimeError):
    """Exécution ou lecture de checklist refusée. Toujours explicite."""


class ChecklistIntrouvable(ErreurChecklist):
    """Aucune exécution de checklist pour cette consultation et ce client."""


# --------------------------------------------------------------------------- #
# Appariement texte — déterministe, conservateur, documenté
# --------------------------------------------------------------------------- #
#: Mots vides et mots génériques de document. Ils ne portent pas le sens métier de
#: l'exigence : les retirer évite des correspondances trompeuses. La liste est
#: **conservatrice** (on préfère un `a_verifier` à un faux `presente`).
_MOTS_VIDES = frozenset(
    {
        # articles, prépositions, conjonctions…
        "de", "du", "des", "d", "l", "la", "le", "les", "un", "une", "au", "aux",
        "a", "et", "ou", "en", "sur", "pour", "par", "avec", "sans", "dans", "ce",
        "cet", "cette", "ces", "son", "sa", "ses", "leur", "leurs", "il", "elle",
        "est", "sont", "doit", "doivent", "tel", "telle", "ayant", "plus", "moins",
        # mots génériques de document/dossier
        "piece", "pieces", "copie", "copies", "document", "documents", "dossier",
        "fourni", "fournir", "produire", "joint", "jointe", "joints", "jointes",
        "signe", "signee", "signes", "signees", "mention", "suivant", "suivante",
        "suivants", "suivantes", "dernier", "derniere", "derniers", "dernieres",
        "candidat", "offre", "offres", "appui", "date", "datant", "realise",
        "realisee", "realises", "realisees", "comparable", "comparables",
        "presentant", "presente", "valide", "valides", "validite", "cours",
        # durées génériques
        "an", "ans", "annee", "annees", "mois", "jour", "jours", "semaine",
        "semaines", "six", "cinq",
    }
)

_MOTIF_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normaliser_texte(texte: Any) -> str:
    """Normalise un texte : minuscules, sans accents, ponctuation → espaces.

    Déterministe et indépendant de la locale : c'est la base de l'appariement.
    """
    brut = unicodedata.normalize("NFKD", str(texte or ""))
    sans_accents = "".join(c for c in brut if not unicodedata.combining(c))
    return " ".join(_MOTIF_NON_ALNUM.sub(" ", sans_accents.casefold()).split())


def tokens_significatifs(texte: Any) -> frozenset[str]:
    """Mots porteurs de sens d'un texte (mots vides retirés)."""
    return frozenset(
        mot for mot in normaliser_texte(texte).split() if mot not in _MOTS_VIDES
    )


def _niveau_correspondance(
    exigence_libelle: str,
    exigence_valeur: Optional[str],
    piece_libelle: Optional[str],
    piece_type: Optional[str],
) -> str:
    """Compare une exigence à une pièce de la bibliothèque.

    Renvoie `forte`, `incertaine` ou `aucune`. Règles, dans l'ordre :

    1. libellés (ou type de pièce) **identiques** après normalisation → `forte` ;
    2. tous les mots significatifs de l'exigence présents dans la pièce → `forte` ;
    3. le **type** déclaré de la pièce est entièrement décrit par l'exigence → `forte` ;
    4. au moins un mot significatif commun, sans couverture totale → `incertaine` ;
    5. aucun mot commun → `aucune`.

    Aucune règle « floue » : une couverture partielle est **toujours** `incertaine`
    (donc `a_verifier`), jamais `presente`.
    """
    exigence = f"{exigence_libelle or ''} {exigence_valeur or ''}".strip()
    e_tokens = tokens_significatifs(exigence)
    if not e_tokens:
        return "aucune"
    d_tokens = tokens_significatifs(f"{piece_libelle or ''} {piece_type or ''}")
    type_tokens = tokens_significatifs(piece_type)

    e_norm = normaliser_texte(exigence)
    if e_norm and e_norm in {normaliser_texte(piece_libelle), normaliser_texte(piece_type)}:
        return "forte"
    if e_tokens <= d_tokens:
        return "forte"
    if type_tokens and type_tokens <= e_tokens:
        return "forte"
    if e_tokens & d_tokens:
        return "incertaine"
    return "aucune"


# --------------------------------------------------------------------------- #
# Lecture des entrées
# --------------------------------------------------------------------------- #
def _lire_consultation(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> dict[str, Any]:
    consultation = connexion.executer_une(
        contexte,
        "SELECT * FROM consultation WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": consultation_id},
    )
    if consultation is None:
        raise ConsultationIntrouvable("Consultation introuvable pour ce client.")
    return consultation


def _lire_fiche(
    connexion: Connexion, contexte: ContexteClient, fiche_version_id: Optional[str]
) -> dict[str, Any]:
    """La fiche demandée, ou la plus récente du client. Jamais celle d'un autre."""
    if fiche_version_id:
        fiche = connexion.executer_une(
            contexte,
            "SELECT * FROM fiche_version WHERE client_id = %(client_id)s AND id = %(id)s;",
            {"id": fiche_version_id},
        )
        if fiche is None:
            raise ErreurChecklist(
                "Version de fiche introuvable pour ce client : la checklist n'est "
                "calculée que sur une fiche du client de la session."
            )
        return fiche
    fiche = connexion.executer_une(
        contexte,
        "SELECT * FROM fiche_version WHERE client_id = %(client_id)s "
        "ORDER BY numero_version DESC, date_creation DESC LIMIT 1;",
    )
    if fiche is None:
        raise ErreurChecklist(
            "Aucune version de fiche pour ce client : la checklist croise l'extraction "
            "avec la bibliothèque ; sans fiche, il n'y a rien à croiser."
        )
    return fiche


def _elements_valides(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> list[dict[str, Any]]:
    """Les éléments **validés** de la consultation — verrou n° 2. Les `propose` sont exclus.

    Toutes catégories confondues : la liste sert à la fois au croisement des pièces
    exigées et à la détection des contradictions (y compris une date limite
    divergente, `docs/SPEC-MVP-V2.md` § 3.4).
    """
    return connexion.executer(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s "
        "AND statut_verification = 'valide' "
        "ORDER BY categorie, date_verification, date_extraction, id;",
        {"consultation_id": consultation_id},
    )


def _exigences_validees(
    elements_valides: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Les **pièces exigées** validées — c'est ce qui alimente une ligne de checklist."""
    return [e for e in elements_valides if str(e["categorie"]) == "piece_exigee"]


def _documents_bibliotheque(
    connexion: Connexion, contexte: ContexteClient, fiche_version_id: str
) -> list[dict[str, Any]]:
    """Les pièces de la bibliothèque rattachées à la fiche (jamais un DCE)."""
    return connexion.executer(
        contexte,
        "SELECT id, libelle, type_document, emetteur, date_emission, "
        "date_validite_fin, reference_document FROM document "
        "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s "
        "AND nature = 'piece_bibliotheque' AND statut_enregistrement = 'actif' "
        "ORDER BY date_creation, id;",
        {"fiche": fiche_version_id},
    )


def _elements_non_valides(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> int:
    """Nombre d'éléments lus mais restés non validés (`propose` ou `corrige`)."""
    ligne = connexion.executer_une(
        contexte,
        "SELECT count(*) AS n FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s "
        "AND statut_verification IN ('propose', 'corrige') "
        "AND statut_enregistrement = 'actif';",
        {"consultation_id": consultation_id},
    )
    return int(ligne["n"]) if ligne else 0


def _categories_sans_element(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> list[str]:
    """Catégories attendues par la brique B et restées sans aucun élément."""
    attendues = ("piece_exigee", "critere", "date_limite")
    lignes = connexion.executer(
        contexte,
        "SELECT DISTINCT categorie FROM extraction_element "
        "WHERE client_id = %(client_id)s AND consultation_id = %(consultation_id)s "
        "AND statut_verification <> 'supprime';",
        {"consultation_id": consultation_id},
    )
    presentes = {str(ligne["categorie"]) for ligne in lignes}
    return [c for c in attendues if c not in presentes]


# --------------------------------------------------------------------------- #
# Détection des contradictions (le système ne choisit pas)
# --------------------------------------------------------------------------- #
def _contradictions(elements: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Repère les éléments de même libellé portant des valeurs **différentes**.

    Ex. deux « Date limite de remise » incohérentes. Les deux valeurs et leur source
    sont exposées ; le système ne choisit pas (`docs/SPEC-MVP-V2.md` § 3.4).
    """
    groupes: dict[str, list[dict[str, Any]]] = {}
    for element in elements:
        groupes.setdefault(normaliser_texte(element["libelle"]), []).append(element)
    resultat: list[dict[str, Any]] = []
    for groupe in groupes.values():
        valeurs = {
            normaliser_texte(e.get("valeur")) for e in groupe if e.get("valeur")
        }
        if len(groupe) <= 1 or len(valeurs) <= 1:
            continue
        resultat.append(
            {
                "libelle": str(groupe[0]["libelle"]),
                "categorie": str(groupe[0]["categorie"]),
                "valeurs": [
                    {
                        "valeur": e.get("valeur"),
                        "source_document_id": e.get("source_document_id"),
                        "source_emplacement": e.get("source_emplacement"),
                    }
                    for e in groupe
                ],
            }
        )
    return resultat


def _valeurs_contradictoires_par_libelle(
    contradictions: Sequence[dict[str, Any]],
) -> dict[str, list[str]]:
    """Index `libellé normalisé` → valeurs normalisées, pour marquer les lignes."""
    index: dict[str, list[str]] = {}
    for contradiction in contradictions:
        index[normaliser_texte(contradiction["libelle"])] = sorted(
            {
                normaliser_texte(valeur["valeur"])
                for valeur in contradiction["valeurs"]
                if valeur.get("valeur")
            }
        )
    return index


# --------------------------------------------------------------------------- #
# Construction d'une ligne
# --------------------------------------------------------------------------- #
def _decrire_document(document: dict[str, Any]) -> str:
    libelle = str(document.get("libelle") or "(sans libellé)")
    type_document = document.get("type_document")
    return f"{libelle} [{type_document}]" if type_document else libelle


def _date_lisible(valeur: Any) -> str:
    if valeur is None:
        return "date non renseignée"
    if isinstance(valeur, _dt.date):
        return valeur.isoformat()
    return str(valeur)


def _construire_ligne(
    exigence: dict[str, Any],
    *,
    documents: Sequence[dict[str, Any]],
    contradiction: Optional[Sequence[str]],
    fenetre_alerte_jours: Optional[int],
    aujourd_hui: _dt.date,
) -> dict[str, Any]:
    """Statut, justification et document retenu pour une exigence validée."""
    libelle = str(exigence["libelle"])
    ligne: dict[str, Any] = {
        "extraction_element_id": str(exigence["id"]),
        "libelle_piece": libelle[:255],
        "document_id": None,
    }

    # (a) Deux valeurs contradictoires : les deux sont exposées, aucun choix.
    if contradiction:
        ligne["statut"] = "a_verifier"
        ligne["justification"] = (
            "Valeurs contradictoires exposées, non tranchées par le système : "
            + " ; ".join(contradiction)
            + ". À vérifier par un humain contre le DCE d'origine."
        )
        return ligne

    correspondances_fortes: list[dict[str, Any]] = []
    correspondances_incertaines: list[dict[str, Any]] = []
    for document in documents:
        niveau = _niveau_correspondance(
            libelle,
            exigence.get("valeur"),
            document.get("libelle"),
            document.get("type_document"),
        )
        if niveau == "forte":
            correspondances_fortes.append(document)
        elif niveau == "incertaine":
            correspondances_incertaines.append(document)

    # (b) Plusieurs pièces correspondent : le système ne choisit pas.
    if len(correspondances_fortes) > 1:
        ligne["statut"] = "a_verifier"
        ligne["justification"] = (
            "Plusieurs pièces de la bibliothèque correspondent ("
            + " ; ".join(_decrire_document(d) for d in correspondances_fortes)
            + ") : le système ne choisit pas, l'humain tranche."
        )
        return ligne

    # (c) Une seule pièce correspond : on regarde son échéance.
    if len(correspondances_fortes) == 1:
        document = correspondances_fortes[0]
        statut_validite = calculer_statut_validite(
            document.get("date_validite_fin"),
            aujourd_hui=aujourd_hui,
            fenetre_alerte_jours=fenetre_alerte_jours,
        )
        if statut_validite == StatutValidite.EXPIRE:
            ligne["statut"] = "a_verifier"
            ligne["document_id"] = str(document["id"])
            ligne["justification"] = (
                f"Pièce présente ({_decrire_document(document)}) mais échéance dépassée "
                f"le {_date_lisible(document.get('date_validite_fin'))} : à vérifier, "
                "le système ne la déclare pas valide."
            )
            return ligne
        if statut_validite == StatutValidite.ECHEANCE_PROCHE:
            ligne["statut"] = "a_verifier"
            ligne["document_id"] = str(document["id"])
            ligne["justification"] = (
                f"Pièce présente ({_decrire_document(document)}) mais échéance proche "
                f"({_date_lisible(document.get('date_validite_fin'))}, fenêtre de "
                f"{fenetre_alerte_jours} jours) : à vérifier."
            )
            return ligne
        ligne["statut"] = "presente"
        ligne["document_id"] = str(document["id"])
        ligne["justification"] = (
            f"Pièce de la bibliothèque retenue : {_decrire_document(document)}."
        )
        return ligne

    # (d) Correspondance incertaine : jamais `presente`.
    if correspondances_incertaines:
        ligne["statut"] = "a_verifier"
        ligne["justification"] = (
            "Correspondance incertaine avec "
            + " ; ".join(_decrire_document(d) for d in correspondances_incertaines)
            + " : à vérifier par un humain, le système ne la déclare pas présente."
        )
        return ligne

    # (e) Aucune correspondance : manquante, et rien n'est fabriqué.
    ligne["statut"] = "manquante"
    ligne["justification"] = (
        "Aucune pièce correspondante dans la bibliothèque de la fiche utilisée : "
        "le système ne fabrique pas la pièce manquante."
    )
    return ligne


# --------------------------------------------------------------------------- #
# Exécution (POST)
# --------------------------------------------------------------------------- #
def executer_checklist(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    consultation_id: str,
    execute_par: str,
    fiche_version_id: Optional[str] = None,
    fenetre_alerte_jours: Optional[int] = None,
    aujourd_hui: Optional[_dt.date] = None,
) -> dict[str, Any]:
    """Exécute la checklist et l'enregistre. Renvoie l'exécution, ses lignes, le résumé.

    `execute_par` est le **nom de l'humain** qui lance l'exécution : il est obligatoire.
    `fiche_version_id` est facultatif ; à défaut, la version la plus récente du client
    est employée (et elle est enregistrée dans `checklist_execution.fiche_version_id`).
    """
    nom = (execute_par or "").strip()
    if not nom:
        raise ErreurChecklist(
            "`execute_par` est obligatoire : une exécution de checklist est une action "
            "nommée, jamais anonyme."
        )

    consultation = _lire_consultation(connexion, contexte, consultation_id)
    fiche = _lire_fiche(connexion, contexte, fiche_version_id)
    fiche_id = str(fiche["id"])

    fenetre = (
        fenetre_alerte_jours
        if fenetre_alerte_jours is not None
        else fenetre_alerte_jours_depuis_environnement()
    )
    reference = aujourd_hui or _dt.date.today()

    elements_valides = _elements_valides(connexion, contexte, consultation_id)
    exigences = _exigences_validees(elements_valides)
    documents = _documents_bibliotheque(connexion, contexte, fiche_id)
    contradictions = _contradictions(elements_valides)
    valeurs_contradictoires = _valeurs_contradictoires_par_libelle(contradictions)

    lignes_construites: list[dict[str, Any]] = []
    for exigence in exigences:
        cle = normaliser_texte(exigence["libelle"])
        lignes_construites.append(
            _construire_ligne(
                exigence,
                documents=documents,
                contradiction=valeurs_contradictoires.get(cle),
                fenetre_alerte_jours=fenetre,
                aujourd_hui=reference,
            )
        )

    nb_presentes = sum(1 for l in lignes_construites if l["statut"] == "presente")
    nb_manquantes = sum(1 for l in lignes_construites if l["statut"] == "manquante")
    nb_a_verifier = sum(1 for l in lignes_construites if l["statut"] == "a_verifier")
    non_valides = _elements_non_valides(connexion, contexte, consultation_id)
    extraction_partielle = non_valides > 0
    categories_sans_element = _categories_sans_element(connexion, contexte, consultation_id)

    execution = connexion.executer_une(
        contexte,
        "INSERT INTO checklist_execution (client_id, consultation_id, fiche_version_id, "
        "execute_par, nb_exigences, nb_presentes, nb_manquantes, nb_a_verifier, "
        "extraction_partielle) "
        "VALUES (%(client_id)s, %(consultation_id)s, %(fiche)s, %(execute_par)s, "
        "%(nb_exigences)s, %(nb_presentes)s, %(nb_manquantes)s, %(nb_a_verifier)s, "
        "%(extraction_partielle)s) RETURNING *;",
        {
            "consultation_id": str(consultation["id"]),
            "fiche": fiche_id,
            "execute_par": nom,
            "nb_exigences": len(lignes_construites),
            "nb_presentes": nb_presentes,
            "nb_manquantes": nb_manquantes,
            "nb_a_verifier": nb_a_verifier,
            "extraction_partielle": 1 if extraction_partielle else 0,
        },
    )
    if execution is None:  # pragma: no cover — RETURNING garantit une ligne
        raise ErreurChecklist("Enregistrement de l'exécution impossible.")
    execution_id = str(execution["id"])

    for construite in lignes_construites:
        connexion.executer_une(
            contexte,
            "INSERT INTO checklist_ligne (client_id, checklist_execution_id, "
            "extraction_element_id, libelle_piece, statut, justification, document_id) "
            "VALUES (%(client_id)s, %(execution)s, %(element)s, %(libelle)s, %(statut)s, "
            "%(justification)s, %(document)s) RETURNING id;",
            {
                "execution": execution_id,
                "element": construite["extraction_element_id"],
                "libelle": construite["libelle_piece"],
                "statut": construite["statut"],
                "justification": construite["justification"],
                "document": construite["document_id"],
            },
        )

    connexion.valider()

    # Relecture des lignes par la jointure : chaque ligne est renvoyée **avec la
    # source de l'exigence** (annexe C), jamais reconstituée.
    lignes = _lire_lignes(connexion, contexte, execution_id)
    return _assembler_reponse(
        consultation=consultation,
        execution=execution,
        lignes=lignes,
        contradictions=contradictions,
        documents=documents,
        non_valides=non_valides,
        categories_sans_element=categories_sans_element,
    )


def _lire_lignes(
    connexion: Connexion, contexte: ContexteClient, execution_id: str
) -> list[dict[str, Any]]:
    """Lignes d'une exécution, avec la source de l'exigence et la pièce retenue."""
    return connexion.executer(
        contexte,
        "SELECT l.*, e.categorie AS exigence_categorie, e.valeur AS exigence_valeur, "
        "e.source_document_id AS exigence_source_document_id, "
        "e.source_emplacement AS exigence_source_emplacement, "
        "e.confiance AS exigence_confiance, "
        "e.verificateur_nom AS exigence_verificateur_nom, "
        "d.libelle AS piece_libelle, d.type_document AS piece_type_document, "
        "d.date_validite_fin AS piece_date_validite_fin "
        "FROM checklist_ligne l "
        "JOIN extraction_element e ON e.id = l.extraction_element_id "
        "AND e.client_id = l.client_id "
        "LEFT JOIN document d ON d.id = l.document_id AND d.client_id = l.client_id "
        "WHERE l.client_id = %(client_id)s AND l.checklist_execution_id = %(execution)s "
        "ORDER BY l.statut, l.date_creation, l.id;",
        {"execution": execution_id},
    )


# --------------------------------------------------------------------------- #
# Lecture (GET)
# --------------------------------------------------------------------------- #
def lire_checklist(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str
) -> dict[str, Any]:
    """Renvoie la **dernière** exécution de checklist de la consultation, et ses lignes.

    Chaque ligne est exposée avec la **source de l'exigence** (document + emplacement)
    et, le cas échéant, la pièce de la bibliothèque retenue.
    """
    consultation = _lire_consultation(connexion, contexte, consultation_id)
    execution = connexion.executer_une(
        contexte,
        "SELECT * FROM checklist_execution WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s "
        "ORDER BY date_execution DESC, id DESC LIMIT 1;",
        {"consultation_id": consultation_id},
    )
    if execution is None:
        raise ChecklistIntrouvable(
            "Aucune checklist n'a encore été exécutée pour cette consultation."
        )

    lignes = _lire_lignes(connexion, contexte, str(execution["id"]))
    return _assembler_reponse(
        consultation=consultation,
        execution=execution,
        lignes=lignes,
        contradictions=None,
        documents=[],
        non_valides=None,
        categories_sans_element=None,
    )


# --------------------------------------------------------------------------- #
# Mise en forme de la réponse
# --------------------------------------------------------------------------- #
def _assembler_reponse(
    *,
    consultation: dict[str, Any],
    execution: dict[str, Any],
    lignes: Sequence[dict[str, Any]],
    contradictions: Optional[Sequence[dict[str, Any]]],
    documents: Sequence[dict[str, Any]],
    non_valides: Optional[int],
    categories_sans_element: Optional[Sequence[str]],
) -> dict[str, Any]:
    """Résumé, manques et avertissements. Ne dit jamais « conforme »."""
    manques = [
        str(ligne["libelle_piece"]) for ligne in lignes if ligne["statut"] == "manquante"
    ]
    a_verifier = [
        str(ligne["libelle_piece"]) for ligne in lignes if ligne["statut"] == "a_verifier"
    ]

    avertissements: list[str] = [MENTION_AIDE_RELECTURE]
    if int(execution.get("extraction_partielle") or 0) == 1:
        nombre = non_valides if non_valides is not None else "au moins un"
        avertissements.append(
            f"Extraction partielle : {nombre} élément(s) du DCE ne sont pas validés et "
            "n'alimentent pas la checklist. Validez-les (ou vérifiez-les) pour un "
            "résultat complet."
        )
    if categories_sans_element:
        avertissements.append(
            "Catégorie(s) attendue(s) sans élément : "
            + ", ".join(categories_sans_element)
            + " — « non trouvé dans le document », rien n'est comblé."
        )
    if manques:
        avertissements.append(
            f"{len(manques)} pièce(s) exigée(s) sans correspondance dans la "
            "bibliothèque : le système ne fabrique aucune pièce."
        )
    if contradictions:
        for contradiction in contradictions:
            valeurs = " ; ".join(
                f"{valeur.get('valeur')} (source : {valeur.get('source_emplacement')})"
                for valeur in contradiction["valeurs"]
            )
            avertissements.append(
                "Valeurs contradictoires pour "
                f"« {contradiction['libelle']} » : {valeurs}. "
                "Le système ne choisit pas, l'humain tranche."
            )

    resume = {
        "nb_exigences": int(execution["nb_exigences"]),
        "nb_presentes": int(execution["nb_presentes"]),
        "nb_manquantes": int(execution["nb_manquantes"]),
        "nb_a_verifier": int(execution["nb_a_verifier"]),
        "extraction_partielle": bool(int(execution.get("extraction_partielle") or 0)),
        "manques": manques,
        "a_verifier": a_verifier,
        "categories_sans_element": list(categories_sans_element or []),
        "nb_pieces_bibliotheque": len(documents),
    }

    lignes_formatees = [_formater_ligne(ligne) for ligne in lignes]
    return {
        "consultation": consultation,
        "execution": execution,
        "lignes": lignes_formatees,
        "contradictions": list(contradictions or []),
        "resume": resume,
        "avertissements": avertissements,
        "mention": MENTION_AIDE_RELECTURE,
        "brouillon": "brouillon — à relire et à vérifier par un humain",
    }


def _formater_ligne(ligne: dict[str, Any]) -> dict[str, Any]:
    """Ajoute à une ligne sa source d'exigence, sans jamais rien inventer."""
    formatee = dict(ligne)
    if "exigence_source_document_id" in formatee:
        formatee["origine"] = "document_extrait"
        formatee["source_document_id"] = formatee.get("exigence_source_document_id")
        formatee["source_emplacement"] = formatee.get("exigence_source_emplacement")
    return formatee


def resume_manques(execution: dict[str, Any]) -> dict[str, Any]:
    """Résumé minimal des manques, pour un affichage d'aide (§ 3.4 écran C2)."""
    return {
        "extraction_partielle": bool(int(execution.get("extraction_partielle") or 0)),
        "nb_exigences": int(execution["nb_exigences"]),
        "nb_presentes": int(execution["nb_presentes"]),
        "nb_manquantes": int(execution["nb_manquantes"]),
        "nb_a_verifier": int(execution["nb_a_verifier"]),
    }
