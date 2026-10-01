"""Tests du lot L6 (phase 4) — export téléchargeable du mémoire technique.

Aucune donnée réelle : clients, DCE, bibliothèque et documents sont **fictifs et
signalés** (décision D10). Aucun appel réseau : `conftest.py` impose le fournisseur
factice et interdit toute sortie (correctif C2).

Exigences vérifiables, démontrées **par exécution** :

1. `GET /consultations/{id}/memoire/export?format=md|docx` télécharge le mémoire **du
   client de la session** ;
2. un mémoire d'un **autre client** répond **404** — jamais `403`, jamais son contenu ;
3. **sans validation nommée et horodatée**, l'export est refusé par un **message qui dit
   quoi faire**, pas par une erreur technique ;
4. le **Markdown est le format canonique** et se produit **sans dépendance nouvelle** ;
5. le **DOCX** passe par `python-docx`, ou répond « non disponible » avec sa raison ;
6. le fichier porte le **contenu validé** et l'empreinte SHA-256 de
   `memoire_validation` **correspond** ; un contenu modifié depuis la validation est
   **refusé** ;
7. **aucun prix, aucun chiffre inventé, aucune conformité garantie** ; **aucun bouton**
   de dépôt, d'envoi ou de signature.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.services import export_memoire, memoire_technique
from app.services.export_memoire import (
    FORMAT_CANONIQUE,
    ContenuDivergent,
    FormatInconnu,
    FormatNonDisponible,
    ValidationManquante,
)

from test_memoire_technique import (  # helpers du lot L2 (mêmes fixtures fictives)
    MOT_DE_PASSE_FICTIF,
    RELECTEUR_FICTIF,
    VALIDATEUR_FICTIF,
    _client_api,
    _preparer_dce_et_bibliotheque,
)

#: Verbes interdits dans un libellé de bouton (aucun envoi, aucun dépôt, aucune signature).
VERBES_INTERDITS = ("déposer", "deposer", "envoyer", "signer", "publier", "payer")

SANS_REDIRECTION = {"follow_redirects": False}


# --------------------------------------------------------------------------- #
# Préparation : un mémoire réellement validé par un humain nommé
# --------------------------------------------------------------------------- #
def _preparer_memoire_brouillon(connexion, contexte, config):
    """Mémoire généré, encore **non validé** : le cas du refus pédagogique."""
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte, config
    )
    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    return resultat, consultation_id


def _preparer_memoire_valide(connexion, contexte, config):
    """Mémoire généré, relu section par section, puis validé (nom + fonction)."""
    resultat, consultation_id = _preparer_memoire_brouillon(connexion, contexte, config)
    sections = resultat["sections"]
    assert sections, "la bibliothèque remplie doit produire au moins une section"
    for section in sections:
        memoire_technique.changer_statut_section(
            connexion,
            contexte,
            section_id=str(section["id"]),
            statut="relue",
            par=RELECTEUR_FICTIF,
        )
    validation = memoire_technique.valider_dossier(
        connexion,
        contexte,
        dossier_id=str(resultat["dossier"]["id"]),
        nom_validateur=VALIDATEUR_FICTIF,
        fonction_validateur="Gérant (fictif)",
    )
    return validation, resultat, consultation_id


def _ligne_validation(connexion, contexte, dossier_id: str):
    return connexion.executer_une(
        contexte,
        "SELECT * FROM memoire_validation WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s ORDER BY horodatage DESC, id LIMIT 1;",
        {"dossier": dossier_id},
    )


def _boutons(html: str) -> list[str]:
    """Libellés de tous les boutons d'une page (texte visible et `value`)."""
    libelles = [
        re.sub(r"<[^>]+>", "", texte).strip()
        for texte in re.findall(r"<button[^>]*>(.*?)</button>", html, re.S)
    ]
    libelles += re.findall(r'<input[^>]*type="submit"[^>]*value="([^"]*)"', html)
    return [libelle for libelle in libelles if libelle]


def _aucun_verbe_interdit(contenu: str) -> list[str]:
    minuscule = contenu.casefold()
    return [verbe for verbe in VERBES_INTERDITS if verbe in minuscule]


