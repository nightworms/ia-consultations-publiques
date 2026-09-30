# L8 — Tests et vérification indépendante (rapport de lot)

*Lot **L8** — agent `qa`. Tâche `t_adc94993`. Écrit le 30 septembre 2026 à 12h24 (+04).*
*Workspace : `/Users/pause/Projets/ia-consultations-publiques`.*

Ce rapport ne remplace pas `docs/RAPPORT-TESTS-PHASE-3.md` (plan de test de la phase,
résultats complets, anomalies et réserves). Il contient les **commandes réellement
lancées** et leur **sortie réelle**, comme l'exige la convention de la phase 3.

---

## 1. Livrables

- `src/tests/integration/` — 7 fichiers, **23 tests** :
  - `conftest.py` — fixtures et outils communs ;
  - `test_isolation.py` — accès croisé refusé sur **chaque** table de contenu + routes ;
  - `test_ligne_rouge.py` — `origine`, `genere_ia`, `verifie` sans source, prix/marge ;
  - `test_invariants.py` — I1…I8 par comptage + contre-épreuve I6 ;
  - `test_migrations.py` — `up`/`down` de `0001`…`0004` sur base dédiée ;
  - `test_parcours_bout_en_bout.py` — parcours complet par l'API + contrat gelé ;
  - `test_provisionnement_parcours.py` — démarrage de zéro (script + API) ;
  - `test_fuite_et_perimetre.py` — contrôle de fuite et de périmètre.
- `docs/RAPPORT-TESTS-PHASE-3.md` — plan de test, résultats, anomalies, « non testé ».
- `docs/RAPPORTS/L8-sortie-pytest-integration.txt` — **sortie brute** de la suite d'intégration.
- `docs/RAPPORTS/L8-sortie-pytest-complet.txt` — **sortie brute** de la suite complète.

**Aucun fichier de code de production des lots 1 à 4 n'a été modifié.** Aucune
dépendance installée. Aucun déploiement, aucun port exposé.

---

## 2. Commandes et sorties réelles

### 2.1 Suite d'intégration du lot

```
$ cd src && ../.venv/bin/python -m pytest tests/integration -v -s
...
======================== 23 passed, 1 warning in 2.24s =========================
```

Extraits de sortie (détail complet dans le fichier joint) :

```
[isolation] tables couvertes avec données A : 28
[isolation] tables couvertes (vides chez A) : 6
[ligne rouge] colonnes examinées : 516
[ligne rouge] colonnes de prix/marge trouvées : []
[invariants] écarts par invariant : {'I1': 0, 'I2': 0, 'I3': 0, 'I4': 0,
  'I5': 0, 'I6': 0, 'I7': 0, 'I8': 0}
[migrations] tables après up complet : 38
[migrations] séquence up/down rejouée : 0001, 0002, 0003, 0004
[fuite] fichiers textuels examinés : 119
[fuite] motifs non expliqués : 0
[périmètre] occurrences hors-périmètre non justifiées : 0
[provisionnement] script : refus d'un mot de passe en argument (code 2), aucune fuite
```

### 2.2 Suite complète (lots précédents + L8)

```
$ cd src && ../.venv/bin/python -m pytest -q
...
167 passed, 1 warning in 10.98s
```

### 2.3 Vue détaillée (noms de tests)

```
tests/integration/test_isolation.py::test_acces_croise_refuse_sur_chaque_table_de_contenu PASSED
tests/integration/test_isolation.py::test_api_acces_croise_refuse_et_aucune_ecriture PASSED
tests/integration/test_isolation.py::test_client_id_du_corps_ignore_a_l_ecriture PASSED
tests/integration/test_ligne_rouge.py::test_schema_sans_champ_de_prix_ni_de_marge PASSED
tests/integration/test_ligne_rouge.py::test_api_refuse_une_valeur_sans_origine PASSED
tests/integration/test_ligne_rouge.py::test_base_refuse_une_valeur_sans_origine PASSED
tests/integration/test_ligne_rouge.py::test_api_refuse_origine_generee_par_ia PASSED
tests/integration/test_ligne_rouge.py::test_base_refuse_origine_generee_par_ia PASSED
tests/integration/test_ligne_rouge.py::test_api_refuse_confiance_verifie_sans_source PASSED
tests/integration/test_ligne_rouge.py::test_confiance_sans_source_reste_a_verifier PASSED
tests/integration/test_ligne_rouge.py::test_aucune_sortie_ne_dit_conforme PASSED
tests/integration/test_invariants.py::test_invariants_i1_a_i8_par_comptage PASSED
tests/integration/test_invariants.py::test_i6_detecte_reellement_une_validation_devenue_fausse PASSED
tests/integration/test_migrations.py::test_up_puis_down_de_chaque_migration PASSED
tests/integration/test_parcours_bout_en_bout.py::test_parcours_complet_de_bout_en_bout PASSED
tests/integration/test_parcours_bout_en_bout.py::test_bibliotheque_vide_signale_des_manques_sans_inventer PASSED
tests/integration/test_parcours_bout_en_bout.py::test_contrat_gele_non_renomme PASSED
tests/integration/test_parcours_bout_en_bout.py::test_routes_de_contenu_refusent_sans_session PASSED
tests/integration/test_provisionnement_parcours.py::test_demarrage_de_zero_par_le_script_puis_l_api PASSED
tests/integration/test_fuite_et_perimetre.py::test_controle_de_fuite_dans_le_depot PASSED
tests/integration/test_fuite_et_perimetre.py::test_aucun_secret_ni_fichier_sensible_versionne PASSED
tests/integration/test_fuite_et_perimetre.py::test_aucune_fonctionnalite_hors_perimetre_dans_le_code PASSED
tests/integration/test_fuite_et_perimetre.py::test_script_provisionnement_ne_fuit_aucun_secret PASSED
```

