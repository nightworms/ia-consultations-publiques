#!/usr/bin/env python3
"""completer_demo_phase4.py — complète le jeu de démonstration FICTIF (lot L7).

Ce script fait les trois choses qu'un fichier SQL **ne peut pas** faire proprement :

1. **Écrire les champs chiffrés par client** (annexe A § A6) : leur charge est
   ``v1:<base64>`` produite par la clé maîtresse du ``.env``, **dérivée par
   ``client_id``** (HKDF). Un SQL versionné ne peut pas contenir cette charge : elle
   dépend d'une clé qui n'est pas dans le dépôt, et elle change si la clé tourne.
   Sont concernés : ``entreprise_version``, ``representant_legal``,
   ``exercice_comptable``, ``reference_chantier.montant_montant`` et
   ``reference_chantier.contact_reference``.
2. **Poser le mot de passe du compte de démonstration**, haché en **Argon2id**
   (``app.securite.mots_de_passe``). Le mot de passe est **saisi au clavier, en
   saisie masquée**, jamais passé en argument (visible par ``ps``), jamais écrit
   dans un fichier, jamais affiché — y compris en cas d'erreur. Aucun mot de passe,
   même fictif, ne figure dans un fichier versionné.
3. **Écrire les pièces sources sur disque**, chiffrées, sous
   ``data/clients/<client_id>/<document_id>.bin`` (``storage/fichiers``), pour que
   les documents de la bibliothèque existent réellement et pas seulement en base.

Idempotent : UUID fixes, ``ON CONFLICT DO NOTHING`` pour les insertions, mise à jour
ciblée pour les montants. Relancer le script ne duplique rien ; le mot de passe
saisi à nouveau remplace le précédent.

Ce script ne crée **ni** entreprise **ni** fiche : elles viennent de
``0002_jeu_demo_phase4.sql``. Il ne crée **aucune** consultation : le DCE se dépose
par le parcours (critère 3 de ``docs/PLAN-PHASE-4.md`` § 1).

Usage (recommandé — passe aussi le SQL et écrit les fichiers) :

    bash scripts/jeu-de-test/charger_demo_phase4.sh

Usage direct (le SQL doit avoir été passé avant) :

    .venv/bin/python scripts/jeu-de-test/completer_demo_phase4.py
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Any, Mapping

RACINE_DEPOT = Path(__file__).resolve().parents[2]
RACINE_SRC = RACINE_DEPOT / "src"
if str(RACINE_SRC) not in sys.path:
    sys.path.insert(0, str(RACINE_SRC))

import psycopg  # noqa: E402

from app.config import ErreurConfiguration, charger_config  # noqa: E402
from app.securite.chiffrement import chiffrer, dechiffrer  # noqa: E402
from app.securite.mots_de_passe import LONGUEUR_MINIMALE, hacher  # noqa: E402
from app.storage.fichiers import StockageFichiers  # noqa: E402

#: UUID fixes du jeu — identiques dans 0002_jeu_demo_phase4.sql et DEMONSTRATION.md.
CLIENT_ID = "d0000000-0000-4000-8000-000000000001"
UTILISATEUR_ID = "d0000000-0000-4000-8000-000000000002"
ENTREPRISE_ID = "d0000000-0000-4000-8000-000000000003"
FICHE_VERSION_ID = "d0000000-0000-4000-8000-000000000004"

IDENTIFIANT_DEMO = "demo@exemple.invalid"

#: Pièces sources du jeu : identifiant de `document` → fichier fictif du dépôt.
#: Chaque fichier est lu **tel quel**, chiffré et écrit hors dépôt. Ce qui est dans
#: le dépôt est donc exactement ce qui est stocké.
PIECES_SOURCES: dict[str, str] = {
    "d0000000-0000-4000-8000-000000000101": "fictif/attestation-assurance-RCD-FICTIF.txt",
    "d0000000-0000-4000-8000-000000000102": "fictif/pieces/attestation-assurance-RCP-FICTIF.txt",
    "d0000000-0000-4000-8000-000000000103": "fictif/pieces/certificat-qualification-FICTIF.txt",
    "d0000000-0000-4000-8000-000000000104": "fictif/pieces/fiche-technique-produit-FICTIF.txt",
    "d0000000-0000-4000-8000-000000000105": "fictif/plaquette-presentation-FICTIF.txt",
    "d0000000-0000-4000-8000-000000000106": "fictif/pieces/attestation-bonne-execution-FICTIF.txt",
}


def _saisir_mot_de_passe() -> str:
    """Demande le mot de passe deux fois, en saisie masquée. Ne le renvoie qu'en mémoire."""
    premier = getpass.getpass(
        f"Mot de passe pour le compte de démonstration {IDENTIFIANT_DEMO!r} "
        f"(saisie masquée, {LONGUEUR_MINIMALE} caractères minimum) : "
    )
    second = getpass.getpass("Confirmez le mot de passe (saisie masquée) : ")
    if premier != second:
        raise RuntimeError("Les deux saisies ne correspondent pas. Rien n'a été écrit.")
    return premier


