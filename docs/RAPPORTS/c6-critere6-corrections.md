# C6 — Critère 6 : codes internes à l'écran (correction du lot `dev-web`)

*Carte `t_ebbaac86`, dérivée de la vérification indépendante L8
(`docs/RAPPORTS/P4-qa-criteres-acceptation.md`, critère 6 NON CONFORME).
Rédigé le 30 septembre 2026 par `dev-web`, à partir d'exécutions réelles.*

**Tout est FICTIF.** Aucune donnée réelle, aucun identifiant d'entreprise ni de
collectivité. Le jeu de démonstration est celui du lot L7
(`scripts/jeu-de-test/`), signalé comme fictif.

---

## 1. Ce qui a été corrigé

| Point de la carte | État | Où |
|---|---|---|
| 1. Codes métier entre crochets visibles, hors bloc replié (checklist) | **corrigé** | `src/app/web/routes_web.py` (affichage), `templates/checklist.html` |
| 2. Valeurs de nomenclature brutes (`responsabilite_civile_decennale`) | **corrigé** (écrans de bibliothèque) | `src/app/web/routes_web.py` (`_valeur_lisible`) |
| 3. Blocs « Références techniques » avec UUID et empreintes | **non touché — arbitrage demandé** | voir § 4 |
| 4. Adresse inconnue : JSON `{"detail":"Not Found"}` au lieu de la page d'erreur | **corrigé** | `src/app/web/routes_web.py` + `src/app/main.py` |

### Point 1 — les codes entre crochets ne sortent plus du corps de l'écran

`app.services.checklist._decrire_document()` construit `f"{libelle} [{type_document}]"`
(`checklist.py:318`). Ce texte arrive dans `l.justification` et `l.piece_libelle`.
**Aucun fichier de `dev-back` n'a été modifié** : le nettoyage se fait à la
construction du contexte d'écran, dans `routes_web.py` — c'est le choix « retirer
l'affichage » proposé par la carte.

- `_MOTIF_CODE_CROCHETS` : motif étroit (`\s*\[[a-z][a-z0-9_]{2,}\]`), pour ne pas
  toucher une crochetée française légitime (`[FICTIF]` n'est pas atteint) ;
- `lignes`, `resume`, `avertissements` et `contradictions` passent par
  `_sans_code_technique` / `_texte_libre_sans_code` ;
- **l'information technique n'est pas perdue** (règle de `docs/DESIGN.md` § 5
  « aucune information utile n'est supprimée ») : les codes relevés sont désormais
  listés dans le bloc replié `Références techniques` de l'écran de checklist
  (`codes_retenus`).

### Point 2 — les valeurs de nomenclature se lisent comme le titre

`_valeur_lisible()` appliquait déjà les dates et les nombres ; il rend maintenant
aussi les valeurs de code lisibles : `_MOTIF_VALEUR_CODE`
(`^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$`) → tirets bas remplacés par des espaces. Le motif
ne touche ni un code en majuscules (`SIREN`, `SAS`), ni un montant, ni une date, ni
un UUID (déjà traité par `_MOTIF_UUID`).

**Portée réelle** : les quatre écrans de famille montraient la valeur brute
(`Type d'assurance : responsabilite_civile_decennale`, `Domaine (référence) :
travaux_en_hauteur`, `Nature des travaux (référence) : etancheite_toiture_terrasse`,
`Catégorie (référence) : materiel_mise_en_oeuvre`) — c'est là que la correction
s'applique. Le même défaut subsiste **dans le texte du mémoire généré** (point 2 du
§ 5) : ce texte-là vient du générateur, pas de l'affichage.

### Point 4 — une adresse inconnue montre la page d'erreur du produit

Un gestionnaire d'exception vit sur l'application, pas sur un routeur : la ligne
`app.add_exception_handler(404, routes_web.gestionnaire_404)` a été ajoutée à
`src/app/main.py` (5 lignes commentées). Garde-fous vérifiés en exécution :

- `/api/…` et `/static/…` gardent **le gestionnaire JSON d'origine de FastAPI** :
  un message métier de route (`« Provisionnez une entreprise »`) n'est pas écrasé —
  c'est ce que le premier essai cassait, et que la suite de tests a rattrapé (§ 3) ;
- `/` garde sa réponse d'identification JSON (contrôle de `demarrer.sh`) ;
- sur une adresse d'écran, la réponse est `erreur.html` en `404` ;
- `_poser_identite_sans_route` : la page d'erreur garde la barre de navigation de
  l'utilisateur **connecté** (aucune dépendance de route n'a tourné), et n'ouvre une
  connexion que si un cookie de session est présent.

