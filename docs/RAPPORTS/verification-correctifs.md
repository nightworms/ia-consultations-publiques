# C4 — Vérification indépendante des trois correctifs

*Agent `qa`, tâche `t_3d6b189a`. 30 septembre 2026 (+04).*
*Projet : `/Users/pause/Projets/ia-consultations-publiques`. Board : `ia-consultations`.*

**Arbre vérifié** : `main` au commit `5737353` (C3 commité) **plus** les modifications
**non commitées** de C1 (`routes_analyse.py`, `analyse_dce.py`, `base.py`) et de C2
(`conftest.py`, `garde_isolation.py`, `test_isolation_fournisseur.py`),
et la modification commitée de C3 (`test_extraction_pdf_non_regression.py`).

**Méthode** : aucune conclusion n'est tirée d'une lecture. Chaque point a été **rejoué
par exécution**, et pour chacun j'ai aussi cherché à **le contredire** : reproduction du
défaut sur l'arbre d'avant correctif, mutations réelles du code pour vérifier que les
tests détectent une régression, canari réseau pour tenter de prendre la garde en défaut.

**Aucun appel réseau extérieur n'a été effectué pendant cette vérification, aucune clé
réelle n'a été utilisée vers un service distant, aucun document d'acheteur n'a été ouvert.**

---

## Verdict court

