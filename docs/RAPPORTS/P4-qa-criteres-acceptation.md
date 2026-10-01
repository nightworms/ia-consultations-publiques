# P4 — Vérification indépendante des critères d'acceptation de la phase 4

*Lot **L8**, agent `qa`, 30 septembre 2026. Tout ce qui suit a été **exécuté** : serveur
réel, base migrée, jeu de démonstration du lot L7 chargé, écran par écran. Aucun constat
de ce rapport ne vient de la lecture du code seul ; les lignes de code citées ne servent
qu'à expliquer une observation faite à l'écran ou en base.*

Captures et sorties brutes : `docs/RAPPORTS/captures-P4/` (28 captures d'écran + 12
fichiers de preuve). Rapports des prédécesseurs lus : `L5a-refonte-ecrans.md`,
`L5b-ecrans-memoire-import.md`, plus les comptes rendus des lots L2, L3, L6, L7.

---

## 0. Verdict en une ligne

| Critère du § 1 du plan | Verdict |
|---|---|
| 1 — écran d'accueil après connexion, action évidente | **conforme** |
| 2 — création d'entreprise + import de 2-3 documents → propositions à valider | **non conforme** |
| 3 — dépôt du DCE : pièces, critères pondérés, date limite, chacun avec sa source | **conforme** |
| 4 — mémoire structuré sur les critères, arguments rattachés, manques listés avec l'action | **non conforme** |
| 5 — export réellement ouvert et relu | **conforme** |
| 6 — aucun écran sans valeur technique, jargon ni identifiant interne | **non conforme** (défauts ciblés, corrigeables) |
| Non-régression : les tests de la phase 3 restent verts | **conforme** (244 verts) |

**La phase 4 n'est pas terminée** : deux critères sur six ne sont pas tenus, et le
critère 4 l'est au prix de la règle centrale de la phase (§ 2.B du plan) — le mémoire
affirme une expérience que la bibliothèque ne contient pas, et ne signale pas le manque
que le jeu L7 a construit exprès. Deux cartes de correction bloquantes ont été créées
(§ 6), plus une carte de conformité pour le critère 6.

---

## 1. Ce qui a réellement été exécuté, et comment

### Base de vérification

Une base **neuve**, dédiée à cette vérification (la base `ia_consultations_verif` de
l'exploitant contient les restes des lots précédents ; je ne l'ai pas touchée) :

```bash
createdb ia_consultations_qa_l8
cd src && DATABASE_URL=…qa_l8 bin/python -m app.storage.migrations up
#   → Migrations appliquées : 0001, 0002, 0003, 0004, 0005, 0006
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0002_jeu_demo_phase4.sql
#   → jeu L7 : 1 client, 1 utilisateur, 1 entreprise, 9 familles, 4 références,
#     2 assurances, 2 certifications, 4 effectifs, 4 moyens matériels,
#     2 produits, 2 chapitres, 6 documents, consultation = 0 (attendu)
.venv/bin/python scripts/jeu-de-test/completer_demo_phase4.py
#   → champs chiffrés, empreinte Argon2id, 6 pièces chiffrées sous verif-data/clients/<client_id>/
```

Compte de démonstration : `demo@exemple.invalid` (mot de passe fictif posé par le
chargeur, haché en Argon2id ; **saisi sans tty** par un lanceur qui remplace
`getpass.getpass`, le mot de passe n'apparaissant ni en argument ni dans un fichier
versionné).

### Serveur

1. `bash demarrer.sh` **tel quel**, avec le `.env` de l'exploitant : le script démarre
   (log intégral dans `captures-P4/demarrer-sh-as-delivered.log`), applique les
   migrations, écoute sur `127.0.0.1:8099`. Un serveur résiduel d'une exécution
   précédente occupait le port : je l'ai arrêté (pid identifié par `lsof`) avant de
   relancer, sinon `demarrer.sh` répond « L'APPLICATION TOURNE DÉJÀ » — comportement
   correct et vérifié.
2. Le parcours complet a été déroulé sur la base neuve ci-dessus, avec les **mêmes**
   variables d'environnement mais `MODELE_FOURNISSEUR=factice` (lecture hors ligne —
   voir le défaut n° 4 : le `.env` livré pointe un fournisseur hors UE, je n'ai pas
   voulu envoyer de document à un tiers, même fictif). Serveur lancé par la commande
   exacte que `demarrer.sh` exécute en fin de script
   (`python -m uvicorn app.main:app --host 127.0.0.1 --port 8099`). Journal des appels :
   `captures-P4/journal-appels-http.txt`.
3. Le `.env` de l'exploitant **n'a pas été modifié** : l'écriture d'un fichier
   d'environnement de projet est bloquée par le garde-fou de l'outil. Les variables de
   la vérification ont donc vécu dans une copie, hors du dépôt.

### Connexion pour les captures

Le mot de passe de démonstration n'a **jamais** été tapé dans le navigateur (règle de
l'outil) : la session a été ouverte par un POST HTTP hors navigateur, et le cookie signé
posé dans le navigateur par CDP (`Network.setCookie`). Les captures montrent donc des
pages authentifiées réelles, obtenues par le chemin de connexion réel.

### Environnement observé

