# tests/ — emplacement des tests (à remplir en phase 2)

Phase 1 = cadrage : **aucun test fonctionnel n'est écrit**, car il n'y a aucune
fonctionnalité à tester (les services lèvent `NotImplementedError`).

Ce dossier est réservé aux tests de la phase 2 :

- tests du modèle de données (structure, contraintes de traçabilité) ;
- tests du versionnement de fiche (une version publiée est immuable) ;
- tests de la checklist de conformité ;
- tests de non-régression sur les migrations (up / down).

Rappel des règles projet applicables aux tests à venir : un test doit être exécuté
réellement avant d'annoncer une fonctionnalité terminée ; les jeux de données de test
sont **fictifs** (jamais de SIRET, IBAN, bilan ou CV réels).
