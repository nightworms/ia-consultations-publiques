# Rapport d'exécution — L4 : checklist de conformité (brique C)

*Lot L4, phase 3. Agent `dev-back`. Tâche Kanban `t_ea8d140e`. Dépend de L2
(`t_1a092acf`) et L3 (`t_d04515df`). Écrit le 30 septembre 2026 (+04).*

Ce rapport ne contient que des **exécutions réelles** : chaque sortie collée ci-dessous
provient d'une commande lancée sur la machine. Aucune donnée réelle, aucun secret : les
jeux sont fictifs et signalés « DOCUMENT FICTIF — DÉMONSTRATION ». Rien n'a été déployé,
aucun port n'est exposé sur Internet (serveurs de démonstration liés à `127.0.0.1`).

---

## 1. Ce qui a changé

| Livrable | État | Contenu |
|---|---|---|
| `src/migrations/0004_checklist.sql` | créé | Tables `checklist_execution` (B4) et `checklist_ligne` (B5), **invariant I8**, jeu de référence `checklist.statut_ligne` (B6), sections **up** et **down** |
| `src/app/services/checklist.py` | remplacé (squelette phase 1) | Croisement pièces exigées validées × bibliothèque ; statuts `presente` / `manquante` / `a_verifier` ; contradictions exposées |
| `src/app/api/routes_checklist.py` | créé | `POST /api/v1/consultations/{id}/checklist`, `GET /api/v1/consultations/{id}/checklist` |
| `src/tests/test_checklist.py` | créé | 17 tests, tous verts |
| `docs/RAPPORTS/L4-checklist.md` | ce fichier | Rapport d'exécution |

**Modifications hors lot** (signalées, additives) :

- `src/app/main.py` : `include_router(routes_checklist.router)` + import (4 lignes).
- `src/tests/test_analyse_dce.py` : deux assertions de `test_migration_0003_down_puis_up`
  rendues robustes (`down(1)` en dur → `down(2)` et appartenance). Motif : l'ajout de la
  migration `0004` fait que `0003` n'est plus la dernière. Précédent assumé : L3 avait fait
  de même sur `test_socle.py`. **Aucun fichier de migration d'un autre lot n'a été touché.**

**Aucune dépendance nouvelle** : le service n'utilise que la bibliothèque standard
(`re`, `unicodedata`, `datetime`). Aucune installation.

---

## 2. Migration 0004 — `up` puis `down` (exigence vérifiable n° 1)

Commande (base locale dédiée aux tests, `ia_consultations_test`) :

```
$ python -m app.storage.migrations statut
0001  appliquée
0002  appliquée
0003  appliquée
0004  appliquée

$ python -m app.storage.migrations down 1
Migrations annulées : 0004

$ psql -c "\dt checklist*"
Did not find any tables named "checklist*".

$ python -m app.storage.migrations up
Migrations appliquées : 0004

$ psql -c "\dt checklist*"
                List of tables
 Schema |        Name         | Type  | Owner
--------+---------------------+-------+------
 public | checklist_execution | table | pause
 public | checklist_ligne     | table | pause

$ psql -c "select code, libelle from valeur_reference where namespace='checklist.statut_ligne' order by ordre;"
    code    |             libelle
------------+---------------------------------
 presente   | Présente dans la bibliothèque
 manquante  | Manquante — rien n'est fabriqué
 a_verifier | À vérifier par un humain
```

Contraintes réellement créées sur `checklist_ligne` (extrait `pg_constraint`) :
`checklist_ligne_i8`, `checklist_ligne_execution_meme_client`,
`checklist_ligne_element_meme_client`, `checklist_ligne_document_meme_client`, plus les
`NOT NULL`. Test dédié : `test_migration_0004_up_down_up`.

### L'invariant I8, porté par le schéma, et pas seulement par le code

- **Cardinalité** — contrainte `checklist_ligne_i8` :
  `presente` ⇒ `document_id` non nul ; `manquante` ⇒ `document_id` nul ; statut borné à
  `presente` / `manquante` / `a_verifier`.
