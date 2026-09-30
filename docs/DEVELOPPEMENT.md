# Développer dans `ia-consultations-publiques`

*Guide du développeur — phase 3, lot L6. Décrit l'application **telle qu'elle est dans le
dépôt** : chaque section renvoie à un fichier ou à une sortie d'exécution. Pour installer
et lancer l'application, voir [`docs/INSTALLATION.md`](INSTALLATION.md).*

**Aucun secret dans ce document** : seuls des **noms** de variables y figurent. **Aucune
donnée réelle** d'entreprise ni document de collectivité n'y est employé : les exemples
sont **fictifs et signalés**.

---

## 1. Vue d'ensemble

```
src/app/
  main.py          point d'entrée FastAPI : routeurs, montage des fichiers statiques
  config.py        lecture stricte de l'environnement (échec explicite si variable absente)
  domain/          structures et annuaires — AUCUNE dépendance hors bibliothèque standard
  storage/         persistance PostgreSQL : connexion cloisonnée, migrations, dépôts, fichiers
  services/        logique applicative (bibliothèque, versionnement, analyse, checklist…)
  api/             exposition HTTP /api/v1 (contrat gelé, annexe C)
  web/             écrans HTML rendus côté serveur (Jinja2, sans JavaScript)
  securite/        chiffrement AES-256-GCM par client, hachage Argon2id des mots de passe
src/migrations/    migrations SQL numérotées et réversibles (0001 → 0004)
src/tests/         suite de tests (unitaires + integration/)
scripts/           scripts d'exploitation (provisionnement, sauvegarde, restauration)
```

Volume constaté : **8 753 lignes** de Python dans `src/app/` (mesure réelle, cf.
`docs/RAPPORTS/L6-documentation.md`). L'interface n'a **aucun** JavaScript et **aucun**
build Node : le rendu est côté serveur (`src/app/web/routes_web.py`).

---

## 2. Règle de dépendance des couches

Règle projet (`src/README.md`, annexe A § A3) :

```
api  →  services  →  storage  →  domain
```

- **`domain`** ne dépend de **rien** d'autre que la bibliothèque standard. Ce sont des
  structures et des annuaires (`familles.py`, `securite.py`, `commun.py`…).
- **`storage`** est le seul endroit où l'on écrit du SQL. `storage/connexion.py` est le
  **point d'entrée unique du SQL sur les données** : chaque requête exige un
  `ContexteClient`, et le filtre `%(client_id)s` y est **imposé par le contexte** — un
  appelant ne peut ni le fournir ni le falsifier.
- **`services`** porte la logique ; **`api`** et **`web`** exposent, sans jamais accéder à
  la persistance en direct.
- **Aucune couche n'accède à la persistance en contournant `storage`.**

**Écart constaté, à ne pas propager (signalé, non corrigé ici).** La règle « aucun SQL
hors de `storage/` » n'est **pas** tenue par du code antérieur : on trouve des ordres SQL
dans `src/app/services/checklist.py`, `src/app/services/analyse_dce.py` et
`src/app/services/authentification.py` (constat de L2 § 10, repris par L2bis § 5, resté
ouvert). Le code nouveau doit, lui, passer par `storage/`. Ce point est un **point chaud**
de reprise : vérifier avant d'ajouter du SQL dans un service.

### Invariants structurants

- **Cloisonnement par client** : `client_id` est présent sur toute entité de contenu
  (même déductible par jointure) et vient **exclusivement de la session** — jamais du
  corps de requête ni du chemin. Une cible d'un autre client répond **404**, jamais 403.
- **Un utilisateur = un client** (MVP) : aucun rôle transverse dans le modèle.
- **Jeux de référence globaux** : `jeu_reference` / `valeur_reference` ne portent **aucun**
  `client_id` (invariant I5).
- **Traçabilité** : toute valeur affichée porte `origine`, `confiance` et, si elle est
  extraite, `source_document_id` et `source_emplacement`. Une valeur introuvable est
  signalée « non trouvée dans le document », jamais comblée.
- **Deux verrous humains distincts**, jamais fusionnés : validation de la bibliothèque et
  validation des éléments extraits d'un DCE.

---

## 3. Conventions de nommage

(Reprises de `src/README.md`, appliquées dans le code existant.)

