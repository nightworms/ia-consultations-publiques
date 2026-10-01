"""Tests du lot L3 (phase 4) — import guidé de documents dans la bibliothèque.

Aucune donnée réelle : les documents employés sont **fictifs et signalés**
(mention « DOCUMENT FICTIF — DÉMONSTRATION », décision D10). Aucun appel réseau :
le fournisseur employé est le `FournisseurFactice` (défaut), ou un faux fournisseur
défini dans ce fichier pour exercer le garde-fou de source.

Exigences vérifiables du lot, démontrées par exécution :

1. migration `0006` : `up` puis `down` (tables créées, puis retirées) ;
2. un document `.txt` et un `.pdf` fictifs déposés produisent des propositions
   **sourcées** (`source_emplacement` et `source_extrait` renseignés) ;
3. un format refusé l'est **explicitement** (message qui dit quoi faire) ;
4. une proposition sans source vérifiable est **refusée** et rien n'est enregistré ;
5. une proposition acceptée écrit un élément de bibliothèque `origine =
   document_extrait`, `confiance = a_verifier`, `source_document_id` renseigné, **via
   le service de bibliothèque** ; une proposition refusée n'écrit rien ;
6. aucune décision sans humain nommé ;
7. isolation par `client_id` : un client ne voit pas les imports d'un autre ;
8. l'état d'avancement utile dit **ce qui manque**, famille par famille.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.cloisonnement import NOM_COOKIE_SESSION
from app.config import charger_config
from app.services import import_guide
from app.services.analyse_dce import ErreurAnalyseDce
from app.services.authentification import ServiceAuthentification
from app.services.bibliotheque import ServiceBibliotheque
from app.services.fournisseur_modele import FournisseurModele
from app.services.fournisseur_modele.base import PropositionImport
from app.services.import_guide import (
    ErreurImportGuide,
    ImportIntrouvable,
    ImportNonValidable,
)
from app.storage.connexion import (
    Connexion,
    ConnexionAdministration,
    ContexteClient,
)
from app.storage.fichiers import StockageFichiers
from app.storage.migrations import ExecuteurMigrations, lister_migrations

from fixtures.generer_fixtures import ecrire_pdf_texte

MOT_DE_PASSE_FICTIF = "MotDePasseFictif!2026"  # fictif — jamais un mot de passe réel
MENTION_FICTIF = "DOCUMENT FICTIF — DÉMONSTRATION — AUCUNE DONNÉE RÉELLE"
DECIDEUR_FICTIF = "Décideur fictif (démonstration)"


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def _stockage(config) -> StockageFichiers:
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _preparer_fiche(connexion: Connexion, contexte: ContexteClient, config):
    """Entreprise + fiche fictives, prêtes à recevoir un import."""
    service = ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)
    entreprise_id = service.creer_entreprise("Entreprise fictive — DÉMONSTRATION")
    fiche = service.ouvrir_fiche(entreprise_id)
    connexion.valider()
    return service, entreprise_id, str(fiche["id"])


def _document_assurance(date_echeance: _dt.date) -> bytes:
    """Document texte fictif décrivant une assurance (règles de lecture du factice)."""
    return (
        f"{MENTION_FICTIF}\n\n"
        "Attestation d'assurance responsabilité décennale (fictive)\n\n"
        "Entité : assurance\n"
        "- type_assurance : responsabilite_decennale\n"
        "- assureur : Assureur Fictif SA\n"
        "- numero_contrat : FICTIF-2026-001\n"
        "- montant_garantie_montant : 1500000\n"
        "- montant_garantie_devise : EUR\n"
        "- date_debut : 2026-01-01\n"
        f"- date_echeance : {date_echeance.isoformat()}\n"
    ).encode("utf-8")


def _importer_document_assurance(
    connexion, contexte, config, fiche, *, date_echeance=None, fournisseur=None
):
    return import_guide.importer_document(
        connexion,
        contexte,
        _stockage(config),
        fiche_version_id=fiche,
        famille_cible="assurances",
        nom_fichier="attestation_assurance_fictive.txt",
        contenu=_document_assurance(date_echeance or _dt.date.today() + _dt.timedelta(days=365)),
        type_mime="text/plain",
        fournisseur=fournisseur,
    )


def _table_existe(conn: ConnexionAdministration, nom: str) -> bool:
    return bool(
        conn.lire(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (nom,),
        )
    )


@pytest.fixture(scope="module")
def pdf_assurance_fictive(tmp_path_factory) -> Path:
    """PDF fictif à lire : une entité `assurance` et ses champs, sans réseau."""
    dossier = tmp_path_factory.mktemp("import_guide_fixture")
    chemin = dossier / "attestation_fictive.pdf"
    texte = (
        f"{MENTION_FICTIF}\n\n"
        "Entité : assurance\n"
        "- type_assurance : responsabilite_civile\n"
        "- assureur : Assureur Fictif PDF\n"
        "- date_debut : 2026-01-01\n"
        "- date_echeance : 2027-01-01\n"
    )
    ecrire_pdf_texte(texte, chemin)
    return chemin


# --------------------------------------------------------------------------- #
# 1. Migration 0006 : up puis down
# --------------------------------------------------------------------------- #
def test_migration_0006_presente_et_reversible(connexion_admin, base_migree):
    numeros = [m.numero for m in lister_migrations()]
    assert "0006" in numeros
    migration = next(m for m in lister_migrations() if m.numero == "0006")
    assert migration.nom == "0006_import_guide"
    assert migration.sql_up and migration.sql_down

    executeur = ExecuteurMigrations(charger_config().database_url)
    assert _table_existe(connexion_admin, "import_document")
    assert _table_existe(connexion_admin, "import_proposition")

    # On annule toutes les migrations postérieures à 0005, puis on remonte : la
    # migration doit être réversible (aucune table existante n'est perdue).
    apres_0005 = [m.numero for m in lister_migrations() if m.numero > "0005"]
    annulees = executeur.down(len(apres_0005))
    assert "0006" in annulees
    assert not _table_existe(connexion_admin, "import_document")
    assert not _table_existe(connexion_admin, "import_proposition")
    # Aucune table existante n'a été détruite par l'annulation.
    assert _table_existe(connexion_admin, "assurance")
    assert _table_existe(connexion_admin, "document")

    reappliquees = executeur.up()
    assert set(reappliquees) == set(annulees)
    assert _table_existe(connexion_admin, "import_document")
    assert _table_existe(connexion_admin, "import_proposition")


# --------------------------------------------------------------------------- #
# 2. Format refusé explicitement
# --------------------------------------------------------------------------- #
def test_format_refuse_explicitement(connexion, contexte_a, config, tmp_path):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    with pytest.raises(ErreurImportGuide) as erreur:
        import_guide.importer_document(
            connexion,
            contexte_a,
            _stockage(config),
            fiche_version_id=fiche,
            famille_cible="assurances",
            nom_fichier="ancien_memoire.docx",
            contenu=b"PK\x03\x04 fake docx",
            type_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    message = str(erreur.value)
    assert "Format refusé" in message
    assert ".pdf" in message and ".txt" in message  # dit quoi faire
    # Rien n'a été enregistré.
    assert import_guide.lister_imports(connexion, contexte_a) == []


def test_fichier_vide_refuse(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    with pytest.raises(ErreurImportGuide):
        import_guide.importer_document(
            connexion,
            contexte_a,
            _stockage(config),
            fiche_version_id=fiche,
            famille_cible="assurances",
            nom_fichier="vide.txt",
            contenu=b"",
            type_mime="text/plain",
        )


def test_famille_cible_inconnue_refusee(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    with pytest.raises(ErreurImportGuide):
        import_guide.importer_document(
            connexion,
            contexte_a,
            _stockage(config),
            fiche_version_id=fiche,
            famille_cible="famille_inexistante",
            nom_fichier="x.txt",
            contenu=_document_assurance(_dt.date.today()),
            type_mime="text/plain",
        )


# --------------------------------------------------------------------------- #
# 3. Dépôt .txt : propositions sourcées, en attente de décision
# --------------------------------------------------------------------------- #
def test_depot_txt_produit_des_propositions_sourcees(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer_document_assurance(connexion, contexte_a, config, fiche)

    assert resultat.import_document["statut"] == "traite"
    assert resultat.fournisseur == "factice"
    assert resultat.propositions, "le document fictif doit produire une proposition"

    proposition = resultat.propositions[0]
    assert proposition["entite_cible"] == "assurance"
    assert proposition["famille"] == "assurances"
    assert proposition["statut"] == "propose"
    assert proposition["source_emplacement"]
    assert "date_echeance" in proposition["champs_proposes"]
    assert proposition["decide_par"] is None and proposition["date_decision"] is None

    # L'extrait invoqué se retrouve littéralement dans le document extrait.
    from app.services.analyse_dce import extraire_document
    import tempfile

    contenu = _stockage(config).lire(contexte_a.client_id, str(resultat.document["id"]))
    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / "doc.txt"
        chemin.write_bytes(contenu)
        extraction = extraire_document(chemin)
    aplatir = " ".join(str(proposition["source_extrait"]).split())
    assert aplatir in " ".join(extraction.texte_complet.split())


def test_depot_pdf_fictif_produit_des_propositions(connexion, contexte_a, config, pdf_assurance_fictive):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = import_guide.importer_document(
        connexion,
        contexte_a,
        _stockage(config),
        fiche_version_id=fiche,
        famille_cible="assurances",
        nom_fichier=pdf_assurance_fictive.name,
        contenu=pdf_assurance_fictive.read_bytes(),
        type_mime="application/pdf",
    )
    assert resultat.fichier_illisible is False
    assert resultat.propositions, "un PDF textuel fictif doit produire une proposition"
    assert resultat.propositions[0]["entite_cible"] == "assurance"


# --------------------------------------------------------------------------- #
# 4. Garde-fou de source : une proposition inventée est refusée
# --------------------------------------------------------------------------- #
class FournisseurSansSource(FournisseurModele):
    """Faux fournisseur qui invente un extrait absent du document (test du refus)."""

    nom = "faux-sans-source"
    modele = "test"

    def analyser(self, extraction):  # pragma: no cover — non exercé ici
        raise NotImplementedError

    def proposer_elements(self, extraction, *, famille_cible):
        return (
            PropositionImport(
                entite_cible="assurance",
                champs_proposes={"assureur": "Assureur Inventé"},
                source_emplacement="page 1",
                source_extrait="cette phrase ne figure pas dans le document",
            ),
        )


def test_proposition_sans_source_refusee_et_rien_enregistre(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    with pytest.raises(ImportNonValidable):
        _importer_document_assurance(
            connexion, contexte_a, config, fiche, fournisseur=FournisseurSansSource()
        )
    # Dépôt annulé : ni import, ni proposition, ni document rattaché.
    assert import_guide.lister_imports(connexion, contexte_a) == []
    restes = connexion.executer(
        contexte_a,
        "SELECT id FROM import_proposition WHERE client_id = %(client_id)s;",
    )
    assert restes == []


def test_champ_hors_registre_refuse(connexion, contexte_a, config):
    class FournisseurChampInconnu(FournisseurModele):
        nom = "faux-champ-inconnu"
        modele = "test"

        def analyser(self, extraction):  # pragma: no cover
            raise NotImplementedError

        def proposer_elements(self, extraction, *, famille_cible):
            return (
                PropositionImport(
                    entite_cible="assurance",
                    champs_proposes={"champ_inexistant": "valeur"},
                    source_emplacement="page 1 — entité « assurance »",
                    source_extrait="Entité : assurance",
                ),
            )

    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    contenu = f"{MENTION_FICTIF}\n\nEntité : assurance\n- assureur : Fictif\n".encode("utf-8")
    with pytest.raises(ImportNonValidable):
        import_guide.importer_document(
            connexion,
            contexte_a,
            _stockage(config),
            fiche_version_id=fiche,
            famille_cible="assurances",
            nom_fichier="x.txt",
            contenu=contenu,
            type_mime="text/plain",
            fournisseur=FournisseurChampInconnu(),
        )
    assert import_guide.lister_imports(connexion, contexte_a) == []


# --------------------------------------------------------------------------- #
# 5. Décision humaine : acceptation écrit en bibliothèque, refus n'écrit rien
# --------------------------------------------------------------------------- #
def test_accepter_ecrit_un_element_de_bibliotheque(connexion, contexte_a, config):
    service, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer_document_assurance(connexion, contexte_a, config, fiche)
    proposition = resultat.propositions[0]

    decision = import_guide.decider_proposition(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        proposition_id=str(proposition["id"]),
        decision="accepter",
        decide_par=DECIDEUR_FICTIF,
    )
    assert decision["proposition"]["statut"] == "acceptee"
    assert decision["proposition"]["decide_par"] == DECIDEUR_FICTIF
    assert decision["proposition"]["date_decision"] is not None
    assert decision["element_id"]

    # L'élément est bien en bibliothèque, avec la traçabilité attendue.
    elements = service.consulter_famille("assurances", fiche)["elements"]["assurance"]
    assert len(elements) == 1
    element = elements[0]
    assert element["origine"] == "document_extrait"
    assert element["confiance"] == "a_verifier"
    assert str(element["source_document_id"]) == str(resultat.document["id"])
    # La pièce justificative est le document importé lui-même (lien, jamais inventé).
    assert str(element["piece"]) == str(resultat.document["id"])
    assert element["assureur"] == "Assureur Fictif SA"

    # Un second refus de la même proposition ne se rejoue pas.
    with pytest.raises(ErreurImportGuide):
        import_guide.decider_proposition(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte_a,
            proposition_id=str(proposition["id"]),
            decision="refuser",
            decide_par=DECIDEUR_FICTIF,
        )


def test_refuser_n_ecrit_aucun_element(connexion, contexte_a, config):
    service, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer_document_assurance(connexion, contexte_a, config, fiche)
    proposition = resultat.propositions[0]

    decision = import_guide.decider_proposition(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        proposition_id=str(proposition["id"]),
        decision="refuser",
        decide_par=DECIDEUR_FICTIF,
    )
    assert decision["proposition"]["statut"] == "refusee"
    assert decision["element_id"] is None
    assert service.consulter_famille("assurances", fiche)["elements"]["assurance"] == []


def test_decision_sans_humain_nomme_refusee(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer_document_assurance(connexion, contexte_a, config, fiche)
    proposition = resultat.propositions[0]

    with pytest.raises(ErreurImportGuide):
        import_guide.decider_proposition(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte_a,
            proposition_id=str(proposition["id"]),
            decision="accepter",
            decide_par="   ",
        )
    # La proposition reste en attente : aucun statut validé n'a été posé.
    relue = import_guide.lire_import_document(
        connexion, contexte_a, str(resultat.import_document["id"])
    )
    assert relue["propositions"][0]["statut"] == "propose"


# --------------------------------------------------------------------------- #
# 6. Isolation par client
# --------------------------------------------------------------------------- #
def test_isolation_par_client(connexion, contexte_a, contexte_b, config):
    _, _, fiche_a = _preparer_fiche(connexion, contexte_a, config)
    resultat = _importer_document_assurance(connexion, contexte_a, config, fiche_a)
    import_id = str(resultat.import_document["id"])

    # Le client B ne voit rien : ni la liste, ni l'import, ni ses propositions.
    assert import_guide.lister_imports(connexion, contexte_b) == []
    with pytest.raises(ImportIntrouvable):
        import_guide.lire_import_document(connexion, contexte_b, import_id)
    with pytest.raises(ImportIntrouvable):
        import_guide.decider_proposition(
            connexion,
            config.cle_chiffrement_maitresse,
            contexte_b,
            proposition_id=str(resultat.propositions[0]["id"]),
            decision="accepter",
            decide_par=DECIDEUR_FICTIF,
        )
    # Aucune lecture croisée des fichiers : le client B ne peut pas lire le document.
    from app.storage.fichiers import ErreurStockage

    with pytest.raises(ErreurStockage):
        _stockage(config).lire(contexte_b.client_id, str(resultat.document["id"]))


# --------------------------------------------------------------------------- #
# 7. État d'avancement utile — ce qui manque, famille par famille
# --------------------------------------------------------------------------- #
def test_avancement_utile_dit_ce_qui_manque(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    echeance = _dt.date.today() + _dt.timedelta(days=40)
    resultat = _importer_document_assurance(
        connexion, contexte_a, config, fiche, date_echeance=echeance
    )
    import_guide.decider_proposition(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        proposition_id=str(resultat.propositions[0]["id"]),
        decision="accepter",
        decide_par=DECIDEUR_FICTIF,
    )

    etat = import_guide.etat_avancement_utile(
        connexion,
        config.cle_chiffrement_maitresse,
        contexte_a,
        fiche,
        fenetre_alerte_jours=60,
    )
    assert etat["pret_a_concourir"] is False
    par_famille = {bloc["famille"]: bloc for bloc in etat["familles"]}

    # L'assurance existe mais expire bientôt : le constat nomme l'échéance.
    manques_assurances = par_famille["assurances"]["manques"]
    assert any("expire dans 40 jour" in m for m in manques_assurances), manques_assurances

    # Aucune référence de chantier : le manque est dit tel quel.
    manques_references = par_famille["references_chantiers"]["manques"]
    assert any("référence de chantier comparable" in m for m in manques_references)

    # Aucun pourcentage de complétion structurelle dans la sortie : pas de champ
    # « pourcentage »/« completude », pas de signe « % ».
    assert "pourcentage" not in etat
    assert "completude" not in etat
    assert "completude" not in str({b["famille"]: list(b) for b in etat["familles"]})
    assert "%" not in str(etat)


# --------------------------------------------------------------------------- #
# 8. Routes `/api/v1/import/...`
# --------------------------------------------------------------------------- #
def _client_api(connexion, contexte, config, identifiant: str = "import@fictif.test") -> TestClient:
    service = ServiceAuthentification(connexion, config.cle_session)
    service.creer_utilisateur(contexte, identifiant, "Importateur Fictif", MOT_DE_PASSE_FICTIF)
    connexion.valider()

    from app.main import app

    client = TestClient(app)
    client.__enter__()
    identite = service.authentifier(identifiant, MOT_DE_PASSE_FICTIF)
    assert identite is not None
    client.cookies.set(NOM_COOKIE_SESSION, service.creer_cookie_session(identite))
    return client


def test_routes_import_refusent_sans_session():
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/import/documents").status_code == 401
        assert client.get("/api/v1/import/avancement").status_code == 401
        assert (
            client.post(
                "/api/v1/import/documents",
                data={"famille_cible": "assurances", "fiche_version_id": "x"},
                files={"fichier": ("x.txt", b"DOCUMENT FICTIF", "text/plain")},
            ).status_code
            == 401
        )


def test_parcours_api_import_complet(connexion, contexte_a, config):
    _, _, fiche = _preparer_fiche(connexion, contexte_a, config)
    client = _client_api(connexion, contexte_a, config)
    try:
        reponse = client.post(
            "/api/v1/import/documents",
            data={"famille_cible": "assurances", "fiche_version_id": fiche},
            files={
                "fichier": (
                    "attestation_fictive.txt",
                    _document_assurance(_dt.date.today() + _dt.timedelta(days=365)),
                    "text/plain",
                )
            },
        )
        assert reponse.status_code == 201, reponse.text
        corps = reponse.json()
        assert corps["propositions"][0]["statut"] == "propose"
        import_id = corps["import_document"]["id"]

        # Le format refusé est un 400 explicite, pas un 500.
        refus = client.post(
            "/api/v1/import/documents",
            data={"famille_cible": "assurances", "fiche_version_id": fiche},
            files={"fichier": ("memoire.docx", b"PK\x03\x04", "application/msword")},
        )
        assert refus.status_code == 400
        assert "Format refusé" in refus.json()["detail"]

        listing = client.get("/api/v1/import/documents")
        assert listing.status_code == 200
        assert [i["id"] for i in listing.json()["imports"]] == [import_id]

        lecture = client.get(f"/api/v1/import/documents/{import_id}")
        assert lecture.status_code == 200
        proposition_id = lecture.json()["propositions"][0]["id"]

        decision = client.post(
            f"/api/v1/import/propositions/{proposition_id}",
            json={"decision": "accepter", "decide_par": DECIDEUR_FICTIF},
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["proposition"]["statut"] == "acceptee"

        avancement = client.get("/api/v1/import/avancement", params={"fiche_version_id": fiche})
        assert avancement.status_code == 200
        assert "familles" in avancement.json()
    finally:
        client.__exit__(None, None, None)