- **Même client** — clés étrangères **composites** `(document_id, client_id)`,
  `(extraction_element_id, client_id)`, `(checklist_execution_id, client_id)` : référencer
  la pièce d'un autre client est refusé **par la base**. Ces clés exigent un `UNIQUE
  (id, client_id)` sur `document` et `extraction_element`, ajouté puis retiré par `0004`
  (contraintes additives, réversibles ; aucun fichier d'autre lot modifié).
  Preuve négative : `test_invariant_i8_au_niveau_de_la_base` (les trois refus sont observés,
  voir § 5).

---

## 3. Verrou n° 2 — seuls les éléments validés alimentent la checklist (exigence n° 2)

`test_verrou_2_seuls_les_elements_valides_alimentent` : un élément `valide` et un élément
resté `propose` sur la même consultation. Résultat : `nb_exigences == 1`, la seule ligne est
l'élément validé ; l'élément `propose` **n'apparaît pas**. La sélection est faite en SQL
(`statut_verification = 'valide'`), pas dans l'affichage.

---

## 4. Cas d'erreur obligatoires (exigence n° 3)

Chacun est un test dédié, vert :

| Cas | Test | Comportement observé |
|---|---|---|
| Pièce exigée absente | `test_piece_absente_manquante_et_rien_fabrique` | ligne `manquante`, `document_id` nul ; **nombre de documents inchangé** avant/après (aucune pièce fabriquée) ; justification « le système ne fabrique pas la pièce manquante » |
| Pièce présente, échéance passée | `test_piece_presente_mais_echeance_passee_a_verifier` | ligne `a_verifier` **avec la raison** (« échéance dépassée le 2020-01-01 »), `document_id` renseigné ; le système ne la déclare pas valide |
| Extraction partielle | `test_extraction_partielle_signalee` | `checklist_execution.extraction_partielle = 1`, `resume.extraction_partielle = true`, avertissement « Extraction partielle : 1 élément… » ; catégorie absente signalée séparément |
| Bibliothèque vide | `test_bibliotheque_vide_beaucoup_de_manquante` | `nb_pieces_bibliotheque = 0`, `nb_manquantes = 3`, `nb_presentes = 0`, toutes les lignes `document_id = null` |
| Deux valeurs contradictoires | `test_deux_valeurs_contradictoires`, `test_contradiction_entre_pieces_exigees` | les **deux** valeurs et leur source sont exposées dans `contradictions` ; lignes concernées `a_verifier` ; aucun choix |
| Correspondance incertaine | `test_correspondance_incertaine_jamais_presente` | `a_verifier`, **jamais** `presente` |

---

## 5. Isolation entre deux clients et invariant I8 en base (exigence n° 4)

- `test_deux_clients_ne_voient_pas_leurs_checklists` : B ne lit pas la consultation de A
  (`ConsultationIntrouvable`), ne compte **aucune** ligne ni exécution de checklist, et ne
  peut pas exécuter une checklist sur la consultation de A.
- `test_invariant_i8_au_niveau_de_la_base` : trois insertions refusées par la base —
  `presente` sans document (`CheckViolation`), `manquante` avec document (`CheckViolation`),
  `presente` référençant la pièce d'un **autre client** (`ForeignKeyViolation`).

Démonstration **de bout en bout sur un vrai serveur** (`uvicorn` sur `127.0.0.1`, jeu seedé
hors dépôt) :

```
POST checklist sans session        -> HTTP 401
GET  checklist avant exécution     -> HTTP 404
connexion (client A, fictif)       -> HTTP 200
POST checklist (client A)          -> HTTP 200
  resume : {"nb_exigences": 3, "nb_presentes": 1, "nb_manquantes": 1, "nb_a_verifier": 1,
            "extraction_partielle": true, "categories_sans_element": ["critere"],
            "nb_pieces_bibliotheque": 2}
  lignes :
    a_verifier | Attestation de vigilance sociale        | doc = 7a197521-… (échéance 2020-01-01)
    manquante  | Fiche technique du système d'étanchéité | doc = None
    presente   | Attestation d'assurance responsabilité décennale | doc = c0807e19-…
  contradictions : « Formulaire de candidature » → 2026-12-15 et 2026-12-20 (les deux, avec source)
