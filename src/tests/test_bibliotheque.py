"""Tests de la bibliothèque d'entreprise (lot L2) — exécutés réellement.

Aucune donnée réelle : tous les noms, identifiants, IBAN et montants de ce fichier
sont **FICTIFS et signalés** (« DOCUMENT FICTIF — DÉMONSTRATION »).

Ce que ces tests démontrent, exigence par exigence :

1. la migration `0002` est appliquée et les tables des familles F1 à F9 existent ;
2. une fiche se saisit sur **plusieurs familles**, avec sa traçabilité ;
3. **aucune valeur sans `origine`** ; `origine` n'accepte que `document_extrait` ou
   `saisie_entreprise` ; une valeur sans source est `a_verifier`, jamais `verifie` ;
4. les champs du registre sensible sont **chiffrés par client** ;
5. un second client ne peut ni lire ni déchiffrer les données du premier ;
6. les routes gelées de l'annexe C répondent (avec session) et refusent sans session.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.config import charger_config
from app.domain.familles import FAMILLE_VERS_ENTITES
from app.securite.chiffrement import ErreurDechiffrement, dechiffrer
from app.services.authentification import ServiceAuthentification
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.versionnement import CibleInconnue
from app.storage.connexion import Connexion, ContexteClient
from app.storage.repositories import DepotDocument

# --------------------------------------------------------------------------- #
# Jeux de données FICTIFS — jamais des données d'entreprise réelles
# --------------------------------------------------------------------------- #

MENTION = "DOCUMENT FICTIF — DÉMONSTRATION"
RAISON_SOCIALE_FICTIVE = "Étanchéité Exemple SARL (fictive)"
SIREN_FICTIF = "000000000"
SIRET_FICTIF = "00000000000000"
IBAN_FICTIF = "FR0000000000000000000000000"
MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"

FICHE_IDENTITE = {
    "origine": "saisie_entreprise",
    "confiance": "declare_non_verifie",
    "raison_sociale": RAISON_SOCIALE_FICTIVE,
    "siren": SIREN_FICTIF,
    "siret_siege": SIRET_FICTIF,
    "forme_juridique_code": "SARL",  # jeu non chargé : accepté tel quel
    "adresse_siege": "1 rue de la Démonstration, 00000 Ville Fictive",
    "iban": IBAN_FICTIF,
    "effectif": 12,
    "date_effectif": "2026-01-01",
}


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #


def _service(connexion: Connexion, contexte: ContexteClient) -> ServiceBibliotheque:
    config = charger_config()
    return ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)


def _preparer_fiche(
    connexion: Connexion, contexte: ContexteClient, libelle: str = "Entreprise fictive — A"
) -> tuple[ServiceBibliotheque, str, str]:
    """Crée une entreprise (fictive) et sa première version de fiche. Renvoie (service, entreprise, fiche)."""
    service = _service(connexion, contexte)
    entreprise_id = service.creer_entreprise(f"{libelle} — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id, commentaire="Jeu de démonstration fictif")
    connexion.valider()
    return service, entreprise_id, str(fiche["id"])


def _document_source(
    connexion: Connexion,
    contexte: ContexteClient,
    entreprise_id: str,
    fiche_version_id: str,
    libelle: str = "Attestation fictive de démonstration",
) -> str:
    depot = DepotDocument(connexion, charger_config().cle_chiffrement_maitresse)
    document_id = depot.creer(
        contexte,
        entreprise_id=entreprise_id,
        fiche_version_id=fiche_version_id,
        type_document="attestation_assurance",
        libelle=f"{libelle} — {MENTION}",
        chemin_stockage=f"clients/{contexte.client_id}/{uuid.uuid4()}.bin",
        deposant="entreprise",
    )
    connexion.valider()
    return document_id


# --------------------------------------------------------------------------- #
# 1. Migration 0002 — structures présentes
# --------------------------------------------------------------------------- #
def test_migration_0002_cree_les_tables_des_neuf_familles(connexion_admin, base_migree):
    attendues = (
        "entreprise_version",
        "representant_legal",
        "exercice_comptable",
        "attestation",
        "capacite_production",
        "assurance",
        "certification",
        "reference_chantier",
        "effectif_metier",
        "organigramme",
        "cv",
        "moyen_materiel",
        "produit",
        "chapitre_memoire",
        "reference_chantier_photo",
        "produit_certificat",
        "chapitre_memoire_reference",
        "chapitre_memoire_document",
    )
    for table in attendues:
        lignes = connexion_admin.lire(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table,),
        )
        assert lignes, f"table manquante après la migration 0002 : {table}"


def test_jeux_de_reference_fermes_charges_par_0002(connexion_admin, base_migree):
    jeux = connexion_admin.lire(
        "SELECT namespace FROM jeu_reference WHERE namespace LIKE 'fiche.%%' ORDER BY namespace;"
    )
    noms = [ligne[0] for ligne in jeux]
    assert "fiche.famille" in noms
    assert "fiche.statut_version" in noms

    familles = connexion_admin.lire(
        "SELECT code FROM valeur_reference WHERE namespace = 'fiche.famille' ORDER BY ordre;"
    )
    assert [ligne[0] for ligne in familles] == list(FAMILLE_VERS_ENTITES)

    statuts = connexion_admin.lire(
        "SELECT code FROM valeur_reference WHERE namespace = 'fiche.statut_version';"
    )
    assert len([ligne for ligne in statuts]) == 7


# --------------------------------------------------------------------------- #
# 2. Saisie sur plusieurs familles + traçabilité
# --------------------------------------------------------------------------- #
def test_saisie_sur_plusieurs_familles(connexion, contexte_a):
    service, entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    document_id = _document_source(connexion, contexte_a, entreprise_id, fiche)

    # F1 — identité
    identite = service.saisir("identite", "entreprise_version", fiche, dict(FICHE_IDENTITE))
    connexion.valider()
    assert identite["element_id"]

    # F3 — assurance, valeur LUE dans un document (origine document_extrait)
    assurance = service.saisir(
        "assurances",
        "assurance",
        fiche,
        {
            "origine": "document_extrait",
            "confiance": "a_verifier",
            "source_document_id": document_id,
            "type_assurance": "decennale",  # jeu non chargé : accepté tel quel
            "assureur": "Assureur Fictif SA — DOCUMENT FICTIF",
            "date_debut": "2026-01-01",
            "date_echeance": "2027-01-01",
            "piece": document_id,
        },
    )
    connexion.valider()

    # F5 — référence de chantier, avec une liste de photos (table de liaison)
    chantier = service.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche,
        {
            "origine": "saisie_entreprise",
            "confiance": "declare_non_verifie",
            "intitule_operation": "Réfection d'étanchéité — chantier fictif de démonstration",
            "maitre_ouvrage": "Collectivité fictive",
            "montant": {"valeur": "1234.56", "devise": "EUR"},
            "photos": [document_id],
        },
    )
    connexion.valider()

    contenu = service.consulter_famille("references_chantiers", fiche)
    elements = contenu["elements"]["reference_chantier"]
    assert len(elements) == 1
    ligne = elements[0]
    assert ligne["origine"] == "saisie_entreprise"
    assert ligne["confiance"] == "declare_non_verifie"
    assert str(ligne["montant_montant"]) == "1234.56"
    assert ligne["montant_devise"] == "EUR"
    assert ligne["photos"] == [document_id]

    avancement = service.etat_avancement(fiche)
    familles_remplies = {f["famille"] for f in avancement["familles"] if f["nb_elements"] > 0}
    assert familles_remplies == {"identite", "assurances", "references_chantiers"}
    assert avancement["familles"][0]["completude_famille"] == "complete"
    assert assurance["element_id"] and chantier["element_id"]


def test_identite_est_unique_par_fiche(connexion, contexte_a):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    premier = service.saisir("identite", "entreprise_version", fiche, dict(FICHE_IDENTITE))
    connexion.valider()
    second = service.saisir(
        "identite",
        "entreprise_version",
        fiche,
        {**FICHE_IDENTITE, "raison_sociale": RAISON_SOCIALE_FICTIVE + " (corrigée)"},
    )
    connexion.valider()
    assert premier["element_id"] == second["element_id"]
    identites = service.consulter_famille("identite", fiche)["elements"]["entreprise_version"]
    assert len(identites) == 1


# --------------------------------------------------------------------------- #
# 3. Exigence 5 — origine obligatoire, confiance bornée, jamais « verifie » sans source
# --------------------------------------------------------------------------- #
def test_origine_obligatoire(connexion, contexte_a):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    donnees = dict(FICHE_IDENTITE)
    donnees.pop("origine")
    with pytest.raises(ErreurBibliotheque) as exc:
        service.saisir("identite", "entreprise_version", fiche, donnees)
    assert "origine" in str(exc.value)


@pytest.mark.parametrize("origine_refusee", ["genere_ia", "ia", "propose", ""])
def test_origine_refusee(connexion, contexte_a, origine_refusee):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    donnees = {**FICHE_IDENTITE, "origine": origine_refusee}
    with pytest.raises(ErreurBibliotheque):
        service.saisir("identite", "entreprise_version", fiche, donnees)


def test_document_extrait_exige_un_document_source(connexion, contexte_a):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    donnees = {**FICHE_IDENTITE, "origine": "document_extrait", "confiance": "a_verifier"}
    with pytest.raises(ErreurBibliotheque) as exc:
        service.saisir("identite", "entreprise_version", fiche, donnees)
    assert "document_extrait" in str(exc.value)


def test_valeur_sans_source_nest_jamais_verifiee(connexion, contexte_a):
    """Exigence 5 : sans source, `verifie` est refusé ; la confiance retombe sur `a_verifier`."""
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    with pytest.raises(ErreurBibliotheque) as exc:
        service.saisir(
            "identite",
            "entreprise_version",
            fiche,
            {**FICHE_IDENTITE, "confiance": "verifie"},
        )
    assert "verifie" in str(exc.value)

    # Sans confiance demandée, une saisie sans source est enregistrée « a_verifier ».
    resultat = service.saisir(
        "identite",
        "entreprise_version",
        fiche,
        {**FICHE_IDENTITE, "confiance": "a_verifier"},
    )
    connexion.valider()
    ligne = service.consulter_famille("identite", fiche)["elements"]["entreprise_version"][0]
    assert ligne["confiance"] == "a_verifier"
    assert ligne["source_document_id"] is None
    assert resultat["statut_fiche"] in {"en_saisie", "socle_complet"}


def test_verifie_exige_un_controle_humain_nomme(connexion, contexte_a):
    service, entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    document_id = _document_source(connexion, contexte_a, entreprise_id, fiche)
    donnees = {
        **FICHE_IDENTITE,
        "origine": "document_extrait",
        "confiance": "verifie",
        "source_document_id": document_id,
    }
    # Avec une source mais sans humain : refusé.
    with pytest.raises(ErreurBibliotheque):
        service.saisir("identite", "entreprise_version", fiche, donnees)

    # Avec la source ET un humain nommé : accepté, et c'est le seul chemin.
    resultat = service.saisir(
        "identite",
        "entreprise_version",
        fiche,
        donnees,
        controle_humain_par="Relecteur Fictif — DÉMONSTRATION",
    )
    connexion.valider()
    assert resultat["element_id"]
    ligne = service.consulter_famille("identite", fiche)["elements"]["entreprise_version"][0]
    assert ligne["confiance"] == "verifie"


def test_code_reference_controle_si_le_jeu_est_charge(connexion, contexte_a):
    """Un jeu **chargé** est contrôlé ; un jeu non chargé n'est pas inventé."""
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    base = {
        "origine": "saisie_entreprise",
        "categorie_code": "engins",  # jeu moyen.categorie NON chargé : accepté
        "designation": "Camion-grue fictif de démonstration",
        "quantite": 2,
    }
    service.saisir("moyens_materiels", "moyen_materiel", fiche, dict(base))
    connexion.valider()

    # `moyen.propriete` est un jeu fermé, chargé par la migration 0002.
    service.saisir(
        "moyens_materiels", "moyen_materiel", fiche, {**base, "propriete": "propre"}
    )
    connexion.valider()
    with pytest.raises(ErreurBibliotheque) as exc:
        service.saisir(
            "moyens_materiels", "moyen_materiel", fiche, {**base, "propriete": "inventee"}
        )
    assert "moyen.propriete" in str(exc.value)


