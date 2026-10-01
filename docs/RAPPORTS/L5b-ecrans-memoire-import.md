# L5b — Écrans du mémoire technique et de l'import guidé

*Rapport du lot L5b (phase 4), écrit par l'agent `dev-web` le 30 septembre 2026,
**après exécution réelle** : application démarrée, parcours déroulé dans un
navigateur, une capture d'écran par état, en desktop **et** en fenêtre étroite.*

Fichiers écrits par ce lot (écrivain unique, `docs/PLAN-PHASE-4.md` § 2.E) :

| Fichier | Nature |
|---|---|
| `src/app/web/routes_web.py` | +5 routes d'écran, aides de rendu, vocabulaire métier |
| `src/app/web/templates/import_guide.html` | **nouveau** — écran d'import guidé |
| `src/app/web/templates/memoire.html` | **nouveau** — écran du mémoire technique |
| `src/app/web/static/style.css` | +`.carte--conseil`, `.manque*`, `.section-texte` |
| `src/tests/test_web.py` | +4 tests (routes gelées, verrou humain, isolation, boutons) |

Rien d'autre n'a été modifié : aucune route `/api/v1`, aucun service métier,
aucune migration, aucun `docs/Model de dossier de consultation/`.

---

## 1. Chemins gelés livrés

| Chemin | Ce que fait l'écran |
|---|---|
| `GET /bibliotheque/import` | dépôt, propositions à décider **une par une**, état d'avancement « ce qui vous manque pour être prêt à concourir » |
| `POST /bibliotheque/import` | **un seul chemin** : lire un document déposé (`action=analyser`) ou décider d'une proposition (`action=accepter|refuser`) |
| `GET /consultations/{id}/memoire` | mémoire généré, sections dans l'ordre des critères pondérés, sources citées, manques avec l'action à mener, validation, liens de téléchargement |
| `POST /consultations/{id}/memoire` | demande de génération |
| `POST /consultations/{id}/memoire/sections/{sid}` | relire / valider / remettre en relecture une section |
| `POST /consultations/{id}/memoire/validation` | validation nommée et horodatée (obligatoire avant export) |

Le **lien de téléchargement** pointe la route du lot L6
(`GET /consultations/{id}/memoire/export?format=md|docx`), déjà livrée et montée
par l'agrégateur `app.api.routes` ; L5b ne l'a pas modifiée.

---

## 2. Décisions prises par ce lot (et pourquoi)

1. **Import : un seul chemin POST pour les deux actes.** `POST /bibliotheque/import`
   lit le document *ou* décide d'une proposition, selon un champ `action` caché.
   Raison : § 2.D ne gèle que `GET/POST /bibliotheque/import` ; ajouter
   `/bibliotheque/import/propositions/{id}` aurait inventé un chemin hors liste.
   Le dépôt et la décision sont donc deux formulaires du même écran vers le même
   chemin — et **aucun `File(...)` obligatoire** dans la signature, sinon la
   décision (formulaire sans fichier) aurait été refusée en 422.
2. **Ordre d'enregistrement des routes.** `/bibliotheque/import` est déclaré
   **avant** `/bibliotheque/{famille}` : Starlette essaie les routes dans l'ordre de
   déclaration, et la route générique avalait l'écran d'import (404). Défaut trouvé
   à l'écran, corrigé, verrouillé par un test
   (`test_ecran_import_repond_200_et_ne_se_confond_pas_avec_une_famille`).
3. **« Corriger » une section = retour en relecture, pas réécriture libre du texte.**
   Le service `memoire_technique` n'expose aucune écriture de contenu de section,
   et c'est cohérent : le texte d'une section est composé de phrases dont **chaque
   valeur vient d'un élément cité** de la bibliothèque. Le réécrire librement
   détacherait l'argument de ses sources — précisément ce que la ligne rouge
   interdit. L'écran propose donc : *Marquer à corriger* (relue → brouillon), et
   pour corriger le fond, **corriger l'élément de bibliothèque** puis *Mettre à jour
   le mémoire*. Un bloc « Pourquoi ? » explique ce choix à l'utilisateur.