# --------------------------------------------------------------------------- #
# 1. Le format canonique est produit sans dépendance nouvelle
# --------------------------------------------------------------------------- #
def test_markdown_est_le_format_canonique_sans_dependance():
    """Le `.md` est assemblé à partir du seul contenu, sans importer `docx`."""
    assert FORMAT_CANONIQUE == "md"
    memoire = {
        "dossier": {"titre": "Mémoire fictif"},
        "avertissement": "Brouillon fictif, rien n'est garanti.",
        "sections": [
            {
                "ordre": 0,
                "titre": "Valeur technique",
                "critere_libelle": "Valeur technique",
                "critere_poids": 40,
                "contenu": "Critère « Valeur technique » — pondération 40 %.\n- Chantier fictif.",
                "sources": [
                    {
                        "libelle_source": "Réfection étanchéité (fictif)",
                        "emplacement_source": "bibliothèque — Références / reference_chantier",
                    }
                ],
            },
            {
                "ordre": 1,
                "titre": "Moyens humains",
                "critere_libelle": "Moyens humains",
                "critere_poids": 25,
                "contenu": "Critère « Moyens humains » — pondération 25 %.\n- Effectif fictif.",
                "sources": [
                    {
                        "libelle_source": "Étancheur",
                        "emplacement_source": "bibliothèque — Moyens humains / effectif_metier",
                    }
                ],
            },
        ],
        "manques": [
            {
                "critere_libelle": "Planning",
                "critere_poids": None,
                "constat": "Aucune référence correspondante dans votre bibliothèque.",
                "action_attendue": "Ajouter un chantier comparable.",
            }
        ],
        "validations": [
            {
                "nom_validateur": VALIDATEUR_FICTIF,
                "fonction_validateur": "Gérant (fictif)",
                "horodatage": "2026-09-30T10:00:00+04:00",
                "empreinte_contenu": "a" * 64,
            }
        ],
    }
    texte = export_memoire.rendre_markdown(memoire)

    # Titres hiérarchisés, sections dans l'ordre reçu (pondération décroissante).
    assert texte.startswith("# Mémoire fictif")
    positions = [texte.index("## 1. Valeur technique"), texte.index("## 2. Moyens humains")]
    assert positions == sorted(positions)
    # Chaque argument porte sa source citée.
    assert "Sources citées :" in texte
    assert "bibliothèque — Références / reference_chantier" in texte
    # Les manques sont listés avec leur action à mener.
    assert "## Manques à traiter" in texte
    assert "Action à mener : Ajouter un chantier comparable." in texte
    # La validation humaine et l'empreinte apparaissent.
    assert VALIDATEUR_FICTIF in texte
    assert "a" * 64 in texte
    # Ni conformité promise, ni bouton de dépôt / envoi / signature.
    assert "aucune conformité n'est garantie" in texte
    assert _aucun_verbe_interdit(texte) == []


# --------------------------------------------------------------------------- #
# 2. Sans validation : refus explicite, pédagogique, sans fichier
# --------------------------------------------------------------------------- #
def test_export_refuse_sans_validation_nommee(connexion, contexte_a, config, tmp_path):
    resultat, consultation_id = _preparer_memoire_brouillon(connexion, contexte_a, config)
    assert resultat["dossier"]["statut"] == "brouillon"

    client = _client_api(connexion, contexte_a, config, identifiant="export1@fictif.test")
    try:
        for fmt in ("md", "docx"):
            reponse = client.get(
                f"/consultations/{consultation_id}/memoire/export?format={fmt}"
            )
            assert reponse.status_code == 409, reponse.text
            assert "content-disposition" not in {c.casefold() for c in reponse.headers}
            corps = reponse.text
            # Un message qui dit quoi faire — pas une erreur technique.
            assert "relu et validé par une personne nommée" in corps
            assert "validez" in corps.casefold()
            assert "Traceback" not in corps
            # Aucun bouton de dépôt, d'envoi ou de signature.
            assert _aucun_verbe_interdit(corps) == []
            assert _boutons(corps) == []
    finally:
        client.__exit__(None, None, None)


def test_preparer_export_leve_validation_manquante(connexion, contexte_a, config):
    """Au niveau service : refus explicite, jamais un fichier partiel."""
    _, consultation_id = _preparer_memoire_brouillon(connexion, contexte_a, config)
    with pytest.raises(ValidationManquante) as erreur:
        export_memoire.preparer_export(
            connexion, contexte_a, consultation_id=consultation_id, format="md"
        )
    assert "nommée" in str(erreur.value)


