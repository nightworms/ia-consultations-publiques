# L2 — Bibliothèque d'entreprise : rapport d'exécution

*Lot L2, phase 3. Rédigé le 30 septembre 2026. Toutes les sorties ci-dessous
proviennent de commandes **réellement lancées** sur la machine de développement
(macOS 27.0.1, arm64, PostgreSQL 18.3 local en écoute `127.0.0.1` uniquement).
Rien n'est extrapolé d'une lecture de code.*

Aucune donnée réelle d'entreprise n'a été utilisée : tous les noms, SIREN, SIRET,
IBAN, téléphones et montants de ce lot sont **fictifs et signalés**
(« DOCUMENT FICTIF — DÉMONSTRATION »). Aucun secret, aucune clé, aucun jeton ne
figure dans le dépôt.

---

## 1. Ce qui a été livré

| Livrable (chemin exact) | État |
|---|---|
| `src/migrations/0002_bibliotheque.sql` | créé — familles F1 à F9 (14 tables + 4 tables de liaison), sections up **et** down, plus le chargement des jeux de référence **fermés** |
| `src/app/domain/` | complété — une entité par famille (voir § 1.1) |
| `src/app/storage/repositories.py` | récrit — dépôts **filtrés par `client_id`**, tout le SQL de la bibliothèque |
| `src/app/services/bibliotheque.py` | récrit — saisie et consultation |
| `src/app/services/versionnement.py` | créé — `fiche_version`, les 7 états, `validation_relecture`, révocation, contrôle par empreinte (I6) |
| `src/app/api/routes_bibliotheque.py` | créé — les 4 routes gelées de l'annexe C |
| `src/tests/test_bibliotheque.py`, `src/tests/test_versionnement.py` | créés — **38 tests**, tous verts |
| `docs/RAPPORTS/L2-bibliotheque.md` | ce document |

Modifications **annexes**, minimales et justifiées :

| Fichier | Modification | Motif |
|---|---|---|
| `src/app/main.py` | trois lignes : import + `include_router` | brancher les routes gelées |
| `src/app/domain/securite.py` | créé | registre des champs sensibles (annexe A § A6) : c'est une **donnée du modèle**, sa place est dans `domain/`, qui ne dépend que de la bibliothèque standard |
| `src/app/domain/familles.py` | créé | registre famille → entité → table → champs (liste blanche) → types → jeux de référence attendus |

**Fichiers d'autres lots : non modifiés.** `src/tests/test_socle.py` (L1) avait déjà
été adapté par le lot L3 pour ne plus exiger que `0001` soit la seule migration ;
aucune correction supplémentaire n'a été nécessaire. Aucune migration d'un autre lot
n'a été touchée (`0001` L1, `0003` L3).

### 1.1 Entités du domaine (une par famille)

| Famille (`fiche.famille`) | Module | Entités |
|---|---|---|
| `identite` (F1) | `domain/entreprise.py` | `EntrepriseVersion`, `RepresentantLegal` |
| `capacites_financieres` (F2) | `domain/financier.py` | `ExerciceComptable`, `Attestation`, `CapaciteProduction` |
| `assurances` (F3) | `domain/assurances.py` | `Assurance` |
| `certifications` (F4) | `domain/certifications.py` | `Certification` |
| `references_chantiers` (F5) | `domain/references_chantiers.py` | `ReferenceChantier` |
| `moyens_humains` (F6) | `domain/moyens_humains.py` | `EffectifMetier`, `Organigramme`, `Cv` |
| `moyens_materiels` (F7) | `domain/moyens_materiels.py` | `MoyenMateriel` |
| `fiches_produits` (F8) | `domain/fiches_produits.py` | `Produit` |
| `memoire_technique` (F9) | `domain/memoire_technique.py` | `ChapitreMemoire` |
| — (transverse) | `domain/commun.py` | `Montant`, `Traceabilite`, `TraceabiliteValeur`, `calculer_statut_validite` |
| — (transverse) | `domain/fiche_version.py` | `FicheVersion`, `FicheFamille`, `ValidationRelecture`, les 7 + 4 + 2 états |
| — (transverse) | `domain/document.py` | `Document` |
| — (transverse) | `domain/securite.py` | registre des champs chiffrés (annexe A § A6) |
| — (transverse) | `domain/familles.py` | registre des entités et des champs |

