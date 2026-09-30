# L2bis — Provisionnement (entreprise + fiche) et script d'exploitant : rapport d'exécution

Lot **L2bis** de la phase 3 (`docs/PLAN-PHASE-3.md`, annexe C § C2, décision figée par la
tâche `t_5b51c472`). Toutes les sorties de ce rapport proviennent de commandes réellement
exécutées sur cette machine ; aucune n'est déduite de la lecture du code.

**Aucune donnée réelle.** Les clients, entreprises, identifiants et mots de passe utilisés
sont **fictifs et signalés** (« DÉMONSTRATION »). Aucun secret réel n'apparaît dans ce
document, dans le dépôt, ni dans un fichier du dépôt. Le mot de passe fictif de la
démonstration n'est reproduit nulle part : il n'a été saisi qu'au clavier masqué.

---

## 1. Ce qui a été livré

| Fichier | Nature |
|---|---|
| `src/app/api/routes_provisionnement.py` | les **trois** routes de l'annexe C § C2 |
| `src/app/main.py` | montage du routeur (2 lignes : import + `include_router`) |
| `scripts/provisionnement.py` | script d'exploitant (racine : `client` + compte d'accès) |
| `src/tests/test_provisionnement.py` | 15 tests, exécutés contre PostgreSQL local |
| `docs/RAPPORTS/L2bis-provisionnement.md` | ce rapport |

### 1.1 Les trois routes (§ C2, volet 1)

| Méthode | Chemin | Réponse |
|---|---|---|
| `POST` | `/api/v1/entreprises` | `201 {entreprise_id, fiche_version_id, numero_version, statut}` |
| `GET` | `/api/v1/entreprises` | `200 {entreprises: [{entreprise_id, libelle_court, statut, derniere_fiche}]}` |
| `POST` | `/api/v1/entreprises/{entreprise_id}/fiches` | `201 {fiche_version_id, numero_version, statut}` |

`POST /api/v1/entreprises` écrit l'`entreprise` **et** sa première `fiche_version` dans
**une seule transaction** : les deux appels partagent la connexion de la requête, et un
échec de la seconde écriture déclenche `annuler()` — aucune entreprise orpheline n'est
laissée derrière.

### 1.2 Le script d'exploitant (§ C2, volet 2)

`scripts/provisionnement.py` crée, dans **une seule transaction** :

1. le `client` par `Connexion.creer_client(libelle)` (exception nommée et bornée de L1) ;
2. le premier compte d'accès par
   `ServiceAuthentification.creer_utilisateur(ContexteClient(client_id), identifiant,
   nom_affichage, mot_de_passe)`.

Mot de passe **saisi au clavier en saisie masquée** (`getpass`), demandé deux fois (ajout
délibéré, voir § 7). `--mot-de-passe` est **déclaré pour être refusé** : la commande
s'arrête avec un message explicite et le code de sortie `2`, sans toucher la base. Le mot
de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier, ni posé en variable
d'environnement. La sortie ne contient que des identifiants techniques (UUID).

---

## 2. Environnement et dépendances

**Aucune dépendance nouvelle.** Le lot n'ajoute ni bibliothèque, ni migration, ni table :
il n'appelle que `ServiceBibliotheque.creer_entreprise()`, `ouvrir_fiche()`,
`dernieres_fiches()`, `DepotEntreprise.lister/obtenir`, `Connexion.creer_client` et
`ServiceAuthentification.creer_utilisateur` — tous livrés par L1 et L2. La liste autorisée
(annexe A § A10) n'est donc pas sollicitée.

Base de démonstration : `ia_consultations_l2bis`, créée pour l'occasion, migrations
`0001`→`0004` appliquées, **supprimée après la démonstration**. Application démarrée
**localement** (`--host 127.0.0.1 --port 8099`), puis arrêtée. Rien n'est exposé sur
Internet.