| Élément | Convention | Exemples |
|---|---|---|
| Fichiers et modules | `snake_case`, vocabulaire métier **français** | `references_chantiers.py`, `moyens_humains.py` |
| Classes | `PascalCase` | `ReferenceChantier`, `DefinitionEntite`, `ContexteClient` |
| Champs et fonctions | `snake_case` français | `date_echeance`, `raison_sociale`, `ouvrir_fiche()` |
| Constantes | `MAJUSCULES` | `FAMILLE_VERS_ENTITES`, `LONGUEUR_MINIMALE` |
| Identifiants techniques | **UUID v4**, jamais un numéro métier | `client_id`, `fiche_version_id` |
| Commentaires et docstrings | **français** | — |

Le vocabulaire métier reste en français pour la lisibilité ; le vocabulaire technique
(noms de modules de la bibliothèque standard, types) suit la convention de Python.

**Règles de dépôt** : aucun secret (ni clé, ni mot de passe, ni jeton) ; aucune donnée
réelle — les jeux d'essai sont fictifs **et portent la mention « FICTIF »**.

---

## 4. Écrire une migration numérotée réversible

Convention (`src/migrations/README.md`, annexe A § A4) : un fichier par changement,
`000N_description.sql`, numéro **croissant**, jamais réutilisé. Un fichier contient **deux
sections balisées** :

```sql
-- 0005_exemple.sql — description courte
-- (en-tête : ce que fait la migration, et à quelle section du modèle elle se rattache)

-- +migrate up

CREATE TABLE exemple (
    id         uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id  uuid         NOT NULL REFERENCES client (id),
    libelle    varchar(255) NOT NULL
);

-- +migrate down

-- Ordre inverse strict.
DROP TABLE IF EXISTS exemple;
```

Règles tenues par l'exécuteur (`src/app/storage/migrations.py`) :

- les deux balises sont **obligatoires** ; une section vide fait **échouer** la lecture ;
- une migration **déjà appliquée n'est jamais modifiée** : une correction est une
  **nouvelle** migration ;
- les migrations appliquées sont enregistrées dans `schema_migration` et ne sont **jamais
  rejouées** ;
- une migration enregistrée en base mais **absente du dossier** rend l'annulation
  impossible : l'exécuteur refuse au lieu de deviner ;
- le `down` doit **annuler proprement**, dans l'**ordre inverse** des dépendances, y compris
  les données de référence qu'un `up` a insérées (voir `0004_checklist.sql`, section
  `down`, qui `DELETE` le namespace `checklist.statut_ligne` qu'il avait créé).

**Vérification obligatoire avant de considérer une migration terminée** :

```bash
set -a; . ./.env; set +a; cd src
../.venv/bin/python -m app.storage.migrations up
../.venv/bin/python -m app.storage.migrations down     # la nouvelle migration s'annule
../.venv/bin/python -m app.storage.migrations up
```

`src/tests/integration/test_migrations.py` fait ce aller-retour **automatiquement** pour
chaque migration, sur une base dédiée. Une migration non réversible fait échouer la suite.

Ne jamais tester une migration directement sur une base contenant des données à conserver
(§ 6 de `docs/INSTALLATION.md`).

---

## 5. Ajouter une famille ou un écran

### 5.1 Ajouter une famille

Le registre est **la** table de correspondance unique (`src/app/domain/familles.py`) : il
relie le code de famille, le nom logique d'entité, la table SQL, les champs saisissables
(liste blanche), le champ d'échéance et les tables de liaison. Les écrans et les services
en **découlent** — il n'y a pas d'écran à écrire « à la main » pour une famille conforme.

Étapes :

1. **Modèle** : ajouter la structure dans `docs/DATA-MODEL-V2.md` (le modèle est la
   source ; une migration qui s'en écarte doit d'abord le mettre à jour).
2. **Migration** : créer `000N_<famille>.sql` (tables, index, contraintes, jeu de
   référence), réversible (§ 4).