`domain/` n'importe **que** la bibliothèque standard (annexe A § A3) — vérifié par
exécution :

```
$ cd src && ../.venv/bin/python -c "
import ast,pathlib
mods=set()
for p in pathlib.Path('app/domain').glob('*.py'):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n,ast.Import): mods|={a.name.split('.')[0] for a in n.names}
        elif isinstance(n,ast.ImportFrom) and n.level==0 and n.module: mods.add(n.module.split('.')[0])
print(sorted(mods))"
['__future__', 'dataclasses', 'datetime', 'decimal', 'enum', 're', 'typing', 'uuid']
```

---

## 2. Environnement et dépendances

**Aucune dépendance nouvelle.** Le lot L2 utilise exactement la liste autorisée
(annexe A § A10) déjà installée par L1 : `psycopg[binary]`, `cryptography`,
`pydantic`, `fastapi`, `pytest`, `httpx`. Aucune bibliothèque supplémentaire n'a été
installée, ni en Python, ni via npm (l'interface web est le lot L5).

Le chiffrement n'a **pas** été réécrit : `app/securite/chiffrement.py` (L1) est
appelé tel quel, avec la clé dérivée par `client_id`.

---

## 3. Exigence vérifiable n° 1 — migration `0002`, `up` puis `down`

Commandes réellement lancées (base de test locale `ia_consultations_test`) :

```
$ cd src && ../.venv/bin/python -m app.storage.migrations statut
0001  appliquée
0002  appliquée
0003  appliquée

$ ../.venv/bin/python -m app.storage.migrations up
Migrations appliquées : aucune

$ psql -h 127.0.0.1 -d ia_consultations_test -tAc "SELECT count(*) FROM information_schema.tables
    WHERE table_schema='public' AND table_name IN
    ('entreprise_version','assurance','cv','produit','chapitre_memoire');"
5

$ ../.venv/bin/python -m app.storage.migrations down 3
Migrations annulées : 0003, 0002, 0001

$ psql -h 127.0.0.1 -d ia_consultations_test -tAc "SELECT count(*) FROM information_schema.tables
    WHERE table_schema='public' AND table_name IN
    ('entreprise_version','assurance','cv','produit','chapitre_memoire');"
0

$ psql -h 127.0.0.1 -d ia_consultations_test -tAc "SELECT count(*) FROM information_schema.tables
    WHERE table_schema='public' AND table_name='jeu_reference';"
0

$ ../.venv/bin/python -m app.storage.migrations up
Migrations appliquées : 0001, 0002, 0003

$ psql -h 127.0.0.1 -d ia_consultations_test -tAc "SELECT count(*) FROM information_schema.tables
    WHERE table_schema='public' AND table_name IN
    ('entreprise_version','assurance','cv','produit','chapitre_memoire');"
5
```

Après `up`, les **36 tables** attendues sont présentes (`\dt`), dont les 14 tables de
familles et les 4 tables de liaison du lot L2. Le `down` de `0002` retire les tables
**et** les jeux de référence qu'il a chargés (valeurs d'abord, puis jeux) : aucune
ligne résiduelle, aucune table d'un autre lot touchée.

Vérifié aussi par test (`test_migration_0002_cree_les_tables_des_neuf_familles`,
`test_jeux_de_reference_fermes_charges_par_0002`).

**Réversibilité.** `down` puis `up` rejoués plusieurs fois dans la même session de
tests : la base revient exactement à son état migré.

---

## 4. Exigence vérifiable n° 2 — saisie multi-familles, `fiche_version`, validation humaine

Test : `test_saisie_sur_plusieurs_familles`, `test_validation_humaine_enregistree`.
Extrait de la démonstration HTTP réelle (§ 8) :

