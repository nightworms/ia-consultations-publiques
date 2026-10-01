"""Tests d'intégration — la ligne rouge du mémoire technique, tenue par du code.

Ce fichier attaque la règle centrale de la phase 4 (`docs/PLAN-PHASE-4.md` § 2.B) :

> l'IA **argumente** et **valorise**, elle n'invente aucun chiffre, ne fixe aucun prix,
> ne garantit aucune conformité, ne crée aucune référence. Une section **sans source
> vérifiable** est **refusée explicitement** et **transformée en manque, jamais produite**.

Aucune donnée réelle : éléments de bibliothèque **fictifs et signalés**. Aucun réseau :
le `FournisseurFactice` est imposé par `conftest.py` (correctif C2).
"""

from __future__ import annotations

import uuid

import pytest

from app.services import memoire_technique
from app.services.extraction_pdf import PageExtraite
from app.services.memoire_technique import (
    ErreurMemoire,
    MemoireIntrouvable,
    SourceMemoireInvalide,
)
from app.domain.memoire_technique_genere import ManqueMemoire, SectionMemoire

from test_memoire_technique import (  # helpers du lot L2 (mêmes fixtures fictives)
    CRITERE_SANS_REFERENCE,
    VERIFICATEUR_FICTIF,
    _ajouter_criteres_valides,
    _bibliotheque_l7,
    _client_api,
    _deposer_dce,
    _preparer_dce_et_bibliotheque,
)


def _pages(*textes: str) -> list[PageExtraite]:
    return [
        PageExtraite(
            numero=i + 1,
            texte=texte,
            methode="bibliotheque",
            analyseable=True,
            message=None,
        )
        for i, texte in enumerate(textes)
    ]


# --------------------------------------------------------------------------- #
# 1. Une section sans source vérifiable est refusée et devient un manque
# --------------------------------------------------------------------------- #
def test_source_inventee_refusee_puis_transformee_en_manque():
    element_fictif = {"id": str(uuid.uuid4()), "intitule": "Certification fictive"}
    candidats = [
        {
            "table_source": "certification",
            "element_id": str(element_fictif["id"]),
            "libelle_source": "Certification fictive",
            "emplacement_source": "bibliothèque — Certifications",
            # Extrait invoqué : il ne figure PAS dans l'élément cité.
            "extrait": "phrase inventée qui ne figure nulle part",
            "element": element_fictif,
        }
    ]
    pages = _pages("intitule : Certification fictive\norganisme : Organisme fictif")

    critere = {"id": "c-1", "libelle": "Qualité", "valeur": "20 %"}

    # (a) Refus explicite du garde-fou de source (réutilise `source_presente`).
    with pytest.raises(SourceMemoireInvalide) as erreur:
        memoire_technique.composer_section(
            critere=critere,
            familles=["certifications"],
            candidats=candidats,
            pages=pages,
            confiances=["a_verifier"],
            ordre=0,
        )
    assert "introuvable" in str(erreur.value)

    # (b) La même tentative devient un MANQUE — jamais une section produite.
    resultat = memoire_technique.section_ou_manque(
        critere=critere,
        familles=["certifications"],
        candidats=candidats,
        pages=pages,
        confiances=["a_verifier"],
        ordre=0,
    )
    assert isinstance(resultat, ManqueMemoire)
    assert not isinstance(resultat, SectionMemoire)
    assert resultat.constat.strip()
    assert resultat.action_attendue.strip()


def test_source_correcte_passe_le_garde_fou():
    """Contre-épreuve : la même mécanique accepte une source réellement présente."""
    element = {"id": str(uuid.uuid4()), "intitule": "Certification fictive"}
    candidats = [
        {
            "table_source": "certification",
            "element_id": str(element["id"]),
            "libelle_source": "Certification fictive",
            "emplacement_source": "bibliothèque — Certifications",
            "extrait": "intitule : Certification fictive",
            "element": element,
        }
    ]
    pages = _pages("intitule : Certification fictive\norganisme : Organisme fictif")
    section = memoire_technique.composer_section(
        critere={"id": "c-1", "libelle": "Qualité", "valeur": "20 %"},
        familles=["certifications"],
        candidats=candidats,
        pages=pages,
        confiances=["a_verifier"],
        ordre=0,
    )
    assert isinstance(section, SectionMemoire)
    assert section.nb_sources == 1


