# L3 — Analyse de DCE : extraction PDF/OCR, adaptateur du modèle, restitution sourcée

*Lot **L3** de la phase 3. Agent `dev-back`. Board `default`, tâche `t_d04515df`.
Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*
*Rapport d'exécution : les commandes ont été réellement lancées et les sorties recopiées
ci-dessous telles quelles.*

---

## 1. Ce qui a été livré

| Livrable | Chemin | État |
|---|---|---|
| Migration `0003` (annexe B § B1, B2, B3, B6) | `src/migrations/0003_analyse_dce.sql` | écrite, **appliquée puis annulée réellement** |
| Extraction PDF page par page + repli OCR | `src/app/services/extraction_pdf.py` | écrite, **exercée sur un PDF texte et sur un PDF scanné** |
| Couche d'abstraction du modèle (D8) | `src/app/services/fournisseur_modele/base.py` | écrite, **testée** |
| Fournisseur factice (déterministe, sans réseau) | `src/app/services/fournisseur_modele/fournisseur_factice.py` | écrit, **utilisé par tous les tests** |
| Fournisseur réel France/UE (HTTP) | `src/app/services/fournisseur_modele/fournisseur_ue.py` | écrit — **non testé sans clé d'API** (voir § 5) |
| Sélection du fournisseur | `src/app/services/fournisseur_modele/__init__.py` | écrite, **testée** |
| Orchestration dépôt → extraction → appel → restitution | `src/app/services/analyse_dce.py` | écrite, **exercée sur l'API réelle** |
| Routes gelées (annexe C) | `src/app/api/routes_analyse.py` | écrites, **exercées sur uvicorn local** |
| Jeu de démonstration fictif | `src/tests/fixtures/dce_fictif.txt`, `dce_fictif.pdf`, `dce_fictif_sans_date.{txt,pdf}`, `dce_fictif_scanne.pdf`, `generer_fixtures.py` | écrits, **régénérables et relus** |
| Tests de l'analyse de DCE | `src/tests/test_analyse_dce.py` | 17 tests, **exécutés** |
| Tests de la couche fournisseur | `src/tests/test_fournisseur_modele.py` | 19 tests, **exécutés** |
| Modèle de données mis à jour | `docs/DATA-MODEL-V2.md` § 17 (+ sommaire) | écrit |
| Ce rapport | `docs/RAPPORTS/L3-analyse-dce.md` | — |

Aucun déploiement, aucun port exposé sur Internet (uvicorn écoutait `127.0.0.1` le temps
de la démonstration, puis a été arrêté). Aucune donnée réelle : tous les documents,
identifiants et libellés portent la mention « DOCUMENT FICTIF — DÉMONSTRATION ».

---

## 2. Dépendances : annoncées, puis installées

Annonce faite **avant installation** en commentaire de carte (`t_d04515df`) :

| Dépendance | Justification | État |
|---|---|---|
| `tesseract` + `tesseract-lang` (binaire, Homebrew) | OCR des pages scannées ; explicitement dans la liste autorisée (annexe A § A10) | **installée** : `tesseract 5.5.3`, 162 langues (`fra` compris) |
| `pytesseract` (Python) | *non installé* — l'appel passe par le CLI `tesseract` via `subprocess`, ce qui évite une dépendance Python pour un simple appel de commande | — |
| `pdftotext` / `pdfinfo` / `pdftoppm` (poppler) | déjà présents (annexe D) | rien installé |
| `httpx` | déjà installé par L1 (tests) ; sert aussi au fournisseur UE | rien installé |

**Aucune nouvelle dépendance Python.** `src/requirements.txt` n'a pas été modifié.

Variables d'environnement ajoutées à `.env.example` (sans aucune valeur réelle) :
`MODELE_FOURNISSEUR`, `MODELE_FOURNISSEUR_URL`, `MODELE_FOURNISSEUR_CLE`,
`MODELE_FOURNISSEUR_NOM`, `MODELE_FOURNISSEUR_ORGANISME`, `MODELE_FOURNISSEUR_DELAI`,
`OCR_LANGUES`.

---

## 3. Migration `0003` — `up` puis `down`, sortie réelle

Commande (script local, hors dépôt) :
`sh demo_migrations_l3.sh > migrations_l3.log`

