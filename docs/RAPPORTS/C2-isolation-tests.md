# C2 — La suite de tests ne dépend plus du fournisseur configuré

*Correctif **C2** — agent `dev-back`. Tâche `t_f521f1f5`. Écrit le 30 septembre 2026 (+04).*
*Projet : `/Users/pause/Projets/ia-consultations-publiques`. Board : `ia-consultations`.*

Ce rapport ne contient que des **commandes réellement lancées** et leurs **sorties
réelles**, copiées dans `docs/RAPPORTS/C2-1…C2-6-*.txt`.

---

## 1. Le défaut, reproduit avant toute modification

Le `.env` du projet contient un vrai fournisseur (`MODELE_FOURNISSEUR=ue`,
adresse OpenRouter). La suite était donc sensible à ce réglage.

**Commande** (depuis `src/`, correctif retiré) :

```
$ MODELE_FOURNISSEUR=ue MODELE_FOURNISSEUR_URL=https://openrouter.ai/api/v1/chat/completions \
  MODELE_FOURNISSEUR_CLE=<cle-fictive-de-test> MODELE_FOURNISSEUR_NOM=anthropic/claude-sonnet-5 \
  ../.venv/bin/python -m pytest tests/test_analyse_dce.py \
  -k "depot_pdf_fictif or route_depot_lecture" -q
```

**Sortie réelle** (`C2-1-avant-fix-ue-tests-cibles.txt`) :

```
FAILED tests/test_analyse_dce.py::test_depot_pdf_fictif_restitueles_trois_categories_avec_source
FAILED tests/test_analyse_dce.py::test_route_depot_lecture_et_validation - ap...
2 failed, 15 deselected, 1 warning in 1.02s
```

Les deux tests nommés dans la fiche échouent bien quand un fournisseur réel est
configuré, et passent avec `factice` : le constat de la fiche est confirmé.

**Ce que la fiche ne disait pas, et qui est plus grave** : sur la suite complète,
avec le même environnement, le pre-correctif ne se contentait pas de rougir —
**il sortait réellement sur Internet** :

**Sortie réelle** (`C2-2-avant-fix-ue-suite-complete.txt`) :

```
E  app.services.fournisseur_modele.base.ErreurFournisseurModele: Fournisseur France/UE
   (non précisé) en échec (HTTP 401). La clé et l'adresse ne sont jamais recopiées ici.
...
27 failed, 158 passed, 1 warning in 19.15s
```

Le `HTTP 401` est une **réponse d'un vrai service distant** : la suite a bien
envoyé une requête hors de la machine. La clé utilisée pour cette démonstration
était fictive, aucune clé réelle n'a été employée. Trente-sept tests verts avant
le premier rouge montrent aussi que le problème n'était pas isolé à deux cas
d'espèce : c'est toute la suite qui dépendait du `.env`.

*(Réserve de méthode : ce dépôt est un espace de travail **partagé** avec les
correctifs C1 et C3, travaillés en parallèle sur les mêmes fichiers produit et la
même base de test. Les chiffres ci-dessus valent pour l'arbre au moment du
passage ; ils ne prétendent pas être la photographie du dépôt gelé.)*

---

## 2. Ce qui a été fait

### 2.1 `src/tests/garde_isolation.py` (nouveau, 265 lignes)

Deux mécanismes, plus un verrou.

1. **Fournisseur imposé.** `forcer_fournisseur_factice()` force
   `MODELE_FOURNISSEUR=factice` et **retire** les variables du fournisseur réel
   (`_URL`, `_CLE`, `_NOM`, `_ORGANISME`, `_DELAI`) du processus de test. La
   valeur demandée par le `.env` est conservée dans `etat_fournisseur()["demande"]`
   pour la traçabilité, jamais utilisée. Une clé du `.env` local n'entre donc
   jamais dans le processus qui exécute les tests.
2. **Garde réseau.** `installer_garde_reseau()` pose une interdiction sur
   `socket.socket.connect`, `connect_ex`, `sendto`, `socket.create_connection` et
   `socket.getaddrinfo`. Toute cible qui n'est pas la machine elle-même lève
   `ReseauInterdit` avec un message qui dit quoi faire à la place
   (`httpx.MockTransport`, fournisseur `factice`). Blocage *et* de la résolution
   de nom : un nom d'hôte externe n'est même pas traduit en adresse.
