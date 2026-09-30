# L5 — Interface web minimale : rapport d'exécution

*Lot **L5** (`t_2cfef350`), agent `dev-web`. Phase 3. Écrit le 30 septembre 2026 à 12h20 (+04).*
*Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*
*Jeux de démonstration **fictifs et signalés** : aucune donnée réelle d'entreprise, aucun
document de collectivité, aucun secret.*

---

## 1. Ce qui a été livré

| Fichier | Rôle |
|---|---|
| `src/app/web/routes_web.py` | Les écrans HTML (`/`) et les `POST` de leurs formulaires |
| `src/app/web/templates/` | 9 gabarits Jinja2 : `base`, `connexion`, `premiere_utilisation`, `bibliotheque`, `famille`, `consultations`, `consultation`, `checklist`, `erreur` |
| `src/app/web/static/style.css` | CSS simple, responsive, sans framework |
| `src/app/web/__init__.py` | Explication de la couche |
| `src/app/storage/depot_consultations.py` | **Ajout** : dépôt de *lecture seule* des `consultation` du client, pour que l'écran `/consultations` liste ce qui existe (voir § 6.2) |
| `src/app/main.py` | **2 modifications** : `include_router(routes_web.router)` et montage du CSS sur `/static` (11 lignes ajoutées) |
| `src/tests/test_web.py` | 14 tests |
| `docs/RAPPORTS/captures-L5/` | 4 captures d'écran réelles |

**Aucune route `/api/v1` n'a été créée, renommée ni modifiée.** Le contrat de l'annexe C est
intact : les écrans appellent les **services** (`app.services`) dans le processus, comme le font
les routes JSON — aucune requête HTTP en boucle sur soi-même. Vérifié :

```
GET /                 -> 200 {'application': 'ia-consultations-publiques', 'version': '0.1.0', 'documentation': '/docs'}
```

Aucune dépendance nouvelle : `jinja2`, `python-multipart` et `httpx` étaient déjà épinglés dans
`src/requirements.txt` (annexe A § A10). Aucun `npm`, aucun `node`, aucun JavaScript, aucun build.

### Écrans couverts

| Chemin (annexe C) | Méthode | Écran |
|---|---|---|
| `/connexion` | GET, POST | Connexion (aucune inscription, aucune réinitialisation) |
| `/deconnexion` | POST | Fermeture de session |
| `/entreprises/nouvelle` | GET | Écran de **première utilisation** (D2 du § C2) |
| `/entreprises` | POST | Crée l'`entreprise` **et** sa première `fiche_version` |
| `/entreprises/{id}/fiches` | POST | Ouvre une nouvelle version (numéro croissant) |
| `/bibliotheque` | GET | État d'avancement, validations, I6, formulaire de relecture |
| `/bibliotheque/{famille}` | GET, POST | Contenu d'une famille + saisie d'un élément |
| `/bibliotheque/validation` | POST | **Verrou humain n° 1** (relecteur nommé + attestation cochée) |
| `/consultations` | GET, POST | Fourniture d'un document + liste des consultations du client |
| `/consultations/{id}` | GET | Analyse, **source sous chaque élément** |
| `/consultations/{id}/elements/{element_id}` | POST | **Verrou humain n° 2** : valider / corriger / supprimer |
| `/consultations/{id}/checklist` | GET, POST | Checklist : `presente` / `manquante` / `a_verifier` + résumé des manques |

---

## 2. Comment lancer (commandes réellement exécutées)

```bash
cd /Users/pause/Projets/ia-consultations-publiques
createdb -h 127.0.0.1 ia_consultations_demo_l5b        # base de démonstration
cd src && DATABASE_URL="postgresql://pause@127.0.0.1:5432/ia_consultations_demo_l5b" \
  CLE_CHIFFREMENT_MAITRESSE="<clé locale, hors dépôt>" \
  CLE_SESSION="<secret local, hors dépôt>" \
  REPERTOIRE_DOCUMENTS="<répertoire hors dépôt>" \
  MODELE_FOURNISSEUR=factice \
  ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8177
```

Puis, dans un navigateur : <http://127.0.0.1:8177/connexion>. **Écoute sur `127.0.0.1`
uniquement**, rien n'est exposé sur Internet, rien n'est déployé. Le serveur de démonstration a
été **arrêté** à la fin du lot (`curl` → code `000`, plus aucun processus).

