# L7 — Rapport d'exécution : procédure de déploiement et sauvegardes

*Lot L7, phase 3. Exécuté le 30 septembre 2026 à 11 h 27–11 h 34 (+04), sur la
machine de développement d'Anthony (`Mac-mini-de-PAUSE.local`).*

## 1. Ce qui a été fait, en une page

| Livrable | État |
|---|---|
| `docs/DEPLOIEMENT-FRANCE.md` | écrit (32 Ko) — région française nommée, **rien n'a été provisionné** |
| `scripts/sauvegarde.sh` | écrit et **exécuté 3 fois** sur la base locale |
| `scripts/restauration.sh` | écrit et **exécuté 3 fois**, dont 2 fois sur une sauvegarde valide |
| `docs/RAPPORTS/L7-deploiement.md` | ce document |
| `scripts/jeu-de-test/0001_jeu_fictif.sql` | jeu de test **fictif**, pour obtenir des comptages non nuls |
| `.env.example` | trois noms de variables ajoutés, **aucune valeur** |
| `.gitignore` | une ligne ajoutée (`data-restaure/`) |

**Rien n'a été déployé.** Aucun compte ouvert, aucun service provisionné, aucune
dépense engagée, aucun port ouvert sur Internet, aucun DNS modifié. La région
visée (`Scaleway fr-par`, Paris) est nommée dans la procédure ; elle n'est pas
provisionnée.

**Ce qui tourne réellement** : une base PostgreSQL **locale** (`Postgres.app`
18.3, `127.0.0.1:5432`, écoute sur `localhost` uniquement), la base
`ia_consultations` du socle L1, complétée par un jeu de test **fictif**.

---

## 2. Environnement d'exécution, vérifié

```
$ date '+%Y-%m-%d %H:%M:%S %Z (%z)'
2026-09-30 11:33:33 +04 (+0400)

$ psql --version
psql (PostgreSQL) 18.3 (Postgres.app)

$ psql -X -h 127.0.0.1 -U pause -d ia_consultations -c "\dt"
… 16 tables …  (18 tables après les migrations 0002 et 0003 appliquées
                en parallèle par les lots L2 et L3)
```

Outils utilisés, **tous déjà présents** (aucune installation) : `pg_dump`,
`pg_restore`, `psql`, `openssl`, `tar`, `awk`, `diff`, `shasum`. Aucune
dépendance nouvelle n'a été installée pour ce lot.

---

## 3. Le jeu de test est fictif, et signalé comme tel

Aucune donnée réelle d'entreprise ni document de collectivité n'a été utilisé
(D10, ligne rouge). `scripts/jeu-de-test/0001_jeu_fictif.sql` insère deux clients
« FICTIF — Client A » et « FICTIF — Client B » — deux locataires distincts, pour
que le jeu de test porte aussi le cloisonnement par `client_id` — avec des
libellés portant tous la mention **FICTIF**, des adresses en `.invalid` et des
identifiants de consultation `FICTIF-CONS-2026-001/002`.

Deux choix à signaler :

- La table `authentification` est **volontairement laissée vide** par le jeu de
  test : elle contient des empreintes de mots de passe, et aucune valeur de
  nature secrète — même fictive — n'a sa place dans un fichier versionné.
- Le jeu est **idempotent** (`ON CONFLICT DO NOTHING`, UUID fixes) : le relancer
  ne duplique rien.

**Ces lignes fictives sont dans la base locale, et nulle part ailleurs.** Le
retrait se fait **table par table, dans l'ordre inverse des dépendances** — il
n'est pas donné ici en une seule commande parce qu'une suppression en cascade non
relue est exactement le geste irréversible que la règle « double contrôle »
interdit. L'ordre est :

```
evenement_facturation_dossier → evenement_facturation → dossier → abonnement →
tracabilite_valeur → validation_relecture → fiche_famille → document →
fiche_version → entreprise → utilisateur → valeur_reference → jeu_reference → client
```