def _chiffrer_champs(
    cle_maitresse: bytes, valeurs: Mapping[str, Any], champs: tuple[str, ...]
) -> dict[str, Any]:
    """Chiffre, au nom du client de démonstration, les colonnes déclarées sensibles."""
    sortie = dict(valeurs)
    for champ in champs:
        valeur = sortie.get(champ)
        if valeur is not None:
            sortie[champ] = chiffrer(cle_maitresse, CLIENT_ID, str(valeur))
    return sortie


def _inserer(cur: psycopg.Cursor, table: str, valeurs: Mapping[str, Any], *, conflit: str) -> None:
    """INSERT idempotent : `ON CONFLICT (<cible>) DO NOTHING`, colonnes triées."""
    colonnes = sorted(valeurs)
    sql = (
        f"INSERT INTO {table} ({', '.join(colonnes)}) "
        f"VALUES ({', '.join('%(' + c + ')s' for c in colonnes)}) "
        f"ON CONFLICT ({conflit}) DO NOTHING"
    )
    cur.execute(sql, dict(valeurs))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Données chiffrées (fictives)
# --------------------------------------------------------------------------- #
def _entreprise_version(cle: bytes) -> dict[str, Any]:
    """Identité de l'entreprise (fictive).

    ÉCART CONSTATÉ ET NON LISSÉ : `entreprise_version.capital_social_montant` est
    déclaré **chiffré** par le registre du domaine (`app/domain/securite.py`,
    entité `entreprise_version`) mais la migration `0002_bibliotheque.sql` le type
    `numeric(18,2)` — donc **non chiffrable**. Conséquence : écrire une charge
    `v1:<base64>` y est refusé par PostgreSQL (« invalid input syntax for type
    numeric »), et lire un nombre en clair y provoque un refus de déchiffrement
    (`chiffrement.dechiffrer` exige le préfixe `v1:`). Le champ est donc laissé
    **NULL** ici : aucune des deux impasses n'est empruntée. La divergence est
    signalée au rapport de lot, à corriger par le lot propriétaire de la migration
    (aucun agent du lot L7 n'a le droit de modifier `0002_bibliotheque.sql`).
    """
    valeurs: dict[str, Any] = {
        "id": "d0000000-0000-4000-8000-000000000b01",
        "client_id": CLIENT_ID,
        "entreprise_id": ENTREPRISE_ID,
        "fiche_version_id": FICHE_VERSION_ID,
        "raison_sociale": "OCÉAN ÉTANCHÉITÉ (FICTIF)",
        "siren": "000000000",
        "siret_siege": "00000000000000",
        "forme_juridique_code": "SAS",
        "capital_social_montant": None,
        "capital_social_devise": None,
        "date_creation_entreprise": "2011-04-18",
        "code_ape_naf": "4391B",
        "numero_tva_intracommunautaire": "FR00000000000",
        "adresse_siege": "14 rue des Alizés, ZA Fictive, 97000 Ville-Inventée (FICTIF)",
        "adresse_etablissement_principal": "14 rue des Alizés, ZA Fictive, 97000 Ville-Inventée (FICTIF)",
        "telephone": "0262000000",
        "email": "contact@ocean-etancheite.exemple.invalid",
        "effectif": 24,
        "date_effectif": "2026-01-31",
        "effectif_source_code": "declaration_entreprise",
        "origine": "saisie_entreprise",
        "confiance": "declare_non_verifie",
    }
    return _chiffrer_champs(
        cle, valeurs, ("siret_siege", "numero_tva_intracommunautaire")
    )


