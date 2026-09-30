# L6 — Documentation d'installation et de développement : rapport d'exécution

*Lot **L6** de la phase 3 (`docs/PLAN-PHASE-3.md`). Exécuté le 30 septembre 2026
(12 h 20 → 12 h 26 +04) sur la machine de développement d'Anthony
(`Mac-mini-de-PAUSE.local`, macOS 27.0.1, arm64).*

Toutes les sorties de ce rapport proviennent de commandes **réellement exécutées** ; aucune
n'est déduite de la lecture du code. La procédure de `docs/INSTALLATION.md` a été **suivie
ligne par ligne** sur une base PostgreSQL **neuve** (`ia_consultations_l6`) et jusqu'à une
application qui **répond**.

**Aucune donnée réelle** : tous les clients, entreprises, identifiants et libellés portent
la mention « DÉMONSTRATION » ou « FICTIF ». **Aucun secret** n'apparaît ici : les valeurs
d'environnement générées localement ne sont montrées nulle part, et le mot de passe fictif
du provisionnement n'a été saisi que dans un pseudo-terminal, jamais affiché ni écrit dans
un fichier du dépôt.

---

## 1. Livrables

| Fichier | Nature |
|---|---|
| `docs/INSTALLATION.md` | installation, mise en route, provisionnement, jeu de démonstration, sauvegarde |
| `docs/DEVELOPPEMENT.md` | architecture, conventions, migrations, tests, familles/écrans, valeurs de référence, pièges |
| `docs/RAPPORTS/L6-documentation.md` | ce rapport |

**Aucun fichier de code de production n'a été modifié.** Aucun commit git n'a été fait
(cohérent avec les lots précédents).

---

## 2. Environnement relevé (celui des prérequis de `INSTALLATION.md` § 1)

```console
# --- L6 : prérequis relevés le 2026-09-30 12:22:29 +04 (+0400) ---
uname            : Darwin arm64
psql             : psql (PostgreSQL) 18.3 (Postgres.app)
pg_isready       : 127.0.0.1:5432 - accepting connections
python3.12       : Python 3.12.14
python3 (system) : Python 3.9.6
tesseract        : tesseract 5.5.3
tesseract-ocr-fra: 1 langue(s) fra installée(s)
pdftotext        : pdftotext version 26.06.0
pdfinfo          : pdfinfo version 26.06.0
openssl          : LibreSSL 3.3.6
git              : git version 2.54.0 (Apple Git-157)
```

Aucune dépendance n'a été installée pour ce lot : `python@3.12`, `tesseract` (+ langue
`fra`), `poppler` et PostgreSQL étaient **déjà présents** (installés par les lots L1 et L3).
Le seul ajout de ce lot est un **second environnement virtuel** (§ 3), créé pour prouver
que la procédure d'installation fonctionne **depuis zéro** sans toucher au `.venv` du
projet.

---

## 3. Environnement virtuel et dépendances — exécuté depuis zéro

Commande de la procédure, exécutée dans un **chemin neuf** :

```console
$ rm -rf …/l6/venv-l6
$ /opt/homebrew/bin/python3.12 -m venv …/l6/venv-l6
code de sortie venv : 0
Python 3.12.14

$ …/venv-l6/bin/python -m pip install --quiet --upgrade pip
$ …/venv-l6/bin/python -m pip install -r src/requirements.txt
…
Successfully installed MarkupSafe-3.0.3 annotated-doc-0.0.5 annotated-types-0.8.0
anyio-4.15.1 argon2-cffi-25.1.0 … fastapi-0.142.1 … jinja2-3.1.6 … psycopg-3.3.6
psycopg-binary-3.3.6 … pydantic-2.13.5 … pytest-9.1.1 … uvicorn-0.54.0 …
code de sortie pip install : 0
```

Contrôle des versions installées (`pip list --format=freeze`, extrait) :

```
argon2-cffi==25.1.0        cryptography==50.0.1       fastapi==0.142.1
httpx==0.28.1              itsdangerous==2.2.0        Jinja2==3.1.6
psycopg==3.3.6             psycopg-binary==3.3.6      pydantic==2.13.5
pytest==9.1.1              python-multipart==0.0.32   uvicorn==0.54.0
```

Les **11 dépendances épinglées** de `src/requirements.txt` sont installées, portées par
`uvicorn[standard]` comprises. **Aucune dépendance supplémentaire n'est nécessaire.**

