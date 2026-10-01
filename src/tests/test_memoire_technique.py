"""Tests du lot L2 (phase 4) — moteur de génération du mémoire technique.

Aucune donnée réelle : clients, DCE et bibliothèque sont **fictifs et signalés**
(« DÉMONSTRATION », décision D10). Aucun appel réseau : la suite impose le
`FournisseurFactice` et interdit toute sortie (correctif C2, `garde_isolation.py`).

Exigences vérifiables, démontrées **par exécution** :

1. migration `0005` : `up` puis `down` (tables créées, puis retirées) ;
2. le plan suit les critères du DCE **dans l'ordre de pondération décroissante** ; le
   critère « prix » ne produit **jamais** de section (hors mémoire technique) ;
3. chaque section porte **au moins une source** pointant un élément réel du **même
   client** ; aucune section sans source ;
4. les manques sont un **résultat** (constat + action à mener), pas une erreur ;
5. un critère **sans pondération connue** passe en fin, avec sa raison affichée ;
6. tout sort en `brouillon` ; aucun statut validé sans action humaine nommée et horodatée ;
   la validation finale écrit une ligne `memoire_validation` avec l'empreinte SHA-256 ;
7. isolation par `client_id` : un client ne voit ni n'alimente le mémoire d'un autre ;
8. parcours API `/api/v1` complet.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.config import charger_config
from app.domain.memoire_technique_genere import (
    CONSTAT_PRIX_HORS_MEMOIRE,
    ManqueMemoire,
    SectionMemoire,
    constat_manque_sujet,
    couverture_sujet,
    familles_pour_critere,
)
from app.services import analyse_dce, memoire_technique
from app.services.authentification import ServiceAuthentification
from app.services.bibliotheque import ServiceBibliotheque
from app.services.memoire_technique import (
    ErreurMemoire,
    MemoireIntrouvable,
    SourceMemoireInvalide,
)
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.fichiers import StockageFichiers
from app.storage.migrations import ExecuteurMigrations, lister_migrations

from fixtures.generer_fixtures import ecrire_pdf_texte

MENTION_FICTIF = "DOCUMENT FICTIF — DÉMONSTRATION — AUCUNE DONNÉE RÉELLE"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel
VERIFICATEUR_FICTIF = "Vérificateur fictif (démonstration)"
RELECTEUR_FICTIF = "Relecteur fictif (démonstration)"
VALIDATEUR_FICTIF = "Validateur fictif (démonstration)"


# --------------------------------------------------------------------------- #
# Utilitaires de préparation
# --------------------------------------------------------------------------- #
def _stockage(config) -> StockageFichiers:
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _creer_document_fictif(
    connexion: Connexion, contexte: ContexteClient, entreprise_id: str, fiche_id: str
) -> str:
    """Crée une pièce de bibliothèque **fictive** (aucun fichier réel n'est lu).

    Certaines entités (`certification`, `assurance`, `cv`) exigent une référence à un
    `document` (contrainte de clé étrangère). On en crée une ligne signalée fictive ;
    aucun contenu réel n'est utilisé et le fichier n'existe pas sur disque.
    """
    document_id = str(uuid.uuid4())
    ligne = connexion.executer_une(
        contexte,
        "INSERT INTO document (id, client_id, entreprise_id, fiche_version_id, nature, "
        "type_document, libelle, chemin_stockage, deposant, empreinte_sha256, "
        "taille_octets, mime_type, sensibilite) "
        "VALUES (%(id)s, %(client_id)s, %(entreprise_id)s, %(fiche)s, "
        "'piece_bibliotheque', 'fiction', %(libelle)s, %(chemin)s, 'entreprise', "
        "%(empreinte)s, 0, 'text/plain', 'interne') RETURNING id;",
        {
            "id": document_id,
            "entreprise_id": entreprise_id,
            "fiche": fiche_id,
            "libelle": f"Pièce fictive — {MENTION_FICTIF}"[:255],
            "chemin": f"fictif/{contexte.client_id}/{document_id}.txt",
            "empreinte": "0" * 64,
        },
    )
    assert ligne is not None
    return document_id


def _bibliotheque(
    connexion: Connexion, contexte: ContexteClient, config, *, remplie: bool
) -> tuple[ServiceBibliotheque, str, str]:
    """Entreprise + fiche fictives, et — si `remplie` — une bibliothèque réelle."""
    service = ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)
    entreprise_id = service.creer_entreprise("Entreprise fictive — DÉMONSTRATION")
    fiche = service.ouvrir_fiche(entreprise_id)
    fiche_id = str(fiche["id"])
    if not remplie:
        connexion.valider()
        return service, str(entreprise_id), fiche_id

    piece = _creer_document_fictif(connexion, contexte, entreprise_id, fiche_id)

    def saisir(famille: str, entite: str, donnees: dict) -> None:
        charge = dict(donnees)
        charge["origine"] = "saisie_entreprise"
        service.saisir(famille, entite, fiche_id, charge)

    saisir(
        "references_chantiers",
        "reference_chantier",
        {
            "intitule_operation": "Réfection étanchéité groupe scolaire (fictif)",
            "maitre_ouvrage": "Collectivité fictive (démonstration)",
            "nature_travaux_libelle": "Étanchéité de toitures-terrasses",
            "lieu_commune": "Commune fictive",
            "date_debut": "2024-06-01",
            "date_fin": "2024-09-30",
            "montant_montant": "320000",
            "montant_devise": "EUR",
            "duree_mois": 4,
            "surface_traitee": "1450",
            "surface_unite": "m2",
            "description": "Support béton dégradé, site occupé pendant les vacances.",
        },
    )
    saisir(
        "certifications",
        "certification",
        {
            "intitule": "Qualification étanchéité (fictive)",
            "organisme": "Organisme fictif",
            "domaine_code": "etancheite",
            "date_obtention": "2023-01-15",
            "date_echeance": "2027-01-15",
            "piece": piece,
        },
    )
    saisir(
        "assurances",
        "assurance",
        {
            "type_assurance": "responsabilite_decennale",
            "assureur": "Assureur fictif SA",
            "numero_contrat": "FICTIF-2026-001",
            "montant_garantie_montant": "1500000",
            "montant_garantie_devise": "EUR",
            "date_debut": "2026-01-01",
            "date_echeance": "2027-01-01",
            "piece": piece,
        },
    )
    saisir(
        "moyens_humains",
        "effectif_metier",
        {"metier_code": "etancheur", "metier_libelle": "Étancheur", "nombre": 6},
    )
    saisir(
        "moyens_humains",
        "cv",
        {
            "nom": "Conducteur",
            "prenom": "Fictif",
            "fonction": "Conducteur de travaux",
            "diplomes": "BTS bâtiment",
            "annees_experience": 12,
            "cv_piece": piece,
        },
    )
    saisir(
        "moyens_materiels",
        "moyen_materiel",
        {
            "categorie_code": "engin",
            "designation": "Camion grue fictif",
            "quantite": 2,
            "propriete": "propre",
        },
    )
    saisir(
        "fiches_produits",
        "produit",
        {
            "fournisseur": "Fournisseur fictif",
            "reference_produit": "REF-FICTIF-001",
            "designation": "Système d'étanchéité bitumineux (fictif)",
            "domaine_application": "Toitures-terrasses",
            "avis_technique": piece,
            "date_validite_document": "2027-06-30",
        },
    )
    saisir(
        "capacites_financieres",
        "exercice_comptable",
        {
            "annee_exercice": 2025,
            "chiffre_affaires_montant": "2400000",
            "chiffre_affaires_devise": "EUR",
            "resultat_net_montant": "140000",
            "resultat_net_devise": "EUR",
            "effectif_moyen": 18,
        },
    )
    saisir(
        "memoire_technique",
        "chapitre_memoire",
        {
            "titre": "Méthode d'exécution et phasage",
            "ordre": 10,
            "contenu_texte": (
                "Décapage, contrôle du support, relevés et protection : chapitre "
                "réutilisable fictif."
            ),
        },
    )
    connexion.valider()
    return service, str(entreprise_id), fiche_id


def _deposer_dce(connexion, contexte, config, entreprise_id: str):
    """Dépose le DCE fictif de démonstration et l'analyse (fournisseur factice)."""
    pdf = Path(__file__).resolve().parent / "fixtures" / "dce_fictif.pdf"
    resultat = analyse_dce.deposer_et_analyser(
        connexion,
        contexte,
        _stockage(config),
        entreprise_id=entreprise_id,
        libelle=f"Consultation fictive — {MENTION_FICTIF}",
        nom_fichier=pdf.name,
        contenu=pdf.read_bytes(),
        type_mime="application/pdf",
    )
    connexion.valider()
    return resultat


def _valider_criteres(connexion, contexte, consultation_id: str) -> list[dict]:
    elements = connexion.executer(
        contexte,
        "SELECT * FROM extraction_element WHERE client_id = %(client_id)s "
        "AND consultation_id = %(consultation_id)s AND categorie = 'critere' "
        "ORDER BY date_extraction, id;",
        {"consultation_id": consultation_id},
    )
    for element in elements:
        analyse_dce.verifier_element(
            connexion,
            contexte,
            consultation_id=consultation_id,
            element_id=str(element["id"]),
            action="valider",
            verificateur_nom=VERIFICATEUR_FICTIF,
        )
    connexion.valider()
    return elements


def _table_existe(conn: ConnexionAdministration, nom: str) -> bool:
    return bool(
        conn.lire(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (nom,),
        )
    )


# --------------------------------------------------------------------------- #
# Jeu L7 (fictif) — la bibliothèque « remplie » qui ne couvre PAS un critère
# --------------------------------------------------------------------------- #
#: Les six critères pondérés du DCE fictif du jeu L7 (`scripts/jeu-de-test/DEMONSTRATION.md`
#: § 3). Le cinquième — « Expérience en toitures-terrasses végétalisées » — est **le manque
#: volontaire** : aucune référence de la bibliothèque L7 ne porte « végétalisé ».
CRITERES_L7: tuple[tuple[str, str], ...] = (
    ("Étanchéité de toitures-terrasses sur bâtiments scolaires", "40 %"),
    ("Traitement des relevés d'étanchéité et des points singuliers", "20 %"),
    ("Exécution en site occupé et planning par phases", "15 %"),
    ("Moyens humains et matériels affectés au marché", "10 %"),
    ("Expérience en toitures-terrasses végétalisées", "10 %"),
    ("Délai d'exécution et engagement de planning", "5 %"),
)
CRITERE_SANS_REFERENCE = "Expérience en toitures-terrasses végétalisées"


def _bibliotheque_l7(connexion: Connexion, contexte: ContexteClient, config):
    """Bibliothèque fictive **fidèle au jeu L7** : des toitures-terrasses ordinaires.

    Elle est volontairement **remplie** (références, certification, moyens humains et
    matériels, produit, chapitres) et pourtant **aucun** élément ne porte le mot
    « végétalisé » : c'est le manque volontaire du jeu. Une section produite sur cette
    bibliothèque pour ce critère serait exactement le défaut B2 (une expérience affirmée
    que rien ne documente).
    """
    service = ServiceBibliotheque(
        connexion, config.cle_chiffrement_maitresse, contexte
    )
    entreprise_id = service.creer_entreprise(
        "Entreprise fictive L7 — DÉMONSTRATION — AUCUNE DONNÉE RÉELLE"
    )
    fiche = service.ouvrir_fiche(entreprise_id)
    fiche_id = str(fiche["id"])
    piece = _creer_document_fictif(connexion, contexte, entreprise_id, fiche_id)

    def saisir(famille: str, entite: str, donnees: dict) -> None:
        charge = dict(donnees)
        charge["origine"] = "saisie_entreprise"
        service.saisir(famille, entite, fiche_id, charge)

    saisir(
        "references_chantiers",
        "reference_chantier",
        {
            "intitule_operation": "Réfection de l'étanchéité des toitures-terrasses — "
                                  "groupe scolaire (fictif)",
            "maitre_ouvrage": "S.I.F.E.P.F. (maître d'ouvrage fictif)",
            "nature_travaux_libelle": "Étanchéité de toitures-terrasses",
            "lieu_commune": "Commune fictive",
            "date_debut": "2024-07-08",
            "date_fin": "2024-10-18",
            "montant_montant": "412000",
            "montant_devise": "EUR",
            "duree_mois": 14,
            "surface_traitee": "3200",
            "surface_unite": "m2",
            "description": (
                "Réfection complète de l'étanchéité de toitures-terrasses de deux "
                "bâtiments scolaires en service. Reprise des relevés d'étanchéité et "
                "traitement des points singuliers. Travaux exécutés en site occupé, par "
                "phases pendant les vacances scolaires."
            ),
            "competences_appliquees": (
                "Étanchéité de toitures-terrasses de bâtiments scolaires ; relevés "
                "d'étanchéité et points singuliers ; exécution en site occupé par phases."
            ),
        },
    )
    saisir(
        "references_chantiers",
        "reference_chantier",
        {
            "intitule_operation": "Étanchéité de bâtiments administratifs — site occupé "
                                  "(fictif)",
            "maitre_ouvrage": "Communauté fictive des services du Plateau",
            "nature_travaux_libelle": "Étanchéité en site occupé",
            "description": (
                "Réfection d'étanchéité de toitures-terrasses de locaux occupés pendant "
                "les travaux. Organisation en trois phases, protection des accès."
            ),
            "competences_appliquees": (
                "Exécution en site occupé ; planning par phases ; protection des accès."
            ),
        },
    )
    saisir(
        "certifications",
        "certification",
        {
            "intitule": "Qualification étanchéité de toitures-terrasses (fictive)",
            "organisme": "O.C.F.E. — Organisme Certificat Fictif Étanchéité",
            "domaine_code": "etancheite",
            "date_obtention": "2021-09-01",
            "date_echeance": "2026-09-15",
            "piece": piece,
        },
    )
    saisir(
        "moyens_humains",
        "effectif_metier",
        {"metier_code": "etancheur", "metier_libelle": "Étancheur", "nombre": 16},
    )
    saisir(
        "moyens_humains",
        "cv",
        {
            "nom": "Conducteur",
            "prenom": "Fictif",
            "fonction": "Conducteur de travaux",
            "diplomes": "BTS bâtiment",
            "annees_experience": 12,
            "cv_piece": piece,
        },
    )
    saisir(
        "moyens_materiels",
        "moyen_materiel",
        {
            "categorie_code": "engin_elevation",
            "designation": "Nacelle élévatrice",
            "quantite": 2,
            "propriete": "location",
        },
    )
    saisir(
        "fiches_produits",
        "produit",
        {
            "fournisseur": "FOURNISSEUR-FICTIF",
            "reference_produit": "REF-FICTIVE-BIT-42",
            "designation": "Membrane bitumineuse bicouche autoprotégée",
            "domaine_application": (
                "Étanchéité de toitures-terrasses, relevés et points singuliers (fictif)."
            ),
            "avis_technique": piece,
            "date_validite_document": "2027-03-01",
        },
    )
    saisir(
        "memoire_technique",
        "chapitre_memoire",
        {
            "titre": "Méthode d'exécution d'une étanchéité de toiture-terrasse",
            "ordre": 1,
            "contenu_texte": (
                "Décapage, contrôle et réparation du support, reprise des relevés et des "
                "points singuliers, contrôle final et réception."
            ),
        },
    )
    saisir(
        "memoire_technique",
        "chapitre_memoire",
        {
            "titre": "Organisation d'un chantier en site occupé",
            "ordre": 2,
            "contenu_texte": (
                "Travaux organisés par phases, balisage des zones, protection des accès."
            ),
        },
    )
    connexion.valider()
    return service, str(entreprise_id), fiche_id


def _ajouter_criteres_valides(
    connexion: Connexion,
    contexte: ContexteClient,
    consultation_id: str,
    criteres: tuple[tuple[str, str], ...],
) -> list[str]:
    """Écrit des **critères validés** du jeu L7 dans `extraction_element`.

    Même table et mêmes verrous que la brique B : `source_document_id` et
    `source_emplacement` non nuls, `statut_verification = 'valide'` avec un vérificateur
    nommé (contrainte `extraction_element_verificateur_requis`). Le DCE fictif déposé a
    les six critères du jeu L7 — comme dans la démonstration.
    """
    reference = connexion.executer_une(
        contexte,
        "SELECT source_document_id FROM extraction_element "
        "WHERE client_id = %(client_id)s AND consultation_id = %(consultation_id)s "
        "ORDER BY date_extraction, id LIMIT 1;",
        {"consultation_id": consultation_id},
    )
    assert reference is not None, "le DCE déposé doit porter au moins un élément"
    document_id = str(reference["source_document_id"])
    identifiants: list[str] = []
    for rang, (libelle, valeur) in enumerate(criteres):
        ligne = connexion.executer_une(
            contexte,
            "INSERT INTO extraction_element (client_id, consultation_id, categorie, "
            "libelle, valeur, source_document_id, source_emplacement, source_extrait, "
            "statut_verification, verificateur_nom, date_verification) "
            "VALUES (%(client_id)s, %(consultation_id)s, 'critere', %(libelle)s, "
            "%(valeur)s, %(document)s, %(emplacement)s, %(extrait)s, 'valide', "
            "%(verificateur)s, now()) RETURNING id;",
            {
                "consultation_id": consultation_id,
                "libelle": libelle,
                "valeur": valeur,
                "document": document_id,
                "emplacement": f"ARTICLE 5 — critère {rang + 1} (fictif)",
                "extrait": f"- {libelle} : {valeur}",
                "verificateur": VERIFICATEUR_FICTIF,
            },
        )
        assert ligne is not None
        identifiants.append(str(ligne["id"]))
    connexion.valider()
    return identifiants


def _preparer_dce_et_bibliotheque(connexion, contexte, config, *, remplie: bool = True):
    service, entreprise_id, fiche_id = _bibliotheque(
        connexion, contexte, config, remplie=remplie
    )
    resultat = _deposer_dce(connexion, contexte, config, entreprise_id)
    consultation_id = str(resultat.consultation["id"])
    _valider_criteres(connexion, contexte, consultation_id)
    return service, entreprise_id, fiche_id, consultation_id


# --------------------------------------------------------------------------- #
# 1. Migration 0005 : up puis down
# --------------------------------------------------------------------------- #
def test_migration_0005_presente_et_reversible(connexion_admin, base_migree):
    numeros = [m.numero for m in lister_migrations()]
    assert "0005" in numeros
    migration = next(m for m in lister_migrations() if m.numero == "0005")
    assert migration.nom == "0005_memoire_technique"
    assert migration.sql_up and migration.sql_down

    executeur = ExecuteurMigrations(charger_config().database_url)
    for table in (
        "memoire_dossier",
        "memoire_section",
        "memoire_section_source",
        "memoire_manque",
        "memoire_validation",
    ):
        assert _table_existe(connexion_admin, table), table

    apres_0004 = [m.numero for m in lister_migrations() if m.numero > "0004"]
    annulees = executeur.down(len(apres_0004))
    assert "0005" in annulees
    for table in (
        "memoire_dossier",
        "memoire_section",
        "memoire_section_source",
        "memoire_manque",
        "memoire_validation",
    ):
        assert not _table_existe(connexion_admin, table), table
    # Aucune table existante n'a été détruite par l'annulation.
    assert _table_existe(connexion_admin, "consultation")
    assert _table_existe(connexion_admin, "reference_chantier")
    assert _table_existe(connexion_admin, "checklist_ligne")

    reappliquees = executeur.up()
    assert set(reappliquees) == set(annulees)
    assert _table_existe(connexion_admin, "memoire_dossier")


# --------------------------------------------------------------------------- #
# 2/3/4. Génération : ordre, sources réelles, critère prix hors mémoire
# --------------------------------------------------------------------------- #
def test_generation_suit_les_criteres_et_les_pondere(connexion, contexte_a, config):
    _, entreprise_id, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config
    )
    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    dossier = resultat["dossier"]
    sections = resultat["sections"]
    manques = resultat["manques"]

    # Tout sort en brouillon : aucun statut validé posé par du code.
    assert dossier["statut"] == "brouillon"
    assert sections, "la bibliothèque remplie doit produire au moins une section"
    assert all(s["statut"] == "brouillon" for s in sections)

    # Ordre = pondération décroissante ; le critère prix ne fait pas de section.
    poids = [float(s["critere_poids"]) for s in sections]
    assert poids == sorted(poids, reverse=True), poids
    assert all("prix" not in str(s["critere_libelle"]).casefold() for s in sections)

    # Le critère prix devient un manque explicite « hors mémoire technique ».
    manque_prix = [
        m for m in manques if "prix" in str(m["critere_libelle"]).casefold()
    ]
    assert manque_prix, manques
    assert manque_prix[0]["constat"] == CONSTAT_PRIX_HORS_MEMOIRE
    assert "acte d'engagement" in manque_prix[0]["action_attendue"]

    # Le critère le plus lourd (hors prix) est le premier des sections.
    assert "valeur technique" in str(sections[0]["critere_libelle"]).casefold()
    assert float(sections[0]["critere_poids"]) >= float(sections[-1]["critere_poids"])


