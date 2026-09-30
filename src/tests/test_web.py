"""Tests de l'interface web minimale (lot L5) — écrans HTML servis par `/`.

Ce que ces tests démontrent, écran par écran et par exécution réelle :

* les écrans répondent et leurs codes HTTP sont ceux attendus ;
* le **parcours complet** fonctionne : création de l'entreprise et de sa
  première version de fiche, saisie d'un élément, **validation humaine nommée
  et horodatée**, fourniture d'un DCE fictif, analyse **avec sources**,
  validation d'un élément, exécution de la checklist, affichage des manques ;
* « créer une valeur de référence manquante sans quitter le formulaire » (D2)
  fonctionne sur une nomenclature ouverte et **échoue proprement** sur une
  nomenclature fermée ;
* aucune sortie engageante n'omet la mention « brouillon — à relire et à
  signer » ;
* **aucun bouton** « déposer », « envoyer » ou « signer », aucun écran côté
  acheteur, aucun bouton de paiement ;
* un client connecté **ne peut pas** atteindre les données d'un autre.

Les données sont **fictives et signalées** ; aucun secret réel n'apparaît ici
(la clé de session est celle de `conftest.py`, valeur de test).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.services.authentification import ServiceAuthentification
from app.storage.connexion import Connexion, ContexteClient

RACINE_DEPOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

MENTION = "DÉMONSTRATION"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # FICTIF — jamais un secret réel
MENTION_BROUILLON = "brouillon — à relire et à signer"

#: Verbes interdits dans un libellé de bouton (annexe A § A8, plan § 3 lot L5).
VERBES_INTERDITS = ("déposer", "deposer", "envoyer", "signer", "publier", "payer")

#: Raccourci d'écriture pour un POST de formulaire non suivi.
SANS_REDIRECTION = {"follow_redirects": False}


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #
def _identifiant_unique(prefixe: str) -> str:
    return f"{prefixe}-{uuid.uuid4().hex[:12]}@demo.test"


def _client_web(
    connexion: Connexion,
    contexte: ContexteClient,
    config,
    prefixe: str = "web",
) -> TestClient:
    """Crée un compte fictif pour ce client, ouvre une session réelle, rend le client HTTP."""
    identifiant = _identifiant_unique(prefixe)
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(
        contexte, identifiant, f"Sonde Web {MENTION}", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def _compter(connexion_admin, sql: str, params: tuple) -> int:
    return int(connexion_admin.lire(sql, params)[0][0])


def _boutons(html: str) -> list[str]:
    """Libellés de tous les boutons d'une page (texte visible et `value`)."""
    libelles = [
        re.sub(r"<[^>]+>", "", texte).strip()
        for texte in re.findall(r"<button[^>]*>(.*?)</button>", html, re.S)
    ]
    libelles += re.findall(r'<input[^>]*type="submit"[^>]*value="([^"]*)"', html)
    libelles += re.findall(r'<button[^>]*value="([^"]*)"', html)
    return [libelle for libelle in libelles if libelle]


def _aucun_verbe_interdit(html: str) -> list[str]:
    """Boutons dont le libellé emploie un verbe interdit (vide = conforme)."""
    fautifs = []
    for libelle in _boutons(html):
        minuscule = libelle.casefold()
        if any(verbe in minuscule for verbe in VERBES_INTERDITS):
            fautifs.append(libelle)
    return fautifs


# --------------------------------------------------------------------------- #
# 1. Écrans et codes HTTP
# --------------------------------------------------------------------------- #
def test_ecrans_repondent_avec_les_codes_attendus():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/connexion").status_code == 200
        # Sans session : aucun écran de données, redirection vers la connexion.
        for chemin in ("/bibliotheque", "/bibliotheque/assurances", "/consultations"):
            reponse = client.get(chemin, **SANS_REDIRECTION)
            assert reponse.status_code == 303, chemin
            assert reponse.headers["location"].startswith("/connexion?suivant=")
        assert client.get(f"/consultations/{uuid.uuid4()}", **SANS_REDIRECTION).status_code == 303
        assert client.get(f"/consultations/{uuid.uuid4()}/checklist", **SANS_REDIRECTION).status_code == 303
        # La feuille de style est servie, et la racine JSON de l'API est inchangée.
        assert client.get("/static/style.css").status_code == 200
        assert client.get("/").json()["application"] == "ia-consultations-publiques"