```
$ createdb -h 127.0.0.1 -p 5432 ia_consultations_l2bis
$ cd src && ../.venv/bin/python -m app.storage.migrations up
Migrations appliquées : 0001, 0002, 0003, 0004
```

---

## 3. Exigences vérifiables — démonstration par exécution

### 3.1 Sans session → 401 sur les trois routes

```
== 1. sans session ==
POST /api/v1/entreprises                 -> 401
GET  /api/v1/entreprises                 -> 401
POST /api/v1/entreprises/<uuid>/fiches   -> 401
```

### 3.2 Provisionnement du client par le script (clic, clavier masqué)

Le script est lancé dans un **vrai terminal** ; le mot de passe est saisi au clavier, en
saisie masquée (rien ne s'affiche). Sortie réelle :

```
$ .venv/bin/python scripts/provisionnement.py \
      --libelle-client "Client fictif — DÉMONSTRATION L2bis A" \
      --identifiant "exploitant-a@demo.test" \
      --nom-affichage "Exploitant Fictif A"
Mot de passe pour 'exploitant-a@demo.test' (saisie masquée) :
Confirmez le mot de passe (saisie masquée) :
OK — provisionnement effectué.
  client_id             : dc6c6669-7a2a-43eb-81ff-969f5bdb4e94
  utilisateur_id        : a8560af6-4dc3-4266-935c-d802a74848dc
  identifiant_connexion : exploitant-a@demo.test
  nom_affichage         : Exploitant Fictif A
  libelle_client        : Client fictif — DÉMONSTRATION L2bis A
Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. Longueur
minimale exigée : 12 caractères.
```

Un second client fictif a été provisionné de la même façon (nécessaire au test
d'isolation de § 3.6) :

```
  client_id             : 305916fb-de6f-4353-add4-fbf1d81d9f6a
  utilisateur_id        : 0655dd86-aaa6-461e-96a0-6519ce196af4
  identifiant_connexion : exploitant-b@demo.test
```

**Refus d'un mot de passe en argument** (exigence explicite du § C2) :

```
$ .venv/bin/python scripts/provisionnement.py --libelle-client "Ne doit pas exister" \
      --identifiant "refuse@demo.test" --mot-de-passe "<un mot de passe en clair>"
REFUSÉ : un mot de passe ne doit jamais être passé en argument de ligne de commande (il
serait visible par `ps`). Relancez la commande sans `--mot-de-passe` : la saisie masquée
vous sera demandée.
code de sortie : 2
```

Aucun client « Ne doit pas exister » n'a été créé : le refus intervient avant toute
ouverture de connexion (vérifié par le test § 4, n° 6).

### 3.3 Connexion par `curl` (route gelée `/api/v1/connexion`)

```
== 2. connexion du client A (POST /api/v1/connexion) ==
{"utilisateur_id":"a8560af6-4dc3-4266-935c-d802a74848dc","client_id":"dc6c6669-7a2a-43eb-81ff-969f5bdb4e94","nom_affichage":"Exploitant Fictif A"}
HTTP 200
```

### 3.4 `GET /api/v1/bibliotheque` : 404 « Provisionnez une entreprise… », puis 200

Avant provisionnement — le `404` gelé, inchangé :

```
== 3. GET /api/v1/bibliotheque AVANT provisionnement ==
{"detail":"Aucune fiche de bibliothèque pour ce client. Provisionnez une entreprise et une version de fiche avant d'appeler ces routes."}
HTTP 404
```

Création de l'entreprise et de sa première fiche par l'API :

```
== 4. création entreprise + première fiche (POST /api/v1/entreprises) ==
{"entreprise_id":"c2b2011f-6a93-469d-8f43-b6f65d906398","fiche_version_id":"9ace46bf-ad91-4d7a-801a-08ac689536b3","numero_version":1,"statut":"vierge"}
HTTP 201
```

Après provisionnement — **le même appel ne renvoie plus 404** :

```
== 5. GET /api/v1/bibliotheque APRÈS provisionnement ==
{"fiche_version_id":"9ace46bf-ad91-4d7a-801a-08ac689536b3","statut":"vierge","statut_libelle":"Vierge","familles":[{"famille":"identite",... "nb_elements":0,"statut":"non_commencee","completude_famille":"incomplete"}, ...]}
HTTP 200
```

Lecture des entreprises du client, avec leur dernière version :

```
== 6. GET /api/v1/entreprises ==
{"entreprises":[{"entreprise_id":"c2b2011f-6a93-469d-8f43-b6f65d906398","libelle_court":"Entreprise fictive de A — DÉMONSTRATION","statut":"active","derniere_fiche":{"fiche_version_id":"9ace46bf-ad91-4d7a-801a-08ac689536b3","numero_version":1,"statut":"vierge"}}]}
```

### 3.5 Numérotation croissante **par entreprise** (jamais partagée)

```
== 7. deuxième puis troisième version de fiche (même entreprise) ==
{"fiche_version_id":"62622697-9d96-40ba-b94a-a5cfd16387c9","numero_version":2,"statut":"vierge"}  HTTP 201
{"fiche_version_id":"44ee0a8c-9c0e-4608-8845-6acdac2ce679","numero_version":3,"statut":"vierge"}  HTTP 201

== 8. deuxième entreprise du même client : numérotation repart à 1 ==
{"entreprise_id":"5f7fd8ec-8ca1-4f38-aeeb-837ae2ca0491","fiche_version_id":"37bfbe8d-db91-460f-8e90-b41e331bdb68","numero_version":1,"statut":"vierge"}  HTTP 201

== 9. données de la base (psql) ==
                  libelle_court                   | numero_version | statut
--------------------------------------------------+----------------+--------
 Entreprise fictive de A — DÉMONSTRATION          |              1 | vierge
 Entreprise fictive de A — DÉMONSTRATION          |              2 | vierge
 Entreprise fictive de A — DÉMONSTRATION          |              3 | vierge
 Deuxième entreprise fictive de A — DÉMONSTRATION |              1 | vierge
(4 rows)
```

### 3.6 Isolation : un client ne peut pas ouvrir de fiche sur l'entreprise d'un autre

Démonstration **par SQL avant/après**, exigence centrale du § C2 (risque R14) :

```
== 10. connexion du client B ==
{"utilisateur_id":"0655dd86-aaa6-461e-96a0-6519ce196af4","client_id":"305916fb-de6f-4353-add4-fbf1d81d9f6a","nom_affichage":"Exploitant Fictif B"}
HTTP 200

== 11. B voit ses propres entreprises (aucune) ==
{"entreprises":[]}
HTTP 200

== 12. B tente d'ouvrir une fiche sur l'entreprise de A ==
   comptage fiche_version AVANT :
3
{"detail":"Entreprise inconnue pour ce client. Aucune écriture n'a été effectuée."}
HTTP 404
   comptage fiche_version APRÈS (inchangé) :
3

== 13. aucune ligne fiche_version n'appartient au client B ==
                libelle                | fiches
---------------------------------------+--------
 Client fictif — DÉMONSTRATION L2bis A |      4
 Client fictif — DÉMONSTRATION L2bis B |      0
(2 rows)
```

La réponse est `404`, **jamais `403`** : elle ne révèle pas que l'entreprise existe
ailleurs. Le contrôle d'appartenance (`DepotEntreprise.obtenir`) est exécuté **avant**
l'appel à `ouvrir_fiche` ; le comptage SQL le confirme, aucune ligne n'est écrite.

### 3.7 `client_id` envoyé dans le corps : ignoré

```
== 15. client_id dans le corps : ignoré ==
{"entreprise_id":"bd288da1-a7ad-43db-8e38-8d82f81b3c29","fiche_version_id":"acef7336-4a19-4445-9455-f7452d45c51f","numero_version":1,"statut":"vierge"}

                  libelle_court                  |              client_id
-------------------------------------------------+--------------------------------------
 Entreprise avec client_id forgé — DÉMONSTRATION | dc6c6669-7a2a-43eb-81ff-969f5bdb4e94
(1 row)
```

Le `client_id` forgé (celui du client B : `305916fb-…`) est ignoré : la ligne appartient
au client de la **session** (`dc6c6669-…`). Le schéma Pydantic du corps déclare
`extra="ignore"` — c'est explicite, pas un effet de bord.

### 3.8 Les quatre routes gelées de la bibliothèque sont intactes

```
== 14. les quatre routes gelées de la bibliothèque, avec session (aucune renommée) ==
GET  /api/v1/bibliotheque                   -> 200
GET  /api/v1/bibliotheque/assurances        -> 200
{"detail":"Champs obligatoires manquants pour 'assurance' : ['type_assurance', 'date_debut', 'date_echeance', 'piece']"}
POST /api/v1/bibliotheque/assurances          -> 400
POST /api/v1/bibliotheque/validation        -> 200
```

Mêmes chemins, mêmes méthodes, mêmes codes, mêmes messages qu'avant L2bis. Le contrôle
est aussi posé en test sur le contrat OpenAPI (§ 4, n° 7).

---

## 4. Suite de tests

```
$ cd src && ../.venv/bin/python -m pytest tests/test_provisionnement.py -q --no-header
15 passed, 1 warning in 0.79s

$ ../.venv/bin/python -m pytest -q --no-header        # tout le dépôt (L1 + L3 + L2 + L2bis)
130 passed, 1 warning in 7.20s
```

L'unique avertissement est la dépréciation de `starlette.TestClient` déjà présente avant
ce lot (héritée de L1) ; elle est sans effet sur ces tests. Avant le lot, la suite comptait
115 tests : les 15 tests de L2bis s'ajoutent sans en casser aucun.

Couverture par exigence de l'énoncé du lot :

| Exigence | Test |
|---|---|
| 1. sans session → `401` sur les trois routes | `test_routes_provisionnement_refusent_sans_session` |
| 2. une `entreprise`, une fiche `numero_version = 1`, `statut = vierge` (SQL après coup) | `test_creation_entreprise_et_premiere_fiche` |
| 3. numéros 1, 2, 3… croissants par entreprise, jamais partagés | `test_numero_version_croissant_par_entreprise` |
| 4. entreprise d'un autre client → `404`, **aucune** ligne écrite (SQL après coup) | `test_second_client_ne_peut_pas_ouvrir_de_fiche` |
| 5. `client_id` du corps ignoré | `test_client_id_du_corps_est_ignore` |
| 6. script : refuse `--mot-de-passe`, accepte la saisie clavier, compte capable de se connecter (`POST /api/v1/connexion` → 200) | `test_script_refuse_un_mot_de_passe_en_argument`, `test_script_provisionne_un_compte_qui_se_connecte`, `test_script_refuse_des_saisies_differentes` |
| 7. les quatre routes de la bibliothèque répondent à l'identique | `test_contrat_openapi_inchange_pour_la_bibliotheque`, `test_bibliotheque_404_puis_parcours_complet_apres_provisionnement`, `test_routes_bibliotheque_refusent_toujours_sans_session`, `test_aucune_route_bibliotheque_renommee` |

Le test n° 6 est celui qui rend le provisionnement **crédible** : le compte créé par
`creer_client` + `creer_utilisateur` se connecte réellement par la route gelée
`/api/v1/connexion` (200), avec le `client_id` attendu.

Les tests s'exécutent contre PostgreSQL local ; les migrations sont appliquées puis
annulées autour de la session (`conftest.py`, fixture `base_migree`).

---

## 5. Contrôles de sécurité et de dépôt

**Aucun SQL nouveau, aucun SQL hors de `storage/`.**

```
$ grep -nE "(SELECT|INSERT[ ]INTO|UPDATE[ ]|DELETE[ ]FROM)" \
      src/app/api/routes_provisionnement.py scripts/provisionnement.py
→ aucun ordre SQL dans les deux fichiers du lot
```

Le lot ne modifie **aucune** migration, **aucune** table, et n'écrit pas une seule requête
SQL : tout passe par les fonctions de service et les dépôts livrés par L1 et L2.

**Aucun secret dans le dépôt.** Le mot de passe est saisi au clavier et n'existe qu'en
mémoire, le temps du hachage Argon2id ; il n'est jamais journalisé, affiché, écrit dans un
fichier, ni posé en variable d'environnement. Les seules valeurs d'environnement utilisées
pour la démonstration sont la chaîne de connexion locale, une clé de chiffrement et un
secret de session **de démonstration**, valeurs fictives, jamais commitées. Le fichier de
corps JSON utilisé pour la connexion `curl` (le mot de passe y figurait) a été créé **hors
du dépôt**, dans le répertoire de travail de l'agent, et supprimé après la démonstration.

**Aucun commit git** n'a été fait (cohérent avec les lots précédents).

**Aucune donnée réelle** : tous les libellés et identifiants de la démonstration portent la
mention « DÉMONSTRATION ».

**Rien n'a été déployé** : écoute `127.0.0.1` uniquement, serveur arrêté après la
démonstration, base de démonstration supprimée, aucun port exposé sur Internet.

**Point signalé, non corrigé (hors périmètre du lot).** La règle « aucun SQL hors de
`storage/` » n'est pas tenue par des lots antérieurs :

```
$ grep -rnE "(SELECT|INSERT[ ]INTO|UPDATE[ ]|DELETE[ ]FROM)" src/app --include=*.py | grep -v src/app/storage/
src/app/services/checklist.py:151, 166, 177, 199, 220, 235, 251, 496, 520, 556, 587
src/app/services/analyse_dce.py:115 … 498        (une vingtaine d'ordres)
src/app/services/authentification.py:70, 80, 92
```

C'est déjà le constat de L2 (§ 10 de `docs/RAPPORTS/L2-bibliotheque.md`) et il reste
ouvert. Les fichiers concernés appartiennent à d'autres lots ; je ne les ai pas touchés.

---

## 6. Ce qui n'a pas été fait, et limites assumées

1. **Aucune route de provisionnement de `client`** n'est exposée, et c'est **voulu**
   (annexe C § C2, volet 2) : un utilisateur = un client (annexe A § A5), donc aucune
   session ne peut exister avant le client. Une telle route serait un point d'entrée
   fabriquant des locataires. Un test vérifie qu'aucun chemin `/api/v1/clients` n'existe.
2. **Aucune nouvelle migration**, aucune contrainte croisée `(client_id, entreprise_id)`
   sur `fiche_version` : le chemin est fermé **applicativement** (contrôle d'appartenance
   avant écriture). Le correctif structurel (risque **R14**, migration `0005`) reste
   différé et n'appartient pas à ce lot.
3. **Aucun écran HTML.** Le lot expose l'API ; l'écran de première utilisation appartient
   à L5 (`t_2cfef350`), désormais débloqué : il a un chemin pour démarrer une bibliothèque
   de zéro.
4. **Aucun rôle d'administration, aucune inscription spontanée, aucune invitation par
   courriel, aucune réinitialisation de mot de passe par l'interface** : hors périmètre de
   la phase 3, conformément à « Ce que C2 ne décide pas ».
5. La vérification d'isolation a été faite **sur le seul chemin exposé** (les trois routes
   nouvelles). Les chemins internes des services (L2) conservent leur propre couverture de
   tests.
6. Le mot de passe n'est **pas** vérifié par l'interface avant hachage au-delà de la
   longueur minimale (12 caractères, `securite/mots_de_passe.py`) : la robustesse réelle
   n'est pas évaluée ici, et le lot n'invente aucun contrôle de conformité.

---

## 7. Décisions non couvertes par les annexes A, B et C

Ces points n'étaient tranchés ni par les annexes ni par le § C2 ; je les ai décidés et je
les signale ici plutôt que de les laisser implicites (un commentaire a été posé sur la
carte `t_8330811a`) :

1. **Forme de `GET /api/v1/entreprises`** : le § C2 fixe le chemin et le rôle, pas
   l'enveloppe. J'ai renvoyé un **objet** `{"entreprises": [...]}` (cohérent avec les
   autres routes de l'API, qui renvoient des objets) plutôt qu'un tableau nu. Chaque entrée
   porte `entreprise_id`, `libelle_court`, `statut` et `derniere_fiche` (objet ou `null`).
2. **`statut` renvoyé à la création** : c'est la valeur de la colonne
   `fiche_version.statut` (`vierge`), telle qu'écrite, et non l'état *calculé* de
   `ServiceVersionnement.statut_fiche`. Sur une fiche vide, les deux valent `vierge` ; le
   calcul ne diverge qu'après des écritures, qui n'ont pas lieu ici. Si un consommateur a
   besoin de l'état calculé, il l'obtient par `GET /api/v1/bibliotheque`.
3. **Confirmation du mot de passe en deux saisies** dans le script : le § C2 décrit « une
   saisie masquée ». J'ai ajouté une seconde saisie de confirmation : sans elle, une faute
   de frappe rend le compte d'accès inutilisable et le rattrapage n'est pas exposé. Une
   saisie divergente est refusée (code `2`) avant toute écriture.
4. **Noms des arguments du script** : `--libelle-client`, `--identifiant`,
   `--nom-affichage` (défaut = identifiant). Le § C2 ne les nomme pas.
5. **`400` vs `422`** : un `libelle_court` **absent** du corps donne `422` (validation
   Pydantic du contrat) ; un `libelle_court` **présent mais blanc** donne `400` (refus
   métier de `DepotEntreprise.creer`). Le § C2 prévoit `400` « libellé vide ou corps
   invalide » sans distinguer les deux cas.
6. **Champs inconnus du corps** : explicitement ignorés (`extra="ignore"`), pour que
   l'exigence « `client_id` du corps ignoré » soit une propriété déclarée du contrat et non
   un comportement implicite par défaut.

---

## 8. Reproduire la démonstration

```bash
# 1. base locale, hors dépôt d'exploitation
createdb -h 127.0.0.1 -p 5432 ia_consultations_l2bis
cd src && ../.venv/bin/python -m app.storage.migrations up

# 2. serveur local (jamais 0.0.0.0)
DATABASE_URL="postgresql://$USER@127.0.0.1:5432/ia_consultations_l2bis" \
CLE_CHIFFREMENT_MAITRESSE="<32 octets base64>" \
CLE_SESSION="<secret de session>" \
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8099

# 3. provisionnement de la racine, par l'exploitant (saisie masquée au clavier)
.venv/bin/python scripts/provisionnement.py \
    --libelle-client "Nom du client" \
    --identifiant "compte@exemple" \
    --nom-affichage "Nom Affiché"

# 4. première utilisation par l'utilisateur connecté
curl -c cookies.txt -X POST http://127.0.0.1:8099/api/v1/connexion \
     -H 'Content-Type: application/json' \
     --data '{"identifiant":"compte@exemple","mot_de_passe":"…"}'
curl -b cookies.txt http://127.0.0.1:8099/api/v1/bibliotheque     # 404 → attendu avant
curl -b cookies.txt -X POST http://127.0.0.1:8099/api/v1/entreprises \
     -H 'Content-Type: application/json' -d '{"libelle_court":"Mon entreprise"}'
curl -b cookies.txt http://127.0.0.1:8099/api/v1/bibliotheque     # 200

# 5. tests
cd src && ../.venv/bin/python -m pytest -q --no-header
```

La procédure destinée à l'exploitant sera reprise dans `docs/INSTALLATION.md` par le lot
L6, et l'exécution refaite indépendamment par le lot L8.