def _representant_legal(cle: bytes) -> dict[str, Any]:
    valeurs: dict[str, Any] = {
        "id": "d0000000-0000-4000-8000-000000000b02",
        "client_id": CLIENT_ID,
        "entreprise_id": ENTREPRISE_ID,
        "fiche_version_id": FICHE_VERSION_ID,
        "nom": "MARTIN-FICTIF",
        "prenom": "Alex",
        "fonction": "Président",
        "qualite_engagement": "Représentant légal de la SAS (FICTIF)",
        "date_nomination": "2011-04-18",
        "statut": "en_exercice",
        "origine": "saisie_entreprise",
        "confiance": "declare_non_verifie",
    }
    return _chiffrer_champs(cle, valeurs, ("nom", "prenom", "date_nomination"))


def _exercices_comptables(cle: bytes) -> list[dict[str, Any]]:
    brut = [
        {
            "id": "d0000000-0000-4000-8000-000000000b03",
            "annee_exercice": 2024,
            "date_cloture": "2024-12-31",
            "chiffre_affaires_montant": "3800000.00",
            "chiffre_affaires_devise": "EUR",
            "resultat_net_montant": "185000.00",
            "resultat_net_devise": "EUR",
            "capitaux_propres_montant": "620000.00",
            "capitaux_propres_devise": "EUR",
            "total_bilan_montant": "1450000.00",
            "total_bilan_devise": "EUR",
            "effectif_moyen": 22,
        },
        {
            "id": "d0000000-0000-4000-8000-000000000b04",
            "annee_exercice": 2025,
            "date_cloture": "2025-12-31",
            "chiffre_affaires_montant": "4120000.00",
            "chiffre_affaires_devise": "EUR",
            "resultat_net_montant": "210000.00",
            "resultat_net_devise": "EUR",
            "capitaux_propres_montant": "830000.00",
            "capitaux_propres_devise": "EUR",
            "total_bilan_montant": "1620000.00",
            "total_bilan_devise": "EUR",
            "effectif_moyen": 24,
        },
    ]
    sortie = []
    for exercice in brut:
        exercice.update(
            {
                "client_id": CLIENT_ID,
                "entreprise_id": ENTREPRISE_ID,
                "fiche_version_id": FICHE_VERSION_ID,
                "origine": "saisie_entreprise",
                "confiance": "declare_non_verifie",
            }
        )
        sortie.append(
            _chiffrer_champs(
                cle,
                exercice,
                (
                    "chiffre_affaires_montant",
                    "resultat_net_montant",
                    "capitaux_propres_montant",
                    "total_bilan_montant",
                ),
            )
        )
    return sortie


def _montants_references(cle: bytes) -> dict[str, dict[str, Any]]:
    """Montant et contact de chaque référence de chantier (chiffrés par client)."""
    donnees = {
        "d0000000-0000-4000-8000-000000000901": (
            "412000.00",
            "S.I.F.E.P.F. — direction des bâtiments (FICTIF)",
        ),
        "d0000000-0000-4000-8000-000000000902": (
            "268000.00",
            "Régie scolaire fictive du Bassin Vert (FICTIF)",
        ),
        "d0000000-0000-4000-8000-000000000903": (
            "195000.00",
            "Communauté FICTIVE des services du Plateau (FICTIF)",
        ),
        "d0000000-0000-4000-8000-000000000904": (
            "156000.00",
            "S.I.F.E.P.F. — direction des bâtiments (FICTIF)",
        ),
    }
    return {
        identifiant: {
            "montant_montant": chiffrer(cle, CLIENT_ID, montant),
            "montant_devise": "EUR",
            "contact_reference": chiffrer(cle, CLIENT_ID, contact),
        }
        for identifiant, (montant, contact) in donnees.items()
    }


