# C3 — verrouiller l'extraction PDF par un test de non-régression

Date : 30/09/2026. Agent : `dev-back`. Tâche : `t_8fd87283`.

## 1. Ce que le lot devait faire

Le correctif du 30/09/2026 (retrait de `pdftotext -layout`, commit `7ee6980`) n'était
protégé par **aucun test**. Ce lot ajoute la protection, sans changer le comportement
d'extraction : **il verrouille, il ne redéfinit pas**.

## 2. Ce qui a été livré

| Fichier | Rôle |
|---|---|
| `src/tests/fixtures/generer_fixtures.py` | + `ecrire_pdf_deux_colonnes()` : produit `dce_fictif_deux_colonnes.pdf`, une page A4 avec un corps en colonne de gauche et des libellés de tableau à droite, **sur les mêmes lignes de base**. Bibliothèque standard seule, aucune dépendance nouvelle. |
| `src/tests/fixtures/dce_fictif_deux_colonnes.pdf` | La fixture générée (1 053 octets, une page). Document entièrement fabriqué, mention « DOCUMENT FICTIF ». |
| `src/tests/test_extraction_pdf_non_regression.py` | Deux tests de non-régression, plus le commentaire de cas réel et la limite connue. |

La fixture est **définie en code** plutôt que dans un `.txt` comme les autres :
les trois fixtures existantes sont du texte, celle-ci est une **mise en page**, et un
`.txt` ne sait pas l'exprimer. Le générateur est le seul endroit d'où elle peut sortir.

Aucun document d'acheteur, aucune donnée réelle : la fixture est écrite octet par octet
par le générateur (règle D10).

## 3. Preuves d'exécution

Toutes les commandes ci-dessous ont été lancées depuis la racine du projet.

### 3.1 La fixture reproduit bien le défaut (constat direct sur `pdftotext`)

    $ pdftotext -f 1 -l 1 -enc UTF-8 src/tests/fixtures/dce_fictif_deux_colonnes.pdf -

    DOCUMENT FICTIF — DEMONSTRATION — AUCUNE DONNEE REELLE
    Le candidat doit justifier de l'importance du
    personnel d'encadrement affecte au chantier,
    notamment pour la maitrise des delais.

    Effectifs moyens et importance
    Personnel d'encadrement

    $ pdftotext -layout -f 1 -l 1 -enc UTF-8 src/tests/fixtures/dce_fictif_deux_colonnes.pdf -

    DOCUMENT FICTIF — DEMONSTRATION — AUCUNE DONNEE REELLE

    Le candidat doit justifier de l'importance du   Effectifs moyens et importance
    personnel d'encadrement affecte au chantier,    Personnel d'encadrement
    notamment pour la maitrise des delais.

Avec `-layout`, le libellé `Effectifs moyens et importance` s'insère **entre « …du » et
« personnel d'encadrement »** : c'est exactement la corruption observée sur le DCE réel.
Sans `-layout`, la phrase reste d'un bloc.

### 3.2 Le test passe avec le correctif en place

    $ .venv/bin/python -m pytest src/tests/test_extraction_pdf_non_regression.py -v
    ============================= test session starts ==============================
    platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0 --
      /Users/pause/Projets/ia-consultations-publiques/.venv/bin/python
    cachedir: .pytest_cache
    rootdir: /Users/pause/Projets/ia-consultations-publiques
    plugins: anyio-4.15.1
    collecting ... collected 2 items

    src/tests/test_extraction_pdf_non_regression.py::test_la_phrase_du_corps_reste_contigue PASSED [ 50%]
    src/tests/test_extraction_pdf_non_regression.py::test_aucune_ligne_ne_melange_les_deux_colonnes PASSED [100%]

    ============================== 2 passed in 0.14s ===============================
    code de sortie pytest = 0

### 3.3 Le test échoue si `-layout` est réintroduit

