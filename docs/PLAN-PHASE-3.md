# PLAN-PHASE-3 — implémentation du socle et des trois briques du MVP

*Tâche racine de la phase 3. Agent `plan`. Écrit le 30 septembre 2026 à 11h13 (+04).*
*Board : `default`, tâche `t_3c57fd67`. Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*
*Révision n° 1 — 30 septembre 2026 à 11h56 (+04) : annexe C complétée du § C2 (décision de
provisionnement, tâche `t_5b51c472`, demandée par le lot L2). Le lot **L2bis** est créé et les
dépendances de L5 et L8 sont ajustées en conséquence. Aucune route existante n'est renommée.*

Ce document est le **plan de la phase 3**. Il contient aussi, en annexes, les **décisions
d'implémentation gelées** : elles sont arrêtées ici, par l'orchestrateur, pour qu'aucun lot
n'ait à les re-trancher et qu'aucun lot n'en décide une différemment d'un autre.

Référence qui fait foi : `docs/DECISIONS.md` (D1 à D10). Aucune décision de ce plan ne la
contredit.

---

## 1. Résultat visé

**Critère vérifiable de fin de phase 3**, énoncé pour être **exécuté**, pas relu :

> Sur une machine locale, avec l'application démarrée et une base PostgreSQL locale :
> (1) un **dossier fictif de démonstration** est saisi dans la bibliothèque via l'interface
> web et **validé par une action humaine nommée et horodatée** ; (2) un **DCE fictif**
> (PDF signalé comme fictif) est déposé dans l'interface ; (3) l'analyse produit une
> **liste de pièces exigées, une liste de critères et une date limite**, **chacun accompagné
> de sa source** (fichier + emplacement) ; (4) chaque élément peut être validé, corrigé ou
> supprimé par l'humain, et **seul un élément validé alimente la checklist** ; (5) la
> checklist produite **croise les pièces exigées avec la bibliothèque** et **signale comme
> manquant** ce qui manque, sans rien fabriquer ; (6) la suite de tests s'exécute réellement
> (unitaires + intégration) et **sa sortie est fournie**.

Condition de forme : **aucun** document interne de collectivité, **aucune** donnée réelle
d'entreprise, **aucun** secret dans le dépôt ; **rien n'est déployé**, aucun port n'est
exposé sur Internet.

Condition d'honnêteté : là où une exécution réelle est impossible (par exemple un appel à un
vrai fournisseur de modèle sans clé d'API), le rapport du lot l'écrit **« non testé »** — il
ne présente jamais un substitut comme la chose elle-même.

---

## 2. Périmètre

**Dans le périmètre** : socle technique ; bibliothèque d'entreprise ; analyse d'un DCE ;
checklist de conformité ; interface web minimale ; tests exécutés ; documentation
d'installation et de développement ; procédure de déploiement en France et scripts de
sauvegarde (sans déployer).

**Hors périmètre, pour toute la phase** (aucune tâche ne doit être ouverte sur ces sujets) :
mémoire technique rédigée automatiquement ; veille / détection d'appels d'offres ; dépôt de
pli, signature électronique, connexion aux plateformes d'achat public ; chiffrage, prix,
marge ; paiement réel et prestataire de facturation ; portail côté acheteur public ;
authentification multi-utilisateurs (au-delà de ce que `DATA-MODEL-V2` prévoit) ;
**mise en production** (le déploiement effectif exige l'accord explicite d'Anthony).

---

## 3. Les neuf lots (les huit lots d'origine, plus L2bis né de la révision n° 1)

| Lot | Titre | Agent | Dépend de | Chemin du livrable principal |
|---|---|---|---|---|
| L1 | Socle technique | `dev-back` | — | `src/migrations/0001_init_socle.sql`, `src/app/main.py`, `.env.example` |
| L2 | Bibliothèque d'entreprise | `dev-back` | L1 | `src/migrations/0002_bibliotheque.sql`, `src/app/services/bibliotheque.py` |
| L2bis | Exposition du provisionnement (`entreprise` + `fiche_version`) et script d'exploitant | `dev-back` | L2 | `src/app/api/routes_provisionnement.py`, `scripts/provisionnement.py` |
| L3 | Analyse de DCE | `dev-back` | L1 | `src/migrations/0003_analyse_dce.sql`, `src/app/services/analyse_dce.py` |
| L4 | Checklist de conformité | `dev-back` | L2, L3 | `src/migrations/0004_checklist.sql`, `src/app/services/checklist.py` |
| L5 | Interface web minimale | `dev-web` | L2, **L2bis**, L3, L4 | `src/app/web/templates/`, `src/app/web/routes_web.py` |
| L6 | Documentation installation et développement | `dev-web` | L5 | `docs/INSTALLATION.md`, `docs/DEVELOPPEMENT.md` |
| L7 | Procédure de déploiement en France + sauvegardes (sans déployer) | `infra` | L1 | `docs/DEPLOIEMENT-FRANCE.md`, `scripts/sauvegarde.sh` |
| L8 | Tests unitaires et d'intégration, vérification indépendante | `qa` | L1, L2, **L2bis**, L3, L4 | `src/tests/integration/`, `docs/RAPPORT-TESTS-PHASE-3.md` |

Chaque lot écrit en plus un **rapport d'exécution** dans `docs/RAPPORTS/L<n>-<sujet>.md`,
contenant les **commandes réellement lancées** et leur **sortie réelle**. Un rapport sans
sortie d'exécution ne vaut pas comme preuve.

### L1 — Socle technique (`dev-back`)

Livrables, chemins exacts :

- `.env.example` — toutes les variables attendues, **aucune valeur secrète**, avec
  commentaire expliquant chacune ;
- `src/requirements.txt` — dépendances épinglées ;
- `src/app/config.py` — lecture stricte des variables d'environnement ; échec explicite si
  une variable obligatoire manque ; **aucune valeur par défaut secrète** ;
- `src/app/storage/connexion.py` — connexion PostgreSQL et point d'entrée unique du SQL ;
- `src/app/storage/migrations.py` — exécuteur de migrations numérotées (« up » et « down »),
  sans ORM ni outil externe ;
