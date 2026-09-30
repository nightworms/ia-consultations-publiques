# RAPPORT-TESTS-PHASE-3 — plan de test et résultats réellement observés

*Lot **L8** — agent `qa`. Phase 3. Écrit le 30 septembre 2026 à 12h24 (+04).*
*Board : `default`, tâche `t_adc94993`. Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*

> **Règle tenue par ce rapport.** Tous les résultats ci-dessous sont **réellement
> observés** : les commandes ont été lancées, la sortie est jointe. Ce qui n'a **pas**
> pu être testé est écrit **« non testé »** — jamais présenté comme validé. Aucun test
> en échec n'a été contourné ni supprimé.

---

## 1. Objet et périmètre

Le lot L8 a deux missions :

1. **écrire les tests d'intégration de la phase 3** (parcours, isolation, ligne rouge,
   invariants, migrations) sur des données **fictives et signalées** (décision D10) ;
2. **vérifier indépendamment** le travail des lots L1, L2, L2bis, L3 et L4 — sans
   relancer leurs tests, et sans **jamais corriger** leur code (un défaut se rapporte).

Dépendances lues : `docs/PLAN-DE-TEST.md`, `docs/REVUE-SECURITE.md`,
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 8.3, `docs/DECISIONS.md` D10,
`docs/PLAN-PHASE-3.md` (dont annexes A, B, C — C2 incluse) et `docs/DATA-MODEL-V2.md`
(§ 3.4 et § 17 pour I1…I8).

---

## 2. Livrables du lot

| Livrable | Chemin | État |
|---|---|---|
| Tests d'intégration | `src/tests/integration/` (7 fichiers, 23 tests) | livré, exécuté |
| Test d'isolation, toutes les tables de contenu | `src/tests/integration/test_isolation.py` | livré, exécuté |
| Tests de la ligne rouge | `src/tests/integration/test_ligne_rouge.py` | livré, exécuté |
| Tests des invariants I1…I8 | `src/tests/integration/test_invariants.py` | livré, exécuté |
| Tests de migration `0001`→`0004` | `src/tests/integration/test_migrations.py` | livré, exécuté |
| Parcours de bout en bout | `src/tests/integration/test_parcours_bout_en_bout.py` | livré, exécuté |
| Démarrage de zéro (script + API) | `src/tests/integration/test_provisionnement_parcours.py` | livré, exécuté |
| Contrôle de fuite et de périmètre | `src/tests/integration/test_fuite_et_perimetre.py` | livré, exécuté |
| Ce rapport | `docs/RAPPORT-TESTS-PHASE-3.md` | présent |
| Rapport de lot | `docs/RAPPORTS/L8-tests.md` | présent |
| Sortie brute (intégration) | `docs/RAPPORTS/L8-sortie-pytest-integration.txt` | jointe |
| Sortie brute (suite complète) | `docs/RAPPORTS/L8-sortie-pytest-complet.txt` | jointe |

---

## 3. Environnement et méthode

- Python **3.12.14** (Homebrew), environnement virtuel `.venv` **hors dépôt**.
- PostgreSQL **18.3** local (`Postgres.app`), écoute **127.0.0.1** uniquement.
- Base applicative de test : `ia_consultations_test`. Base **dédiée** au test de
  migrations : `ia_consultations_qa_migrations` (créée et supprimée par le test).
- Lancement, depuis `src/` :
  `../.venv/bin/python -m pytest tests/integration -v -s` puis `../.venv/bin/python -m pytest -q`.
- **Aucune dépendance nouvelle installée.** Aucun réseau, aucun déploiement, aucun port exposé.
- Les tests exercent soit l'**API HTTP** (routes gelées de l'annexe C), soit la
  **base par SQL** (comptages d'invariants, tentatives d'accès croisé).

---

## 4. Résultats réellement observés

### 4.1 Suite d'intégration du lot

```
$ cd src && ../.venv/bin/python -m pytest tests/integration -v -s
...
======================== 23 passed, 1 warning in 2.24s =========================
```

Sortie brute complète : `docs/RAPPORTS/L8-sortie-pytest-integration.txt`.

Répartition : parcours 4, ligne rouge 8, isolation 3, invariants 2, migrations 1,
fuite/périmètre 4, démarrage de zéro 1.

### 4.2 Suite complète (lots précédents + L8)

```
$ cd src && ../.venv/bin/python -m pytest -q
...
167 passed, 1 warning in 10.98s
```

