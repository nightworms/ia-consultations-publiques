# L1 — Socle technique : rapport d'exécution

*Lot L1, phase 3. Rédigé le 30 septembre 2026. Toutes les sorties ci-dessous
proviennent de commandes réellement lancées sur la machine de développement
(macOS 27.0.1, arm64, PostgreSQL 18.3 local). Rien n'est extrapolé d'une lecture
de code.*

---

## 1. Ce qui a été livré

| Livrable (chemin exact) | État |
|---|---|
| `.env.example` | créé — toutes les variables, commentées, **aucune valeur secrète** |
| `src/requirements.txt` | créé — dépendances épinglées (annexe A § A10) |
| `src/app/config.py` | créé — lecture stricte, échec explicite si variable manquante |
| `src/app/storage/connexion.py` | créé — point d'entrée unique du SQL, exige un contexte client |
| `src/app/storage/migrations.py` | créé — exécuteur `up`/`down`, sans ORM |
| `src/migrations/0001_init_socle.sql` | créé — 14 tables + table d'authentification, sections up **et** down |
| `src/app/securite/chiffrement.py` | créé — AES-256-GCM, clé dérivée par `client_id` (HKDF), format `v1:` |
| `src/app/securite/mots_de_passe.py` | créé — Argon2id |
| `src/app/storage/fichiers.py` | créé — stockage hors dépôt, préfixé par client, chiffré |
| `src/app/services/authentification.py` | créé — compte local, mot de passe haché |
| `src/app/api/routes_authentification.py` | créé — `/api/v1/connexion`, `/api/v1/deconnexion` |
| `src/app/api/cloisonnement.py` | créé — dépendance obligatoire posant le `client_id` |
| `src/app/main.py` | récrit — `app = FastAPI()` réellement exécutable |
| `src/tests/conftest.py`, `src/tests/test_socle.py` | créés — 24 tests, tous verts |
| `docs/RAPPORTS/L1-socle.md` | ce document |

Modifications annexes : `.gitignore` (ajout de `!.env.example` — voir § 8),
`src/app/securite/__init__.py` (paquet).

---

## 2. Environnement : ce qui a été installé ou démarré

Annoncé et justifié avant exécution, conformément à la contrainte commune.

1. **Python 3.12** — absent de la machine (annexe D). Installé par Homebrew :

   ```
   $ brew install python@3.12
   ==> Installing python@3.12
   🍺  /opt/homebrew/Cellar/python@3.12/3.12.14: 3,615 files, 68.4MB
   ```

   Environnement virtuel créé **dans le projet, hors dépôt** (`.venv/`, ignoré par
   git) avec l'interpréteur ainsi obtenu.

2. **Dépendances** — liste autorisée annexe A § A10, installées dans `.venv` :
   `fastapi 0.142.1`, `uvicorn[standard] 0.54.0`, `jinja2 3.1.6`,
   `psycopg[binary] 3.3.6`, `pydantic 2.13.5`, `cryptography 50.0.1`,
   `argon2-cffi 25.1.0`, `itsdangerous 2.2.0`, `python-multipart 0.0.32`,
   `pytest 9.1.1`, `httpx 0.28.1`. Aucune dépendance hors liste.

3. **PostgreSQL** — instance **Postgres.app** existante (var-18), démarrée sur
   l'écoute locale uniquement :

   ```
   $ pg_ctl -D "$HOME/Library/Application Support/Postgres/var-18" start
   server started
   LOG:  listening on IPv6 address "::1", port 5432
   LOG:  listening on IPv4 address "127.0.0.1", port 5432
   LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
   ```

   Deux bases créées, locales : `ia_consultations` (applicative) et
   `ia_consultations_test` (tests). **Aucun port exposé sur Internet** :
   `listen_addresses` reste `localhost`, les deux adresses écoutées sont `::1` et
   `127.0.0.1`. Ce démarrage est manuel et **non persistant** (voir § 7, chemin R2).

---

## 3. Exigence 1 — les migrations s'appliquent (`up`) et s'annulent (`down`)