---

## 2. Comment le vérifier soi-même

```bash
# base de démonstration neuve (aucune donnée réelle)
createdb -h 127.0.0.1 -U pause ia_consultations_c6demo
cd src && DATABASE_URL=postgresql://pause@127.0.0.1:5432/ia_consultations_c6demo \
  ../.venv/bin/python -m app.storage.migrations up
cd .. && DATABASE_URL=postgresql://pause@127.0.0.1:5432/ia_consultations_c6demo \
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0002_jeu_demo_phase4.sql
# puis le compléteur (champs chiffrés + pièces) et le parcours (DCE → checklist → mémoire)

# l'application
cd src && DATABASE_URL=…c6demo MODELE_FOURNISSEUR=factice \
  ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8098

# la suite complète, sur une base de test privée (la base partagée est utilisée
# en parallèle par un autre lot — un run concurrent y fausse le verdict)
cd src && TEST_DATABASE_URL=postgresql://pause@127.0.0.1:5432/ia_consultations_test_c6 \
  ../.venv/bin/python -m pytest -q
```

Contrôles en une ligne (session ouverte) :

| Adresse | Attendu | Observé |
|---|---|---|
| `/` | JSON d'identification | `{"application":"ia-consultations-publiques",…}` |
| `/static/style.css` | `200 text/css` | `200 text/css; charset=utf-8` |
| `/cette-page-nexiste-pas` | page d'erreur du produit, `404`, HTML | `404 text/html; charset=utf-8` |
| `/api/v1/inconnu` | JSON de FastAPI | `{"detail":"Not Found"} [404]` |

---

## 3. Résultat de la suite de tests

```
$ cd src && TEST_DATABASE_URL=…/ia_consultations_test_c6 ../.venv/bin/python -m pytest -q
260 passed, 1 warning in 20.46s            # docs/RAPPORTS/captures-c6/pytest-suite-complete.txt
```

260 et non les 244 de la vérification L8 : **des tests ont été ajoutés depuis** par
les lots en cours (`test_web.py` notamment). Aucun test supprimé, aucun rouge.

**Rejoué le 01/10 à la clôture de la carte** (les lots `B1`/`B2` de `dev-back` ont
modifié des services entre-temps) :

```
$ cd /Users/pause/Projets/ia-consultations-publiques && MODELE_FOURNISSEUR=factice .venv/bin/python -m pytest -q
259 passed, 1 warning in 19.89s
```

259 et non 260 : ce sont les lots voisins qui ont fait bouger le compte, pas cette
carte (aucun de mes fichiers n'est concerné par l'écart). Aucun rouge.

**Ce que la suite a réellement attrapé** : le premier essai du gestionnaire 404
renvoyait `{"detail":"Not Found"}` sur toute réponse 404 d'API, ce qui effaçait le
message métier des routes de provisionnement.
`tests/test_provisionnement.py::test_bibliotheque_404_puis_parcours_complet_apres_provisionnement`
et `tests/integration/test_provisionnement_parcours.py::test_demarrage_de_zero_par_le_script_puis_l_api`
sont passés au rouge ; le gestionnaire délègue maintenant au gestionnaire JSON
d'origine de FastAPI pour `/api/…`, et les deux tests sont revenus au vert.

---

## 4. Point 3 — tranché par arbitrage (D11) : rien à coder

La carte exigeait de trancher **avant d'écrire du code** : « soit le bloc est
supprimé […], soit le critère 6 est reformulé et la décision est écrite dans
`docs/DECISIONS.md` ». L'arbitrage a été demandé (carte `t_18a19ff7`, `plan`) puis
rendu — **option 2 retenue** :

- `docs/DECISIONS.md` **D11** : le critère 6 est reformulé, les blocs repliés ne
  sont **pas** supprimés ;
- `docs/PLAN-PHASE-4.md` § 1.6 point 6 est réécrit en conséquence : « … ni
  d'identifiant interne **visible sans action de l'utilisateur** … sans déplier les
  blocs « Références techniques » ».

**Conséquence : aucun des huit blocs n'a été touché, et il n'y avait rien à
toucher.** Ils restent tels que livrés en L5a/L5b, fermés par défaut.