def test_chaque_section_est_adossée_a_une_source_du_meme_client(
    connexion, contexte_a, config
):
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
    assert resultat["sections"]
    tables_connues = {
        "entreprise_version", "representant_legal", "exercice_comptable", "attestation",
        "capacite_production", "assurance", "certification", "reference_chantier",
        "effectif_metier", "organigramme", "cv", "moyen_materiel", "produit",
        "chapitre_memoire",
    }
    for section in resultat["sections"]:
        sources = section["sources"]
        assert sources, f"section sans source : {section['titre']!r}"
        for source in sources:
            table = str(source["table_source"])
            assert table in tables_connues, table
            # L'élément cité existe réellement, pour CE client.
            ligne = connexion.executer_une(
                contexte_a,
                f"SELECT id FROM {table} WHERE client_id = %(client_id)s AND id = %(id)s;",
                {"id": str(source["element_id"])},
            )
            assert ligne is not None, (table, source["element_id"])
            assert source["libelle_source"] and source["emplacement_source"]

    # Chaque affirmation est couverte : au moins une phrase « - … » par source citée.
    for section in resultat["sections"]:
        assert section["contenu"].count("\n- ") >= len(section["sources"])


def test_bibliotheque_vide_produit_des_manques_pas_des_sections(
    connexion, contexte_a, config
):
    """Sans bibliothèque, tout devient manque : ce n'est pas un cas d'erreur."""
    _, entreprise_id, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
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
    assert resultat["manques"], "chaque critère doit produire un manque"
    for manque in resultat["manques"]:
        assert manque["constat"].strip()
        assert manque["action_attendue"].strip()
    # Un critère de contenu (valeur technique) dit quoi ajouter.
    vt = [m for m in resultat["manques"] if "valeur technique" in m["critere_libelle"].casefold()]
    assert vt, resultat["manques"]
    assert "chantier" in vt[0]["action_attendue"].casefold()