Provisionnement de la racine (geste d'exploitant, hors API, hors interface) — **le vrai script**
a été déroulé, avec un pty pour la saisie masquée :

```
migrations appliquées — 38 tables
Mot de passe pour 'demo.l5@demo.test' (saisie masquée) :
Confirmez le mot de passe (saisie masquée) :
OK — provisionnement effectué.
  client_id             : 175d43eb-577b-4716-9d6b-1f81690c312d
  utilisateur_id        : 0e1e34b7-50bc-4163-84fa-441493cc0f39
  identifiant_connexion : demo.l5@demo.test
  nom_affichage         : Relecteur Fictif — DÉMONSTRATION
  libelle_client        : Client de démonstration L5 — DÉMONSTRATION
Le mot de passe n'est ni affiché, ni journalisé, ni écrit dans un fichier. Longueur minimale exigée : 12 caractères.
[driver] invites de mot de passe servies : 2
```

Le même script, lancé **sans terminal**, refuse (code de sortie `1`, aucune ligne écrite) :
la saisie masquée est bien la seule entrée possible.

---

## 3. Exigence 1 — l'application démarre et les écrans répondent réellement

Trace `curl` réelle, serveur `uvicorn` sur `127.0.0.1:8177`, jeu fictif :

```
=== Interface web — parcours réel (jeu de démonstration, fictif) ===
2026-09-30 12:17:43 +0400

GET  /connexion (écran de connexion)                          200
GET  /bibliotheque (anonyme → redirection)                   303|http://127.0.0.1:8177/connexion?suivant=/bibliotheque
GET  /static/style.css                                        200
POST /connexion (mauvais mot de passe)                        401
POST /connexion (compte de démonstration)                     303|http://127.0.0.1:8177/bibliotheque
GET  /bibliotheque (1re utilisation, aucun cul-de-sac)        200
POST /entreprises (entreprise + 1re fiche)                    303|.../bibliotheque?ok=entreprise_creee
GET  /bibliotheque (avancement par famille)                   200
GET  /bibliotheque/references_chantiers                       200
POST /bibliotheque/references_chantiers (saisie)              303|.../bibliotheque/references_chantiers?ok=element_enregistre
GET  /bibliotheque/references_chantiers (relu)                200
POST /bibliotheque/validation (attestation NON cochée : refus) 303|.../bibliotheque?erreur=L%27attestation%20...%20ne%20se%20court-circuite%20pas.
POST /bibliotheque/validation (nom + attestation cochée)      303|.../bibliotheque?ok=validation_enregistree
GET  /consultations (écran de fourniture + liste)             200
POST /consultations (DCE fictif déposé)                      303|.../consultations/708afc5d-...?ok=document_analyse
GET  /consultations/{id} (analyse + sources)                   200
POST /consultations/{id}/elements/{e} (valider)                303|.../consultations/708afc5d-...?ok=element_verifie
POST /consultations/{id}/checklist (exécuter)                 303|.../consultations/708afc5d-.../checklist?ok=checklist_executee
GET  /consultations/{id}/checklist (résultat)                 200
```

Extraits réels de contenu renvoyés par le serveur :

```
mention analyse    : brouillon — à relire et à signer
source             : emplacement : page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES »
section            : Résumé des manques
statuts            : 1 etiquette-manquante
mention checklist  : brouillon — à relire et à signer
```

### Captures d'écran (navigateur réel, `Google Chrome`, 1280 px)

Toutes dans `docs/RAPPORTS/captures-L5/` :

| Fichier | Ce qui est visible |
|---|---|
| `01-bibliotheque-avancement.png` | État de la fiche « Relue et validée par humain », tableau d'avancement des 9 familles, boutons visibles : « Fermer la session » seulement |
| `02-famille-references-chantiers.png` | Élément saisi (« source : aucune source — **non vérifiée** »), formulaire de saisie, nomenclature `reference.nature_travaux` annoncée **non chargée (ouverte)** et champ « **Valeur absente de la liste (créer pour cet élément)** » |
| `03-analyse-avec-sources.png` | Mention « brouillon — à relire et à signer », 6 pièces exigées proposées, **Source : document 839f7363…, emplacement : page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES »**, extrait littéral, « Statut de vérification : proposé — non vérifié », boutons « Valider cet élément » / « Enregistrer la correction » / « Marquer comme supprimé » |
| `04-checklist-manques.png` | Résumé (1 exigence, 0 présente, 1 manquante), « 1 pièce(s) exigée(s) sans correspondance dans la bibliothèque : le système ne fabrique aucune pièce », avertissement « Extraction partielle », ligne de checklist avec statut textuel **manquante** et source de l'exigence |

L'écran de connexion a également été ouvert et regardé (capture prise pendant la session de
vérification) : formulaire `Identifiant` / `Mot de passe`, un seul bouton « Ouvrir la session »,
et la note rappelant que le compte est créé par l'exploitant.

