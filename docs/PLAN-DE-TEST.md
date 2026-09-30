# PLAN-DE-TEST — Plan de test de la phase 1

*Lot L6 — agent `qa`. Phase 1 = cadrage et squelettes.
Board : `ia-consultations`. Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*

> **Ce document ne teste pas une application.** La phase 1 ne livre aucun produit fini :
> elle produit des documents de cadrage et un squelette de code dont les points d'entrée
> lèvent `NotImplementedError`. Les vérifications ci-dessous portent donc sur
> **la conformité, la cohérence, la traçabilité et l'hygiène du cadrage**, plus quelques
> vérifications techniques sur l'état du squelette. Les vérifications qui portent sur des
> fonctionnalités (analyse de DCE, checklist, interface) **doivent échouer aujourd'hui** :
> c'est le résultat attendu en phase 1, pas un défaut.

---

## 1. Objet et périmètre

### 1.1 Ce que ce plan vérifie

| Axe | Section | Objet |
|---|---|---|
| A | § 3 | **Périmètre** : chaque livrable reste dans le MVP, n'empiète pas sur le hors-périmètre |
| B | § 4 | **Cohérence entre livrables** : modèle ↔ spécification ↔ interface |
| C | § 5 | **Ligne rouge** : toute affirmation pointe vers une source ; aucun chiffre / référence / garantie non sourcé |
| D | § 6 | **Traçabilité et échéances** : source de chaque information, dates de validité |
| E | § 7 | **Fuites de données** : données réelles, secrets, exemples non signalés |
| F | § 8 | **Relecture humaine bloquante** : décrite comme blocage technique |
| G | § 9 | **Chemins de fichiers et présence des livrables** ; état du squelette `src/` |
| H | § 10 | **Ce qui doit échouer aujourd'hui** (produit non construit) |

### 1.2 Livrables relus pour établir ce plan

- `PROJECT.md`, `README.md`, `docs/PLAN.md` — cadrage racine ;
- `docs/SPEC-MVP.md` (408 lignes) — lot L1 ;
- `docs/DATA-MODEL.md` (523 lignes) + `src/` — lot L2 ;
- `docs/UI-SAISIE.md` (674 lignes) — lot L3 ;
- `docs/CONFORMITE-COMMANDE-PUBLIQUE.md`, `docs/DONNEES-METIER-BATIMENT.md` — lots L4/L5, relus pour la cohérence croisée, **hors du périmètre de dépendance de ce lot** (L6 ne dépend que de L1/L2/L3).

### 1.3 Outils autorisés

Toutes les méthodes décrites sont réalisables avec des outils sans dépendance externe :
lecture ciblée de fichier, recherche de motif (`grep -nE`, `grep -rnoE`), comptage,
`git status`, `python3 -m compileall`, `python3 -c "import …"`. **Aucune installation,
aucun déploiement, aucun appel réseau.**

### 1.4 Conventions de numérotation

Chaque vérification porte un identifiant `V-A1`, `V-B3`, … La colonne **Statut au
30/09/2026** donne le résultat **réellement observé lors de la rédaction de ce plan**
(les commandes de la colonne « Méthode » ont été exécutées). Les valeurs : `OK`
(vérification passée), `ÉCHEC` (défaut constaté), `ATTENDU` (l'échec est normal en
phase 1).

---

## 2. Méthode générale

```bash
cd /Users/pause/Projets/ia-consultations-publiques
# présence et taille des livrables
ls -la docs/ ; find src -type f | sort
# recherche d'un motif dans les docs
grep -rniE "<motif>" docs/*.md
# squelette : non-exécutabilité attendue
python3 -m compileall -q src
python3 -c "from app.main import main; main()"   # doit lever NotImplementedError
git status --short
```

Pour chaque vérification : **critère de succès**, **critère d'échec**, **statut constaté**.

---

## 3. Axe A — Conformité au périmètre du MVP

Le périmètre du MVP (`PROJECT.md` § 7, `README.md`) = 3 briques : bibliothèque
d'entreprise, analyse d'un DCE déposé, checklist de conformité.
Hors-périmètre = mémoire technique **rédigé automatiquement**, veille / détection
d'appels d'offres, dépôt de pli, signature électronique, connexion aux plateformes
d'achat, chiffrage / prix / marge, authentification multi-utilisateurs, paiement,
facturation, mise en production.

### V-A1 — Le hors-périmètre est nommé dans chaque livrable
**Méthode.** `grep -nE "hors[- ]périmètre|hors périmètre" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Chaque livrable nomme explicitement ce qu'il ne fait pas.
**Échec.** Un livrable ne borne pas son périmètre.
**Statut.** OK — SPEC § 1.2 ; DATA-MODEL § 0 (« rien n'est exécutable »), § 14 ; UI § 1 (lignes 37-41).

### V-A2 — Aucune trace de mémoire technique *rédigé* automatiquement
**Méthode.** `grep -rniE "rédige.*automatiquement|génère.*mémoire|assemble.*automatiquement" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Les seules occurrences sont des **refus** explicites ou des renvois « hors périmètre ».
**Échec.** Un livrable décrit une production automatique de mémoire.
**Statut.** OK — SPEC § 1.2/§ 3.3 (note de périmètre, lignes 120-124) ; DATA-MODEL § 14 (lignes 467-470) ; UI § 5-E2 Famille 9 (lignes 315-318).

### V-A3 — Aucune veille, aucun dépôt, aucun chiffrage, aucune authentification multi-utilisateurs décrits comme fonctionnalités
**Méthode.** `grep -rniE "veille|dépôt de pli|chiffrage|authentification" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md` puis lecture des occurrences.
**Succès.** Chaque occurrence est un **renvoi au hors-périmètre**, jamais une maquette de fonctionnalité.
**Échec.** Une fonctionnalité hors-périmètre est décrite comme à construire.
**Statut.** OK — les occurrences sont toutes des exclusions (ex. SPEC § 1.2, § 4.6, § 7.3 ; UI § 7 lignes 501-504). Point de vigilance : `DATA-MODEL.md` § 0 propose **FastAPI** et des **migrations SQL** comme « cible phase 2 » — c'est une proposition de stack explicitement étiquetée « proposition à valider par Anthony », donc admissible, mais elle évoque une API HTTP (phase 2). À confirmer comme non-empiètement.