macOS, Python 3.12 (`.venv` du projet), PostgreSQL 16 (Postgres.app, `127.0.0.1:5432`),
`python-docx 1.2.0` installé. Aucune dépendance nouvelle ajoutée par cette vérification.

---

## 2. Critère par critère

### Critère 1 — CONFORME

**Fait** : ouverture de `/connexion`, POST réel avec `demo@exemple.invalid`, puis
navigation sur chaque page. Captures : `01-connexion-deconnectee-desktop.png`,
`01b-connexion-mobile.png`, `02-accueil-mobile.png`.

**Vu** :

- `POST /connexion` → **303 `Location: /accueil`** avec cookie de session posé ;
  `GET /connexion` avec session → 303 vers `/accueil` ; mauvais mot de passe → **401**
  avec message générique (« Identifiant ou mot de passe incorrect. », sans dire si
  l'identifiant existe) ; sans session, `/accueil`, `/bibliotheque`, `/consultations`,
  `/bibliotheque/import` → 303 vers `/connexion?suivant=…` (jamais de 403 ni de 500).
- L'écran d'accueil dit ce que la plateforme apporte — « **Répondez à une consultation
  publique sans repartir de zéro** — Déposez le dossier de consultation : nous en sortons
  les pièces exigées, les critères notés et la date limite… » — avec **une seule action
  principale** (« Déposer un dossier de consultation »), plus un bloc « Où vous en êtes »
  en trois étapes (entreprise déclarée / bibliothèque renseignée / mémoire à démarrer)
  en vocabulaire métier.

**Verdict : conforme.** C'est le point que L7 laissait ouvert (la redirection pointait
encore `/bibliotheque` au 30/09) : L5a l'a bien fermé.

---

### Critère 2 — NON CONFORME

**Fait** : création d'une entreprise et de sa première fiche depuis l'écran
(`/entreprises/nouvelle` → POST `/entreprises`), puis import de **trois** documents
existants du jeu L7 par l'écran `/bibliotheque/import` (dépôt réel du fichier via
`DOM.setFileInputFiles`, soumission du formulaire réel).

**Vu — la création marche :** POST `/entreprises` → 303
`/bibliotheque?ok=entreprise_creee`, message « Entreprise créée avec sa première version
de fiche (aucune donnée déduite : le libellé vient de la saisie) », et l'écran bibliothèque
affiche les neuf familles vides avec, pour chacune, ce qui manque et l'action à mener.
Captures `24-premiere-utilisation-desktop.png`, `25-bibliotheque-nouvelle-entreprise-desktop.png`.

**Vu — l'import ne produit rien :**

| Document déposé (jeu L7) | Famille choisie | HTTP | Propositions créées |
|---|---|---|---|
| `plaquette-presentation-FICTIF.txt` | `references_chantiers` | 303 | **0** |
| `memoire-technique-anterieur-FICTIF.txt` | `memoire_technique` | 303 | **0** |
| `attestation-assurance-RCD-FICTIF.txt` | `assurances` | 303 | **0** |

L'écran affiche « Document lu. Chaque proposition porte le passage exact dont elle vient ;
rien n'entre dans votre bibliothèque sans votre décision. » puis **aucun bloc de décision** :
aucun élément à valider, aucun bouton accepter/refuser. En base :
`import_document.statut = 'traite'`, `SELECT count(*) FROM import_proposition` = **0**.
Captures `09-import-propositions-desktop.png`, `09b-import-propositions-desktop.png`.

La bibliothèque se remplit donc **uniquement par saisie champ par champ** — exactement ce
que le critère interdit.