def test_colonne_inconnue_refusee(connexion, contexte_a):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    with pytest.raises(Exception) as exc:
        service.saisir(
            "identite", "entreprise_version", fiche, {**FICHE_IDENTITE, "prix": "1000"}
        )
    assert "prix" in str(exc.value)


# --------------------------------------------------------------------------- #
# 4. Chiffrement par client des champs du registre sensible
# --------------------------------------------------------------------------- #
def test_champs_sensibles_chiffres_en_base(connexion, connexion_admin, contexte_a):
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    service.saisir("identite", "entreprise_version", fiche, dict(FICHE_IDENTITE))
    connexion.valider()

    lignes = connexion_admin.lire(
        "SELECT iban, siret_siege FROM entreprise_version WHERE client_id = %s;",
        (contexte_a.client_id,),
    )
    assert len(lignes) == 1
    iban_stocke, siret_stocke = lignes[0]
    assert iban_stocke.startswith("v1:")
    assert IBAN_FICTIF not in iban_stocke
    assert SIRET_FICTIF not in siret_stocke

    # Le client propriétaire, lui, relit la valeur en clair.
    ligne = service.consulter_famille("identite", fiche)["elements"]["entreprise_version"][0]
    assert ligne["iban"] == IBAN_FICTIF
    assert ligne["siret_siege"] == SIRET_FICTIF