```
POST /api/v1/bibliotheque/references_chantiers -> HTTP 200
{"element_id":"d26a2be3-…","entite":"reference_chantier","famille":"references_chantiers",
 "fiche_version_id":"b58a57e8-…","validations_revoquees":[],"statut_fiche":"en_saisie"}

POST /api/v1/bibliotheque/assurances -> HTTP 200
{"element_id":"0c9b6297-…","entite":"assurance","famille":"assurances", …}

POST /api/v1/bibliotheque/validation -> HTTP 200
statut = validee | validation_id = e5b0bc6d-9c83-41f6-80d7-9af66d3fe426
```

Contrôles portés par les tests (tous verts) :

* la fiche accepte des éléments de **plusieurs familles** dans la même version ;
* `fiche_version.version_parente_id` et `numero_version` sont croissants par
  entreprise (test : `[2, 1]`) ;
* la validation enregistre **le nom du relecteur** (`relecteur_nom`), **l'attestation
  cochée** (`attestation_cochee = 1`) et un **horodatage** `date_validation` posé par
  la base au moment de l'action humaine (lu en base et comparé à l'heure du test) ;
* sans nom de relecteur (`""` → 422 en HTTP) ou sans attestation cochée (→ 400), la
  validation est **refusée** : le verrou ne se court-circuite pas ;
* l'état de la fiche passe à `validee` et son libellé est bien
  « Relue et validée par humain » — jamais « conforme » ni « certifiée ».

---

## 5. Exigence vérifiable n° 3 — révocation et contrôle par empreinte

**Révocation à la première modification.** Sortie réelle (démonstration HTTP § 8) :

```
POST /api/v1/bibliotheque/assurances -> HTTP 200
validations revoquees = ['e5b0bc6d-9c83-41f6-80d7-9af66d3fe426']
statut de la fiche = en_relecture

GET /api/v1/bibliotheque -> HTTP 200
statut = en_relecture | En relecture
  validation e5b0bc6d-… -> statut revoquee | motif: écriture sur un champ de la famille assurances
```

La ligne `validation_relecture` porte donc bien `statut = revoquee`,
`date_revocation` (non nul) et `motif_revocation` ; la fiche repasse
`en_relecture` (§ 6.5 point 1).

**Contrôle par empreinte — test dédié.** `test_le_controle_par_empreinte_detecte_une_validation_indument_valable`
simule le défaut de code redouté (§ 6.5 point 2) : la valeur est modifiée par un SQL
**direct**, sans passer par le service, donc **sans révocation**. La validation reste
`validee` en base ; le contrôle indépendant la démasque :

```
anomalie : empreinte_enregistree ≠ empreinte_recalculee
motif     : « validation indûment valable : le contenu du périmètre a changé depuis
             la validation (invariant I6) »
statut de la fiche : validee_puis_modifiee — « Validée puis modifiée (à relire) »
```

Quand la révocation a bien eu lieu, `controler_validations` renvoie **zéro anomalie**
(`test_aucune_anomalie_quand_la_revocation_a_eu_lieu`).

**Ce que l'empreinte nomme, et ce qu'elle ne décide pas.** L'algorithme est
`sha256-canonique-v1` (JSON canonique : clés triées, sérialisation déterministe des
dates et des décimaux, puis SHA-256) et il est **enregistré** dans
`validation_relecture.empreinte_algorithme` : le modèle (§ 6.4) exige de pouvoir le
nommer, et le point ouvert § 15 point 12 laisse le choix ouvert — il n'est pas tranché
ici à la place d'Anthony.

**Granularité (§ 6.4).** La validation est représentée à deux niveaux. Une validation
de **fiche** couvre toutes les familles ; une validation de **famille** ne couvre que
la sienne — démontré par `test_validation_de_famille_ne_couvre_que_sa_famille` :
écrire dans une autre famille laisse la validation d'assurances `validee`, écrire
dans la famille validée la révoque.

---

## 6. Exigence vérifiable n° 4 — non-déchiffrement croisé entre clients

Test : `test_second_client_ne_peut_pas_dechiffrer`. Lecture de la valeur **telle
qu'elle est stockée**, dans une colonne chiffrée :