---

## 4. Base neuve, variables d'environnement, migrations

```console
# --- base neuve ---
NOTICE:  database "ia_consultations_l6" does not exist, skipping
createdb -> code 0

# --- fichier .env (valeurs LOCALES FICTIVES, jamais commité) ---
écrit : /Users/pause/Projets/ia-consultations-publiques/.env (mode 100600)
masqué (noms de variables seulement) :
DATABASE_URL=<valeur locale, non affichée>
CLE_CHIFFREMENT_MAITRESSE=<valeur locale, non affichée>
CLE_SESSION=<valeur locale, non affichée>
HOTE_API=<valeur locale, non affichée>
PORT_API=<valeur locale, non affichée>
REPERTOIRE_DOCUMENTS=<valeur locale, non affichée>
MODELE_FOURNISSEUR=<valeur locale, non affichée>
OCR_LANGUES=<valeur locale, non affichée>

# --- migrations : statut (base neuve) ---
0001  en attente
0002  en attente
0003  en attente
0004  en attente
-> code 0

# --- migrations : up ---
Migrations appliquées : 0001, 0002, 0003, 0004
-> code 0

# --- schéma réellement créé ---
 nb_tables
-----------
        38

 numero |        nom
--------+-------------------
 0001   | 0001_init_socle
 0002   | 0002_bibliotheque
 0003   | 0003_analyse_dce
 0004   | 0004_checklist
```

Les deux valeurs sensibles ont été **générées par les commandes documentées** :

```console
$ cd src && ../.venv/bin/python -m app.config
commande : cd src && ../.venv/bin/python -m app.config   (exécutée depuis src/)
sortie   : xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  <-- masquée ici
longueur : 44 caractères base64
octets décodés : 32

$ openssl rand -base64 48
→ 65 caractères (nouvelle ligne incluse)
```

Deux écarts **de forme seulement** entre la procédure écrite et son exécution, sans effet
sur les commandes elles-mêmes : la base de démonstration a été nommée `ia_consultations_l6`
(la procédure donne `ia_consultations` en exemple) et le serveur a écouté sur le port
`8191` (`PORT_API`), pour ne pas entrer en collision avec les autres lots exécutés en
parallèle sur la même machine.

Le fichier `.env` de démonstration a été **supprimé en fin de lot** ; aucune de ses valeurs
n'apparaît ici, ni dans `INSTALLATION.md`, ni dans `DEVELOPPEMENT.md`.

---

## 5. Démarrage — l'application répond

```console
$ cd src && ../.venv/bin/python -m uvicorn app.main:app --env-file ../.env \
        --host 127.0.0.1 --port 8191
INFO:     Loading environment from '../.env'
INFO:     Started server process [92560]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8191 (Press CTRL+C to quit)

GET /                 -> HTTP 200
corps : {"application":"ia-consultations-publiques","version":"0.1.0","documentation":"/docs"}
GET /connexion        -> HTTP 200
GET /static/style.css -> HTTP 200
GET /bibliotheque (anonyme) -> HTTP 303 (redirection attendue vers /connexion)
GET /api/v1/bibliotheque (sans session) -> HTTP 401
GET /docs (OpenAPI)   -> HTTP 200

# --- le port n'écoute PAS sur Internet ---
COMMAND PID   USER   FD   TYPE  …  NAME
Python  92560 pause  10u  IPv4  …  TCP 127.0.0.1:8191 (LISTEN)

# --- arrêt ---
curl après arrêt -> code 000 (connexion refusée)
```

Le serveur a été arrêté en fin de démonstration : rien n'écoute, rien n'est exposé.

---

## 6. Provisionnement (exploitant, hors API) — exécuté pour de vrai

### 6.1 Le refus d'un mot de passe en argument (exigence de l'annexe C § C2)

```console
$ .venv/bin/python scripts/provisionnement.py --libelle-client "Ne doit pas exister" \
      --identifiant "refuse@demo.invalid" --mot-de-passe "un-mot-de-passe-fictif"
REFUSÉ : un mot de passe ne doit jamais être passé en argument de ligne de commande (il
serait visible par `ps`). Relancez la commande sans `--mot-de-passe` : la saisie masquée
vous sera demandée.
-> code 2
clients créés portant ce libellé : 0
```

