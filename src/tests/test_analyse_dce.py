"""Tests de la brique B — dépôt d'un DCE, extraction, analyse, restitution sourcée.

Aucune donnée réelle : le matériau est le jeu **fictif** de `src/tests/fixtures/`,
chaque fichier portant la mention « DOCUMENT FICTIF — DÉMONSTRATION » (décision D10).
Aucun appel réseau : le fournisseur employé est le factice (défaut).

Les exigences vérifiables du lot sont démontrées par exécution :
1. migration `0003` : `up` puis `down` ;
2. un PDF fictif déposé produit une pièce, un critère et une date limite, **chacun
   avec fichier source et emplacement** ;
3. une page scannée est lue par l'OCR **si `tesseract` est disponible** ; sinon le
   chemin est déclaré non testé, jamais présenté comme validé ;
4. un élément introuvable est restitué « non trouvé dans le document » ;
5. seul un élément `valide` est utilisable par la brique C ;
6. deux clients ne voient pas leurs consultations respectives.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.config import charger_config
from app.services import analyse_dce, extraction_pdf
from app.services.analyse_dce import ErreurAnalyseDce, ConsultationIntrouvable
from app.services.authentification import ServiceAuthentification
from app.services.extraction_pdf import ExtractionPdf
from app.services.fournisseur_modele import FournisseurFactice
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.fichiers import StockageFichiers
from app.storage.migrations import ExecuteurMigrations, lister_migrations

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF_FICTIF = FIXTURES / "dce_fictif.pdf"
PDF_SANS_DATE = FIXTURES / "dce_fictif_sans_date.pdf"
PDF_SCANNE = FIXTURES / "dce_fictif_scanne.pdf"

LIBELLE_FICTIF = "Consultation fictive — DÉMONSTRATION"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel
RELECTEUR_FICTIF = "Relecteur fictif (démonstration)"


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def _inserer_entreprise(connexion: Connexion, contexte: ContexteClient, libelle: str) -> str:
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO entreprise (client_id, libelle_court) "
        "VALUES (%(client_id)s, %(libelle)s) RETURNING id;",
        {"libelle": libelle},
    )
    assert ligne is not None
    connexion.valider()
    return str(ligne["id"])


def _stockage(config) -> StockageFichiers:
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _deposer(connexion, contexte, config, chemin: Path, *, libelle: str = LIBELLE_FICTIF):
    entreprise_id = _inserer_entreprise(connexion, contexte, "Entreprise fictive — DÉMONSTRATION")
    return analyse_dce.deposer_et_analyser(
        connexion,
        contexte,
        _stockage(config),
        entreprise_id=entreprise_id,
        libelle=libelle,
        nom_fichier=chemin.name,
        contenu=chemin.read_bytes(),
        type_mime="application/pdf",
    )


def _table_existe(conn: ConnexionAdministration, nom: str) -> bool:
    lignes = conn.lire(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s;",
        (nom,),
    )
    return len(lignes) > 0


def _colonne_existe(conn: ConnexionAdministration, table: str, colonne: str) -> bool:
    lignes = conn.lire(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s;",
        (table, colonne),
    )
    return len(lignes) > 0


@pytest.fixture(scope="module")
def extraction_scan() -> ExtractionPdf:
    """Extraction du PDF « scanné », faite une fois pour tous les tests du fichier."""
    return extraction_pdf.extraire(PDF_SCANNE)


# --------------------------------------------------------------------------- #
# 1. Migration 0003 : up puis down (exigence vérifiable n° 1)
# --------------------------------------------------------------------------- #
def test_migration_0003_est_presente_et_lisible():
    numeros = [m.numero for m in lister_migrations()]
    assert "0003" in numeros
    migration = next(m for m in lister_migrations() if m.numero == "0003")
    assert migration.nom == "0003_analyse_dce"
    assert migration.sql_up and migration.sql_down


def test_migration_0003_down_puis_up(connexion_admin, base_migree):
    executeur = ExecuteurMigrations(charger_config().database_url)
    assert _table_existe(connexion_admin, "consultation")
    assert _table_existe(connexion_admin, "extraction_element")
    assert _colonne_existe(connexion_admin, "document", "nature")
    assert _colonne_existe(connexion_admin, "document", "consultation_id")

    # Modifié par le lot L4 (phase 3) : l'annulation portait sur « 0003 » en dur,
    # ce que l'ajout de la migration 0004 (checklist) invalide. Elle porte désormais
    # sur les deux dernières migrations, ce qui reste vrai à chaque ajout de lot.
    annulees = executeur.down(2)
    assert "0003" in annulees
    assert not _table_existe(connexion_admin, "consultation")
    assert not _table_existe(connexion_admin, "extraction_element")
    assert not _colonne_existe(connexion_admin, "document", "nature")
    assert not _colonne_existe(connexion_admin, "document", "consultation_id")

    appliquees = executeur.up()
    assert set(appliquees) == set(annulees)
    assert _table_existe(connexion_admin, "consultation")
    assert _colonne_existe(connexion_admin, "document", "consultation_id")


def test_invariant_i7_refuse_un_dce_sans_consultation(connexion, contexte_a):
    """Invariant I7 : `nature = dce` exige un `consultation_id`."""
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — I7")
    with pytest.raises(psycopg.errors.CheckViolation):
        connexion.executer(
            contexte_a,
            "INSERT INTO document (client_id, entreprise_id, fiche_version_id, nature, "
            "type_document, libelle, chemin_stockage, deposant) "
            "VALUES (%(client_id)s, %(entreprise_id)s, NULL, 'dce', 'dce', 'fictif', "
            "'clients/x/y.bin', 'entreprise');",
            {"entreprise_id": entreprise_id},
        )
    connexion.annuler()


# --------------------------------------------------------------------------- #
# 2. Dépôt d'un PDF fictif → pièce, critère, date limite, chacune sourcée
# --------------------------------------------------------------------------- #
def test_depot_pdf_fictif_restitueles_trois_categories_avec_source(connexion, contexte_a, config):
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    categories = {e["categorie"] for e in resultat.elements}
    assert {"piece_exigee", "critere", "date_limite"} <= categories

    # Chaque élément porte sa source : fichier + emplacement (ligne rouge).
    for element in resultat.elements:
        assert str(element["source_document_id"]) == str(resultat.document["id"])
        assert element["source_emplacement"]
        assert element["source_extrait"]
        assert element["confiance"] == "a_verifier"
        assert element["statut_verification"] == "propose"
        assert element["moteur_fournisseur"] == "factice"

    dates = [e for e in resultat.elements if e["categorie"] == "date_limite"]
    assert dates[0]["valeur"] == "2026-12-15"  # date écrite dans le document fictif
    assert "15 décembre 2026" in dates[0]["source_extrait"]

    criteres = [e for e in resultat.elements if e["categorie"] == "critere"]
    assert {c["valeur"] for c in criteres} == {"40 %", "35 %", "25 %"}

    assert resultat.consultation["statut"] == "analysee"
    assert resultat.document["nature"] == "dce"
    assert resultat.document["fiche_version_id"] is None
    assert resultat.elements_non_trouves == ()
    assert resultat.fichier_illisible is False
    # Le fournisseur factice est annoncé pour ce qu'il est.
    assert resultat.fournisseur == "factice"
    assert "non-IQ" in (resultat.avertissement_fournisseur or "")


def test_tous_les_elements_stockes_portent_une_source_reelle(connexion, contexte_a, config):
    """Aucune ligne en base sans source, et la source existe bien dans le document."""
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    stockage = _stockage(config)
    contenu = stockage.lire(contexte_a.client_id, str(resultat.document["id"]))
    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / "document.pdf"
        chemin.write_bytes(contenu)
        extraction = extraction_pdf.extraire(chemin)

    lignes = connexion.executer(
        contexte_a,
        "SELECT categorie, source_document_id, source_emplacement, source_extrait "
        "FROM extraction_element WHERE client_id = %(client_id)s AND consultation_id = %(id)s;",
        {"id": str(resultat.consultation["id"])},
    )
    assert lignes
    for ligne in lignes:
        assert str(ligne["source_document_id"]) == str(resultat.document["id"])
        assert ligne["source_emplacement"].strip()
        if ligne["source_extrait"]:
            aplatir = " ".join(ligne["source_extrait"].split())
            assert aplatir in " ".join(extraction.texte_complet.split()), (
                "un extrait stocké ne se retrouve pas dans le document : source invérifiable"
            )


def test_le_depot_n_accepte_que_les_formats_traites(connexion, contexte_a, config):
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — formats")
    with pytest.raises(ErreurAnalyseDce) as exc:
        analyse_dce.deposer_et_analyser(
            connexion,
            contexte_a,
            _stockage(config),
            entreprise_id=entreprise_id,
            libelle=LIBELLE_FICTIF,
            nom_fichier="dce.docx",
            contenu=b"PK\x03\x04docx fictif",
            type_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert "Format refusé" in str(exc.value)
    connexion.annuler()


# --------------------------------------------------------------------------- #
# 3. Élément introuvable → « non trouvé dans le document » (jamais comblé)
# --------------------------------------------------------------------------- #
def test_element_introuvable_est_declare_non_trouve(connexion, contexte_a, config):
    resultat = _deposer(connexion, contexte_a, config, PDF_SANS_DATE, libelle="DCE fictif incomplet")
    categories = {e["categorie"] for e in resultat.elements}
    assert "piece_exigee" in categories

    absences = {a["categorie"]: a for a in resultat.elements_non_trouves}
    assert set(absences) == {"critere", "date_limite"}
    for absence in absences.values():
        assert absence["message"] == "non trouvé dans le document"
        assert absence["source_document_id"] == str(resultat.document["id"])
        assert absence["source_emplacement"] == "absent du document"

    # Rien n'a été inventé en base pour ces deux catégories.
    lignes = connexion.executer(
        contexte_a,
        "SELECT categorie FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(id)s;",
        {"id": str(resultat.consultation["id"])},
    )
    assert {ligne["categorie"] for ligne in lignes} == categories
    assert "critere" not in categories and "date_limite" not in categories


# --------------------------------------------------------------------------- #
# 4. Verrou n° 2 : seul un élément `valide` alimente la brique C
# --------------------------------------------------------------------------- #
def test_seul_un_element_valide_est_utilisable_par_la_brique_c(connexion, contexte_a, config):
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    consultation_id = str(resultat.consultation["id"])

    # Avant toute action humaine : rien n'est utilisable.
    assert analyse_dce.elements_valides(connexion, contexte_a, consultation_id) == []

    piece = next(e for e in resultat.elements if e["categorie"] == "piece_exigee")
    critere = next(e for e in resultat.elements if e["categorie"] == "critere")

    valide = analyse_dce.verifier_element(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        element_id=str(piece["id"]),
        action="valider",
        verificateur_nom=RELECTEUR_FICTIF,
    )
    assert valide["statut_verification"] == "valide"
    assert valide["verificateur_nom"] == RELECTEUR_FICTIF
    assert valide["date_verification"] is not None

    utilisables = analyse_dce.elements_valides(connexion, contexte_a, consultation_id)
    assert [str(e["id"]) for e in utilisables] == [str(piece["id"])]
    # Le critère, encore `propose`, n'est pas utilisable.
    assert str(critere["id"]) not in {str(e["id"]) for e in utilisables}

    # Une correction est aussi une action humaine nommée.
    corrige = analyse_dce.verifier_element(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        element_id=str(critere["id"]),
        action="corriger",
        verificateur_nom=RELECTEUR_FICTIF,
        libelle="Prix des prestations (libellé corrigé par l'humain)",
    )
    assert corrige["statut_verification"] == "corrige"
    assert "corrigé" in corrige["libelle"]
    # La source de l'extraction n'est pas effacée par une correction.
    assert corrige["source_emplacement"] == critere["source_emplacement"]
    assert str(corrige["id"]) not in {
        str(e["id"]) for e in analyse_dce.elements_valides(connexion, contexte_a, consultation_id)
    }


def test_verificateur_nom_obligatoire_pour_valider(connexion, contexte_a, config):
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    element = resultat.elements[0]
    with pytest.raises(ErreurAnalyseDce) as exc:
        analyse_dce.verifier_element(
            connexion,
            contexte_a,
            consultation_id=str(resultat.consultation["id"]),
            element_id=str(element["id"]),
            action="valider",
        )
    assert "verificateur_nom" in str(exc.value)
    connexion.annuler()


def test_supprimer_un_element_le_retire_de_la_lecture(connexion, contexte_a, config):
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    consultation_id = str(resultat.consultation["id"])
    element = resultat.elements[0]

    supprime = analyse_dce.verifier_element(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        element_id=str(element["id"]),
        action="supprimer",
        verificateur_nom=RELECTEUR_FICTIF,
    )
    assert supprime["statut_verification"] == "supprime"

    lecture = analyse_dce.lire_consultation(connexion, contexte_a, consultation_id)
    assert str(element["id"]) not in {str(e["id"]) for e in lecture["elements"]}


# --------------------------------------------------------------------------- #
# 5. Isolation entre deux clients (exigence vérifiable n° 6)
# --------------------------------------------------------------------------- #
def test_deux_clients_ne_voient_pas_leurs_consultations(
    connexion, contexte_a, contexte_b, config
):
    resultat = _deposer(connexion, contexte_a, config, PDF_FICTIF)
    consultation_id = str(resultat.consultation["id"])
    element_id = str(resultat.elements[0]["id"])

    # A voit la sienne.
    assert analyse_dce.lire_consultation(connexion, contexte_a, consultation_id)

    # B ne la voit pas — et n'obtient aucun indice sur son existence.
    with pytest.raises(ConsultationIntrouvable):
        analyse_dce.lire_consultation(connexion, contexte_b, consultation_id)

    consult_b = connexion.executer(
        contexte_b,
        "SELECT id FROM consultation WHERE client_id = %(client_id)s AND id = %(id)s;",
        {"id": consultation_id},
    )
    assert consult_b == []
    element_b = connexion.executer(
        contexte_b,
        "SELECT id FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(id)s;",
        {"id": consultation_id},
    )
    assert element_b == []

    # B ne peut pas non plus agir sur un élément de A, ni le lire dans la brique C.
    with pytest.raises(ConsultationIntrouvable):
        analyse_dce.verifier_element(
            connexion,
            contexte_b,
            consultation_id=consultation_id,
            element_id=element_id,
            action="valider",
            verificateur_nom="Relecteur fictif B",
        )
    assert analyse_dce.elements_valides(connexion, contexte_b, consultation_id) == []


# --------------------------------------------------------------------------- #
# 6. Chemin OCR sur la variante « scannée » (exigence vérifiable n° 3)
# --------------------------------------------------------------------------- #
def test_le_pdf_scanne_n_a_aucune_couche_texte():
    """Vérification du matériau lui-même : sans texte extractible, l'OCR est requis."""
    extraction = extraction_pdf.extraire(PDF_SCANNE, ocr=False)
    assert extraction.nombre_pages >= 1
    assert all(not p.analyseable for p in extraction.pages)
    assert all(p.methode == "non_analysable" for p in extraction.pages)