# --------------------------------------------------------------------------- #
# 4bis. Le sujet du critère — « la source existe » ne suffit pas (défaut B2)
# --------------------------------------------------------------------------- #
def test_couverture_sujet_distingue_le_sujet_de_la_presence_d_un_element():
    """Un élément peut exister et **ne pas** porter le sujet du critère."""
    textes = [
        "intitule_operation : Réfection de l'étanchéité des toitures-terrasses (fictif)\n"
        "nature_travaux_libelle : Étanchéité de toitures-terrasses"
    ]
    couverture = couverture_sujet(
        CRITERE_SANS_REFERENCE, ("experience",), textes
    )
    assert couverture.termes_sujet == ("toitures", "terrasses", "végétalisées")
    assert couverture.termes_corrobore == ("toitures", "terrasses")
    assert couverture.termes_absents == ("végétalisées",)
    assert couverture.etablie is False
    # Le constat nomme le terme absent — vérifiable par une requête sur la bibliothèque.
    constat = constat_manque_sujet(couverture.termes_absents)
    assert "végétalisées" in constat
    assert "n'est pas couvert" in constat


def test_couverture_sujet_etablie_quand_la_bibliotheque_porte_le_sujet():
    """Contre-épreuve : le même critère est couvert si un élément porte son sujet."""
    textes = [
        "intitule_operation : Toiture-terrasse végétalisée d'un groupe scolaire (fictif)"
    ]
    couverture = couverture_sujet(CRITERE_SANS_REFERENCE, ("experience",), textes)
    assert couverture.termes_absents == ()
    assert couverture.etablie is True
    assert "végétalisées" in couverture.justification()