```
### 0. up (état de départ : toutes les migrations appliquées)
Migrations appliquées : aucune

### 1. statut avant l'annulation
0001  appliquée
0003  appliquée

### 2. down 1 (annule 0003)
Migrations annulées : 0003

### 3. tables consultation / extraction_element après down (attendu : aucune)
(rien au-dessus = correct)

### 4. colonnes nature / consultation_id de document après down (attendu : aucune)
(rien au-dessus = correct)

### 5. contrainte document.entreprise_id / fiche_version_id revenue NOT NULL
entreprise_id is_nullable=NO
fiche_version_id is_nullable=NO

### 6. up
Migrations appliquées : 0003

### 7. statut après
0001  appliquée
0003  appliquée

### 8. tables après up
consultation
extraction_element

### 9. contrainte I7 (document_nature_coherence)
document_nature_coherence : CHECK (((((nature)::text = 'piece_bibliotheque'::text) AND (entreprise_id IS NOT NULL) AND (fiche_version_id IS NOT NULL)) OR (((nature)::text = 'dce'::text) AND (consultation_id IS NOT NULL))))
extraction_element_source_emplacement_non_vide : CHECK ((length(btrim((source_emplacement)::text)) > 0))
extraction_element_verificateur_requis : CHECK ((((statut_verification)::text <> ALL ((ARRAY['valide'::character varying, 'corrige'::character varying])::text[])) OR ((verificateur_nom IS NOT NULL) AND (length(btrim((verificateur_nom)::text)) > 0))))

### 10. jeux de référence créés par 0003
consultation.categorie_element : 3 valeurs
consultation.statut : 4 valeurs
consultation.statut_verification : 4 valeurs
document.nature : 2 valeurs
```

Lecture : le schéma est **réversible sans reste** (tables, colonnes et contraintes
disparaissent au `down`, les deux colonnes redeviennent `NOT NULL`), et le `up` suivant
le rétablit à l'identique.

Deux points de conception à connaître, imposés par l'annexe B :

- **Le `down` supprime les lignes `document` de nature `dce`** avant de remettre
  `fiche_version_id` en `NOT NULL`. Sans cela, l'annulation serait impossible dès qu'un
  DCE a été déposé (un DCE n'a pas de version de fiche, par définition). C'est écrit dans
  le fichier de migration, et c'est la seule écriture de données qu'il effectue côté client.
- **Un DCE peut porter `entreprise_id`** (l'espace de travail qui l'a déposé) mais
  **jamais** `fiche_version_id` : c'est ce que la contrainte I7 ci-dessus impose.

---

## 4. Un PDF fictif déposé → pièces, critères, date limite, **chacun sourcé**

Démonstration **sur l'API réelle** (uvicorn local `127.0.0.1:8011`, fournisseur `factice`,
aucun appel externe). Extraits de la sortie réelle :

```
2. Dépôt du DCE fictif (POST /api/v1/consultations, multipart)
HTTP 201
consultation : {"id": "c3b0bc15-...", "statut": "analysee", "libelle": "Étanchéité groupe scolaire — DCE FICTIF DÉMONSTRATION", ...}
document     : {"id": "fdaed235-...", "nature": "dce", "fiche_version_id": null,
                "chemin_stockage": "clients/828859ba-.../fdaed235-....bin",
                "empreinte_sha256": "379faff0...", "mime_type": "application/pdf"}
fournisseur  : factice | modèle : regles-de-lecture-v1
avertissement: Fournisseur factice — non-IQ réel : règles de lecture mécaniques, sans modèle de langage. [...]
pages lues   : [{"page": 1, "methode": "texte", ...}, ..., {"page": 5, "methode": "texte", ...}]
éléments non trouvés : []

[critere      ] 'Prix des prestations'
                 valeur      : '40 %'
                 source doc  : fdaed235-6ba6-4245-8c19-80f0724168de
                 emplacement : page 4 — section « ARTICLE 3 — CRITÈRES D'ATTRIBUTION »
                 extrait     : '- Prix des prestations : 40 %'
                 confiance   : a_verifier | vérification : propose

[date_limite  ] 'La date limite de remise des offres est fixée au 15 décembre 2026 à 12h00 (heure locale).'
                 valeur      : '2026-12-15'
                 emplacement : page 5 — section « ARTICLE 4 — DATE LIMITE DE REMISE DES OFFRES »
                 extrait     : 'La date limite de remise des offres est fixée au 15 décembre 2026 à 12h00 (heure locale).'
                 confiance   : a_verifier | vérification : propose

[piece_exigee ] "Attestation d'assurance responsabilité décennale en cours de validité"
                 emplacement : page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES »
                 extrait     : "Attestation d'assurance responsabilité décennale en cours de validité"
                 confiance   : a_verifier | vérification : propose
```