3. **Libellé** : ajouter la constante `FAMILLE_<NOM>` et l'entrée dans `LIBELLES_FAMILLES`.
4. **Entités** : ajouter les `DefinitionEntite` dans `_ENTITES` (`champs`,
   `champs_obligatoires`, `champ_echeance`, `liaisons`, `sensibilite_defaut`,
   `un_seul_par_fiche` le cas échéant). `FAMILLE_VERS_ENTITES`, `TABLES_CONTENU`,
   `ENTITE_PAR_TABLE` sont **calculés** à partir de `_ENTITES` : rien à tenir à la main.
5. **Types de saisie** : renseigner `TYPES_CHAMPS` si le champ n'est pas du texte
   (`date`, `entier`…). **Les champs chiffrés restent toujours « texte »** : la valeur
   stockée est une charge `v1:<base64>`, et la coercition se fait dans le domaine **avant**
   chiffrement.
6. **Champs sensibles** : déclarer les colonnes à chiffrer dans
   `src/app/domain/securite.py` (`REGISTRE_CHAMPS_CHIFFRES`), en source du modèle
   (`docs/DATA-MODEL-V2.md` § 13.2).
7. **Jeux de référence** : si un champ doit choisir dans une liste, l'associer à un
   namespace via `JEUX_PAR_CHAMP` / `JEUX_COMMUNS` (§ 5.3).
8. **Vérifier** : une famille hors registre répond **404** (et non une erreur serveur) ;
   lancer la suite de tests.

Ce qu'il **ne faut pas** faire : écrire les noms de colonnes depuis une entrée utilisateur
— la liste blanche `champs` existe précisément parce que les noms de colonnes **ne peuvent
pas** être paramétrés en SQL.

### 5.2 Ajouter un écran

Les écrans vivent dans `src/app/web/routes_web.py` (+ `src/app/web/templates/*.html` et
`static/style.css`). Contraintes tenues par tout le module :

- **HTML rendu côté serveur, Jinja2, aucun JavaScript, aucun build Node.** Chaque écran est
  atteignable et utilisable **au clavier** (lien d'évitement présent dans `base.html`) ;
- le routeur est déjà monté dans `app/main.py` (`include_router(routes_web.router)`) : un
  nouvel écran n'exige aucune modification de `main.py` ;
- les écrans appellent les **services** directement, dans le processus — **pas** de requête
  HTTP en boucle sur soi-même ;
- **aucune route `/api/v1`** n'est créée ni renommée : le contrat de l'annexe C est gelé ;
- une session ouverte vaut pour l'API et les écrans (même cookie, `NOM_COOKIE_SESSION`) ;
  sans session, l'écran **redirige** (303) vers `/connexion` ;
- toute sortie **engageante** affiche la mention « brouillon — à relire et à signer » ;
  aucun libellé de bouton ne contient `déposer`, `envoyer`, `signer`, `publier` ou `payer`.

Étapes : ajouter la fonction de route, le gabarit dans `templates/`, le style dans
`static/style.css` ; vérifier au clavier et avec la suite de tests
(`src/tests/test_web.py` couvre les écrans rendus, l'isolation et l'absence de bouton
engageant).

### 5.3 Ajouter une valeur de référence **sans migration destructive**

`jeu_reference` et `valeur_reference` sont des tables **globales** (aucun `client_id`,
invariant I5). Ajouter une valeur est donc une **écriture additive**, jamais une
modification de schéma.

**Méthode recommandée — une migration de données numérotée** (c'est ce que font `0002`,
`0003` et `0004`) :

```sql
-- +migrate up

INSERT INTO jeu_reference (namespace, libelle, description, domaine, portee, source, statut)
VALUES ('mon.domaine', 'Libellé du jeu', 'À quoi il sert', 'métier', 'global',
        'docs/DATA-MODEL-V2.md § … (référence sourcée)', 'actif')
ON CONFLICT (namespace) DO NOTHING;

INSERT INTO valeur_reference (namespace, code, libelle, ordre, domaine, source, statut)
VALUES ('mon.domaine', 'CODE_A', 'Libellé A', 1, 'métier', 'source citée', 'actif'),
       ('mon.domaine', 'CODE_B', 'Libellé B', 2, 'métier', 'source citée', 'actif')
ON CONFLICT (namespace, code) DO NOTHING;

-- +migrate down

DELETE FROM valeur_reference WHERE namespace = 'mon.domaine';
DELETE FROM jeu_reference     WHERE namespace = 'mon.domaine';
```

Pourquoi c'est non destructif : `ON CONFLICT DO NOTHING` rend l'insertion **idempotente**,
le `down` ne retire que le namespace ajouté, et aucune colonne ni table existante n'est
touchée. `valeur_reference` porte `date_debut_validite` / `date_fin_validite` et un
`statut` : pour **retirer** une valeur utilisée, on la passe `statut = 'inactif'` (ou on
borne sa validité) plutôt que de la supprimer — l'historique reste lisible.

**Aucune donnée de collectivité** ne doit entrer dans ces tables sans source citée
(`source` est obligatoire) : ligne rouge.

**Piège à connaître.** « Créer une valeur de référence manquante sans quitter le
formulaire » (écran de saisie) est rendu **sur l'élément**, jamais dans la table globale :
un écran d'entreprise qui écrirait dans `valeur_reference` croiserait les locataires (la
table est globale), et une nomenclature par client est explicitement réservée au MVP
(`docs/DATA-MODEL-V2.md` § 8.4). La valeur saisie reste donc portée par l'élément, marquée
à vérifier (décision signalée dans `docs/RAPPORTS/L5-interface-web.md`).