def test_repli_familles_defaut_ne_fabrique_plus_une_section():
    """Le repli par défaut collecte des candidats mais ne **produit** plus rien seul.

    Sans le contrôle de couverture, `FAMILLES_DEFAUT` — non vide dès qu'une source du lot
    existe — faisait produire une section pour n'importe quel libellé non reconnu.
    """
    libelle = "Étanchéité de toitures-terrasses végétalisées"
    familles = familles_pour_critere(libelle)
    assert familles, "le repli doit toujours proposer des familles à interroger"
    element = {
        "id": str(uuid.uuid4()),
        "designation": "Camion grue fictif",
        "propriete": "propre",
    }
    candidats, pages, confiances = memoire_technique._candidats_pour_familles(
        ["moyens_materiels"], {"moyens_materiels": {"moyen_materiel": [element]}}
    )
    assert candidats, "la source existe bien : c'est justement le piège"
    resultat = memoire_technique.section_ou_manque(
        critere={"id": "c-default", "libelle": libelle, "valeur": "10 %"},
        familles=familles,
        candidats=candidats,
        pages=pages,
        confiances=confiances,
        ordre=0,
        identifiants_autorises={c["element_id"] for c in candidats},
    )
    assert isinstance(resultat, ManqueMemoire)
    assert "végétalisées" in resultat.constat
    assert resultat.action_attendue.strip()