def test_connexion_refusee_avec_un_mauvais_mot_de_passe():
    from app.main import app

    with TestClient(app) as client:
        reponse = client.post(
            "/connexion",
            data={"identifiant": "inconnu@demo.test", "mot_de_passe": "faux"},
        )
        assert reponse.status_code == 401
        assert "Identifiant ou mot de passe incorrect" in reponse.text
        # Aucune session n'a été posée.
        assert NOM_COOKIE_SESSION not in client.cookies


def test_famille_inconnue_repond_404(connexion, contexte_a, config):
    client = _client_web(connexion, contexte_a, config)
    assert client.get("/bibliotheque/famille_bidon").status_code == 404


def test_aucun_ecran_acheteur_ni_de_paiement():
    from app.main import app

    with TestClient(app) as client:
        for chemin in ("/acheteur", "/paiement", "/facturation", "/inscription"):
            assert client.get(chemin, **SANS_REDIRECTION).status_code == 404, chemin


# --------------------------------------------------------------------------- #
# 2. Démarrage de zéro : entreprise + première fiche
# --------------------------------------------------------------------------- #
def test_premiere_utilisation_cree_entreprise_et_premiere_fiche(
    connexion, connexion_admin, contexte_a, config
):
    client = _client_web(connexion, contexte_a, config)

    # Aucune entreprise : l'écran de première utilisation s'affiche (plus de cul-de-sac).
    reponse = client.get("/bibliotheque")
    assert reponse.status_code == 200
    assert "Première utilisation" in reponse.text

    reponse = client.post(
        "/entreprises",
        data={"libelle_court": f"Étanchéité Fictive — {MENTION}"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/bibliotheque?ok=entreprise_creee"

    # SQL : une entreprise, une fiche n°1, rattachées au client de la session.
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM entreprise WHERE client_id = %s;",
            (contexte_a.client_id,),
        )
        == 1
    )
    versions = connexion_admin.lire(
        "SELECT numero_version, statut FROM fiche_version WHERE client_id = %s;",
        (contexte_a.client_id,),
    )
    assert len(versions) == 1
    assert versions[0][0] == 1 and versions[0][1] == "vierge"

    # L'écran d'avancement s'affiche, avec les neuf familles.
    reponse = client.get("/bibliotheque")
    assert "Avancement par famille" in reponse.text
    for famille in ("Identité", "Assurances", "Références de chantiers"):
        assert famille in reponse.text

    # Ouvrir une nouvelle version : numérotation croissante, depuis l'écran.
    entreprise_id = str(
        connexion_admin.lire(
            "SELECT id FROM entreprise WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    reponse = client.post(
        f"/entreprises/{entreprise_id}/fiches", data={}, **SANS_REDIRECTION
    )
    assert reponse.status_code == 303
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM fiche_version WHERE client_id = %s;",
            (contexte_a.client_id,),
        )
        == 2
    )


def test_ouvrir_fiche_sur_entreprise_d_un_autre_client_repete_404(
    connexion, connexion_admin, contexte_a, contexte_b, config
):
    """Aucune écriture sur l'entreprise d'un autre : 404, jamais 403."""
    client_a = _client_web(connexion, contexte_a, config, "web-a")
    client_b = _client_web(connexion, contexte_b, config, "web-b")
    client_a.post("/entreprises", data={"libelle_court": f"Fictive A — {MENTION}"})
    entreprise_a = str(
        connexion_admin.lire(
            "SELECT id FROM entreprise WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    avant = _compter(
        connexion_admin,
        "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
        (entreprise_a,),
    )
    reponse = client_b.post(
        f"/entreprises/{entreprise_a}/fiches", data={}, **SANS_REDIRECTION
    )
    assert reponse.status_code == 404
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
            (entreprise_a,),
        )
        == avant
    )