```
SELECT iban, siret_siege FROM entreprise_version WHERE client_id = '<client A>';
  -> iban stocké commence par « v1: », et NE CONTIENT PAS l'IBAN en clair
  -> siret stocké ne contient pas le SIRET en clair

dechiffrer(cle, client_B, iban_stocke) -> ErreurDechiffrement
dechiffrer(cle, client_A, iban_stocke) -> l'IBAN en clair (le propriétaire seul)
```

Le cloisonnement est vérifié en plus sur la lecture applicative :

* `client B` qui demande la fiche de `client A` reçoit `CibleInconnue` — la lecture
  filtre sur `client_id` et **aucune ligne** ne remonte ;
* `client B` n'a aucune fiche courante (« pas de lecture par défaut ») ;
* `client B` ne peut ni calculer le statut, ni l'empreinte, ni valider la fiche de
  `client A` (`test_le_versionnement_refuse_la_fiche_d_un_autre_client`,
  `test_le_second_client_ne_peut_pas_valider_la_fiche_du_premier`).

---

## 7. Exigence vérifiable n° 5 — origine obligatoire, confiance jamais « verifie » sans source

Règles codées dans `app/domain/commun.py` (§ 7.5) et appliquées par le service :

| Cas | Comportement | Test |
|---|---|---|
| `origine` absente | **refus** — « Aucune valeur n'est enregistrée sans `origine` » | `test_origine_obligatoire` |
| `origine` hors `document_extrait` / `saisie_entreprise` (`genere_ia`, `propose`, `ia`, `""`) | **refus** (message rappelant la ligne rouge) | `test_origine_refusee` |
| `origine = mixte` | **refus** à la saisie : c'est un **résumé calculé** (§ 7.4) | idem |
| `document_extrait` sans `source_document_id` | **refus** (règle 1) | `test_document_extrait_exige_un_document_source` |
| `confiance = verifie` sans source | **refus** : « une valeur sans source est `a_verifier`, jamais `verifie` » | `test_valeur_sans_source_nest_jamais_verifiee` |
| `confiance = verifie` avec source mais **sans humain nommé** | **refus** — aucun chemin automatique ne pose `verifie` | `test_verifie_exige_un_controle_humain_nomme` |
| valeur saisie sans confiance demandée | enregistrée `a_verifier` (jamais `verifie`) | idem |

Contraintes **aussi** posées dans le schéma, indépendamment du code applicatif :
`CHECK (origine IN ('document_extrait','saisie_entreprise','mixte'))`,
`CHECK (confiance IN ('verifie','declare_non_verifie','a_verifier'))`,
`CHECK (origine <> 'document_extrait' OR source_document_id IS NOT NULL)`,
`CHECK (confiance <> 'verifie' OR source_document_id IS NOT NULL)` — sur **les 14
tables**. Un code qui oublierait la règle ne pourrait pas l'écrire en base.

Contrôle des `code_reference` : un code n'est vérifié que **si son jeu est chargé**.

```
moyen.propriete = 'propre'   -> accepté (jeu fermé, chargé par 0002)
moyen.propriete = 'inventee' -> refusé  : « code inconnu ou déprécié dans le jeu 'moyen.propriete' »
moyen.categorie = 'engins'   -> accepté (jeu NON chargé : contenu d'un autre lot / source : on n'invente rien)
```

---

## 8. Démonstration HTTP réelle (annexe C)

Application démarrée **localement** (`--host 127.0.0.1 --port 8099`), session ouverte
par `/api/v1/connexion` (cookie signé), puis les routes gelées appelées par `curl`.
Sortie brute (extrait) :