def test_page_scannee_lue_par_ocr_ou_declaree_non_testee(extraction_scan):
    """OCR réellement exercé si `tesseract` est là ; sinon le chemin est dit non testé."""
    if not extraction_pdf.ocr_disponible():
        # Chemin livré mais non testé : aucun test ne prétend l'avoir validé.
        assert all(p.methode == "non_analysable" for p in extraction_scan.pages)
        pytest.skip(
            "tesseract absent : chemin OCR livré mais NON TESTÉ (aucune validation prétendue)."
        )

    pages_ocr = [p for p in extraction_scan.pages if p.methode == "ocr"]
    assert pages_ocr, "tesseract est présent mais aucune page n'a été lue par OCR"
    texte = " ".join(p.texte for p in pages_ocr)
    assert "ARTICLE" in texte.upper()
    assert "DOCUMENT FICTIF" in texte.upper() or "FICTIF" in texte.upper()
    # Une page lue par OCR reste analystée comme une page normale.
    assert all(p.analyseable for p in pages_ocr)


def test_depot_du_pdf_scanne_par_le_service(connexion, contexte_a, config, extraction_scan):
    """Le dépôt d'un scan suit le chemin réel : OCR, puis extraction sourcée."""
    resultat = _deposer(connexion, contexte_a, config, PDF_SCANNE, libelle="DCE fictif scanné")
    if not extraction_pdf.ocr_disponible():
        assert resultat.fichier_illisible is True
        assert resultat.elements == ()
        assert {a["categorie"] for a in resultat.elements_non_trouves} == {
            "piece_exigee",
            "critere",
            "date_limite",
        }
        for absence in resultat.elements_non_trouves:
            assert absence["message"] == "non trouvé dans le document"
        pytest.skip("tesseract absent : l'analyse d'un scan n'a pas pu être testée.")
    else:
        categories = {e["categorie"] for e in resultat.elements}
        assert {"piece_exigee", "date_limite"} <= categories
        for element in resultat.elements:
            assert element["source_emplacement"].startswith("page ")
            assert element["source_extrait"]