# --------------------------------------------------------------------------- #
# 3. Export Markdown après validation : le fichier porte le contenu validé
# --------------------------------------------------------------------------- #
def test_export_markdown_apres_validation(connexion, contexte_a, config, tmp_path):
    validation, resultat, consultation_id = _preparer_memoire_valide(
        connexion, contexte_a, config
    )
    dossier_id = str(resultat["dossier"]["id"])
    ligne = _ligne_validation(connexion, contexte_a, dossier_id)
    assert ligne is not None
    assert ligne["nom_validateur"] == VALIDATEUR_FICTIF
    assert len(str(ligne["empreinte_contenu"])) == 64

    client = _client_api(connexion, contexte_a, config, identifiant="export2@fictif.test")
    try:
        reponse = client.get(
            f"/consultations/{consultation_id}/memoire/export?format=md"
        )
        assert reponse.status_code == 200, reponse.text
        entetes = {c.casefold(): v for c, v in reponse.headers.items()}
        assert entetes["content-type"].startswith("text/markdown")
        assert entetes["content-disposition"].startswith("attachment;")
        assert ".md" in entetes["content-disposition"]
        # L'empreinte servie est **celle enregistrée à la validation**.
        assert entetes["x-empreinte-contenu"] == ligne["empreinte_contenu"]

        texte = reponse.text
        assert dossier_id not in texte, "un identifiant interne ne doit pas sortir"
        assert "## 1. " in texte
        assert "Sources citées :" in texte
        assert "## Manques à traiter" in texte
        assert "Action à mener :" in texte
        assert str(ligne["empreinte_contenu"]) in texte
        assert VALIDATEUR_FICTIF in texte
        # Le fichier écrit sur disque est relu (preuve d'exécution réelle).
        fichier = tmp_path / "export.md"
        fichier.write_bytes(reponse.content)
        relu = fichier.read_text(encoding="utf-8")
        assert relu == texte and relu.strip()
        # Aucun prix fixé, aucune conformité garantie, aucun bouton d'action.
        assert "aucune conformité n'est garantie" in relu
        assert _aucun_verbe_interdit(relu) == []
    finally:
        client.__exit__(None, None, None)