# --------------------------------------------------------------------------- #
# 1bis. « La source existe » ne suffit pas : elle doit porter le sujet du critère
# --------------------------------------------------------------------------- #
def test_la_source_qui_ne_parle_pas_du_critere_ne_produit_pas_de_section(
    connexion, contexte_a, config
):
    """Défaut B2 de la vérification L8, tenu par du code jusqu'en base.

    La bibliothèque est **remplie** (deux références d'étanchéité de toitures-terrasses,
    certification, moyens humains et matériels, produit, chapitres) : des sources réelles
    existent, et le garde-fou de source les accepte toutes. Pourtant **aucune** ne porte
    « végétalisé » : le critère « Expérience en toitures-terrasses végétalisées » ne doit
    donc produire **aucune section** — seulement un manque, écrit en base, avec l'action.
    C'est exactement ce que la machine faisait avant : une section étayée par des chantiers
    qui ne sont pas végétalisés, et « 0 manque signalé ».
    """
    _, entreprise_id, fiche_id = _bibliotheque_l7(connexion, contexte_a, config)
    resultat_dce = _deposer_dce(connexion, contexte_a, config, entreprise_id)
    consultation_id = str(resultat_dce.consultation["id"])
    _ajouter_criteres_valides(
        connexion, contexte_a, consultation_id, ((CRITERE_SANS_REFERENCE, "10 %"),)
    )

    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    dossier_id = str(resultat["dossier"]["id"])

    assert resultat["sections"] == [], "aucune section ne doit être fabriquée"
    assert len(resultat["manques"]) == 1
    manque = resultat["manques"][0]
    assert manque["critere_libelle"] == CRITERE_SANS_REFERENCE
    assert float(manque["critere_poids"]) == 10.0
    assert "végétalisées" in manque["constat"]
    assert manque["action_attendue"].strip()

    # Rien en base non plus : ni section, ni source de section pour ce critère.
    sections = connexion.executer(
        contexte_a,
        "SELECT count(*) AS n FROM memoire_section WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s;",
        {"dossier": dossier_id},
    )
    assert int(sections[0]["n"]) == 0
    sources = connexion.executer(
        contexte_a,
        "SELECT count(*) AS n FROM memoire_section_source WHERE client_id = %(client_id)s;",
    )
    assert int(sources[0]["n"]) == 0
    manques = connexion.executer(
        contexte_a,
        "SELECT critere_libelle, critere_poids, constat, action_attendue FROM memoire_manque "
        "WHERE client_id = %(client_id)s AND memoire_dossier_id = %(dossier)s;",
        {"dossier": dossier_id},
    )
    assert [m["critere_libelle"] for m in manques] == [CRITERE_SANS_REFERENCE]
    assert float(manques[0]["critere_poids"]) == 10.0
    assert "végétalisées" in manques[0]["constat"]
    assert "chantier comparable" in manques[0]["action_attendue"]


# --------------------------------------------------------------------------- #
# 2. Un élément d'un autre client ne peut pas servir de source
# --------------------------------------------------------------------------- #
def test_element_d_un_autre_client_ne_peut_pas_etre_une_source():
    element_autre = {"id": str(uuid.uuid4()), "intitule": "Certification d'un autre"}
    candidats = [
        {
            "table_source": "certification",
            "element_id": str(element_autre["id"]),
            "libelle_source": "Certification d'un autre",
            "emplacement_source": "bibliothèque — Certifications",
            "extrait": "intitule : Certification d'un autre",
            "element": element_autre,
        }
    ]
    pages = _pages("intitule : Certification d'un autre")
    # Aucun identifiant autorisé pour ce client : l'élément n'est pas du client.
    with pytest.raises(SourceMemoireInvalide):
        memoire_technique.verifier_sources(candidats, pages, identifiants_autorises=set())


# --------------------------------------------------------------------------- #
# 3. Sans source, rien n'est produit en base
# --------------------------------------------------------------------------- #
def test_bibliotheque_vide_ne_produit_aucune_section_en_base(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config, remplie=False
    )
    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    assert resultat["sections"] == []
    assert resultat["manques"]
    restes = connexion.executer(
        contexte_a,
        "SELECT count(*) AS n FROM memoire_section WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s;",
        {"dossier": str(resultat["dossier"]["id"])},
    )
    assert int(restes[0]["n"]) == 0, "une section a été écrite sans source"