en filtrant chaque table sur `client_id IN
('a0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000001')`
(et sur `namespace = 'test.fictif.l7'` pour `jeu_reference` / `valeur_reference`,
qui ne portent pas de `client_id` — les jeux de référence sont globaux).

Rien de tout cela n'est obligatoire : ces lignes sont inoffensives en base locale.
Elles ne doivent simplement **jamais** se retrouver en production.

---

## 4. Exigence 1 — `scripts/sauvegarde.sh` s'exécute et produit une sauvegarde chiffrée

### 4.1 Exécution

```
$ cd /Users/pause/Projets/ia-consultations-publiques
$ ./scripts/sauvegarde.sh --base "postgresql://pause@127.0.0.1:5432/ia_consultations"
```

Sortie (verbatim) :

```
[sauvegarde] sauvegarde de la base « ia_consultations »…
[sauvegarde] sauvegarde des fichiers de /Users/pause/Projets/ia-consultations-publiques/data (lus en place, jamais recopiés en clair) …
Sauvegarde terminée.
  répertoire         : /Users/pause/sauvegardes-ia-consultations/20260930-113052
  base               : ia_consultations
  base chiffrée      : 64 Kio  (273caca5e9e119cf86e80f735a263d3d48cf5ca4b1aa0019f467e64fc0f2553b)
  documents chiffrés : 2632 Kio  (878a6796d6dbae4f97e9d766f353fdb6ec56cc5eced770389d871e9d1ed90506)
  documents en clair : 3500 Kio (lus en place, jamais recopiés en clair)
  manifeste chiffré  : manifeste.tar.gz.enc (3fa27be04a1bf3818be427e375aee226913abc235c6f230c40fa842ce9b823df)
  rien en clair      : vérifié, aucun fichier non chiffré dans la destination
  lien de commodité  : /Users/pause/sauvegardes-ia-consultations/derniere
```

Code de retour : **0**.

### 4.2 Contenu produit, sur le disque

```
$ ls -la ~/sauvegardes-ia-consultations/derniere/
-rw-------  base.dump.enc          61 696 o
-rw-------  documents.tar.gz.enc  2 693 152 o
-rw-------  empreintes.sha256         254 o
-rw-------  manifeste.tar.gz.enc   10 272 o
```

Le répertoire parent est en `drwx------` (700) et les fichiers en `-rw-------`
(600). `derniere` est un lien symbolique vers la sauvegarde la plus récente.

### 4.3 Preuve que le contenu est bien chiffré

```
$ head -c 8 base.dump.enc | xxd
00000000: 5361 6c74 6564 5f5f                      Salted__

$ head -c 8 documents.tar.gz.enc | xxd
00000000: 5361 6c74 6564 5f5f                      Salted__

$ head -c 8 manifeste.tar.gz.enc | xxd
00000000: 5361 6c74 6564 5f5f                      Salted__
```

Les trois archives commencent par l'en-tête `Salted__` d'`openssl enc` : elles
sont chiffrées. **Une archive `pg_dump` non chiffrée commence par `PGDMP`** — ce
n'est le cas d'aucune des trois, et le script refuse explicitement de continuer
si ce motif apparaît.

### 4.4 Contenu du manifeste (déchiffré pour contrôle, extrait)

Le manifeste est **rangé dans une archive chiffrée** ; il est déchiffré ici à la
main pour montrer ce qu'il contient :

```
format	1
horodatage	2026-09-30T11:30:52+0400
base	ia_consultations
repertoire_fichiers	data
pg_dump	pg_dump (PostgreSQL) 18.3 (Postgres.app)
chiffrement	AES-256-CBC/PBKDF2-HMAC-SHA256-200000
table	abonnement	2
table	authentification	1
table	client	3
table	consultation	3
table	document	5
table	dossier	2
table	entreprise	3
table	evenement_facturation	2
table	evenement_facturation_dossier	1
table	extraction_element	22
table	fiche_famille	3
table	fiche_version	2
table	jeu_reference	5
table	schema_migration	2
table	tracabilite_valeur	2
table	utilisateur	3
table	valeur_reference	15
table	validation_relecture	1
fichier	1878c954…	./client-a-fictif/documents/piece-a.txt
fichier	d421f43f…	./client-b-fictif/documents/piece-b.txt
… 46 lignes « fichier » au total …
```