| Point | Verdict | Ce qui le prouve |
| --- | --- | --- |
| 1. Refus de modèle → 4xx au lieu de 500, transaction annulée, test auto | **Tient** | `422` sur un vrai serveur HTTP ; 0 ligne avant / 0 après ; l'arbre HEAD reproduit le `500` **et** 2 lignes orphelines + 1 fichier chiffré résiduel ; 3 mutations du correctif toutes détectées par les tests |
| 2. Suite indépendante du fournisseur configuré, réseau interdit, verrouillé | **Tient, avec une réserve nommée** | 185 verts dans **trois** configurations ; canari : **0** connexion après correctif contre **10** avant ; le verrou arrête réellement la suite (code 4). Réserve : la garde réseau ne couvre pas `socket.sendmsg` (trou réel, sans conséquence aujourd'hui) |
| 3. Test de non-régression `-layout` | **Tient** | `-layout` réintroduit par moi → `2 failed` (code 1) ; retiré → `2 passed` ; fichier restauré à l'empreinte près |

Détail, commandes et sorties réelles ci-dessous.

---

## 1. Le refus de modèle ne produit plus de 500

### 1.1 Reproduction par un vrai serveur HTTP (arbre corrigé)

Un faux fournisseur local (compatible OpenAI) répond **toujours** par une proposition dont
l'extrait de source est inventé (`EXTRAIT INVENTE PAR LA SONDE C4 — …`). Le produit est
lancé en vrai (`uvicorn`, vrai socket TCP), avec **le fournisseur `ue` réel** pointé sur ce
faux serveur — donc par le vrai chemin HTTP de `FournisseurUe`, sans
`dependency_overrides` :

```
$ cd src && env DATABASE_URL=… ia_consultations_c4_apres \
    MODELE_FOURNISSEUR=ue MODELE_FOURNISSEUR_URL=http://127.0.0.1:8791/v1/chat/completions \
    .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8790
$ curl … -X POST http://127.0.0.1:8790/api/v1/connexion   # 200, cookie de session
$ curl … -b cookies.txt -X POST http://127.0.0.1:8790/api/v1/consultations \
    -F "libelle=Consultation fictive C4 — DÉMONSTRATION" -F "entreprise_id=…" \
    -F "fichier=@src/tests/fixtures/dce_fictif.pdf;type=application/pdf"
```

Sortie réelle :

```
HTTP depot = 422
HTTP/1.1 422 Unprocessable Entity
{"detail":"Le document a bien été reçu, mais l'analyse n'a pas pu être validée. Proposition
non adossée au document : l'extrait invoqué est introuvable dans le texte extrait (catégorie
'piece_exigee'). Une valeur sans source n'est jamais acceptée. Catégorie mise en cause :
piece_exigee. Extrait invoqué, introuvable dans le document : « EXTRAIT INVENTE PAR LA SONDE
C4 — PHRASE QUI N EXISTE DANS AUCUN DOCUMENT ». Aucun élément n'a été enregistré : le dépôt
a été annulé."}
```

Lignes en base, lues par une **connexion séparée** (`ConnexionAdministration`, donc seules
les lignes réellement validées sont vues) :

```
avant :  consultation=0  document=0  extraction_element=0  utilisateur=1  entreprise=1
après :  consultation=0  document=0  extraction_element=0  utilisateur=1  entreprise=1
fichiers chiffrés laissés pour ce client : répertoire clients/<client_id> VIDE (aucun .bin)
```

Le journal du faux fournisseur confirme que le chemin HTTP du fournisseur a bien été
exercé (`POST /v1/chat/completions traite`), donc il ne s'agit pas d'un court-circuit.

### 1.2 Contre-épreuve : l'arbre d'avant correctif

Le correctif C1 n'étant pas commité, l'état d'avant est obtenu par un worktree en lecture
seule sur `HEAD` (aucune modification de l'arbre de travail) :

```
$ git worktree add --detach <scratch>/c4/head HEAD
```
Vérification préalable : `grep -c AnalyseNonValidable head/src/app/api/routes_analyse.py` → `0`.

Même sonde, même faux fournisseur, autre base :

```
HTTP depot = 500
corps : Internal Server Error
avant :  consultation=0  document=0  extraction_element=0
après :  consultation=1  document=1  extraction_element=0
fichiers chiffrés laissés : 1 fichier de 7519 octets (…fef2b881….bin)
journal uvicorn : ERROR: Exception in ASGI application  (traceback complet)
```

C'est exactement le double défaut décrit par C1 : **500 opaque + consultation et document
validés en base malgré l'échec + fichier chiffré orphelin sur disque**. Le diagnostic de C1
est donc confirmé, et sa correction change bien le comportement observable.

### 1.3 Les tests détectent-ils une régression ? (mutations réelles)

Trois mutations ont été appliquées **pour de vrai** au code, puis annulées. Empreintes
SHA-256 relevées avant et après : restauration identique dans les trois cas.

| Mutation | Ce qui a été retiré | Résultat de `pytest src/tests/test_refus_modele.py -q` |
| --- | --- | --- |
| M1 | le bloc `except AnalyseNonValidable` de la route | `1 failed, 3 passed` — `test_la_route_repond_422_et_non_500` (reçu 400 au lieu de 422) |
| M2 | les deux `valider=False` du dépôt (retour à une validation précoce) | `3 failed, 1 passed` — dont `test_un_extrait_invente_est_refuse_sans_laisser_de_ligne` (lignes orphelines de retour) |
| M3 | la traduction `_refus_modele(exc)` (le refus remonte brut) | `3 failed, 1 passed` — dont le test de route (500 de retour) |

Après restauration : empreintes identiques, `git diff` inchangé (celui de C1), et
`4 passed` sur l'arbre restauré. Les tests de C1 ne sont donc pas décoratifs : chacun des
trois maillons du correctif est verrouillé par au moins un test rouge quand on le casse.

### 1.4 Le garde-fou anti-invention a-t-il été affaibli ?

`git diff` sur `fournisseur_modele/base.py` : les **quatre branches de refus** de
`verifier_propositions` (catégorie hors contrat, libellé vide, emplacement vide, extrait non
adossé) sont **inchangées**, messages compris ; seuls des attributs `categorie`/`extrait`
sont ajoutés à `ReponseModeleInvalide` et passés en arguments. Aucune condition n'a été
supprimée ni assouplie. Point négatif écarté.

---

## 2. La suite ne dépend plus du fournisseur configuré

### 2.1 Les deux configurations demandées, par exécution

Depuis `src/` :

```
$ MODELE_FOURNISSEUR=factice ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 14.25s        (code de sortie 0)

$ set -a && . ../.env && set +a       # → MODELE_FOURNISSEUR=ue + URL OpenRouter + clé réelle
$ ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 12.25s        (code de sortie 0)
```

Troisième configuration, pour mémoire (aucune variable de fournisseur dans le shell) :
`185 passed in 11.97s`. `pytest --collect-only -q` → `185 tests collected`, aucun test ignoré.

**Précaution de méthode, à dire telle quelle** : la deuxième commande exporte la **clé
réelle** du `.env`. Je ne l'ai lancée **qu'après** avoir prouvé par exécution que la garde
réseau bloque (`pytest tests/test_isolation_fournisseur.py -q` → `12 passed`, dont les tests
qui exigent `ReseauInterdit` sur `httpx.post`, `socket.connect`, `sendto`, `getaddrinfo`).
Si la garde avait été inopérante, cette étape aurait été refusée et non lancée. La clé n'a
été ni affichée, ni recopiée, ni envoyée nulle part.

### 2.2 Canari : la suite appelle-t-elle le fournisseur configuré ?

Un écouteur TCP placé **exactement à l'adresse du fournisseur configuré**
(`MODELE_FOURNISSEUR=ue`, URL en bouclage — donc autorisée par la garde : si un appel
partait, il **aboutirait** et serait journalisé) :

```
$ python canari.py 8792 canari.log 30 &
$ MODELE_FOURNISSEUR=ue MODELE_FOURNISSEUR_URL=http://127.0.0.1:8792/v1/chat/completions \
  MODELE_FOURNISSEUR_CLE=cle-fictive-canari MODELE_FOURNISSEUR_NOM=modele-fictif-canari \
  ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 12.54s
$ cat canari.log
canari en ecoute sur 127.0.0.1:8792
canari arrete apres 30 s — connexions recues = 0
```

**Contrôle de sensibilité du canari** (sinon « 0 connexion » ne prouve rien) : en se
connectant volontairement à un canari identique, celui-ci journalise bien la connexion :

```
canari en ecoute sur 127.0.0.1:8793
CONNEXION RECUE depuis ('127.0.0.1', 52478) (total=1)
canari arrete apres 6 s — connexions recues = 1
```

### 2.3 Contre-épreuve : la suite d'avant correctif appelait bien le fournisseur

Même canari, mais la suite lancée depuis l'arbre `HEAD` (pré-C2, sans garde) :

```
$ cd <scratch>/c4/head/src
$ MODELE_FOURNISSEUR=ue MODELE_FOURNISSEUR_URL=http://127.0.0.1:8794/v1/chat/completions … \
  ../.venv/bin/python -m pytest tests/test_analyse_dce.py -q
10 failed, 7 passed in 6.55s            (code 1)

journal du canari :
CONNEXION RECUE depuis ('127.0.0.1', 53032) (total=1)
… (10 lignes)
canari arrete apres 25 s — connexions recues = 10
```

Dix connexions sortantes vers le fournisseur configuré pour un seul fichier de tests, zéro
après correctif : le défaut décrit par C2 est réel et sa correction est mesurable.

### 2.4 Le verrou arrête-t-il vraiment la suite ?

Mutation réelle de `conftest.py` : retrait de l'appel `garde_isolation.installer_garde_reseau()`
puis lancement de la suite :

```
ERROR: ISOLATION DES TESTS NON APPLIQUÉE — la suite refuse de démarrer.
  - la garde réseau n'est pas posée (src/tests/conftest.py n'a pas appelé installer_garde_reseau()).
…
code pytest = 4        (aucun test exécuté)
```

`conftest.py` restauré à l'empreinte près (`cc742c24…`), `git diff` toujours à +23 lignes.
Le verrou n'est pas un commentaire : il empêche la suite de tourner.

### 2.5 Ce que la garde réseau ne couvre pas (trouvé en essayant de la contredire)

`src/tests/garde_isolation.py` annonce couvrir `connect`, `connect_ex`, `sendto`,
`create_connection`, `getaddrinfo`. J'ai essayé les autres chemins :

```
[PASSE] socket.socket.sendmsg UDP (méthode NON surveillée) — NON bloqué par la garde ; résultat=16
[BLOQUE] socket.socket.connect UDP puis send — ReseauInterdit
[BLOQUE] socket.socket.sendto UDP (data, flags, adresse) — ReseauInterdit
[BLOQUE] getaddrinfo(exemple-fictif.invalid) — ReseauInterdit
[BLOQUE] httpx.post HTTPS vers un nom externe — ReseauInterdit
```

`socket.sendmsg` vers `192.0.2.1:80` **n'est pas intercepté** : le noyau a accepté l'envoi de
16 octets vers une adresse hors bouclage. **Portée réelle aujourd'hui : nulle** — aucun
module de `src/app/` n'utilise le module `socket` (`grep -rn "sendmsg\|sendto\|import socket" src/app/`
→ aucune correspondance) ; le produit sort uniquement par `httpx` (surveillé) et par `libpq`
(non Python, déjà documenté par C2). C'est une **imprécision de la garde, pas une fuite
actuelle** : à corriger le jour où un client bas niveau entre dans le produit. Conséquence
rédactionnelle : la phrase « aucun appel réseau sortant n'est possible » du rapport C2 est
plus large que ce que le code garantit ; le docstring de `garde_isolation.py`, lui, est exact.

### 2.6 Limite structurelle confirmée

L'isolation est portée par `src/tests/conftest.py`. Chargement du conftest désactivé :

```
$ ../.venv/bin/python -m pytest --noconftest tests/test_isolation_fournisseur.py -q
7 failed, 5 passed in 2.19s
```

Sans conftest, ni fournisseur imposé ni garde réseau : les tests qui exigent
`ReseauInterdit` échouent. C'est la contrepartie assumée du dispositif (le contourner
demande une option explicite ou un autre lanceur que pytest) ; à garder en tête, ce n'est
pas une protection au niveau du système.

