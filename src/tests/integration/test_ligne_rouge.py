"""Tests de la ligne rouge — le code refuse-t-il vraiment d'enfreindre les règles ?

Règles opposables (annexe A § A9, `docs/SPEC-MVP-V2.md` § 2, `docs/DATA-MODEL-V2.md`
§ 7.5) :

1. aucune valeur enregistrée sans `origine` ;
2. `origine` n'accepte jamais une valeur « générée par l'IA » (`genere_ia`) ;
3. aucune valeur sans source n'est présentée comme `verifie` ;
4. aucun champ de **prix**, de **marge** ou de **tarif** n'existe dans le schéma ;
5. aucune sortie ne dit « conforme » ni ne présente un résultat comme un certificat.

Chaque contrôle est fait **en exécutant réellement** : refus observé côté API et
côté base. Aucune donnée réelle (clients et pièces **FICTIFS**, « DÉMONSTRATION »).
"""

from __future__ import annotations

import re

import psycopg
import pytest

from app.config import charger_config
from app.services.bibliotheque import ServiceBibliotheque

from .conftest import MENTION, compter_admin, ouvrir_session_api

#: Segments de nom de colonne interdits (prix, marge, tarif…). Le motif exige un
#: segment entier (`prix`, `prix_unitaire`) — il ne doit pas attraper `devise`
#: (nom d'une unité monétaire) ni `montant` (une donnée d'engagement n'est pas un prix).
_MOTIF_PRIX = re.compile(
    r"(^|_)(prix|marge|tarif|chiffrage|devis|cout|cost|price|remise)(_|$)"
)