# --------------------------------------------------------------------------- #
# Exécution
# --------------------------------------------------------------------------- #
def main() -> int:
    try:
        config = charger_config()
    except ErreurConfiguration as exc:
        print(f"ERREUR de configuration : {exc}", file=sys.stderr)
        return 1

    try:
        mot_de_passe = _saisir_mot_de_passe()
        empreinte = hacher(mot_de_passe)
    except Exception as exc:  # noqa: BLE001 — mot de passe refusé : on le dit, sans le montrer
        print(f"REFUSÉ : {exc}", file=sys.stderr)
        return 2
    finally:
        mot_de_passe = ""

    cle = config.cle_chiffrement_maitresse
    stockage = StockageFichiers(config.repertoire_documents, cle)
    connexion = psycopg.connect(config.database_url)
    try:
        with connexion.cursor() as cur:
            # (1) L'entreprise doit exister : elle vient du fichier SQL.
            cur.execute(
                "SELECT 1 FROM entreprise WHERE client_id = %s AND id = %s",
                (CLIENT_ID, ENTREPRISE_ID),
            )
            if cur.fetchone() is None:
                print(
                    "ERREUR : l'entreprise de démonstration est absente. Passez d'abord "
                    "scripts/jeu-de-test/0002_jeu_demo_phase4.sql "
                    "(ou utilisez charger_demo_phase4.sh).",
                    file=sys.stderr,
                )
                return 1

            # (2) Champs chiffrés.
            _inserer(cur, "entreprise_version", _entreprise_version(cle), conflit="id")
            _inserer(cur, "representant_legal", _representant_legal(cle), conflit="id")
            for exercice in _exercices_comptables(cle):
                _inserer(cur, "exercice_comptable", exercice, conflit="id")

            # (3) Montants des références : mise à jour ciblée (le SQL les laisse nuls,
            #     la contrainte de paire montant/devise l'impose).
            for identifiant, valeurs in _montants_references(cle).items():
                cur.execute(
                    "UPDATE reference_chantier SET montant_montant = %s, montant_devise = %s, "
                    "contact_reference = %s, date_modification = now() "
                    "WHERE client_id = %s AND id = %s",
                    (
                        valeurs["montant_montant"],
                        valeurs["montant_devise"],
                        valeurs["contact_reference"],
                        CLIENT_ID,
                        identifiant,
                    ),
                )

            # (4) Compte d'accès : empreinte Argon2id. Rejouer le script remplace le
            #     mot de passe (c'est le seul moyen de le changer sans le versionner).
            cur.execute(
                "INSERT INTO authentification (client_id, utilisateur_id, mot_de_passe_empreinte, "
                "algorithme) VALUES (%s, %s, %s, 'argon2id') "
                "ON CONFLICT (utilisateur_id) DO UPDATE SET "
                "mot_de_passe_empreinte = EXCLUDED.mot_de_passe_empreinte, "
                "date_modification = now()",
                (CLIENT_ID, UTILISATEUR_ID, empreinte),
            )

            # (5) Contrôle de lecture : les champs chiffrés se déchiffrent-ils ?
            cur.execute(
                "SELECT raison_sociale, siret_siege FROM entreprise_version "
                "WHERE client_id = %s",
                (CLIENT_ID,),
            )
            ligne = cur.fetchone()
            siret_relu = dechiffrer(cle, CLIENT_ID, ligne[1]) if ligne else "(absent)"

        # (6) Pièces sources sur disque (chiffrées, hors dépôt).
        base = RACINE_DEPOT / "scripts" / "jeu-de-test"
        ecrites = 0
        for document_id, relatif in PIECES_SOURCES.items():
            contenu = (base / relatif).read_bytes()
            stockage.ecrire(CLIENT_ID, document_id, contenu)
            ecrites += 1

        connexion.commit()
    except Exception as exc:  # noqa: BLE001
        connexion.rollback()
        print(f"ERREUR : {type(exc).__name__} — {exc}", file=sys.stderr)
        return 1
    finally:
        connexion.close()

    # Vérification réelle du déchiffrement (on relit ce qu'on vient d'écrire).
    verif = psycopg.connect(config.database_url)
    try:
        with verif.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM entreprise_version WHERE client_id = %s",
                (CLIENT_ID,),
            )
            ligne_n = cur.fetchone()
            nb_version = int(ligne_n[0]) if ligne_n else 0
            cur.execute(
                "SELECT count(*) FROM authentification WHERE client_id = %s",
                (CLIENT_ID,),
            )
            ligne_c = cur.fetchone()
            nb_compte = int(ligne_c[0]) if ligne_c else 0
    finally:
        verif.close()

    print("OK — jeu de démonstration complété.")
    print(f"  client_id             : {CLIENT_ID}")
    print(f"  utilisateur           : {IDENTIFIANT_DEMO} (identifiant_connexion)")
    print(f"  entreprise_version    : {nb_version} ligne (champs chiffrés écrits)")
    print(f"  siret relu et déchiffré : {siret_relu}")
    print(f"  compte d'accès        : {nb_compte} empreinte Argon2id enregistrée")
    print(f"  pièces écrites        : {ecrites} fichiers chiffrés sous "
          f"{config.repertoire_documents}/clients/{CLIENT_ID}/")
    print(
        "Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. "
        f"Longueur minimale exigée : {LONGUEUR_MINIMALE} caractères."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover — lancement manuel
    raise SystemExit(main())