def test_critere_du_jeu_l7_non_couvert_produit_un_manque_et_cinq_sections(
    connexion, contexte_a, config
):
    """Le cas du jeu L7, de bout en bout : **1 manque et 5 sections**.

    Bibliothèque **remplie** (références de toitures-terrasses ordinaires, certification,
    moyens, produit, chapitres), six critères pondérés validés. Le critère « Expérience en
    toitures-terrasses végétalisées » (10 %) n'est couvert par **aucun** élément : il doit
    sortir en **manque** avec son action, et **jamais** en section étayée par des chantiers
    qui ne sont pas végétalisés.
    """
    _, entreprise_id, fiche_id = _bibliotheque_l7(connexion, contexte_a, config)
    resultat_dce = _deposer_dce(connexion, contexte_a, config, entreprise_id)
    consultation_id = str(resultat_dce.consultation["id"])
    _ajouter_criteres_valides(connexion, contexte_a, consultation_id, CRITERES_L7)

    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    sections = resultat["sections"]
    manques = resultat["manques"]

    # Le manque volontaire du jeu L7 — et lui seul sur les six critères.
    assert len(manques) == 1, [m["critere_libelle"] for m in manques]
    assert len(sections) == 5, [s["critere_libelle"] for s in sections]
    manque = manques[0]
    assert manque["critere_libelle"] == CRITERE_SANS_REFERENCE
    assert float(manque["critere_poids"]) == 10.0
    assert "végétalisées" in manque["constat"]
    assert "n'est pas couvert" in manque["constat"]
    assert "chantier comparable" in manque["action_attendue"]
    # Aucune section ne parle de ce critère : rien n'est affirmé sans preuve.
    assert all(
        "végétalis" not in str(section["critere_libelle"]).casefold() for section in sections
    )
    # Ordre = pondération décroissante (le plan suit la notation du DCE).
    poids = [float(s["critere_poids"]) for s in sections]
    assert poids == sorted(poids, reverse=True), poids
    assert poids[0] == 40.0
    # Chaque section est sourcée, et **traçable** : sa correspondance est écrite.
    for section in sections:
        assert section["sources"], section["titre"]
        assert "Correspondance établie" in section["contenu"]

    # Le manque est bien **écrit en base** (pas seulement retourné) : c'est le résultat.
    lignes = connexion.executer(
        contexte_a,
        "SELECT critere_libelle, constat, action_attendue FROM memoire_manque "
        "WHERE client_id = %(client_id)s AND memoire_dossier_id = %(dossier)s;",
        {"dossier": str(resultat["dossier"]["id"])},
    )
    assert [ligne["critere_libelle"] for ligne in lignes] == [CRITERE_SANS_REFERENCE]
    assert "végétalisées" in lignes[0]["constat"]