3. **Verrou.** `verifier_isolation()` lève `pytest.UsageError` — la suite **ne
   démarre pas** — si `MODELE_FOURNISSEUR` n'est pas `factice`, si le forçage n'a
   pas été appliqué, ou si la garde réseau n'est pas posée. Le message explique
   pourquoi (non-reproductibilité, faux négatif, risque d'affaiblir les
   assertions, envoi d'un document à un service extérieur).

### 2.2 `src/tests/conftest.py` (modifié, +23 lignes)

À l'import, **avant tout import du produit** :

```python
import garde_isolation
garde_isolation.forcer_fournisseur_factice()
garde_isolation.installer_garde_reseau()

def pytest_sessionstart(session) -> None:
    garde_isolation.verifier_isolation()
```

### 2.3 `src/tests/test_isolation_fournisseur.py` (nouveau, 12 tests)

Verrouille les quatre propriétés, avec des cibles qui ne peuvent **pas** être
jointes par construction (RFC 5737 `192.0.2.1`, RFC 2606 `.invalid`) :

| Test | Ce qu'il prouve |
| --- | --- |
| `test_la_suite_impose_le_fournisseur_factice` | `MODELE_FOURNISSEUR` vaut `factice`, `creer_fournisseur()` rend le factice |
| `test_le_verrou_arrete_la_suite_si_le_fournisseur_change` | `verifier_isolation()` lève `pytest.UsageError` si l'environnement impose `ue` (cas provoqué pour de vrai) |
| `test_verifier_isolation_ne_se_plaint_pas_quand_tout_est_en_place` | le verrou ne bloque pas quand tout est en place |
| `test_la_configuration_reelle_du_fournisseur_n_entre_pas_dans_les_tests` | aucune variable `MODELE_FOURNISSEUR_*` du `.env` n'est présente (valeur jamais lue ni affichée) |
| `test_connexion_sortante_brute_refusee`, `test_socket_brut_sortant_refuse`, `test_envoi_udp_sortant_refuse` | connexion TCP brute, `connect` direct et envoi UDP refusés |
| `test_resolution_d_un_nom_externe_refusee` | `getaddrinfo` sur un nom externe refusé |
| `test_client_http_python_ne_peut_pas_sortir` | `httpx.post()` vers l'extérieur refusé |
| `test_un_fournisseur_ue_configure_ne_peut_atteindre_aucun_reseau` | même un `FournisseurUe` explicitement construit ne peut pas sortir |
| `test_le_bouclage_reste_autorise`, `test_le_poste_parle_toujours_a_postgresql` | PostgreSQL local reste joignable (la garde ne casse pas la base) |

**Les deux tests d'origine n'ont pas été touchés** : `src/tests/test_analyse_dce.py`
est inchangé (`git diff` vide sur ce fichier). Aucune assertion n'a été retirée ni
affaiblie. Aucune dépendance installée.

---

## 3. Vérification par exécution, dans les deux configurations

Les deux commandes ont été lancées depuis `src/`, l'une après l'autre, sans
redémarrer quoi que ce soit d'autre.

### 3.1 `.env` en `factice`

```
$ MODELE_FOURNISSEUR=factice ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 13.42s
```
*(sortie complète : `C2-3-apres-fix-env-factice.txt`)*

### 3.2 `.env` en `ue` — le vrai `.env` du projet, clé réelle comprise

```
$ set -a && . ../.env && set +a
$ echo "MODELE_FOURNISSEUR=$MODELE_FOURNISSEUR"
MODELE_FOURNISSEUR=ue
$ ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 12.31s
```
*(sortie complète : `C2-4-apres-fix-env-reel-ue.txt`)*

**Les deux verdicts sont identiques et verts.** C'est la propriété demandée : la
machine, son `.env` et sa clé ne décident plus du résultat. Aucune clé n'a été
affichée, recopiée dans un fichier ou envoyée nulle part : le `conftest` retire
ces variables avant le premier test, et l'absence est vérifiée par un test.

### 3.3 Preuve que la suite ne parle plus à personne : le canari

Un écouteur TCP en boucle locale a été placé **à la place du fournisseur**
(`MODELE_FOURNISSEUR=ue`, `MODELE_FOURNISSEUR_URL=http://127.0.0.1:8766/...`).
Toute utilisation du fournisseur configuré se serait présentée à lui.

```
$ bash …/canari_c2.sh
185 passed, 1 warning in 11.69s

--- journal du canari (…/canari.log) ---
canari en ecoute sur 127.0.0.1:8766
canari arrete
```
*(sortie complète : `C2-5-canari.txt`)*

**Zéro connexion reçue.** La suite passe entièrement sans jamais instancier le
fournisseur configuré — ce qui est plus fort qu'un test rouge attendu : il n'y a
même pas de tentative.

### 3.4 Les tests de verrouillage

```
$ ../.venv/bin/python -m pytest tests/test_isolation_fournisseur.py -v
12 passed in 0.14s
```
*(sortie complète : `C2-6-tests-de-verrouillage.txt`)*

### 3.5 Sans aucune variable de fournisseur

Troisième configuration, pour mémoire :

```
$ env -u MODELE_FOURNISSEUR ../.venv/bin/python -m pytest -q
185 passed, 1 warning in 12.34s
```

Un développeur sans `.env` du tout obtient donc exactement le même verdict.

---

## 4. Ce que je n'ai pas vérifié, et ce qui reste en doute

1. **Le bouclage reste autorisé** (`127.0.0.0/8`, `::1`, `localhost`, sockets
   UNIX). C'est un choix assumé : PostgreSQL local est indispensable à la suite.
   Conséquence : un test qui viserait *explicitement* un service local resterait
   possible. Un fournisseur externe, lui, est hors d'atteinte. Bloquer aussi le
   bouclage romprait la base de test ; ce n'est pas fait.

   **J'ai essayé le mode strict** (blocage de *toutes* les connexions, bouclage
   compris, sans toucher à la base) : la suite reste verte — 184 tests passent,
   seul mon test `test_le_bouclage_reste_autorise` tombe. Cela confirme que
   PostgreSQL est joint par `libpq` (C) et pas par le module `socket` de Python.
   Je ne l'ai pas retenu pour deux raisons : un service local reste un besoin
   légitime, et surtout cela viderait le canari de son sens — je préfère une
   garde qui laisse le canari *parler* (il prouve l'absence de tentative) à une
   garde qui l'empêche de parler et masque la différence entre « pas appelé » et
   « appel bloqué ».
2. **La garde protège les sockets de Python, pas la sortie réseau du C.**
   `psycopg` parle à PostgreSQL par `libpq` (bibliothèque C) : ses connexions ne
   passent pas par le module `socket` (confirmé par l'essai strict ci-dessus).
   Aucun test ne sort par un autre chemin
   (aucun autre client C n'est utilisé), mais la garde n'est pas une barrière
   système — c'est une barrière au niveau de la suite. Un `firewall` ou un
   `unshare -n` le seraient ; ce n'était pas demandé et je ne l'ai pas fait.
3. **Un run rouge non reproduit.** Sur douze passages de la suite complète, un
   seul a échoué (10 échecs, 81 erreurs) avec `relation "client" does not exist`
   sur les tests situés après le 37e. Deux passages identiques juste après ont
   été verts, puis six passages consécutifs verts. La cause la plus probable est
   l'**espace de travail partagé** : C1 et C3 exécutent leur propre suite en
   parallèle sur la *même* base `ia_consultations_test`, et une session qui
   annule ses migrations pendant qu'une autre tourne supprime les tables sous
   les pieds de la seconde. Je n'ai pas la preuve directe de cette concurrence
   (seulement la chronologie et le fait que les fichiers produit de C1/C3 ont
   changé pendant mon travail). **À retenir : la suite n'est pas sûre en
   exécution parallèle sur une base unique** — c'est un défaut distinct de C2.
4. **Le nombre de tests.** 185 tests collectés au moment des preuves, dont 12
   apportés par ce correctif. Six d'entre eux existaient déjà sous une autre
   forme dans `test_fournisseur_modele.py` (fournisseur par défaut, absence de
   socket du factice) ; je ne les ai ni déplacés ni supprimés.
5. **`MODELE_FOURNISSEUR_DELAI`** est aussi retiré du processus de test : c'est
   cohérent (variable du fournisseur réel) mais sans effet observable, le
   fournisseur factice ne l'utilisant pas.

---

## 5. Livrables

| Fichier | Nature |
| --- | --- |
| `src/tests/garde_isolation.py` | nouveau — forçage du fournisseur, garde réseau, verrou |
| `src/tests/conftest.py` | modifié (+23 lignes) — appelle le forçage, la garde et le verrou |
| `src/tests/test_isolation_fournisseur.py` | nouveau — 12 tests de verrouillage |
| `docs/RAPPORTS/C2-isolation-tests.md` | ce rapport |
| `docs/RAPPORTS/C2-1…C2-6-*.txt` | sorties brutes des six passages |

`src/tests/test_analyse_dce.py` : **non modifié** (vérifié par `git diff`).
Aucun secret, aucune clé, aucun appel réseau réel dans le dépôt.