Faits vérifiés par exécution (blocs ouverts à la main, contenu exact relevé) :

| Écran | Contenu du bloc replié |
|---|---|
| `/consultations/{id}` | `Dossier b3d0ff50-… — statut analysee.` + empreinte SHA-256 `ca46cf7b…f101` |
| `/consultations/{id}/checklist` | fiche `d0000000-…-0004` (UUID) + les 5 codes de type de pièce |
| `/consultations/{id}/memoire` | UUID des 6 sections + noms de tables (`moyen_materiel`, `reference_chantier`, `effectif_metier`, `organigramme`, `chapitre_memoire`) + `[valide]`, `[expire]` |
| `/bibliotheque` | `Fiche de bibliothèque n° 1 — identifiant d0000000-…-0004` |
| `/bibliotheque/{famille}` | `Famille assurances — fiche d0000000-…-0004 — état « Socle complet (non relue) »` |
| `/bibliotheque/import` | les 8 noms de familles techniques + nombre de constats |
| `/consultations` | chemin d'un fichier de test (`src/tests/fixtures/dce_fictif.pdf`) |
| page d'erreur | code de réponse + détail technique |

**La tension est réelle et doit être tranchée, pas contournée** :

- `docs/PLAN-PHASE-4.md` § 1.6 : « aucun écran n'affiche de valeur technique, de
  jargon d'architecture, ni d'identifiant interne », contrôle fait « en ouvrant
  chaque page et en la regardant (capture d'écran) » ;
- `docs/DESIGN.md` § 5 : « tout ce qui est technique (identifiants, empreintes, noms
  de tables) est **replié** dans un bloc « Références techniques », fermé par défaut »
  et « aucune information utile n'est supprimée […] pas effacé ».

Les deux options que la carte posait sont rappelées pour mémoire :

1. **supprimer les blocs** (8 gabarits) et journaliser l'information technique côté
   serveur — le critère 6 tenu au sens strict, mais la règle de `DESIGN.md` § 5
   tombe ;
2. **reformuler le critère 6** et écrire la décision dans `docs/DECISIONS.md` —
   retenue (D11).

La décision appartient à `plan`, pas à `dev-web` ; elle est écrite, la carte
`t_18a19ff7` est traitée. **Aucun code ne reste à écrire sur ce point.**

### Contrôle live du 01/10 (texte visible, blocs repliés retirés)

`scripts/jeu-de-test/verifier_critere6.py` ouvre les 16 écrans servis par
l'application, **retire les `<details>`** puis cherche les crochets et les valeurs
de code dans ce qui reste. Sortie brute :
`docs/RAPPORTS/captures-c6/verif-live-critere6.txt` ; pages et textes extraits dans
`docs/RAPPORTS/captures-c6/verif-live/`.

```
OK        /accueil, /consultations, /consultations/{id}
OK        /consultations/{id}/checklist          ← le défaut principal : plus aucun crochet
OK        /bibliotheque, /bibliotheque/assurances, /bibliotheque/certifications
OK        /bibliotheque/import, /connexion, /cette-page-nexiste-pas
ANOMALIE  /consultations/{id}/memoire            ← codes du texte généré (dev-back, t_1c7d0532)
```

Le seul point rouge restant est **le texte produit du mémoire**, pas un défaut
d'affichage de cette carte : voir § 5.1.

---

## 5. Défauts voisins constatés, non corrigés ici

1. **Le texte du mémoire généré contient encore des codes.**
   `- Moyen matériel Groupe d'étanchéité à air chaud (materiel_mise_en_oeuvre) — …`,
   `Votre source : Groupe d'étanchéité à air chaud materiel_mise_en_oeuvre — Moyens
   matériels`, `(chef_equipe)`, `(engin_elevation)`, `(vehicule_chantier)`,
   `(materiel_chantier)`, `(conducteur_travaux)`, `(responsable_qse)`.
   Origine, dans `src/app/services/memoire_technique.py` (fichier de `dev-back`) :
   `_CHAMPS_LIBELLE` (`moyen_materiel: categorie_code`, `effectif_metier:
   metier_code`) alimente `libelle_source`, `_phrase_element` et `_lignes_element`.
   Ce n'est pas un défaut d'affichage : le code est **dans le contenu produit**.
   → carte séparée pour `dev-back` : **`t_1c7d0532`** (créée par cette carte, non
   fermée ici). Confirmation live du 01/10 : l'écran `/consultations/{id}/memoire`
   est le **seul** des 16 écrans à porter encore des codes dans le texte visible
   (`chef_equipe`, `conducteur_travaux`, `engin_elevation`, `materiel_chantier`,
   `responsable_qse`, `vehicule_chantier`).
2. **`CHECKLIST` : « pièces de la bibliothèque examinées : 0 »** alors que la même
   page compte 4 `presente`. Constaté sur le jeu L7 rejoué ; hors périmètre de cette
   carte (service `checklist`, lot `dev-back`), non instruit.

---

## 6. Preuves

Toutes dans `docs/RAPPORTS/captures-c6/` :

- **30 captures `avant-*` et 30 captures `apres-*`** : les **10 écrans** contrôlés,
  chacun en desktop **1280 px**, en mobile **390 px**, et une variante « bloc replié
  ouvert ». Les captures « avant » sont produites en servant une **copie exacte du
  code d'avant correction** (`avant-src/`, construite par retrait des cinq
  modifications listées au § 1) sur la **même base et le même jeu de données** que
  les captures « après » : l'écart observé ne vient que de la correction ;
