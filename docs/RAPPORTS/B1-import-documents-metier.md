# B1 — Import guidé : le lecteur lit un document courant en français métier

*Carte `t_43088781` (correctif bloquant, critère 2 du § 1 du plan de phase 4).
Agent `dev-back`, 30 septembre 2026. Tout ce qui suit a été **exécuté** : suite de
tests, lecteur seul, serveur réel, base neuve, écran d'import et captures.*

---

## 1. Le défaut, et sa cause

Constat L8 : les trois documents du jeu L7 (`scripts/jeu-de-test/fictif/*.txt`),
rédigés en français métier, produisaient **0 proposition**. Cause identifiée :
`fournisseur_factice.py` ne reconnaissait que le micro-format
`Entité : <identifiant_snake_case>` / `- champ : valeur`. Aucun document réel n'est
écrit ainsi ; les documents L7 non plus.

## 2. Ce qui a changé

Un seul fichier de code modifié : `src/app/services/fournisseur_modele/fournisseur_factice.py`.

* nouvelle règle de lecture **`I4 — français métier`** : quand le document n'est pas
  au micro-format, il est relu comme un document d'entreprise courant ;
* la lecture est **orientée par `famille_cible`** : seules les entités de la famille
  visée sont proposées (exactement ce que le service accepte) ;
* deux formes d'écriture reconnues :
  * lignes `Libellé : valeur` (plaquette, attestation) — ex. `Raison sociale : …`,
    `Type d'assurance : …`, `Date d'échéance : …` ;
  * sections titrées — `QUALIFICATIONS ET CERTIFICATIONS`, `MOYENS HUMAINS`,
    `MOYENS MATÉRIELS`, `RÉFÉRENCES`, chapitres numérotés d'un ancien mémoire ;
* entités couvertes : `entreprise_version`, `assurance`, `attestation`, `produit`,
  `certification`, `reference_chantier`, `moyen_materiel`, `organigramme`,
  `chapitre_memoire` ;
* **le micro-format reste prioritaire** : un document qui le porte donne exactement
  les mêmes propositions qu'avant (aucun test L3 modifié) ;
* **aucun garde-fou abaissé** : `source_emplacement` reste obligatoire et
  `source_extrait` est la portion **littérale** du texte ; `source_presente` /
  `verifier_propositions_import` sont réutilisés tels quels, sans modification.

Les documents du lot L7 **n'ont pas été touchés** (`git status` : rien sous
`scripts/jeu-de-test/`). Aucun secret ajouté.

### Choix de lecture, assumés et contestables

* un montant n'est reconnu que suivi de sa devise (`412 000 EUR`), et ne franchit
  jamais une virgule de liste ;
* un « moyen matériel » provient d'un item de la section, sa quantité d'un nombre
  écrit en toutes lettres (`deux nacelles` → 2) ;
* les « moyens humains » sont proposés en **organigramme** (`description` littérale)
  plutôt qu'inventés en effectif par métier : le document ne donne pas de
  métier/nombre non ambigus ;
* un champ obligatoire absent du document (ex. `maitre_ouvrage`) **n'est pas
  inventé** : la proposition reste incomplète et attend une correction humaine.

## 3. Ce qui a été exécuté, et le résultat

### 3.1 Suite complète (non-régression)

```
$ cd src && ../.venv/bin/python -m pytest -q
259 passed, 1 warning in 19.36s      (rejoué deux fois, résultat identique)
```

Les 244 tests attendus au 30/09 restent verts ; **9 tests** sont ajoutés par cette
carte (`src/tests/test_import_documents_metier.py`). Le total observé (259) est
supérieur à 244 + 9 = 253 parce que la carte voisine **`t_21fffbbc`** (mémoire) édite
le **même arbre de travail** en parallèle et y a ajouté ses propres tests : mesuré
sans mon fichier, la suite est à 250. Aucun test retiré ni modifié par cette carte.

```
$ ../.venv/bin/python -m pytest -q tests/test_import_documents_metier.py
9 passed in 0.24s
```

### 3.2 Lecture seule, sur les trois documents du jeu L7

```
plaquette-presentation-FICTIF.txt      -> references_chantiers : 3 propositions
memoire-technique-anterieur-FICTIF.txt -> memoire_technique    : 5 propositions
attestation-assurance-RCD-FICTIF.txt   -> assurances           : 1 proposition
```

Champs réellement extraits (exemples) :

* `reference_chantier` : `intitule_operation` = « Réfection de l'étanchéité des
  toitures-terrasses du groupe scolaire FICTIF « Les Filaos » », `montant_montant`
  = `412000`, `montant_devise` = `EUR` ;
* `chapitre_memoire` : `titre` = « COMPRÉHENSION DE L'OPÉRATION », `ordre` = 1,
  `contenu_texte` = le paragraphe ;
