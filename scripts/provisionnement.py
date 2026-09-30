#!/usr/bin/env python3
"""provisionnement.py — provisionnement de la racine, **hors API** (annexe C § C2, volet 2).

Ce script est le geste d'**exploitant**, exécuté une fois par client, à l'installation.
Il crée les deux objets qui ne peuvent pas passer par l'API :

1. le `client` — racine du cloisonnement, créé par `Connexion.creer_client(libelle)`,
   exception nommée et bornée de L1 (aucune session ne peut exister avant lui : annexe A
   § A5, un utilisateur appartient à un seul client) ;
2. le premier **compte d'accès** — créé par
   `ServiceAuthentification.creer_utilisateur(ContexteClient(client_id), identifiant,
   nom_affichage, mot_de_passe)`, le contexte étant construit avec le `client_id` qui
   vient d'être créé.

Ce que ce script ne fait **jamais**
-----------------------------------

* il **refuse** un mot de passe passé en argument de ligne de commande (`--mot-de-passe`
  ou toute variante) : ce serait visible par `ps` dans la table des processus ;
* il ne journalise, n'affiche, n'écrit dans un fichier et ne pose en variable
  d'environnement **aucun** mot de passe — il n'en affiche jamais, pas même en cas
  d'erreur ; le hachage Argon2id est fait par `securite/mots_de_passe.py` ;
* il n'écrit **aucun SQL** : il n'appelle que `Connexion.creer_client` et
  `ServiceAuthentification.creer_utilisateur` (aucune migration, aucune table touchée
  directement) ;
* il ne crée ni `entreprise` ni `fiche_version` : cela passe par l'API, par un
  utilisateur connecté (`POST /api/v1/entreprises`).

Les deux écritures partagent **une seule transaction** : si la création du compte échoue
(mot de passe trop faible, identifiant déjà pris…), le `client` n'est pas laissé
derrière.

Usage
-----

    .venv/bin/python scripts/provisionnement.py \\
        --libelle-client "Nom du client" \\
        --identifiant "compte@exemple" \\
        --nom-affichage "Nom Affiché"

Le mot de passe est demandé deux fois, au clavier, **en saisie masquée**. Aucun port n'est
ouvert ; rien n'est déployé.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# --- `app` importable quand le script est lancé depuis la racine du dépôt ---------------
RACINE_DEPOT = Path(__file__).resolve().parents[1]
RACINE_SRC = RACINE_DEPOT / "src"
if str(RACINE_SRC) not in sys.path:
    sys.path.insert(0, str(RACINE_SRC))

from app.config import ErreurConfiguration, charger_config  # noqa: E402
from app.securite.mots_de_passe import LONGUEUR_MINIMALE, ErreurMotDePasse  # noqa: E402
from app.services.authentification import (  # noqa: E402
    ErreurAuthentification,
    ServiceAuthentification,
)
from app.storage.connexion import (  # noqa: E402
    Connexion,
    ContexteClient,
    ErreurCloisonnement,
)

CODE_SUCCES = 0
CODE_REFUS = 2
CODE_ERREUR = 1


def construire_analyseur() -> argparse.ArgumentParser:
    """Analyseur d'arguments — `--mot-de-passe` est **déclaré pour être refusé**."""
    analyseur = argparse.ArgumentParser(
        prog="provisionnement.py",
        description=(
            "Provisionne la racine d'un client : le `client` et son premier compte "
            "d'accès. Le mot de passe est saisi au clavier, en saisie masquée."
        ),
    )
    analyseur.add_argument(
        "--libelle-client",
        required=True,
        help="Libellé du client (personne morale ou entité), obligatoire.",
    )
    analyseur.add_argument(
        "--identifiant",
        required=True,
        help="Identifiant de connexion du compte d'accès.",
    )
    analyseur.add_argument(
        "--nom-affichage",
        default=None,
        help="Nom affiché du compte (défaut : l'identifiant).",
    )
    # Déclaré uniquement pour produire un refus explicite et lisible plutôt que
    # l'erreur « unrecognized arguments » d'argparse. Il n'est jamais utilisé.
    analyseur.add_argument(
        "--mot-de-passe",
        dest="mot_de_passe_refuse",
        default=None,
        help=argparse.SUPPRESS,
    )
    return analyseur