# --------------------------------------------------------------------------- #
# 4. Aucun statut validé posé tout seul
# --------------------------------------------------------------------------- #
def test_aucun_statut_valide_pose_automatiquement(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config
    )
    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    dossier_id = str(resultat["dossier"]["id"])
    assert resultat["dossier"]["statut"] == "brouillon"
    assert all(s["statut"] == "brouillon" for s in resultat["sections"])
    # Aucune ligne de validation à la génération.
    validations = connexion.executer(
        contexte_a,
        "SELECT count(*) AS n FROM memoire_validation WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s;",
        {"dossier": dossier_id},
    )
    assert int(validations[0]["n"]) == 0
    # Et aucun statut validé en base non plus.
    lignes = connexion.executer(
        contexte_a,
        "SELECT statut FROM memoire_section WHERE client_id = %(client_id)s "
        "AND memoire_dossier_id = %(dossier)s;",
        {"dossier": dossier_id},
    )
    assert {ligne["statut"] for ligne in lignes} <= {"brouillon"}


# --------------------------------------------------------------------------- #
# 5. Chaque section persistée est adossée à au moins une source
# --------------------------------------------------------------------------- #
def test_toute_section_persistee_porte_au_moins_une_source(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config
    )
    memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    orphelines = connexion.executer(
        contexte_a,
        "SELECT s.id FROM memoire_section s "
        "LEFT JOIN memoire_section_source src ON src.memoire_section_id = s.id "
        "AND src.client_id = s.client_id "
        "WHERE s.client_id = %(client_id)s AND src.id IS NULL;",
    )
    assert orphelines == [], "section(s) sans aucune source"


# --------------------------------------------------------------------------- #
# 6. Le générateur ne dit ni « conforme » ni « garanti », et ne fixe aucun prix
# --------------------------------------------------------------------------- #
def test_sortie_sans_conformite_ni_prix(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config
    )
    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    texte = (
        " ".join(str(s["contenu"]) for s in resultat["sections"])
        + " "
        + " ".join(str(m["constat"]) + " " + str(m["action_attendue"]) for m in resultat["manques"])
    ).casefold()
    for interdit in ("conforme", "garanti", "certifiée conforme"):
        assert interdit not in texte, interdit


# --------------------------------------------------------------------------- #
# 7. Le schéma du mémoire ne porte aucun champ de prix / marge / tarif
# --------------------------------------------------------------------------- #
def test_schema_memoire_sans_champ_de_prix(connexion_admin):
    lignes = connexion_admin.lire(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name LIKE 'memoire%%' "
        "ORDER BY table_name, column_name;"
    )
    colonnes = [colonne.casefold() for _, colonne in lignes]
    assert colonnes, "aucune colonne trouvée : les tables du mémoire sont absentes"
    for colonne in colonnes:
        for interdit in ("prix", "marge", "tarif", "remise"):
            assert interdit not in colonne, (colonne, interdit)


# --------------------------------------------------------------------------- #
# 8. Parcours API : les manques sortent en 200 (résultat), pas en erreur
# --------------------------------------------------------------------------- #
def test_api_renvoie_les_manques_en_200(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config, remplie=False
    )
    client = _client_api(connexion, contexte_a, config, identifiant="lignesrouges@fictif.test")
    try:
        reponse = client.post(
            f"/api/v1/consultations/{consultation_id}/memoire",
            json={"fiche_version_id": fiche_id},
        )
        assert reponse.status_code == 201, reponse.text
        corps = reponse.json()
        assert corps["sections"] == []
        assert corps["manques"]
        assert corps["resume"]["nb_manques"] == len(corps["manques"])
    finally:
        client.__exit__(None, None, None)


def test_api_memoire_introuvable_renvoie_404(connexion, contexte_a, config):
    _, entreprise_id, _, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config, remplie=True
    )
    # Aucune génération préalable : la lecture doit être un 404 explicite.
    client = _client_api(connexion, contexte_a, config, identifiant="lignesrouges2@fictif.test")
    try:
        reponse = client.get(f"/api/v1/consultations/{consultation_id}/memoire")
        assert reponse.status_code == 404, reponse.text
    finally:
        client.__exit__(None, None, None)
    assert isinstance(entreprise_id, str)