`-layout` a été **réellement remis** dans la commande de `_texte_page`
(`src/app/services/extraction_pdf.py`) :

    $ python3  # ajout de "-layout" avant "-f"
    [-layout] reintroduit temporairement
    $ grep -n -A6 "pdftotext = _exiger_outil" src/app/services/extraction_pdf.py
    192:    pdftotext = _exiger_outil("pdftotext")
    193-    resultat = _executer(
    194-        [
    195-            pdftotext,
    196-            "-layout",
    197-            "-f", str(numero),
    198-            "-l", str(numero),

Puis :

    $ .venv/bin/python -m pytest src/tests/test_extraction_pdf_non_regression.py -v
    ============================= test session starts ==============================
    platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0 --
      /Users/pause/Projets/ia-consultations-publiques/.venv/bin/python
    cachedir: .pytest_cache
    rootdir: /Users/pause/Projets/ia-consultations-publiques
    plugins: anyio-4.15.1
    collecting ... collected 2 items

    src/tests/test_extraction_pdf_non_regression.py::test_la_phrase_du_corps_reste_contigue FAILED [ 50%]
    src/tests/test_extraction_pdf_non_regression.py::test_aucune_ligne_ne_melange_les_deux_colonnes FAILED [100%]

    =================================== FAILURES ===================================
    ____________________ test_la_phrase_du_corps_reste_contigue ____________________

        def test_la_phrase_du_corps_reste_contigue() -> None:
            """La phrase du corps ne doit pas être coupée par le libellé de la colonne voisine.

            Échoue si `-layout` est réintroduit dans `app/services/extraction_pdf.py`
            (fonction `_texte_page`) : la colonne latérale vient alors s'insérer entre
            « …du » et « personnel d'encadrement ».
            """
            texte = _normaliser(_page_unique().texte)
            assert LIBELLE_LATERAL in texte, (
                "la colonne latérale de la fixture n'a pas été lue : le test ne prouverait rien."
            )
            assert FIN_DU_CORPS in texte, "le corps de la fixture n'a pas été lu en entier."
    >       assert PHRASE_DU_CORPS in texte, (
                f"la phrase du corps a été coupée par la colonne voisine : « {PHRASE_DU_CORPS} » "
                f"est absente du texte lu. `-layout` a probablement été réintroduit dans "
                f"`app/services/extraction_pdf.py` (fonction `_texte_page`).\n"
                f"Texte lu : {texte!r}"
            )
    E       AssertionError: la phrase du corps a été coupée par la colonne voisine : « importance du personnel d'encadrement » est absente du texte lu. `-layout` a probablement été réintroduit dans `app/services/extraction_pdf.py` (fonction `_texte_page`).
    E         Texte lu : "DOCUMENT FICTIF — DEMONSTRATION — AUCUNE DONNEE REELLE Le candidat doit justifier de l'importance du Effectifs moyens et importance personnel d'encadrement affecte au chantier, Personnel d'encadrement notamment pour la maitrise des delais. "
    E       assert "importance du personnel d'encadrement" in "DOCUMENT FICTIF — DEMONSTRATION — AUCUNE DONNEE REELLE Le candidat doit justifier de l'importance du Effectifs moyens et importance personnel d'encadrement affecte au chantier, Personnel d'encadrement notamment pour la maitrise des delais. "

    src/tests/test_extraction_pdf_non_regression.py:78: AssertionError
    ________________ test_aucune_ligne_ne_melange_les_deux_colonnes ________________

        def test_aucune_ligne_ne_melange_les_deux_colonnes() -> None:
            """Aucune ligne lue ne doit porter à la fois du corps de texte et un libellé latéral.

            Formulation structurelle du même interdit : `-layout` aligne physiquement les deux
            colonnes, ce qui les fait cohabiter sur une même ligne de sortie.
            """
            lignes = _page_unique().texte.splitlines()
            melangees = [
                ligne
                for ligne in lignes
                if LIBELLE_LATERAL in ligne and "importance du" in ligne and len(ligne.strip()) > len(LIBELLE_LATERAL)
            ]
    >       assert not melangees, (
                "des lignes lues portent à la fois le corps de texte et la colonne latérale "
                f"— `-layout` a probablement été réintroduit : {melangees!r}"
            )
    E       AssertionError: des lignes lues portent à la fois le corps de texte et la colonne latérale — `-layout` a probablement été réintroduit : ["Le candidat doit justifier de l'importance du   Effectifs moyens et importance"]
    E       assert not ["Le candidat doit justifier de l'importance du   Effectifs moyens et importance"]

    src/tests/test_extraction_pdf_non_regression.py:102: AssertionError
    =========================== short test summary info ============================
    FAILED src/tests/test_extraction_pdf_non_regression.py::test_la_phrase_du_corps_reste_contigue
    FAILED src/tests/test_extraction_pdf_non_regression.py::test_aucune_ligne_ne_melange_les_deux_colonnes
    ============================== 2 failed in 0.22s ==============================
    code de sortie pytest = 1

Les deux tests détectent la réintroduction, et le message de panne **reproduit
littéralement** le défaut de production : « …l'importance du *Effectifs moyens et
importance* personnel d'encadrement… ».

### 3.4 Retour à l'état correct, vérifié

    $ cp <copie de sauvegarde> src/app/services/extraction_pdf.py   # puis
    $ git diff --stat -- src/app/services/extraction_pdf.py
    (aucune sortie — fichier identique à HEAD)
    $ .venv/bin/python -m pytest src/tests/test_extraction_pdf_non_regression.py -v
    ============================= test session starts ==============================
    platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0 --
      /Users/pause/Projets/ia-consultations-publiques/.venv/bin/python
    cachedir: .pytest_cache
    rootdir: /Users/pause/Projets/ia-consultations-publiques
    plugins: anyio-4.15.1
    collecting ... collected 2 items

    src/tests/test_extraction_pdf_non_regression.py::test_la_phrase_du_corps_reste_contigue PASSED [ 50%]
    src/tests/test_extraction_pdf_non_regression.py::test_aucune_ligne_ne_melange_les_deux_colonnes PASSED [100%]

    ============================== 2 passed in 0.14s ===============================
    code de sortie pytest = 0

### 3.5 Suite complète

La suite exige une base PostgreSQL. Les autres correctifs (C1, C2) tournaient en
parallèle dans le **même dossier de travail** et sur la **même base de test** : lancée
dans ces conditions, la suite a rendu `9 failed, 81 passed, 83 errors` — des erreurs
`psycopg` dues au chevauchement des migrations `down(999)`/`up()` de deux exécutions
simultanées, pas au présent lot.

Mesure propre, sur une base dédiée (variable `TEST_DATABASE_URL` déjà honorée par
`src/tests/conftest.py`), avec l'arbre de travail tel qu'il était :

    $ createdb ia_consultations_c3_verif
    $ TEST_DATABASE_URL="postgresql://<utilisateur>@127.0.0.1:5432/ia_consultations_c3_verif" \
        .venv/bin/python -m pytest src/tests -q
    ........................................................................ [ 41%]
    ........................................................................ [ 83%]
    .............................                                            [100%]
    ============================== warnings summary ===============================
    .venv/lib/python3.12/site-packages/fastapi/testclient.py:1
      .../fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with
      `starlette.testclient` is deprecated; install `httpx2` instead.
        from starlette.testclient import TestClient as TestClient  # noqa

    -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
    173 passed, 1 warning in 13.33s
    code de sortie = 0

173 = 167 avant ce lot + 2 tests ajoutés ici + 4 tests ajoutés par le correctif C1
encore non commité. La base dédiée a été supprimée après la mesure.

## 4. Limite connue, inscrite dans le test

Sur une page **réellement tabulaire**, l'ordre de lecture sans `-layout` peut présenter
les colonnes dans un autre ordre (les libellés peuvent remonter avant le corps, comme
le montre la sortie du § 3.1). Pour la vérification sourcée, ce qui compte est qu'aucune
phrase ne soit **corrompue** ; l'ordre, lui, n'est pas garanti. Ce compromis est retenu
sur un cas et devra être réévalué sur plusieurs DCE réels — c'est écrit en tête du
fichier de test, pour que le prochain lecteur ne le croie pas figé.

## 5. Ce qui reste

- Le compromis du § 4 n'est **pas** levé par ce lot : aucun DCE réel supplémentaire n'a
  été passé dans l'extracteur (et il n'y en a pas dans le dépôt, par construction).
- La concurrence de deux exécutions de tests sur la même base de test est un vrai
  défaut d'atelier (le correctif C2 en traite un aspect). Il n'est pas traité ici.

## 6. État du dépôt à la fin du lot

Fichiers ajoutés ou modifiés par ce lot :

- `src/tests/fixtures/generer_fixtures.py` (modifié)
- `src/tests/fixtures/dce_fictif_deux_colonnes.pdf` (ajouté)
- `src/tests/test_extraction_pdf_non_regression.py` (ajouté)
- `docs/RAPPORTS/C3-extraction-pdf-non-regression.md` (ce rapport)

`src/app/services/extraction_pdf.py` : **inchangé**, vérifié par `git diff` vide.