Le refus intervient **avant toute ouverture de connexion** : aucun client n'a été créé.

### 6.2 Le provisionnement, en pseudo-terminal (saisie masquée)

Le script exige un **tty** : la démonstration l'a piloté dans un **vrai pseudo-terminal**
(`pty.fork`), avec un mot de passe **fictif généré**, jamais écrit dans le dépôt ni affiché.
Sortie réelle :

```console
Mot de passe pour 'exploitant-l6@demo.invalid' (saisie masquée) :
Confirmez le mot de passe (saisie masquée) :
OK — provisionnement effectué.
  client_id             : bd784710-c641-4d12-a2ea-7973b6df0fc8
  utilisateur_id        : f7cf2e47-4ba5-431e-9622-e03d33e05488
  identifiant_connexion : exploitant-l6@demo.invalid
  nom_affichage         : Exploitant FICTIF L6
  libelle_client        : Client fictif — DÉMONSTRATION L6
Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. Longueur
minimale exigée : 12 caractères.

[pty] saisies envoyées : 2 | code de sortie : 0
```

Les deux objets sont en base :

```
              client              |   identifiant_connexion    |    nom_affichage
----------------------------------+----------------------------+----------------------
 Client fictif — DÉMONSTRATION L6 | exploitant-l6@demo.invalid | Exploitant FICTIF L6
(1 row)

empreintes de mots de passe en base : 1 ligne(s) hachée(s) — aucune valeur en clair
```

Le compte créé **se connecte réellement** par la route gelée :

```console
POST /api/v1/connexion -> HTTP 200
{"utilisateur_id":"f7cf2e47-…","client_id":"bd784710-…","nom_affichage":"Exploitant FICTIF L6"}
```

---

## 7. Démarrer une bibliothèque : interface **et** API

C'est le geste décrit par l'annexe C § C2 volet 1 — les deux chemins ont été exécutés.

**Par l'API** (cookie de session) :

```console
GET  /api/v1/bibliotheque (avant) -> HTTP 404
{"detail":"Aucune fiche de bibliothèque pour ce client. Provisionnez une entreprise et une version de fiche avant d'appeler ces routes."}

POST /api/v1/entreprises -> HTTP 201
{"entreprise_id":"af1d301e-…","fiche_version_id":"37df9052-…","numero_version":1,"statut":"vierge"}

POST /api/v1/entreprises/af1d301e-…/fiches -> HTTP 201
{"fiche_version_id":"cbe122c7-…","numero_version":2,"statut":"vierge"}

GET  /api/v1/entreprises -> HTTP 200
{"entreprises":[{"entreprise_id":"af1d301e-…","libelle_court":"Entreprise fictive — DÉMONSTRATION L6",…}]}

GET  /api/v1/bibliotheque (après) -> HTTP 200   (plus de cul-de-sac)
```

**Par l'interface** (écrans rendus côté serveur, sans JavaScript) :

```console
GET  /connexion                 -> HTTP 200  (<title>Connexion — ia-consultations-publiques</title>)
POST /connexion (formulaire)    -> HTTP 200, cookie de session posé
GET  /entreprises/nouvelle      -> HTTP 200  (champ libelle_court présent)
POST /entreprises (formulaire)  -> HTTP 200

état en base :
                   libelle_court                   | numero_version | statut
---------------------------------------------------+----------------+--------
 Entreprise fictive via l'écran — DÉMONSTRATION L6 |              1 | vierge
```

---

## 8. Annulation des migrations (`down`) — documentée **et exécutée**

```console
$ python -m app.storage.migrations down
Migrations annulées : 0004       -> tables restantes : 36
$ python -m app.storage.migrations down
Migrations annulées : 0003       -> tables restantes : 34
$ python -m app.storage.migrations down
Migrations annulées : 0002       -> tables restantes : 16
$ python -m app.storage.migrations down
Migrations annulées : 0001       -> tables restantes : 1

$ python -m app.storage.migrations statut
0001  en attente
0002  en attente
0003  en attente
0004  en attente

$ python -m app.storage.migrations down      # une annulation de trop
Migrations annulées : aucune                 -> code 0, aucune erreur

$ python -m app.storage.migrations up
Migrations appliquées : 0001, 0002, 0003, 0004   -> 38 tables
```

