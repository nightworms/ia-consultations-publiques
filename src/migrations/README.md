# migrations/ — migrations SQL versionnées (convention)

Aucune migration n'est appliquée en phase 1 : aucun schéma n'est créé, aucun fichier
SQL n'est fourni ici. Ce dossier décrit la **convention** à respecter.

## Convention

- Un fichier par changement de schéma, nommé `000N_description.sql`, numéro croissant
  (`0001_init.sql`, `0002_ajout_attestations.sql`, ...). Les numéros ne sont jamais
  réutilisés ni modifiés après application.
- Chaque fichier contient **deux sections réversibles** :
  - une section « up » qui applique le changement ;
  - une section « down » qui l'annule proprement.
- Une migration déjà appliquée n'est **jamais** modifiée : une correction est une
  nouvelle migration.
- Le schéma de référence est `docs/DATA-MODEL.md`. Une migration qui s'en écarte doit
  d'abord mettre ce document à jour.

## Règles de sûreté (repris des règles projet)

- Tester la migration sur une **copie** de la base avant toute application réelle.
- Toute modification de schéma passe par une migration versionnée — jamais par une
  modification à la main.
- Aucune donnée réelle d'entreprise dans les fichiers de migration ni dans les jeux
  d'essai : tout exemple est **fictif et signalé comme tel**.

## Emplacement cible de la base

La base (SQLite, proposition à valider) vivra hors du dépôt, sous `data/` (ignoré par
git), pour éviter tout versionnement de données confidentielles.