* `assurance` : `type_assurance` = `responsabilité civile décennale`, `assureur` =
  `ASSURANCES-FICTIVES OCÉANE (FICTIF)`, `date_debut` = `2026-01-01`,
  `date_echeance` = `2026-10-15`, `montant_garantie_montant` = `1500000`.

### 3.3 Serveur réel, base neuve, jeu L7, fournisseur `factice`

Base dédiée `ia_consultations_t4308` (migrations 0001→0006), compte de
démonstration fictif, serveur `python -m uvicorn app.main:app --host 127.0.0.1
--port 8099`. Les **trois documents ont été déposés par le formulaire réel** de
`/bibliotheque/import` (`DOM.setFileInputFiles` + soumission), comme L8 l'avait fait.

| Document déposé | Famille choisie | HTTP | Propositions créées |
|---|---|---|---|
| `plaquette-presentation-FICTIF.txt` | `references_chantiers` | 303 | **3** |
| `memoire-technique-anterieur-FICTIF.txt` | `memoire_technique` | 303 | **5** |
| `attestation-assurance-RCD-FICTIF.txt` | `assurances` | 303 | **1** |

Contrôle SQL sur la base du parcours :

```
document                                | famille_cible        | propositions | acceptees | en_attente
attestation-assurance-RCD-FICTIF.txt    | assurances           | 1 | 1 | 0
memoire-technique-anterieur-FICTIF.txt  | memoire_technique    | 5 | 5 | 0
plaquette-presentation-FICTIF.txt       | references_chantiers | 3 | 1 | 2
```

```
total_propositions | sans_emplacement | sans_extrait
                 9 |                0 |           0
```

Contrôle d'adossement (même mécanique que `source_presente`, sur les documents
**chiffrés réellement stockés**, ré-extraits) : **9/9 propositions adossées** au
document, 0 non adossée — sortie complète dans
`captures-B1/verif-propositions-sourcees.txt`.

### 3.4 Décisions humaines

* Acceptation d'une proposition issue d'un document courant (assurance), depuis
  l'écran, avec un nom : l'élément est écrit en bibliothèque
  (`origine = document_extrait`, `confiance = a_verifier`, `piece` et
  `source_document_id` = document importé) ;
* acceptation d'une **référence de chantier** (correction nommée `maitre_ouvrage`)
  via `POST /api/v1/import/propositions/{id}` → **HTTP 200**, élément créé, affiché
  dans la famille avec « Origine : extraite d'un document que vous avez fourni »,
  « Source : document que vous avez fourni », « À vérifier » ;
* une décision sans nom reste refusée (`ErreurImportGuide`), vérifié par test.

### 3.5 Captures d'écran (`docs/RAPPORTS/captures-B1/`)

* `01-proposition-assurance-document-courant.png` — proposition d'assurance avec sa
  source littérale et ses champs ;
* `01b-decision-assurance-avant-acceptation.png` ;
* `02-proposition-chapitre-memoire.png` — chapitre lu dans l'ancien mémoire ;
* `03-proposition-reference-chantier.png` — référence lue dans la plaquette ;
* `04-decisions-deja-prises.png` — décisions nommées et horodatées ;
* `05-famille-references-apres-import.png` — bibliothèque enrichie par l'import ;
* `verif-propositions-sourcees.txt` — contrôle d'adossement brut.

## 4. Vérifié / supposé

**Vérifié par exécution** : les trois documents produisent des propositions ; chaque
proposition (9/9) porte un emplacement et un extrait littéralement présent ; la suite
est verte (253) ; l'acceptation écrit un élément `document_extrait` / `a_verifier` avec
`source_document_id` ; la décision exige un nom ; les tests le revérifient sur un
document courant (pas sur la fixture au micro-format).

**Supposé / non couvert** : le rendu avec un **vrai modèle** (`ue`) n'est pas exercé
(aucun appel réseau, comme L8) ; l'OCR/PDF ne sont pas rejoués (le jeu L7 est en
`.txt`) ; la lecture d'un document d'un **autre domaine** que celui du jeu L7 n'est
pas éprouvée.

## 5. Point résiduel signalé (hors périmètre de cette carte)

L'écran d'import n'affiche **pas de champ de saisie pour un champ obligatoire
absent** : il écrit « Il manque encore : Maître d'ouvrage » mais n'offre pas de le
saisir, alors que le service accepte une correction (`corrections`). Accepter une
telle proposition depuis l'écran échoue donc. Le correctif minimal appartient à un lot
d'interface (proche de la carte critère 6 `t_ebbaac86`) ; le service, lui, sait déjà
faire (test `test_accepter_une_reference_avec_correction_nommee`).