4. **Aucun nom de table ni d'entité à l'écran.** L'emplacement d'une source
   (`page 1 — entité « reference_chantier »`) est réécrit en français
   (« page 1 — entité « Référence de chantier » »), et l'emplacement des sources du
   mémoire est rendu par le **nom de la famille** de bibliothèque. Le détail
   technique reste dans « Références techniques », replié.
5. **Les champs de liaison documentaire sortent du formulaire.** Un champ dont la
   valeur est un identifiant de document n'est pas proposé à la saisie : il est
   rattaché automatiquement au document importé à l'acceptation. On ne tape pas
   d'identifiant interne.
6. **Un seul bouton d'action principale par écran** (`.btn--action`) :
   * *Lire ce document* quand aucune proposition n'attend ;
   * *Valider cette proposition* dès qu'une proposition attend ;
   * *Demander le mémoire technique* quand aucun mémoire n'existe ;
   * *Relire et valider* sur l'écran du mémoire (ancre vers la validation finale).
7. **Les manques ne sont jamais une erreur.** Bloc `.carte--conseil` accentué
   (bleu), pas d'encart rouge : constat, puis « Pour renforcer ce critère : … »,
   puis un lien direct vers la famille où l'information s'ajoute. Le critère de
   prix, hors périmètre du mémoire, l'explique sans lien d'ajout.
8. **Refus du garde-fou de source = conseil, pas panne.** La variante
   `ImportNonValidable` s'affiche en encart d'attention (« Ce document n'a pas pu
   être lu jusqu'au bout »), jamais en erreur rouge, et rien n'est enregistré.

---

## 3. Défauts trouvés à l'écran, et corrigés

| # | Défaut | Preuve | Correction |
|---|---|---|---|
| 1 | `/bibliotheque/import` répondait **404** : la route générique `/bibliotheque/{famille}` l'avalait | `captures-L5b/00-defaut-ordre-routes-404-avant-correction.png` | route déclarée avant la route générique + test de non-régression |
| 2 | Déposer un document levait **« Internal Server Error »** : le fournisseur configuré (`MODELE_FOURNISSEUR=ue`) n'implémente pas la lecture d'import, et l'écran ne rattrapait pas l'erreur du service | `captures-L5b/07-import-moteur-inactif-desktop.png` | `ErreurFournisseurModele` rattrapée : message lisible en français, aucun élément écrit |
| 3 | L'emplacement d'une proposition affichait `entité « reference_chantier »` — un nom de code | — | nom d'entité traduit en libellé métier |
| 4 | La progression de l'import affichait « Étape en cours » à l'étape 1 après une lecture | visible sur `03-import-proposition-desktop.png` puis corrigé | l'étape 1 est « Terminé » dès qu'un document a été lu |

Le défaut 2 est **le plus important pour la démonstration** : avec le `.env` du
projet tel quel, l'import guidé ne peut pas produire de propositions (le
fournisseur réel ne sait pas le faire, décision documentée par le lot L3). L'écran
le dit maintenant proprement, au lieu de tomber.

---

## 4. Parcours déroulé réellement (résultats observés, pas prévus)

Application lancée, navigateur piloté, compte **fictif** créé pour la démonstration
(`Sonde L5b — DÉMONSTRATION`, entreprise `Océan Étanchéité FICTIVE`) :

1. **Créer l'entreprise** depuis l'écran de première utilisation → bibliothèque
   vide, 9 familles à compléter.
2. **Importer deux documents fictifs** (écrits pour la démonstration, signalés
   FICTIF, hors dépôt) au format lisible par la brique d'import :
   * `reference-chantier-FICTIF-L5B.txt` → 1 proposition ;
   * `attestation-assurance-FICTIF-L5B.txt` → 1 proposition.
3. **Décider** : refus **sans nom** → refusé par le verrou (message « sans un humain
   nommé », aucune écriture) ; puis **accepter avec nom** → l'élément entre dans la
   bibliothèque (« Réfection de l'étanchéité des toitures-terrasses — groupe
   scolaire fictif Les Filaos », visible dans `/bibliotheque/references_chantiers`) ;
   le second document est **refusé** → « rien n'a été écrit dans votre
   bibliothèque ».
4. **Déposer un DCE fictif** (jeu de démonstration du lot L7) → 15 éléments lus,
   chacun avec sa source ; **accepter les 15** avec un nom → 0 « non vérifié ».