---

## 3. Exigences vérifiables du lot (annexe du plan) — état

| # | Exigence | État | Preuve |
|---|---|---|---|
| 1 | Suite exécutée réellement, sortie brute jointe | **fait** | § 2, fichiers joints |
| 2 | Isolation sur **toutes** les tables de contenu, accès croisé démontré en échec | **fait** | `test_isolation.py` (34 tables sondées, 28 avec données) |
| 3 | Invariants I1…I8 contrôlés par comptage, résultat joint | **fait** | `test_invariants.py` (zéro écart) |
| 4 | Contrôle de fuite (SIRET, IBAN, clés, mots de passe, en-têtes) — résultat joint | **fait** | `test_fuite_et_perimetre.py` (0 motif non expliqué) |
| 5 | Contrôle de périmètre (paiement, veille, pli, signature, tarifs) | **fait** | `test_fuite_et_perimetre.py` (0 occurrence non justifiée) |
| 6 | Tout test en échec rapporté comme échec | **fait** | aucun échec ; anomalies rapportées § 5 du rapport de phase |

Exigences propres à l'ajout de périmètre (commentaire de carte, § C2) :

| # | Contrôle | État | Preuve |
|---|---|---|---|
| 1 | Isolation sur l'**écriture** : 404, jamais 403, **aucune** ligne dans `fiche_version` | **fait** | `test_api_acces_croise_refuse_et_aucune_ecriture` (comptage avant/après) |
| 2 | `client_id` non fournissable par le corps HTTP | **fait** | `test_client_id_du_corps_ignore_a_l_ecriture` |
| 3 | Démarrage de zéro : script → connexion → `POST /entreprises` → `GET /bibliotheque` ≠ 404 | **fait** | `test_provisionnement_parcours.py` |
| 4 | Contrat gelé inchangé ; aucun secret ne fuit du script | **fait** | `test_contrat_gele_non_renomme`, `test_script_provisionnement_ne_fuit_aucun_secret` |
| 5 | Défaut constaté, pas corrigé | **fait** | § 5 du rapport de phase (A1…A5) |

---

## 4. Anomalies rapportées (détail en `docs/RAPPORT-TESTS-PHASE-3.md` § 5)

| # | Gravité | Résumé |
|---|---|---|
| A1 | majeur (infra de test) | `conftest.py` détruit/recrée les migrations sur une base unique (session) → suites parallèles non fiables |
| A2 | mineur (schéma) | le `CHECK` sur `origine` accepte `mixte` sur les tables de contenu |
| A3 | mineur (résiduel) | `fiche_version` sans contrainte croisée `(client_id, entreprise_id)` — parade applicative prouvée par test |
| A4 | majeur (règle A3/R9) | du SQL subsiste dans `services/authentification.py`, `analyse_dce.py`, `checklist.py` |
| A5 | mineur (couverture) | 6 tables de contenu sans chemin d'écriture au MVP — isolation prouvée au seul niveau du filtre SQL |

**Aucun constat bloquant.** Aucune faille de cloisonnement observée.

---

## 5. Ce qui n'a pas pu être testé

Voir `docs/RAPPORT-TESTS-PHASE-3.md` § 6. En résumé : fournisseur de modèle France/UE
réel (**sans clé d'API → non testé**), OCR sur scan dégradé réel, écrans HTML au niveau
navigateur, concurrence, DCE volumineux, sauvegarde/restauration, journalisation.

---

*Fin du rapport de lot L8 — `qa`.*