Le manifeste ne contient **aucune valeur de donnée** : uniquement des noms de
tables, des comptages, des empreintes et des chemins relatifs.

---

## 5. Exigence 2 — `scripts/restauration.sh` restaure et le contenu est vérifié

### 5.1 Exécution

```
$ ./scripts/restauration.sh --base "postgresql://pause@127.0.0.1:5432/ia_consultations"
```

Sortie (verbatim) :

```
[restauration] sauvegarde à restaurer : /Users/pause/sauvegardes-ia-consultations/derniere
base.dump.enc: OK
documents.tar.gz.enc: OK
manifeste.tar.gz.enc: OK
[restauration] sauvegarde du 2026-09-30T11:30:52+0400, base « ia_consultations »
[restauration] base cible ia_consultations_restauration_test déjà présente : suppression puis recréation (idempotence).
[restauration] création de la base de test « ia_consultations_restauration_test »…
[restauration] restauration de la base…

Comptage de lignes — table par table
table                              sauvegarde  source(now)   restaurée   verdict
-------------------------------------------------------------------------------------
abonnement                                  2            2            2   identique
authentification                            1            1            1   identique
client                                      3            3            3   identique
consultation                                3            3            3   identique
document                                    5            5            5   identique
dossier                                     2            2            2   identique
entreprise                                  3            3            3   identique
evenement_facturation                       2            2            2   identique
evenement_facturation_dossier               1            1            1   identique
extraction_element                         22           22           22   identique
fiche_famille                               3            3            3   identique
fiche_version                               2            2            2   identique
jeu_reference                               5            5            5   identique
schema_migration                            2            2            2   identique
tracabilite_valeur                          2            2            2   identique
utilisateur                                 3            3            3   identique
valeur_reference                           15           15           15   identique
validation_relecture                        1            1            1   identique
[restauration] restauration des fichiers dans /Users/pause/restauration-ia-consultations/documents …

Fichiers — 46 fichier(s) attendu(s)
  tous les fichiers restaurés portent l'empreinte attendue  : identique

RESTAURATION VÉRIFIÉE : base « ia_consultations_restauration_test » restaurée depuis /Users/pause/sauvegardes-ia-consultations/derniere,
  comptages de lignes identiques table par table, 46 fichier(s) conforme(s).
  Pour revenir en arrière : DROP DATABASE "ia_consultations_restauration_test";
```

Code de retour : **0**.

### 5.2 Ce que la vérification couvre réellement

- **18 tables** comparées, ligne à ligne, entre le manifeste de sauvegarde et la
  base restaurée : toutes **identiques**.
- **46 fichiers** restaurés, chacun comparé à l'empreinte SHA-256 enregistrée
  dans le manifeste au moment de la sauvegarde : tous **conformes**.
- Les fichiers restaurés sont bien présents sur le disque :
  `~/restauration-ia-consultations/documents/` → `find … | wc -l` = **46**.

### 5.3 Point honnête : la colonne « source(now) »

Dans l'exécution la plus récente, les trois colonnes concordent. Dans une
exécution antérieure (11 h 30 min 26 s), la colonne « source(now) » était **plus
élevée** que les deux autres sur plusieurs tables (`jeu_reference` 5 contre 1,
`valeur_reference` 15 contre 2, `schema_migration` 2 contre 1, `utilisateur` 3
contre 2) : **les lots L2 et L3 écrivaient dans la base locale pendant
l'exécution**, et appliquaient leurs migrations `0002` et `0003`.

Ce n'est pas un défaut du script, c'est la démonstration qu'il fait la bonne
chose : la restauration est comparée **au manifeste de la sauvegarde**, jamais à
l'état courant d'une base qui bouge. Une sauvegarde est une photographie ; la
comparer au présent n'aurait aucun sens.