def test_critere_du_jeu_l7_couvert_par_la_bibliotheque_produit_une_section(
    connexion, contexte_a, config
):
    """Contre-épreuve du même critère : dès qu'un élément porte le sujet, la section naît.

    Non-régression du contrôle : il ne bloque pas un critère réellement documenté.
    """
    service, entreprise_id, fiche_id = _bibliotheque_l7(connexion, contexte_a, config)
    service.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche_id,
        {
            "intitule_operation": "Toiture-terrasse végétalisée d'un groupe scolaire (fictif)",
            "maitre_ouvrage": "Collectivité fictive (démonstration)",
            "nature_travaux_libelle": "Étanchéité de toiture-terrasse végétalisée",
            "description": "Étanchéité d'une toiture-terrasse végétalisée (fictif).",
            "origine": "saisie_entreprise",
        },
    )
    connexion.valider()
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
    assert resultat["manques"] == []
    assert len(resultat["sections"]) == 1
    section = resultat["sections"][0]
    assert section["critere_libelle"] == CRITERE_SANS_REFERENCE
    assert "végétalisées" in section["contenu"]  # la trace de la correspondance
    assert section["sources"]


# --------------------------------------------------------------------------- #
# 4ter. Aucun code de nomenclature dans le texte produit (critère 6)
# --------------------------------------------------------------------------- #
#: Un code de nomenclature tel qu'il ne doit **jamais** sortir : minuscules, segments
#: séparés par des tirets bas (`materiel_mise_en_oeuvre`, `chef_equipe`).
MOTIF_CODE_NOMENCLATURE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)+")


def _codes_dans(texte: str) -> list[str]:
    """Les codes de nomenclature encore présents dans un texte (idéalement : aucun)."""
    return MOTIF_CODE_NOMENCLATURE.findall(texte or "")


def test_code_de_nomenclature_rendu_lisible_jamais_en_tirets_bas():
    """Un code sans libellé disponible est rendu lisible, pas écrit en tirets bas."""
    assert memoire_technique._code_lisible("materiel_mise_en_oeuvre") == (
        "materiel mise en oeuvre"
    )
    assert memoire_technique._code_lisible("metier.etancheite") == "metier etancheite"
    # Une valeur qui n'est pas un code est rendue inchangée (rien n'est inventé).
    assert memoire_technique._code_lisible("Nacelle élévatrice") == "Nacelle élévatrice"
    assert memoire_technique._code_lisible(None) == ""


def test_statut_validite_dit_en_metier_jamais_en_code():
    """« valide », « échéance proche », « échéance dépassée » — jamais `[expire]`."""
    assert memoire_technique._libelle_validite("valide") == "valide"
    assert memoire_technique._libelle_validite("echeance_proche") == "échéance proche"
    assert memoire_technique._libelle_validite("expire") == "échéance dépassée"
    assert memoire_technique._libelle_validite("non_renseigne") == (
        "validité non renseignée"
    )
    assert memoire_technique._libelle_validite(None) == ""


def test_libelle_source_garde_le_libelle_metier_et_ecarte_le_code():
    """Le libellé métier (`designation`) d'abord : le code de catégorie n'y entre pas."""
    element = {
        "designation": "Groupe d'étanchéité à air chaud",
        "categorie_code": "materiel_mise_en_oeuvre",
    }
    assert memoire_technique.libelle_source("moyen_materiel", element) == (
        "Groupe d'étanchéité à air chaud"
    )
    effectif = {"metier_libelle": "Chef d'équipe étanchéité", "metier_code": "chef_equipe"}
    assert memoire_technique.libelle_source("effectif_metier", effectif) == (
        "Chef d'équipe étanchéité"
    )


def test_libelle_source_retombe_sur_le_code_rendu_lisible_si_aucun_libelle():
    """Sans libellé disponible, le code sert de repli — rendu lisible."""
    assert memoire_technique.libelle_source(
        "moyen_materiel", {"categorie_code": "materiel_mise_en_oeuvre"}
    ) == "materiel mise en oeuvre"
    assert memoire_technique.libelle_source(
        "effectif_metier", {"metier_code": "responsable_qse", "nombre": 1}
    ) == "responsable qse"


def test_emplacement_source_dit_l_entite_et_la_validite_en_francais():
    """Aucun code dans `emplacement_source` : il est persisté puis exporté tel quel."""
    element = {
        "id": str(uuid.uuid4()),
        "designation": "Nacelle élévatrice",
        "categorie_code": "engin_elevation",
        "quantite": 2,
        "statut_validite": "expire",
    }
    candidats, _, _ = memoire_technique._candidats_pour_familles(
        ["moyens_materiels"], {"moyens_materiels": {"moyen_materiel": [element]}}
    )
    emplacement = candidats[0]["emplacement_source"]
    assert emplacement == (
        "bibliothèque — Moyens matériels / Moyen matériel — validité : échéance dépassée"
    )
    assert _codes_dans(emplacement) == []
    assert "[" not in emplacement and "]" not in emplacement


def test_texte_du_memoire_du_jeu_l7_ne_porte_aucun_code_de_nomenclature(
    connexion, contexte_a, config
):
    """Bout en bout (jeu L7) : ni le texte, ni les sources, ni l'export ne parlent en code.

    C'est le défaut relevé sur `/consultations/{id}/memoire` : les codes de la
    bibliothèque (`materiel_mise_en_oeuvre`, `chef_equipe`, …) et les crochets de
    validité (`[valide]`, `[expire]`) sortaient du générateur.
    """
    from app.services.export_memoire import rendre_markdown

    _, entreprise_id, fiche_id = _bibliotheque_l7(connexion, contexte_a, config)
    resultat_dce = _deposer_dce(connexion, contexte_a, config, entreprise_id)
    consultation_id = str(resultat_dce.consultation["id"])
    _ajouter_criteres_valides(connexion, contexte_a, consultation_id, CRITERES_L7)

    resultat = memoire_technique.generer_memoire(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        consultation_id=consultation_id,
        fiche_version_id=fiche_id,
    )
    assert resultat["sections"]

    textes: dict[str, str] = {
        "contenu": "\n".join(str(s["contenu"]) for s in resultat["sections"]),
        "sources": "\n".join(
            f"{source['libelle_source']} — {source['emplacement_source']}"
            for section in resultat["sections"]
            for source in section["sources"]
        ),
        "export_markdown": rendre_markdown(resultat),
    }
    for nom, texte in textes.items():
        assert _codes_dans(texte) == [], (nom, _codes_dans(texte))
        assert "[valide]" not in texte and "[expire]" not in texte, nom

    # Le critère « Moyens humains et matériels » est bien rendu en métier.
    moyens = [
        s for s in resultat["sections"] if "moyens humains et matériels" in s["titre"].casefold()
    ]
    assert moyens, [s["titre"] for s in resultat["sections"]]
    contenu = str(moyens[0]["contenu"])
    assert "Effectif Étancheur : 16." in contenu
    assert "Moyen matériel Nacelle élévatrice (engin elevation)" in contenu
    # Les deux éléments cités portent leur libellé métier, sans code.
    libelles = {str(s["libelle_source"]) for s in moyens[0]["sources"]}
    assert "Nacelle élévatrice" in libelles
    assert "Étancheur" in libelles