---

## 3. Le test de non-régression d'extraction PDF

### 3.1 État de départ vérifié

```
$ shasum -a 256 src/app/services/extraction_pdf.py
5b18a2c87ba9f2d7acd6f67ae1e1464f5abfa05c6fe794960e60e8e23e5be367
$ git diff --stat -- src/app/services/extraction_pdf.py     → (aucune sortie)
```

### 3.2 Je réintroduis moi-même `-layout`

Substitution exacte dans `_texte_page` (ajout de `"-layout",` avant `"-f"`), contrôlée :

```
192:    pdftotext = _exiger_outil("pdftotext")
193-    resultat = _executer(
194-        [
195-            pdftotext,
196-            "-layout",
```

### 3.3 Le test échoue (ce qu'on veut)

```
$ .venv/bin/python -m pytest src/tests/test_extraction_pdf_non_regression.py -q
FAILED src/tests/test_extraction_pdf_non_regression.py::test_la_phrase_du_corps_reste_contigue
FAILED src/tests/test_extraction_pdf_non_regression.py::test_aucune_ligne_ne_melange_les_deux_colonnes
2 failed in 0.15s
code de sortie pytest = 1

E  AssertionError: des lignes lues portent à la fois le corps de texte et la colonne latérale
   — `-layout` a probablement été réintroduit : ["Le candidat doit justifier de l'importance du
   Effectifs moyens et importance"]
```