---

## 6. Lancer les tests

```bash
# 1. base de test dédiée (évite la collision entre exécutions simultanées, § 7)
createdb -h 127.0.0.1 -p 5432 ia_consultations_tests
export TEST_DATABASE_URL="postgresql://$USER@127.0.0.1:5432/ia_consultations_tests"

# 2. exécution
cd src
../.venv/bin/python -m pytest -q                      # toute la suite
../.venv/bin/python -m pytest tests/test_web.py -q    # un seul fichier
```

Sortie réelle de référence (base neuve, venv neuf) :

```
167 passed, 1 warning in 11.06s
```

L'unique avertissement est une dépréciation `starlette`/`httpx` héritée de L1, sans effet.

Comment les tests s'exécutent (`src/tests/conftest.py`) : ils travaillent contre une base
PostgreSQL **locale** ; la fixture de session annule puis applique **toutes** les
migrations (`down(999)` puis `up()`), et les annule à la fin. Les valeurs d'environnement
posées par le `conftest` sont **fictives** (clé de chiffrement de test, secret de session
de test).

Structure : un fichier par brique à la racine de `src/tests/`
(`test_socle`, `test_bibliotheque`, `test_versionnement`, `test_analyse_dce`,
`test_checklist`, `test_provisionnement`, `test_web`, `test_fournisseur_modele`), plus
`src/tests/integration/` pour les invariants transverses (isolation entre clients,
cloisonnement, ligne rouge, migrations, parcours de bout en bout). Les pièces PDF fictives
sont dans `src/tests/fixtures/` (`dce_fictif.pdf`, `dce_fictif_scanne.pdf`), régénérables
par `src/tests/fixtures/generer_fixtures.py`.

Le test d'OCR se déclare « non testé » si `tesseract` est absent
(`extraction_pdf.ocr_disponible()`) : sur une machine sans `tesseract`, la suite passe
quand même mais la lecture des pages scannées n'est pas couverte.

**Un test s'exécute réellement avant qu'une fonctionnalité soit annoncée terminée**, et un
jeu de test est **fictif** (jamais de SIRET, IBAN, bilan ou CV réels).

---

## 7. Pièges connus

1. **`.env` n'est pas chargé par le code Python.** `src/app/config.py` lit `os.environ`.
   Toute commande hors serveur (migrations, provisionnement) exige
   `set -a; . ./.env; set +a`. Seuls `scripts/sauvegarde.sh` et `scripts/restauration.sh`
   lisent `.env` d'eux-mêmes (pour `DATABASE_URL`). Détail : `docs/INSTALLATION.md` § 6.3.
2. **Base de test partagée.** `src/tests/conftest.py` vise `ia_consultations_test` par
   défaut : deux lots qui lancent la suite en parallèle se **marchent dessus** (erreurs du
   type « relation inexistante » ou UUID invalide). Toujours poser `TEST_DATABASE_URL` sur
   une base dédiée. **Point chaud** signalé par L5.