def _fiche_a(connexion, contexte_a) -> tuple[str, str]:
    service = ServiceBibliotheque(
        connexion, charger_config().cle_chiffrement_maitresse, contexte_a
    )
    entreprise_id = service.creer_entreprise(f"Entreprise fictive — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id)
    connexion.valider()
    return str(entreprise_id), str(fiche["id"])


def _inserer_effectif(connexion, contexte_a, entreprise_id, fiche_id, origine: str | None):
    """Insertion directe d'une ligne d'`effectif_metier` (contourne le service).

    Sert à éprouver la contrainte **de schéma** (et non seulement le service).
    """
    colonnes = "client_id, entreprise_id, fiche_version_id, metier_code, nombre"
    valeurs = "%(client_id)s, %(entreprise_id)s, %(fiche)s, %(code)s, 1"
    params = {"entreprise_id": entreprise_id, "fiche": fiche_id, "code": "fictif"}
    if origine is not None:
        colonnes += ", origine"
        valeurs += ", %(origine)s"
        params["origine"] = origine
    connexion.executer(
        contexte_a,
        f"INSERT INTO effectif_metier ({colonnes}) VALUES ({valeurs});",
        params,
    )


# --------------------------------------------------------------------------- #
# 4. Aucun champ de prix / marge / tarif dans le schéma
# --------------------------------------------------------------------------- #
def test_schema_sans_champ_de_prix_ni_de_marge(connexion_admin):
    """Aucune colonne du schéma ne porte un nom de prix, de marge ou de tarif."""
    lignes = connexion_admin.lire(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' ORDER BY table_name, column_name;"
    )
    suspects = [
        (table, colonne)
        for table, colonne in lignes
        if _MOTIF_PRIX.search(colonne.casefold())
    ]
    print(f"\n[ligne rouge] colonnes examinées : {len(lignes)}")
    print(f"[ligne rouge] colonnes de prix/marge trouvées : {suspects}")
    assert suspects == [], f"champ de prix/marge détecté dans le schéma : {suspects}"


# --------------------------------------------------------------------------- #
# 1. Aucune valeur sans origine
# --------------------------------------------------------------------------- #
def test_api_refuse_une_valeur_sans_origine(connexion, connexion_admin, contexte_a, config):
    client = ouvrir_session_api(connexion, contexte_a, config)
    _fiche_a(connexion, contexte_a)
    avant = compter_admin(connexion_admin, "SELECT count(*) FROM effectif_metier;")
    try:
        reponse = client.post(
            "/api/v1/bibliotheque/moyens_humains",
            json={
                "entite": "effectif_metier",
                "donnees": {"metier_code": "fictif", "nombre": 1},  # pas d'origine
            },
        )
        assert reponse.status_code == 400, reponse.text
    finally:
        client.__exit__(None, None, None)
    apres = compter_admin(connexion_admin, "SELECT count(*) FROM effectif_metier;")
    assert apres == avant, "une ligne a été enregistrée sans origine"


def test_base_refuse_une_valeur_sans_origine(connexion, contexte_a):
    entreprise_id, fiche_id = _fiche_a(connexion, contexte_a)
    with pytest.raises(psycopg.errors.NotNullViolation):
        _inserer_effectif(connexion, contexte_a, entreprise_id, fiche_id, origine=None)
    connexion.annuler()


# --------------------------------------------------------------------------- #
# 2. `origine` n'accepte jamais « genere_ia »
# --------------------------------------------------------------------------- #
def test_api_refuse_origine_generee_par_ia(connexion, connexion_admin, contexte_a, config):
    client = ouvrir_session_api(connexion, contexte_a, config)
    _fiche_a(connexion, contexte_a)
    avant = compter_admin(connexion_admin, "SELECT count(*) FROM effectif_metier;")
    try:
        reponse = client.post(
            "/api/v1/bibliotheque/moyens_humains",
            json={
                "entite": "effectif_metier",
                "donnees": {"metier_code": "fictif", "nombre": 1, "origine": "genere_ia"},
            },
        )
        assert reponse.status_code == 400, reponse.text
        assert "origine" in reponse.json()["detail"].casefold()
    finally:
        client.__exit__(None, None, None)
    assert compter_admin(connexion_admin, "SELECT count(*) FROM effectif_metier;") == avant


def test_base_refuse_origine_generee_par_ia(connexion, contexte_a):
    entreprise_id, fiche_id = _fiche_a(connexion, contexte_a)
    with pytest.raises(psycopg.errors.CheckViolation):
        _inserer_effectif(connexion, contexte_a, entreprise_id, fiche_id, origine="genere_ia")
    connexion.annuler()

    # Contre-épreuve : les deux origines admises passent (le contrôle n'est pas
    # un refus en bloc qui rendrait le test creux).
    _inserer_effectif(connexion, contexte_a, entreprise_id, fiche_id, origine="saisie_entreprise")
    connexion.valider()


# --------------------------------------------------------------------------- #
# 3. Aucune valeur sans source présentée comme `verifie`
# --------------------------------------------------------------------------- #
def test_api_refuse_confiance_verifie_sans_source(connexion, contexte_a, config):
    client = ouvrir_session_api(connexion, contexte_a, config)
    _fiche_a(connexion, contexte_a)
    try:
        reponse = client.post(
            "/api/v1/bibliotheque/moyens_humains",
            json={
                "entite": "effectif_metier",
                "donnees": {
                    "metier_code": "fictif",
                    "nombre": 1,
                    "origine": "saisie_entreprise",
                    "confiance": "verifie",  # sans source : doit être refusé
                },
            },
        )
        assert reponse.status_code == 400, reponse.text
        assert "verifie" in reponse.json()["detail"].casefold()
    finally:
        client.__exit__(None, None, None)


def test_confiance_sans_source_reste_a_verifier(connexion, connexion_admin, contexte_a):
    """Une valeur sans source est stockée `a_verifier`, jamais `verifie`."""
    # Insertion directe (schéma) : sans confiance explicite, le défaut est `a_verifier`.
    entreprise_id, fiche_id = _fiche_a(connexion, contexte_a)
    _inserer_effectif(connexion, contexte_a, entreprise_id, fiche_id, origine="saisie_entreprise")
    connexion.valider()
    ligne = connexion_admin.lire(
        "SELECT confiance FROM effectif_metier WHERE client_id = %s "
        "ORDER BY date_creation DESC LIMIT 1;",
        (contexte_a.client_id,),
    )
    assert ligne and ligne[0][0] == "a_verifier"

    # Et aucun chemin automatique ne peut poser `verifie` sans contrôle humain :
    # la règle de domaine le refuse explicitement.
    from app.domain.commun import Confiance, ErreurTracabilite, confiance_recevable

    with pytest.raises(ErreurTracabilite):
        confiance_recevable(
            origine="saisie_entreprise",
            confiance=Confiance.VERIFIE.value,
            source_document_id=None,
            controle_humain_par=None,
        )


# --------------------------------------------------------------------------- #
# 5. Aucune sortie ne présente un résultat comme un certificat de conformité
# --------------------------------------------------------------------------- #
def test_aucune_sortie_ne_dit_conforme(connexion, contexte_a, config):
    """La checklist ne prononce jamais « conforme » comme un verdict.

    On exécute un parcours réel (dépôt d'un DCE fictif → validation d'un élément →
    checklist) et on inspecte la réponse : les statuts de ligne sont bornés au
    vocabulaire `presente` / `manquante` / `a_verifier`, et aucun champ ne porte le
    verdict « conforme » ou « certifiée ».
    """
    from pathlib import Path

    from app.services import analyse_dce, checklist
    from app.services.bibliotheque import ServiceBibliotheque
    from app.storage.fichiers import StockageFichiers

    entreprise_id, fiche_id = _fiche_a(connexion, contexte_a)
    pdf = Path(__file__).resolve().parents[1] / "fixtures" / "dce_fictif.pdf"
    stockage = StockageFichiers(config.repertoire_documents, config.cle_chiffrement_maitresse)
    resultat = analyse_dce.deposer_et_analyser(
        connexion,
        contexte_a,
        stockage,
        entreprise_id=entreprise_id,
        libelle=f"Consultation fictive — {MENTION}",
        nom_fichier=pdf.name,
        contenu=pdf.read_bytes(),
        type_mime="application/pdf",
    )
    consultation_id = str(resultat.consultation["id"])
    element_id = str(resultat.elements[0]["id"])
    analyse_dce.verifier_element(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        element_id=element_id,
        action="valider",
        verificateur_nom=f"Vérificateur fictif — {MENTION}",
    )
    connexion.valider()
    sortie = checklist.executer_checklist(
        connexion,
        contexte_a,
        consultation_id=consultation_id,
        execute_par=f"Exécutant fictif — {MENTION}",
        fiche_version_id=fiche_id,
    )
    connexion.valider()

    statuts = {str(ligne["statut"]) for ligne in sortie["lignes"]}
    assert statuts <= {"presente", "manquante", "a_verifier"}, statuts
    mention = str(sortie["mention"]).casefold()
    assert "certificat" in mention, "la mention doit rappeler qu'il ne s'agit pas d'un certificat"
    assert "pas un certificat" in mention or "aucune conformit" in mention
    assert "conformit" in mention, "la mention doit dire explicitement qu'aucune conformité n'est garantie"

    # Le mot « conforme » n'apparaît jamais comme verdict : aucun statut ne le porte.
    for ligne in sortie["lignes"]:
        assert ligne["statut"] != "conforme"