La panne **reproduit littéralement** le défaut de production (« …l'importance du *Effectifs
moyens et importance* personnel d'encadrement… »). Le test ne se contente pas de chercher la
chaîne `-layout` : il détecte la **corruption** produite, ce qui le rend robuste à une
réintroduction écrite autrement.

### 3.4 Retour à l'état correct, vérifié

```
$ cp <sauvegarde> src/app/services/extraction_pdf.py
$ shasum -a 256 src/app/services/extraction_pdf.py
5b18a2c87ba9f2d7acd6f67ae1e1464f5abfa05c6fe794960e60e8e23e5be367     (identique)
$ git diff --stat -- src/app/services/extraction_pdf.py      → (aucune sortie)
$ git status --porcelain -- src/app/services/extraction_pdf.py  → (aucune sortie)

$ .venv/bin/python -m pytest src/tests/test_extraction_pdf_non_regression.py -q
2 passed in 0.14s
code de sortie pytest = 0
```

Fichier remis **à l'identique** (empreinte SHA-256), arbre propre. Le correctif 3 est bon :
il détecte la réintroduction et passe sans elle.

---

## Constats classés par gravité

| # | Gravité | Constat | Preuve |
| --- | --- | --- | --- |
| 1 | **Mineur** | La garde réseau ne couvre pas `socket.sendmsg` : un envoi UDP hors bouclage passe (16 octets acceptés vers `192.0.2.1:80`). Aucun code de `src/app/` n'utilise `socket` aujourd'hui → pas de fuite actuelle, mais la garantie annoncée est plus large que le code | § 2.5 |
| 2 | **Mineur** | Un fournisseur **injoignable** produit toujours un `500` opaque (inchangé par C1, documenté comme hors périmètre) : `httpx.ConnectError` → `ErreurFournisseurModele` non rattrapée. L'utilisateur reçoit « Internal Server Error » alors que le refus de modèle, lui, est expliqué en 422 | § 4.1 |
| 3 | **Mineur** | L'isolation des tests tient au seul `conftest.py` : `pytest --noconftest` la désarme (7 échecs de la garde). Contournement explicite, pas une faille, mais à documenter | § 2.6 |
| 4 | **Cosmétique** | `docs/RAPPORTS/C2-isolation-tests.md` ligne 20 montre un fragment de clé (`MODELE_FOURNISSEUR_CLE=sk-or-...test`) : valeur tronquée, ce n'est **pas** un secret, mais c'est une trace du préfixe du fournisseur — une redaction complète suffirait | `grep -n "sk-" docs/RAPPORTS/C2-isolation-tests.md` |
| 5 | **Cosmétique** | L'écran web (L5) retombe sur le `400` générique de `ErreurAnalyseDce` pour un refus anti-invention : message complet, mais code sémantique identique à « format refusé » (déjà signalé par C1 comme reste à faire) | lecture `routes_web.py:771` + `consultations.html` ; `autoescape("erreur.html") = True` (donc pas d'injection HTML par le texte du modèle, mais cas non joué en bout en bout) |

