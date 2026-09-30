# src/ — squelette de code (phase 1)

Ce dossier contient le **squelette** du code applicatif. Phase 1 = cadrage : il n'y a
**aucune logique métier complète, aucun appel réseau, aucune connexion à une base**.
Rien ici ne s'exécute comme une application finie.

Le modèle de données de référence est `docs/DATA-MODEL.md`. Ce squelette en est la
traduction en arborescence.

## Découpage

```
src/
├── app/
│   ├── main.py         point d'entrée applicatif (squelette)
│   ├── config.py       configuration via variables d'environnement (squelette)
│   ├── domain/         structure des données — une entité par famille du modèle
│   ├── storage/        persistance (interfaces + squelettes, aucune base réelle)
│   ├── services/       logique applicative (fonctions vides)
│   └── api/            exposition HTTP (routes vides)
├── migrations/         migrations SQL versionnées (convention décrite, aucune appliquée)
└── tests/              emplacement des tests (à remplir en phase 2)
```

Règle de dépendance : `api` → `services` → `storage` → `domain`. `domain` ne dépend de
rien d'autre que la bibliothèque standard. Aucune couche n'accède à la persistance en
contournant `storage`.

## Conventions de nommage

- **Fichiers et modules** : `snake_case`, français pour le vocabulaire métier
  (`references_chantiers.py`, `moyens_humains.py`).
- **Classes** : `PascalCase` (`ReferenceChantier`, `Assurance`).
- **Champs et fonctions** : `snake_case` en français (`date_echeance`, `raison_sociale`).
- **Constantes** : `MAJUSCULES`.
- **Identifiants techniques** : UUID v4, jamais un numéro métier.
- **Commentaires et docstrings** : français. Les identifiants de code restent en
  français métier par choix de lisibilité pour Anthony ; le vocabulaire technique
  (noms de modules Python, types) suit la convention de la bibliothèque standard.

## Stack technique — *proposition à valider par Anthony*

La stack n'est pas tranchée (voir `docs/PLAN.md` § 5, question 5, et
`docs/DATA-MODEL.md` § 0). Proposition retenue, **réversible** :

- **Python 3.12**, bibliothèque standard uniquement pour le squelette ;
- **SQLite** pour la persistance locale ;
- **FastAPI** pour l'API HTTP (phase 2) ;
- **migrations SQL numérotées** (`migrations/000N_*.sql`).

Le squelette n'importe **rien** hors bibliothèque standard : ni FastAPI, ni SQLite, ni
ORM. Ces briques sont une cible, pas une dépendance installée. Aucune n'est installée
dans cette phase.

## Ce que ce squelette n'est pas

- Pas de logique métier complète : les fonctions des `services` lèvent
  `NotImplementedError`.
- Pas de schéma appliqué : les migrations décrivent une convention, aucun fichier SQL
  n'est exécuté et aucun n'est fourni à ce stade.
- Pas de données réelles : tout exemple de code est fictif et signalé comme tel.