def test_second_client_ne_peut_pas_dechiffrer(
    connexion, connexion_admin, contexte_a, client_b, cle_maitresse
):
    """Exigence 4 : test de non-déchiffrement croisé."""
    service, _, fiche = _preparer_fiche(connexion, contexte_a)
    service.saisir("identite", "entreprise_version", fiche, dict(FICHE_IDENTITE))
    connexion.valider()

    iban_stocke = connexion_admin.lire(
        "SELECT iban FROM entreprise_version WHERE client_id = %s;", (contexte_a.client_id,)
    )[0][0]
    with pytest.raises(ErreurDechiffrement):
        dechiffrer(cle_maitresse, client_b, iban_stocke)


# --------------------------------------------------------------------------- #
# 5. Cloisonnement — un second client ne lit rien du premier
# --------------------------------------------------------------------------- #
def test_second_client_ne_peut_pas_lire_la_fiche_du_premier(connexion, contexte_a, contexte_b):
    service_a, _, fiche_a = _preparer_fiche(connexion, contexte_a, "Entreprise fictive — A")
    service_a.saisir("identite", "entreprise_version", fiche_a, dict(FICHE_IDENTITE))
    connexion.valider()

    with pytest.raises(CibleInconnue):
        service_b = _service(connexion, contexte_b)
        service_b.consulter_famille("identite", fiche_a)