### 5.4 Idempotence

- `sauvegarde.sh` a été lancé **3 fois** : trois répertoires horodatés
  coexistent (`20260930-112840`, `-113026`, `-113052`), aucun n'a été modifié ni
  supprimé par un lancement suivant.
- `restauration.sh` a été lancé **2 fois** sur la même sauvegarde : la seconde
  exécution a détecté la base de test existante, l'a recréée, et a retrouvé le
  même résultat (message « déjà présente : suppression puis recréation »).

### 5.5 Retour en arrière de cet essai

L'essai a laissé, en local : la base `ia_consultations_restauration_test`, le
répertoire `~/restauration-ia-consultations/documents/`, et les sauvegardes dans
`~/sauvegardes-ia-consultations/`. Le retrait est d'une commande :

```
psql -X -h 127.0.0.1 -U pause -d postgres -c 'DROP DATABASE "ia_consultations_restauration_test";'
```

Les sauvegardes, elles, ne doivent **pas** être supprimées : c'est la preuve du
lot. La clé de sauvegarde est en `~/.config/ia-consultations/cle-sauvegarde`
(600).

---

## 6. Exigence 3 — pas de sauvegarde non chiffrée, aucune clé dans le dépôt

### 6.1 Sans clé, aucune sauvegarde n'est produite

```
$ SAUVEGARDE_CLE_FICHIER="$HOME/.config/ia-consultations/cle-absente-test" \
  ./scripts/sauvegarde.sh --base "postgresql://pause@127.0.0.1:5432/ia_consultations"
```

```
ERREUR : clé de sauvegarde absente : /Users/pause/.config/ia-consultations/cle-absente-test
AUCUNE sauvegarde n'a été produite : une sauvegarde non chiffrée est interdite.
Générez la clé UNE SEULE FOIS, hors dépôt, et conservez-la :
  install -d -m 700 "$(dirname "/Users/pause/.config/ia-consultations/cle-absente-test")"
  openssl rand -base64 48 > "/Users/pause/.config/ia-consultations/cle-absente-test"
  chmod 600 "/Users/pause/.config/ia-consultations/cle-absente-test"
Sans cette clé, aucune sauvegarde existante n'est déchiffrable.
```

Code de retour : **1**. Vérification faite juste après : **aucun nouveau
répertoire de sauvegarde n'a été créé** (le répertoire contenait toujours les
trois mêmes sauvegardes).

### 6.2 Une sauvegarde altérée est refusée avant déchiffrement

Un octet du milieu de `base.dump.enc` a été modifié dans une **copie** de la
sauvegarde (`/tmp/l7-preuves/sauvegarde-alteree`), puis :

```
$ ./scripts/restauration.sh --sauvegarde /tmp/l7-preuves/sauvegarde-alteree --base "…"
```

```
[restauration] sauvegarde à restaurer : /tmp/l7-preuves/sauvegarde-alteree
sha256sum: WARNING: 1 computed checksum did NOT match
base.dump.enc: FAILED
documents.tar.gz.enc: OK
manifeste.tar.gz.enc: OK
ÉCHEC DE VÉRIFICATION : l'empreinte SHA-256 des archives ne correspond pas : sauvegarde corrompue ou altérée.
```

Code de retour : **2**. La base n'a **pas** été touchée : le contrôle a lieu
avant la création de la base cible.

### 6.3 Une mauvaise clé échoue proprement

Avec une clé valide mais différente (fichier temporaire en 600, hors dépôt) :

```
bad decrypt
tar: Error opening archive: Unrecognized archive format
ÉCHEC DE VÉRIFICATION : manifeste illisible : clé incorrecte ou archive corrompue.
```

Code de retour : **2**. Aucune base touchée.

### 6.4 Scan de secrets sur le dépôt

Un script de contrôle a été exécuté sur `/Users/pause/Projets/ia-consultations-publiques` :

