"""Outil local de vérification (carte t_ebbaac86).

Pose un mot de passe connu sur l'utilisateur de démonstration de la base
DISPOSABLE ``ia_consultations_c6demo`` afin de pouvoir ouvrir les écrans dans un
navigateur et contrôler le critère 6. Ne touche à aucune base de production, ni à
``ia_consultations``, ni aux bases partagées par d'autres lots.
"""

import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE = "postgresql://pause@127.0.0.1:5432/ia_consultations_c6demo"
UTILISATEUR = "d0000000-0000-4000-8000-000000000002"
MOT_DE_PASSE = os.environ.get("MOT_DE_PASSE_DEMO") or ""
if not MOT_DE_PASSE:
    raise SystemExit(
        "MOT_DE_PASSE_DEMO absent : exportez-le (base de démonstration jetable "
        "uniquement). Aucun mot de passe n'est écrit dans ce fichier."
    )


def charger_env_projet() -> None:
    fichier = RACINE / ".env"
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip())


def main() -> None:
    charger_env_projet()
    os.environ["DATABASE_URL"] = BASE
    sys.path.insert(0, str(RACINE / "src"))

    from app.config import charger_config
    from app.securite.mots_de_passe import hacher
    from app.storage.connexion import ConnexionAdministration

    config = charger_config()
    assert "c6demo" in config.database_url, config.database_url

    empreinte = hacher(MOT_DE_PASSE)
    with ConnexionAdministration(config.database_url) as connexion:
        connexion.executer_script(
            "update authentification set mot_de_passe_empreinte = %s "
            "where utilisateur_id = %s",
            (empreinte, UTILISATEUR),
        )
        restant = connexion.lire(
            "select count(*) from authentification where utilisateur_id = %s "
            "and mot_de_passe_empreinte = %s",
            (UTILISATEUR, empreinte),
        )
    print("empreinte posee, lignes correspondantes :", restant)


if __name__ == "__main__":
    main()