Bilan de ce dépôt : **10 éléments** (6 pièces exigées, 3 critères pondérés, 1 date limite),
**chacun** avec `source_document_id`, `source_emplacement` (page + section) et
`source_extrait` littéral, `confiance = a_verifier` et `statut_verification = propose`.

Le rejet d'une valeur inventée est également démontré, côté fournisseur réel simulé
(§ 5) : un extrait qui ne se retrouve pas dans le document fait lever
`ReponseModeleInvalide`.

---

## 5. OCR : **testé pour de vrai** (tesseract a pu être installé)

Le jeu de test contient une variante **« scannée »** : `dce_fictif_scanne.pdf` est
construit par `src/tests/fixtures/generer_fixtures.py` en rasterisant le PDF texte
(`pdftoppm`, JPEG) puis en ré-embarquant les images — **aucune couche texte**. Vérifié :

```
$ pdftotext -layout src/tests/fixtures/dce_fictif_scanne.pdf - | wc -c
       6          # uniquement des sauts de page : aucune couche texte
```

Dépôt réel de ce PDF scanné par l'API :

```
A. Dépôt du PDF SCANNÉ (image seule) — chemin OCR
HTTP 201
pages (méthode réelle) : [{"page": 1, "methode": "ocr", "analyseable": true, "caracteres": 136, ...},
                          {"page": 2, "methode": "ocr", ...}, {"page": 3, "methode": "ocr", "caracteres": 517, ...},
                          {"page": 4, "methode": "ocr", "caracteres": 216, ...}, {"page": 5, "methode": "ocr", ...},
                          {"page": 6, "methode": "ocr", ...}]
fichier illisible      : False
éléments non trouvés   : []
  [piece_exigee ] "Attestation d'assurance responsabilité décennale en cours de validité"
      page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES »
  [critere      ] 'Prix des prestations'  valeur='40 %'   page 4 — section « ARTICLE 3 — CRITÈRES D'ATTRIBUTION »
  [date_limite  ] '...15 décembre 2026 à 12h00...'  valeur='2026-12-15'
      page 5 — section « ARTICLE 4 — DATE LIMITE DE REMISE DES OFFRES »
```

Les 6 pages ont été lues par OCR (`fra`), et l'analyse produit le **même jeu d'éléments
sourcés** que sur le PDF natif. La machine lit réellement le scan : ce chemin n'est donc
pas « livré non testé ».

*Réserve honnête* : le jeu de test est un scan **synthétique**, propre (300 dpi, sans
inclinaison ni bruit). Un scan réel dégradé (photocopie, tampon, encre pâle) n'a pas été
essayé ; la qualité d'OCR sur ce type de document reste à démontrer avec un cas réel —
et aucun DCE réel n'est disponible (D10).

---

## 6. Élément introuvable → « non trouvé dans le document »

Dépôt réel de `dce_fictif_sans_date.pdf` (fictif, sans critère ni date limite) :

```
B. Dépôt d'un DCE fictif INCOMPLET — catégories absentes
HTTP 201
  trouvé    [piece_exigee ] "Attestation d'assurance responsabilité civile professionnelle"
  trouvé    [piece_exigee ] "Extrait d'immatriculation au registre du commerce (document fictif)"
  ABSENT    [critere      ] 'non trouvé dans le document' (document f10185a6-..., 'absent du document')
  ABSENT    [date_limite  ] 'non trouvé dans le document' (document f10185a6-..., 'absent du document')
aucune ligne en base pour ces absences : True
```