---

## 4. Exigence 2 — le parcours complet, exécuté dans le lot

Deux fois : une fois **en HTTP réel** (`curl`, § 3) et une fois par la suite de tests
(`test_parcours_complet_web_de_bout_en_bout`). Les étapes, dans l'ordre de la carte :

1. **Saisie d'un dossier fictif** — écran de première utilisation → `POST /entreprises`
   (entreprise + fiche n° 1) → `POST /bibliotheque/references_chantiers` avec
   « Toiture bâtiment communal fictif — DÉMONSTRATION ».
2. **Validation humaine nommée et horodatée** — `POST /bibliotheque/validation` : attestation
   **non cochée → refus** (l'URL de retour porte le motif) ; nom du relecteur **manquant →
   422** (le champ est exigé par le formulaire lui-même) ; avec nom **et** attestation →
   validation écrite, `relecteur_nom` et `date_validation` posés, fiche « Relue et validée ».
   Le nom du relecteur est vérifié **en base**, pas seulement à l'écran.
3. **Fourniture d'un DCE fictif** — `POST /consultations` avec
   `src/tests/fixtures/dce_fictif.pdf` (fichier signalé « DOCUMENT FICTIF — DÉMONSTRATION »).
4. **Affichage de l'analyse avec sources** — 10 éléments proposés (6 pièces exigées,
   3 critères pondérés, 1 date limite), chacun avec `source_document_id`, `source_emplacement`
   (« page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES » ») et son extrait.
5. **Validation d'un élément** — `POST /consultations/{id}/elements/{id}` avec
   `action=valider` et `verificateur_nom` : `statut_verification = valide`, `verificateur_nom`
   et `date_verification` posés. Sans nom : refus explicite, aucun état validé écrit.
6. **Exécution de la checklist** — `POST /consultations/{id}/checklist` avec `execute_par`
   (obligatoire).