**Aucun constat bloquant ni majeur.** Les trois correctifs tiennent, et les tests qui les
verrouillent échouent tous quand on casse le code qu'ils protègent.

---

## 4. Ce que je n'ai PAS vérifié, et ce qui me laisse un doute

1. **Le cas réel d'origine (Claude via OpenRouter)** n'a pas été rejoué : cela exigerait de
   sortir sur Internet et de consommer la clé du `.env`. Je l'ai remplacé par un faux
   fournisseur local, exercé par le **vrai chemin HTTP de `FournisseurUe`**, et par une
   contre-épreuve sur l'arbre `HEAD` : le `500` et les lignes orphelines sont reproduits,
   mais la réponse **exacte** du modèle réel (forme du JSON, extrait invoqué) n'est pas
   garantie identique.
2. **Reste un 500 possible** que j'ai vérifié par exécution (§ 4.1 ci-dessous) : fournisseur
   injoignable, mal configuré, ou clé refusée. Le périmètre de C1 le laisse de côté —
   je le signale parce qu'un utilisateur ne peut pas distinguer ce 500 d'une panne serveur.
3. **La transaction « à moitié écrite »** est vérifiée pour le chemin du refus de modèle
   (0 ligne) et pour le chemin « fournisseur injoignable » (0 ligne aussi). Je **n'ai pas**
   testé le cas où l'échec survient *pendant* l'`INSERT` d'un élément ou l'`UPDATE` de
   statut (échec SQL en cours d'analyse) — C1 le signale lui-même comme cas marginal non
   vérifié, je confirme ne pas l'avoir couvert.
4. **La concurrence** n'a pas été testée : C1, C2 et C3 signalent tous des échecs en base de
   test partagée (migrations `down/up` simultanées). Toutes mes mesures ont été prises en
   **seul** sur l'arbre, sur des bases dédiées ; je n'ai donc pas reproduit ce défaut, mais
   je ne l'ai pas non plus infirmé. Il reste un vrai risque d'atelier.
5. **Une seule machine, un seul système** : macOS 27, Python 3.12.14, pytest 9.1.1,
   PostgreSQL local. La propriété « même verdict sur toute machine » n'est démontrée que
   pour trois configurations d'environnement sur **cette** machine.
6. **L5 (écran web) en bout en bout** : je n'ai pas déroulé le formulaire web pour voir le
   refus s'afficher ; j'ai vérifié par lecture la branche d'erreur et que l'auto-échappement
   des gabarits est actif (`autoescape("erreur.html") = True`), donc pas d'injection HTML par
   le texte renvoyé par un modèle. Cas non joué.
7. **La limite connue de C3** (l'ordre de lecture sans `-layout` sur une page réellement
   tabulaire) reste non levée : aucun DCE réel n'est dans le dépôt, je n'ai rien pu ajouter
   sur ce point — c'est un compromis à réévaluer, comme l'écrit C3 lui-même.
8. **Couverture par le test et non par le code** pour C3 : le test empêche la corruption,
   mais rien n'empêche quelqu'un d'écrire un jour `-raw` ou `-layout` dans une autre fonction
   d'extraction sans que ce test le voie. Le verrou porte sur `_texte_page` de fait, pas par
   construction.

### 4.1 Détail du 500 « fournisseur injoignable » (vérifié, hors périmètre C1)

Même sonde HTTP, fournisseur `ue` pointé sur un port fermé (`http://127.0.0.1:8799/…`) :

```
HTTP depot = 500
corps : Internal Server Error
journal uvicorn :
  httpx.ConnectError: [Errno 61] Connection refused
  → app.services.fournisseur_modele.base.ErreurFournisseurModele (non rattrapée) → ASGI 500
base après : consultation=0  document=0  extraction_element=0   (aucune ligne orpheline : le rollback tient)
```

La transaction est propre ; seul le code HTTP ne dit rien d'exploitable au client.

---

## 5. État du dépôt après mon passage

Toutes mes manipulations destructrices ont été faites sur des **copies** et annulées ;
empreintes vérifiées :

```
f6ee1529ddce8a3004af94e04521a69884c2545b1ff5635fdad7315941a761fe  src/app/api/routes_analyse.py      (C1, inchangé par moi)
7f507b051a21af6915c119b118aca4110dc894cc7ac7b1b9435afbaf4c4ed7e0  src/app/services/analyse_dce.py    (C1, inchangé par moi)
9518eb3ab9de47cbaf0f96f53f91c36e4c912bc3b2bf47d71af5a1907ecf4543  src/app/services/fournisseur_modele/base.py (C1)
cc742c24988ebe4b33e5230915f36889b34d587f8bf9812c2cff97ee520a70df  src/tests/conftest.py              (C2, +23 lignes)
5b18a2c87ba9f2d7acd6f67ae1e1464f5abfa05c6fe794960e60e8e23e5be367  src/app/services/extraction_pdf.py (C3, restauré à l'identique)
```

`git status --porcelain` est **exactement** celui d'avant mon passage : 4 fichiers modifiés
(C1 ×3, C2 ×1) et 11 fichiers non suivis appartenant à C1/C2, plus ce rapport. Aucun
worktree résiduel (`git worktree list` → une seule entrée). `.env` non modifié. Aucune
donnée d'acheteur, aucun secret ajouté au dépôt (`grep` sur les motifs `sk-…` : seule
occurrence, la trace tronquée déjà présente dans le rapport C2).

Bases dédiées créées pour ne pas perturber le travail des autres lots :
`ia_consultations_c4_apres`, `ia_consultations_c4_avant`, `ia_consultations_c4_indispo`
(reproductibles via `<scratch>/c4/recreer_base.py <nom>`).