Aucune valeur n'est comblée, aucune ligne n'est créée pour ces deux catégories : le
« non trouvé » est restitué **avec le document où il a été cherché**, et rien d'autre.
Un test (`test_element_introuvable_est_declare_non_trouve`) verrouille ce comportement.

---

## 7. Verrou n° 2 : seul un élément `valide` alimente la brique C

Test `test_seul_un_element_valide_est_utilisable_par_la_brique_c` : avant toute action
humaine, `elements_valides()` renvoie une liste **vide** ; après une validation nommée, il
renvoie **exactement** l'élément validé ; l'élément encore `propose`, et l'élément
`corrige` non re-validé, en restent exclus.

```
4a. Validation d'un élément SANS nom de vérificateur (doit être refusée)
HTTP 400 {'detail': '`verificateur_nom` est obligatoire pour valider ou corriger un élément :
                    aucune validation sans action humaine nommée (ligne rouge).'}

4b. Validation avec nom du vérificateur (JSON)
HTTP 200 ... "statut_verification": "valide", "verificateur_nom": "Anthony (démonstration)",
             "date_verification": "2026-09-30T11:30:37.958028+04:00"

4c. Correction d'un autre élément (formulaire, comme le fera l'interface web)
HTTP 200 ... "statut_verification": "corrige", "verificateur_nom": "Anthony (démonstration)",
             "source_emplacement": "page 3 — section « ARTICLE 2 — PIÈCES EXIGÉES »"  # la source survit
```

Le formulaire **et** le JSON sont acceptés sur cette route (l'interface de L5 n'aura pas
de JavaScript ; un client d'API envoie du JSON).

---

## 8. Isolation entre deux clients

Tests `test_deux_clients_ne_voient_pas_leurs_consultations` et
`test_route_isolation_entre_deux_clients` : le client B, authentifié, obtient **404** sur
la consultation de A (aucun indice sur son existence) ; en base, ses requêtes sur
`consultation` et `extraction_element` renvoient **zéro ligne** ; il ne peut ni valider un
élément de A ni l'obtenir par `elements_valides`. La route vérifie aussi le refus **401**
sans session.

---

## 9. Ce qui n'est **pas** testé (et pourquoi)

| Élément | État | Motif |
|---|---|---|
| Fournisseur de modèle **réel** (Mistral, OVHcloud, modèle auto-hébergé) | **NON TESTÉ** | Aucune clé d'API disponible (risque **R3**). Le chemin est codé, la lecture de réponse est testée avec un transport HTTP **simulé en mémoire** (`httpx.MockTransport`, aucun accès réseau) ; l'appel sortant réel, l'adresse et le nom du modèle ne sont pas prouvés. À rejouer dès qu'une clé sera fournie. |
| Qualité d'analyse d'un **vrai modèle** | **NON TESTÉE** | Conséquence directe : le fournisseur factice applique des règles de lecture, il ne comprend rien. Les tests prouvent la mécanique et les garde-fous, **pas** la pertinence d'une extraction par IA. |
| OCR sur un **scan dégradé réel** | **NON TESTÉ** | Aucun DCE réel (D10) ; le scan du jeu de test est synthétique et propre. |
| Formats non PDF/texte (`.docx`, `.odt`…) | **refusés volontairement** | Défaut retenu de la question ouverte n° 2 : refus explicite plutôt qu'acceptation sans traitement (`HTTP 400` vérifié). |
| Non-conservation des données chez le fournisseur (D6) | **non implémentée, non promise** | Aucune option de non-conservation n'est envoyée : elles n'existent pas chez tous les fournisseurs. La garantie doit être **vérifiée au niveau du compte** du fournisseur retenu — le code ne prétend rien de plus (commentaire du module). |
| `conftest.py` : base de test dédiée | réutilisé tel que livré par L1 | migrations `up`/`down` par session de tests |

---

## 10. Suite de tests — sortie réelle

```
$ cd src && pytest -q
60 passed, 1 warning in 5.90s
```

(1 avertissement de dépréciation `starlette`/`httpx`, déjà présent avant ce lot.)

Détail : 17 tests dans `test_analyse_dce.py`, 19 dans `test_fournisseur_modele.py`,
24 dans `test_socle.py` (socle L1, dont deux assertions corrigées — § 11.1). Aucun test
n'est ignoré : le chemin OCR s'exécute réellement depuis que `tesseract` est installé.
**Aucun appel réseau** dans les tests : le fournisseur par défaut est le factice, et le
fournisseur UE est exercé avec un transport simulé.

---

## 11. Modifications hors de mes fichiers — assumées et signalées

Trois fichiers appartiennent à d'autres lots ; je les ai touchés au minimum, et je le
declare ici :

1. **`src/tests/test_socle.py`** (L1) — deux tests y échouaient dès l'ajout d'une
   migration `0002`/`0003` : ils exigeaient en dur que `0001` fût **la seule** migration du
   dossier, ce que l'annexe A § A4 contredit en réservant `0001` à `0004`. J'ai remplacé
   ces deux assertions par des invariants qui restent vrais (présence de `0001`, liste
   triée, cycle complet `down`/`up`). **Ce point est aussi un commentaire de carte** —
   c'est une collision inter-lots : L2 produit le même effet.
2. **`src/app/main.py`** (L1) — deux lignes pour enregistrer le routeur
   `routes_analyse` (contrat gelé de l'annexe C : sans cela, aucune route n'existerait).
3. **`.env.example`** (L1) — ajout, en fin de fichier, des variables du fournisseur de
   modèle et de l'OCR, **sans aucune valeur secrète** (l'adresse et la clé sont vides).