**Conséquence observée, et documentée comme telle** : l'annulation a **effacé** le client
et le compte provisionnés au § 6 (les tables sont supprimées). `INSTALLATION.md` § 7 le dit
explicitement : `down` **détruit les données** et n'est pas un geste d'exploitation.

---

## 9. Jeu de démonstration fictif

```console
$ psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0001_jeu_fictif.sql
BEGIN / INSERT 0 2 / … / COMMIT
-> code 0

tables non vides après le jeu :
 abonnement 2 | client 2 | document 2 | dossier 2 | entreprise 2 | evenement_facturation 2
 evenement_facturation_dossier 1 | fiche_famille 3 | fiche_version 2 | jeu_reference 29
 tracabilite_valeur 2 | utilisateur 2 | valeur_reference 98 | validation_relecture 1
 authentification 0   (volontairement vide : aucune empreinte, même fictive, dans le dépôt)

libellés présents : FICTIF — Client A (jeu de test L7) / FICTIF — Client B (jeu de test L7)
```

Aucune donnée réelle ; le jeu est idempotent et ne permet pas de se connecter (comptes
absents) — c'est indiqué dans `INSTALLATION.md` § 11.

---

## 10. Suite de tests — exécutée sur une base dédiée

```console
$ createdb -h 127.0.0.1 -p 5432 ia_consultations_l6_tests
$ TEST_DATABASE_URL="postgresql://…/ia_consultations_l6_tests" python -m pytest -q
…
167 passed, 1 warning in 11.06s

$ python -m pytest tests/test_web.py -q
14 passed, 1 warning in 1.62s
```

`tesseract` étant présent avec la langue `fra`, le test de lecture d'une page **scannée**
(`test_page_scannee_lue_par_ocr_ou_declaree_non_testee`) n'est **pas sauté** : aucun
`skipped` dans le résumé. La brique **OCR est donc couverte** à l'installation ; c'est un
point qu'aucun rapport précédent n'avait démontré (L5 signalait l'OCR « non exercé » dans
sa démonstration).

Le seul avertissement est une dépréciation `starlette`/`httpx` héritée de L1.

---

## 11. Sauvegarde et restauration — exécutées

```console
$ SAUVEGARDE_REPERTOIRE=…/l6/sauvegardes SAUVEGARDE_CLE_FICHIER=…/l6/cle-sauvegarde \
      scripts/sauvegarde.sh --base "$DATABASE_URL" --documents data
Sauvegarde terminée.
  répertoire         : …/l6/sauvegardes/20260930-122528
  base               : ia_consultations_l6
  base chiffrée      : 160 Kio  (55024854…1f731f56)
  documents chiffrés : 14392 Kio (851a2321…e47a045af)
  documents en clair : 19188 Kio (lus en place, jamais recopiés en clair)
  manifeste chiffré  : manifeste.tar.gz.enc (6142c2d9…24bb338f)
  rien en clair      : vérifié, aucun fichier non chiffré dans la destination
-> code 0

$ scripts/restauration.sh --sauvegarde …/sauvegardes/derniere \
      --base-cible ia_consultations_l6_restauration_test \
      --repertoire-fichiers …/l6/documents-restaures --base "$DATABASE_URL"
base.dump.enc: OK
documents.tar.gz.enc: OK
manifeste.tar.gz.enc: OK
Comptage de lignes — table par table
table                       sauvegarde  source(now)  restaurée  verdict
client                               3            3          3  identique
utilisateur                          3            3          3  identique
valeur_reference                    98           98         98  identique
… (38 tables, toutes « identique ») …
Fichiers — 359 fichier(s) attendu(s)
  tous les fichiers restaurés portent l'empreinte attendue  : identique
RESTAURATION VÉRIFIÉE : … comptages de lignes identiques table par table, 359 fichier(s) conforme(s).
-> code 0
```

La clé de sauvegarde employée est **fictive**, créée hors dépôt (permissions 600) pour la
seule démonstration. Les archives produites sont **hors du dépôt**.

---

## 12. Points durs, erreurs rencontrées et défauts signalés

**Règle tenue** : un défaut constaté est écrit ici **et** signalé par un commentaire sur la
carte `t_afa55c06` ; le code de production n'est pas corrigé à la place des autres lots.

### 12.1 Défaut réel : `.env` n'est pas lu par le code Python (majeur pour l'installation)