3. **Chiffrement par client — la clé maîtresse n'est pas anodine.** Les champs déclarés
   sensibles sont chiffrés en **AES-256-GCM** avec une clé **dérivée par `client_id`**
   (HKDF-SHA256, sel = `client_id`) depuis `CLE_CHIFFREMENT_MAITRESSE`
   (`src/app/securite/chiffrement.py`). Conséquences :
   - **changer `CLE_CHIFFREMENT_MAITRESSE` rend illisibles les données déjà chiffrées** et
     les fichiers déjà stockés (`storage/fichiers.py` chiffre avec la même clé dérivée) ;
   - le format stocké est **versionné** (`v1:<base64…>`) précisément pour autoriser une
     rotation future : ne pas casser ce préfixe ;
   - la liste de ce qui est chiffré est `REGISTRE_CHAMPS_CHIFFRES`
     (`src/app/domain/securite.py`) — **toute** nouvelle colonne sensible doit y être
     déclarée, sinon elle est stockée en clair sans que rien ne le signale.
4. **Cloisonnement : ce qui compte, c'est la session.** `client_id` vient uniquement du
   contexte de session (`src/app/api/cloisonnement.py`) ; un `client_id` présent dans un
   corps de requête est **ignoré** (schémas Pydantic en `extra="ignore"` — c'est explicite,
   pas un effet de bord). Avant toute écriture dépendant d'un identifiant reçu, **contrôler
   l'appartenance** puis répondre **404** (jamais 403) si la cible appartient à un autre
   client — sans révéler qu'elle existe.
5. **`fiche_version` n'a pas de contrainte croisée `(client_id, entreprise_id)` en base**
   (risque R14) : le chemin est fermé **applicativement**, par le contrôle d'appartenance
   avant appel à `ouvrir_fiche()`. Ne pas s'appuyer sur la base pour ce contrôle.
6. **Ligne rouge, dans le code comme dans la doc.** Aucun chiffre, aucun seuil, aucune
   référence non sourcée. Aucune **garantie de conformité**, aucune promesse de
   confidentialité : la seule formulation autorisée est celle de
   `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 10, et la liste de ses formules **interdites**
   y est opposable à toute relecture. Aucun chemin de code ne doit automatiser un acte
   engageant
   (dépôt de pli, signature, paiement) : les sorties portent la mention « brouillon — à
   relire et à signer ».
7. **SQL hors de `storage/`** : présent dans trois fichiers de `services/` (§ 2). Ne pas
   imiter ; le corriger est un lot à part entière.
8. **Les jeux de référence sont globaux** (§ 5.3) : toute écriture dans
   `jeu_reference` / `valeur_reference` depuis une session d'entreprise est un croisement
   de locataires — interdit par construction (I5).
9. **`src/app/main.py` est un point chaud** : c'est le cinquième lot consécutif à y ajouter
   quelque chose (L2, L3, L4, L2bis, L5). Avant d'y toucher, vérifier qu'un autre lot n'est
   pas en cours sur le même fichier.

---

## 8. Modifier la documentation

Les documents de cadrage (`PROJECT.md`, `docs/SPEC-MVP-V2.md`, `docs/DATA-MODEL-V2.md`) ne
se réécrivent pas : ils se **mettent à jour** quand le modèle change, et les nouveaux
documents y **renvoient**.

Convention des rapports d'exécution : un fichier par lot dans `docs/RAPPORTS/`, contenant
la **sortie réelle** des commandes exécutées — y compris les erreurs rencontrées et leur
correction. Un document fondé sur la seule lecture du code ne compte pas.

## 9. Pour aller plus loin

- Installer, lancer, provisionner : [`docs/INSTALLATION.md`](INSTALLATION.md).
- Modèle de données de référence : [`docs/DATA-MODEL-V2.md`](DATA-MODEL-V2.md).
- Contrat d'API et écrans gelés : [`docs/PLAN-PHASE-3.md`](PLAN-PHASE-3.md) annexes A et C.
- Nomenclature et jeux de référence : [`docs/NOMENCLATURE-REFERENCE.md`](NOMENCLATURE-REFERENCE.md).
- Confidentialité et hébergement (formulation autorisée § 10) : [`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`](CONFIDENTIALITE-ET-HEBERGEMENT.md).
- Déploiement (non exécuté) : [`docs/DEPLOIEMENT-FRANCE.md`](DEPLOIEMENT-FRANCE.md).