# --------------------------------------------------------------------------- #
# 5. Critère sans pondération : en fin, avec sa raison affichée
# --------------------------------------------------------------------------- #
def test_tri_ponderation_et_critere_sans_poids_en_fin():
    criteres = [
        {"id": "c1", "libelle": "Sans poids", "valeur": None},
        {"id": "c2", "libelle": "Léger", "valeur": "10 %"},
        {"id": "c3", "libelle": "Lourd", "valeur": "40 %"},
    ]
    tries = memoire_technique.trier_criteres(criteres)
    assert [c["id"] for c in tries] == ["c3", "c2", "c1"]


def test_critere_sans_ponderation_affiche_sa_raison():
    """Une section d'un critère non pondéré porte la raison de son classement en fin."""
    element = {"id": str(uuid.uuid4()), "titre": "Chapitre fictif", "ordre": 1}
    candidats, pages, confiances = memoire_technique._candidats_pour_familles(
        ["memoire_technique"], {"memoire_technique": {"chapitre_memoire": [element]}}
    )
    resultat = memoire_technique.section_ou_manque(
        critere={"id": "c-x", "libelle": "Critère divers", "valeur": None},
        familles=["memoire_technique"],
        candidats=candidats,
        pages=pages,
        confiances=confiances,
        ordre=9,
    )
    assert isinstance(resultat, SectionMemoire)
    assert "non connue du DCE" in resultat.contenu
    assert "traité en fin de mémoire" in resultat.contenu


# --------------------------------------------------------------------------- #
# 6. Statuts humains — aucun statut validé sans un humain nommé
# --------------------------------------------------------------------------- #
def test_statuts_humains_et_validation_finale(connexion, contexte_a, config):
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
    sections = resultat["sections"]
    assert sections

    # Aucun nom : refus explicite.
    with pytest.raises(ErreurMemoire):
        memoire_technique.changer_statut_section(
            connexion, contexte_a, section_id=str(sections[0]["id"]), statut="relue", par="  "
        )

    # Transition interdite : brouillon → validee d'un coup.
    with pytest.raises(ErreurMemoire):
        memoire_technique.changer_statut_section(
            connexion, contexte_a, section_id=str(sections[0]["id"]),
            statut="validee", par=RELECTEUR_FICTIF,
        )

    # Chemin normal : brouillon → relue → validee, puis le dossier passe en relecture.
    for section in sections:
        memoire_technique.changer_statut_section(
            connexion, contexte_a, section_id=str(section["id"]),
            statut="relue", par=RELECTEUR_FICTIF,
        )
    dossier = memoire_technique.lire_memoire(connexion, contexte_a, consultation_id)["dossier"]
    assert dossier["statut"] == "en_relecture"

    # Validation finale : nom + fonction obligatoires.
    with pytest.raises(ErreurMemoire):
        memoire_technique.valider_dossier(
            connexion, contexte_a, dossier_id=dossier_id,
            nom_validateur="", fonction_validateur="",
        )
    validation = memoire_technique.valider_dossier(
        connexion, contexte_a, dossier_id=dossier_id,
        nom_validateur=VALIDATEUR_FICTIF, fonction_validateur="Gérant (fictif)",
    )
    assert len(validation["empreinte_contenu"]) == 64
    int(validation["empreinte_contenu"], 16)  # hexadécimal valide
    assert validation["dossier"]["statut"] == "valide"
    assert validation["validation"]["nom_validateur"] == VALIDATEUR_FICTIF

    # Une validation ne se rejoue pas.
    with pytest.raises(ErreurMemoire):
        memoire_technique.valider_dossier(
            connexion, contexte_a, dossier_id=dossier_id,
            nom_validateur=VALIDATEUR_FICTIF, fonction_validateur="Gérant (fictif)",
        )


def test_validation_refusee_si_une_section_reste_en_brouillon(connexion, contexte_a, config):
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
    with pytest.raises(ErreurMemoire) as erreur:
        memoire_technique.valider_dossier(
            connexion, contexte_a, dossier_id=dossier_id,
            nom_validateur=VALIDATEUR_FICTIF, fonction_validateur="Gérant (fictif)",
        )
    assert "brouillon" in str(erreur.value)


def test_empreinte_deterministe(connexion, contexte_a, config):
    """Deux contenus identiques donnent la même empreinte (reproductibilité)."""
    dossier = {"titre": "T"}
    sections = [{"ordre": 0, "titre": "S", "statut": "validee", "contenu": "C",
                 "critere_libelle": "Crit", "sources": [{"table_source": "cv",
                 "libelle_source": "L", "emplacement_source": "E"}]}]
    manques = [{"critere_libelle": "M", "constat": "K", "action_attendue": "A"}]
    a = memoire_technique.empreinte_contenu(dossier, sections, manques)
    b = memoire_technique.empreinte_contenu(dossier, list(sections), list(manques))
    assert a == b and len(a) == 64