def test_second_client_ne_voit_aucun_element(connexion, contexte_a, contexte_b):
    service_a, _, fiche_a = _preparer_fiche(connexion, contexte_a, "Entreprise fictive — A")
    service_a.saisir("identite", "entreprise_version", fiche_a, dict(FICHE_IDENTITE))
    connexion.valider()
    # B n'a aucune fiche : aucun élément ne lui est visible.
    service_b = _service(connexion, contexte_b)
    assert service_b.fiche_courante() is None


# --------------------------------------------------------------------------- #
# 6. Statut de validité — calculé, jamais stocké
# --------------------------------------------------------------------------- #
def test_statut_validite_calcule_a_la_lecture(connexion, contexte_a):
    service, entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    document_id = _document_source(connexion, contexte_a, entreprise_id, fiche)
    passe = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    futur = (dt.date.today() + dt.timedelta(days=400)).isoformat()

    service.saisir(
        "assurances",
        "assurance",
        fiche,
        {
            "origine": "document_extrait",
            "source_document_id": document_id,
            "type_assurance": "decennale",
            "assureur": "Assureur Fictif SA",
            "date_debut": "2024-01-01",
            "date_echeance": passe,
            "piece": document_id,
        },
    )
    service.saisir(
        "certifications",
        "certification",
        fiche,
        {
            "origine": "document_extrait",
            "source_document_id": document_id,
            "intitule": "Certification fictive de démonstration",
            "organisme": "Organisme fictif",
            "domaine_code": "etancheite",
            "date_echeance": futur,
            "piece": document_id,
        },
    )
    connexion.valider()

    assurances = service.consulter_famille("assurances", fiche)["elements"]["assurance"]
    assert assurances[0]["statut_validite"] == "expire"
    certifications = service.consulter_famille("certifications", fiche)["elements"][
        "certification"
    ]
    assert certifications[0]["statut_validite"] == "valide"

    # Aucun seuil en dur : sans réglage de fenêtre, `echeance_proche` n'est jamais produit.
    contenu = service.consulter_famille("assurances", fiche)
    assert contenu["fenetre_alerte_jours"] is None