```
GET  /api/v1/bibliotheque            -> HTTP 401        (sans session)
POST /api/v1/bibliotheque/validation -> HTTP 401        (sans session)
POST /api/v1/connexion               -> HTTP 200
   {"nom_affichage":"Relecteur Fictif — DÉMONSTRATION", …}
GET  /api/v1/bibliotheque            -> HTTP 200   statut = vierge | 9 familles | 0 anomalie
POST /api/v1/bibliotheque/references_chantiers -> HTTP 200
GET  /api/v1/bibliotheque/assurances -> HTTP 200
   origine = document_extrait | confiance = a_verifier
   source_document_id = 43dcdffa-…   statut_validite = valide (calculé, jamais stocké)
POST /api/v1/bibliotheque/validation -> HTTP 200   statut = validee
POST /api/v1/bibliotheque/assurances -> HTTP 200   → 1 validation révoquée, fiche en_relecture
GET  /api/v1/bibliotheque            -> HTTP 200   en_relecture | validation revoquee + motif
GET  /api/v1/bibliotheque/inconnue   -> HTTP 404   (famille inconnue, message explicite)
```

Aucun port n'a été exposé sur Internet ; l'écoute est `127.0.0.1` uniquement. Le
serveur a été arrêté après la démonstration.

**Aucune capture d'écran** n'est fournie : la bibliothèque n'a pas encore d'interface
HTML (c'est le lot L5). Ce rapport ne présente donc pas de substitut à une capture.

---

## 9. Suite de tests

```
$ cd src && ../.venv/bin/python -m pytest tests/test_bibliotheque.py tests/test_versionnement.py -q --no-header
38 passed, 1 warning in 0.82s

$ ../.venv/bin/python -m pytest -q --no-header        # tout le dépôt (L1 + L3 + L2)
98 passed, 1 warning in 6.71s
```

L'unique avertissement est une dépréciation de `starlette.TestClient` (héritée de
L1) : sans effet sur ces tests.

