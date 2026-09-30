# Installation et mise en route

*Document d'installation du socle `ia-consultations-publiques` — phase 3, lot L6.
Toutes les commandes de ce document ont été **exécutées telles quelles** sur une base
PostgreSQL neuve le 30 septembre 2026 ; les sorties réelles, y compris les erreurs
rencontrées et leur correction, sont jointes dans
[`docs/RAPPORTS/L6-documentation.md`](RAPPORTS/L6-documentation.md).*

## 0. À qui s'adresse ce document, et ce qu'il ne fait pas

Ce document permet d'installer, de lancer et d'utiliser l'application **sur une machine
locale**, sans son auteur. Il décrit l'application **telle qu'elle existe dans le dépôt** :
chaque affirmation renvoie à un fichier du dépôt ou à une sortie d'exécution.

Ce document ne couvre pas, et rien ici ne doit être improvisé pour les couvrir :

- la **mise en production** et l'hébergement (voir
  [`docs/DEPLOIEMENT-FRANCE.md`](DEPLOIEMENT-FRANCE.md) — rien n'est provisionné) ;
- l'**inscription spontanée**, l'invitation par courriel et la **réinitialisation de mot
  de passe** : hors périmètre de la phase 3 (annexe C § C2, « Ce que C2 ne décide pas ») ;
- toute mise en relation avec un **portail acheteur**, un dépôt de pli, une signature
  électronique ou un paiement : hors périmètre (règle projet, ligne rouge).

Il n'énonce **aucune garantie de confidentialité**. La seule formulation autorisée sur ce
sujet est celle de [`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`](CONFIDENTIALITE-ET-HEBERGEMENT.md) § 10 ;
aucune autre n'a sa place ici.

**Aucun secret dans ce document.** Seuls des **noms** de variables d'environnement y
figurent, jamais de valeur. **Aucune donnée réelle** d'entreprise ni document de
collectivité n'y est employé : les jeux de démonstration sont **fictifs et signalés**.

---

## 1. Prérequis

Relevés sur la machine de référence (macOS 27.0.1, arm64). La version est celle
réellement constatée ; une version supérieure fonctionne, une version inférieure n'a pas
été testée.