`src/app/config.py` lit `os.environ` et n'appelle **aucun** chargeur de `.env` — alors que
`.env.example` demande de « copier en `.env` ». Constat par exécution :

```console
$ cd src && ../.venv/bin/python -m app.storage.migrations statut
[config] Variables d'environnement obligatoires absentes : DATABASE_URL,
CLE_CHIFFREMENT_MAITRESSE, CLE_SESSION. Copiez `.env.example` vers `.env`…
-> code 2
```

*Contournement documenté et vérifié* : `set -a; . ./.env; set +a` avant les commandes hors
serveur, ou `--env-file ../.env` avec uvicorn (journal `Loading environment from '../.env'`).
*Fichiers concernés, non modifiés* : `.env.example` (message), `src/app/config.py`
(message d'erreur), `src/app/main.py` (docstring de démarrage, qui n'emploie pas
`--env-file`).

### 12.2 Erreurs normales, documentées pour ne pas être confondues avec une panne

- `NOTICE: database "…" does not exist, skipping` — émis par `dropdb --if-exists` ; ce n'est
  pas une erreur.
- `down` suivi de `up` efface les données : comportement normal, dangereux en exploitation.
- Le provisionnement **exige un tty** : lancé sans terminal, la saisie masquée échoue. C'est
  la contrepartie assumée du refus du mot de passe en argument.
- Les binaires de `Postgres.app` ne sont pas dans le `PATH` par défaut : sans préfixe de
  `PATH`, `createdb` est introuvable.

### 12.3 Défauts antérieurs, reconduits sans être corrigés (hors périmètre du lot)

1. **SQL hors de `storage/`** — ordres SQL dans `services/checklist.py`,
   `services/analyse_dce.py`, `services/authentification.py`. Constat déjà posé par L2 § 10
   et L2bis § 5 ; reste ouvert. Documenté comme piège dans `DEVELOPPEMENT.md` § 2 et § 7.
2. **Base de test partagée** — `src/tests/conftest.py` vise `ia_consultations_test` par
   défaut : deux lots simultanés se marchent dessus. Contourné ici par
   `TEST_DATABASE_URL` dédiée ; signalé comme **point chaud** dans `DEVELOPPEMENT.md` § 7.
3. **Point chaud `src/app/main.py`** — cinquième lot consécutif à y ajouter quelque chose
   (L2, L3, L4, L2bis, L5). Signalé dans `DEVELOPPEMENT.md` § 7.
4. **Absence de contrainte croisée `(client_id, entreprise_id)` sur `fiche_version`**
   (risque R14) : fermé applicativement seulement. Documenté comme piège.
5. **`src/README.md` et `src/migrations/README.md` datent de la phase 1** : ils décrivent un
   « squelette » sans base ni logique, un emplacement de base « SQLite (proposition) » et
   « aucune migration appliquée ». C'est **faux** depuis les lots L1–L5 : les deux nouveaux
   documents renvoient donc à ce qui existe **réellement** et ne se fondent pas sur ces
   deux fichiers de phase 1. (Signalé, non corrigé : ces fichiers de cadrage ne se
   réécrivent pas sans décision.)

---

## 13. Vérifications d'exigence

| Exigence de la carte | Preuve |
|---|---|
| 1. Procédure d'installation suivie ligne par ligne sur une base **neuve**, application qui **répond** | § 2 → § 7 ci-dessus : base `ia_consultations_l6` créée à zéro, venv neuf, 38 tables, `GET /` = 200, cookie de session, parcours complet. Erreurs rencontrées et corrigées : § 12 |
| 2. Procédure `down` **documentée et exécutée** | § 8 : quatre annulations successives jusqu'à 1 table, sur-annulation sans erreur, remise en place ; `INSTALLATION.md` § 7 |
| 3. Aucune fonctionnalité affirmée qui n'existe pas | Chaque affirmation des deux documents renvoie à un fichier du dépôt (`src/app/...`, `src/migrations/...`, `scripts/...`) ou à une sortie de ce rapport. Contrôle automatisé : **131 références** de fichiers citées dans les trois documents, **115 noms de fichiers retrouvés** dans le dépôt, **aucune référence introuvable** (seule exception, volontaire : le gabarit de convention `` `000N_description.sql` ``) |
| 4. Aucun secret dans les deux documents | `INSTALLATION.md` et `DEVELOPPEMENT.md` ne contiennent que des **noms** de variables ; contrôle § 14 |
| Ajout de périmètre : provisionnement documenté **et** exécuté | § 6 : refus de `--mot-de-passe` (code 2, 0 client créé), provisionnement en pty, connexion `200` du compte créé |
| Ajout de périmètre : démarrage de la bibliothèque depuis l'interface | § 7 : `POST /entreprises` par formulaire → entreprise + version 1 en base, **et** les routes `§ C2` par l'API |