# --------------------------------------------------------------------------- #
# 3. Saisie d'un élément, et valeur de référence manquante (D2)
# --------------------------------------------------------------------------- #
def test_saisie_element_et_valeur_de_reference_creee_dans_le_formulaire(
    connexion, connexion_admin, contexte_a, config
):
    client = _client_web(connexion, contexte_a, config, "web-ref")
    client.post("/entreprises", data={"libelle_court": f"Fictive réf. — {MENTION}"})

    reponse = client.get("/bibliotheque/references_chantiers")
    assert reponse.status_code == 200
    # Nomenclature ouverte annoncée comme telle, et champ de création présent.
    assert "jeu <strong>non chargé</strong>" in reponse.text
    assert 'name="champ_nature_travaux_code__nouvelle"' in reponse.text

    # La valeur de référence n'existe dans aucun jeu chargé : elle est créée ici,
    # sans quitter le formulaire, et reste portée par l'élément.
    reponse = client.post(
        "/bibliotheque/references_chantiers",
        data={
            "entite": "reference_chantier",
            "origine": "saisie_entreprise",
            "confiance": "declare_non_verifie",
            "champ_intitule_operation": f"Réfection terrasse fictive — {MENTION}",
            "champ_maitre_ouvrage": "Commune fictive de Démonstration",
            "champ_nature_travaux_code__nouvelle": "etancheite-toiture-valeur-inventee-pour-le-test",
            "champ_date_debut": "2024-03-01",
        },
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert "ok=element_enregistre" in reponse.headers["location"]

    reponse = client.get("/bibliotheque/references_chantiers")
    assert "Réfection terrasse fictive" in reponse.text
    assert "etancheite-toiture-valeur-inventee-pour-le-test" in reponse.text
    # Valeur sans source : affichée comme non vérifiée, jamais comme un fait.
    assert "non vérifiée" in reponse.text

    # La valeur créée reste sur l'élément : aucune ligne n'est écrite dans la
    # nomenclature globale (I5) — c'est une décision signalée de ce lot.
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM valeur_reference WHERE code = %s;",
            ("etancheite-toiture-valeur-inventee-pour-le-test",),
        )
        == 0
    )