| Élément | Version constatée | Rôle | Contrôle |
|---|---|---|---|
| Python | **3.12.14** (`/opt/homebrew/bin/python3.12`) | l'application exige Python 3.12 | `python3.12 --version` |
| PostgreSQL | **18.3** (`psql`, via `Postgres.app`), sur `127.0.0.1:5432` | base de données | `pg_isready -h 127.0.0.1 -p 5432` |
| `tesseract` | **5.5.3**, données de langue **`fra`** présentes | lecture **OCR** des pages scannées | `tesseract --version`, `tesseract --list-langs` |
| `poppler` | **26.06.0** (`pdftotext`, `pdfinfo`, `pdftoppm`) | lecture **PDF** (couche texte et rasterisation pour l'OCR) | `pdftotext -v` |
| `openssl` | **3.3.6** (LibreSSL) | génération du secret de session | `openssl version` |

Sur macOS : `brew install python@3.12 tesseract tesseract-lang poppler`.
`tesseract-lang` est nécessaire : sans le paquet de langue `fra`, l'OCR fonctionne en
langue par défaut et le signale (repli explicite de `src/app/services/extraction_pdf.py`).

PostgreSQL n'est pas installé par le projet : il doit déjà tourner. **Rien ne doit être
exposé sur Internet** : l'application écoute par défaut sur `127.0.0.1`
(`src/app/config.py`, `HOTE_API`).

---

## 2. Récupérer le dépôt

```bash
git clone <adresse du dépôt> ia-consultations-publiques
cd ia-consultations-publiques
```

Arborescence utile :

```
PROJECT.md                     cadrage produit
README.md                      point d'entrée du dépôt
.env.example                   MODÈLE des variables d'environnement (aucune valeur)
src/                           l'application
  app/                         code applicatif (voir docs/DEVELOPPEMENT.md)
  migrations/                  migrations SQL numérotées et réversibles (0001 → 0004)
  requirements.txt             dépendances épinglées
  tests/                       suite de tests (167 tests)
scripts/                       scripts d'exploitation (provisionnement, sauvegarde…)
data/                          pièces et fichiers ; IGNORÉ par git
docs/                          cadrage, modèle de données, rapports d'exécution
```

---

## 3. Environnement virtuel

```bash
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
```

Contrôle (vérifié) :

```
$ .venv/bin/python --version
Python 3.12.14
```

Le `.venv` n'est pas versionné (`.gitignore`).

## 4. Dépendances

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r src/requirements.txt
```

`src/requirements.txt` est **épinglé** : chaque version est fixée. Les briques sont
`fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `jinja2` (application et
écrans), `psycopg[binary]` (PostgreSQL, SQL paramétré, **sans ORM**), `cryptography`,
`argon2-cffi`, `itsdangerous` (sécurité), `pytest`, `httpx` (tests).

Aucune dépendance supplémentaire n'est nécessaire pour la sauvegarde ou la restauration :
`scripts/*.sh` n'emploient que des outils déjà présents avec PostgreSQL et le système —
`pg_dump`, `pg_restore`, `psql`, `openssl`, `tar`, `sha256sum`/`shasum`, `awk`, `sed`,
`grep`, `find`, `mktemp`, `stat`, `du`.

---

## 5. Créer la base

La base vit **hors du dépôt**, sur l'instance PostgreSQL locale. Exemple avec la base
`ia_consultations` :

```bash
export PATH="/chemin/vers/Postgres.app/Contents/Versions/latest/bin:$PATH"
createdb -h 127.0.0.1 -p 5432 ia_consultations
```

Aucune table n'est créée à ce stade : le schéma vient des migrations (§ 7).

## 6. Variables d'environnement

### 6.1 Noms et rôles

Copier le modèle et renseigner **localement** : `.env.example` → `.env` (`.env` est ignoré
par git). Aucune valeur ne doit jamais être écrite dans un fichier versionné.

| Variable | Obligatoire | Rôle |
|---|---|---|
| `DATABASE_URL` | **oui** | chaîne de connexion PostgreSQL (`postgresql://…`) |
| `CLE_CHIFFREMENT_MAITRESSE` | **oui** | clé **maîtresse** du chiffrement applicatif, **32 octets en base64** |
| `CLE_SESSION` | **oui** | secret de signature du cookie de session |
| `HOTE_API` | non | interface d'écoute ; défaut `127.0.0.1` |
| `PORT_API` | non | port d'écoute ; défaut `8000` |
| `REPERTOIRE_DOCUMENTS` | non | racine des pièces, hors dépôt ; défaut `data` |
| `DUREE_SESSION_SECONDES` | non | durée de vie d'une session ; défaut 24 h |
| `MODELE_FOURNISSEUR` | non | `factice` (défaut, **sans réseau**) ou `ue` |
| `MODELE_FOURNISSEUR_URL`, `_CLE`, `_NOM`, `_ORGANISME`, `_DELAI` | non | fournisseur de modèle réel (usage réel seulement) |
| `OCR_LANGUES` | non | langues passées à `tesseract` ; défaut `fra` |
| `SAUVEGARDE_REPERTOIRE`, `SAUVEGARDE_CLE_FICHIER`, `RESTAURATION_REPERTOIRE` | non | scripts de sauvegarde/restauration (§ 12) |

Une variable **obligatoire absente fait échouer le démarrage** avec un message explicite
(`ErreurConfiguration`, `src/app/config.py`). Aucune valeur par défaut n'est inventée pour
un secret.

### 6.2 Les générer

```bash
# Clé maîtresse (32 octets, base64) — la valeur affichée va dans .env, jamais dans le dépôt
cd src && ../.venv/bin/python -m app.config

# Secret de session
openssl rand -base64 48
```

Contrôles vérifiés : la première commande produit une chaîne base64 de **32 octets
décodés** (`bytes` vérifiés, cf. rapport) ; la seconde, une chaîne aléatoire.

### 6.3 Le point dur : `.env` n'est pas lu par lui-même

**Constat vérifié.** Le code Python lit `os.environ`, il **ne charge pas** `.env` de
lui-même. Copier `.env.example` en `.env` ne suffit donc **pas** :

```
$ cd src && ../.venv/bin/python -m app.storage.migrations statut
[config] Variables d'environnement obligatoires absentes : DATABASE_URL,
CLE_CHIFFREMENT_MAITRESSE, CLE_SESSION. Copiez `.env.example` vers `.env`…
→ code de sortie 2
```

Deux façons de faire, les deux vérifiées :

```bash
# a) charger .env dans l'environnement du shell avant toute commande Python
set -a; . ./.env; set +a

# b) laisser uvicorn charger .env lui-même au démarrage
cd src && ../.venv/bin/python -m uvicorn app.main:app \
    --env-file ../.env --host 127.0.0.1 --port 8000
```

L'option (a) est obligatoire pour les commandes **hors serveur** : exécuteur de migrations
(§ 7) et script de provisionnement (§ 9). Le journal uvicorn affiche
`Loading environment from '../.env'` quand l'option (b) est employée.

---

## 7. Migrations

L'exécuteur est `src/app/storage/migrations.py` (aucun ORM, aucun outil externe). Il lit
les fichiers `src/migrations/000N_*.sql`, qui contiennent **deux sections balisées**
(`-- +migrate up` / `-- +migrate down`).

```bash
set -a; . ./.env; set +a
cd src

../.venv/bin/python -m app.storage.migrations statut   # état des migrations
../.venv/bin/python -m app.storage.migrations up       # applique les migrations en attente
../.venv/bin/python -m app.storage.migrations down     # annule LA DERNIÈRE
../.venv/bin/python -m app.storage.migrations down 2   # annule les deux dernières
```

Sorties réelles sur base neuve (cf. rapport) :

```
$ python -m app.storage.migrations up
Migrations appliquées : 0001, 0002, 0003, 0004

$ psql -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
38
```

**Annulation (`down`) — documentée et exécutée.** Chaque annulation retire une migration,
dans l'ordre inverse :

```
$ python -m app.storage.migrations down     →  Migrations annulées : 0004   (36 tables)
$ python -m app.storage.migrations down     →  Migrations annulées : 0003   (34 tables)
$ python -m app.storage.migrations down     →  Migrations annulées : 0002   (16 tables)
$ python -m app.storage.migrations down     →  Migrations annulées : 0001   (1 table : schema_migration)
$ python -m app.storage.migrations down     →  Migrations annulées : aucune  (code 0, aucune erreur)
```

> **Attention.** `down` **détruit les données** : les tables sont supprimées. Sur une base
> de démonstration, l'annulation de `0002` puis `0001` efface le client et le compte
> provisionnés (§ 9). Ne jamais lancer `down` sur une base qui contient des données à
> conserver — c'est un geste de développement, pas d'exploitation.

`down` s'exécute aussi depuis la suite de tests `src/tests/integration/test_migrations.py`
(up puis down de chaque migration).

---

## 8. Démarrer l'application

```bash
set -a; . ./.env; set +a
cd src
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

(ou, en une commande, avec chargement de `.env` par uvicorn :
`../.venv/bin/python -m uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8000`)

Contrôle — l'application **répond** (sorties réelles) :

| Requête | Résultat attendu | Constaté |
|---|---|---|
| `GET /` | 200, identité du service en JSON | 200 `{"application":"ia-consultations-publiques","version":"0.1.0","documentation":"/docs"}` |
| `GET /connexion` | 200, écran de connexion | 200 |
| `GET /static/style.css` | 200 | 200 |
| `GET /bibliotheque` (sans session) | 303 vers `/connexion` | 303 |
| `GET /api/v1/bibliotheque` (sans session) | 401 | 401 |
| `GET /docs` | 200, documentation OpenAPI | 200 |

Le port n'écoute que sur la boucle locale (`lsof -nP -iTCP:8000 -sTCP:LISTEN` affiche
`127.0.0.1:8000`, jamais `*:8000`). Arrêt : `Ctrl-C`.

---

## 9. Provisionnement : `client` et compte d'accès (exploitant, hors API)

Ces deux objets **ne passent pas par l'API** : au démarrage, aucune session ne peut exister
avant que le `client` existe (annexe C § C2, volet 2). Le script est le geste d'exploitant,
exécuté une fois par client.

```bash
set -a; . ./.env; set +a
.venv/bin/python scripts/provisionnement.py \
    --libelle-client "Nom du client" \
    --identifiant "compte@exemple" \
    --nom-affichage "Nom Affiché"
```

Le mot de passe est demandé **deux fois, au clavier, en saisie masquée**. Le script
**refuse** un mot de passe passé en argument (`--mot-de-passe`), qui serait visible par
`ps` — refus vérifié, **avant toute connexion à la base** :

```
$ .venv/bin/python scripts/provisionnement.py --libelle-client "Ne doit pas exister" \
      --identifiant "refuse@demo.invalid" --mot-de-passe "<…>"
REFUSÉ : un mot de passe ne doit jamais être passé en argument de ligne de commande
(il serait visible par `ps`). Relancez la commande sans `--mot-de-passe` …
→ code de sortie 2
```

Le script exige un **terminal** (il ne fonctionne pas sans, la saisie masquée passant par le
tty). Sortie réelle (client fictif de démonstration) :

```
Mot de passe pour 'exploitant-l6@demo.invalid' (saisie masquée) :
Confirmez le mot de passe (saisie masquée) :
OK — provisionnement effectué.
  client_id             : <uuid>
  utilisateur_id        : <uuid>
  identifiant_connexion : exploitant-l6@demo.invalid
  nom_affichage         : Exploitant FICTIF L6
  libelle_client        : Client fictif — DÉMONSTRATION L6
Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. Longueur
minimale exigée : 12 caractères.
```

La sortie ne contient que des **identifiants techniques** : jamais le mot de passe. Le
mot de passe est haché Argon2id, jamais stocké en clair ; il n'est ni journalisé, ni écrit
dans un fichier, ni posé en variable d'environnement persistée. La longueur minimale est
une constante du code (`LONGUEUR_MINIMALE`, `src/app/securite/mots_de_passe.py`).

Un compte créé se connecte par la route gelée `POST /api/v1/connexion` (vérifié : HTTP 200).

---

## 10. Démarrer une bibliothèque (utilisateur connecté)

Qui crée quoi, sans ambiguïté (annexe C § C2) :

| Objet | Créé par | Par quel chemin | Quand |
|---|---|---|---|
| `client` | **exploitant** | `scripts/provisionnement.py` | une fois par client, à l'installation |
| compte d'accès | **exploitant** | `scripts/provisionnement.py` | à l'installation, puis pour chaque compte ajouté |
| `entreprise` + 1re `fiche_version` | **utilisateur connecté** | écran « première utilisation » ou `POST /api/v1/entreprises` | première utilisation |
| `fiche_version` suivante | **utilisateur connecté** | `POST /api/v1/entreprises/{id}/fiches` | nouveau dossier ou nouvelle campagne |

**Depuis l'interface** (écrans rendus côté serveur, aucun JavaScript) : se connecter sur
`/connexion`, puis ouvrir `/entreprises/nouvelle` et créer l'entreprise. Sortie réelle de
la démonstration :

```
GET  /connexion                 -> HTTP 200  (<title>Connexion — ia-consultations-publiques</title>)
POST /connexion (formulaire)    -> HTTP 200, cookie de session posé
GET  /entreprises/nouvelle      -> HTTP 200
POST /entreprises (formulaire)  -> HTTP 200
en base :  Entreprise fictive via l'écran — DÉMONSTRATION L6 | version 1 | vierge
```

**Par l'API** (mêmes gestes), avec le cookie de session :

```
GET  /api/v1/bibliotheque            -> 404  « Aucune fiche de bibliothèque pour ce client.
                                              Provisionnez une entreprise et une version de fiche… »
POST /api/v1/entreprises             -> 201  {entreprise_id, fiche_version_id, numero_version: 1, statut: "vierge"}
POST /api/v1/entreprises/{id}/fiches -> 201  {fiche_version_id, numero_version: 2, statut: "vierge"}
GET  /api/v1/entreprises             -> 200  {entreprises: [...]}
GET  /api/v1/bibliotheque            -> 200  (l'écran de bibliothèque n'est plus un cul-de-sac)
```

Aucun écran d'inscription, aucune réinitialisation de mot de passe : hors périmètre.

---

## 11. Jeu de démonstration fictif

Pour vérifier une sauvegarde, une restauration ou un écran sur des données **non vides**,
le dépôt fournit un jeu **fictif et signalé** :

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0001_jeu_fictif.sql
```

Ce jeu crée **deux clients** distincts (`FICTIF — Client A`, `FICTIF — Client B`),
entreprises, fiches, documents et un jeu de référence. Il est **idempotent**
(`ON CONFLICT DO NOTHING`, UUID fixes) : le relancer ne duplique rien. Il laisse
volontairement **vide** la table `authentification` (aucune empreinte, même fictive, dans
un fichier versionné) : ce jeu ne permet donc **pas** de se connecter — pour se connecter,
provisionner un compte (§ 9).

Aucune donnée réelle n'est employée : voir `docs/RAPPORTS/L7-deploiement.md` § 3 pour
l'ordre de retrait table par table.

---

## 12. Sauvegarde et restauration

Les procédures sont portées par les scripts, pas par ce document :

| Script | Rôle | Documentation |
|---|---|---|
| `scripts/sauvegarde.sh` | sauvegarde **chiffrée** de la base (`pg_dump` + `openssl enc`) et des fichiers, dans un répertoire **hors dépôt** | en-tête du script et `--help` |
| `scripts/restauration.sh` | vérifie les empreintes **avant** de déchiffrer, restaure dans une **base de test distincte**, compare les comptages table par table et l'empreinte de chaque fichier | en-tête du script et `--help` |

Points à connaître :

- la **clé de sauvegarde** est lue dans le fichier désigné par `SAUVEGARDE_CLE_FICHIER`
  (défaut `$HOME/.config/ia-consultations/cle-sauvegarde`, permissions 600 exigées). Les
  scripts ne créent **jamais** de clé : une clé créée silencieusement rendrait les
  sauvegardes précédentes indéchiffrables ;
- le répertoire de sauvegarde et la chaîne de connexion peuvent venir de `DATABASE_URL` ou,
  à défaut, du `DATABASE_URL` lu dans `<dépôt>/.env` par les scripts — c'est le **seul**
  endroit du projet où `.env` est lu automatiquement ;
- aucune archive en clair n'est écrite ; l'intégrité est contrôlée par empreinte SHA-256
  avant tout déchiffrement. Limite assumée et alternative écartée : en-tête de
  `scripts/sauvegarde.sh` et `docs/DEPLOIEMENT-FRANCE.md`.

Exemple de déroulé (exécuté, sorties réelles dans le rapport) :

```bash
export SAUVEGARDE_REPERTOIRE="$HOME/sauvegardes-ia-consultations"
scripts/sauvegarde.sh --base "$DATABASE_URL" --documents data
scripts/restauration.sh --sauvegarde "$SAUVEGARDE_REPERTOIRE/derniere" \
    --base-cible ia_consultations_restauration_test \
    --repertoire-fichiers "$HOME/restauration-ia-consultations/documents" \
    --base "$DATABASE_URL"
```

La restauration se termine par `RESTAURATION VÉRIFIÉE` avec les comptages table par table
et le nombre de fichiers conformes, ou **échoue bruyamment** si un contrôle ne passe pas.

---

## 13. Arrêt et nettoyage

- **Arrêt du serveur** : `Ctrl-C` dans le terminal uvicorn.
- **Retrait d'une base de démonstration** : `dropdb -h 127.0.0.1 ia_consultations_l6`.
- **Fichiers** : ils sont sous `REPERTOIRE_DOCUMENTS` (défaut `data/`), **hors dépôt**.

---

## 14. Erreurs rencontrées, et leur correction

Ces erreurs ont été rencontrées pendant l'installation réelle ; elles sont corrigées ici
pour que la prochaine personne les évite.

1. **`[config] Variables d'environnement obligatoires absentes` (code 2)** — `.env` a été
   copié mais n'est pas chargé par le code Python. *Correction* : `set -a; . ./.env; set +a`
   avant toute commande hors serveur, ou `--env-file ../.env` avec uvicorn (§ 6.3).
2. **`createdb: database "…" does not exist, skipping` (NOTICE)** — n'est pas une erreur :
   `dropdb --if-exists` signale simplement qu'il n'y avait rien à supprimer.
3. **Tentative de provisionnement sans terminal** — la saisie masquée exige un tty. *Correction* :
   lancer `scripts/provisionnement.py` depuis un vrai terminal (ou sous un pseudo-terminal).
4. **`down` a effacé le client et le compte provisionnés** — conséquence normale : `down`
   supprime les tables. Ne pas enchaîner `down`/`up` sur une base dont on veut garder le
   contenu (§ 7).
5. **Collision de base de test entre lots** — `src/tests/conftest.py` utilise une base de
   test **partagée** (`ia_consultations_test`). Deux exécutions simultanées se marchent
   dessus. *Correction* : poser `TEST_DATABASE_URL` sur une base dédiée (§ 11 de
   `docs/DEVELOPPEMENT.md`).
6. **`"/Volumes/…"` non trouvé pour `createdb`** — les binaires de `Postgres.app` ne sont pas
   dans le `PATH` par défaut. *Correction* : préfixer le `PATH` (§ 5) ou employer les chemins
   absolus.

## 15. Pour aller plus loin

- Modifier le code, ajouter une famille, un écran, une migration : [`docs/DEVELOPPEMENT.md`](DEVELOPPEMENT.md).
- Modèle de données : [`docs/DATA-MODEL-V2.md`](DATA-MODEL-V2.md).
- Contrat d'API et écrans : [`docs/PLAN-PHASE-3.md`](PLAN-PHASE-3.md) annexes A et C.
- Déploiement (non exécuté) : [`docs/DEPLOIEMENT-FRANCE.md`](DEPLOIEMENT-FRANCE.md).
- Formulation publique autorisée sur la confidentialité : [`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`](CONFIDENTIALITE-ET-HEBERGEMENT.md) § 10.
- Rapports d'exécution par lot : [`docs/RAPPORTS/`](RAPPORTS/).
