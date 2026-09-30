"""Test d'isolation — le cloisonnement tient-il sur **chaque** table de contenu ?

Exigence `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 8.3 (constat S1) et lot L8 :
« tenter d'accéder aux données d'un client depuis le compte d'un autre et
**démontrer que l'accès échoue** », à faire sur **chaque** table de contenu.

Deux angles, indépendants des tests des lots :

1. **Angle table par table (SQL)** : pour chaque table du schéma qui porte une
   colonne `client_id`, on crée une donnée chez A, puis on tente d'y accéder avec
   le contexte de B — en forgeant aussi le paramètre `client_id` pour B. Aucune
   ligne de A ne doit être joignable.
2. **Angle API** : les points d'entrée de contenu (bibliothèque, consultation,
   checklist, provisionnement) doivent refuser l'accès croisé (404, jamais 403).

Aucune donnée réelle : clients, entreprises et pièces sont **FICTIFS et signalés**
(« DÉMONSTRATION », décision D10).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.config import charger_config
from app.services import analyse_dce, checklist
from app.services.authentification import ServiceAuthentification
from app.services.bibliotheque import ServiceBibliotheque
from app.services.versionnement import ServiceVersionnement

from .conftest import (
    MENTION,
    MOT_DE_PASSE_FICTIF,
    compter_admin,
    identifiant_unique,
    tables_avec_client_id,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PDF_FICTIF = FIXTURES / "dce_fictif.pdf"


# --------------------------------------------------------------------------- #
# Préparation de données chey A, à travers les services (jamais en SQL brut)
# --------------------------------------------------------------------------- #
def _preparer_donnees_a(connexion, contexte_a) -> dict:
    """Remplit A par les services réels : familles, DCE, élément validé, checklist.

    Renvoie les identifiants utiles. Aucune donnée réelle.
    """
    config = charger_config()
    service = ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte_a)
    entreprise_id = service.creer_entreprise(f"Entreprise fictive A — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id, commentaire="Jeu fictif — DÉMONSTRATION")
    connexion.valider()
    fiche_id = str(fiche["id"])

    # Une pièce fictive (document de bibliothèque) pour rattacher l'assurance.
    from app.storage.repositories import DepotDocument

    document_piece = DepotDocument(connexion, config.cle_chiffrement_maitresse).creer(
        contexte_a,
        entreprise_id=entreprise_id,
        fiche_version_id=fiche_id,
        type_document="attestation_assurance",
        libelle=f"Pièce fictive — {MENTION}",
        chemin_stockage=f"clients/{contexte_a.client_id}/{uuid.uuid4()}.bin",
        deposant="entreprise",
    )
    connexion.valider()

    # Identité (famille F1), avec des valeurs **manifestement fictives**.
    service.saisir(
        "identite",
        "entreprise_version",
        fiche_id,
        {
            "raison_sociale": f"Entreprise de démonstration — {MENTION}",
            "siren": "000000000",
            "siret_siege": "00000000000000",
            "forme_juridique_code": "sarl",
            "adresse_siege": f"1 rue Fictive — {MENTION}",
            "origine": "saisie_entreprise",
        },
    )
    connexion.valider()

    # Deux familles, pour peupler des tables de contenu distinctes.
    service.saisir(
        "assurances",
        "assurance",
        fiche_id,
        {
            "type_assurance": "tous_risques",
            "assureur": f"Assureur fictif — {MENTION}",
            "date_debut": "2026-01-01",
            "date_echeance": "2027-01-01",
            "piece": document_piece,
            "origine": "saisie_entreprise",
        },
    )
    service.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche_id,
        {
            "intitule_operation": f"Chantier fictif — {MENTION}",
            "maitre_ouvrage": f"Maître d'ouvrage fictif — {MENTION}",
            "photos": [document_piece],
            "origine": "saisie_entreprise",
        },
    )
    connexion.valider()

    # Le reste des familles de contenu, pour couvrir un maximum de tables.
    autres_saisies = [
        ("identite", "representant_legal", {"nom": "Nom", "prenom": "Prénom", "fonction": "Gérant"}),
        ("capacites_financieres", "exercice_comptable",
         {"annee_exercice": 2025, "chiffre_affaires_montant": "1000", "chiffre_affaires_devise": "EUR"}),
        ("capacites_financieres", "attestation",
         {"type_attestation": "fiscale", "emetteur": f"Émetteur fictif — {MENTION}",
          "date_emission": "2026-01-01", "piece": document_piece}),
        ("capacites_financieres", "capacite_production", {"description": f"Capacité — {MENTION}"}),
        ("certifications", "certification",
         {"intitule": f"Certification — {MENTION}", "organisme": "Organisme fictif",
          "domaine_code": "fictif", "piece": document_piece}),
        ("moyens_humains", "effectif_metier", {"metier_code": "fictif", "nombre": 3}),
        ("moyens_humains", "organigramme", {"description": f"Organigramme — {MENTION}"}),
        ("moyens_humains", "cv",
         {"nom": "Nom", "prenom": "Prénom", "fonction": "Chef d'équipe", "cv_piece": document_piece}),
        ("moyens_materiels", "moyen_materiel",
         {"categorie_code": "fictif", "designation": f"Camion fictif — {MENTION}", "quantite": 1}),
        ("fiches_produits", "produit",
         {"fournisseur": "Fournisseur fictif", "reference_produit": "REF-FICTIVE",
          "designation": f"Produit fictif — {MENTION}", "certificats": [document_piece]}),
        ("memoire_technique", "chapitre_memoire",
         {"titre": f"Chapitre — {MENTION}", "ordre": 1, "documents_associes": [document_piece]}),
    ]
    for famille, entite, donnees in autres_saisies:
        service.saisir(famille, entite, fiche_id, {**donnees, "origine": "saisie_entreprise"})
    connexion.valider()

    # Un compte d'accès fictif : couvre `utilisateur` et `authentification`.
    ServiceAuthentification(connexion, config.cle_session).creer_utilisateur(
        contexte_a, identifiant_unique("seed"), f"Compte fictif — {MENTION}", MOT_DE_PASSE_FICTIF
    )
    connexion.valider()

    # DCE fictif : consultation + document + éléments extraits (sourcés).
    resultat = analyse_dce.deposer_et_analyser(
        connexion,
        contexte_a,
        _stockage(),
        entreprise_id=entreprise_id,
        libelle=f"Consultation fictive A — {MENTION}",
        nom_fichier=PDF_FICTIF.name,
        contenu=PDF_FICTIF.read_bytes(),
        type_mime="application/pdf",
    )
    consultation_id = str(resultat.consultation["id"])
    elements = list(resultat.elements)
    assert elements, "le DCE fictif doit produire au moins un élément"
    element_id = str(elements[0]["id"])

    # Un élément validé par un humain nommé → alimente la checklist.
    analyse_dce.verifier_element(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        element_id=element_id,
        action="valider",
        verificateur_nom=f"Vérificateur fictif — {MENTION}",
    )
    connexion.valider()

    # Checklist : remplit checklist_execution et checklist_ligne.
    checklist.executer_checklist(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        execute_par=f"Exécutant fictif — {MENTION}",
        fiche_version_id=fiche_id,
    )
    connexion.valider()

    # Validation de relecture : validation_relecture.
    ServiceVersionnement(connexion, config.cle_chiffrement_maitresse, contexte_a).valider(
        fiche_id, relecteur_nom=f"Relecteur fictif — {MENTION}", attestation_cochee=True
    )
    connexion.valider()

    return {
        "entreprise_id": str(entreprise_id),
        "fiche_id": fiche_id,
        "consultation_id": consultation_id,
        "element_id": element_id,
    }


def _stockage():
    from app.storage.fichiers import StockageFichiers

    config = charger_config()
    return StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)


def _ids_chez(connexion_admin, table: str, client_id: str, limite: int = 5) -> list[str]:
    lignes = connexion_admin.lire(
        f"SELECT id FROM {table} WHERE client_id = %s LIMIT {limite};", (client_id,)
    )
    return [str(ligne[0]) for ligne in lignes]


def _compter_chez(connexion_admin, table: str, client_id: str) -> int:
    return int(
        connexion_admin.lire(
            f"SELECT count(*) FROM {table} WHERE client_id = %s;", (client_id,)
        )[0][0]
    )


# --------------------------------------------------------------------------- #
# 1. Angle table par table (SQL)
# --------------------------------------------------------------------------- #
def test_acces_croise_refuse_sur_chaque_table_de_contenu(
    connexion, connexion_admin, contexte_a, contexte_b
):
    """Chaque table portant `client_id` est sondée : B ne joint aucune ligne de A.

    On mesure aussi l'effet d'un `client_id` **forgé dans les paramètres** : la
    valeur imposée par le contexte prime, le forgé n'a aucun effet.
    """
    _preparer_donnees_a(connexion, contexte_a)

    tables = tables_avec_client_id(connexion_admin)
    assert tables, "aucune table portant client_id n'a été trouvée"
    id_a = contexte_a.client_id
    id_b = contexte_b.client_id

    colonnes = {
        table: {
            ligne[0]
            for ligne in connexion_admin.lire(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s;",
                (table,),
            )
        }
        for table in tables
    }

    tables_avec_donnees: list[str] = []
    tables_sans_donnees: list[str] = []

    for table in tables:
        # B lit « ses » lignes, puis tente de lire celles de A en forgeant le
        # paramètre client_id = id_a. La valeur forgée doit être écrasée.
        propre = connexion.executer(
            contexte_b, f"SELECT client_id FROM {table} WHERE client_id = %(client_id)s"
        )
        forge = connexion.executer(
            contexte_b,
            f"SELECT client_id FROM {table} WHERE client_id = %(client_id)s",
            {"client_id": id_a},
        )
        assert len(forge) == len(propre), table
        assert {str(l["client_id"]) for l in propre} <= {id_b}, (
            f"{table} : B voit des lignes d'un autre client que le sien"
        )

        # Accès direct par identifiant : B tente de récupérer des lignes réelles de A.
        # Seules les tables portant une colonne `id` s'y prêtent ; les tables de
        # liaison (clé composite) sont couvertes par le contrôle de comptage ci-dessus.
        if _compter_chez(connexion_admin, table, id_a) == 0:
            tables_sans_donnees.append(table)
            continue
        tables_avec_donnees.append(table)
        ids_a = _ids_chez(connexion_admin, table, id_a) if "id" in colonnes[table] else []
        for ligne_id in ids_a:
            volee = connexion.executer_une(
                contexte_b,
                f"SELECT id FROM {table} WHERE client_id = %(client_id)s AND id = %(id)s",
                {"id": ligne_id},
            )
            assert volee is None, (
                f"FUITE : B a lu la ligne {ligne_id} de A dans {table}"
            )

    # Le test doit porter sur un volume réel, pas sur du vide : au moins les
    # entités de contenu peuplées par A doivent être couvertes.
    for attendue in (
        "entreprise",
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
        "chapitre_memoire_document",
        "utilisateur",
        "authentification",
        "fiche_version",
        "fiche_famille",
        "consultation",
        "document",
        "extraction_element",
        "checklist_execution",
        "checklist_ligne",
        "validation_relecture",
    ):
        assert attendue in tables_avec_donnees, (
            f"{attendue} attendue peuplée chez A mais vide — couverture à revoir"
        )

    print(f"\n[isolation] tables couvertes avec données A : {len(tables_avec_donnees)}")
    print(f"[isolation] tables couvertes (vides chez A) : {len(tables_sans_donnees)}")
    print(f"[isolation] tables sans données chez A : {sorted(tables_sans_donnees)}")


# --------------------------------------------------------------------------- #
# 2. Angle API — accès croisé refusé (404, jamais 403)
# --------------------------------------------------------------------------- #
def test_api_acces_croise_refuse_et_aucune_ecriture(
    connexion, connexion_admin, contexte_a, contexte_b, api_a, api_b
):
    """Les routes de contenu refusent B sur les objets de A, sans rien révéler."""
    donnees = _preparer_donnees_a(connexion, contexte_a)
    consultation_id = donnees["consultation_id"]
    element_id = donnees["element_id"]
    entreprise_id = donnees["entreprise_id"]

    # B n'a aucune fiche : lire la bibliothèque de A n'a pas de sens ici, B lit « la sienne ».
    assert api_b.get("/api/v1/bibliotheque").status_code == 404
    assert api_b.get("/api/v1/entreprises").json()["entreprises"] == []

    # Consultation de A vue par B : 404, jamais 403.
    assert api_b.get(f"/api/v1/consultations/{consultation_id}").status_code == 404

    # B tente de valider un élément de A : 404 et la ligne ne bouge pas.
    avant = connexion_admin.lire(
        "SELECT statut_verification FROM extraction_element WHERE id = %s;", (element_id,)
    )[0][0]
    refus = api_b.post(
        f"/api/v1/consultations/{consultation_id}/elements/{element_id}",
        json={"action": "supprimer", "verificateur_nom": f"B — {MENTION}"},
    )
    assert refus.status_code == 404, refus.text
    apres = connexion_admin.lire(
        "SELECT statut_verification FROM extraction_element WHERE id = %s;", (element_id,)
    )[0][0]
    assert apres == avant, "B a modifié un élément de A"

    # B tente de lire / exécuter la checklist de A : 404.
    assert api_b.get(f"/api/v1/consultations/{consultation_id}/checklist").status_code == 404
    assert (
        api_b.post(
            f"/api/v1/consultations/{consultation_id}/checklist",
            json={"execute_par": f"B — {MENTION}"},
        ).status_code
        == 404
    )

    # B tente d'ouvrir une fiche sur l'entreprise de A : 404, aucune ligne écrite.
    avant_fv = compter_admin(
        connexion_admin,
        "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
        (entreprise_id,),
    )
    refus = api_b.post(f"/api/v1/entreprises/{entreprise_id}/fiches", json={})
    assert refus.status_code == 404, refus.text
    apres_fv = compter_admin(
        connexion_admin,
        "SELECT count(*) FROM fiche_version WHERE entreprise_id = %s;",
        (entreprise_id,),
    )
    assert apres_fv == avant_fv, "une ligne a été écrite dans fiche_version par B (R14)"

    # Et A continue de voir les siennes : le refus n'a pas cassé l'accès légitime.
    assert api_a.get(f"/api/v1/consultations/{consultation_id}").status_code == 200


def test_client_id_du_corps_ignore_a_l_ecriture(
    connexion, connexion_admin, contexte_a, contexte_b, api_a
):
    """Un `client_id` d'un autre client dans le corps ne change rien à la ligne créée."""
    reponse = api_a.post(
        "/api/v1/entreprises",
        json={
            "libelle_court": f"Entreprise fictive — {MENTION}",
            "client_id": contexte_b.client_id,  # champ étranger : doit être ignoré
        },
    )
    assert reponse.status_code == 201, reponse.text
    entreprise_id = reponse.json()["entreprise_id"]
    proprietaire = connexion_admin.lire(
        "SELECT client_id FROM entreprise WHERE id = %s;", (entreprise_id,)
    )[0][0]
    assert str(proprietaire) == contexte_a.client_id
    assert str(proprietaire) != contexte_b.client_id