# --------------------------------------------------------------------------- #
# 7. Routes gelées de l'annexe C (avec et sans session)
# --------------------------------------------------------------------------- #
def _client_api(connexion, contexte, config, identifiant: str = "bib@fictif.test") -> TestClient:
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, "Relecteur Fictif", MOT_DE_PASSE_FICTIF)
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def test_routes_bibliotheque_refusent_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/bibliotheque").status_code == 401
        assert client.get("/api/v1/bibliotheque/assurances").status_code == 401
        assert (
            client.post("/api/v1/bibliotheque/assurances", json={"entite": "x", "donnees": {}}).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/bibliotheque/validation",
                json={"fiche_version_id": "x", "relecteur_nom": "y", "attestation_cochee": True},
            ).status_code
            == 401
        )


def test_routes_bibliotheque_parcours_complet(connexion, contexte_a, config):
    service, entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    document_id = _document_source(connexion, contexte_a, entreprise_id, fiche)
    client = _client_api(connexion, contexte_a, config)
    try:
        # État initial : la fiche existe mais est vierge.
        etat = client.get("/api/v1/bibliotheque")
        assert etat.status_code == 200
        assert etat.json()["statut"] == "vierge"

        # Saisie d'une assurance via la route gelée.
        reponse = client.post(
            "/api/v1/bibliotheque/assurances",
            json={
                "entite": "assurance",
                "donnees": {
                    "origine": "document_extrait",
                    "source_document_id": document_id,
                    "type_assurance": "decennale",
                    "assureur": "Assureur Fictif SA",
                    "date_debut": "2026-01-01",
                    "date_echeance": "2027-01-01",
                    "piece": document_id,
                },
            },
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["element_id"]

        # Lecture : chaque valeur porte son origine et sa confiance.
        lecture = client.get("/api/v1/bibliotheque/assurances")
        assert lecture.status_code == 200
        corps = lecture.json()
        assert corps["famille"] == "assurances"
        element = corps["elements"]["assurance"][0]
        assert element["origine"] == "document_extrait"
        assert element["confiance"] == "a_verifier"
        assert str(element["source_document_id"]) == document_id
        assert element["statut_validite"] == "valide"

        # Validation humaine : sans le nom du relecteur, refusée.
        sans_nom = client.post(
            "/api/v1/bibliotheque/validation",
            json={"fiche_version_id": fiche, "relecteur_nom": "", "attestation_cochee": True},
        )
        assert sans_nom.status_code == 422  # champ obligatoire (pydantic)

        # Sans attestation cochée, refusée aussi.
        sans_attestation = client.post(
            "/api/v1/bibliotheque/validation",
            json={
                "fiche_version_id": fiche,
                "relecteur_nom": "Relecteur Fictif",
                "attestation_cochee": False,
            },
        )
        assert sans_attestation.status_code == 400

        validee = client.post(
            "/api/v1/bibliotheque/validation",
            json={
                "fiche_version_id": fiche,
                "relecteur_nom": "Relecteur Fictif — DÉMONSTRATION",
                "attestation_cochee": True,
                "commentaire": "Relecture de démonstration",
            },
        )
        assert validee.status_code == 200, validee.text
        assert validee.json()["statut"] == "validee"

        # Famille inconnue : 404 explicite.
        assert client.get("/api/v1/bibliotheque/famille_inexistante").status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_la_saisie_par_route_revoque_la_validation(connexion, contexte_a, config):
    service, entreprise_id, fiche = _preparer_fiche(connexion, contexte_a)
    document_id = _document_source(connexion, contexte_a, entreprise_id, fiche)
    service.saisir(
        "identite",
        "entreprise_version",
        fiche,
        {**FICHE_IDENTITE, "origine": "document_extrait", "source_document_id": document_id},
    )
    service.valider_fiche(
        fiche,
        relecteur_nom="Relecteur Fictif — DÉMONSTRATION",
        attestation_cochee=True,
    )
    connexion.valider()

    client = _client_api(connexion, contexte_a, config, identifiant="bib2@fictif.test")
    try:
        reponse = client.post(
            "/api/v1/bibliotheque/identite",
            json={
                "entite": "entreprise_version",
                "donnees": {
                    **FICHE_IDENTITE,
                    "origine": "saisie_entreprise",
                    "confiance": "declare_non_verifie",
                    "telephone": "0000000000",  # numéro FICTIF de démonstration
                },
            },
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["validations_revoquees"]
        assert reponse.json()["statut_fiche"] == "en_relecture"
    finally:
        client.__exit__(None, None, None)
