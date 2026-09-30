"""Tests de la brique C — checklist de conformité (lot L4) — exécutés réellement.

Aucune donnée réelle : clients, entreprises, pièces, exigences et noms sont
**FICTIFS et signalés** (« DOCUMENT FICTIF — DÉMONSTRATION »).

Les exigences vérifiables du lot sont démontrées par exécution :

1. migration `0004` : `up` puis `down` réussis, structures présentes puis retirées ;
2. **verrou n° 2** : seuls les éléments `statut_verification = valide` alimentent la
   checklist ; un élément encore `propose` n'apparaît pas ;
3. cas d'erreur obligatoires :
   - pièce exigée absente → `manquante`, **aucune pièce fabriquée** ;
   - pièce présente mais échéance passée → `a_verifier` **avec la raison** ;
   - extraction partielle → `extraction_partielle = vrai`, la checklist le dit ;
   - bibliothèque vide → beaucoup de `manquante`, rien d'inventé (comptage) ;
   - deux valeurs contradictoires → les deux sont exposées, le système ne choisit pas ;
   - correspondance incertaine → `a_verifier`, **jamais** `presente` ;
4. deux clients ne voient pas leurs checklists respectives (isolation) ;
5. routes gelées de l'annexe C : `POST` puis `GET`, 401 sans session.
"""

from __future__ import annotations

import uuid

import pytest
import psycopg
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.config import charger_config
from app.services import analyse_dce, checklist
from app.services.analyse_dce import ConsultationIntrouvable
from app.services.authentification import ServiceAuthentification
from app.services.bibliotheque import ServiceBibliotheque
from app.services.checklist import ChecklistIntrouvable, ErreurChecklist
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.migrations import ExecuteurMigrations, lister_migrations
from app.storage.repositories import DepotDocument

MENTION = "DOCUMENT FICTIF — DÉMONSTRATION"
RELECTEUR_FICTIF = "Relecteur fictif (démonstration)"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def _service_bibliotheque(connexion, contexte):
    config = charger_config()
    return ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)