5. **Demander le mémoire technique** → **5 sections rédigées** (critères 40 %,
   20 %, 15 %, 10 %, 5 %), **1 critère sans référence** (§ « Moyens humains et
   matériels affectés au marché — 10 % »), chaque section portant « Votre source ».
6. **Relire les 5 sections** avec un nom → état du mémoire « En relecture »,
   5 relues / 0 validée ; chaque section affiche « le 30/09/2026 par … ».
7. **Valider avant relecture** → refus lisible ; **valider après relecture** avec
   nom + fonction → statut « Validé », empreinte du contenu enregistrée.
8. **Télécharger** : le lien `format=md` renvoie réellement un fichier —
   `200`, `Content-Disposition: attachment; filename="memoire-technique-…md"`,
   **5969 caractères**, commençant par `# Mémoire technique — …` avec
   l'avertissement de génération. Le lien `format=docx` est offert de la même façon.
9. **Deuxième consultation** (fixture `dce_fictif.pdf`, critères Prix 40 % /
   Valeur technique 35 % / Moyens humains et matériels 25 %) → le critère **Prix
   produit un manque**, avec son constat et son action, et **aucun lien d'ajout**
   (hors périmètre du mémoire) — c'est le cas R1 du plan, constaté à l'écran.

Contrôle final, sur les trois écrans L5b ouverts : **aucun UUID visible, aucun nom
de table, aucun nom de fournisseur de modèle, aucune référence d'annexe**. Le seul
« brouillon » qui subsiste est celui de la mention obligatoire du pied de page
(« Ce que vous produisez reste un brouillon — à relire et à signer »), exigée par
la phase 3.

---

## 5. Captures d'écran (une par état, desktop **et** mobile)

Dossier : `docs/RAPPORTS/captures-L5b/`. Fenêtre étroite : **390 px** ; desktop :
**1280 px**. Débordement horizontal mesuré à chaque prise : **0 px partout**.

| Capture | Ce qu'elle montre |
|---|---|
| `00-defaut-ordre-routes-404-avant-correction.png` | le défaut n° 1, avant correction |
| `02-import-vide-desktop.png` / `…-mobile.png` | écran d'import, aucune proposition : progression, dépôt, action principale |
| `03-import-proposition-desktop.png` / `…-mobile.png` | proposition à valider : source (document + emplacement), passage littéral, champs, décision nommée |
| `04-import-refus-sans-nom-desktop.png` | refus sans nom : le verrou humain tient |
| `05-import-decisions-desktop.png` / `…-mobile.png` | décisions prises (Acceptée / Refusée) + bloc « Ce qui vous manque pour être prêt à concourir » |
| `07-import-moteur-inactif-desktop.png` | défaut n° 2 corrigé : refus lisible au lieu d'une erreur 500 |
| `06-consultation-elements-acceptes-desktop.png` | l'analyse du DCE, éléments acceptés par un humain nommé |
| `10-memoire-avant-generation-desktop.png` / `…-mobile.png` | mémoire avant génération : action principale « Demander le mémoire technique » |
| `11-memoire-desktop.png` / `…-mobile.png` / `…-desktop-pleine-page.png` | mémoire généré : sections ordonnées, sources, manques, statuts métier |
| `12-memoire-pret-a-valider-desktop.png` | 5 sections relues : le formulaire de validation nommée apparaît |
| `13-memoire-valide-export-desktop.png` / `…-mobile.png` | mémoire validé : validation nommée horodatée et liens de téléchargement |
| `14-memoire-refus-validation-desktop.png` / `…-mobile.png` | refus de validation, message lisible (« section(s) encore en brouillon ») |
| `15-memoire-manques-fixture-desktop.png` / `…-mobile.png` | manques du critère Prix (40 %) et du critère sans référence, avec actions |

---

## 6. Tests

```
cd src && ../.venv/bin/python -m pytest -q
244 passed, 1 warning in 17.12s
```