Sortie brute complète : `docs/RAPPORTS/L8-sortie-pytest-complet.txt`.
**167 réussites, 0 échec** (144 tests des lots précédents + 23 tests d'intégration L8).

> **Réserve de mesure.** Le dépôt a été **modifié pendant mon exécution** par des lots
> parallèles (l'interface `src/app/web/` et `src/app/storage/depot_consultations.py`
> ont apparu en cours de route). Le compte de 167 correspond à l'état du dépôt au
> **30/09/2026 12h24**. Un lot qui ajoute des tests fera mécaniquement bouger ce total.

### 4.3 Parcours de bout en bout (extrait de la sortie brute)

```
[parcours] étapes franchies :
  - 1. POST /entreprises -> 201
  - 2. GET /bibliotheque -> 200 (vierge)
  - 3. POST /bibliotheque/assurances sans pièce -> 400
  - 4. POST /bibliotheque/references_chantiers -> 200
  - 5. POST /bibliotheque/validation -> 200 (validee)
  - 6. POST /consultations -> 201 (10 éléments)
  - 7. GET /consultations/{id} -> 200 (sources présentes)
  - 8. POST .../elements/{id} valider -> 200 (valide)
  - 9. POST .../checklist -> 200 (1 exigences)
  - 10. GET .../checklist -> 200 (présentes=0, manquantes=1)
```

### 4.4 Isolation entre clients (extrait)

```
[isolation] tables couvertes avec données A : 28
[isolation] tables couvertes (vides chez A) : 6
[isolation] tables sans données chez A : ['abonnement', 'chapitre_memoire_reference',
  'dossier', 'evenement_facturation', 'evenement_facturation_dossier', 'tracabilite_valeur']
```

Les **34** tables du schéma portant une colonne `client_id` sont sondées. Pour
**28** d'entre elles une donnée réelle de A est créée, puis on tente d'y accéder
depuis le contexte de B — **en forgeant** aussi le paramètre `client_id` pour B.
Aucune ligne de A n'est joignable. Les **6** tables restantes n'ont **aucun chemin
d'écriture au MVP** (facturation, rattachement de facturation, mémoire technique
liée) : elles sont couvertes au niveau du filtre SQL (0 ligne, valeur forgée
écrasée), **pas** avec des données réelles — c'est une réserve, pas un défaut.

### 4.5 Invariants I1 à I8 (comptage, extrait)

```
[invariants] tables portant client_id : 34
[invariants] écarts par invariant :
  {'I1': 0, 'I2': 0, 'I3': 0, 'I4': 0, 'I5': 0, 'I6': 0, 'I7': 0, 'I8': 0}
[invariants] volume contrôlé : {'entreprise': 2, 'fiche_version': 2, 'assurance': 1,
  'document': 2, 'consultation': 1, 'extraction_element': 10, 'checklist_ligne': 1,
  'validation_relecture': 1}
```

**Zéro ligne en écart sur les huit invariants**, sur un jeu non vide. Une
**contre-épreuve** (`test_i6_detecte_reellement_une_validation_devenue_fausse`)
montre que I6 n'est pas un compteur figé à zéro : après une modification du contenu
en SQL direct (sans révocation), le contrôle par empreinte signale bien l'anomalie.

### 4.6 Ligne rouge (extrait)

```
[ligne rouge] colonnes examinées : 516
[ligne rouge] colonnes de prix/marge trouvées : []
```

Aucune colonne de prix, de marge ou de tarif dans le schéma. Refus observés **côté
API (400)** et **côté base (contrainte)** : valeur sans `origine`, `origine =
genere_ia`, `confiance = verifie` sans source. Aucun statut de checklist ne vaut
« conforme » ; la mention rappelle qu'il ne s'agit **pas** d'un certificat.

### 4.7 Migrations (extrait)

```
[migrations] tables après up complet : 38
[migrations] séquence up/down rejouée : 0001, 0002, 0003, 0004
```

`up` puis `down` rejoué **pour chaque** migration, sur base dédiée ; la structure
disparaît puis revient à l'identique.

### 4.8 Contrôles de fuite et de périmètre (extrait)

```
[fuite] fichiers textuels examinés : 119
[fuite] occurrences du mot de passe de test (fictif) : 7
[fuite] motifs non expliqués : 0
[périmètre] occurrences hors-périmètre non justifiées : 0
[provisionnement] script : refus d'un mot de passe en argument (code 2), aucune fuite
```