- `src/migrations/0001_init_socle.sql` — tables racines et transverses, sections « up » et
  « down » séparées : `client`, `utilisateur`, `entreprise`, `fiche_version`, `fiche_famille`,
  `validation_relecture`, `tracabilite_valeur`, `jeu_reference`, `valeur_reference`,
  `document`, `abonnement`, `dossier`, `evenement_facturation`,
  `evenement_facturation_dossier` (noms et champs conformes à `docs/DATA-MODEL-V2.md`) ;
- `src/app/securite/chiffrement.py` — chiffrement applicatif des champs déclarés sensibles
  (voir annexe A) ;
- `src/app/securite/mots_de_passe.py` — hachage des mots de passe ;
- `src/app/storage/fichiers.py` — stockage des pièces **hors dépôt**, chemin préfixé par
  `client_id`, fichier chiffré sur disque ;
- `src/app/services/authentification.py` et `src/app/api/routes_authentification.py` —
  compte local, session ; un utilisateur = un client au MVP ;
- `src/app/api/cloisonnement.py` — dépendance obligatoire qui pose le `client_id` dans un
  contexte de requête, et par laquelle **tout** accès aux données doit passer ;
- `src/app/main.py` — application FastAPI exécutable ;
- `src/tests/conftest.py`, `src/tests/test_socle.py` — socle, migrations up/down, chiffrement,
  refus d'accès hors cloisonnement ;
- `docs/RAPPORTS/L1-socle.md`.

Contraintes propres : PostgreSQL **local uniquement** (`listen_addresses` limité à
`127.0.0.1`/`localhost`), base de test dédiée, aucune exposition réseau. L'état de la machine
est décrit en annexe D (Python 3.12 absent, PostgreSQL 18.3 présent mais arrêté).

### L2 — Bibliothèque d'entreprise (`dev-back`)

- `src/migrations/0002_bibliotheque.sql` — familles F1 à F9 : `entreprise_version`,
  `representant_legal`, `exercice_comptable`, `attestation`, `capacite_production`,
  `assurance`, `certification`, `reference_chantier`, `effectif_metier`, `organigramme`,
  `cv`, `moyen_materiel`, `produit`, `chapitre_memoire` ;
- `src/app/domain/` — entités complétées (une par famille) ;
- `src/app/storage/repositories.py` — dépôts **filtrés par `client_id`**, sans exception ;
- `src/app/services/bibliotheque.py` — saisie et consultation ;
- `src/app/services/versionnement.py` — `fiche_version`, les états de `fiche.statut_version`,
  `validation_relecture`, révocation à la première modification, contrôle par empreinte ;
- `src/app/api/routes_bibliotheque.py` — points d'entrée JSON `/api/v1/...` ;
- `src/tests/test_bibliotheque.py`, `src/tests/test_versionnement.py` ;
- `docs/RAPPORTS/L2-bibliotheque.md`.

Chiffrement : les champs du registre sensible (annexe A) sont chiffrés **par client**, pas
globalement. Un test doit montrer qu'un second client ne peut pas les déchiffrer.

### L2bis — Exposition du provisionnement et script d'exploitant (`dev-back`)

Né du constat du lot L2 (`docs/RAPPORTS/L2-bibliotheque.md` § 11 point 2 et § 12 point 6) :
le contrat de l'annexe C ne permettait de créer ni `client`, ni `entreprise`, ni
`fiche_version`, si bien que L5 ne pouvait pas faire démarrer une bibliothèque de zéro.
Décision et contrat exact : **annexe C § C2** (à implémenter tel quel, sans la re-trancher).

- `src/app/api/routes_provisionnement.py` — les **trois** routes du § C2 (`POST /api/v1/entreprises`,
  `GET /api/v1/entreprises`, `POST /api/v1/entreprises/{entreprise_id}/fiches`), montées dans
  `src/app/main.py` ;
- `scripts/provisionnement.py` — script d'exploitant pour la **racine** (`client` + premier
  compte d'accès), hors API, avec les seules fonctions existantes
  (`Connexion.creer_client`, `ServiceAuthentification.creer_utilisateur`) ;
- `src/tests/test_provisionnement.py` — exigences : la vérification d'appartenance de
  l'`entreprise` au client de la session **précède** toute ouverture de fiche ; un client ne
  peut pas créer de fiche sur l'`entreprise` d'un autre (400/404, **aucune ligne écrite**) ;
  aucune route du contrat existant n'est renommée ; le script refuse un mot de passe passé en
  argument ;
- `docs/RAPPORTS/L2bis-provisionnement.md`.

Aucune nouvelle migration : les tables existent depuis `0002`/`0001`. Aucune route existante
n'est modifiée ni renommée. Le provisionnement d'un `client` **reste hors API** (annexe C § C2).

### L3 — Analyse de DCE (`dev-back`)

- `src/migrations/0003_analyse_dce.sql` — extension de `document` + tables `consultation` et
  `extraction_element` (annexe B) ;
- `src/app/services/extraction_pdf.py` — extraction du texte ; **OCR si page sans texte
  exploitable** ; une page illisible est signalée « non analysable », jamais devinée ;
- `src/app/services/fournisseur_modele/base.py` — la couche d'abstraction (D8) ;
- `src/app/services/fournisseur_modele/fournisseur_factice.py` — fournisseur déterministe,
  utilisé par les tests, **explicitement signalé comme non-IQ réel** ;
- `src/app/services/fournisseur_modele/fournisseur_ue.py` — appel HTTP à un fournisseur
  France/UE, clé et adresse par variables d'environnement, **jamais appelé par les tests** ;
- `src/app/services/analyse_dce.py` — orchestration : dépôt → extraction texte → appel du
  fournisseur → restitution structurée (**pièces exigées, critères, date limite**), chaque
  élément portant **sa source** (document + emplacement) et un niveau de confiance ;
- `src/app/api/routes_analyse.py` — dépôt, lecture, validation/correction/suppression d'un
  élément ;