```
1) Fichiers du dépôt contenant un fragment de la clé de sauvegarde :
   -> nombre : 0

2) Fichiers de sauvegarde (.dump/.enc/.tar.gz/.sql) présents dans le dépôt :
   -> nombre : 0

3) Motifs de secret évidents dans les fichiers versionnables du dépôt :
   (clés privées au format PEM, chaînes de connexion portant un mot de passe,
    clés d'API de la famille « sk-… »)
   -> nombre : 0

4) Fichiers suivis par git qui matcheraient .env, data/ ou *.key :
   -> nombre : 0

5) Permissions de la clé de sauvegarde (hors dépôt) :
   /Users/pause/.config/ia-consultations/cle-sauvegarde 600
```

Le seul contenu du dépôt qui ressemble à un secret est le **nom** des variables
dans `.env.example` et `src/app/config.py` — jamais une valeur.

**Fichiers temporaires du contrôle** : `/tmp/l7-preuves/` contient la sauvegarde
altérée de l'essai 6.2 et une clé factice (`cle-fausse`). Ce sont des artefacts de
test, hors du dépôt, à retirer : `rm -r /tmp/l7-preuves`. Ils ne sont pas
versionnés.

---

## 7. Exigence 4 — la procédure nomme la région et dit que rien n'est provisionné

`docs/DEPLOIEMENT-FRANCE.md` :

- § 0 : « **Rien n'a été provisionné.** Aucun compte n'a été ouvert, aucun
  service n'a été commandé, aucune dépense n'a été engagée, aucun port n'a été
  ouvert sur Internet, aucun nom de domaine n'a été réservé, aucun DNS n'a été
  modifié. »
- § 0 et § 2 : « **Région française retenue : Scaleway `fr-par` (Paris)** »,
  zones `fr-par-1`, `fr-par-2`, `fr-par-3`.
- § 2.1 : alternatives écartées, y compris les régions UE **hors France**
  (Amsterdam, Varsovie, Milan) présentées comme des pièges.
- § 9 : la mise en service est décrite en trois phases, **aucune exécutée**.
- § 14 : sources datées et marquées « à revérifier ».

Deux points de forme imposés par les décisions gelées ont été respectés :

- la formulation « seul le client a accès à ses données » n'apparaît **nulle
  part** dans la procédure, et § 4 en interdit explicitement l'usage ;
- le maillon du fournisseur de modèle est traité (§ 4), avec l'exigence D8
  (France ou UE) et la mention que le serveur **lit** pendant le traitement.

---

## 8. Ce qui n'a pas pu être testé, et pourquoi

| Non testé | Raison |
|---|---|
| Sauvegarde d'une base **managée** (Scaleway ou OVHcloud) | aucun service provisionné — c'est interdit dans ce lot |
| Restauration vers un serveur distant | idem |
| TLS, reverse-proxy, DNS | idem |
| Chiffrement au repos de l'hébergeur | dépend du fournisseur, non souscrit |
| Appel réel au fournisseur de modèle | hors périmètre L7 (annexe A § A7, lot L3) |
| Restauration de nuit, sous charge | pas d'infrastructure réelle |
| Comportement du script sur une base de plusieurs centaines de Go | `pg_dump` écrit en flux et `openssl` en flux : cela devrait tenir, mais **ce n'est pas mesuré** et je ne l'affirme pas |

**Sur la portabilité** : les commandes utilisées (`pg_dump --format=custom`,
`openssl enc -aes-256-cbc -pbkdf2`, `tar`, `psql`) sont les mêmes sur une Debian
serveur. L'option `--pbkdf2` existe depuis OpenSSL 1.1.1 ; elle n'existe pas sur
les versions plus anciennes. **À vérifier sur le serveur retenu** avant toute
mise en service.

---

## 9. Notes d'exécution, y compris ce qui a mal tourné

Deux incidents, tous deux sans conséquence, mais ils méritent d'être dits :