def test_valeur_de_reference_refusee_sur_nomenclature_fermee(
    connexion, contexte_a, config
):
    """Un jeu **chargé** est une nomenclature fermée : une valeur hors jeu est refusée."""
    client = _client_web(connexion, contexte_a, config, "web-ferme")
    client.post("/entreprises", data={"libelle_court": f"Fictive fermée — {MENTION}"})

    reponse = client.get("/bibliotheque/identite")
    assert "jeu <strong>chargé</strong>" in reponse.text  # rh.statut_mandat est chargé

    reponse = client.post(
        "/bibliotheque/identite",
        data={
            "entite": "representant_legal",
            "origine": "saisie_entreprise",
            "champ_nom": "Nom Fictif",
            "champ_prenom": "Prénom Fictif",
            "champ_fonction": "Gérant (fictif)",
            "champ_statut": "statut-impossible-hors-jeu",
        },
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert "erreur=" in reponse.headers["location"]
    assert "code+inconnu" in reponse.headers["location"] or "inconnu" in reponse.headers["location"]


def test_saisie_sans_origine_est_refusee(connexion, contexte_a, config):
    """Aucune valeur sans origine (§ 7.5 règle 4) : le refus est explicite."""
    client = _client_web(connexion, contexte_a, config, "web-origine")
    client.post("/entreprises", data={"libelle_court": f"Fictive origine — {MENTION}"})
    reponse = client.post(
        "/bibliotheque/assurances",
        data={
            "entite": "assurance",
            "origine": "",
            "champ_type_assurance": "decennale (fictif)",
            "champ_assureur": "Assureur fictif",
            "champ_date_debut": "2024-01-01",
            "champ_date_echeance": "2030-01-01",
            "champ_piece": "attestation_fictive.pdf",
        },
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert "origine" in reponse.headers["location"]


# --------------------------------------------------------------------------- #
# 4. Verrou humain n° 1 : la validation de la bibliothèque
# --------------------------------------------------------------------------- #
def test_validation_bibliotheque_non_court_circuitable(
    connexion, connexion_admin, contexte_a, config
):
    client = _client_web(connexion, contexte_a, config, "web-val")
    client.post("/entreprises", data={"libelle_court": f"Fictive validation — {MENTION}"})
    client.post(
        "/bibliotheque/references_chantiers",
        data={
            "entite": "reference_chantier",
            "origine": "saisie_entreprise",
            "champ_intitule_operation": f"Chantier fictif à valider — {MENTION}",
            "champ_maitre_ouvrage": "Commune fictive",
        },
    )
    fiche = str(
        connexion_admin.lire(
            "SELECT id FROM fiche_version WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )

    # (a) Nom du relecteur manquant : la requête elle-même est refusée (422).
    reponse = client.post(
        "/bibliotheque/validation",
        data={"fiche_version_id": fiche, "attestation_cochee": "1"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 422

    # (b) Attestation non cochée : refus explicite, aucune validation écrite.
    reponse = client.post(
        "/bibliotheque/validation",
        data={"fiche_version_id": fiche, "relecteur_nom": "Sonde Fictive"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert "erreur=" in reponse.headers["location"]
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM validation_relecture WHERE fiche_version_id = %s;",
            (fiche,),
        )
        == 0
    )

    # (c) Nom + attestation : validation enregistrée, horodatée par la base.
    reponse = client.post(
        "/bibliotheque/validation",
        data={
            "fiche_version_id": fiche,
            "relecteur_nom": f"Sonde Fictive — {MENTION}",
            "attestation_cochee": "1",
            "cible_type": "fiche",
        },
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert reponse.headers["location"].endswith("ok=validation_enregistree")
    lignes = connexion_admin.lire(
        "SELECT relecteur_nom, attestation_cochee, date_validation, statut "
        "FROM validation_relecture WHERE fiche_version_id = %s;",
        (fiche,),
    )
    assert len(lignes) == 1
    assert lignes[0][0] == f"Sonde Fictive — {MENTION}"
    assert lignes[0][1] in (1, True)
    assert lignes[0][2] is not None
    assert lignes[0][3] == "validee"

    # L'état « relue et validée » est visible à l'écran.
    assert "Relue et validée" in client.get("/bibliotheque").text

    # (d) Une écriture ultérieure révoque la validation : retour en relecture.
    client.post(
        "/bibliotheque/references_chantiers",
        data={
            "entite": "reference_chantier",
            "origine": "saisie_entreprise",
            "champ_intitule_operation": f"Chantier fictif modifié — {MENTION}",
            "champ_maitre_ouvrage": "Commune fictive",
        },
    )
    statuts = connexion_admin.lire(
        "SELECT statut FROM validation_relecture WHERE fiche_version_id = %s;", (fiche,)
    )
    assert statuts and statuts[0][0] == "revoquee"


# --------------------------------------------------------------------------- #
# 5. Parcours complet de bout en bout (le critère de fin de phase 3)
# --------------------------------------------------------------------------- #
def test_parcours_complet_web_de_bout_en_bout(connexion, connexion_admin, contexte_a, config):
    client = _client_web(connexion, contexte_a, config, "web-parcours")

    # 1. Premier écran : première utilisation, entreprise et fiche créées ici.
    assert "Première utilisation" in client.get("/bibliotheque").text
    client.post("/entreprises", data={"libelle_court": f"Étanchéité Fictive — {MENTION}"})
    assert "Avancement par famille" in client.get("/bibliotheque").text

    # 2. Saisie d'un élément de bibliothèque.
    client.post(
        "/bibliotheque/references_chantiers",
        data={
            "entite": "reference_chantier",
            "origine": "saisie_entreprise",
            "confiance": "declare_non_verifie",
            "champ_intitule_operation": f"Toiture bâtiment communal fictif — {MENTION}",
            "champ_maitre_ouvrage": "Commune fictive de Démonstration",
            "champ_nature_travaux_code": "etancheite-toiture",
            "champ_date_debut": "2023-05-01",
            "champ_date_fin": "2023-09-30",
        },
    )
    assert "Toiture bâtiment communal fictif" in client.get(
        "/bibliotheque/references_chantiers"
    ).text

    # 3. Validation humaine nommée et horodatée.
    fiche = str(
        connexion_admin.lire(
            "SELECT id FROM fiche_version WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    client.post(
        "/bibliotheque/validation",
        data={
            "fiche_version_id": fiche,
            "relecteur_nom": f"Anthony Fictif — {MENTION}",
            "attestation_cochee": "1",
        },
    )
    assert "Relue et validée" in client.get("/bibliotheque").text

    # 4. Fourniture d'un DCE fictif (document de démonstration du dépôt).
    reponse = client.get("/consultations")
    assert reponse.status_code == 200
    assert "dce_fictif.pdf" in reponse.text  # fixture de démonstration indiquée à l'écran
    entreprise_id = str(
        connexion_admin.lire(
            "SELECT id FROM entreprise WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    with (FIXTURES / "dce_fictif.pdf").open("rb") as fichier:
        reponse = client.post(
            "/consultations",
            data={
                "libelle": f"DCE fictif — {MENTION}",
                "entreprise_id": entreprise_id,
                "reference_consultation": "FICTIF-2026-001",
                "maitre_ouvrage_declare": "Commune fictive de Démonstration",
            },
            files={"fichier": ("dce_fictif.pdf", fichier, "application/pdf")},
            **SANS_REDIRECTION,
        )
    assert reponse.status_code == 303, reponse.text
    url_consultation = reponse.headers["location"]
    consultation_id = url_consultation.split("/consultations/")[1].split("?")[0]

    # 5. Analyse affichée, chaque élément portant sa source (fichier + emplacement).
    reponse = client.get(f"/consultations/{consultation_id}")
    assert reponse.status_code == 200
    assert "source" in reponse.text.casefold()
    assert "emplacement" in reponse.text
    assert f"DCE fictif — {MENTION}" in reponse.text
    assert MENTION_BROUILLON in reponse.text  # mention engageante (exigence 3)
    identifiants_elements = re.findall(
        rf"/consultations/{consultation_id}/elements/([0-9a-f-]+)", reponse.text
    )
    assert len(identifiants_elements) >= 5  # pièces, critères, date limite
    assert "proposé" in reponse.text and "non vérifié" in reponse.text

    # 6. Validation d'un élément : nommé (le service l'exige), horodaté.
    element_id = identifiants_elements[0]
    reponse = client.post(
        f"/consultations/{consultation_id}/elements/{element_id}",
        data={"action": "valider", "verificateur_nom": f"Anthony Fictif — {MENTION}"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    lignes = connexion_admin.lire(
        "SELECT statut_verification, verificateur_nom, date_verification "
        "FROM extraction_element WHERE id = %s;",
        (element_id,),
    )
    assert lignes and lignes[0][0] == "valide"
    assert lignes[0][1] == f"Anthony Fictif — {MENTION}" and lignes[0][2] is not None

    # Un élément sans nom n'est pas validé : le refus est explicite.
    reponse = client.post(
        f"/consultations/{consultation_id}/elements/{element_id}",
        data={"action": "valider"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303 and "erreur=" in reponse.headers["location"]

    # 7. Exécution de la checklist (action nommée).
    reponse = client.post(
        f"/consultations/{consultation_id}/checklist",
        data={"execute_par": f"Anthony Fictif — {MENTION}"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 303
    assert reponse.headers["location"].endswith("ok=checklist_executee")

    # 8. Affichage : statuts, résumé des manques, mention brouillon.
    reponse = client.get(f"/consultations/{consultation_id}/checklist")
    assert reponse.status_code == 200
    assert "Résumé des manques" in reponse.text
    assert "manquante" in reponse.text
    assert MENTION_BROUILLON in reponse.text
    assert "pas un certificat" in reponse.text
    # Le vocabulaire interdit n'apparaît pas : jamais « conforme » comme garantie.
    # (l'apostrophe est échappée en HTML : on cherche un fragment sans apostrophe)
    assert "aucune conformit" in reponse.text.casefold()
    assert "garantie" in reponse.text.casefold()

    # La checklist ne contient que l'exigence validée par un humain (verrou n° 2).
    execution = connexion_admin.lire(
        "SELECT nb_exigences, nb_manquantes, extraction_partielle FROM checklist_execution "
        "WHERE consultation_id = %s;",
        (consultation_id,),
    )
    assert execution and execution[0][0] == 1
    assert execution[0][1] == 1  # la bibliothèque ne contient pas cette pièce
    assert execution[0][2] in (1, True)  # extraction partielle signalée
    assert "Extraction partielle" in reponse.text


# --------------------------------------------------------------------------- #
# 6. Isolation : un client ne voit jamais les données d'un autre
# --------------------------------------------------------------------------- #
def test_un_client_ne_peut_pas_atteindre_les_donnees_d_un_autre(
    connexion, connexion_admin, contexte_a, contexte_b, config
):
    client_a = _client_web(connexion, contexte_a, config, "iso-a")
    client_b = _client_web(connexion, contexte_b, config, "iso-b")

    client_a.post("/entreprises", data={"libelle_court": f"Iso A fictive — {MENTION}"})
    client_a.post(
        "/bibliotheque/references_chantiers",
        data={
            "entite": "reference_chantier",
            "origine": "saisie_entreprise",
            "champ_intitule_operation": f"Chantier secret de A — {MENTION}",
            "champ_maitre_ouvrage": "Commune fictive A",
        },
    )
    entreprise_a = str(
        connexion_admin.lire(
            "SELECT id FROM entreprise WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    with (FIXTURES / "dce_fictif.pdf").open("rb") as fichier:
        reponse = client_a.post(
            "/consultations",
            data={"libelle": f"DCE de A — {MENTION}", "entreprise_id": entreprise_a},
            files={"fichier": ("dce_fictif.pdf", fichier, "application/pdf")},
            **SANS_REDIRECTION,
        )
    consultation_a = reponse.headers["location"].split("/consultations/")[1].split("?")[0]
    element_a = str(
        connexion_admin.lire(
            "SELECT id FROM extraction_element WHERE consultation_id = %s LIMIT 1;",
            (consultation_a,),
        )[0][0]
    )

    # B, connecté, n'atteint ni la consultation, ni sa checklist, ni son élément.
    assert client_b.get(f"/consultations/{consultation_a}").status_code == 404
    assert client_b.get(f"/consultations/{consultation_a}/checklist").status_code == 404
    reponse = client_b.post(
        f"/consultations/{consultation_a}/elements/{element_a}",
        data={"action": "valider", "verificateur_nom": "Sonde B"},
        **SANS_REDIRECTION,
    )
    assert reponse.status_code == 404
    # Aucune donnée de A n'est affichée dans la bibliothèque de B.
    reponse = client_b.get("/bibliotheque")
    assert reponse.status_code == 200
    assert "Chantier secret de A" not in reponse.text
    assert "Iso A fictive" not in reponse.text

    # La base confirme : rien n'a été écrit dans le client de B.
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM consultation WHERE client_id = %s;",
            (contexte_b.client_id,),
        )
        == 0
    )
    assert (
        _compter(
            connexion_admin,
            "SELECT count(*) FROM extraction_element WHERE id = %s AND statut_verification = 'valide';",
            (element_a,),
        )
        == 0
    )


# --------------------------------------------------------------------------- #
# 7. Aucun bouton engageant, mention brouillon partout où elle est due
# --------------------------------------------------------------------------- #
def test_aucun_bouton_de_depot_d_envoi_ou_de_signature(connexion, connexion_admin, contexte_a, config):
    client = _client_web(connexion, contexte_a, config, "web-boutons")
    client.post("/entreprises", data={"libelle_court": f"Fictive boutons — {MENTION}"})
    entreprise_id = str(
        connexion_admin.lire(
            "SELECT id FROM entreprise WHERE client_id = %s;", (contexte_a.client_id,)
        )[0][0]
    )
    with (FIXTURES / "dce_fictif.pdf").open("rb") as fichier:
        reponse = client.post(
            "/consultations",
            data={"libelle": f"DCE boutons — {MENTION}", "entreprise_id": entreprise_id},
            files={"fichier": ("dce_fictif.pdf", fichier, "application/pdf")},
            **SANS_REDIRECTION,
        )
    consultation_id = reponse.headers["location"].split("/consultations/")[1].split("?")[0]
    client.post(
        f"/consultations/{consultation_id}/checklist",
        data={"execute_par": f"Sonde Fictive — {MENTION}"},
    )

    pages = {
        "/connexion": client.get("/connexion").text,
        "/bibliotheque": client.get("/bibliotheque").text,
        "/bibliotheque/assurances": client.get("/bibliotheque/assurances").text,
        "/consultations": client.get("/consultations").text,
        f"/consultations/{consultation_id}": client.get(f"/consultations/{consultation_id}").text,
        f"/consultations/{consultation_id}/checklist": client.get(
            f"/consultations/{consultation_id}/checklist"
        ).text,
    }
    for chemin, html in pages.items():
        fautifs = _aucun_verbe_interdit(html)
        assert not fautifs, f"{chemin} : boutons interdits {fautifs}"
        assert _boutons(html), f"{chemin} : aucun bouton trouvé (test aveugle)"

    # La mention « brouillon — à relire et à signer » est portée par toute sortie
    # de nature à engager l'entreprise (analyse et checklist ici).
    assert MENTION_BROUILLON in pages[f"/consultations/{consultation_id}"]
    assert MENTION_BROUILLON in pages[f"/consultations/{consultation_id}/checklist"]


def test_les_gabarits_ne_portent_aucun_bouton_engageant():
    """Contrôle direct des gabarits : aucun libellé de bouton interdit, même non rendu."""
    gabarits = sorted((Path(__file__).resolve().parents[1] / "app" / "web" / "templates").glob("*.html"))
    assert gabarits, "aucun gabarit trouvé : le test ne prouverait rien"
    for gabarit in gabarits:
        fautifs = _aucun_verbe_interdit(gabarit.read_text(encoding="utf-8"))
        assert not fautifs, f"{gabarit.name} : boutons interdits {fautifs}"