### V-A4 — Le squelette `src/` reste un squelette (pas de logique métier)
**Méthode.** `grep -rnE "^\s*(import|from)\s" src --include=*.py | grep -vE "__future__|from app|import app"` ; `grep -rn "NotImplementedError" src --include=*.py | wc -l`
**Succès.** Zéro import hors bibliothèque standard ; tous les points d'entrée lèvent `NotImplementedError`.
**Échec.** Une dépendance externe est importée, ou une fonction retourne un résultat calculé.
**Statut.** OK — seuls `dataclasses`, `datetime`, `decimal`, `enum`, `typing` sont importés ; 32 occurrences de `NotImplementedError` relevées.

### V-A5 — Aucune énumération close inventée pour le métier / le juridique
**Méthode.** `grep -nE "liste indicative|à compléter|à valider|non fixé|à vérifier" docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Les listes fermées (formes juridiques, types de documents, catégories) sont marquées « indicative / à compléter ».
**Échec.** Une liste est présentée comme définitive sans source.
**Statut.** OK — DATA-MODEL § 3.1 `forme_juridique`, § 3.2 `type_document`, § 8 `type_assurance`, § 12 `categorie` ; UI § 13 point 1.

---

## 4. Axe B — Cohérence entre livrables

### V-B1 — Les 9 familles d'informations sont identiques dans les trois livrables
**Méthode.** Comparer `PROJECT.md` § 3, `SPEC-MVP.md` § 3.3, `DATA-MODEL.md` § 6 à § 14, `UI-SAISIE.md` § 3.1 et § 5-E2.
**Succès.** Même nombre, même intitulés, même ordre de numérotation (1-9).
**Échec.** Une famille existe dans un livrable et manque dans un autre.
**Statut.** OK sur la numérotation (9 familles, 1-9, identiques). **Réserve** : la famille « Mémoire technique type » est en périmètre pour le stockage mais son **inclusion dans le MVP est explicitement non tranchée** (SPEC § 3.3 note + § 9 point 1). Elle est donc présente partout (identité de structure) mais son statut de périmètre reste ouvert — ce n'est pas une incohérence de contenu, c'est une décision d'Anthony à obtenir.

### V-B2 — Le modèle de données couvre la famille « Identité » telle que définie par PROJECT.md § 3
**Méthode.** Comparer la ligne « Identité » de `SPEC-MVP.md` § 3.3 (ligne 110) et les champs E1a de `UI-SAISIE.md` (lignes 204-214) avec l'entité `entreprise` de `DATA-MODEL.md` § 3.1 (lignes 119-143) : `grep -niE "iban|bic|coordonnées bancaires|effectif" docs/DATA-MODEL.md`
**Succès.** Chaque élément listé par la spécification et par l'interface possède un champ dans le modèle.
**Échec.** Un élément demandé à l'utilisateur n'a nulle part où être stocké.
**Statut.** **ÉCHEC (majeur)** — voir § 11, constat C1. `PROJECT.md` § 3 et `SPEC-MVP.md` § 3.3 listent les « coordonnées bancaires » et l'« effectif » dans l'Identité ; `UI-SAISIE.md` E1a les présente en champs (lignes 213-214 : « Effectif (nombre) », « Coordonnées bancaires (IBAN, BIC) ») ; `DATA-MODEL.md` § 3.1 ne contient **aucun** champ `iban`/`bic` ni `effectif` (l'`effectif_moyen` de § 7.1 est rattaché aux capacités financières, pas à l'identité). Les coordonnées bancaires n'apparaissent dans le modèle que comme **exemple** de donnée sensible (§ 2.2, § 17).

### V-B3 — L'interface de saisie correspond au modèle
**Méthode.** Pour chaque écran de `UI-SAISIE.md` § 5, retrouver l'entité ou le champ correspondant dans `DATA-MODEL.md`.
**Succès.** Chaque écran / champ de l'interface se projette sur une entité ou un champ du modèle.
**Échec.** Un écran produit une donnée que le modèle ne sait pas représenter.
**Statut.** **ÉCHEC (majeur)** — deux écarts : (a) « Coordonnées bancaires (IBAN, BIC) » (V-B2) ; (b) l'écran **E4 « Nature de la pièce »** (ligne 346) propose la liste `attestation, certificat, bilan, CV, photo, autre`, non alignée sur l'énumération `type_document` du modèle (14 valeurs, ligne 154 : `kbis`, `avis_sirene`, `liasse_fiscale`, `attestation_fiscale`, `attestation_sociale`, `attestation_assurance`, `fiche_technique`, `avis_technique`, `attestation_bonne_execution`…). Voir constats C1 et C4 (§ 11).

### V-B4 — L'énumération `type_document` est utilisée de façon identique partout
**Méthode.** `grep -nE "type_document|Nature de la pièce" docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Une seule liste de valeurs pour un même concept.
**Échec.** Deux listes différentes pour la même chose.
**Statut.** **ÉCHEC (mineur)** — voir C4. `UI-SAISIE.md` § 13 point 6 reconnaît la règle (« les libellés d'écran devront reprendre `type_document` ») mais le tableau E4 de la ligne 346 affiche une liste réduite et différente. Incohérence non signalée dans les points ouverts du lot L3.

### V-B5 — La checklist de conformité alimente la spécification
**Méthode.** Vérifier que la brique C de `SPEC-MVP.md` § 5 renvoie à `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` (L4) et que L4 fournit une structure exploitable par la checklist.
**Succès.** SPEC brique C s'appuie sur L4 comme source des pièces exigées ; L4 fournit une liste de pièces + statuts.
**Échec.** La brique C ne renvoie à aucune source des exigences, ou L4 ne fournit rien d'exploitable.
**Statut.** OK sur la structure — L4 (`docs/CONFORMITE-COMMANDE-PUBLIQUE.md` § 2-5) fournit des checklists A/B/C/D avec un statut par ligne, et `SPEC-MVP.md` § 9 point 5 délègue explicitement à L4 « la liste précise des pièces exigées et le vocabulaire d'extraction ». **Réserve (dépendance non satisfaite)** : la brique C de SPEC § 5 ne cite **pas** nommément L4 dans son corps ; le lien n'existe qu'en § 9 point 5. À vérifier lors de l'implémentation phase 2 que la checklist s'alimente bien de L4.

### V-B6 — Les délégations entre livrables ont un destinataire effectif
**Méthode.** Lister chaque renvoi « à fixer par L2 / dépend de L2 » dans `SPEC-MVP.md` et `UI-SAISIE.md`, puis vérifier que `DATA-MODEL.md` traite le point (ou le liste en § 16 « Points ouverts ») : `grep -niE "export|format" docs/DATA-MODEL.md`
**Succès.** Chaque point explicitement délégué à L2 est traité ou listé comme point ouvert par L2.
**Échec.** Un livrable délègue, l'autre ne reprend pas la balle.
**Statut.** **ÉCHEC (mineur)** — voir C5. `SPEC-MVP.md` § 3.5 et § 9 point 2/3 délèguent à L2 : (a) le **format d'export** de la bibliothèque, (b) les **formats de fichiers acceptés** pour un DCE. `UI-SAISIE.md` § 13 point 4 délègue aussi le format d'export à L2. Or `DATA-MODEL.md` ne traite ni l'un ni l'autre et **ne les liste pas** en § 16 (points ouverts) : la recherche `export|format` n'y retourne que des occurrences de « format de date » et « format de fichier » génériques. Délégation sans destinataire.

---

## 5. Axe C — Tenue de la ligne rouge

### V-C1 — Chaque affirmation de cadrage pointe vers sa source
**Méthode.** `SPEC-MVP.md` § « Sources de ce document » (lignes 9-16) : vérifier que chaque section renvoie à `PROJECT.md` / `README.md` / `PLAN.md`. `grep -nE "PROJECT\.md|README\.md|PLAN\.md" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Les affirmations structurantes portent un renvoi vérifiable.
**Échec.** Une affirmation de cadrage ne pointe vers rien.
**Statut.** OK pour SPEC et UI. **Réserve (mineur)** — voir C7 : `SPEC-MVP.md` § 7 (ligne 16) cite comme source « carte Kanban L1 (`t_1c466d22`) », qui n'est **pas un fichier du dépôt** ; une source qui n'existe que sur le board n'est pas vérifiable par un relecteur du dépôt.

### V-C2 — Aucun chiffre, seuil ou durée non sourcé
**Méthode.** `grep -rnoE "[0-9]+ *(ans|jours|mois|semaines|%)|durée de validité de [0-9]+|seuil de [0-9]+" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Aucune occurrence, ou toute occurrence est explicitement renvoyée à une source / marquée « à vérifier ».
**Échec.** Un seuil ou une durée est affirmé sans source.
**Statut.** OK — **aucune occurrence** dans les trois livrables. Le seuil d'alerte `echeance_proche` est systématiquement laissé ouvert (DATA-MODEL § 2.2, § 15, § 16 point 3 ; UI § 5-E5 ligne 381).

### V-C3 — Aucune norme ni référence juridique inventée dans L1/L2/L3
**Méthode.** `grep -rnoiE "\b(loi|décret|arrêté|article [0-9L]|code des marchés|CCAG|CCP|RGPD|DTU|NF [A-Z]|ISO [0-9])\b" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md`
**Succès.** Aucune référence juridique nommée ; les mots génériques (`ISO`, `RGPD`) n'apparaissent que comme sujets explicitement renvoyés à L4 / à un juriste.
**Échec.** Une référence légale est citée sans source dans un livrable non habilité.
**Statut.** OK — les seules occurrences dans L1/L2/L3 sont les mots `Qualibat`, `RGE`, `MASE`, `ISO` **recopiés de la liste d'exemple de `PROJECT.md` § 3** (SPEC § 3.3 ligne 113, UI ligne 281) et `RGPD` comme sujet renvoyé à un juriste (SPEC § 7.6, DATA-MODEL § 11.3/§ 16). Aucune référence juridique n'est nommée dans ces trois documents. `SPEC-MVP.md` § « Sources » (lignes 18-21) pose lui-même la règle : seul L4 est habilité à citer des sources administratives.

### V-C4 — Aucune garantie de conformité, aucun prix
**Méthode.** `grep -rniE "conforme|garantie?|certifi[ée]|prix|marge|chiffrage" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md` puis lecture.
**Succès.** Les occurrences sont soit des **refus** (« ne garantit aucune conformité »), soit des renvois hors-périmètre (prix/chiffrage).
**Échec.** Le système est présenté comme garantissant une conformité ou fixant un prix.
**Statut.** OK — SPEC § 2, § 5.4, § 5.6 ; DATA-MODEL § 14 ; UI § 9 (« jamais “conforme”, “validée par l'IA” ou “certifiée” ») ; UI § 2 P4 (« ne fixe aucun prix »).

### V-C5 — Aucune valeur « générée par l'IA » dans le modèle
**Méthode.** `grep -rniE "genere_ia|généré par l'IA|générée par l'IA" docs/DATA-MODEL.md src`
**Succès.** L'énumération `origine_valeur` ne comporte que `document_extrait` / `saisie_entreprise`, et le code le reflète.
**Échec.** Une troisième valeur d'origine existe.
**Statut.** OK — DATA-MODEL § 2.2 (ligne 90) et `src/app/domain/commun.py` (`OrigineValeur` : deux valeurs) ; UI § 10 (lignes 572-574).

---

## 6. Axe D — Traçabilité et échéances

### V-D1 — Chaque entité de contenu porte un motif de traçabilité
**Méthode.** Vérifier que `DATA-MODEL.md` § 4 s'applique à chaque famille (§ 6 à § 14) et que le squelette le reflète (`src/app/domain/commun.py`, classe `Traceabilite`).
**Succès.** Le motif `source_document_id` / `origine` / `confiance` est déclaré pour toute entité de contenu.
**Échec.** Une famille n'est pas traçable.
**Statut.** **ÉCHEC (majeur)** — voir C2. Le motif de traçabilité de `DATA-MODEL.md` § 4 (et § 2.3) est porté **au niveau de l'enregistrement** (« chaque enregistrement de contenu », ligne 173). Or `DATA-MODEL.md` § 6 demande que « chaque **champ** d'identité pointe vers sa source (`kbis`, `avis_sirene`, `statuts`) » (lignes 238-239) : l'entité `entreprise` (§ 3.1) est une **ligne unique** sans colonne `source_document_id`, et la sous-entité `representant_legal` (§ 3.1, lignes 141-143) n'en porte pas davantage. Une ligne d'entreprise ne peut pas pointer vers plusieurs sources hétérogènes (raison sociale ↔ KBIS, SIREN ↔ avis SIRENE). La règle de § 6 est donc inapplicable avec la structure de § 3.1.

### V-D2 — La granularité de la traçabilité est la même dans L2 et L3
**Méthode.** Comparer `DATA-MODEL.md` § 2.3/§ 4 (granularité **enregistrement**) avec `UI-SAISIE.md` § 2 P1 (lignes 50-58) et § 10 (lignes 555-563, granularité **champ** : chaque valeur affichée porte son origine / validité / vérification).
**Succès.** Une seule granularité, ou une règle de passage documentée.
**Échec.** L'interface exige une finesse que le modèle ne fournit pas.
**Statut.** **ÉCHEC (majeur)** — voir C2. L'interface affiche l'origine et la confiance **champ par champ** ; le modèle ne les porte que **par enregistrement**. Aucune correspondance n'est écrite. Idem pour `confiance` : `DATA-MODEL.md` § 2.3 le déclare **obligatoire** par enregistrement, alors que `UI-SAISIE.md` § 4 (lignes 161-163) affirme « un champ vide n'a pas de `confiance` » — deux granularités différentes.

### V-D3 — Les dates de validité et les échéances sont présentes et recensées
**Méthode.** Vérifier `DATA-MODEL.md` § 15 (vue transverse des échéances) et `UI-SAISIE.md` § 5-E5.
**Succès.** Chaque famille porteuse d'une échéance (assurance, certification, attestation, produit) est recensée, et l'interface les restitue.
**Échec.** Une échéance existe dans un livrable et pas dans l'autre.
**Statut.** OK — DATA-MODEL § 15 (lignes 478-486) recense 7 entrées ; UI E5 (lignes 356-385) les restitue avec le vocabulaire `statut_validite`. Aucun seuil d'alerte n'est fixé des deux côtés (cohérent, et volontairement ouvert).

### V-D4 — Le statut d'une date est calculable sans seuil inventé
**Méthode.** `grep -nE "echeance_proche|non_renseigne" docs/DATA-MODEL.md docs/UI-SAISIE.md` ; vérifier la note « seuil non fixé ».
**Succès.** Les états sont définis ; le passage `valide → echeance_proche` est marqué comme dépendant d'un seuil non tranché.
**Échec.** Un nombre de jours est codé en dur.
**Statut.** OK — DATA-MODEL § 2.2 (ligne 97-99) et § 15 (ligne 488) ; UI § 5-E5 (ligne 381).

---

## 7. Axe E — Chasse aux fuites de données

### V-E1 — Aucune donnée d'entreprise réelle (SIRET, IBAN, téléphone, courriel)
**Méthode.**
`grep -rnoE "FR[0-9]{2}[ ]?([0-9A-Z]{4}[ ]?){4}[0-9A-Z]{2,3}|[0-9]{14}\b|\b0[1-9]([ .-]?[0-9]{2}){4}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" docs/*.md README.md PROJECT.md src -r`
**Succès.** Aucun identifiant réaliste ; les seules occurrences sont des valeurs d'exemple manifestement factices (`0000…`).
**Échec.** Un SIRET / IBAN / téléphone / courriel plausible apparaît dans le dépôt.
**Statut.** OK — **une seule occurrence** : `00000000000000` dans `src/app/domain/entreprise.py` ligne 7, à l'intérieur d'une docstring qui porte la mention « EXEMPLE FICTIF à ne pas confondre avec une donnée réelle ». Aucun IBAN réel, aucun SIRET réaliste, aucun numéro de téléphone, aucune adresse électronique réelle.

### V-E2 — Les exemples sont signalés comme fictifs
**Méthode.** `grep -rci "fictif" docs/*.md`
**Succès.** Chaque document contenant un exemple porte une mention « fictif ».
**Échec.** Un exemple non signalé peut passer pour une donnée réelle.
**Statut.** OK — comptage : CONFORMITE 1, DATA-MODEL 1, DONNEES-METIER 5, PLAN 1, SPEC 2, UI 11. L'essentiel des exemples affichés se trouve dans `UI-SAISIE.md`, qui les signale abondamment (§ 3.2 blocs « EXEMPLE FICTIF », § 12 en-tête « Tout le contenu ci-dessous est fictif »).

### V-E3 — Aucun secret ni fichier sensible versionné
**Méthode.** `git status --short` ; lire `.gitignore` ; `find . -name "*.env" -o -name "*.key" -o -name "*.pem"`
**Succès.** `.gitignore` couvre `data/`, `.env`, `*.key`, `*.pem`, `*.secret` ; aucun secret dans le dépôt.
**Échec.** Un fichier de secret est présent ou non ignoré.
**Statut.** OK — `.gitignore` couvre `data/`, `.env`, `.env.*`, `*.secret`, `*.key`, `*.pem` (lignes 2-6). `git status --short` ne montre que `docs/` et `src/` non suivis. Aucun fichier `.env`/`.key`/`.pem` présent.

### V-E4 — Aucun document confidentiel dans le dépôt
**Méthode.** `find . -type f -name "*.pdf" -o -name "*.docx" -o -name "*.xlsx" -o -name "*.zip"` ; vérifier que `data/` est vide.
**Succès.** Aucun fichier de document (KBIS, bilan, CV, DCE) versionné ; `data/` vide.
**Échec.** Un document réel est présent.
**Statut.** OK — aucun fichier de ce type ; `data/` et `scripts/` sont vides.

### V-E5 — Aucune donnée réelle de tiers (candidat, client, collectivité)
**Méthode.** `grep -rnoiE "saint-denis|mairie|crédit agricole|anthony|pause" docs/*.md README.md PROJECT.md`
**Succès.** Aucune donnée de tiers réelle ; les mentions de personnes/collectivités sont des éléments de cadrage assumés (le porteur du projet), pas des données de la bibliothèque.
**Échec.** Un nom de client, de candidat ou de fournisseur réel est présenté comme donnée exploitable.
**Statut.** **Réserve (cosmétique)** — voir C8. Aucune donnée de tiers au sens de la bibliothèque. En revanche : `PROJECT.md` § 6, `README.md` et `PLAN.md` § 4 nomment la **Mairie de Saint-Denis** comme employeur du porteur (risque de conflit d'intérêts) ; `docs/DONNEES-METIER-BATIMENT.md` mentionne plusieurs fois La Réunion (contexte géographique métier). Ce ne sont pas des fuites de données d'entreprise, mais des références au monde réel dans un dépôt de cadrage — à assumer sciemment. Aucun nom de client ni de fournisseur réel.

---

## 8. Axe F — Relecture humaine bloquante

### V-F1 — La relecture humaine est décrite comme un blocage technique
**Méthode.** `grep -rniE "blocage technique|relecture humaine|Relue et validée" docs/SPEC-MVP.md docs/DATA-MODEL.md docs/UI-SAISIE.md README.md`
**Succès.** Dans chaque livrable, la relecture humaine est qualifiée de **blocage technique / contrainte d'implémentation**, pas de recommandation.
**Échec.** Un livrable la présente comme optionnelle.
**Statut.** OK — `README.md` ligne 27 ; SPEC § 2 (lignes 51-77, « contrainte de conception, pas une recommandation ») ; UI § 2 P2, § 9 (« contraintes techniques de conception »).

### V-F2 — Aucun chemin ne mène à l'état validé sans action humaine
**Méthode.** Lire `UI-SAISIE.md` § 9 (lignes 525-539) et § 5-E7 (lignes 408-449) ; vérifier que l'attestation exige une case cochée + nom + horodatage, et que toute écriture révoque la validation.
**Succès.** L'état « Relue et validée » n'est posable que par une action humaine explicite, et il est révocable.
**Échec.** Un composant automatique peut poser l'état.
**Statut.** OK côté interface — UI § 9 impose : aucun composant automatique ne pose l'état, toute écriture révoque la validation, machine à états § 5-E7 (lignes 429-443) avec « Validée puis modifiée (à relecture) ».

### V-F3 — Le modèle de données porte le verrou de relecture
**Méthode.** `grep -rniE "relecteur|horodatage|validation|relue" docs/DATA-MODEL.md src`
**Succès.** Le modèle sait représenter « qui a relu, quand, sur quelle version ».
**Échec.** L'interface exige une donnée que le modèle ne stocke pas.
**Statut.** **ÉCHEC (majeur)** — voir C3. La recherche ne retourne, dans `DATA-MODEL.md`, que `date_creation` / `date_modification` (« horodatage » générique, lignes 110-111) et une phrase générale en § 14 (ligne 470). Aucun champ **nom du relecteur**, aucune colonne d'horodatage de validation, aucun état « relue et validée » dans `fiche_version` (§ 5 : statuts `brouillon` / `publiee` / `archivee` uniquement). `src/app/domain/fiche_version.py` confirme (`StatutFiche` : trois valeurs). Le lot L3 signale lui-même ce point (UI § 13 point 6, lignes 663-666) mais **L2 ne le reprend pas** dans ses points ouverts (§ 16).

### V-F4 — Le verrou est cohérent entre interface et versionnement
**Méthode.** Comparer les états de fiche de `UI-SAISIE.md` (E0 ligne 184-186, E7 ligne 429-443) avec `fiche_version.statut` de `DATA-MODEL.md` § 5.
**Succès.** Une correspondance explicite existe entre les états d'interface et les statuts du modèle.
**Échec.** Deux vocabulaires d'états sans table de correspondance.
**Statut.** **ÉCHEC (mineur)** — voir C9. L'interface a 6 états de fiche (`Vierge`, `En cours de saisie`, `Socle complet (non relue)`, `En relecture`, `Relue et validée`, `Validée puis modifiée`), le modèle n'en a que 3 (`brouillon`, `publiee`, `archivee`). Aucune table de correspondance n'est écrite. De plus, l'interface valide **par famille** (UI § 7, lignes 486-495) alors que le modèle versionne **la fiche entière** (DATA-MODEL § 5, ligne 198) — granularité de validation non alignée.

---

## 9. Axe G — Chemins de fichiers et présence effective des livrables

### V-G1 — Les six livrables existent aux chemins exacts
**Méthode.** `ls -la docs/` ; comparer avec `docs/PLAN.md` § 2 (tableau des lots).
**Succès.** Les 6 fichiers existent : `docs/SPEC-MVP.md`, `docs/DATA-MODEL.md`, `docs/UI-SAISIE.md`, `docs/CONFORMITE-COMMANDE-PUBLIQUE.md`, `docs/DONNEES-METIER-BATIMENT.md`, `docs/PLAN-DE-TEST.md`.
**Échec.** Un fichier manque ou est ailleurs.
**Statut.** OK — les six sont présents dans `docs/` (`SPEC-MVP.md` 21 609 o, `DATA-MODEL.md` 24 939 o, `UI-SAISIE.md` 35 249 o, `CONFORMITE-COMMANDE-PUBLIQUE.md` 29 473 o, `DONNEES-METIER-BATIMENT.md` 34 034 o, `PLAN-DE-TEST.md` = ce fichier). Aucun livrable n'a été écrit hors du dossier projet.

### V-G2 — Le squelette `src/` est conforme à la description de L2
**Méthode.** `find src -type f | sort` ; comparer avec `src/README.md` et `DATA-MODEL.md` § 1.6.
**Succès.** Une entité de domaine par famille, plus `commun`, `document`, `fiche_version` ; dossiers `api/`, `services/`, `storage/`, `migrations/`, `tests/`.
**Échec.** Une famille n'a pas de module, ou un module non prévu existe.
**Statut.** OK — 20 modules Python : 9 entités de famille (`entreprise`, `financier`, `assurances`, `certifications`, `references_chantiers`, `moyens_humains`, `moyens_materiels`, `fiches_produits`, `memoire_technique`) + `commun`, `document`, `fiche_version` + `main`, `config`, `api/routes`, 3 services, 2 modules storage.

### V-G3 — Aucun chemin de fichier affirmé n'est faux
**Méthode.** Extraire les chemins cités dans les livrables (`grep -rnoE "\`?[a-zA-Z0-9_./-]+\.(md|py|sql)\`?" docs/*.md`) et vérifier leur existence réelle.
**Succès.** Tout chemin cité existe.
**Échec.** Un livrable renvoie à un fichier inexistant.
**Statut.** OK pour les chemins du dépôt (`docs/DATA-MODEL.md`, `docs/DONNEES-METIER-BATIMENT.md`, `docs/CONFORMITE-COMMANDE-PUBLIQUE.md`, `src/migrations/`, `src/app/...`). **Réserve** : `DATA-MODEL.md` § 0 renvoie à des chemins de migration **futurs** (`src/migrations/000N_*.sql`) qui n'existent pas encore — c'est une convention, pas un livrable (voir V-G4).

### V-G4 — La convention de migrations est décrite, aucune migration appliquée
**Méthode.** `ls src/migrations/` ; lire `src/migrations/README.md`.
**Succès.** Aucun fichier `.sql` ; la convention est écrite.
**Échec.** Une migration est présente ou un schéma a été appliqué.
**Statut.** OK — `src/migrations/` ne contient que `README.md` (convention `000N_*.sql`, sections up/down, jamais modifiée après application). Aucun `.sql`.

### V-G5 — Aucun test fonctionnel présent (attendu en phase 1)
**Méthode.** `ls src/tests/` ; lire `src/tests/README.md`.
**Succès.** `src/tests/` contient uniquement son `README.md` expliquant que les tests viendront en phase 2.
**Échec.** (Non applicable en phase 1.)
**Statut.** ATTENDU — `src/tests/README.md` annonce explicitement « aucun test fonctionnel n'est écrit » en phase 1. C'est conforme.

### V-G6 — Le squelette compile et ses points d'entrée sont bien bloqués
**Méthode.** `python3 -m compileall -q src` ; `python3 -c "from app.main import main; main()"` (depuis `src/`) ; `find src -name "__pycache__" -o -name "*.pyc"`.
**Succès.** La compilation réussit ; les points d'entrée lèvent `NotImplementedError` ; aucun `__pycache__` résiduel versionnable.
**Échec.** Un module ne compile pas, ou une fonction retourne un résultat.
**Statut.** OK — `main()` lève `NotImplementedError("Phase 1 : squelette. Aucune application exécutable.")` (ligne 12) ; 32 `NotImplementedError` recensés ; aucun `__pycache__`/`.pyc` présent ; `.gitignore` couvre `__pycache__/`.

### V-G7 — Rien n'est committé sans intention
**Méthode.** `git status --short`
**Succès.** L'état du dépôt est connu et documenté ; les livrables ne sont pas committés par surprise.
**Échec.** Un commit non voulu.
**Statut.** OK — `docs/` et `src/` sont **non suivis** (`?? docs/`, `?? src/`), conformément au choix des lots L2 et L3 de ne rien committer pour ne pas gêner les lots parallèles. Ce point est un **constat à remonter** : la phase 1 se termine avec des livrables non versionnés ; leur archivage (git) reste à faire par `plan`.

---

## 10. Axe H — Ce qui doit échouer aujourd'hui (produit non construit)

Ces vérifications portent sur des **fonctionnalités**. En phase 1, leur « échec » est le
résultat attendu. Elles serviront de point de départ à la phase 2 : le jour où elles
passent, la phase 2 avance.

| # | Vérification | Méthode prévue (phase 2) | Résultat attendu aujourd'hui |
|---|---|---|---|
| V-H1 | Créer une entreprise et la lire | Appeler `creer_fiche_entreprise(...)` puis la relire | ÉCHEC attendu — `NotImplementedError` |
| V-H2 | Ajouter une information à une famille et vérifier sa traçabilité | `ajouter_information(...)` puis contrôle `source_document_id` | ÉCHEC attendu — `NotImplementedError` |
| V-H3 | Refuser une valeur `document_extrait` sans source | Test d'entrée invalide sur `ajouter_information` | Non testable — aucune implémentation |
| V-H4 | Analyser un DCE déposé et rendre pièces + critères + date limite avec sources | `analyser_dce(chemin)` | ÉCHEC attendu — `NotImplementedError` |
| V-H5 | Refuser un DCE illisible sans deviner son contenu | Jeu d'essai : fichier scanné sans texte | Non testable — aucune implémentation |
| V-H6 | Générer la checklist et signaler les manques | `construire_checklist(...)` | ÉCHEC attendu — `NotImplementedError` |
| V-H7 | Ne jamais présenter la checklist comme un certificat | Lecture de la sortie | Non testable — aucune sortie produite |
| V-H8 | Bloquer la sortie d'un élément engageant sans relecture humaine validée | Appeler le service de sortie/export | ÉCHEC attendu — aucune implémentation |
| V-H9 | Révoquer la validation après modification d'un champ | Machine à états de fiche | Non testable — aucune implémentation |
| V-H10 | Persister et relire (SQLite) | Connexion base | ÉCHEC attendu — aucune base, aucune migration |
| V-H11 | Appliquer / annuler une migration (up / down) | `0001_init.sql` | ÉCHEC attendu — aucun fichier SQL |
| V-H12 | Exécuter une suite de tests de non-régression | `pytest src/tests` | ÉCHEC attendu — aucun test écrit (par conception) |

**Critère de succès de l'axe H en phase 1 :** toutes ces vérifications **échouent**, et
l'échec est **documenté** comme tel — pas contourné, pas simulé, pas remplacé par une
sortie factice.

---

## 11. Constats relevés lors de la rédaction (résultats réels)

Ces constats ne sont pas des prévisions : ils ont été **observés** en exécutant les
commandes des colonnes « Méthode » ci-dessus, sur le dépôt au 30/09/2026.

### C1 — [majeur] Le modèle ne couvre pas l'Identité définie par la spécification et l'interface
- **Preuve.** `PROJECT.md` § 3 et `SPEC-MVP.md` § 3.3 ligne 110 listent « coordonnées bancaires » et « effectif » dans l'Identité ; `UI-SAISIE.md` lignes 213-214 les présente comme champs de saisie ; `DATA-MODEL.md` § 3.1 (entité `entreprise`) n'a **aucun** champ `iban`/`bic` ni `effectif` (recherche `grep -niE "iban|bic|effectif" docs/DATA-MODEL.md` : seules occurrences en exemple de sensibilité ou en famille financière).
- **Attendu.** Tout élément saisi par l'utilisateur a un emplacement dans le modèle.
- **Observé.** Deux éléments de l'écran E1a n'ont pas de champ correspondant.
- **Gravité.** Majeur (bloque la phase 2 sur la famille Identité).
- **Recommandation.** À traiter par le lot L2 (propriétaire du modèle) : ajouter les champs manquants ou écrire explicitement qu'ils sont hors modèle, et arbitrer si l'« effectif » d'identité se confond avec `effectif_moyen` (§ 7.1).

### C2 — [majeur] Granularité de traçabilité incohérente entre modèle et interface
- **Preuve.** `DATA-MODEL.md` § 2.3/§ 4 porte `origine`/`confiance`/`source_document_id` **par enregistrement** (lignes 103-114, 173) ; § 6 demande pourtant que « chaque **champ** d'identité pointe vers sa source » (lignes 238-239), ce que la structure de `entreprise` (ligne unique, § 3.1) ne permet pas. `UI-SAISIE.md` § 2 P1 (lignes 50-58) et § 10 affichent la traçabilité **par champ**, et § 4 (lignes 161-163) va jusqu'à dire qu'un champ vide « n'a pas de confiance » quand le modèle rend `confiance` obligatoire par enregistrement.
- **Gravité.** Majeur.
- **Recommandation.** À trancher par L2 : soit porter les colonnes de traçabilité au niveau de chaque valeur (entité `valeur` document/valeur/homme/origine/confiance), soit écrire la règle qui projette la traçabilité d'enregistrement sur l'affichage par champ. L3 doit alors s'aligner.

### C3 — [majeur] Le verrou de relecture humaine n'est pas représentable dans le modèle
- **Preuve.** `UI-SAISIE.md` § 9 et § 5-E7 exigent : case cochée + **nom du relecteur** + **horodatage** + révocation à la première modification. `grep -rniE "relecteur|horodatage|relue" docs/DATA-MODEL.md src` ne retourne que `date_creation`/`date_modification` génériques et une phrase générale (§ 14, ligne 470). `fiche_version` (§ 5) n'a que `brouillon`/`publiee`/`archivee` ; `src/app/domain/fiche_version.py` le confirme. L3 signale le point (UI § 13 point 6), L2 ne le reprend pas en § 16.
- **Gravité.** Majeur (la ligne rouge « blocage technique » n'est pas implémentable en l'état).
- **Recommandation.** L2 doit ajouter au modèle : identité du relecteur, horodatage de validation, et un état de validation (fiche et/ou famille). À défaut, le verrou restera une intention d'interface sans support.

### C4 — [mineur] Deux listes différentes pour `type_document`
- **Preuve.** `DATA-MODEL.md` ligne 154 : 14 valeurs (`kbis`, `avis_sirene`, `liasse_fiscale`, `attestation_fiscale`, `attestation_sociale`, `attestation_assurance`, `certificat`, `fiche_technique`, `avis_technique`, `cv`, `attestation_bonne_execution`, `photo`, `autre`…). `UI-SAISIE.md` ligne 346 (E4 « Nature de la pièce ») : `attestation, certificat, bilan, CV, photo, autre` — 6 valeurs, dont « bilan » qui ne figure pas dans `type_document`.
- **Gravité.** Mineur (corrigeable à l'implémentation), mais L3 § 13 point 6 exige déjà de reprendre `type_document` : la règle est écrite et le tableau ne la respecte pas.
- **Recommandation.** L3 aligne la liste E4 sur `type_document` du modèle, ou documente la projection (liste d'écran plus grossière → valeur de modèle).

### C5 — [mineur] Délégations sans destinataire (export, formats de DCE)
- **Preuve.** `SPEC-MVP.md` § 3.5 et § 9 points 2-3 délèguent à L2 le format d'export et les formats de fichiers DCE acceptés ; `UI-SAISIE.md` § 13 point 4 délègue aussi le format d'export à L2. `grep -niE "export|format" docs/DATA-MODEL.md` : aucune section sur ces sujets ; § 16 « Points ouverts » ne les liste pas.
- **Gravité.** Mineur.
- **Recommandation.** L2 ajoute ces deux points à sa liste de points ouverts (ou les traite). Sinon la phase 2 les découvrira non tranchés.

### C6 — [mineur] Le statut « mémoire technique type » dans le MVP reste non tranché
- **Preuve.** `SPEC-MVP.md` § 3.3 note (lignes 120-124) et § 9 point 1 : la famille est collectée/stockée mais son inclusion dans le MVP est « à confirmer par Anthony » ; `PROJECT.md` § 3 la liste comme contenu, § 7 exclut la rédaction automatique.
- **Gravité.** Mineur (décision, pas défaut).
- **Recommandation.** Décision d'Anthony à obtenir avant la phase 2. Les trois livrables sont cohérents entre eux sur ce point (tous la stockent, aucun ne la rédige).

### C7 — [mineur] Source de traçabilité non vérifiable dans le dépôt
- **Preuve.** `SPEC-MVP.md` § « Sources » ligne 16 cite « carte Kanban L1 (`t_1c466d22`) » comme source d'affirmations. Cette carte existe sur le board, pas dans le dépôt (`.git` ne contient aucun fichier de carte).
- **Gravité.** Mineur.
- **Recommandation.** Remplacer par la référence au brief racine recopié, ou joindre le texte de la carte dans le dépôt. La ligne rouge exige que toute affirmation pointe vers une source **consultable**.

### C8 — [cosmétique] Références au monde réel dans le dépôt de cadrage
- **Preuve.** `PROJECT.md` § 6, `README.md` § « Point de vigilance juridique » et `PLAN.md` § 4 nomment la **Mairie de Saint-Denis** ; `DONNEES-METIER-BATIMENT.md` mentionne La Réunion (lignes 284, 314, 344, 418, 494).
- **Gravité.** Cosmétique — ce n'est pas une donnée d'entreprise ni un secret, c'est un élément de cadrage du conflit d'intérêts.
- **Recommandation.** Assumer sciemment. Aucune action requise, mais à ne pas confondre avec un exemple de bibliothèque.

### C9 — [mineur] États de fiche et granularité de validation non alignés
- **Preuve.** `UI-SAISIE.md` E0 (lignes 184-186) définit 6 états de fiche ; `DATA-MODEL.md` § 5 `fiche_version.statut` n'en a que 3. L'interface valide **par famille** (§ 7 lignes 486-495) ; le modèle versionne **la fiche entière** (§ 5 ligne 198).
- **Gravité.** Mineur.
- **Recommandation.** Écrire la table de correspondance états d'interface ↔ statuts du modèle, et trancher le niveau de validation (fiche ou famille). À traiter avec C3 (même sujet).

### C10 — [mineur] `fiche_version_id` obligatoire mais absent de l'entité racine
- **Preuve.** `DATA-MODEL.md` § 2.3 déclare `fiche_version_id` **obligatoire** pour « toute entité de contenu » ; l'entité `entreprise` (§ 3.1) ne le porte pas (elle est la racine du versionnement). Le cas limite (comment `entreprise` se rattache à une version) n'est pas documenté.
- **Gravité.** Mineur (ambiguïté de modèle).
- **Recommandation.** L2 documente explicitement le cas de l'entité racine.

### Bilan des constats

| Gravité | Nombre | Constats |
|---|---|---|
| Bloquant | 0 | — |
| Majeur | 3 | C1, C2, C3 |
| Mineur | 6 | C4, C5, C6, C7, C9, C10 |
| Cosmétique | 1 | C8 |

Aucun constat **bloquant** : rien n'empêche la phase 1 d'être considérée comme livrée.
Les trois constats majeurs (C1, C2, C3) concernent tous **le modèle de données (lot L2)**
et l'articulation avec l'interface : ils doivent être traités avant que la phase 2
n'écrive du code sur ce modèle.

---

## 12. Ce que cette vérification **ne couvre pas**

Honnêtement, et pour éviter tout faux sentiment de complétude :

1. **Je ne teste aucune fonctionnalité.** Le produit n'existe pas ; l'axe H se limite à constater et documenter l'échec attendu. Aucun comportement réel (analyse de DCE, checklist, export, persistance) n'a été exercé.
2. **Le contenu juridique de L4 n'est pas vérifié sur la source.** Je n'ai pas ouvert Légifrance ni le site de la DAJ. Je constate seulement que `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` cite des références et les marque « à vérifier » ; **l'exactitude de ces références reste à confirmer par un juriste** — c'est précisément ce que le document demande.
3. **Le contenu métier de L5 n'est pas vérifié.** Je n'ai pas de compétence métier étanchéité pour juger si les éléments à collecter sont complets ou exacts.
4. **Lots L4 et L5 relus en survol.** Ils ne font pas partie des dépendances de L6. Leur cohérence fine avec L1/L2/L3 n'est vérifiée que sur les points de recouvrement cités (C1, C5, V-B5).
5. **Aucune recherche sur dépôt distant ni historique git.** Le dépôt est local, `docs/` et `src/` ne sont pas committés : la traçabilité par commit n'existe pas encore et n'a pas été évaluée.
6. **L'accessibilité de l'interface (UI § 11) n'est pas testable** en phase 1 : aucune page n'existe. Les contraintes annoncées (HTML sémantique, contraste, clavier) sont plausibles mais non vérifiées.
7. **Les risques listés au `PLAN.md` § 4 ne sont pas tous évalués** : je ne peux pas mesurer la probabilité d'un dépassement de périmètre futur ni l'impact réel du conflit d'intérêts (question juridique).
8. **Aucune vérification de sécurité au sens applicatif** (injection, authentification, chiffrement au repos) : le code ne fait rien, il n'y a pas de surface d'attaque. Le modèle identifie les champs `sensibilite = confidentiel` à protéger, ce qui est un bon point, mais **aucun mécanisme de chiffrement n'existe** et rien ne peut être testé.

---

*Fin du plan de test. Lot L6 — `qa`. 48 vérifications définies (§ 3 à § 10 : 36 sur le
cadrage, 12 sur les fonctionnalités à venir), 10 constats documentés (§ 11), 8 réserves
de couverture (§ 12).*