Commande réellement lancée (depuis `src/`, variables d'environnement locales) :

```
$ python -m app.storage.migrations statut
0001  en attente

$ python -m app.storage.migrations up
Migrations appliquées : 0001

$ psql -h 127.0.0.1 -U pause -d ia_consultations -c "\dt"
 Schema |             Name              | Type  | Owner
--------+-------------------------------+-------+-------
 public | abonnement                    | table | pause
 public | authentification              | table | pause
 public | client                        | table | pause
 public | document                      | table | pause
 public | dossier                       | table | pause
 public | entreprise                    | table | pause
 public | evenement_facturation         | table | pause
 public | evenement_facturation_dossier | table | pause
 public | fiche_famille                 | table | pause
 public | fiche_version                 | table | pause
 public | jeu_reference                 | table | pause
 public | schema_migration              | table | pause
 public | tracabilite_valeur            | table | pause
 public | utilisateur                   | table | pause
 public | valeur_reference              | table | pause
 public | validation_relecture          | table | pause
(16 rows)

$ python -m app.storage.migrations down 1
Migrations annulées : 0001

$ psql -h 127.0.0.1 -U pause -d ia_consultations -c "\dt"
 Schema |       Name       | Type  | Owner
--------+------------------+-------+-------
 public | schema_migration | table | pause
(1 row)

$ python -m app.storage.migrations up
Migrations appliquées : 0001
```

**Lecture du résultat.** Les 14 tables prévues + `authentification` (§ 5) +
`schema_migration` sont créées par `up` et **toutes** supprimées par `down`, hors
`schema_migration` — table de tenue du journal de migrations, hors périmètre de
`0001` (elle appartient à l'exécuteur, elle accompagne le fichier SQL). Le cycle
`down` puis `up` est reproductible.

Le test `test_migrations_down_puis_up` (pytest) vérifie le même comportement de
façon programmatique, y compris l'absence puis la présence de la table `client`.

---

## 4. Exigence 2 — lecture des données d'un autre client : échec démontré

Le cloisonnement n'est pas déclaratif : `storage/connexion.py` **refuse** toute
requête sans contexte client et **impose** la valeur du `client_id` depuis le
contexte de session, écrasant toute valeur fournie par l'appelant.

Extrait de la sortie `pytest` (tests réellement exécutés contre PostgreSQL) :

```
tests/test_socle.py::test_lecture_impossible_des_donnees_d_un_autre_client PASSED
tests/test_socle.py::test_falsifier_client_id_est_sans_effet PASSED
tests/test_socle.py::test_requete_sans_filtre_client_refusee PASSED
tests/test_socle.py::test_requete_sans_contexte_client_refusee PASSED
```

Ce que ces tests démontrent, sur des lignes réellement insérées :

* avec le contexte du client A, une requête filtrée sur le `client_id` de A **ne
  renvoie jamais** la ligne de B (lecture par identifiant ciblé : 0 ligne) ;
* fournir `client_id = <B>` en paramètre **n'a aucun effet** : le contexte prime,
  A ne voit que ses données ;
* une requête sans filtre `%(client_id)s` lève `ErreurCloisonnement` ;
* une requête sans contexte client lève `ContexteClientManquant`.

---

## 5. Exigence 3 — deux clients ne peuvent pas se déchiffrer mutuellement

Clé de données **dérivée par client** (HKDF-SHA256, sel = `client_id`, annexe A
§ A6). Un client ne peut donc pas produire la clé d'un autre.

```
tests/test_socle.py::test_chiffrement_aller_retour PASSED
tests/test_socle.py::test_deux_clients_ne_peuvent_pas_se_dechiffrer PASSED
tests/test_socle.py::test_cles_derivees_different_par_client PASSED
tests/test_socle.py::test_chiffrement_non_deterministe PASSED
tests/test_socle.py::test_dechiffrement_refuse_une_alteration PASSED
tests/test_socle.py::test_fichier_d_un_client_illisible_par_un_autre PASSED
```

Démontré : une valeur chiffrée au nom de A, relue avec la clé dérivée pour B,
lève `ErreurDechiffrement` (échec d'authentification GCM). Les clés dérivées de
deux clients diffèrent. Le chiffrement est non déterministe (nonce aléatoire), et
une altération d'un seul octet est détectée.

---

## 6. Exigence 5 — l'application démarre réellement (uvicorn)

Commande et sortie réelles :

```
$ .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8123
INFO:     Started server process [67637]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8123 (Press CTRL+C to quit)

$ curl -s -i http://127.0.0.1:8123/
HTTP/1.1 200 OK
content-type: application/json

{"application":"ia-consultations-publiques","version":"0.1.0","documentation":"/docs"}

$ curl -s -i -X POST http://127.0.0.1:8123/api/v1/connexion \
    -H 'Content-Type: application/json' \
    -d '{"identifiant":"inconnu@fictif.test","mot_de_passe":"peu-importe"}'
HTTP/1.1 401 Unauthorized
{"detail":"Identifiant ou mot de passe incorrect."}

$ curl -s -i -X POST http://127.0.0.1:8123/api/v1/deconnexion
HTTP/1.1 200 OK
set-cookie: session=""; expires=...; Max-Age=0; Path=/; SameSite=lax
{"statut":"deconnecte"}
```

Le serveur démarre, sert la racine, refuse une connexion invalide (401) et
efface le cookie de session. Il est lancé sur `127.0.0.1` : **rien n'est exposé**.

---

## 7. Suite de tests — sortie complète

```
$ cd src && ../.venv/bin/python -m pytest -v tests/
platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
collected 24 items

tests/test_socle.py::test_config_echoue_si_variable_obligatoire_absente PASSED
tests/test_socle.py::test_config_echoue_si_cle_maitresse_invalide PASSED
tests/test_socle.py::test_config_charge PASSED
tests/test_socle.py::test_lecture_impossible_des_donnees_d_un_autre_client PASSED
tests/test_socle.py::test_falsifier_client_id_est_sans_effet PASSED
tests/test_socle.py::test_requete_sans_filtre_client_refusee PASSED
tests/test_socle.py::test_requete_sans_contexte_client_refusee PASSED
tests/test_socle.py::test_contexte_client_refuse_un_identifiant_invalide PASSED
tests/test_socle.py::test_chiffrement_aller_retour PASSED
tests/test_socle.py::test_deux_clients_ne_peuvent_pas_se_dechiffrer PASSED
tests/test_socle.py::test_cles_derivees_different_par_client PASSED
tests/test_socle.py::test_chiffrement_non_deterministe PASSED
tests/test_socle.py::test_dechiffrement_refuse_une_alteration PASSED
tests/test_socle.py::test_hachage_et_verification_mot_de_passe PASSED
tests/test_socle.py::test_mot_de_passe_trop_court_refuse PASSED
tests/test_socle.py::test_fichiers_aller_retour_et_contenu_chiffre PASSED
tests/test_socle.py::test_fichier_d_un_client_illisible_par_un_autre PASSED
tests/test_socle.py::test_chemin_refuse_identifiant_invalide PASSED
tests/test_socle.py::test_creation_compte_connexion_et_session PASSED
tests/test_socle.py::test_application_demarre_et_sert_la_racine PASSED
tests/test_socle.py::test_routes_connexion_et_deconnexion PASSED
tests/test_socle.py::test_dependance_cloisonnement_401_puis_200 PASSED
tests/test_socle.py::test_migrations_lister_0001 PASSED
tests/test_socle.py::test_migrations_down_puis_up PASSED

======================== 24 passed, 1 warning in 0.63s ========================
```

Le seul avertissement est une dépréciation de Starlette sur `httpx` dans son
`TestClient` — sans effet sur le socle.

---

## 8. Exigence 4 — aucun secret dans le dépôt

Recherche de motifs réellement exécutée (hors `.venv`, `.git`, `__pycache__`) :

| Motif recherché | Résultat |
|---|---|
| clés privées `BEGIN ... PRIVATE KEY` | aucune correspondance |
| jetons usuels (`AKIA…`, `ghp_…`, `xox…`, `sk-…`) | aucune correspondance |
| affectations `mot_de_passe/password/secret/api_key/token = "…"` | aucune correspondance |
| chaîne de connexion avec mot de passe (`://user:pwd@`) | aucune correspondance |
| jetons JWT (`eyJ….`) | aucune correspondance |

`.venv/`, `data/` et `.env` sont bien ignorés par git (vérifié par
`git check-ignore -v`).

**Correction apportée** : la règle `.env.*` du `.gitignore` masquait aussi
`.env.example`, qui doit être versionné. Ajout de `!.env.example`. Vérifié :
`.env.example` n'est plus ignoré.

Les valeurs d'environnement présentes dans `src/tests/conftest.py` sont des
**valeurs de test explicitement fictives** (clé maîtresse 32 octets littérale
commentée « clé FICTIVE de test », secret de session de test) — ce ne sont pas des
secrets de production, et aucune valeur réelle n'existe dans le dépôt.

---

## 9. Décisions appliquées faute d'être couvertes par les annexes

Signalées par commentaire sur la carte Kanban (annexe A, règle de conduite), et
appliquées au plus simple :

1. **Table `authentification` séparée.** `docs/DATA-MODEL-V2.md` § 5.2 exclut tout
   mot de passe des tables de contenu, alors que l'annexe A § A5 exige un mot de
   passe haché. Résolution : une table dédiée `authentification`
   (`utilisateur_id` unique, empreinte Argon2id), `client_id` non nul.
2. **`client_id` ajouté à `evenement_facturation_dossier`.** Le § 11.4 ne le liste
   pas, mais l'annexe A § A1 l'exige « sur toute entité de contenu, y compris
   déductible par jointure ». A1 prime : colonne ajoutée.
3. **Colonnes techniques communes (§ 3.2)** appliquées aux entités de contenu
   (`document`, `fiche_famille`, `validation_relecture`, `dossier`,
   `tracabilite_valeur`) : `date_creation`, `date_modification`, `sensibilite`,
   `statut_enregistrement`.
4. **Aucune contrainte `CHECK` sur les `code_reference`.** Les jeux de référence
   sont des **données** (§ 8.5 : « rien de métier n'entre jamais dans le schéma »)
   ; leur contenu appartient à L5. La résolution des codes est laissée à
   l'application et au jeu de données, pas figée dans le schéma.
5. **Deux points d'entrée SQL hors contexte client, nommés et bornés** : la
   recherche d'identité à la connexion (le client n'est pas encore connu) et la
   provision d'un `client` (racine du cloisonnement, sans `client_id`). SQL figé,
   sans concaténation, sans donnée de contenu — documentés comme exceptions.
6. **Vocabulaire « booléens 0/1 »** (annexe A § A2) appliqué littéralement :
   colonnes `smallint` avec `CHECK (…) IN (0,1)`.

---

## 10. Ce qui reste à faire / limites assumées

- **Démarrage de PostgreSQL non persistant.** L'instance a été démarrée à la main
  (`pg_ctl`) pour ce lot ; elle ne redémarre pas automatiquement. Deux chemins
  documentés : (a) relancer l'instance Postgres.app existante, données déjà
  initialisées sous `~/Library/Application Support/Postgres/var-18` (sur volume
  externe — dépend que le disque soit monté, risque R2) ; (b) `initdb` d'une base
  neuve sous le disque interne, hors dépôt. Aucun des deux n'est câblé dans le
  projet (hors périmètre L1).
- **Aucun écran HTML ni route de contenu.** Les écrans et les routes
  `/api/v1/bibliotheque`, `/api/v1/consultations` appartiennent aux lots L4/L5/L6.
  L1 livre la surface d'authentification et le socle.
- **`src/app/storage/repositories.py`, `src/app/api/routes.py`** restent les
  squelettes de la phase 1 (levées `NotImplementedError`) — remplis par les lots
  suivants, pas par L1.
- **`src/README.md`** décrit encore le squelette de phase 1 ; non mis à jour pour
  éviter un conflit avec les autres lots (à réviser en fin de phase 3).
- **Jeux de référence non semés.** La structure `jeu_reference` / `valeur_reference`
  existe ; le contenu (même les listes « fermées » du § 8.6) n'est **pas** semé par
  `0001`. Le semis n'est nommément attribué à aucun lot ; à confier à L5 ou à une
  carte dédiée.
- **`secure=False` sur le cookie de session** : localhost sans TLS. À passer à
  `True` derrière HTTPS, en production.

---

## 11. Vérifié / supposé

**Vérifié par exécution** : installation Python 3.12 ; démarrage PostgreSQL ;
création des bases ; migrations `up`/`down` (CLI + pytest) ; cloisonnement
(tests) ; chiffrement par client (tests) ; hachage Argon2id (tests) ; stockage
fichier chiffré (tests) ; authentification et session (tests) ; démarrage uvicorn
et réponses HTTP ; absence de secrets (recherche de motifs).

**Non vérifié / supposé** : la persistance du serveur PostgreSQL au redémarrage de
la machine (non traitée) ; le comportement derrière HTTPS (`secure=True`) ; les
performances et la montée en charge.