def _saisir_mot_de_passe(identifiant: str) -> str:
    """Demande le mot de passe deux fois, en saisie masquée. Ne le renvoie qu'en mémoire."""
    premier = getpass.getpass(f"Mot de passe pour {identifiant!r} (saisie masquée) : ")
    second = getpass.getpass("Confirmez le mot de passe (saisie masquée) : ")
    if premier != second:
        raise ErreurMotDePasse("Les deux saisies ne correspondent pas. Rien n'a été créé.")
    return premier


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée. Renvoie un code de sortie (0 succès, 2 refus, 1 erreur)."""
    analyseur = construire_analyseur()
    arguments = analyseur.parse_args(argv)

    if arguments.mot_de_passe_refuse is not None:
        # Refus explicite : un mot de passe en argument est visible par `ps`.
        print(
            "REFUSÉ : un mot de passe ne doit jamais être passé en argument de ligne de "
            "commande (il serait visible par `ps`). Relancez la commande sans "
            "`--mot-de-passe` : la saisie masquée vous sera demandée.",
            file=sys.stderr,
        )
        return CODE_REFUS

    libelle_client = arguments.libelle_client.strip()
    identifiant = arguments.identifiant.strip()
    nom_affichage = (arguments.nom_affichage or identifiant).strip()
    if not libelle_client or not identifiant or not nom_affichage:
        print(
            "REFUSÉ : le libellé du client, l'identifiant et le nom affiché sont "
            "obligatoires (aucun champ blanc).",
            file=sys.stderr,
        )
        return CODE_REFUS

    try:
        mot_de_passe = _saisir_mot_de_passe(identifiant)
    except ErreurMotDePasse as exc:
        print(f"REFUSÉ : {exc}", file=sys.stderr)
        return CODE_REFUS

    config = None
    connexion = None
    try:
        config = charger_config()
        connexion = Connexion(config.database_url).ouvrir()

        # Une seule transaction : client + compte, ou rien.
        client_id = connexion.creer_client(libelle_client)
        contexte = ContexteClient(client_id)
        service = ServiceAuthentification(
            connexion=connexion,
            cle_session=config.cle_session,
            duree_session_secondes=config.duree_session_secondes,
        )
        utilisateur_id = service.creer_utilisateur(
            contexte, identifiant, nom_affichage, mot_de_passe
        )
        connexion.valider()
    except ErreurConfiguration as exc:
        print(f"ERREUR de configuration : {exc}", file=sys.stderr)
        return CODE_ERREUR
    except ErreurMotDePasse as exc:
        if connexion is not None:
            connexion.annuler()
        print(f"REFUSÉ : {exc}", file=sys.stderr)
        return CODE_REFUS
    except (ErreurAuthentification, ErreurCloisonnement) as exc:
        # Aucune erreur n'est avalée : elle est annulée en base **et** signalée.
        if connexion is not None:
            connexion.annuler()
        print(f"ERREUR : {type(exc).__name__} — {exc}", file=sys.stderr)
        return CODE_ERREUR
    except Exception as exc:  # noqa: BLE001 — dernière barrière : annuler puis signaler
        if connexion is not None:
            connexion.annuler()
        print(f"ERREUR : {type(exc).__name__} — {exc}", file=sys.stderr)
        return CODE_ERREUR
    finally:
        mot_de_passe = ""
        if connexion is not None:
            connexion.fermer()

    # Sortie : uniquement des identifiants techniques. Jamais le mot de passe.
    print("OK — provisionnement effectué.")
    print(f"  client_id             : {client_id}")
    print(f"  utilisateur_id        : {utilisateur_id}")
    print(f"  identifiant_connexion : {identifiant}")
    print(f"  nom_affichage         : {nom_affichage}")
    print(f"  libelle_client        : {libelle_client}")
    print(
        "Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. "
        f"Longueur minimale exigée : {LONGUEUR_MINIMALE} caractères."
    )
    return CODE_SUCCES


if __name__ == "__main__":  # pragma: no cover — lancement manuel
    sys.exit(main())