`docs/DATA-MODEL-V2.md` est le fichier qui m'est explicitement attribué : j'y ai ajouté la
**section 17** (briques B et C : `document.nature`, `consultation`, `extraction_element`,
`checklist_execution`, `checklist_ligne`, invariants I7/I8, jeux de référence) et l'entrée
de sommaire correspondante. J'ai aussi corrigé la **phrase de clôture** du document, qui
affirmait « aucun schéma appliqué, aucune migration écrite, aucun code produit » : elle
était devenue fausse pour la section 17 et ne l'était pas pour les sections 0 à 16 dont
elle parlait. Aucune section antérieure n'a été modifiée sur le fond.

---

## 12. Décisions non couvertes par les annexes (signalées en commentaire de carte)

1. **`test_migrations_lister_0001`** / **`test_migrations_down_puis_up`** — voir § 11.1.
2. **Jeux de référence de l'annexe B § B6** : j'ai fait semer par la migration `0003` les
   **valeurs** de `document.nature`, `consultation.statut`,
   `consultation.categorie_element`, `consultation.statut_verification` (les codes viennent
   de l'annexe, aucune valeur inventée). L1 laissait ces jeux non semés (« non attribué »).
   L4 devra semer `checklist.statut_ligne` dans `0004`.
3. **Élément « non trouvé »** : comme `source_document_id` et `source_emplacement` sont
   **non nuls** (annexe B § B3/B7), un « non trouvé » n'est **pas** stocké comme élément —
   il est restitué par la lecture, avec `source_emplacement = "absent du document"`. Cela
   évite de faire valider par un humain un élément qui n'existe pas.
4. **Corps de la route de vérification** : accepté en formulaire **et** en JSON (l'annexe C
   ne le précisait pas ; L5 n'aura pas de JavaScript).
5. **`document.type_document = 'dce'`** : jeu non semé au MVP (contenu attribué à L5) ; la
   valeur employée est donc marquée non sourcée et à vérifier (annexe B § B6).

---

## 13. Reste à faire (hors lot)

- Fournir une **clé d'API** France/UE et rejouer le chemin réel (`MODELE_FOURNISSEUR=ue`) :
  c'est la seule façon de prouver la brique B avec un vrai modèle (question ouverte n° 1).
- **L4** consomme `analyse_dce.elements_valides()` (verrou n° 2) et écrit `0004`.
- **L5** reprend le contrat gelé de l'annexe C pour les écrans (dépôt, analyse avec source,
  vérification d'un élément).
- **L8** refait, indépendamment, le test d'isolation et cherche à faire échouer les garde-fous
  de source (par exemple en injectant une proposition inventée côté fournisseur).
- Les fichiers déposés en démonstration vivent dans `data/demonstration/` (hors dépôt, ignoré
  par git) ; ils peuvent être supprimés à tout moment sans casser le produit.