# --------------------------------------------------------------------------- #
# 7. Isolation par client
# --------------------------------------------------------------------------- #
def test_isolation_par_client(connexion, contexte_a, contexte_b, config):
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

    # Le client B ne voit rien du mémoire de A.
    with pytest.raises(MemoireIntrouvable):
        memoire_technique.lire_memoire(connexion, contexte_b, consultation_id)

    # La bibliothèque de B ne doit pas alimenter le mémoire de A : on crée un élément
    # chez B et on vérifie qu'aucune source de A ne le cite.
    service_b, _, fiche_b = _bibliotheque(connexion, contexte_b, config, remplie=False)
    service_b.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche_b,
        {
            "intitule_operation": "Chantier du client B (fictif)",
            "maitre_ouvrage": "Maître d'ouvrage B (fictif)",
            "origine": "saisie_entreprise",
        },
    )
    connexion.valider()
    element_b = connexion.executer_une(
        contexte_b,
        "SELECT id FROM reference_chantier WHERE client_id = %(client_id)s "
        "ORDER BY date_creation DESC LIMIT 1;",
    )
    identifiants_a = {
        str(s["element_id"])
        for section in resultat["sections"]
        for s in section["sources"]
    }
    assert str(element_b["id"]) not in identifiants_a


def test_source_hors_client_refusee_par_le_garde_fou(connexion, contexte_a, contexte_b, config):
    """L'élément d'un autre client ne peut pas servir de source : refus explicite."""
    _, _, fiche_b = _bibliotheque(connexion, contexte_b, config, remplie=False)
    service_b = ServiceBibliotheque(
        connexion, config.cle_chiffrement_maitresse, contexte_b
    )
    service_b.saisir(
        "moyens_humains",
        "effectif_metier",
        fiche_b,
        {"metier_code": "etancheur", "metier_libelle": "Étancheur", "nombre": 3,
         "origine": "saisie_entreprise"},
    )
    connexion.valider()
    element = connexion.executer_une(
        contexte_b,
        "SELECT * FROM effectif_metier WHERE client_id = %(client_id)s "
        "ORDER BY date_creation DESC LIMIT 1;",
    )
    candidats, pages, confiances = memoire_technique._candidats_pour_familles(
        ["moyens_humains"], {"moyens_humains": {"effectif_metier": [element]}}
    )
    with pytest.raises(SourceMemoireInvalide):
        memoire_technique.verifier_sources(
            candidats, pages, identifiants_autorises={str(uuid.uuid4())}
        )


# --------------------------------------------------------------------------- #
# 8. Ligne rouge : aucun prix, aucune conformité promise
# --------------------------------------------------------------------------- #
def test_aucun_prix_ni_conformite_dans_le_memoire(connexion, contexte_a, config):
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
    texte = " ".join(str(s["contenu"]) for s in resultat["sections"]).casefold()
    assert "conforme" not in texte
    assert "garanti" not in texte
    # Aucune section ne parle du prix : le critère « prix » n'en produit pas. Le mot
    # n'apparaît qu'une fois, dans l'avertissement « aucun prix n'est fixé ».
    for section in resultat["sections"]:
        assert "prix" not in str(section["titre"]).casefold()
    assert "aucun prix n'est fixé" in texte
    assert texte.count("prix") == texte.count("aucun prix n'est fixé")


# --------------------------------------------------------------------------- #
# 9. Parcours API `/api/v1`
# --------------------------------------------------------------------------- #
def _client_api(connexion, contexte, config, identifiant: str = "memoire@fictif.test") -> TestClient:
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, "Utilisateur fictif (démonstration)", MOT_DE_PASSE_FICTIF)
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def test_routes_memoire_refusent_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/consultations/x/memoire").status_code == 401
        assert client.post("/api/v1/consultations/x/memoire").status_code == 401
        assert client.post("/api/v1/memoire/sections/x").status_code == 401
        assert client.post("/api/v1/memoire/x/validation").status_code == 401


def test_parcours_api_memoire_complet(connexion, contexte_a, config):
    _, _, fiche_id, consultation_id = _preparer_dce_et_bibliotheque(
        connexion, contexte_a, config
    )
    client = _client_api(connexion, contexte_a, config)
    try:
        creation = client.post(
            f"/api/v1/consultations/{consultation_id}/memoire",
            json={"fiche_version_id": fiche_id},
        )
        assert creation.status_code == 201, creation.text
        corps = creation.json()
        assert corps["dossier"]["statut"] == "brouillon"
        assert corps["sections"]
        dossier_id = corps["dossier"]["id"]

        lecture = client.get(f"/api/v1/consultations/{consultation_id}/memoire")
        assert lecture.status_code == 200
        assert lecture.json()["dossier"]["id"] == dossier_id

        for section in corps["sections"]:
            relu = client.post(
                f"/api/v1/memoire/sections/{section['id']}",
                json={"statut": "relue", "par": RELECTEUR_FICTIF},
            )
            assert relu.status_code == 200, relu.text

        refus = client.post(
            f"/api/v1/memoire/{dossier_id}/validation",
            json={"nom_validateur": "", "fonction_validateur": ""},
        )
        assert refus.status_code == 400

        validation = client.post(
            f"/api/v1/memoire/{dossier_id}/validation",
            json={"nom_validateur": VALIDATEUR_FICTIF, "fonction_validateur": "Gérant (fictif)"},
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["dossier"]["statut"] == "valide"
        assert len(validation.json()["empreinte_contenu"]) == 64
    finally:
        client.__exit__(None, None, None)


def test_route_generation_refusee_sans_critere_valide(connexion, contexte_a, config):
    """Générer avant d'avoir validé les critères est un refus explicite (400)."""
    _, entreprise_id, _ = _bibliotheque(connexion, contexte_a, config, remplie=True)
    resultat = _deposer_dce(connexion, contexte_a, config, entreprise_id)
    consultation_id = str(resultat.consultation["id"])
    client = _client_api(connexion, contexte_a, config, identifiant="memoire2@fictif.test")
    try:
        reponse = client.post(f"/api/v1/consultations/{consultation_id}/memoire", json={})
        assert reponse.status_code == 400, reponse.text
        assert "critère" in reponse.json()["detail"].casefold()
    finally:
        client.__exit__(None, None, None)