7. **Affichage des manques** — ligne `manquante`, justification, source de l'exigence, résumé
   des manques, avertissement « extraction partielle » (les 9 éléments restés `propose`
   n'alimentent pas la checklist — verrou n° 2).

Preuve que seul l'élément validé alimente la checklist, requête SQL après exécution :

```
nb_exigences = 1   nb_manquantes = 1   extraction_partielle = 1
```

---

## 5. Exigences 3, 4 et 5

**Exigence 3 — la mention « brouillon — à relire et à signer »** apparaît sur toute sortie de
nature à engager l'entreprise : l'analyse (`/consultations/{id}`) et la checklist
(`/consultations/{id}/checklist`). C'est la formulation exacte de l'annexe A § A8 ; elle est
portée aussi par le pied de page de tous les écrans. Vérifié dans les captures et par test
(`MENTION_BROUILLON in réponse`).

**Exigence 4 — aucun bouton engageant, aucun écran acheteur, aucun paiement.** Deux tests :

* un test extrait **tous** les libellés de boutons (`<button>`, `value` de boutons `submit`)
  des 6 écrans rendus et échoue si l'un contient `déposer`, `deposer`, `envoyer`, `signer`,
  `publier` ou `payer` — il vérifie aussi que chaque page contient bien au moins un bouton
  (pour ne pas passer à vide) ;
* le même contrôle est refait **directement sur les 9 gabarits**, y compris ceux non rendus ;
* `/acheteur`, `/paiement`, `/facturation`, `/inscription` répondent `404`.

Le verbe « déposer » n'apparaît donc nulle part dans un bouton : le formulaire de DCE est
libellé « **Analyser ce document** », et la fourniture du pli reste hors périmètre.

**Exigence 5 — un client ne peut pas atteindre les données d'un autre.** Test dédié: le client
B, connecté, reçoit `404` (jamais `403`) sur la consultation de A, sur sa checklist et sur
l'action de vérification d'un élément de A ; l'écran de bibliothèque de B n'affiche aucune
donnée de A ; et la base confirme qu'aucune ligne n'a été écrite ni modifiée chez B.

---

## 6. Décisions non couvertes par les annexes (commentées sur la carte, pas tranchées en silence)

### 6.1 Créer une valeur de référence manquante : sur l'élément, jamais dans la nomenclature globale

Le lot doit permettre de « créer une valeur de référence manquante **sans quitter le
formulaire** » (D2). Aucune couche ne fournit d'écriture vers `valeur_reference`
(`DepotReference` est explicitement *« accès en lecture »*, tables **globales**, I5).

Décision retenue et appliquée :

* le formulaire d'une famille affiche, pour chaque champ `code_reference`, les valeurs du jeu
  **s'il est chargé** (nomenclature fermée : seules ces valeurs sont acceptées), et **annonce
  l'ouverture** du jeu s'il ne l'est pas ;
* un champ « **Valeur absente de la liste (créer pour cet élément)** » permet de saisir la
  valeur manquante **sans quitter le formulaire** ; le service l'accepte alors que le jeu n'est
  pas chargé, et la valeur reste portée par l'élément, marquée à vérifier ;
* **rien n'est écrit dans `valeur_reference`** : une écriture dans une table globale depuis une
  session d'entreprise croiserait les locataires (I5), et une nomenclature **par client** est
  explicitement *réservée, non utilisée au MVP* (`docs/DATA-MODEL-V2.md` § 8.4). Le test
  correspondant vérifie en base qu'**aucune** ligne n'est ajoutée à la nomenclature globale ;
* sur une nomenclature **fermée**, une valeur hors jeu est **refusée avec son motif** (test
  dédié), ce qui est le comportement correct d'un jeu de référence fermé.

Si `plan` veut une extension **persistée** des nomenclatures, c'est une décision de contrat
(ajout de route à l'annexe C) qui ne m'appartient pas.

### 6.2 Un dépôt de lecture pour lister les consultations

Aucune route de l'annexe C ne liste les `consultation`. Sans listing, l'écran `/consultations`
serait un cul-de-sac (une consultation déposée ne serait atteignable que par son URL). Le web ne
contient aucun SQL (annexe A § A3). J'ai donc ajouté `src/app/storage/depot_consultations.py`,
**lecture seule**, filtré par le `client_id` du contexte. Aucune route, aucun contrat modifié.

### 6.3 Écran anonyme : redirection (303) plutôt que 401

Les routes JSON répondent `401` sans session (contrat gelé, inchangé). Les écrans HTML, eux,
redirigent en `303` vers `/connexion?suivant=…` : c'est le comportement attendu d'un navigateur,
et cela ne divulgue rien. L'API garde son `401`.

### 6.4 Autres points

* les `POST` de formulaire sont posés **sur les chemins d'écran déjà gelés** (`/bibliotheque/{famille}`,
  `/consultations/{id}/checklist`…) plus `/entreprises` et `/entreprises/{id}/fiches` ; aucune
  route `/api/v1` n'est touchée ;
* les captures d'écran sont versionnées dans `docs/RAPPORTS/captures-L5/` (elles ne montrent que
  le jeu fictif) ;
* en cas de refus de saisie, l'écran revient avec le **motif** dans l'URL (`?erreur=…`) : les
  valeurs déjà saisies ne sont pas recollées dans le formulaire (limite connue de l'interface
  minimale sans JavaScript).

---

## 7. Défauts constatés hors lot (non corrigés : ce n'est pas mon périmètre)

1. **`src/tests/conftest.py` — base de test partagée (hotspot déjà signalé par L4 et L2bis).**
   La fixture de session fait `down(999)`/`up()` sur **une seule** base
   `ia_consultations_test`. Pendant mon lot, le worker du lot **L8 (`qa`)** écrivait
   `src/tests/integration/` et lançait la suite en parallèle : ma première exécution complète a
   produit `10 failed, 60 errors` (`relation "client" does not exist`,
   `invalid input syntax for type uuid: "pièce fictive — DÉMONSTRATION"`) — **c'est une
   collision entre deux lots, pas un défaut de L5**. Contournement utilisé ici : une base dédiée
   par lot via `TEST_DATABASE_URL`. À traiter avant d'ouvrir d'autres lots parallèles.
