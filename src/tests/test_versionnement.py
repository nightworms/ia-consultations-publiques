"""Tests du versionnement et de la relecture humaine (lot L2) — exécutés réellement.

Aucune donnée réelle : montants, noms et références de ce fichier sont **FICTIFS** et
signalés (« DOCUMENT FICTIF — DÉMONSTRATION »).

Ce que ces tests démontrent :

* les **7 états** de `fiche.statut_version` sont **calculés** à la lecture ;
* une validation humaine exige un **nom de relecteur**, une **attestation cochée** et
  reçoit un **horodatage** posé automatiquement ;
* toute écriture **après** validation **révoque** la validation (`statut = revoquee`,
  `date_revocation`, motif) et remet la fiche en `en_relecture` ;
* le **contrôle par empreinte** (invariant I6) détecte une validation qui se prétend
  encore valable alors que le contenu a changé, **même si le code d'écriture a oublié
  de la révoquer** — c'est l'objet du test dédié.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.config import charger_config
from app.domain.familles import LIBELLES_FAMILLES
from app.services.bibliotheque import ErreurBibliotheque, ServiceBibliotheque
from app.services.versionnement import (
    ALGORITHME_EMPREINTE,
    ErreurVersionnement,
    ServiceVersionnement,
)
from app.storage.connexion import Connexion, ContexteClient
from app.storage.repositories import DepotDocument

MENTION = "DOCUMENT FICTIF — DÉMONSTRATION"
RELECTEUR = "Relecteur Fictif — DÉMONSTRATION"


def _service(connexion: Connexion, contexte: ContexteClient) -> ServiceBibliotheque:
    config = charger_config()
    return ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte)


def _versionnement(connexion: Connexion, contexte: ContexteClient) -> ServiceVersionnement:
    config = charger_config()
    return ServiceVersionnement(connexion, config.cle_chiffrement_maitresse, contexte)


def _preparer(connexion: Connexion, contexte: ContexteClient) -> tuple[ServiceBibliotheque, str, str]:
    service = _service(connexion, contexte)
    entreprise_id = service.creer_entreprise(f"Entreprise fictive de test — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id)
    connexion.valider()
    return service, entreprise_id, str(fiche["id"])


def _document(connexion: Connexion, contexte: ContexteClient, entreprise_id: str, fiche: str) -> str:
    depot = DepotDocument(connexion, charger_config().cle_chiffrement_maitresse)
    document_id = depot.creer(
        contexte,
        entreprise_id=entreprise_id,
        fiche_version_id=fiche,
        type_document="autre",
        libelle=f"Pièce fictive de démonstration — {MENTION}",
        chemin_stockage=f"clients/{contexte.client_id}/{uuid.uuid4()}.bin",
        deposant="entreprise",
    )
    connexion.valider()
    return document_id


def _saisir_identite(service: ServiceBibliotheque, fiche: str, **extra) -> dict:
    donnees = {
        "origine": "saisie_entreprise",
        "confiance": "declare_non_verifie",
        "raison_sociale": f"Étanchéité Exemple SARL — {MENTION}",
        "siren": "000000000",
        "siret_siege": "00000000000000",
        "forme_juridique_code": "SARL",
        "adresse_siege": "1 rue de la Démonstration, 00000 Ville Fictive",
        **extra,
    }
    return service.saisir("identite", "entreprise_version", fiche, donnees)


def _remplir_les_neuf_familles(
    service: ServiceBibliotheque, fiche: str, document_id: str
) -> None:
    """Un élément au moins dans chacune des neuf familles — jeu fictif."""
    _saisir_identite(service, fiche)
    service.saisir(
        "capacites_financieres",
        "capacite_production",
        fiche,
        {
            "origine": "saisie_entreprise",
            "description": "Capacité de production déclarée (fictive)",
            "unite": "m2/an",
            "valeur": "10000",
        },
    )
    service.saisir(
        "assurances",
        "assurance",
        fiche,
        {
            "origine": "saisie_entreprise",
            "type_assurance": "decennale",
            "assureur": "Assureur Fictif SA",
            "date_debut": "2026-01-01",
            "date_echeance": "2027-01-01",
            "piece": document_id,
        },
    )
    service.saisir(
        "certifications",
        "certification",
        fiche,
        {
            "origine": "saisie_entreprise",
            "intitule": "Certification fictive",
            "organisme": "Organisme fictif",
            "domaine_code": "etancheite",
            "piece": document_id,
        },
    )
    service.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche,
        {
            "origine": "saisie_entreprise",
            "intitule_operation": "Chantier fictif de démonstration",
            "maitre_ouvrage": "Collectivité fictive",
        },
    )
    service.saisir(
        "moyens_humains",
        "effectif_metier",
        fiche,
        {
            "origine": "saisie_entreprise",
            "metier_code": "metier.etancheite",
            "nombre": 4,
        },
    )
    service.saisir(
        "moyens_materiels",
        "moyen_materiel",
        fiche,
        {
            "origine": "saisie_entreprise",
            "categorie_code": "engins",
            "designation": "Engin fictif de démonstration",
            "quantite": 1,
        },
    )
    service.saisir(
        "fiches_produits",
        "produit",
        fiche,
        {
            "origine": "saisie_entreprise",
            "fournisseur": "Fournisseur fictif",
            "reference_produit": "REF-FICTIVE-001",
            "designation": "Produit fictif de démonstration",
        },
    )
    service.saisir(
        "memoire_technique",
        "chapitre_memoire",
        fiche,
        {
            "origine": "saisie_entreprise",
            "titre": "Chapitre fictif de démonstration",
            "ordre": 1,
            "contenu_texte": "Contenu fictif — démonstration.",
        },
    )


# --------------------------------------------------------------------------- #
# 1. fiche_version — l'axe de versionnement
# --------------------------------------------------------------------------- #
def test_creation_de_version_numero_croissant(connexion, contexte_a):
    service, entreprise_id, fiche_1 = _preparer(connexion, contexte_a)
    versionnement = _versionnement(connexion, contexte_a)
    fiche_2 = versionnement.creer_version(entreprise_id, commentaire="Correction fictive")
    connexion.valider()

    versions = service.dernieres_fiches(entreprise_id)
    numeros = [v["numero_version"] for v in versions]
    assert numeros == [2, 1]
    assert str(fiche_2["id"]) != fiche_1
    assert fiche_2["statut"] == "vierge"


def test_la_fiche_creee_porte_ses_neuf_familles(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    etat = service.etat_avancement(fiche)
    assert [f["famille"] for f in etat["familles"]] == list(LIBELLES_FAMILLES)
    assert all(f["statut"] == "non_commencee" for f in etat["familles"])
    assert etat["statut"] == "vierge"


# --------------------------------------------------------------------------- #
# 2. États calculés (§ 6.2)
# --------------------------------------------------------------------------- #
def test_etats_vierge_puis_en_saisie(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    assert service.etat_avancement(fiche)["statut"] == "vierge"

    _saisir_identite(service, fiche)
    connexion.valider()
    etat = service.etat_avancement(fiche)
    assert etat["statut"] == "en_saisie"
    identite = [f for f in etat["familles"] if f["famille"] == "identite"][0]
    assert identite["nb_elements"] == 1
    assert identite["completude_famille"] == "complete"
    assert identite["statut"] == "demarree"


def test_etat_socle_complet_quand_les_neuf_familles_sont_remplies(connexion, contexte_a):
    service, entreprise_id, fiche = _preparer(connexion, contexte_a)
    document_id = _document(connexion, contexte_a, entreprise_id, fiche)
    _remplir_les_neuf_familles(service, fiche, document_id)
    connexion.valider()

    etat = service.etat_avancement(fiche)
    assert all(f["nb_elements"] > 0 for f in etat["familles"])
    assert etat["statut"] == "socle_complet"
    assert etat["statut_libelle"] == "Socle complet (non relue)"


def test_tous_les_etats_de_fiche_sont_ceux_du_modele():
    from app.domain.fiche_version import LIBELLES_STATUT_VERSION, StatutVersion

    assert len(list(StatutVersion)) == 7
    assert set(LIBELLES_STATUT_VERSION) == {s.value for s in StatutVersion}


# --------------------------------------------------------------------------- #
# 3. Validation humaine (§ 6.4) et exigence 2
# --------------------------------------------------------------------------- #
def test_validation_humaine_enregistree(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()

    avant = dt.datetime.now(dt.timezone.utc)

    resultat = service.valider_fiche(
        fiche,
        relecteur_nom=RELECTEUR,
        attestation_cochee=True,
        commentaire="Relecture de démonstration",
    )
    connexion.valider()

    assert resultat["statut"] == "validee"
    assert resultat["empreinte_algorithme"] == ALGORITHME_EMPREINTE

    validations = service.versionnement.validations.lister_pour_fiche(contexte_a, fiche)
    assert len(validations) == 1
    validation = validations[0]
    assert validation["relecteur_nom"] == RELECTEUR
    assert int(validation["attestation_cochee"]) == 1
    assert validation["statut"] == "validee"
    assert validation["date_validation"] is not None
    assert validation["date_validation"] >= avant - dt.timedelta(seconds=5)
    assert validation["date_revocation"] is None
    assert validation["empreinte_contenu"]

    etat = service.etat_avancement(fiche)
    assert etat["statut"] == "validee"
    assert etat["statut_libelle"] == "Relue et validée par humain"


def test_validation_refusee_sans_relecteur_nomme(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    with pytest.raises(ErreurVersionnement):
        service.valider_fiche(fiche, relecteur_nom="   ", attestation_cochee=True)


def test_validation_refusee_sans_attestation_cochee(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    with pytest.raises(ErreurVersionnement):
        service.valider_fiche(fiche, relecteur_nom=RELECTEUR, attestation_cochee=False)


# --------------------------------------------------------------------------- #
# 4. Révocation à la première modification (§ 6.5) — exigence 3
# --------------------------------------------------------------------------- #
def test_modification_apres_validation_revoque(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    service.valider_fiche(fiche, relecteur_nom=RELECTEUR, attestation_cochee=True)
    connexion.valider()
    assert service.etat_avancement(fiche)["statut"] == "validee"

    # Une modification **après** validation.
    resultat = _saisir_identite(service, fiche, telephone="0000000000")
    connexion.valider()

    assert resultat["validations_revoquees"], "la validation aurait dû être révoquée"
    assert resultat["statut_fiche"] == "en_relecture"

    validation = service.versionnement.validations.lister_pour_fiche(contexte_a, fiche)[0]
    assert validation["statut"] == "revoquee"
    assert validation["date_revocation"] is not None
    assert "identite" in str(validation["motif_revocation"])

    etat = service.etat_avancement(fiche)
    assert etat["statut"] == "en_relecture"
    assert etat["statut_libelle"] == "En relecture"


def test_validation_de_famille_ne_couvre_que_sa_famille(connexion, contexte_a):
    service, entreprise_id, fiche = _preparer(connexion, contexte_a)
    document_id = _document(connexion, contexte_a, entreprise_id, fiche)
    _remplir_les_neuf_familles(service, fiche, document_id)
    connexion.valider()

    service.valider_fiche(
        fiche,
        relecteur_nom=RELECTEUR,
        attestation_cochee=True,
        cible_type="famille",
        famille_code="assurances",
    )
    connexion.valider()
    etat = service.etat_avancement(fiche)
    statut_assurances = [f for f in etat["familles"] if f["famille"] == "assurances"][0]
    assert statut_assurances["statut"] == "validee"

    # Écrire dans une AUTRE famille ne révoque pas la validation d'assurances.
    service.saisir(
        "moyens_materiels",
        "moyen_materiel",
        fiche,
        {
            "origine": "saisie_entreprise",
            "categorie_code": "engins",
            "designation": "Second engin fictif",
            "quantite": 3,
        },
    )
    connexion.valider()
    validations = service.versionnement.validations.lister_pour_fiche(contexte_a, fiche)
    assert [v["statut"] for v in validations] == ["validee"]

    # Écrire DANS la famille validée la révoque.
    service.saisir(
        "assurances",
        "assurance",
        fiche,
        {
            "origine": "saisie_entreprise",
            "type_assurance": "decennale",
            "assureur": "Assureur Fictif SA (corrigé)",
            "date_debut": "2026-01-01",
            "date_echeance": "2027-06-30",
            "piece": document_id,
        },
    )
    connexion.valider()
    validations = service.versionnement.validations.lister_pour_fiche(contexte_a, fiche)
    assert [v["statut"] for v in validations] == ["revoquee"]


# --------------------------------------------------------------------------- #
# 5. Contrôle par empreinte (invariant I6) — exigence 3, test dédié
# --------------------------------------------------------------------------- #
def test_empreinte_stable_et_sensible_au_contenu(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    versionnement = _versionnement(connexion, contexte_a)

    premiere = versionnement.empreinte(fiche)
    seconde = versionnement.empreinte(fiche)
    assert premiere == seconde  # recalculable : c'est ce qui rend le contrôle opposable

    _saisir_identite(service, fiche, telephone="0000000000")
    connexion.valider()
    assert versionnement.empreinte(fiche) != premiere


def test_le_controle_par_empreinte_detecte_une_validation_indument_valable(
    connexion, connexion_admin, contexte_a
):
    """Test dédié : une écriture qui **oublie** de révoquer n'échappe pas au contrôle.

    On simule ici le défaut de code redouté (§ 6.5 point 2) : la valeur est modifiée
    par un SQL direct, **sans** passer par le service — donc sans révocation. La
    validation reste marquée `validee` en base ; le contrôle par empreinte doit la
    démasquer.
    """
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    service.valider_fiche(fiche, relecteur_nom=RELECTEUR, attestation_cochee=True)
    connexion.valider()

    versionnement = _versionnement(connexion, contexte_a)
    assert versionnement.controler_validations(fiche) == []
    assert service.etat_avancement(fiche)["statut"] == "validee"

    # Écriture directe, sans révocation : le « défaut de code ».
    connexion_admin.executer_script(
        "UPDATE entreprise_version SET raison_sociale = %s WHERE client_id = %s;",
        ("Étanchéité Exemple SARL (modifiée hors service)", contexte_a.client_id),
    )
    connexion.annuler()  # on abandonne la transaction du service, pas la base

    anomalies = versionnement.controler_validations(fiche)
    assert len(anomalies) == 1
    anomalie = anomalies[0]
    assert anomalie["empreinte_enregistree"] != anomalie["empreinte_recalculee"]
    assert "I6" in anomalie["motif"]

    etat = service.etat_avancement(fiche)
    assert etat["statut"] == "validee_puis_modifiee"
    assert etat["statut_libelle"] == "Validée puis modifiée (à relire)"
    assert len(etat["anomalies_empreinte"]) == 1


def test_aucune_anomalie_quand_la_revocation_a_eu_lieu(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    service.valider_fiche(fiche, relecteur_nom=RELECTEUR, attestation_cochee=True)
    connexion.valider()
    _saisir_identite(service, fiche, telephone="0000000000")
    connexion.valider()
    assert service.etat_avancement(fiche)["anomalies_empreinte"] == []


# --------------------------------------------------------------------------- #
# 6. Cloisonnement du versionnement
# --------------------------------------------------------------------------- #
def test_le_versionnement_refuse_la_fiche_d_un_autre_client(connexion, contexte_a, contexte_b):
    service_a, _, fiche_a = _preparer(connexion, contexte_a)
    _saisir_identite(service_a, fiche_a)
    connexion.valider()

    versionnement_b = _versionnement(connexion, contexte_b)
    with pytest.raises(ErreurVersionnement):
        versionnement_b.statut_fiche(fiche_a)
    with pytest.raises(ErreurVersionnement):
        versionnement_b.empreinte(fiche_a)


def test_le_second_client_ne_peut_pas_valider_la_fiche_du_premier(
    connexion, contexte_a, contexte_b
):
    service_a, _, fiche_a = _preparer(connexion, contexte_a)
    _saisir_identite(service_a, fiche_a)
    connexion.valider()

    versionnement_b = _versionnement(connexion, contexte_b)
    with pytest.raises(ErreurVersionnement):
        versionnement_b.valider(fiche_a, relecteur_nom="Intrus Fictif", attestation_cochee=True)


# --------------------------------------------------------------------------- #
# 7. Aucune écriture sur une version archivée
# --------------------------------------------------------------------------- #
def test_version_archivee_refuse_les_ecritures(connexion, contexte_a):
    service, _, fiche = _preparer(connexion, contexte_a)
    _saisir_identite(service, fiche)
    connexion.valider()
    service.versionnement.archiver(fiche)
    connexion.valider()

    assert service.etat_avancement(fiche)["statut"] == "archivee"
    with pytest.raises(ErreurBibliotheque):
        _saisir_identite(service, fiche, telephone="0000000000")