- `textes-avant.json` / `textes-apres.json` : le texte visible de chaque page
  (et le contenu des blocs repliés), extrait par le navigateur — c'est ce que le
  balayage automatique confronte aux motifs « UUID », « empreinte », « code entre
  crochets », « nomenclature à underscores » ;
- `pytest-suite-complete.txt` : le journal de la suite ;
- `intermediaires/` : captures et extractions d'un premier passage sur la copie de
  la base de vérification L8, conservées mais **remplacées** par le jeu L7 rejoué.

Balayage avant / après (texte visible, hors blocs repliés) :

| Écran | Avant | Après |
|---|---|---|
| `/bibliotheque/assurances` | `responsabilite_civile_decennale`, `responsabilite_civile_professionnelle` | propre |
| `/bibliotheque/certifications` | `travaux_en_hauteur` | propre |
| `/bibliotheque/references_chantiers` | `etancheite_toiture_terrasse`, `etancheite_site_occupe` | propre |
| `/bibliotheque/moyens_materiels` | `materiel_mise_en_oeuvre`, `engin_elevation`, `vehicule_chantier`, `materiel_chantier` | propre |
| `/consultations/{id}/checklist` | `[attestation_assurance_decennale]`, `[attestation_assurance_professionnelle]`, `[attestation_bonne_execution]`, `[certificat_qualification]`, `[fiche_technique_produit]` | propre |
| `/consultations/{id}/memoire` | `materiel_mise_en_oeuvre`, `chef_equipe`, `conducteur_travaux`, `engin_elevation`, … | **inchangé** — défaut du générateur, § 5.1 |
| page inconnue | `{"detail":"Not Found"}` | page d'erreur du produit, `404 text/html` |

Aucun débordement horizontal : `documentElement.scrollWidth − clientWidth = 0`
sur les **dix écrans**, en 1280 px comme en 390 px.

**Re-vérification du 01/10** (état du code à la clôture de la carte, application
réellement servie sur `127.0.0.1:8098`, base de démonstration jetable
`ia_consultations_c6demo`) :

- `verif-live-critere6.txt` : sortie brute du balayage des 16 écrans ;
- `verif-live/` : le HTML et le **texte visible sans les blocs repliés** de chaque
  écran — c'est la pièce à lire pour juger le critère 6 ;
- `reverif-*.png` : 5 captures fraîches (checklist desktop + mobile, certifications
  desktop + mobile, page inconnue desktop), débordement mesuré à **0 px** ;
- `scripts/jeu-de-test/verifier_critere6.py` : le balayage, rejouable
  (`MOT_DE_PASSE_DEMO=… .venv/bin/python scripts/jeu-de-test/verifier_critere6.py`) ;
- `scripts/jeu-de-test/reinitialiser_mot_de_passe_demo.py` : pose un mot de passe
  connu sur l'utilisateur **de la seule base de démonstration jetable** (le script
  refuse toute base dont le nom ne contient pas `c6demo`), pour pouvoir ouvrir les
  écrans dans un navigateur. Aucun mot de passe n'est écrit dans les fichiers : il
  est lu dans la variable d'environnement `MOT_DE_PASSE_DEMO`.

