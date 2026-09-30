"""Parcours de **démarrage de zéro**, indépendamment de L2bis (exigence du lot L8).

Chemin que l'interface emprunte (annexe C § C2) :

    script d'exploitant (client + compte fictifs) → connexion (route gelée) →
    POST /api/v1/entreprises → GET /api/v1/bibliotheque (qui ne renvoie plus le
    404 « Provisionnez une entreprise… »).

Contrôlé **par mes propres moyens** : le script est réellement exécuté (saisie clavier
simulée), puis l'API est exercée avec le compte ainsi créé. Données **FICTIVES**
(« DÉMONSTRATION »).
"""

from __future__ import annotations

import getpass
import importlib.util
import io
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from fastapi.testclient import TestClient

from .conftest import MENTION, MOT_DE_PASSE_FICTIF

RACINE = Path(__file__).resolve().parents[3]
SCRIPT = RACINE / "scripts" / "provisionnement.py"


def _charger_script():
    spec = importlib.util.spec_from_file_location("script_provisionnement_parcours", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demarrage_de_zero_par_le_script_puis_l_api(connexion_admin, monkeypatch):
    module = _charger_script()
    identifiant = f"demarrage-{uuid.uuid4().hex[:10]}@demo.test"
    libelle = f"Client démarrage fictif — {MENTION} {uuid.uuid4().hex[:6]}"

    # Saisie clavier masquée simulée (deux saisies concordantes) : aucun secret en argument.
    saisies = iter([MOT_DE_PASSE_FICTIF, MOT_DE_PASSE_FICTIF])
    monkeypatch.setattr(getpass, "getpass", lambda *a, **k: next(saisies))

    sortie = io.StringIO()
    erreurs = io.StringIO()
    with redirect_stdout(sortie), redirect_stderr(erreurs):
        code = module.main(
            [
                "--libelle-client",
                libelle,
                "--identifiant",
                identifiant,
                "--nom-affichage",
                "Compte fictif — DÉMONSTRATION",
            ]
        )
    assert code == 0, erreurs.getvalue()
    assert "OK" in sortie.getvalue()
    assert MOT_DE_PASSE_FICTIF not in sortie.getvalue(), "le mot de passe fuit dans la sortie"

    # Le client et le compte existent en base.
    lignes = connexion_admin.lire("SELECT id FROM client WHERE libelle = %s;", (libelle,))
    assert len(lignes) == 1
    client_id = str(lignes[0][0])

    from app.main import app

    with TestClient(app) as api:
        # 1. Connexion par la route gelée.
        connexion_reponse = api.post(
            "/api/v1/connexion",
            json={"identifiant": identifiant, "mot_de_passe": MOT_DE_PASSE_FICTIF},
        )
        assert connexion_reponse.status_code == 200, connexion_reponse.text
        assert connexion_reponse.json()["client_id"] == client_id

        # 2. La bibliothèque renvoie le 404 explicite tant qu'aucune fiche n'existe.
        avant = api.get("/api/v1/bibliotheque")
        assert avant.status_code == 404
        assert "Provisionnez une entreprise" in avant.json()["detail"]

        # 3. Création de l'entreprise (et de sa première fiche) : 201.
        creation = api.post(
            "/api/v1/entreprises", json={"libelle_court": f"Entreprise fictive — {MENTION}"}
        )
        assert creation.status_code == 201, creation.text

        # 4. Le 404 a disparu : la bibliothèque répond 200 — le cul-de-sac est ouvert.
        apres = api.get("/api/v1/bibliotheque")
        assert apres.status_code == 200, apres.text
        assert apres.json()["statut"] == "vierge"