- `src/tests/fixtures/` — **jeu de démonstration fictif** : texte du DCE fictif + PDF fictif
  généré (dont une variante « scannée » pour l'OCR), chaque fichier portant en clair la
  mention « DOCUMENT FICTIF — DÉMONSTRATION » ;
- `src/tests/test_analyse_dce.py` ;
- **mise à jour de `docs/DATA-MODEL-V2.md`** : ajout de la section décrivant `consultation`,
  `extraction_element` et les tables de la checklist (annexe B) — **L3 est le seul lot à
  écrire dans ce fichier** ;
- `docs/RAPPORTS/L3-analyse-dce.md`.

Interdit absolu : que la restitution **invente** une pièce, un critère ou une date absents du
document. Un élément introuvable est restitué « non trouvé dans le document ».

### L4 — Checklist de conformité (`dev-back`)

- `src/migrations/0004_checklist.sql` — tables `checklist_execution` et `checklist_ligne`
  (annexe B) ;
- `src/app/services/checklist.py` — croisement **pièces exigées validées** × **bibliothèque** ;
  chaque ligne est `presente`, `manquante` ou `a_verifier` ; **aucune ligne sans source** ;
  une correspondance incertaine est `a_verifier`, jamais `presente` ;
- `src/app/api/routes_checklist.py` ;
- `src/tests/test_checklist.py` — cas obligatoires : pièce absente → `manquante` ; échéance
  passée → `a_verifier` avec la raison ; extraction partielle → la checklist le dit ;
  bibliothèque vide → beaucoup de `manquante`, rien d'inventé ;
- `docs/RAPPORTS/L4-checklist.md`.

Contrainte propre : **seuls les éléments `extraction_element.statut_verification = valide`
alimentent la checklist** (verrou n° 2 de `docs/SPEC-MVP-V2.md` § 2). Un test doit le montrer.

### L5 — Interface web minimale (`dev-web`)

- `src/app/web/routes_web.py`, `src/app/web/templates/`, `src/app/web/static/` ;
- écrans : connexion ; **première utilisation** (création de l'`entreprise` et de sa première
  `fiche_version` via les routes du § C2 — un client sans fiche ne doit plus être un cul-de-sac) ;
  état de la bibliothèque ; saisie par famille ; validation humaine
  bloquante (relecteur nommé + attestation cochée) ; dépôt d'un DCE ; affichage de l'analyse
  **avec la source sous chaque élément** ; validation/correction/suppression d'un élément ;
  affichage de la checklist et du résumé des manques ;
- `src/tests/test_web.py` ;
- `docs/RAPPORTS/L5-interface-web.md`.

HTML rendu côté serveur, **aucun framework JavaScript, aucun build Node** (annexe A).
La mention « brouillon — à relire et à signer » doit apparaître sur toute sortie de nature à
engager l'entreprise. Aucun bouton « déposer », « envoyer » ou « signer ».

### L6 — Documentation d'installation et de développement (`dev-web`)

- `docs/INSTALLATION.md` — prérequis, installation, création de la base, migrations,
  démarrage, jeu de démonstration ; comprend la **procédure de provisionnement** de l'annexe C
  § C2 (script `scripts/provisionnement.py` : création d'un `client` fictif puis de son premier
  compte d'accès, mot de passe **jamais en argument ni dans le dépôt**), et la marche à suivre
  pour démarrer une bibliothèque depuis l'interface ;
- `docs/DEVELOPPEMENT.md` — architecture, conventions, migrations, tests, ajout d'un écran ;
- `docs/RAPPORTS/L6-documentation.md` — **la procédure d'installation doit être déroulée
  pour de vrai** et sa sortie jointe.

### L7 — Procédure de déploiement en France et sauvegardes (`infra`)

- `docs/DEPLOIEMENT-FRANCE.md` — hébergement en région française, PostgreSQL managé,
  chiffrement au repos, sauvegardes, journalisation, procédure de restauration ; **procédure
  écrite, rien n'est déployé, aucun compte n'est ouvert** ;
- `scripts/sauvegarde.sh` et `scripts/restauration.sh` — **exécutés réellement sur la base
  locale** pendant le lot, avec la sortie jointe ;
- `docs/RAPPORTS/L7-deploiement.md`.

Interdit : ouvrir un port sur Internet, provisionner un service, engager une dépense.

### L8 — Tests et vérification indépendante (`qa`)

- `src/tests/integration/` — parcours de bout en bout sur données fictives ;
- **test d'isolation** : tenter d'accéder aux données d'un client depuis le compte d'un autre
  et **démontrer que l'accès échoue** (exigence `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 8.3) ;
- `docs/RAPPORT-TESTS-PHASE-3.md` — plan de test de la phase, résultats **réellement
  observés**, échecs compris, et ce qui **n'a pas pu être testé** (par exemple le fournisseur
  de modèle réel sans clé d'API) ;
- `docs/RAPPORTS/L8-tests.md`.

L8 est **indépendant** des lots d'implémentation : il ne se contente pas de relancer leurs
tests, il écrit les siens et cherche à les faire échouer. Il ne corrige pas le code des
autres lots : il constate et rapporte.

---

## 4. Ordre, parallélismes, et pourquoi

```
Vague 1 :  L1  (socle)                       ← tout en dépend
Vague 2 :  L2  ∥  L3  ∥  L7                 ← trois chemins disjoints, fichiers distincts
Vague 3 :  L4  (dépend de L2 et L3)  ∥  L2bis  (dépend de L2 seulement)
Vague 4 :  L5  (dépend de L2, L2bis, L3, L4)
Vague 5 :  L6  ∥  L8  (dépendent du code des vagues 1 à 4)
```

- **L1 d'abord, sans exception** : configuration, base, migrations, authentification,
  cloisonnement, chiffrement sont le support de tout le reste.
- **L2 et L3 en parallèle** : la bibliothèque et l'analyse d'un DCE ne partagent que le socle.
  Elles écrivent dans des migrations différentes (`0002`, `0003`) — contrainte de numérotation
  gelée en annexe A pour éviter tout conflit.
- **L4 après L2 et L3** : une checklist se calcule sur les pièces exigées **et** sur la
  bibliothèque ; la coder avant ses deux entrées produirait un test creux.
- **L5 après L4** : les écrans affichent l'analyse et la checklist ; les construire contre une
  API non figée serait du travail à jeter. Le contrat d'API est **gelé** en annexe C, ce qui
  est la vraie parade à l'attente.
- **L2bis en vague 3, en parallèle de L4** : l'exposition du provisionnement ne dépend que de
  L2 (les fonctions de service existent déjà). L5 l'attend parce que son écran de première
  utilisation appelle ces routes : sans L2bis, un client neuf reste bloqué au 404.
- **L6 et L8 à la fin**, sur du code stable.
- **L7 en vague 2** : la procédure de déploiement et les scripts de sauvegarde ne dépendent que
  du socle ; ils n'attendent ni l'analyse ni l'interface.

Aucun lot ne dépend d'un lot pour une **décision** : toutes les décisions de structure, de
nommage et d'interface sont arrêtées dans les annexes A, B et C de ce plan. Chaque lot ne
dépend d'un autre que pour du **code existant**.

---

## 5. Risques

| # | Risque | Prob. | Impact | Parade |
|---|---|---|---|---|
| R1 | L'environnement ne sait pas exécuter la cible : Python 3.12 **absent**, PostgreSQL **arrêté**, `tesseract` **absent**, Docker **absent** (annexe D) | Élevée | Fort (bloque les tests réels) | L1 installe `python@3.12` et démarre PostgreSQL **local** (`Postgres.app` présent, données `var-18`) ; L3 annonce et installe `tesseract` avant de l'utiliser. Si une installation échoue, le rapport du lot le dit et marque le chemin concerné **« non testé »** |
| R2 | `Postgres.app` réside sur un volume externe (`/Volumes/SAVE SSD`) : volume démonté = base indisponible | Moyenne | Moyen | L1 documente et permet les **deux** chemins : base sur le volume existant, ou `initdb` d'une base neuve sous le disque interne, hors dépôt |
| R3 | **Aucune clé d'API d'un fournisseur France/UE** : la brique B ne peut pas être prouvée avec un vrai modèle | Élevée | Fort sur la valeur démontrée | Adaptateur + **fournisseur factice** pour les tests ; le chemin réel (fournisseur France/UE) est codé mais **non testé tant qu'aucune clé n'est fournie** — écrit franchement, pas contourné. Question ouverte n° 1 |
| R4 | Le modèle v2 **ne couvre pas les briques B et C** (constat **S2**, `docs/REVUE-SECURITE.md`) | Certaine | Fort (base non implémentable en l'état) | Les tables manquantes sont **décidées ici** (annexe B) : L3 écrit la mise à jour de `docs/DATA-MODEL-V2.md`, L4 implémente sans y toucher |
| R5 | Divergence de clé de cloisonnement `entreprise_id` / `client_id` (constat **S1**) répliquée dans le code | Moyenne | Fort | Décision gelée : la clé est **`client_id`**, partout (annexe A). Interdiction explicite dans chaque carte |
| R6 | Étalement du chemin critique L1 → L2 → L3 → L4 → L5 | Élevée | Moyen (délai) | Interfaces gelées (annexes B, C) ; fichiers strictement disjoints entre lots ; L2 ∥ L3 ∥ L7 en vague 2 |
| R7 | Une donnée réelle ou un secret entre dans le dépôt (D4, D10, ligne rouge) | Faible à moyenne | Fort (juridique) | Jeux de test **fictifs et signalés** ; clés uniquement par variables d'environnement ; `data/` hors dépôt ; contrôle `qa` (L8) par recherche de motifs (SIRET, IBAN, clés) |
| R8 | Clé de chiffrement dans le dépôt, ou chiffrement **global** au lieu de par client | Moyenne | Fort | Clé maîtresse par variable d'environnement uniquement ; clé de données dérivée **par `client_id`** ; test de non-déchiffrement croisé ; recherche de motifs en revue |
| R9 | Une requête SQL échappe au filtre de cloisonnement | Moyenne | Fort (D6) | Le SQL est **centralisé** dans `src/app/storage/connexion.py`, qui exige un contexte client ; test d'isolation dès L1, refait **indépendamment** par L8 |
| R10 | Les installations de dépendances modifient la machine d'Anthony sans son accord | Certaine | Faible à moyen | Chaque lot **annonce et justifie** ses dépendances avant de les installer ; installation dans un environnement virtuel du projet ; versions documentées |
| R11 | Dépassement de périmètre (paiement, veille, mémoire technique rédigée, mise en production) | Moyenne | Moyen | Hors-périmètre recopié dans **chaque** carte ; L8 le contrôle explicitement |
| R12 | L'OCR est annoncé comme fonctionnel alors qu'il ne l'est pas (page scannée non testée) | Moyenne | Moyen (crédibilité) | Le jeu de test contient **une page scannée fictive** ; si `tesseract` ne peut pas être installé, le chemin OCR est livré **et déclaré non testé**, jamais présenté comme validé |
| R13 | Les routes de provisionnement deviennent un vecteur d'écriture mal filtré (créer une `entreprise`, ouvrir une fiche) | Faible à moyenne | Fort (cloisonnement, A1) | `client_id` pris **exclusivement de la session**, jamais du corps de requête ; **vérification d'appartenance de l'`entreprise` au client avant toute ouverture de fiche** ; `404` (et non `403`) pour une cible d'un autre client ; test croisé dédié dans L2bis puis refait par L8 |
| R14 | `fiche_version` n'a **pas** de contrainte d'intégrité croisée `(client_id, entreprise_id)` en base : un `entreprise_id` étranger passerait la clé étrangère | Certaine (constat de lecture) | Moyen | Risque **résiduel accepté au MVP** : toutes les écritures passent par le service, qui doit contrôler l'appartenance (R13) ; les lectures restent filtrées par `client_id`. Correctif structurel (index/contrainte composite + migration) **hors de cette révision** : il exigerait une migration et une écriture dans `docs/DATA-MODEL-V2.md` (propriété du lot L3) |

---

## 6. Questions ouvertes pour Anthony

Aucune de ces questions ne bloque le démarrage : le travail peut avancer avec la réponse par
défaut indiquée. Elles bloquent en revanche la **démonstration finale** et la mise en service.

1. **Clé d'accès à un fournisseur de modèle France ou UE** (Mistral AI, OVHcloud AI
   Endpoints). Sans elle, la brique B est livrée et testée **avec un fournisseur factice**
   seulement : l'analyse ne sera pas prouvée avec un vrai modèle. *Défaut retenu : fournisseur
   factice, chemin réel codé mais non testé.*
2. **Formats de DCE acceptés** (constat **C5**). *Défaut retenu : PDF en priorité (y compris
   scanné, via OCR) et texte brut ; les formats bureautiques sont refusés explicitement plutôt
   qu'acceptés sans traitement.*
3. **Famille « mémoire technique type » dans le MVP** (constat **C6**). *Défaut retenu : la
   famille est **stockée** (le modèle la porte) mais aucune exploitation automatique ; c'est
   conforme à `docs/SPEC-MVP-V2.md` § 7.1 option A.*
4. **Fenêtre d'alerte des échéances** (nombre de jours avant expiration). *Défaut retenu :
   aucun seuil en dur ; valeur réglable, avec un défaut neutre documenté comme tel.*
5. **Cible d'hébergement pour la procédure de déploiement** : Scaleway `fr-par` ou OVHcloud
   `eu-west-par` / `eu-west-gra`, sur une base **managée** PostgreSQL (D9). *Défaut retenu :
   procédure écrite pour les deux, aucun compte ouvert, aucune dépense engagée.*
6. **Base PostgreSQL locale pour le développement** : confirmation d'utiliser l'instance
   `Postgres.app` déjà présente (18.3, données `var-18`) plutôt que d'en installer une autre.
   *Défaut retenu : instance existante, sinon base neuve créée par `initdb` sous le disque
   interne, hors dépôt.*

Question différée, déjà documentée et bloquante pour la commercialisation seulement :
le portage juridique et le conflit d'intérêts (D4), et la qualification RGPD
responsable / sous-traitant — à traiter par un juriste, hors phase 3.

---

## Annexe A — Décisions d'implémentation gelées

Elles sont arrêtées ici. Un lot qui veut les changer **le signale en commentaire sur sa carte**
au lieu de décider seul.

**A1. Clé de cloisonnement unique : `client_id`.** Jamais `entreprise_id` comme clé
d'isolation (constat S1). `client_id` est présent sur toute entité de contenu, y compris
lorsqu'il serait déductible par jointure.

**A2. Conventions de nommage.** Celles de `src/README.md` et de `docs/DATA-MODEL-V2.md` :
tables et champs en `snake_case` français, identifiants techniques en UUID v4, dates en
ISO 8601, booléens en 0/1, aucune fonctionnalité propriétaire présumée du moteur. Vocabulaire
métier en français, code et identifiants techniques en anglais quand la bibliothèque standard
l'impose.

**A3. Arborescence et règle de dépendance.**

```
src/app/config.py          lecture des variables d'environnement
src/app/main.py            application FastAPI (objet `app`), point d'entrée exécutable
src/app/domain/            entités — bibliothèque standard uniquement
src/app/storage/           connexion.py, migrations.py, repositories.py, fichiers.py
src/app/services/          logique applicative, y compris fournisseur_modele/
src/app/securite/          chiffrement.py, mots_de_passe.py
src/app/api/               routes JSON (`/api/v1/...`) et cloisonnement.py
src/app/web/               écrans HTML rendus côté serveur (templates/, static/, routes_web.py)
src/migrations/            000N_*.sql
src/tests/                 conftest.py, fixtures/, unitaires, integration/
```

Règle de dépendance : `web`/`api` → `services` → `storage` → `domain`. `domain` ne dépend de
rien d'autre que la bibliothèque standard. Aucune couche n'accède à la persistance en
contournant `storage`.

**A4. Migrations.** Un fichier par changement, nommé `000N_description.sql`, deux sections
balisées `-- +migrate up` et `-- +migrate down`. Numéros **réservés** :
`0001_init_socle.sql` (L1), `0002_bibliotheque.sql` (L2), `0003_analyse_dce.sql` (L3),
`0004_checklist.sql` (L4). Aucune migration déjà appliquée n'est modifiée. Aucun ORM, aucun
outil de migration externe.

**A5. Authentification.** Compte local : identifiant + mot de passe haché ; session par
cookie signé ; **un utilisateur appartient à un seul `client`** au MVP. Aucun secret dans le
code : la clé de session et la clé de chiffrement vivent en variables d'environnement.

**A6. Chiffrement applicatif.** AES-256-GCM via la bibliothèque `cryptography`. Une **clé
maîtresse** par variable d'environnement ; une **clé de données dérivée par `client_id`**
(HKDF, sel = `client_id`) — le chiffrement est **par client, jamais global**. Format stocké
préfixé par une version (`v1:…`) pour rester réversible. Registre des champs chiffrés, repris
de `docs/DATA-MODEL-V2.md` § 13.2 :

- `entreprise_version` : `iban`, `bic`, `piece_rib`, `siret_siege`,
  `numero_tva_intracommunautaire` ;
- `representant_legal` : `nom`, `prenom`, `date_nomination`, `piece` ;
- `exercice_comptable` : tous les `montant`, `piece` ;
- `attestation` : `piece`, `montant_engage` ;
- `reference_chantier` : `contact_reference`, `montant` ;
- `cv` : `nom`, `prenom`, `diplomes`, `cv_piece` ;
- fichiers de `document` : chiffrés sur disque lorsque `sensibilite = confidentiel`.

Les fichiers sont stockés **hors dépôt**, sous un chemin préfixé par le client ; aucun nom de
fichier fourni par l'utilisateur n'est utilisé tel quel.

**A7. Fournisseur de modèle (D8).** Couche d'abstraction dans
`src/app/services/fournisseur_modele/` : `base.py` (l'interface), `fournisseur_factice.py`
(déterministe, utilisé par les tests), `fournisseur_ue.py` (HTTP, fournisseur France/UE, clé
et adresse par variables d'environnement). Sélection par une variable
d'environnement (`MODELE_FOURNISSEUR`). **Aucun appel réseau dans les tests.** Aucun
entraînement : les appels se font avec les options de non-conservation lorsque le fournisseur
les propose ; le code documente ce qu'il demande, il ne promet rien de plus.

**A8. Interface web.** HTML rendu côté serveur (Jinja2), CSS simple, **aucun framework
JavaScript, aucun build Node**. Toute sortie engageante porte la mention
« brouillon — à relire et à signer ». Aucun bouton de dépôt, d'envoi ou de signature.

**A9. Ligne rouge dans le code.** `origine` ne prend que `document_extrait` ou
`saisie_entreprise` ; jamais de valeur « générée par l'IA ». Une valeur sans source est
affichée comme **non vérifiée** (`confiance = a_verifier`), jamais présentée comme un fait.
Aucun champ de prix, de marge ou de garantie de conformité nulle part.

**A10. Dépendances.** Liste autorisée, à annoncer avant installation :
`fastapi`, `uvicorn`, `jinja2`, `psycopg[binary]`, `pydantic`, `cryptography`, `argon2-cffi`,
`itsdangerous`, `python-multipart`, `pypdf`, `pytesseract` (+ binaire `tesseract`), `pytest`,
`httpx`. Python **3.12** (à installer : absent de la machine, annexe D). Toute autre
dépendance est annoncée et justifiée avant ajout.

**A11. Tests.** `pytest`. Base PostgreSQL **locale** dédiée aux tests, migrations appliquées
puis annulées (`up` / `down`) par la suite. Aucun port exposé sur Internet. Les tests
s'exécutent réellement : la sortie est jointe au rapport du lot.

---

## Annexe B — Extension du modèle pour les briques B et C (gelée)

Motif : le constat **S2** (`docs/REVUE-SECURITE.md`) établit que les briques B et C n'ont
**aucune** représentation dans `docs/DATA-MODEL-V2.md`. Ce plan tranche à leur place. Les
noms ci-dessous sont **définitifs** : L3 et L4 les implémentent tels quels. L3 est le **seul**
lot à écrire dans `docs/DATA-MODEL-V2.md`.

**B1. `document` — extension (migration `0003`).**

- nouveau champ `nature` (`code_reference` `document.nature`) : `piece_bibliotheque` |
  `dce` — obligatoire, défaut `piece_bibliotheque` ;
- `entreprise_id` et `fiche_version_id` deviennent **NULL-ables** ;
- nouveau champ `consultation_id` (`reference` `consultation.id`), NULL-able ;
- `client_id` reste **non nul** (I1 tient) ;
- **invariant I7** : `nature = piece_bibliotheque` ⇒ `entreprise_id` et `fiche_version_id`
  non nuls ; `nature = dce` ⇒ `consultation_id` non nul.

Motif : un DCE est un document de l'acheteur, extérieur à la bibliothèque ; le modèle actuel
lui interdit structurellement d'exister sans fausser la bibliothèque.

**B2. `consultation` — le DCE déposé et analysé.**

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | l'entreprise qui répond |
| `dossier_id` | `reference` `dossier.id` | non | rattachement à la facturation (D3) |
| `libelle` | `texte_court` | oui | nom donné par l'entreprise |
| `reference_consultation` | `texte_court` | non | saisie par l'humain ; l'outil ne va rien chercher |
| `maitre_ouvrage_declare` | `texte_court` | non | saisi par l'humain, **jamais déduit** |
| `statut` | `code_reference` `consultation.statut` | oui | `deposee` \| `analysee` \| `verifiee` \| `abandonnee` |
| `date_creation`, `date_modification` | `horodatage` | oui | — |
| `sensibilite` | `code_reference` `securite.sensibilite` | oui | défaut `interne` |
| `statut_enregistrement` | `code_reference` `commun.statut_enregistrement` | oui | `actif` \| `archive` |

**B3. `extraction_element` — un élément proposé puis vérifié par un humain.**

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `consultation_id` | `reference` `consultation.id` | oui | — |
| `categorie` | `code_reference` `consultation.categorie_element` | oui | `piece_exigee` \| `critere` \| `date_limite` |
| `libelle` | `texte_long` | oui | l'élément tel qu'extrait |
| `valeur` | `texte_long` | non | pondération, date ISO 8601, précision |
| `source_document_id` | `reference` `document.id` | **oui** | document de nature `dce` — **aucune valeur sans source** |
| `source_emplacement` | `texte_court` | **oui** | page ou section |
| `source_extrait` | `texte_long` | non | extrait littéral du document |
| `confiance` | `code_reference` `tracabilite.confiance` | oui | valeur initiale `a_verifier` |
| `statut_verification` | `code_reference` `consultation.statut_verification` | oui | `propose` \| `valide` \| `corrige` \| `supprime` |
| `verificateur_nom` | `texte_court` | oui si `statut_verification` ∈ {`valide`, `corrige`} | saisi par l'humain |
| `date_verification` | `horodatage` | non | posée automatiquement par l'action humaine |
| `date_extraction` | `horodatage` | oui | — |
| `moteur_fournisseur` | `texte_court` | non | ex. `factice`, `mistral`, `ovh` |
| `moteur_modele` | `texte_court` | non | nom du modèle employé |
| `date_creation`, `date_modification` | `horodatage` | oui | — |
| `sensibilite`, `statut_enregistrement` | `code_reference` | oui | conformes à § 3.2 |

Contrainte opposable : **seul un élément dont `statut_verification = valide` alimente la
checklist** (verrou n° 2, `docs/SPEC-MVP-V2.md` § 2).

**B4. `checklist_execution` — une exécution de la checklist.**

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `consultation_id` | `reference` `consultation.id` | oui | — |
| `fiche_version_id` | `reference` `fiche_version.id` | oui | **quelle fiche a servi** |
| `date_execution` | `horodatage` | oui | — |
| `execute_par` | `texte_court` | oui | nom saisi par l'humain |
| `nb_exigences` | `entier` | oui | — |
| `nb_presentes` | `entier` | oui | — |
| `nb_manquantes` | `entier` | oui | — |
| `nb_a_verifier` | `entier` | oui | — |
| `extraction_partielle` | `booleen` | oui | vrai si des éléments lus sont restés non validés |
| `sensibilite`, `statut_enregistrement` | `code_reference` | oui | conformes à § 3.2 |

**B5. `checklist_ligne` — une ligne de résultat.**

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `checklist_execution_id` | `reference` `checklist_execution.id` | oui | — |
| `extraction_element_id` | `reference` `extraction_element.id` | oui | l'exigence comparée |
| `libelle_piece` | `texte_court` | oui | l'exigence, telle que validée |
| `statut` | `code_reference` `checklist.statut_ligne` | oui | `presente` \| `manquante` \| `a_verifier` |
| `justification` | `texte_long` | oui | la pièce de la bibliothèque qui satisfait l'exigence, ou la raison du manque |
| `document_id` | `reference` `document.id` | non | renseigné si et seulement si `statut = presente` |
| `date_creation`, `date_modification` | `horodatage` | oui | — |
| `sensibilite`, `statut_enregistrement` | `code_reference` | oui | conformes à § 3.2 |

**Invariant I8** : une ligne `presente` référence **obligatoirement** un `document_id` du même
`client_id` ; une ligne `manquante` ne référence **aucun** document. Une correspondance
incertaine est `a_verifier`, **jamais** `presente`.

**B6. Jeux de référence à créer** (structure `jeu_reference` / `valeur_reference` déjà en
place) : `document.nature`, `consultation.statut`, `consultation.categorie_element`,
`consultation.statut_verification`, `checklist.statut_ligne`. Plus le jeu déjà attendu
`document.type_document` (résolution du constat **C4**), dont le contenu doit rester
**extensible** (D2) et sans valeur inventée : les valeurs non sourcées sont marquées
`statut = a_verifier`.

**B7. Ce que cette annexe ne fait pas.** Elle n'ajoute aucun prix, aucun seuil, aucune durée
légale, aucune garantie de conformité. Aucun de ces champs ne peut être alimenté par une
valeur inventée : `source_document_id` et `source_emplacement` sont **obligatoires** sur tout
élément extrait.

---

## Annexe C — Contrat d'API (gelé)

Chemins **figés** ici pour que L5 puisse être écrit sans attendre L4, et pour qu'aucun lot ne
renomme une route en cours de route.

JSON, préfixe `/api/v1` :

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/connexion` | ouverture de session |
| `POST` | `/api/v1/deconnexion` | fermeture de session |
| `GET` | `/api/v1/bibliotheque` | état d'avancement, par famille |
| `GET` | `/api/v1/bibliotheque/{famille}` | contenu d'une famille |
| `POST` | `/api/v1/bibliotheque/{famille}` | création / modification d'un élément |
| `POST` | `/api/v1/bibliotheque/validation` | `validation_relecture` (nom du relecteur + attestation cochée) |
| `POST` | `/api/v1/consultations` | dépôt d'un DCE (multipart) ; crée `consultation` + `document(nature=dce)` |
| `GET` | `/api/v1/consultations/{id}` | consultation et éléments extraits, **avec leur source** |
| `POST` | `/api/v1/consultations/{id}/elements/{element_id}` | valider / corriger / supprimer un élément |
| `POST` | `/api/v1/consultations/{id}/checklist` | exécuter la checklist |
| `GET` | `/api/v1/consultations/{id}/checklist` | lignes et résumé des manques |

Écrans HTML sur `/` : `/connexion`, `/bibliotheque`, `/bibliotheque/{famille}`,
`/consultations`, `/consultations/{id}`, `/consultations/{id}/checklist`.

Règles de réponse : toute valeur renvoyée porte `origine`, `confiance` et, si elle est
extraite, `source_document_id` et `source_emplacement`. Une exigence introuvable est renvoyée
avec la mention explicite « non trouvé dans le document » — jamais comblée.

### C2 — Provisionnement (ajouté à la révision n° 1, 30 septembre 2026 ; gelé comme le reste)

Décision **unique**, en deux volets insécables, prise par `plan` (tâche `t_5b51c472`) sur le
constat du lot L2 (`docs/RAPPORTS/L2-bibliotheque.md` § 11 point 2 et § 12 point 6) :

1. **`entreprise` et `fiche_version` passent par l'API** — extension bornée du contrat ;
2. **`client` et le compte d'accès restent hors API** — script exécuté par l'exploitant.

Motif du volet 2, **structurel et non un choix de confort** : l'annexe A § A5 pose qu'un
utilisateur appartient à **un seul** client. Aucune session ne peut donc exister avant que le
`client` existe, et le modèle ne connaît **aucun** rôle transverse. Une route non authentifiée
qui créerait un `client` serait un point d'entrée ouvert pour fabriquer des locataires : refusé.
Le provisionnement de la racine est un geste d'exploitant, une fois par client.

Motif du volet 1 : une `entreprise` et une `fiche_version` se créent **dans le contexte d'un
client authentifié**, `client_id` pris de la session — même cloisonnement que tout le reste.
Sans ces routes, L5 ne peut pas faire démarrer une bibliothèque de zéro : l'écran de première
utilisation n'a aucun chemin.

Routes ajoutées (définitives, **mêmes règles de gel** que le tableau ci-dessus) :

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/entreprises` | crée l'`entreprise` (`libelle_court`) **et** sa première `fiche_version`, dans une seule transaction |
| `GET` | `/api/v1/entreprises` | les `entreprise` du client de la session, avec leur dernière `fiche_version` |
| `POST` | `/api/v1/entreprises/{entreprise_id}/fiches` | ouvre une **nouvelle** version (`ouvrir_fiche`) ; numéro croissant par entreprise |

Réponses : `201` (création) avec `{entreprise_id, fiche_version_id, numero_version, statut}` —
`200` (lecture) — `400` libellé vide ou corps invalide — `404` entreprise hors du client —
`401` sans session. Une cible d'un autre client répond `404`, **jamais** `403` : ne pas révéler
qu'elle existe (même règle que `CibleInconnue`).

Règles d'implémentation **obligatoires** :

- `client_id` vient **exclusivement de la session** (`src/app/api/cloisonnement.py`) ; il n'est
  **jamais** lu dans le corps de la requête ni dans le chemin.
- **Contrôle d'appartenance avant toute écriture** : `POST /api/v1/entreprises/{id}/fiches`
  vérifie que l'`entreprise` est bien du client de la session **avant** d'appeler `ouvrir_fiche`.
  Nécessaire parce que `fiche_version` ne porte aucune contrainte croisée `(client_id,
  entreprise_id)` en base (risque **R14** du § 5).
- Les routes appellent les fonctions existantes `creer_entreprise()`, `ouvrir_fiche()` et
  `DepotEntreprise.lister/obtenir` : **aucune nouvelle écriture SQL**, aucun SQL hors de
  `storage/` (règle R9), aucune nouvelle migration.
- **Aucune** des quatre routes existantes de la bibliothèque n'est renommée ni modifiée. Le 404
  « Provisionnez une entreprise et une version de fiche » reste le comportement de
  `GET /api/v1/bibliotheque` tant qu'aucune fiche n'existe ; il cesse d'être un cul-de-sac.

**Volet 2 — provisionnement de la racine, hors API.** Script `scripts/provisionnement.py`,
exécuté par l'exploitant sur la base, hors interface :

- `client` créé par `Connexion.creer_client(libelle)` — exception nommée et bornée de L1, seul
  point d'entrée légitime **hors** contexte client (annexe A § A1) ;
- premier compte créé par `ServiceAuthentification.creer_utilisateur(ContexteClient(client_id),
  identifiant, nom_affichage, mot_de_passe)`, le contexte étant construit avec le `client_id`
  qui vient d'être créé ;
- le mot de passe est saisi **au clavier** (saisie masquée) ; le script **refuse** un mot de
  passe passé en argument de ligne de commande (visible par `ps`) ; il n'est ni journalisé, ni
  écrit dans un fichier, ni stocké en variable d'environnement persistée ; il est haché Argon2id
  par `securite/mots_de_passe.py` ;
- sortie : les identifiants techniques créés (UUID) — **jamais** le mot de passe ;
- pas de SQL nouveau : le script n'appelle que les fonctions ci-dessus ;
- procédure et exemple de session (fictifs, signalés) documentés dans `docs/INSTALLATION.md`
  (lot L6) ; exécution refaite indépendamment par L8.

Qui crée quoi, sans ambiguïté :

| Objet | Créé par | Par quel chemin | Quand |
|---|---|---|---|
| `client` | exploitant | `scripts/provisionnement.py` | une fois par client, à l'installation |
| compte d'accès | exploitant | `scripts/provisionnement.py` | à l'installation, puis pour chaque compte ajouté |
| `entreprise` + 1re `fiche_version` | utilisateur connecté | `POST /api/v1/entreprises` | première utilisation |
| `fiche_version` suivante | utilisateur connecté | `POST /api/v1/entreprises/{id}/fiches` | nouveau dossier ou nouvelle campagne |

**Ce que C2 ne décide pas** (et ne doit pas être improvisé par un lot) : aucun rôle
d'administration, aucune inscription spontanée, aucune invitation par courriel, aucune
réinitialisation de mot de passe par l'interface, aucun changement de mot de passe exposé hors
du service existant. Ces sujets supposeraient un modèle de rôles que l'annexe A § A5 n'a pas :
ils restent **hors périmètre de la phase 3**.

---

## Annexe D — État de la machine, vérifié le 30 septembre 2026 à 11h13 (+04)

Constats issus de commandes réellement exécutées (macOS 27.0.1, arm64) :

| Élément | Constat | Conséquence |
|---|---|---|
| Python | `python3` = **3.9.6** (`/usr/bin/python3`, Xcode). **Aucun Python 3.12** ; aucun Python Homebrew installé | L1 doit installer `python@3.12` (Homebrew) et créer un environnement virtuel de projet |
| PostgreSQL | **PostgreSQL 18.3** via `Postgres.app` (`/Volumes/SAVE SSD/Application/Postgres.app/...`), données `~/Library/Application Support/Postgres/var-18` (initialisées), serveur **arrêté** (`pg_ctl status` : *no server running*) | L1 démarre l'instance locale ou en initialise une neuve ; **rien n'est exposé sur Internet** |
| OCR | `tesseract` **absent** | L3 annonce et installe `tesseract` ; sinon OCR déclaré non testé (R12) |
| Lecture PDF | `pdftotext` / `pdfinfo` (poppler 26.06) **présents** | Le chemin texte est disponible sans installation |
| Conteneurs | `docker`, `colima`, `podman` **absents** | Aucune solution « tout-en-un » : PostgreSQL local assumé |
| Réseau | PyPI et Formulae Homebrew joignables (`HTTP 200`) | Les installations sont possibles |
| Disque | **71 Go** libres sur `/` | Suffisant pour Python 3.12, PostgreSQL, tesseract |
| Node | `node 25.9.0` | Non utilisé : l'interface est rendue côté serveur (A8) |

---

*Fin du plan de phase 3. Les lots sont créés sur le board, liés à la tâche racine
`t_3c57fd67` comme parent, avec leurs dépendances exprimées par `parents` — jamais par du
texte. Toute décision non couverte par les annexes A, B et C doit être signalée en commentaire
de carte, pas tranchée en silence.*