2. **SQL hors de `storage/`** dans `services/checklist.py`, `services/analyse_dce.py`,
   `services/authentification.py` (signalé par L2, toujours ouvert, règle R9). Je n'en ai ajouté
   aucun : mes écrans n'écrivent pas de SQL, et le seul SQL neuf est dans `storage/`.
3. **`src/app/main.py`** est un point de collision (5e lot consécutif à y ajouter quelque
   chose) ; mon apport est de 11 lignes, isolées en un bloc commenté.
4. La base de démonstration `ia_consultations_demo_l5b` reste présente sur l'instance locale
   (`Postgres.app`), avec **uniquement** des données fictives ; le serveur, lui, est arrêté.
   Sa suppression est un geste d'exploitant.

---

## 8. Ce qui n'a pas été fait, et ce qui n'est pas prouvé

* Le **fournisseur de modèle réel** (France/UE) n'est pas testé — aucune clé d'API. Les écrans
  affichent le fournisseur employé et, quand c'est `factice`, disent explicitement qu'il ne
  « comprend » rien et qu'aucun appel réseau n'a lieu. L'analyse ci-dessus vient donc du
  fournisseur **factice**.
* Pas d'OCR exercé dans ce lot : le DCE fictif employé est un PDF natif. Le chemin OCR a été
  exercé par L3, pas par L5.
* **Pas de JavaScript** : pas d'auto-enregistrement, pas de recollage des valeurs après un
  refus, pas de filtre de formulaire côté client. C'est une conséquence assumée de l'annexe A § A8.
* L'écran E4 « dépôt d'un justificatif » de la maquette `docs/UI-SAISIE.md` n'a pas d'écran
  dédié : l'entité `document` existe, mais aucune route de l'annexe C ne dépose une pièce de
  bibliothèque. Seul le DCE (pièce de nature `dce`) est déposable. Signalé, non improvisé.
* Les rôles, l'inscription, la réinitialisation de mot de passe, le multi-utilisateur restent
  hors périmètre (§ C2) : aucun écran ne les expose.
* **Aucun commit git** (cohérent avec les lots précédents) ; aucun déploiement, aucun port exposé.

---

## 9. Tests — sorties réelles

```
$ cd src && ../.venv/bin/python -m pytest tests/test_web.py -q
14 passed, 1 warning in 1.66s
```

```
$ cd src && TEST_DATABASE_URL="postgresql://pause@127.0.0.1:5432/ia_consultations_l5_test" \
    ../.venv/bin/python -m pytest -q --ignore=tests/integration
144 passed, 1 warning in 8.97s          # 130 avant ce lot + 14 nouveaux
```

```
$ cd src && TEST_DATABASE_URL="…/ia_consultations_l5_test" ../.venv/bin/python -m pytest -q
1 failed, 146 passed in 9.19s
# le seul échec est tests/integration/test_isolation.py — fichier du lot L8 (qa),
# en cours d'écriture pendant ce lot (collision de base partagée, voir § 7.1)
```

Les 14 tests de `src/tests/test_web.py` couvrent : les écrans et leurs codes HTTP ; la connexion
refusée ; la première utilisation et la création d'entreprise + première fiche (+ numérotation
croissante des versions) ; la saisie d'un élément ; **la création d'une valeur de référence
manquante** (nomenclature ouverte) et son **refus** sur une nomenclature fermée ; la saisie sans
`origine` refusée ; **les trois cas du verrou humain n° 1** (nom manquant → 422, attestation non
cochée → refus sans écriture, nom + attestation → validation datée en base) et la **révocation**
après écriture ; le **parcours complet** de bout en bout avec vérifications SQL ; l'**isolation**
entre deux clients ; l'**absence de bouton engageant** ; et l'absence d'écran acheteur/paiement.

---

## 10. Conclusion

L'interface web minimale est **exécutable et vérifiée par exécution réelle** : serveur local,
parcours complet en HTTP, captures d'écran à l'appui, 14 tests verts, 144 tests verts pour la
suite hors lot L8. Les deux verrous humains sont distincts et non court-circuitables, aucune
sortie engageante n'omet la mention « brouillon — à relire et à signer », aucun bouton
« déposer », « envoyer » ou « signer » n'existe, et un client ne peut pas atteindre les données
d'un autre. Les quatre décisions non couvertes par les annexes sont documentées ci-dessus et en
commentaire de carte (`t_2cfef350`) ; elles n'ont pas été tranchées en silence.