**Contre-épreuve faite pour ne pas accuser à tort** : le mécanisme d'import fonctionne
quand le document est écrit dans le micro-format que le lecteur de démonstration attend
(`Entité : assurance` puis `- type_assurance : responsabilite_civile_decennale`,
`- assureur : …`, `- date_debut : …`, `- date_echeance : …`) → **1 proposition**, affichée
avec sa source (« Tirée de : doc-format-attendu-FICTIF.txt, page 1 — entité « Contrat
d'assurance » ») et son passage littéral, décidable avec un nom obligatoire. Acceptée →
élément écrit en bibliothèque avec « Origine : extraite d'un document que vous avez
fourni », « Source : document que vous avez fourni », statut « À vérifier ». Captures
`10-import-proposition-desktop.png`, `11-famille-assurances-apres-import-desktop.png`.

**Cause identifiée** : `src/app/services/fournisseur_modele/fournisseur_factice.py:63-69`
(`_MOTIF_ENTITE_IMPORT`, `_MOTIF_CHAMP_IMPORT`) et `_lire_import_page` (`:171-210`) : le
lecteur ne reconnaît que `entité : <identifiant_snake_case>` suivi de `- champ : valeur`.
Les documents du jeu L7 (`scripts/jeu-de-test/fictif/*.txt`) sont rédigés en français
métier (« Raison sociale : OCÉAN ÉTANCHÉITÉ (FICTIF) », « Qualification « étanchéité de
toitures-terrasses » — organisme certificateur FICTIF O.C.F.E. … ») : aucun n'est dans ce
format. Les tests du lot L3 (`src/tests/test_import_guide.py:117-131`) utilisent une
fixture écrite dans le micro-format — ils passent sans couvrir le cas réel.

**Verdict : non conforme.** Carte de correction bloquante **`t_43088781`** (`dev-back`).

---

### Critère 3 — CONFORME

**Fait** : dépôt du DCE fictif (`scripts/jeu-de-test/fictif/DCE-FICTIF-DEMO-2026-ETN-001.txt`)
par le formulaire réel de `/consultations`, avec libellé, référence, maître d'ouvrage
déclarés à la main (rien n'est déduit du document). Captures
`12-consultations-avant-depot-desktop.png`, `13-consultation-analyse-desktop.png`,
`14-consultation-criteres-ponderes-desktop.png`, `05-consultation-analyse-mobile.png`.

**Vu**, sur la consultation `d12e36e9-c447-4929-a0eb-8e16ef9215f0` :

- **15 éléments lus, 0 catégorie non trouvée** : 8 pièces exigées, 6 critères, 1 date limite ;
- **chaque élément porte sa source** (`source_emplacement` non vide **et** `source_extrait`
  non nul pour 15/15 — vérifié en SQL), par exemple :
  - critère : `Étanchéité de toitures-terrasses sur bâtiments scolaires` / `40 %` /
    source `page 1 — section « ARTICLE 5 — CRITÈRES D'ATTRIBUTION »` / extrait littéral
    `- Étanchéité de toitures-terrasses sur bâtiments scolaires : 40 %` ;
  - date limite : `2026-12-12` / source `page 1 — section « ARTICLE 6 — DATE LIMITE DE
    REMISE DES OFFRES »` / extrait « Date limite de remise des offres : 12 décembre 2026
    à 12 h 00 (heure locale). » ;
- les six critères pondérés sont affichés dans l'ordre décroissant (40, 20, 15, 10, 10, 5 %) ;
- **rien n'est un fait avant validation humaine** : les 15 éléments sont `propose` ; la
  validation nominative les fait passer à `valide` (6 critères, 1 date, 8 pièces) —
  contrôlé en base avant/après (`captures-P4/verif-dce-et-checklist.txt`) ;
- après validation, la vérification du dossier donne **4 présentes / 3 à vérifier /
  1 manquante**, la manquante étant « Liste des moyens matériels affectés au marché » avec
  le motif « Aucune pièce correspondante dans la bibliothèque de la fiche utilisée : le
  système ne fabrique pas la pièce manquante. » (captures `16-checklist-desktop.png`,
  `16b-checklist-piece-par-piece-desktop.png`, `07-checklist-mobile.png`) ;
- la page porte l'avertissement « Checklist — outil d'aide à la relecture, pas un
  certificat de conformité. Aucune conformité n'est garantie. »

**Verdict : conforme.**

---

### Critère 4 — NON CONFORME

**Fait** : génération du mémoire depuis la consultation (`POST
/consultations/{id}/memoire`), lecture de l'écran, contrôle en base, puis export du
mémoire validé et relecture du fichier.

**Vu :**

- le plan suit bien l'ordre de pondération, et le critère lourd reçoit le développement le
  plus long (40 % → 5 115 caractères, 20 % → 3 701, 15 % → 2 390, 10 % → 1 823, 10 % →
  1 423, 5 % → 1 687) ;
- **mais 6 sections pour 6 critères et `SELECT count(*) FROM memoire_manque` = 0** : aucun
  manque n'est signalé, et l'écran l'écrit noir sur blanc : « **0 critère sans référence
  dans votre bibliothèque** » (`20-memoire-valide-desktop.png`) ;
- la section du critère — pourtant construit par le lot L7 comme **le manque volontaire
  principal** — est produite :

  > **« Expérience en toitures-terrasses végétalisées » — 10 %**
  > « Éléments de votre bibliothèque mobilisés : 6 (familles : Références de chantiers,
  > Certifications et qualifications). Chaque phrase ci-dessous renvoie à un élément réel
  > et vérifiable… »

  avec 4 références de chantiers d'étanchéité **ordinaires** et 2 certifications, dont
  **aucune ne porte le mot « végétalisé »** :
  `SELECT count(*) … ILIKE '%végétalis%'` → **0** (captures
  `21-memoire-section-vegetalisees-desktop.png`, `22-memoire-references-techniques-ouvertes-desktop.png`) ;
- le fichier exporté aggrave l'affirmation :

  > `## Manques à traiter`
  > « **Aucun manque signalé : tous les critères du DCE sont étayés par un élément réel de
  > votre bibliothèque.** » (`captures-P4/export-qa-l8.md`, lignes 217-219)

**C'est la violation de la règle centrale de la phase.** Toute phrase est bien adossée à
un élément *existant*, mais l'élément cité ne prouve pas le critère : l'affirmation
« nous avons l'expérience des toitures végétalisées » n'est rattachable à rien, et la
phrase « Aucun manque signalé » est fausse. Le critère 4 exige précisément l'inverse :
« les manques sont listés avec l'action à mener ».

**Contre-épreuve** : sur une entreprise à fiche vide, le même parcours donne **0 section et
6 manques** correctement rédigés (constat + action, ex. « Ajouter un chantier comparable
(nature de travaux, maître d'ouvrage, montant € HT, année de réception, difficulté
traitée). »), capture `26-memoire-manques-bibliotheque-vide-desktop.png`. Le mécanisme
existe donc, mais il ne se déclenche que si la bibliothèque est **entièrement** vide.

**Cause identifiée** : `src/app/domain/memoire_technique_genere.py:255-273`,
`familles_pour_critere()` : tout libellé non reconnu retombe sur `FAMILLES_DEFAUT`
(`:198-204`, six familles). Dès qu'une de ces familles contient un élément, la section est
produite ; le lien entre le **sujet** du critère et le contenu des éléments n'est jamais
vérifié — seul le nombre de sources compte.

**Verdict : non conforme.** Carte de correction bloquante **`t_21fffbbc`** (`dev-back`).

---

### Critère 5 — CONFORME

**Fait** : tentative d'export **avant** validation, puis relecture nommée des six
sections, validation nommée et horodatée du mémoire, puis export `.md` et `.docx`,
téléchargés et **réellement ouverts**.

**Vu :**

- **avant validation** : `GET /consultations/{id}/memoire/export?format=md|docx` →
  **HTTP 409**, corps en français et non technique : « Le mémoire doit d'abord être relu et
  validé par une personne nommée. Rien ne sort sans relecture humaine : c'est la règle du
  produit. Pour débloquer le téléchargement : ouvrez le mémoire, relisez chaque section
  (une section passe de « à relire » à « relue »), puis validez le mémoire en indiquant
  votre nom et votre fonction… » (capture
  `27-export-refuse-sans-validation-desktop.png` ; au passage, l'écran affiche cette page
  en texte brut, ce qui est cohérent avec le message) ;
- validation du mémoire alors que 5 sections sont encore en brouillon → refusée
  (303 avec erreur « 5 section(s) encore en brouillon : relisez chaque section avant de
  valider le mémoire »), dossier laissé en `en_relecture`, **0** ligne
  `memoire_validation` ;
- après relecture des 6 sections et validation nominative : dossier `valide`, ligne
  `memoire_validation` écrite (nom, fonction, horodatage `2026-09-30 19:49 +04`) ;
- **export `.md`** : HTTP 200, 29 610 octets, `Content-Disposition: attachment;
  filename="memoire-technique-fictif-refection-etancheite-toitures-terra.docx|.md"`
  (nom tiré du titre métier, **sans UUID**), en-tête `X-Empreinte-Contenu` égal à
  l'empreinte enregistrée ;
- **export `.docx`** : HTTP 200, 40 068 octets, même empreinte ;
- format inconnu (`format=pdf`) → **400** « Format d'export inconnu : 'pdf'. Formats
  admis : md, docx (Markdown = format canonique). »

**Ouverture réelle des deux fichiers** (`captures-P4/verif-ouverture-des-exports.txt`) :

- `export-qa-l8.docx` **ouvert avec python-docx** : **183 paragraphes** non vides, 0 tableau,
  premier paragraphe = titre du mémoire, puis le bloc « Relecture et validation humaine »
  (nom, fonction, date, empreinte SHA-256) ;
- `export-qa-l8.md` lu : 27 638 caractères, 220 lignes, structure `## 1. … ## 6.` dans
  l'ordre des pondérations, plus la section `## Manques à traiter` (vide ici — voir le
  critère 4) ;
- les deux fichiers sont déposés dans `captures-P4/` pour relecture humaine.

**Verdict : conforme** (le défaut constaté dans l'export — « Aucun manque signalé » —
appartient au critère 4, pas à l'export lui-même).

---

### Critère 6 — NON CONFORME

**Méthode** : balayage automatique de **18 écrans** (avec et sans session) : le texte
visible est extrait, les blocs repliés `Références techniques` sont isolés à part, et le
résultat est confronté à neuf familles de motifs (UUID, empreinte SHA-256, code entre
crochets, nom de table/colonne, code d'état interne, chemin d'API, jargon, référence
interne, identifiant à underscores). Sortie brute :
`captures-P4/verif-critere6-jetons-techniques.txt` (75 constats). Toutes les captures de ce
rapport ont été regardées.

**Ce qui est propre** (à ne pas casser) : aucun UUID, aucune empreinte et aucun nom de
table dans le texte visible de `/connexion`, `/accueil`, `/bibliotheque`,
`/bibliotheque/{les 9 familles}`, `/consultations`, `/consultations/{id}`,
`/consultations/{id}/memoire`, `/entreprises/nouvelle`. Le vocabulaire métier est
correctement traduit à l'écran (« Prête », « À compléter », « À vérifier », « Manquante »,
« Relue », « Validé », « Déclaré, non vérifié »). Aucun débordement horizontal en 390 px.

**Ce qui ne va pas :**

1. **Codes internes affichés en clair, hors de tout bloc replié** — le défaut le plus net.
   Texte exact lu à l'écran sur `/consultations/{id}/checklist`
   (`16b-checklist-piece-par-piece-desktop.png`) :

   > « Pièce de la bibliothèque retenue : Attestation d'assurance responsabilité civile
   > décennale **[attestation_assurance_decennale]**. »
   > « Pièce présente (Certificat de qualification professionnelle de l'entreprise —
   > domaine étanchéité **[certificat_qualification]**) mais échéance dépassée le 2026-09-15… »

   Six codes relevés dans le texte visible : `[attestation_assurance_decennale]`,
   `[attestation_assurance_professionnelle]`, `[attestation_bonne_execution]`,
   `[certificat_qualification]`, `[fiche_technique_produit]`, `[references_chantiers]`
   (plus `[expire]`, `[valide]` dans un bloc replié). Origine :
   `src/app/services/checklist.py:318` (`_decrire_document` → `f"{libelle} [{type_document}]"`),
   rendu par `checklist.html:86`.

2. **Valeurs de nomenclature brutes** : « Type d'assurance :
   **responsabilite_civile_decennale** » (`11-famille-assurances-apres-import-desktop.png`),
   également `travaux_en_hauteur`, `etancheite_toiture_terrasse`,
   `materiel_mise_en_oeuvre` (écran famille et écran mémoire). Défaut cosmétique, mais
   c'est bien une valeur technique à l'écran.

3. **Blocs « Références techniques »** présents sur **six** écrans et contenant, en clair,
   des identifiants internes. Textes exacts, blocs ouverts :
   - analyse du dossier : « Dossier `d12e36e9-c447-4929-a0eb-8e16ef9215f0` — statut
     `analysee`. » + « empreinte SHA-256 `ca46cf7b…f101` »
     (`15-…-references-techniques-ouvertes-desktop.png`) ;
   - import guidé : « Famille de destination : `references_chantiers, certifications,
     assurances, moyens_humains, moyens_materiels, fiches_produits, capacites_financieres,
     memoire_technique`. » + « Proposition en cours de décision : `<uuid>` »
     (`23-…-references-techniques-ouvertes-desktop.png`) ;
   - mémoire : UUID de sections, entités (`moyen_materiel`, `reference_chantier`,
     `effectif_metier`, `organigramme`), codes `[expire]`, `[valide]`
     (`22-…-references-techniques-ouvertes-desktop.png`) ;
   - également sur bibliothèque, famille, dépôt, checklist et page d'erreur.

   Ce point est **une décision assumée du lot L5a** (identifiants « repliés ») : il ne
   s'invente pas, il se tranche. Le contenu reste affichable par n'importe quel
   utilisateur, donc le critère 6 tel qu'écrit n'est pas satisfait, mais la correction
   peut aussi bien être « supprimer le bloc et journaliser côté serveur » que
   « reformuler le critère dans `docs/DECISIONS.md` ». Je ne tranche pas à la place de
   l'orchestrateur : c'est écrit dans la carte `t_ebbaac86`.

4. Mineur : une adresse inexistante renvoie le JSON par défaut de FastAPI
   (`{"detail":"Not Found"}`, capture `19-page-erreur-desktop.png`) au lieu de la page
   d'erreur du produit.

**Verdict : non conforme.** Carte de conformité **`t_ebbaac86`** (`dev-web`).

---

## 3. Les contrôles de méthode imposés (points 4 à 9)

### 4. Non-régression — CONFORME

```
$ cd src && ../.venv/bin/python -m pytest -q
244 passed, 1 warning in 17.16s          # captures-P4/pytest-suite-complete.txt
```

- Corpus de la phase 3 : **189 tests collectés** aujourd'hui, tous verts. Le décompte est
  vérifiable : 244 (suite complète) − 55 (fichiers de tests créés par la phase 4 :
  `test_memoire_technique` 15, `test_import_guide` 15, `test_export_memoire` 15,
  `integration/test_memoire_ligne_rouge` 10) = **189**. Sur ces 189, **4 ont été ajoutés
  par L5a/L5b à `test_web.py`** (14 tests à la fin de la phase 3, 18 aujourd'hui : comptage
  des `def test_` dans le fichier au commit `aa95138` puis maintenant). Donc **185 tests
  existaient avant la phase 4 et sont tous verts** — aucun test supprimé, seules des
  additions (`captures-P4/pytest-phase-3-ordre-naturel.txt`, 181 collected pour le
  sous-ensemble rejoué hors filtres).
- Nouveaux tests de la phase 4 : 55 collectés (`test_memoire_technique` 15,
  `test_import_guide` 15, `test_export_memoire` 15, `integration/test_memoire_ligne_rouge`
  10) ; 189 + 55 = 244, cohérent.
- **Point signalé, sans en faire un défaut produit** : le test d'invariants
  `test_invariants_i1_a_i8_par_comptage` **échoue** si l'on force un ordre de fichiers
  inhabituel (les tests unitaires avant `tests/integration/`) : il compte l'invariant I6
  sur l'ensemble de la base de test, et un état laissé par un autre fichier le fait
  dévier de 1. Preuve : `captures-P4/pytest-phase-3-ordre-impose-echec-I6.txt`
  (`1 failed, 180 passed`) contre `…ordre-naturel.txt` (`181 passed`). L'invocation
  documentée (`pytest -q`) passe : ce n'est pas une régression du produit, mais le test
  n'est pas indépendant de l'ordre — à corriger si la suite doit être découpée.
- `git status` : **aucun fichier de `docs/Model de dossier de consultation/` n'est suivi
  ni réintégré** (`git status --porcelain --ignored=matching docs/` → `!! "docs/Model de
  dossier de consultation/"`, `git ls-files docs/ | grep -c consultation/` → 0). D10
  respectée.

### 5. Migrations 0005 et 0006, `up` / `down` / `up` — CONFORME

Sur une **copie** de la base de démonstration (pour ne pas détruire l'état du parcours) :

```
=== ETAT INITIAL ===         0001..0006 appliquée ; tables memoire_/import_ : 7
                              donnes : client=2 entreprise=2 reference=5 document=13
                                       assurance=3 certification=2 consultation=2
=== DOWN 2 ===               Migrations annulées : 0006, 0005
                             0005 en attente, 0006 en attente
                             tables memoire_/import_ restantes : 0
                             donnes : client=2 entreprise=2 reference=5 document=13
                                      assurance=3 certification=2 consultation=2
=== UP ===                   Migrations appliquées : 0005, 0006 ; tables : 7
                             donnes : identiques
=== DOWN puis UP a nouveau   identique
```

Sorties brutes : `captures-P4/verif-migrations-up-down-up.txt` et
`captures-P4/verif-donnees-demo-pendant-down.txt`. Les deux migrations sont
**réversibles** et **les données du jeu de démonstration survivent** à un cycle complet
(elles ne dépendent d'aucune des deux tables annulées). Les mémoires et les imports, eux,
disparaissent avec le `down` — c'est le sens d'un `down`, et le jeu L7 ne sème
volontairement aucun mémoire.

### 6. Isolation par client — CONFORME

Un second locataire fictif (« client B », UUID `b0000000-…`) a été créé uniquement pour
cette vérification, avec sa propre entreprise, sa fiche, un élément de bibliothèque, un
document, un import et une consultation portant un libellé reconnaissable
(« FICTIF — chantier confidentiel du client B »). Puis le client **A** (démonstration) a
tenté d'y accéder :

| Tentative de A | Réponse | Donnée de B affichée |
|---|---|---|
| `GET /api/v1/import/documents/{import de B}` | **404** | non |
| `GET /api/v1/consultations/{consultation de B}` | **404** | non |
| `GET /api/v1/consultations/{…}/memoire` (mémoire de B) | **404** | non |
| `GET /consultations/{…}/memoire` (écran de B) | **404** | non |
| `GET /consultations/{…}/memoire/export?format=md` (export de B) | **404** | non |
| `GET /consultations/{…}/checklist` (checklist de B) | **404** | non |
| `GET /consultations/{…}` (analyse de B) | **404** | non |
| `POST /api/v1/bibliotheque/references_chantiers` avec l'`element_id` **de B** | **400** « Élément introuvable pour ce client : 'b0000000-…' (lecture refusée). » | non |
| `GET /api/v1/bibliotheque` et `/api/v1/bibliotheque/{famille}` de A | 200, **le libellé de B n'apparaît pas** | non |
| `POST /api/v1/memoire/sections/{section inconnue}` | **404** | non |

Après la tentative d'écriture, la ligne de B est **inchangée** en base et aucune ligne
n'a été créée côté A. Aucune réponse ne prend la forme 403 (pas d'aveu d'existence) ni 500.
Sortie brute : `captures-P4/verif-isolation-entre-clients.txt`.

### 7. Manques volontaires du jeu L7 — NON CONFORME (voir critère 4)

Le jeu L7 prévoit deux manques : le **critère** « Expérience en toitures-terrasses
végétalisées » (10 %, aucune référence ne le couvre) et la **pièce exigée** « Liste des
moyens matériels affectés au marché ».

- Pièce exigée : **le manque est bien signalé** — la vérification du dossier la donne
  « Manquante » avec « Aucune pièce correspondante dans la bibliothèque… le système ne
  fabrique pas la pièce manquante. »
- Critère : **le manque n'est pas signalé**. Le mémoire produit une section étayée par des
  chantiers qui ne sont pas végétalisés, et la page affirme « 0 critère sans référence »
  puis « Aucun manque signalé ». Aucun paragraphe n'a été inventé au sens littéral (tout
  est copié d'éléments réels), mais **une affirmation non rattachable au critère a été
  produite**, ce qui est l'interdit de la phase.

Le `DEMONSTRATION.md` du lot L7 annonce pourtant ce manque comme attendu : le jeu a été
conçu pour cela, le moteur ne le restitue pas.

### 8. Mobile — CONFORME

Captures en fenêtre 390 × 844 : `01b-connexion-mobile.png`, `02-accueil-mobile.png`,
`03-bibliotheque-mobile.png`, `04-import-mobile.png`,
`05-consultation-analyse-mobile.png`, `06-memoire-mobile.png`,
`07-checklist-mobile.png`. Pour chacune : `scrollWidth - clientWidth` mesuré = **0 px**
(contrôle fait dans la page, pas à l'œil), titres et contenus conformes à l'écran desktop.

### 9. Test de la ligne rouge — CONFORME sur l'export, NON CONFORME sur la source

- **Export refusé tant que la validation nommée n'est pas posée** : vérifié à deux
  endroits — sur un mémoire monté mais non validé (HTTP **409** + message pédagogique,
  capture `27-export-refuse-sans-validation-desktop.png`, corps exact au critère 5), et en
  tentant de valider le mémoire avec des sections encore en brouillon (refusé, aucune
  ligne `memoire_validation` créée). L'export n'a jamais servi un contenu non validé.
- **Section sans source de bibliothèque signalée comme manquante plutôt que produite** :
  **non conforme** — c'est exactement le défaut du critère 4. La section est produite.

---

## 4. Défauts, classés par gravité

### Bloquants

| # | Défaut | Preuve | Carte |
|---|---|---|---|
| B1 | **Import guidé : 0 proposition** sur les trois documents du jeu L7 (et sur tout document en français métier). Le critère 2 tombe : la bibliothèque ne se remplit que par saisie champ par champ. | `09-…`, `09b-…`, `10-…` ; `import_proposition` = 0 ; `fournisseur_factice.py:63-69` | `t_43088781` |
| B2 | **Mémoire : section produite pour un critère que la bibliothèque ne couvre pas** ; 0 manque alors que le jeu L7 en prévoit un ; l'export affirme « Aucun manque signalé ». Critère 4 non conforme **et règle centrale violée**. | `21-…`, `20-…`, `26-…` ; `memoire_manque` = 0 ; `ILIKE '%végétalis%'` = 0 ; `memoire_technique_genere.py:255-273` | `t_21fffbbc` |

### Majeur

| # | Défaut | Preuve |
|---|---|---|
| M1 | **Mot de passe en clair dans un fichier versionné** : `demarrer.sh` (fichier suivi par git, commit `663981e`) affiche au démarrage l'identifiant `verif@exemple.test` **et son mot de passe en clair** (non recopié ici volontairement : voir la ligne correspondante de `demarrer.sh`). Entorse à « aucun secret dans le dépôt » ; la ligne est masquée dans ma copie de log. | `demarrer.sh` ; `captures-P4/demarrer-sh-as-delivered.log` (ligne 13, masquée) |
| M2 | **Le `.env` livré configure un fournisseur hors UE** (`MODELE_FOURNISSEUR=ue` pointant `openrouter.ai`, clé d'accès active) alors que D8 impose un fournisseur France/UE, et R9 exige une démonstration **hors ligne**. Conséquence : `bash demarrer.sh` **tel quel** ne peut pas dérouler la démonstration sans faire sortir le DCE vers un tiers hors UE. Le `.env` n'est pas versionné (donc pas un secret au dépôt), mais c'est la configuration que l'exploitant exécute. Relevé sans aucune valeur de secret (hôte seul). | `grep` sur `.env` ; `demarrer-sh-as-delivered.log` ; `docs/DECISIONS.md` D8 |
| M3 | **Critère 6 : codes internes visibles à l'écran** (`[attestation_assurance_decennale]`, `[certificat_qualification]`, …) hors de tout bloc replié, plus six blocs « Références techniques » contenant UUID et empreintes SHA-256. | `16b-…`, `11-…`, `15-…`, `22-…`, `23-…` ; `checklist.py:318` | 

### Mineur

| # | Défaut | Preuve |
|---|---|---|
| m1 | Valeurs de nomenclature affichées avec leurs underscores (« Type d'assurance : `responsabilite_civile_decennale` ») alors que le titre de la carte est traduit. | `11-famille-assurances-apres-import-desktop.png` |
| m2 | Montants et surfaces formatés à l'anglaise dans le mémoire (« montant 412000.00 EUR HT, surface 3200.00 m2 ») alors que le reste du produit est en format français. | `export-qa-l8.md` |
| m3 | Une adresse inexistante renvoie `{"detail":"Not Found"}` (JSON FastAPI) au lieu de la page d'erreur du produit. | `19-page-erreur-desktop.png` |
| m4 | `test_invariants` dépend de l'ordre des fichiers de test (I6 compté sur l'état global de la base) : la suite est fragile si on l'exécute par sous-ensembles. | `pytest-phase-3-ordre-impose-echec-I6.txt` |
| m5 | `verif-data/` n'est pas dans `.gitignore` et contient des pièces chiffrées ; mes 6 pièces de jeu y ont été réécrites (fichiers non suivis, régénérés par le chargeur). Choix d'exploitant à trancher, déjà signalé par L7. | `git status` ; `scripts/jeu-de-test/DEMONSTRATION.md` |
| m6 | Le jeu L7 annonce dans `DEMONSTRATION.md` des résultats que le moteur ne restitue pas au 30/09 (le manque du critère à 10 %). La documentation n'est pas fausse sur la conception du jeu, mais elle décrit un comportement attendu non tenu : à relire après la correction de B2. | `scripts/jeu-de-test/DEMONSTRATION.md` § 4 |

### Aucun défaut de sécurité bloquant constaté

Isolation par client tenue (10 tentatives croisées, toutes en 404/400 sans fuite), aucune
clé ni mot de passe de démonstration en clair dans le dépôt **sauf** M1, aucun appel
réseau pendant la vérification (fournisseur `factice`), aucune donnée réelle (tout est
fictif et signalé).

---

## 5. Ce que cette vérification n'a PAS couvert

- **Le fournisseur de modèle réel (`ue`) n'a jamais été appelé** : je n'ai pas voulu
  envoyer de document à `openrouter.ai` et dépenser la clé de l'exploitant. Le
  comportement de l'analyse et de l'import **avec un modèle réel** n'est donc pas vérifié
  par cette passe (aucun test de la suite ne le fait non plus, par construction).
- **Le format PDF et l'OCR** : le jeu L7 ne fournit que des `.txt` ; je n'ai pas fabriqué
  de PDF pour ce parcours. Le refus explicite des autres formats n'a pas été retenté ici
  (couvert par les tests de la phase 3).
- **La restauration après `down`** : j'ai vérifié que les données survivent, pas qu'un
  `down` détruisant un mémoire validé est réversible (il ne l'est pas).
- **L'accessibilité (RGAA/WCAG AA)** : non mesurée (pas d'audit de contraste ni de
  navigation clavier). Seul le débordement horizontal mobile a été mesuré.
- **Les performances et le comportement concurrent** : non testés (jeu mono-utilisateur).
- **Le rendu des exports dans un vrai traitement de texte** : les `.docx` ont été ouverts
  par `python-docx` (structure et texte), pas par Word/LibreOffice, qui n'est pas installé
  ici. Le `.md` a été lu en texte.
- **Les écrans hors parcours** : je n'ai pas exploré les écrans de facturation,
  d'abonnement ou de provisionnement (hors périmètre de la phase 4).
- **L'état de la base de l'exploitant** (`ia_consultations_verif`) : non vérifié ; mes
  constats portent sur une base neuve dédiée. Le dossier `verif-data/clients/<client de
  démonstration>/` a en revanche été réécrit (6 pièces chiffrées, non suivies par git).

---

## 6. Cartes de correction créées

| Carte | Profil | Objet | Parents |
|---|---|---|---|
| `t_43088781` | `dev-back` | Correction bloquante — import guidé : 0 proposition sur un document réel (critère 2) | `t_097bbe97` |
| `t_21fffbbc` | `dev-back` | Correction bloquante — mémoire : section produite pour un critère non couvert, 0 manque (critère 4, ligne rouge) | `t_097bbe97` |
| `t_ebbaac86` | `dev-web` | Correction — critère 6 : codes internes visibles et blocs « Références techniques » | `t_097bbe97` |
| `t_928aec4b` | — | **doublon annulé** (créé par erreur en workspace `scratch`, remplacé par `t_43088781`) : commentaire « CARTE ANNULÉE » posé, à archiver par l'opérateur | — |

Je n'ai corrigé aucun code : je diagnostique, les lots propriétaires réparent.

---

## 7. Inventaire des preuves

Dans `docs/RAPPORTS/captures-P4/` :

*Écrans (desktop 1280 px)* — `01-connexion-deconnectee-desktop`, `08-import-vide-desktop`,
`09-import-propositions-desktop`, `09b-import-propositions-desktop`,
`10-import-proposition-desktop`, `11-famille-assurances-apres-import-desktop`,
`12-consultations-avant-depot-desktop`, `13-consultation-analyse-desktop`,
`14-consultation-criteres-ponderes-desktop`,
`15-consultation-references-techniques-ouvertes-desktop`, `16-checklist-desktop`,
`16b-checklist-piece-par-piece-desktop`, `17-memoire-avant-generation-desktop`,
`18-memoire-genere-desktop`, `19-page-erreur-desktop`, `20-memoire-valide-desktop`,
`21-memoire-section-vegetalisees-desktop`,
`22-memoire-references-techniques-ouvertes-desktop`,
`23-import-references-techniques-ouvertes-desktop`, `24-premiere-utilisation-desktop`,
`25-bibliotheque-nouvelle-entreprise-desktop`,
`26-memoire-manques-bibliotheque-vide-desktop`,
`27-export-refuse-sans-validation-desktop`.

*Écrans (mobile 390 px)* — `01b-connexion-mobile`, `02-accueil-mobile`,
`03-bibliotheque-mobile`, `04-import-mobile`, `05-consultation-analyse-mobile`,
`06-memoire-mobile`, `07-checklist-mobile`.

*Fichiers réels* — `export-qa-l8.md` (29 610 o), `export-qa-l8.docx` (40 068 o, ouvert).

*Sorties brutes* — `pytest-suite-complete.txt`, `pytest-phase-3-ordre-naturel.txt`,
`pytest-phase-3-ordre-impose-echec-I6.txt`, `verif-dce-et-checklist.txt`,
`verif-validation-et-export.txt`, `verif-ouverture-des-exports.txt`,
`verif-isolation-entre-clients.txt`, `verif-migrations-up-down-up.txt`,
`verif-donnees-demo-pendant-down.txt`, `verif-critere6-jetons-techniques.txt`,
`demarrer-sh-as-delivered.log`, `journal-appels-http.txt`.

Les captures de l'essai précédent de cette carte (interrompu par une limite de quota à
18 h 12, base et état différents) ont été écartées du dossier : elles ne sont pas
reproductibles telles quelles, et l'une d'elles contenait des cookies de session en clair
(`sessions.json`, supprimé du dépôt pour cette raison).