def test_export_refuse_si_le_contenu_a_change_depuis_la_validation(
    connexion, contexte_a, config
):
    """Une modification après validation rend l'export refusé (empreinte divergente)."""
    _, resultat, consultation_id = _preparer_memoire_valide(connexion, contexte_a, config)
    section_id = str(resultat["sections"][0]["id"])

    connexion.executer_une(
        contexte_a,
        "UPDATE memoire_section SET contenu = contenu || ' (modifié après validation)' "
        "WHERE client_id = %(client_id)s AND id = %(id)s RETURNING id;",
        {"id": section_id},
    )
    connexion.valider()

    with pytest.raises(ContenuDivergent) as erreur:
        export_memoire.preparer_export(
            connexion, contexte_a, consultation_id=consultation_id, format="md"
        )
    assert "changé depuis sa validation" in str(erreur.value)

    client = _client_api(connexion, contexte_a, config, identifiant="export3@fictif.test")
    try:
        reponse = client.get(f"/consultations/{consultation_id}/memoire/export?format=md")
        assert reponse.status_code == 409, reponse.text
        assert "Relisez les sections modifiées" in reponse.text
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 4. Format confort : DOCX réellement ouvert, ou dégradation propre
# --------------------------------------------------------------------------- #
def test_export_docx_ou_degradation_propre(connexion, contexte_a, config, tmp_path):
    _, resultat, consultation_id = _preparer_memoire_valide(connexion, contexte_a, config)
    client = _client_api(connexion, contexte_a, config, identifiant="export4@fictif.test")
    disponible, raison = export_memoire.docx_disponible()
    try:
        reponse = client.get(f"/consultations/{consultation_id}/memoire/export?format=docx")
        if not disponible:
            # Le lot n'est pas bloqué : refus lisible, Markdown toujours disponible.
            assert reponse.status_code == 409, reponse.text
            assert "n'est pas disponible" in reponse.text
            assert raison in reponse.text
            markdown = client.get(
                f"/consultations/{consultation_id}/memoire/export?format=md"
            )
            assert markdown.status_code == 200
            return
        assert reponse.status_code == 200, reponse.text
        entetes = {c.casefold(): v for c, v in reponse.headers.items()}
        assert entetes["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert reponse.content[:2] == b"PK", "un .docx est une archive ZIP"
        fichier = tmp_path / "export.docx"
        fichier.write_bytes(reponse.content)
        # On **ouvre réellement** le fichier produit et on lit son texte.
        from docx import Document

        document = Document(str(fichier))
        paragraphes = [p.text for p in document.paragraphs]
        texte = "\n".join(paragraphes)
        assert paragraphes[0].startswith("Mémoire technique")
        assert "Valeur technique" in texte
        assert "Sources citées :" in texte
        assert "Manques à traiter" in texte
        assert "Action à mener :" in texte
        assert VALIDATEUR_FICTIF in texte
        assert "aucune conformité n'est garantie" in texte
        # Le titre de la première section réelle est présent.
        titre_section = str(resultat["sections"][0]["titre"])
        assert titre_section in texte, titre_section
    finally:
        client.__exit__(None, None, None)


def test_rendre_docx_leve_format_non_disponible_si_absent(monkeypatch):
    monkeypatch.setattr(
        export_memoire, "docx_disponible", lambda: (False, "bibliothèque absente (test)")
    )
    with pytest.raises(FormatNonDisponible) as erreur:
        export_memoire.rendre_docx({"dossier": {"titre": "T"}})
    assert "n'est pas disponible" in str(erreur.value)
    assert "Markdown" in str(erreur.value)


# --------------------------------------------------------------------------- #
# 5. Format inconnu : refus explicite listant les formats admis
# --------------------------------------------------------------------------- #
def test_export_format_inconnu(connexion, contexte_a, config):
    _, resultat, consultation_id = _preparer_memoire_valide(connexion, contexte_a, config)
    with pytest.raises(FormatInconnu) as erreur:
        export_memoire.preparer_export(
            connexion, contexte_a, consultation_id=consultation_id, format="pdf"
        )
    assert "md" in str(erreur.value) and "docx" in str(erreur.value)

    client = _client_api(connexion, contexte_a, config, identifiant="export5@fictif.test")
    try:
        reponse = client.get(
            f"/consultations/{consultation_id}/memoire/export?format=pdf"
        )
        assert reponse.status_code == 400, reponse.text
        assert "Formats admis" in reponse.text
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 6. Isolation : le mémoire d'un autre client est introuvable (404, jamais 403)
# --------------------------------------------------------------------------- #
def test_export_du_memoire_d_un_autre_client_renvoie_404(
    connexion, contexte_a, contexte_b, config
):
    _, resultat, consultation_id = _preparer_memoire_valide(connexion, contexte_a, config)
    titre_premier = str(resultat["sections"][0]["titre"])

    client_b = _client_api(connexion, contexte_b, config, identifiant="export-b@fictif.test")
    try:
        for fmt in ("md", "docx"):
            reponse = client_b.get(
                f"/consultations/{consultation_id}/memoire/export?format={fmt}"
            )
            assert reponse.status_code == 404, reponse.text
            assert reponse.status_code != 403
            assert titre_premier not in reponse.text
            assert "content-disposition" not in {c.casefold() for c in reponse.headers}
            assert "SIREN" not in reponse.text
    finally:
        client_b.__exit__(None, None, None)


def test_export_consultation_inconnue_404(connexion, contexte_a, config):
    client = _client_api(connexion, contexte_a, config, identifiant="export6@fictif.test")
    try:
        reponse = client.get(
            f"/consultations/{uuid.uuid4()}/memoire/export?format=md"
        )
        assert reponse.status_code == 404, reponse.text
    finally:
        client.__exit__(None, None, None)


# --------------------------------------------------------------------------- #
# 7. Sans session : redirection vers la connexion, jamais de données
# --------------------------------------------------------------------------- #
def test_export_sans_session_redirige_vers_la_connexion():
    from app.main import app

    consultation_id = uuid.uuid4()
    with TestClient(app) as client:
        reponse = client.get(
            f"/consultations/{consultation_id}/memoire/export?format=md",
            **SANS_REDIRECTION,
        )
        assert reponse.status_code == 303
        assert reponse.headers["location"].startswith("/connexion?suivant=")
        assert "content-disposition" not in {c.casefold() for c in reponse.headers}


# --------------------------------------------------------------------------- #
# 8. Empreinte recalculée : elle doit correspondre (la porte du fichier)
# --------------------------------------------------------------------------- #
def test_empreinte_recalculee_egale_celle_validee(connexion, contexte_a, config):
    validation, resultat, consultation_id = _preparer_memoire_valide(
        connexion, contexte_a, config
    )
    dossier = resultat["dossier"]
    assert (
        export_memoire.empreinte_actuelle(connexion, contexte_a, dossier)
        == validation["empreinte_contenu"]
    )
    assert len(validation["empreinte_contenu"]) == 64


# --------------------------------------------------------------------------- #
# 9. La route est bien exposée par l'application
# --------------------------------------------------------------------------- #
def test_route_export_exposee():
    from app.main import app

    chemins = set(app.openapi()["paths"])
    assert "/consultations/{consultation_id}/memoire/export" in chemins


def test_nom_de_fichier_sans_identifiant_interne():
    nom = export_memoire.nom_fichier_export({"titre": "Mémoire — écoles du Brûlé (fictif)"}, "md")
    assert nom.startswith("memoire-technique-") and nom.endswith(".md")
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}", nom)
    assert re.search(r"^[A-Za-z0-9._-]+$", nom), nom


def test_fichier_de_route_dedie_non_confondu_avec_web():
    """L'export ne vit pas dans `routes_web.py` (règle § 2.C/§ 2.E du plan)."""
    racine = Path(__file__).resolve().parents[1]
    assert (racine / "app" / "api" / "routes_export.py").is_file()
    web = (racine / "app" / "web" / "routes_web.py").read_text(encoding="utf-8")
    assert "memoire/export" not in web