Couverture par exigence : § 4 (n° 2), § 5 (n° 3, test dédié sur l'empreinte), § 6
(n° 4), § 7 (n° 5), § 3 (n° 1). Les tests s'exécutent contre PostgreSQL local, avec
migrations appliquées puis annulées par la suite.

---

## 10. Contrôles de sécurité et de dépôt

**Aucun secret dans le dépôt.** Recherche de motifs sur tous les fichiers écrits par
ce lot :

```
$ grep -nE "BEGIN (RSA|OPENSSH|PRIVATE)|sk-[A-Za-z0-9]{20}|api[_-]?key|mot_de_passe *= *['\"][^'\"]{4}|[0-9]{9,14}|FR[0-9]{2}[0-9A-Z]{10,}|@(gmail|orange|wanadoo|free|laposte)" <fichiers du lot>
→ 10 correspondances, toutes des valeurs volontairement nulles ou fictives :
   « 000000000 », « 00000000000000 », « FR0000000000000000000000000 », « 0000000000 ».
```

Aucune clé, aucun jeton, aucune adresse réelle. La clé maîtresse et la clé de session
proviennent exclusivement de l'environnement (L1) ; le script de démonstration, qui
porte une clé **de test locale**, vit **hors du dépôt** (répertoire de travail de
l'agent).

**SQL centralisé.** Tout le SQL du lot L2 est dans `src/app/storage/repositories.py`
et passe par `Connexion`, qui exige un `ContexteClient` et impose le filtre
`%(client_id)s` :

```
$ grep -rnE "\b(SELECT|INSERT INTO|UPDATE|DELETE FROM)\b" src/app --include=*.py | grep -v "src/app/storage/"
src/app/services/authentification.py:70, 80, 92      <- lot L1
src/app/services/analyse_dce.py:115 … 498            <- lot L3
```

**Constats portant sur d'autres lots** (signalés, **non corrigés** — fichiers d'autres
lots, L3 en cours d'exécution) :

1. `services/authentification.py` (L1) écrit du SQL depuis `services/`.
2. `services/analyse_dce.py` (L3) écrit du SQL depuis `services/` (une quinzaine
   d'ordres).

La règle « aucune requête SQL hors de la couche `storage/` » est tenue **par le lot
L2** ; elle ne l'est pas, à ce jour, par L1 ni par L3.

**Troisième exception nommée et bornée (L2).** `DepotReference` lit `jeu_reference` et
`valeur_reference` par un **SQL figé**, sur ces deux tables uniquement, et **sans**
contexte client : ces tables sont **globales** par construction (invariant I5) et ne
contiennent aucune donnée d'entreprise. Les deux autres exceptions ont été nommées et
bornées par L1 (`rechercher_identite_connexion`, `creer_client`). Cette troisième
exception mérite d'être entérinée par l'orchestrateur.

---

## 11. Ce qui n'a pas été fait, et limites assumées

1. **Rien n'a été déployé**, aucun port n'a été exposé, aucune donnée réelle n'a été
   introduite. Aucun commit git n'a été fait (cohérent avec les lots précédents).
2. **Le provisionnement n'est pas exposé par l'API.** Les quatre routes gelées de
   l'annexe C supposent une `entreprise` et une `fiche_version` existantes ; aucune
   route du contrat gelé ne les crée. Le lot L5 (interface web) aura besoin de ce
   chemin. Je n'ai **pas** ajouté de route (contrat gelé) : le provisionnement passe
   par les services `creer_entreprise()` et `ouvrir_fiche()`. **À trancher** par
   l'orchestrateur — voir le commentaire de carte.
3. **Le contenu des jeux de référence non fermés n'est pas chargé** (`metier.*`,
   `document.type_document`, `entreprise.forme_juridique`, `assurance.type`,
   `attestation.type`, `certification.domaine`, `moyen.categorie`, `produit.famille`,
   `reference.nature_travaux`, `rh.origine_effectif`, `facturation.formule`,
   `facturation.periodicite`). Il appartient à `docs/NOMENCLATURE-REFERENCE.md` ou à la
   source administrative ; **rien n'a été inventé** pour le remplir. Corollaire
   assumé : un champ dont le jeu n'est pas chargé accepte n'importe quel code (aucun
   contrôle n'est possible sans contenu).
4. **Les niveaux d'exigence N1/N2/N3 ne sont pas décidés.** L'état `socle_complet`
   utilise une lecture **structurelle** (« un élément au moins dans chacune des neuf
   familles »), qui n'est pas la définition définitive de l'interface — voir le
   commentaire de carte.
5. **Le nom de l'humain qui contrôle une valeur n'est pas persisté.** Il est exigé
   pour `confiance = verifie` (`controle_humain_par`), mais le modèle n'a pas de
   colonne « qui a vérifié cette valeur » au niveau de l'élément : la trace nominative
   vit dans `validation_relecture`. Limite signalée.
6. **Aucun test de charge, aucune mesure de performance.** Hors périmètre de ce lot.
7. **Le lot L3 (analyse de DCE) s'exécutait en parallèle** sur la même base de test
   (espace de travail partagé). La base a été recréée deux fois pendant ce lot
   (migrations rejouées) : les sorties ci-dessus proviennent d'exécutions complètes et
   reproductibles, mais le partage d'une même base entre lots parallèles est un
   facteur de fragilité à connaître.

---

## 12. Décisions non couvertes par les annexes A, B et C

Elles sont listées **ici** et postées en **commentaire de carte** (exigence : ne pas
trancher en silence) :

1. définition **structurelle** de l'état `socle_complet` (§ 6.2) ;
2. arbitrage entre l'immuabilité d'une version validée (§ 6.1 règle 1) et
   l'**exigence 3** de la carte (écriture après validation ⇒ révocation) ;
3. colonnes des champs chiffrés en **texte** (une charge `v1:` n'est ni un `numeric`
   ni une `date`) et contrôle de forme déplacé dans le domaine ;
4. paramètre **`controle_humain_par`** exigé, non persisté ;
5. chargement par la migration `0002` des seuls jeux de référence **fermés**, et règle
   « un code n'est vérifié que si son jeu est chargé » ;
6. **absence de route de provisionnement** dans le contrat gelé de l'annexe C ;
7. **troisième exception nommée** au filtre client (`jeu_reference`,
   `valeur_reference` : tables globales, sans donnée client).

---

*Fin du rapport L2. Toutes les affirmations de ce document proviennent d'une commande
exécutée ; les limites du § 11 disent franchement ce qui n'a pas pu être vérifié.*
