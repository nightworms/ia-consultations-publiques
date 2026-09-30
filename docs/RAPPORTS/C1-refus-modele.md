# C1 — une réponse de modèle refusée ne doit pas produire un 500

**Correctif livré et vérifié par exécution le 30/09/2026.**
Note courte : ce qui a changé, ce qui a été exécuté, ce qui reste ouvert.

---

## 1. Le fait, et ce qui le produisait réellement

Fait initial (test réel du 30/09/2026) : `POST /api/v1/consultations` renvoyait
`HTTP 500 Internal Server Error` sur un DCE analysé par un modèle réel, parce que
`ReponseModeleInvalide` (garde-fou anti-invention) remontait non gérée jusqu'à
FastAPI. La route ne rattrapait que `ErreurAnalyseDce`, dont cette erreur n'héritait
pas.

La reproduction **a montré un second défaut**, non décrit dans la fiche : le dépôt
était déjà **validé en base** au moment de l'échec. `creer_consultation()` et
`enregistrer_document_dce()` appelaient `connexion.valider()` (commit) avant que
l'analyse n'ait lieu, si bien que le `connexion.annuler()` du chemin d'erreur ne
pouvait plus annuler grand-chose.

Sortie réelle de la sonde **avant** correctif (fournisseur de test qui cite un
extrait absent du document) :

```
SONDE service — exception : ReponseModeleInvalide: Proposition non adossée au document : …
SONDE service — lignes avant={'consultation': 0, 'document': 0, 'extraction_element': 0}
                lignes apres={'consultation': 1, 'document': 1, 'extraction_element': 0}
SONDE http — statut=500 corps=Internal Server Error
SONDE http — lignes avant={'consultation': 0, 'document': 0, 'extraction_element': 0}
             lignes apres={'consultation': 1, 'document': 1, 'extraction_element': 0}
```

Deux constats : 500 opaque **et** deux lignes orphelines (`consultation`,
`document`). Les deux sont corrigés.

---

## 2. Ce qui a changé

| Fichier | Changement |
| --- | --- |
| `src/app/services/analyse_dce.py` | Nouvelle erreur applicative `AnalyseNonValidable` (hérite de `ErreurAnalyseDce`, porte `categorie` et `extrait_invoque`). `analyser_consultation` traduit tout `ReponseModeleInvalide` en `AnalyseNonValidable` : le refus est **conservé et expliqué**, jamais ignoré. `creer_consultation` / `enregistrer_document_dce` acceptent `valider=False` et `deposer_et_analyser` n'a plus qu'**un seul point de validation** (fin de l'analyse) : un échec annule donc réellement le dépôt, y compris le fichier chiffré écrit sur disque. |
| `src/app/services/fournisseur_modele/base.py` | `ReponseModeleInvalide` porte désormais `categorie` et `extrait` (information structurée pour l'appelant). Les contrôles de `verifier_propositions` sont **inchangés** : mêmes rejets, mêmes cas, message d'origine mot pour mot. |
| `src/app/api/routes_analyse.py` | La route rattrape `AnalyseNonValidable` **avant** `ErreurAnalyseDce` et répond `422` avec le message complet ; `connexion.annuler()` est appelé. Nouvelle dépendance `obtenir_fournisseur` (le fournisseur est injectable, donc testable sans réseau) passée explicitement au service. |
| `src/tests/test_refus_modele.py` | 4 tests : refus explicite, aucune ligne en base (vérifié par une connexion **séparée**), aucun fichier orphelin, aucun succès partiel, route `422` (et non `500`), chemin nominal préservé. |

La règle « aucune valeur sans source » n'est pas touchée : `verifier_propositions`
refuse toujours exactement ce qu'il refusait. Ce qui change est la **manière de
rendre le refus**, pas le refus.

---

## 3. Vérification réellement exécutée

### 3.1 Test automatisé — `.venv/bin/python -m pytest src/tests/test_refus_modele.py -v`

```
platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/pause/Projets/ia-consultations-publiques
collecting ... collected 4 items

src/tests/test_refus_modele.py::test_un_extrait_invente_est_refuse_sans_laisser_de_ligne PASSED [ 25%]
src/tests/test_refus_modele.py::test_le_refus_n_est_pas_converti_en_succes PASSED [ 50%]
src/tests/test_refus_modele.py::test_la_route_repond_422_et_non_500 PASSED [ 75%]
src/tests/test_refus_modele.py::test_la_route_accepte_toujours_une_analyse_valide PASSED [100%]
========================= 4 passed, 1 warning in 0.76s =========================
```

### 3.2 Suite complète — `.venv/bin/python -m pytest src/tests -q`

```
184 passed, 1 warning in 12.41s
```

Aucune régression : les 184 tests passent (dont les 23 tests d'intégration).

### 3.3 Appel HTTP réel (serveur uvicorn sur 127.0.0.1:8099 + `curl`)

Dépôt d'un DCE fictif (`src/tests/fixtures/dce_fictif.pdf`) avec un fournisseur
volontairement fautif, session ouverte par `POST /api/v1/connexion` :

```
HTTP/1.1 422 Unprocessable Entity
content-type: application/json
{"detail":"Le document a bien été reçu, mais l'analyse n'a pas pu être validée.
Proposition non adossée au document : l'extrait invoqué est introuvable dans le texte
extrait (catégorie 'piece_exigee'). Une valeur sans source n'est jamais acceptée.
Catégorie mise en cause : piece_exigee. Extrait invoqué, introuvable dans le document :
« ATTESTATION D'ASSURANCE DECENNALE — PASSAGE QUI N'EXISTE NULLE PART ».
Aucun élément n'a été enregistré : le dépôt a été annulé."}
```

État de la base **après** l'appel, lu par une connexion séparée :

```
BASE avant appel : {'consultation': 0, 'document': 0, 'extraction_element': 0}
BASE après appel : {'consultation': 0, 'document': 0, 'extraction_element': 0}
Fichiers chiffrés restants pour ce client : []
```

Le dépôt est donc bien annulé : aucune ligne, aucun fichier, aucune proposition
partielle.

---

## 4. Ce qui reste ouvert (assumé, non corrigé ici)

1. **Autres erreurs du fournisseur.** `ErreurFournisseurModele` (fournisseur mal
   configuré, appel réseau en échec) reste une erreur non rattrapée → toujours un
   `500`. C'est un incident d'infrastructure, distinct du refus du garde-fou ; il
   mériterait un `502`/`503` explicite, mais hors du périmètre de C1.
2. **Écran HTML (L5).** `app/web/routes_web.py` rattrape déjà `ErreurAnalyseDce` :
   comme `AnalyseNonValidable` en hérite, l'écran renvoie désormais `400` **avec le
   message complet** au lieu d'une erreur interne — mais il n'affiche pas de code
   sémantique distinct de « format refusé ». À uniformiser si souhaité.
3. **Fichier orphelin résiduel.** Si `enregistrer_document_dce` échoue *après*
   l'écriture du fichier (échec SQL, pas refus de modèle), l'identifiant du document
   n'est pas encore connu et le fichier n'est pas supprimé. Cas marginal, non vérifié.
4. **Contention de la base de test.** Trois workers dev-back tournaient en parallèle
   sur la **même** base `ia_consultations_test` et le **même** dossier de travail : un
   `deadlock detected` PostgreSQL a été observé en cours de vérification. Les preuves
   ci-dessus ont donc été produites sur une base dédiée
   (`ia_consultations_verif_c1`, via `TEST_DATABASE_URL`). À retenir pour la suite :
   `src/tests/conftest.py` est un point de collision entre lots.