Motifs recherchés : SIRET à 14 chiffres, IBAN, clé privée, en-tête de document réel.
**Toutes** les correspondances sont des valeurs **manifestement fictives**
(`00000000000000`, IBAN à zéro). Le contrôle de périmètre ne trouve aucune
fonctionnalité hors périmètre dans le code livré (les occurrences sont des refus ou
des renvois documentaires).

---

## 5. Anomalies constatées (par gravité)

Aucune anomalie **bloquante**. Aucune faille de cloisonnement observée : les
tentatives d'accès croisé échouent toutes. Les constats ci-dessous sont des défauts
**de robustesse ou d'hygiène**, rapportés avec leur preuve.

### A1 — [majeur, infrastructure de test] La base de test est détruite par une suite parallèle
- **Preuve.** `src/tests/conftest.py` lignes 53-60 : la fixture `base_migree`, de portée
  **session**, fait `down(999)` puis `up()` sur la base **unique** `ia_consultations_test`,
  et `down(999)` en sortie.
- **Observé.** Constat déjà porté par les lots L4 (`t_ea8d140e`) et L2bis (`t_8330811a`) :
  deux suites exécutées en parallèle annulent et recréent mutuellement les migrations.
- **Effet.** Lancements parallèles non fiables ; risque de faux échecs. **Non corrigé**
  (fichier d'un autre lot — je constate, je ne corrige pas).
- **Recommandation.** Base dédiée par suite (nom dérivé du lot) ou migrations
  appliquées une fois hors de la portée session, avec base éphémère par exécution.

### A2 — [mineur, schéma] Le `CHECK` sur `origine` accepte `mixte` sur les tables de contenu
- **Preuve.** `pg_get_constraintdef` des tables de contenu : la contrainte autorise
  `ARRAY['document_extrait','saisie_entreprise','mixte']`. Le service refuse `mixte`
  (énumération `Origine` à deux valeurs, `src/app/domain/commun.py` lignes 32-36), mais
  rien au niveau du schéma ne l'interdit.
- **Attendu.** Une écriture directe (hors service) ne devrait pas pouvoir stocker une
  origine que le service interdit.
- **Observé.** Une insertion SQL directe avec `origine = 'mixte'` serait acceptée.
- **Gravité.** Mineur — `mixte` n'est **pas** « générée par l'IA », la ligne rouge n'est
  donc pas franchie ; c'est une incohérence de périmètre d'interdiction.
- **Recommandation.** Lot propriétaire du schéma : restreindre le `CHECK` à
  `('document_extrait','saisie_entreprise')`, ou documenter explicitement que `mixte`
  est réservé à un résumé calculé non saisissable.

### A3 — [mineur, risque résiduel R14] `fiche_version` sans contrainte croisée `(client_id, entreprise_id)`
- **Preuve.** Le schéma de `fiche_version` ne porte pas de contrainte composite
  (risque R14 du plan § 5). La parade est **applicative** :
  `src/app/api/routes_provisionnement.py` `_exiger_entreprise_du_client` (contrôle
  d'appartenance avant écriture).
- **Observé.** Le test `test_second_client_ne_peut_pas_ouvrir_de_fiche` (L2bis) et mon
  test `test_api_acces_croise_refuse_et_aucune_ecriture` démontrent que la route
  répond **404** et qu'**aucune ligne** n'est écrite (`count` avant/après identiques).
- **Gravité.** Mineur **aujourd'hui** (la parade tient), mais le risque est **structurel** :
  tout nouveau chemin d'écriture qui appellerait `creer_version()` avec un
  `entreprise_id` étranger écrirait une ligne croisée sans que la base ne l'arrête.
- **Recommandation.** Correctif structurel (index/contrainte composite + migration)
  **hors du lot L8**, à programmer ; en attendant, la règle « passer par le service »
  doit rester opposable.

### A4 — [majeur, règle A3 / R9] Du SQL subsiste hors de `src/app/storage/`
- **Preuve.** `src/app/services/authentification.py` (l. 70, 80, 92),
  `src/app/services/analyse_dce.py` (l. 115, 141, 205, 240-…, 350, 359, 383, 452, 467),
  `src/app/services/checklist.py` (l. 151, 166, …, 496, 520, 556, 587).
- **Attendu.** Annexe A § A3 et risque R9 : « aucune couche n'accède à la persistance en
  contournant `storage` ».
- **Observé.** Des requêtes SQL sont écrites dans des modules de `services/`. Le filtre
  `client_id` y est bien présent (le cloisonnement tient — c'est prouvé par mes tests),
  mais la centralisation exigée n'est pas respectée.
- **Gravité.** Majeur sur la **règle d'architecture** (déjà signalé par L2 puis L2bis ;
  toujours ouvert). Aucune fuite constatée.
- **Recommandation.** Déplacer ce SQL vers `storage/` (dépôts dédiés), comme l'a fait
  récemment `src/app/storage/depot_consultations.py` pour la lecture des consultations.

### A5 — [mineur, réserve de couverture] Tables sans chemin d'écriture au MVP
- **Preuve.** 6 tables portant `client_id` restent sans donnée dans mon test
  d'isolation : `abonnement`, `dossier`, `evenement_facturation`,
  `evenement_facturation_dossier`, `tracabilite_valeur`, `chapitre_memoire_reference`.
- **Effet.** Pour ces 6 tables, l'isolation est démontrée au niveau du **filtre SQL**
  (valeur forgée écrasée, 0 ligne), **pas** avec des données réelles.
- **Gravité.** Mineur — ce sont des tables de facturation/écriture fine non exposées au
  MVP de la phase 3. La réserve est écrite ici pour ne pas laisser croire à une
  couverture par les données sur ces six tables.

### Contrôles **passés** (pas d'anomalie)
- Isolation croisée : **toutes** les tentatives d'accès de B aux données de A échouent
  (404, 0 ligne) sur les 34 tables et sur les routes de contenu.
- Ligne rouge : refus effectifs (API + base) de l'origine absente, de `genere_ia`, de
  `confiance=verifie` sans source ; aucun champ de prix/marge au schéma.
- Invariants I1…I8 : zéro écart, sur un jeu non vide, avec contre-épreuve I6.
- Migrations : `up`/`down` rejoués pour `0001`…`0004` sans erreur.
- Contrat gelé : les 12 routes de l'annexe C (bibliothèque, provisionnement, analyse,
  checklist) sont présentes sans renommage ; aucune route de création de `client`.

---

## 6. Ce que cette vérification **ne couvre pas** (« non testé »)

1. **Fournisseur de modèle France/UE réel** (Mistral, OVHcloud) : **non testé** — aucune
   clé d'API. Toute l'analyse tourne avec le **fournisseur factice** déterministe
   (défaut, sans réseau). La qualité d'un vrai modèle n'est donc **pas** prouvée
   (risque R3 du plan, question ouverte n° 1).
2. **OCR sur un scan réel dégradé** : **non testé** — seul un scan **synthétique**
   propre a été exercé (par le lot L3). Un scan réel mal cadré reste à éprouver.
3. **Écrans HTML de l'interface (L5)** : **non parcourus au niveau navigateur**. Mes
   tests exercent l'API JSON ; l'interface web a ses propres tests (lot L5) mais je ne
   les ai ni relancés ni remplacés par un parcours navigateur.
4. **Concurrence / accès simultanés** : **non testé** — aucune charge parallèle
   (deux requêtes concurrentes, verrouillage, sérialisation) n'a été simulée.
5. **DCE volumineux et ressources** : **non testé** — seul le DCE fictif court de
   `src/tests/fixtures/` a été déposé.
6. **Sauvegarde / restauration (L7)** : **non testé** ici — hors de mon lot ; les scripts
   de L7 n'ont pas été rejoués par moi.
7. **Journalisation et rotation des traces** : **non testé**.
8. **Le contenu juridique** (`docs/CONFORMITE-COMMANDE-PUBLIQUE.md`) n'est pas vérifié
   sur la source : je ne suis pas juriste (même réserve que `docs/PLAN-DE-TEST.md` § 12).

---

## 7. Conclusion

- La suite **s'exécute réellement** : **23 tests d'intégration L8**, **167 tests** au
  total, **0 échec**, sorties brutes jointes.
- L'**isolation** tient sur le périmètre testé, y compris à l'**écriture** (aucune
  ligne croisée) ; l'**isolation en lecture** tient sur les tables sondées.
- La **ligne rouge** est tenue par du code qui **refuse** (API et base), pas seulement
  par une intention.
- Les **invariants** sont à zéro écart, avec une contre-épreuve qui prouve que le
  contrôle n'est pas creux.
- **Cinq constats** sont rapportés (1 majeur d'infrastructure A1, 1 majeur de règle A4,
  3 mineurs A2/A3/A5). **Aucun bloquant.** Les constats A1 et A4 sont **déjà ouverts**
  par des lots antérieurs et **n'ont pas été corrigés par L8** (je constate, je ne
  corrige pas le code des autres lots).

*Fin du rapport de test de la phase 3. Lot L8 — `qa`.*