def _preparer_fiche(
    connexion: Connexion, contexte: ContexteClient, libelle: str = "Entreprise fictive"
) -> tuple[str, str]:
    """Crée une entreprise (fictive) et sa première version de fiche."""
    service = _service_bibliotheque(connexion, contexte)
    entreprise_id = service.creer_entreprise(f"{libelle} — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id, commentaire="Jeu de démonstration fictif")
    connexion.valider()
    return entreprise_id, str(fiche["id"])


def _piece_bibliotheque(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    entreprise_id: str,
    fiche_version_id: str,
    libelle: str,
    type_document: str,
    date_validite_fin: str | None = None,
) -> str:
    """Ajoute une pièce (fictive) à la bibliothèque. Renvoie son document_id."""
    depot = DepotDocument(connexion, charger_config().cle_chiffrement_maitresse)
    document_id = depot.creer(
        contexte,
        entreprise_id=entreprise_id,
        fiche_version_id=fiche_version_id,
        type_document=type_document,
        libelle=f"{libelle} — {MENTION}",
        chemin_stockage=f"clients/{contexte.client_id}/{uuid.uuid4()}.bin",
        deposant="entreprise",
        date_validite_fin=date_validite_fin,
    )
    connexion.valider()
    return document_id


def _consultation(
    connexion: Connexion, contexte: ContexteClient, entreprise_id: str, libelle: str
) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO consultation (client_id, entreprise_id, libelle) "
        "VALUES (%(client_id)s, %(entreprise_id)s, %(libelle)s) RETURNING id;",
        {"entreprise_id": entreprise_id, "libelle": f"{libelle} — {MENTION}"},
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _document_dce(
    connexion: Connexion, contexte: ContexteClient, entreprise_id: str, consultation_id: str
) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO document (client_id, entreprise_id, fiche_version_id, "
        "consultation_id, nature, type_document, libelle, chemin_stockage, deposant) "
        "VALUES (%(client_id)s, %(entreprise_id)s, NULL, %(consultation_id)s, 'dce', "
        "'dce', %(libelle)s, %(chemin)s, 'entreprise') RETURNING id;",
        {
            "entreprise_id": entreprise_id,
            "consultation_id": consultation_id,
            "libelle": f"DCE fictif — {MENTION}",
            "chemin": f"clients/{contexte.client_id}/{uuid.uuid4()}.bin",
        },
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _element(
    connexion: Connexion,
    contexte: ContexteClient,
    *,
    consultation_id: str,
    document_id: str,
    libelle: str,
    categorie: str = "piece_exigee",
    valeur: str | None = None,
) -> str:
    """Insère un élément extrait **non validé** (`propose`), avec sa source."""
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO extraction_element (client_id, consultation_id, categorie, libelle, "
        "valeur, source_document_id, source_emplacement, statut_verification) "
        "VALUES (%(client_id)s, %(consultation_id)s, %(categorie)s, %(libelle)s, "
        "%(valeur)s, %(document)s, %(emplacement)s, 'propose') RETURNING id;",
        {
            "consultation_id": consultation_id,
            "categorie": categorie,
            "libelle": libelle,
            "valeur": valeur,
            "document": document_id,
            "emplacement": "page 1 — ARTICLE 2",
        },
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _valider(
    connexion: Connexion, contexte: ContexteClient, consultation_id: str, element_id: str
) -> None:
    """Valide un élément par l'action humaine réelle (verrou n° 2)."""
    analyse_dce.verifier_element(
        connexion,
        contexte,
        consultation_id=consultation_id,
        element_id=element_id,
        action="valider",
        verificateur_nom=RELECTEUR_FICTIF,
    )


def _compter_documents(connexion: Connexion, contexte: ContexteClient) -> int:
    ligne = connexion.executer_une(
        contexte, "SELECT count(*) AS n FROM document WHERE client_id = %(client_id)s;"
    )
    return int(ligne["n"]) if ligne else 0


def _table_existe(conn: ConnexionAdministration, nom: str) -> bool:
    lignes = conn.lire(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s;",
        (nom,),
    )
    return len(lignes) > 0


# --------------------------------------------------------------------------- #
# 1. Migration 0004 : up puis down (exigence vérifiable n° 1)
# --------------------------------------------------------------------------- #
def test_migration_0004_presente_et_deux_sections():
    numeros = [m.numero for m in lister_migrations()]
    assert "0004" in numeros
    migration = next(m for m in lister_migrations() if m.numero == "0004")
    assert migration.nom == "0004_checklist"
    assert migration.sql_up and migration.sql_down


def test_migration_0004_up_down_up(connexion_admin, base_migree):
    executeur = ExecuteurMigrations(charger_config().database_url)
    assert _table_existe(connexion_admin, "checklist_execution")
    assert _table_existe(connexion_admin, "checklist_ligne")

    annulees = executeur.down(1)
    assert annulees == ["0004"]
    assert not _table_existe(connexion_admin, "checklist_execution")
    assert not _table_existe(connexion_admin, "checklist_ligne")

    # Le jeu de référence de la brique C est retiré par l'annulation.
    restes = connexion_admin.lire(
        "SELECT 1 FROM jeu_reference WHERE namespace = 'checklist.statut_ligne';"
    )
    assert restes == []

    reappliquees = executeur.up()
    assert reappliquees == ["0004"]
    assert _table_existe(connexion_admin, "checklist_execution")
    assert _table_existe(connexion_admin, "checklist_ligne")
    valeurs = connexion_admin.lire(
        "SELECT code FROM valeur_reference WHERE namespace = 'checklist.statut_ligne' "
        "ORDER BY ordre;"
    )
    assert [ligne[0] for ligne in valeurs] == ["presente", "manquante", "a_verifier"]


# --------------------------------------------------------------------------- #
# 2. Verrou n° 2 — seuls les éléments validés alimentent la checklist
# --------------------------------------------------------------------------- #
def test_verrou_2_seuls_les_elements_valides_alimentent(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)

    valide_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation d'assurance responsabilité décennale",
    )
    _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Formulaire de candidature",  # reste `propose`
    )
    _valider(connexion, contexte_a, consultation_id, valide_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    assert resultat["execution"]["nb_exigences"] == 1
    libelles = [ligne["libelle_piece"] for ligne in resultat["lignes"]]
    assert libelles == ["Attestation d'assurance responsabilité décennale"]
    assert "Formulaire de candidature" not in libelles
    # L'élément non validé ne laisse aucune ligne derrière lui.
    assert len(resultat["lignes"]) == 1


# --------------------------------------------------------------------------- #
# 3a. Pièce absente → manquante, aucune pièce fabriquée
# --------------------------------------------------------------------------- #
def test_piece_absente_manquante_et_rien_fabrique(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation de vigilance sociale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)

    avant = _compter_documents(connexion, contexte_a)
    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )
    apres = _compter_documents(connexion, contexte_a)

    ligne = resultat["lignes"][0]
    assert ligne["statut"] == "manquante"
    assert ligne["document_id"] is None
    # Aucune pièce n'a été fabriquée : le nombre de documents est inchangé.
    assert apres == avant
    assert resultat["resume"]["nb_manquantes"] == 1
    assert "ne fabrique" in ligne["justification"]


# --------------------------------------------------------------------------- #
# 3b. Pièce présente mais échéance passée → a_verifier AVEC LA RAISON
# --------------------------------------------------------------------------- #
def test_piece_presente_mais_echeance_passee_a_verifier(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    _piece_bibliotheque(
        connexion, contexte_a,
        entreprise_id=entreprise_id, fiche_version_id=fiche,
        libelle="Attestation d'assurance décennale",
        type_document="attestation_assurance",
        date_validite_fin="2020-01-01",  # échéance passée
    )
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation d'assurance responsabilité décennale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    ligne = resultat["lignes"][0]
    assert ligne["statut"] == "a_verifier"
    assert ligne["document_id"] is not None  # la pièce est bien identifiée
    assert "échéance dépassée" in ligne["justification"]
    assert "2020-01-01" in ligne["justification"]


def test_piece_presente_sans_echeance_est_presente(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    piece_id = _piece_bibliotheque(
        connexion, contexte_a,
        entreprise_id=entreprise_id, fiche_version_id=fiche,
        libelle="Attestation d'assurance décennale",
        type_document="attestation_assurance",
    )
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation d'assurance responsabilité décennale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )
    ligne = resultat["lignes"][0]
    assert ligne["statut"] == "presente"
    assert str(ligne["document_id"]) == piece_id


# --------------------------------------------------------------------------- #
# 3c. Extraction partielle → extraction_partielle = vrai, la checklist le dit
# --------------------------------------------------------------------------- #
def test_extraction_partielle_signalee(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    valide_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation de vigilance sociale",
    )
    _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Fiche technique du système d'étanchéité",  # non validé
    )
    _valider(connexion, contexte_a, consultation_id, valide_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    assert int(resultat["execution"]["extraction_partielle"]) == 1
    assert resultat["resume"]["extraction_partielle"] is True
    assert any("Extraction partielle" in a for a in resultat["avertissements"])
    # Le DCE n'a pas de critère ni de date limite : c'est aussi signalé, sans être
    # présenté comme un contenu existant.
    assert "critere" in resultat["resume"]["categories_sans_element"]


# --------------------------------------------------------------------------- #
# 3d. Bibliothèque vide → beaucoup de manquante, rien d'inventé
# --------------------------------------------------------------------------- #
def test_bibliotheque_vide_beaucoup_de_manquante(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)  # fiche sans aucune pièce
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    for libelle in (
        "Formulaire de candidature",
        "Attestation de vigilance sociale",
        "Fiche technique du système d'étanchéité",
    ):
        element_id = _element(
            connexion, contexte_a,
            consultation_id=consultation_id, document_id=document_id, libelle=libelle,
        )
        _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    assert resultat["resume"]["nb_pieces_bibliotheque"] == 0
    assert resultat["resume"]["nb_manquantes"] == 3
    assert resultat["resume"]["nb_presentes"] == 0
    assert all(ligne["document_id"] is None for ligne in resultat["lignes"])
    assert all(ligne["statut"] == "manquante" for ligne in resultat["lignes"])


# --------------------------------------------------------------------------- #
# 3e. Deux valeurs contradictoires → les deux sont exposées
# --------------------------------------------------------------------------- #
def test_deux_valeurs_contradictoires(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    for valeur in ("2026-12-15", "2026-12-20"):  # mêmes libellés, valeurs différentes
        element_id = _element(
            connexion, contexte_a,
            consultation_id=consultation_id, document_id=document_id,
            libelle="Date limite de remise", categorie="date_limite", valeur=valeur,
        )
        _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    # Les deux valeurs et leur source sont exposées ; le système ne choisit pas.
    assert len(resultat["contradictions"]) == 1
    contradiction = resultat["contradictions"][0]
    assert contradiction["libelle"] == "Date limite de remise"
    valeurs_exposees = {str(v["valeur"]) for v in contradiction["valeurs"]}
    assert valeurs_exposees == {"2026-12-15", "2026-12-20"}
    assert all(v["source_emplacement"] for v in contradiction["valeurs"])
    assert any("contradictoires" in a for a in resultat["avertissements"])


def test_contradiction_entre_pieces_exigees(connexion, contexte_a):
    """Deux pièces exigées de même libellé et de valeurs divergentes : les deux
    lignes sont exposées et marquées « à vérifier », aucune n'est tranchée."""
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    for valeur in ("exemplaire original", "copie certifiée"):
        element_id = _element(
            connexion, contexte_a,
            consultation_id=consultation_id, document_id=document_id,
            libelle="Formulaire de candidature", valeur=valeur,
        )
        _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    assert len(resultat["lignes"]) == 2
    assert all(ligne["statut"] == "a_verifier" for ligne in resultat["lignes"])
    for ligne in resultat["lignes"]:
        assert "exemplaire original" in ligne["justification"]
        assert "copie certifiee" in ligne["justification"]
    assert len(resultat["contradictions"]) == 1


# --------------------------------------------------------------------------- #
# 3f. Correspondance incertaine → a_verifier, jamais presente
# --------------------------------------------------------------------------- #
def test_correspondance_incertaine_jamais_presente(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    _piece_bibliotheque(
        connexion, contexte_a,
        entreprise_id=entreprise_id, fiche_version_id=fiche,
        libelle="Attestation de capacité financière",
        type_document="attestation_capacite",
    )
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation de vigilance sociale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)

    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )
    assert resultat["lignes"][0]["statut"] == "a_verifier"


# --------------------------------------------------------------------------- #
# 4. Isolation entre deux clients
# --------------------------------------------------------------------------- #
def test_deux_clients_ne_voient_pas_leurs_checklists(connexion, contexte_a, contexte_b):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation de vigilance sociale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)
    checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )

    # B ne voit ni la consultation de A, ni sa checklist.
    with pytest.raises(ConsultationIntrouvable):
        checklist.lire_checklist(connexion, contexte_b, consultation_id)

    lignes_b = connexion.executer(
        contexte_b, "SELECT count(*) AS n FROM checklist_ligne WHERE client_id = %(client_id)s;"
    )
    executions_b = connexion.executer(
        contexte_b,
        "SELECT count(*) AS n FROM checklist_execution WHERE client_id = %(client_id)s;",
    )
    assert int(lignes_b[0]["n"]) == 0
    assert int(executions_b[0]["n"]) == 0

    # Et B ne peut pas exécuter une checklist sur la consultation de A.
    with pytest.raises(ConsultationIntrouvable):
        checklist.executer_checklist(
            connexion, contexte_b,
            consultation_id=consultation_id, execute_par="Client B (fictif)",
        )


def test_execute_par_obligatoire(connexion, contexte_a):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    with pytest.raises(ErreurChecklist):
        checklist.executer_checklist(
            connexion, contexte_a, consultation_id=consultation_id, execute_par="  ",
            fiche_version_id=fiche,
        )


def test_invariant_i8_au_niveau_de_la_base(connexion, contexte_a, contexte_b):
    """I8 est porté par le schéma : un `presente` sans document est refusé, un
    `manquante` avec document est refusé, et un document d'un AUTRE client est refusé."""
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_dce = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_dce,
        libelle="Attestation de vigilance sociale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)
    resultat = checklist.executer_checklist(
        connexion, contexte_a,
        consultation_id=consultation_id, execute_par=RELECTEUR_FICTIF,
        fiche_version_id=fiche,
    )
    execution_id = str(resultat["execution"]["id"])

    # Une pièce de l'AUTRE client (B).
    entreprise_b, fiche_b = _preparer_fiche(connexion, contexte_b, "Entreprise fictive B")
    piece_b = _piece_bibliotheque(
        connexion, contexte_b,
        entreprise_id=entreprise_b, fiche_version_id=fiche_b,
        libelle="Pièce de B", type_document="autre",
    )

    requete = (
        "INSERT INTO checklist_ligne (client_id, checklist_execution_id, "
        "extraction_element_id, libelle_piece, statut, justification, document_id) "
        "VALUES (%(client_id)s, %(execution)s, %(element)s, 'x', %(statut)s, 'y', "
        "%(document)s) RETURNING id;"
    )
    base = {"execution": execution_id, "element": element_id}

    # presente sans document → refusé par la contrainte garde-fou.
    with pytest.raises(psycopg.errors.CheckViolation):
        connexion.executer_une(contexte_a, requete, {**base, "statut": "presente", "document": None})
    connexion.annuler()

    # manquante avec document → refusé par la contrainte garde-fou.
    with pytest.raises(psycopg.errors.CheckViolation):
        connexion.executer_une(contexte_a, requete, {**base, "statut": "manquante", "document": document_dce})
    connexion.annuler()

    # presente référençant un document d'un autre client → refusé par la clé
    # étrangère composite `(document_id, client_id)`.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        connexion.executer_une(contexte_a, requete, {**base, "statut": "presente", "document": piece_b})
    connexion.annuler()


def test_lecture_sans_execution_est_explicite(connexion, contexte_a):
    entreprise_id, _fiche = _preparer_fiche(connexion, contexte_a)
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    with pytest.raises(ChecklistIntrouvable):
        checklist.lire_checklist(connexion, contexte_a, consultation_id)


# --------------------------------------------------------------------------- #
# 5. Routes gelées de l'annexe C
# --------------------------------------------------------------------------- #
def test_routes_checklist_refusent_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/consultations/n-importe/checklist").status_code == 401
        assert client.post("/api/v1/consultations/n-importe/checklist").status_code == 401


def test_routes_checklist_parcours_complet(connexion, contexte_a, config):
    entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    _piece_bibliotheque(
        connexion, contexte_a,
        entreprise_id=entreprise_id, fiche_version_id=fiche,
        libelle="Attestation d'assurance décennale",
        type_document="attestation_assurance",
    )
    consultation_id = _consultation(connexion, contexte_a, entreprise_id, "Consultation A")
    document_id = _document_dce(connexion, contexte_a, entreprise_id, consultation_id)
    element_id = _element(
        connexion, contexte_a,
        consultation_id=consultation_id, document_id=document_id,
        libelle="Attestation d'assurance responsabilité décennale",
    )
    _valider(connexion, contexte_a, consultation_id, element_id)

    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(
        contexte_a, "checklist@fictif.test", "Relecteur fictif", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()
    identite = service.authentifier("checklist@fictif.test", MOT_DE_PASSE_FICTIF)
    assert identite is not None

    from app.main import app

    with TestClient(app) as client:
        client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))

        # Avant toute exécution : 404 explicite.
        assert (
            client.get(f"/api/v1/consultations/{consultation_id}/checklist").status_code
            == 404
        )

        reponse = client.post(
            f"/api/v1/consultations/{consultation_id}/checklist",
            json={"execute_par": RELECTEUR_FICTIF, "fiche_version_id": fiche},
        )
        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["resume"]["nb_exigences"] == 1
        assert corps["resume"]["nb_presentes"] == 1
        # Chaque ligne porte sa source d'exigence (annexe C).
        ligne = corps["lignes"][0]
        assert ligne["origine"] == "document_extrait"
        assert str(ligne["source_document_id"]) == document_id
        assert ligne["source_emplacement"]
        # Jamais le mot « conforme » dans la sortie.
        assert "conforme" not in reponse.text.casefold()
        assert "contradictions" in corps

        relecture = client.get(f"/api/v1/consultations/{consultation_id}/checklist")
        assert relecture.status_code == 200
        corps_get = relecture.json()
        assert corps_get["execution"]["id"] == corps["execution"]["id"]
        assert len(corps_get["lignes"]) == 1
        assert corps_get["lignes"][0]["statut"] == "presente"