# --------------------------------------------------------------------------- #
# 7. Routes gelées (annexe C)
# --------------------------------------------------------------------------- #
def _creer_utilisateur(connexion, contexte, identifiant: str, config) -> ServiceAuthentification:
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, "Utilisateur fictif", MOT_DE_PASSE_FICTIF)
    connexion.valider()
    return service


def test_route_depot_lecture_et_validation(connexion, contexte_a, config):
    _creer_utilisateur(connexion, contexte_a, "api-analyse@fictif.test", config)
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — route")

    from app.main import app

    with TestClient(app) as client:
        assert client.post(
            "/api/v1/consultations",
            data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
            files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
        ).status_code == 401

        connexion_ok = client.post(
            "/api/v1/connexion",
            json={"identifiant": "api-analyse@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        assert connexion_ok.status_code == 200
        assert NOM_COOKIE_SESSION in connexion_ok.cookies

        depot = client.post(
            "/api/v1/consultations",
            data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
            files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
        )
        assert depot.status_code == 201, depot.text
        corps = depot.json()
        assert corps["consultation"]["statut"] == "analysee"
        assert corps["fournisseur"] == "factice"
        assert "brouillon" in corps["brouillon"]

        for element in corps["elements"]:
            assert element["origine"] == "document_extrait"
            assert element["confiance"] == "a_verifier"
            assert element["source_document_id"]
            assert element["source_emplacement"]

        consultation_id = corps["consultation"]["id"]
        lecture = client.get(f"/api/v1/consultations/{consultation_id}")
        assert lecture.status_code == 200
        assert len(lecture.json()["elements"]) == len(corps["elements"])

        element = corps["elements"][0]
        refuse = client.post(
            f"/api/v1/consultations/{consultation_id}/elements/{element['id']}",
            json={"action": "valider"},
        )
        assert refuse.status_code == 400
        assert "verificateur_nom" in refuse.json()["detail"]

        accepte = client.post(
            f"/api/v1/consultations/{consultation_id}/elements/{element['id']}",
            json={"action": "valider", "verificateur_nom": RELECTEUR_FICTIF},
        )
        assert accepte.status_code == 200, accepte.text
        assert accepte.json()["element"]["statut_verification"] == "valide"
        assert accepte.json()["element"]["date_verification"]

        inconnue = client.get(f"/api/v1/consultations/{uuid.uuid4()}")
        assert inconnue.status_code == 404


def test_route_refuse_un_format_non_traite(connexion, contexte_a, config):
    _creer_utilisateur(connexion, contexte_a, "api-format@fictif.test", config)
    entreprise_id = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive — format")

    from app.main import app

    with TestClient(app) as client:
        client.post(
            "/api/v1/connexion",
            json={"identifiant": "api-format@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        refus = client.post(
            "/api/v1/consultations",
            data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_id},
            files={"fichier": ("dce.docx", b"contenu fictif", "application/octet-stream")},
        )
        assert refus.status_code == 400
        assert "Format refusé" in refus.json()["detail"]


def test_route_isolation_entre_deux_clients(connexion, contexte_a, contexte_b, config):
    """Le client B, authentifié, n'obtient rien de la consultation de A."""
    _creer_utilisateur(connexion, contexte_a, "api-a@fictif.test", config)
    _creer_utilisateur(connexion, contexte_b, "api-b@fictif.test", config)
    entreprise_a = _inserer_entreprise(connexion, contexte_a, "Entreprise fictive A")

    from app.main import app

    with TestClient(app) as client:
        client.post(
            "/api/v1/connexion",
            json={"identifiant": "api-a@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        depot = client.post(
            "/api/v1/consultations",
            data={"libelle": LIBELLE_FICTIF, "entreprise_id": entreprise_a},
            files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
        )
        assert depot.status_code == 201
        consultation_id = depot.json()["consultation"]["id"]
        assert client.get(f"/api/v1/consultations/{consultation_id}").status_code == 200

        client.post("/api/v1/deconnexion")
        client.post(
            "/api/v1/connexion",
            json={"identifiant": "api-b@fictif.test", "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        # 404 : aucune information n'est divulguée sur l'existence de la consultation.
        assert client.get(f"/api/v1/consultations/{consultation_id}").status_code == 404