---

## 14. Contrôles sur les livrables

Contrôle exécuté après écriture des documents (`…/l6/11-controle.sh`) — sortie réelle :

```console
# --- 1. les valeurs réellement générées apparaissent-elles dans les documents ? ---
  DATABASE_URL : absent des documents (valeur de 53 caractères) ✓
  CLE_CHIFFREMENT_MAITRESSE : absent des documents (valeur de 44 caractères) ✓
  CLE_SESSION : absent des documents (valeur de 64 caractères) ✓
valeurs retrouvées : 0

# --- 2. motifs de secret (clé = valeur non vide en .md) ---
docs/RAPPORTS/L6-documentation.md:101:DATABASE_URL=<valeur locale, non affichée>
… 8 lignes, toutes de la forme « NOM=<valeur locale, non affichée> » (aucune valeur)

# --- 3. formule de confidentialité interdite ---
  absente des documents ✓

# --- 4. mentions de garanties non tenables ---
  aucune promesse de garantie ✓
```

Lecture : les **seules** lignes « `NOM=valeur` » des documents sont les huit lignes
volontairement **masquées** du § 4 de ce rapport (`<valeur locale, non affichée>`). Aucune
valeur générée (chaîne de connexion, clé maîtresse, secret de session, mot de passe) ne se
retrouve dans un livrable.

- **Aucune donnée réelle** : tous les libellés des sorties jointes portent « FICTIF » ou
  « DÉMONSTRATION » ; les adresses sont en `.invalid` (domaine non routable).
- **Aucune promesse de confidentialité** : les deux documents ne formulent rien sur ce
  sujet et renvoient à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 10 ; la formule interdite
  n'y apparaît **pas** (contrôle ci-dessus, ligne 3).
- **Rien n'a été déployé** : écoute `127.0.0.1` uniquement, serveur arrêté après chaque
  démonstration (`curl` → code `000`), rien ne reste à l'écoute.
- **Bases créées pour la démonstration** : `ia_consultations_l6`,
  `ia_consultations_l6_tests`, `ia_consultations_l6_restauration_test`. Elles peuvent être
  retirées par `dropdb` ; elles restent en place car elles ne contiennent que des données
  fictives.
- **Fichiers temporaires** : le `.env` de démonstration, les sauvegardes, la clé de
  sauvegarde, les documents restaurés et l'environnement virtuel de démonstration sont
  **hors du dépôt** (répertoire de travail de l'agent). Le `.env` écrit à la racine du
  dépôt pendant la démonstration a été **supprimé** à la fin du lot.

---

## 15. Ce qui n'a pas été fait, et limites assumées

1. **Aucune mise en production, aucun déploiement, aucun port exposé.** Rien n'a été
   provisionné chez un hébergeur.
2. **Le fournisseur de modèle réel (France/UE) n'a pas été exercé** : la démonstration
   emploie le fournisseur **factice** (`MODELE_FOURNISSEUR=factice`, sans réseau), qui est
   le défaut. Aucune clé n'existe pour tester le chemin `ue`.
3. **Aucune garantie de conformité n'est énoncée** dans les deux documents — ni ici :
   la conformité est une démarche, pas un label que l'éditeur s'attribue seul.
4. **La documentation ne remplace pas la relecture humaine des actes engageants** : le
   produit ne dépose rien, ne signe rien, ne paie rien, et les sorties portent la mention
   « brouillon — à relire et à signer ».
5. **Le dépôt n'a pas été commité** : c'est cohérent avec les lots précédents, mais les
   deux nouveaux documents sont pour l'instant **non versionnés** (comme le reste de la
   phase 3).
6. **`src/README.md` et `src/migrations/README.md` restent périmés** (§ 12.3.5) : leur mise
   à jour n'était pas demandée et modifier un document de cadrage sans décision est
   interdit — le point est signalé, pas tranché.

---

*Fin du rapport L6.*
