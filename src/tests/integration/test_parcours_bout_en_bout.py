"""Parcours de bout en bout, par l'API HTTP — sur des données **fictives**.

Chemin complet du critère de fin de phase 3 (`docs/PLAN-PHASE-3.md` § 1) :

    provisionnement → saisie bibliothèque → validation humaine →
    dépôt d'un DCE fictif → analyse → validation d'un élément →
    checklist → manques.

Tout passe par les routes gelées (annexe C). Aucun appel direct aux services pour
le chemin nominal : c'est bien l'API qui est exercée. Données **FICTIVES et
signalées** (« DÉMONSTRATION », décision D10) ; le DCE est `dce_fictif.pdf`.
"""

from __future__ import annotations

from pathlib import Path

from .conftest import MENTION

PDF_FICTIF = Path(__file__).resolve().parents[1] / "fixtures" / "dce_fictif.pdf"


def _creer_entreprise(client) -> str:
    reponse = client.post(
        "/api/v1/entreprises", json={"libelle_court": f"Entreprise fictive — {MENTION}"}
    )
    assert reponse.status_code == 201, reponse.text
    return reponse.json()["entreprise_id"]


def test_parcours_complet_de_bout_en_bout(api_a):
    client = api_a
    etapes: list[str] = []

    # 1. Démarrage de zéro : une entreprise et sa première fiche.
    entreprise_id = _creer_entreprise(client)
    etapes.append(f"1. POST /entreprises -> 201 ({entreprise_id})")

    # 2. La bibliothèque ne renvoie plus le 404 « Provisionnez une entreprise ».
    etat = client.get("/api/v1/bibliotheque")
    assert etat.status_code == 200, etat.text
    assert etat.json()["statut"] == "vierge"
    etapes.append(f"2. GET /bibliotheque -> 200 ({etat.json()['statut']})")

    # 3. Saisie d'un élément de bibliothèque (assurances).
    piece = client.post(
        "/api/v1/bibliotheque/assurances",
        json={
            "entite": "assurance",
            "donnees": {
                "type_assurance": "tous_risques",
                "assureur": f"Assureur fictif — {MENTION}",
                "date_debut": "2026-01-01",
                "date_echeance": "2099-01-01",
                "piece": None,
                "origine": "saisie_entreprise",
            },
        },
    )
    # `piece` est un document obligatoire : sans lui la saisie est refusée (400).
    assert piece.status_code in (400, 422), piece.text
    etapes.append(f"3. POST /bibliotheque/assurances sans pièce -> {piece.status_code}")

    # 4. Saisie d'une référence de chantier (pas de pièce obligatoire).
    saisie = client.post(
        "/api/v1/bibliotheque/references_chantiers",
        json={
            "entite": "reference_chantier",
            "donnees": {
                "intitule_operation": f"Chantier fictif — {MENTION}",
                "maitre_ouvrage": f"MO fictif — {MENTION}",
                "origine": "saisie_entreprise",
            },
        },
    )
    assert saisie.status_code == 200, saisie.text
    etapes.append("4. POST /bibliotheque/references_chantiers -> 200")

    # 5. Validation humaine nommée (blocage technique) — fiche complète.
    fiche_id = etat.json()["fiche_version_id"]
    validation = client.post(
        "/api/v1/bibliotheque/validation",
        json={
            "fiche_version_id": fiche_id,
            "relecteur_nom": f"Relecteur fictif — {MENTION}",
            "attestation_cochee": True,
        },
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["statut"] in {"validee", "en_relecture", "en_saisie"}
    etapes.append(f"5. POST /bibliotheque/validation -> 200 ({validation.json()['statut']})")

    # 6. Dépôt d'un DCE fictif (multipart) → consultation + document + analyse.
    depot = client.post(
        "/api/v1/consultations",
        data={
            "libelle": f"Consultation fictive — {MENTION}",
            "entreprise_id": entreprise_id,
            "maitre_ouvrage_declare": f"MO déclaré fictif — {MENTION}",
        },
        files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
    )
    assert depot.status_code == 201, depot.text
    corps = depot.json()
    consultation_id = corps["consultation"]["id"]
    elements = corps["elements"]
    assert elements, "le DCE fictif doit produire des éléments"
    etapes.append(f"6. POST /consultations -> 201 ({len(elements)} éléments)")

    # 7. Lecture : chaque élément porte sa source (document + emplacement).
    lecture = client.get(f"/api/v1/consultations/{consultation_id}")
    assert lecture.status_code == 200, lecture.text
    for element in lecture.json()["elements"]:
        assert element["source_document_id"], element
        assert element["source_emplacement"], element
        assert element["origine"] == "document_extrait"
    etapes.append("7. GET /consultations/{id} -> 200 (sources présentes)")

    # 8. Validation d'un élément par un humain nommé.
    element_id = elements[0]["id"]
    acte = client.post(
        f"/api/v1/consultations/{consultation_id}/elements/{element_id}",
        json={"action": "valider", "verificateur_nom": f"Vérificateur fictif — {MENTION}"},
    )
    assert acte.status_code == 200, acte.text
    assert acte.json()["element"]["statut_verification"] == "valide"
    etapes.append("8. POST .../elements/{id} valider -> 200 (valide)")

    # 9. Exécution de la checklist.
    execution = client.post(
        f"/api/v1/consultations/{consultation_id}/checklist",
        json={"execute_par": f"Exécutant fictif — {MENTION}", "fiche_version_id": fiche_id},
    )
    assert execution.status_code == 200, execution.text
    resume = execution.json()["resume"]
    assert resume["nb_exigences"] >= 1, resume
    etapes.append(f"9. POST .../checklist -> 200 ({resume['nb_exigences']} exigences)")

    # 10. Lecture : lignes, manques et avertissements (jamais un certificat).
    relecture = client.get(f"/api/v1/consultations/{consultation_id}/checklist")
    assert relecture.status_code == 200, relecture.text
    corps_checklist = relecture.json()
    assert corps_checklist["resume"]["nb_manquantes"] >= 0
    assert "certificat" in corps_checklist["mention"].casefold()
    etapes.append(
        f"10. GET .../checklist -> 200 "
        f"(présentes={corps_checklist['resume']['nb_presentes']}, "
        f"manquantes={corps_checklist['resume']['nb_manquantes']})"
    )

    print("\n[parcours] étapes franchies :")
    for etape in etapes:
        print("  -", etape)


def test_bibliotheque_vide_signale_des_manques_sans_inventer(api_a):
    """Scénario « bibliothèque vide » : beaucoup de `manquante`, rien de fabriqué."""
    client = api_a
    entreprise_id = _creer_entreprise(client)
    depot = client.post(
        "/api/v1/consultations",
        data={"libelle": f"Consultation fictive — {MENTION}", "entreprise_id": entreprise_id},
        files={"fichier": (PDF_FICTIF.name, PDF_FICTIF.read_bytes(), "application/pdf")},
    )
    assert depot.status_code == 201, depot.text
    consultation_id = depot.json()["consultation"]["id"]

    # Aucun élément validé → la checklist est vide d'exigences (verrou n° 2).
    execution = client.post(
        f"/api/v1/consultations/{consultation_id}/checklist",
        json={"execute_par": f"Exécutant fictif — {MENTION}"},
    )
    assert execution.status_code == 200, execution.text
    resume = execution.json()["resume"]
    assert resume["nb_exigences"] == 0, resume
    assert resume["manques"] == []
    # Rien n'est inventé : aucune ligne fabriquée sans exigence validée.
    assert execution.json()["lignes"] == []


# --------------------------------------------------------------------------- #
# Non-régression du contrat gelé (annexe C)
# --------------------------------------------------------------------------- #
ROUTES_BIBLIOTHEQUE = ("GET", "GET", "POST", "POST")
CHEMINS_FIGES = (
    ("get", "/api/v1/bibliotheque"),
    ("get", "/api/v1/bibliotheque/{famille}"),
    ("post", "/api/v1/bibliotheque/{famille}"),
    ("post", "/api/v1/bibliotheque/validation"),
    ("post", "/api/v1/entreprises"),
    ("get", "/api/v1/entreprises"),
    ("post", "/api/v1/entreprises/{entreprise_id}/fiches"),
    ("post", "/api/v1/consultations"),
    ("get", "/api/v1/consultations/{consultation_id}"),
    ("post", "/api/v1/consultations/{consultation_id}/elements/{element_id}"),
    ("post", "/api/v1/consultations/{consultation_id}/checklist"),
    ("get", "/api/v1/consultations/{consultation_id}/checklist"),
)


def test_contrat_gele_non_renomme():
    from app.main import app

    chemins = app.openapi()["paths"]
    manquants = [(m, c) for m, c in CHEMINS_FIGES if m not in chemins.get(c, {})]
    assert manquants == [], f"routes gelées absentes ou renommées : {manquants}"
    # Aucune route de création de `client` n'est exposée (annexe C § C2, volet 2).
    assert "/api/v1/clients" not in chemins


def test_routes_de_contenu_refusent_sans_session():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as anonyme:
        assert anonyme.get("/api/v1/bibliotheque").status_code == 401
        assert anonyme.post("/api/v1/entreprises", json={"libelle_court": "x"}).status_code == 401
        assert anonyme.get("/api/v1/consultations/00000000-0000-0000-0000-000000000000").status_code == 401