* **185 tests de la phase 3 : verts** (non touchés).
* 55 tests de la phase 4 (lots L2, L3, L6 et les 4 nouveaux de ce lot).
* Les 4 tests ajoutés portent sur : la route gelée qui ne se confond pas avec une
  famille, l'import de bout en bout avec le **verrou de décision nommée**, la
  génération du mémoire et l'**isolation par client** (404 pour l'écran, la
  génération et la validation d'un autre client), et l'absence de bouton engageant
  sur les deux nouveaux écrans.

Isolation : le `client_id` vient exclusivement de la session ; un mémoire, une
section ou une proposition d'un autre client répond **404**, jamais 403, et aucune
de ses données n'est rendue (vérifié en test et par lecture du code des services).

---

## 7. Limites et points à savoir pour la démonstration (lot L8)

1. **Fournisseur de lecture.** Les propositions d'import n'existent qu'avec le
   fournisseur **factice** (`MODELE_FOURNISSEUR=factice`), comme pour l'analyse de
   DCE en phase 3. Le `.env` du projet porte `ue` : l'écran affiche alors le refus
   lisible du défaut n° 2, jamais une panne. Pour la démonstration, l'application a
   été lancée par un **harnais hors dépôt** qui source le `.env` puis force
   `MODELE_FOURNISSEUR=factice` — **le fichier `.env` n'a pas été modifié**. Le
   jeu de démonstration du lot L7 (`charger_demo_phase4.sh`) rencontre la même
   contrainte pour son étape 2.
2. **Les documents du jeu L7 ne sont pas au format lisible par l'import.**
   `scripts/jeu-de-test/fictif/*.txt` (plaquette, ancien mémoire, attestation)
   n'ont **pas** de blocs « Entité : … / - champ : valeur » : l'import en tire
   **zéro proposition**. Signalé par un commentaire sur la carte L5b (à arbitrer
   entre L3, L7 et L8) — ce n'est pas un défaut de l'écran, qui gère l'absence de
   proposition en le disant.
3. **L'extrait littéral montre les noms de champs** (`- intitule_operation : …`).
   C'est la conséquence du format lisible par le factice et du choix — imposé par
   la ligne rouge — d'afficher le **passage exact** du document. Un document réel
   n'aurait pas ces identifiants ; un vrai fournisseur les comprendrait.
4. **Action d'un manque** : quand un critère mobilise plusieurs familles, l'action
   affichée vient de la première famille de la priorité de preuve du lot L2 (par
   exemple « ajouter la qualification » pour un critère « moyens humains et
   matériels »). Le libellé est celui du service, jamais réécrit par l'écran.
5. **Un prix de référence de chantier peut apparaître dans le texte d'une section**
   (montant réel de la bibliothèque du client). Ce n'est pas un prix d'offre : le
   critère de prix ne produit jamais de section, et aucun montant d'offre n'est
   écrit nulle part.
6. **Traces laissées par la démonstration, à ne pas versionner.**
   `REPERTOIRE_DOCUMENTS` du `.env` vaut `verif-data/`, et **`verif-data/` n'est pas
   dans `.gitignore`** (seul `data/` l'est). Le jeu de démonstration L7 y a déjà
   laissé les pièces chiffrées de son compte (`verif-data/clients/d0000000-…/`) ;
   la démonstration L5b y a ajouté `verif-data/clients/7f8bed6a-…/` (4 documents
   chiffrés, **tous fictifs**). Ces blobs apparaissent donc en `git status` comme
   non suivis : à ne pas committer — ou à couvrir par le `.gitignore`, décision qui
   n'appartient pas à ce lot. La base de vérification garde par ailleurs le compte
   `l5b-demo@exemple.invalid` (fictif) et sa consultation : utile pour rejouer les
   écrans en vérification, sans effet sur un autre espace.

---

## 8. Relancer et regarder

```bash
# 1. le fournisseur FACTICE est requis pour que l'import produise des propositions
cd /Users/pause/Projets/ia-consultations-publiques
set -a; . ./.env; set +a; export MODELE_FOURNISSEUR=factice
cd src && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8099

# 2. ouvrir http://127.0.0.1:8099/connexion
```

Sans forcer le fournisseur (`bash demarrer.sh`), les écrans restent utilisables :
l'import affiche son refus lisible, le mémoire se génère et se valide normalement
(il ne dépend d'aucun appel de modèle).