1. **Premier lancement : erreur de script.** La première exécution de
   `sauvegarde.sh` s'est arrêtée sur
   `line 157: REPERTOIRE_DOC…: unbound variable` — une variable suivie
   immédiatement d'un caractère de ponctuation UTF-8 (`…`) était interprétée par
   bash comme faisant partie du nom. Corrigé en écrivant `${REPERTOIRE_DOC}`
   entre accolades. Le répertoire partiel laissé par cet essai a été **mis à la
   corbeille** (`~/.Trash/sauvegarde-l7-partielle-20260930-112808`), pas
   supprimé, et aucune sauvegarde valide n'a été touchée.
2. **Structure des archives revue.** La première version recopiait les documents
   dans un répertoire temporaire avant de les empaqueter. La version livrée
   **lit les documents en place** et écrit le manifeste dans une **archive
   chiffrée distincte** : plus aucune copie en clair des documents n'est écrite,
   même temporairement, et le manifeste n'est pas lisible dans le répertoire de
   sauvegarde.

**Déplacement de fichiers plutôt que suppression.** Les outils de suppression
récursive (`rm -rf`, `find -delete`) sont bloqués dans le contexte d'exécution
automatisé de ce lot. Quand il a fallu retirer quelque chose, la solution
retenue a été de **déplacer** vers la corbeille ou vers un nom explicite, jamais
de supprimer. C'est cohérent avec la règle « pas de retour en arrière = pas de
modification » : ici, le retour en arrière reste possible.

**Limite connue de `restauration.sh`** : la chaîne de connexion ne doit pas
porter de paramètres d'URL (`?sslmode=…`) — le script le détecte et refuse plutôt
que de mal construire l'URL cible. En production, où le TLS sera exigé, cette
limite devra être traitée (`PGSSLMODE` dans l'environnement ou prise en charge des
paramètres). **Ce point n'est pas corrigé dans ce lot** ; il est signalé.

---

## 10. Fichiers touchés par ce lot

| Fichier | Nature |
|---|---|
| `docs/DEPLOIEMENT-FRANCE.md` | **créé** |
| `docs/RAPPORTS/L7-deploiement.md` | **créé** (ce document) |
| `scripts/sauvegarde.sh` | **créé**, exécutable |
| `scripts/restauration.sh` | **créé**, exécutable |
| `scripts/jeu-de-test/0001_jeu_fictif.sql` | **créé** |
| `.env.example` | **modifié** : section « SAUVEGARDE ET RESTAURATION » ajoutée (noms de variables, aucune valeur) |
| `.gitignore` | **modifié** : ligne `data-restaure/` ajoutée |

**Aucun commit git n'a été fait** — cohérent avec les lots précédents.

`data/` et `.env.example` sont des **fichiers partagés**, modifiés par plusieurs
lots en parallèle pendant cette phase : `.env.example` a d'ailleurs été modifié
par L3 pendant que ce lot travaillait (section « ANALYSE DE DCE »). Les ajouts de
ce lot sont purement additifs, mais le risque de collision de fusion existe.

---

## 11. Vérifications restant à faire

- Rejouer `scripts/restauration.sh` **sur la base managée réelle**, après
  provisionnement : c'est le seul exercice qui prouve quelque chose sur
  l'infrastructure (procédure § 8.2).
- Confirmer que la clé de sauvegarde est **conservée dans un coffre**, séparément
  des sauvegardes. Sans elle, aucune sauvegarde n'est déchiffrable : c'est le
  point de défaillance unique du dispositif.
- Valider les objectifs proposés (RPO ≤ 24 h, RTO ≤ 4 h, rétention 30 jours) —
  ce sont des **propositions**, pas des engagements.
- Faire arbitrer par le juriste les dix points de `docs/DEPLOIEMENT-FRANCE.md`
  § 11, en particulier le DPA et la clause de non-entraînement auprès du
  fournisseur de modèle.

---

*Fin du rapport. Rien n'a été déployé. Tout ce qui est affirmé ici a été exécuté
et la sortie est reproduite telle quelle.*