GET  checklist (client A)          -> HTTP 200, même exécution (2c2152b7-…), 3 lignes
connexion (client B, fictif)       -> HTTP 200
GET  checklist de A par B          -> HTTP 404
```

La sortie ne contient **jamais** le mot « conforme » : vérifié par assertion dans les tests
(`"conforme" not in reponse.text.casefold()`) et sur la réponse HTTP réelle.

---

## 6. Sortie réelle de la suite de tests

```
$ ../.venv/bin/python -m pytest tests/test_checklist.py -v
collected 17 items
tests/test_checklist.py::test_migration_0004_presente_et_deux_sections PASSED
tests/test_checklist.py::test_migration_0004_up_down_up PASSED
tests/test_checklist.py::test_verrou_2_seuls_les_elements_valides_alimentent PASSED
tests/test_checklist.py::test_piece_absente_manquante_et_rien_fabrique PASSED
tests/test_checklist.py::test_piece_presente_mais_echeance_passee_a_verifier PASSED
tests/test_checklist.py::test_piece_presente_sans_echeance_est_presente PASSED
tests/test_checklist.py::test_extraction_partielle_signalee PASSED
tests/test_checklist.py::test_bibliotheque_vide_beaucoup_de_manquante PASSED
tests/test_checklist.py::test_deux_valeurs_contradictoires PASSED
tests/test_checklist.py::test_contradiction_entre_pieces_exigees PASSED
tests/test_checklist.py::test_correspondance_incertaine_jamais_presente PASSED
tests/test_checklist.py::test_deux_clients_ne_voient_pas_leurs_checklists PASSED
tests/test_checklist.py::test_execute_par_obligatoire PASSED
tests/test_checklist.py::test_invariant_i8_au_niveau_de_la_base PASSED
tests/test_checklist.py::test_lecture_sans_execution_est_explicite PASSED
tests/test_checklist.py::test_routes_checklist_refusent_sans_session PASSED
tests/test_checklist.py::test_routes_checklist_parcours_complet PASSED
17 passed, 1 warning in 0.49s
```

Suite complète (tous lots) : **115 passed** (98 avant ce lot + 17 du lot L4).

---

## 7. Décisions prises (non couvertes par les annexes)

Chacune est aussi signalée en commentaire sur la carte Kanban `t_ea8d140e`.

1. **Appariement texte** — les annexes ne disent pas *comment* rapprocher une exigence d'une
   pièce. Règle retenue, **conservatrice** : normalisation (minuscules, sans accents,
   ponctuation → espaces) puis appariement `forte` (libellés identiques, ou tous les mots
   significatifs de l'exigence présents dans la pièce, ou le type déclaré de la pièce
   entièrement décrit par l'exigence), sinon `incertaine` (au moins un mot commun). Une
   couverture partielle est **toujours** `a_verifier`. Un appariement sémantique (modèle)
   reste à faire ; le présent appariement est lexical et assumé comme tel.
2. **Contradictions** — détectées sur **tous** les éléments validés (et pas seulement les
   pièces exigées), pour couvrir l'exemple « date différente » de `SPEC-MVP-V2` § 3.4 ; elles
   sont exposées dans la clé `contradictions` avec les deux valeurs et leur source. Les pièces
   exigées concernées passent `a_verifier`.
3. **`fiche_version_id` en entrée** — B4 le déclare obligatoire ; la route l'accepte
   *facultatif* et retient alors **la version la plus récente du client** (enregistrée dans
   l'exécution). À défaut de fiche, erreur explicite (rien à croiser).
4. **Code HTTP** — l'annexe C ne fige pas les codes de la branche checklist : `POST` renvoie
   `200` (action de calcul) et `GET` `200` ; `404` si la consultation ou la checklist est
   introuvable, `400` pour une demande invalide, `401` sans session.
5. **`extraction_partielle`** — vrai dès qu'un élément lu reste `propose` ou `corrige`
   (formulation B4 « des éléments lus sont restés non validés »). Les catégories attendues
   sans aucun élément sont signalées en plus, sous `categories_sans_element`.
6. **`a_verifier` et document** — I8 n'interdit un `document_id` qu'aux lignes `manquante` :
   une pièce présente mais douteuse (échéance passée) porte donc son `document_id`, pour que
   le relecteur la retrouve.
7. **Contraintes d'unicité composites** — ajout de `UNIQUE (id, client_id)` sur `document` et
   `extraction_element` dans `0004` (additives, retirées par `down`) pour porter l'invariant
   « même client » au niveau de la base.

---

## 8. Ce qui n'est pas fait / réserves honnêtes

- **Appariement lexical, pas sémantique** : un libellé d'exigence et un libellé de pièce qui
  ne partagent aucun mot ressortiront `manquante` (ou `a_verifier` si un mot commun). C'est
  volontairement prudent ; un vrai appariement métier reste à concevoir.
- **Aucun test avec un vrai DCE volumineux** : la bibliothèque et les extractions employées
  dans les tests sont construites par le code de test, fictives et signalées.
- **Aucune route de provisionnement** de la bibliothèque n'existe (contrat gelé, constat déjà
  porté par L2, carte `t_5b51c472`) : la démonstration HTTP a donc été seedée hors dépôt.
- **Aucun commit git** (cohérent avec les lots précédents) ; **aucun déploiement**.
- **`docs/DATA-MODEL-V2.md` n'est pas touché** (L3 en est le seul rédacteur) ; aucun fichier
  de migration d'un autre lot n'est modifié.

---

## 9. Points chauds (à ne pas empiler)

- `src/app/main.py` : ajout d'`include_router` à chaque lot (L2, L3, L4). L5 devra y brancher
  son routeur web : collision probable, à sérialiser.
- `src/tests/test_socle.py` et `src/tests/test_analyse_dce.py` : assertions de migrations qui
  supposent quelle migration est « la dernière ». Toute nouvelle migration les invalide ; à
  traiter comme un point unique si une `0005` apparaît.
