# PLAN — Phase 2 : architecture technique et décisions structurantes

*Écrit par l'agent `plan` le 30 septembre 2026. Board : `ia-consultations`.
Dossier de travail : `/Users/pause/Projets/ia-consultations-publiques`.
Phase 1 livrée (`docs/PLAN.md`), décisions actées (`docs/DECISIONS.md`, D1 à D6).*

---

## 0. Ce sur quoi ce plan s'appuie

- `docs/DECISIONS.md` — **fait foi**. Les six décisions D1 à D6 d'Anthony.
- `PROJECT.md` — cadrage d'origine, ligne rouge (§ 5), points de vigilance (§ 6).
- `docs/PLAN.md` — plan de phase 1, structure de lots et risques.
- Livrables de phase 1 : `docs/SPEC-MVP.md`, `docs/DATA-MODEL.md`, `docs/UI-SAISIE.md`,
  `docs/CONFORMITE-COMMANDE-PUBLIQUE.md`, `docs/DONNEES-METIER-BATIMENT.md`,
  `docs/PLAN-DE-TEST.md`.
- `docs/PLAN-DE-TEST.md` § 11 — **dix constats observés** sur le cadrage de phase 1
  (3 majeurs : C1, C2, C3 ; 6 mineurs : C4, C5, C6, C7, C9, C10 ; 1 cosmétique : C8).
  Ils ne sont pas des prévisions, ils ont été vérifiés par commandes réelles. La phase 2
  doit les traiter ou les réfuter explicitement, sinon le modèle v2 reconduit des défauts
  mesurés.

---

## 1. Résultat visé de la phase 2

**Critère vérifiable de fin de phase :** les six documents suivants existent aux chemins
exacts, écrits en français, chacun se réclamant de `docs/DECISIONS.md` —

`docs/STACK-PROPOSAL.md`, `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`,
`docs/DATA-MODEL-V2.md`, `docs/SPEC-MVP-V2.md`, `docs/NOMENCLATURE-REFERENCE.md`,
`docs/REVUE-SECURITE.md` —

**et** les quatre conditions suivantes sont vérifiables à la lecture :

1. `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` pose les trois options de D6 (chiffrement
   côté client et traitement local / chiffrement au repos et isolation serveur / clés
   détenues par le client, déverrouillage à la demande), et pour chacune rend un verdict
   explicite sur la phrase « seul le client a accès à ses données » : *vraie par
   construction*, *vraie sous conditions* (lesquelles), ou *fausse au sens strict* ;
2. **aucune pièce du dépôt n'affirme une confidentialité que l'architecture ne tient
   pas** : toute phrase de confidentialité est soit un extrait de
   `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`, soit la mention « à compléter après
   validation de ce document » ;
3. `docs/DATA-MODEL-V2.md` traite nommément les constats **C1, C2, C3** (majeurs) et
   **C4, C9, C10** (mineurs), prévoit les **deux modes de facturation** de D3 sans
   implémenter de paiement, et reste **métier-agnostique** (D2) avec des jeux de
   référence extensibles ;
4. **rien n'a été installé, déployé ni mis en production**, le squelette `src/` est
   resté un squelette, `docs/DATA-MODEL.md` (v1) est resté intact, et le dépôt ne
   contient **aucune donnée réelle** d'entreprise.

Ce qui **n'est pas** un critère : que le produit fonctionne, qu'un serveur existe, qu'un
hébergeur soit retenu, qu'un prix soit fixé. La phase 2 conçoit sur le papier.

---

## 2. Les lots

| # | Lot | Agent | Livrable (chemin exact) | Dépend de | Tâche |
|---|---|---|---|---|---|
| L1 | Proposition de stack technique | `dev-back` | `docs/STACK-PROPOSAL.md` | — | `t_51a45758` |
| L2 | Hébergement France et analyse des trois options de confidentialité | `infra` | `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` | — | `t_522cd6f9` |
| L3 | Modèle de données v2 (multi-client, chiffrement, double facturation, métier-agnostique) | `dev-back` | `docs/DATA-MODEL-V2.md` | — | `t_a4173773` |
| L4 | Spécification fonctionnelle mise à jour (D1, D2, D3) | `docs` | `docs/SPEC-MVP-V2.md` | — | `t_a73f3225` |
| L5 | Nomenclature de référence généraliste | `batiment` | `docs/NOMENCLATURE-REFERENCE.md` | — | `t_6a41441a` |
| L6 | Revue de sécurité et de conformité des choix | `qa` | `docs/REVUE-SECURITE.md` | **L2, L3** | `t_123f9034` |

Aucun lot hors de cette liste. Le hors-périmètre de la phase (implémentation, serveur
réel, paiement/Stripe, mémoire technique rédigée automatiquement, veille, dépôt de pli,
portail acheteur public) est recopié dans le corps de **chaque** tâche enfant.

---

## 3. Décisions structurantes prises par l'orchestrateur

Ces décisions sont **écrites dans les tâches enfants** : deux lots ne doivent jamais
avoir à trancher le même point, et un agent ne voit pas les cartes de ses voisins.

- **D-C1 — Format du jeu de référence.** Un jeu de référence est un *namespace* (chaîne
  en minuscules, `.` comme séparateur ; les jeux métier sont préfixés `metier.`, ex.
  `metier.etancheite`) contenant des valeurs décrites par : `code`, `libelle`,
  `parent_code`, `ordre`, `domaine`, `source`, `statut`. `docs/NOMENCLATURE-REFERENCE.md`
  décrit **des contenus** dans ce format et **ne définit aucun schéma** ; le conteneur
  générique appartient à `docs/DATA-MODEL-V2.md`. Divergence de structure : c'est
  `DATA-MODEL-V2.md` qui fait foi, la nomenclature qui fait foi pour le contenu.
- **D-C2 — Autorité sur la formulation de confidentialité.** Le seul document habilité à
  énoncer une garantie de confidentialité est `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.
  Tout autre livrable ne peut qu'en **citer un extrait textuel** ou écrire la mention
  « à compléter après validation de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` ». Cette
  règle est vérifiée par L6.
- **D-C3 — Périmètre documentaire.** La phase 2 écrit des documents et **ne touche pas**
  à `src/`, ni à `README.md`, ni à `PROJECT.md`, ni à `docs/DATA-MODEL.md` (v1, archivé
  comme référence de phase 1). Interdiction d'installer, déployer ou exécuter quoi que
  ce soit.
- **D-C4 — Les constats de la phase 1 sont des exigences d'entrée.** L3 doit traiter
  nommément C1, C2, C3, C4, C9, C10 ; L4 traite C7 (source non consultable) ; L6 vérifie
  le traitement des dix constats. Un constat réfuté doit être réfuté avec preuve.
- **D-C5 — Portabilité du modèle.** `docs/DATA-MODEL-V2.md` ne présuppose aucun moteur :
  il reste portable entre SQLite et un SGBD hébergé, et toute indication de type SQL est
  indicative. Motif : la stack n'est validée qu'après décision d'Anthony (D5), et L1 et
  L3 avancent en parallèle. L6 vérifie la cohérence entre `STACK-PROPOSAL` et
  `DATA-MODEL-V2` sans exiger que l'un dépende de l'autre.
- **D-C6 — Aucune option de confidentialité n'est tranchée en interne.** L2 recommande,
  L3 regroupe dans une section dédiée « points dépendant de l'option retenue » tout ce
  que le modèle doit changer selon l'option, sans en choisir une. Le choix appartient à
  Anthony.

---

## 4. Ordre d'exécution et parallélisme

**Vague 1 — cinq lots en parallèle, immédiatement :** L1, L2, L3, L4, L5.
Ils écrivent cinq fichiers distincts et n'ont aucune dépendance entre eux. Les deux
points de recouvrement connus sont neutralisés par D-C1 (structure ↔ contenu du jeu de
référence), D-C2 (confidentialité ↔ spécification) et D-C5 (modèle ↔ stack).

**Vague 2 — après L2 et L3 :** L6 (revue de sécurité).
Elle a besoin du verdict de confidentialité (L2) et du modèle v2 (L3) pour vérifier le
cloisonnement entre clients et l'honnêteté des formulations. Elle est chaînée par
dépendance de tableau : elle reste en `todo` jusqu'à la fin de L2 et L3.

**Recouvrement à surveiller entre L3 et L5 :** c'est exactement le risque qui s'est
matérialisé en phase 1 (constat C2 : granularité de traçabilité incohérente). Le partage
est explicite et écrit dans les deux cartes : **L3 dit comment c'est structuré, L5 dit
quel est le contenu.** Aucun des deux ne redéfinit le champ de l'autre.

**Recouvrement à surveiller entre L1 et L3 :** la persistance. Réglé par D-C5 : le modèle
ne dépend d'aucun moteur, la proposition de stack décrit un moteur sans réécrire le
modèle.

**Ordre d'écriture des fichiers :** chaque lot écrit uniquement son chemin. Aucun lot ne
modifie le fichier d'un autre.

---

## 5. Risques

| Risque | Probabilité | Impact | Parade |
|---|---|---|---|
| **Tension D6 : « seul le client a accès à ses données » est techniquement intenable en même temps que l'analyse côté serveur** | Certaine (connue, actée par Anthony) | Élevé — une promesse intenable engage l'éditeur et se retourne à la commercialisation | L2 doit rendre un verdict explicite par option (vrai par construction / sous conditions / faux au sens strict) ; D-C2 interdit toute autre formulation ; L6 chasse les écarts dans tous les livrables |
| **Sous-traitant du modèle d'IA hors Union européenne** : pour analyser un DCE, le texte part chez un prestataire (souvent américain), ce qui contredit « hébergé en France » au sens strict | Élevée | Élevé — transfert de données hors UE, RGPD, promesse d'hébergement France | L2 doit tracer le chemin complet de la donnée **jusqu'au fournisseur du modèle**, nommer ce maillon, et proposer la parade (fournisseur européen, ou clauses contractuelles + information du client). Décision renvoyée à Anthony (question 2) |
| Modèle économique et hébergement seulement « prévus » dans le papier, mais **un lot implémente** un abonnement, un paiement ou un schéma appliqué | Moyenne | Élevé — dépassement de périmètre, dette | Hors-périmètre recopié dans chaque carte ; D-C3 interdit toute écriture hors livrable ; L6 constate |
| Un livrable affirme une garantie de confidentialité non tenue (recopie d'une formulation commerciale) | Moyenne | Élevé — même conséquence que le risque 1, mais par négligence | D-C2 (citation seule) ; L6 confronte chaque phrase de confidentialité au verdict de L2 |
| Les constats majeurs C1, C2, C3 sont ignorés et le modèle v2 les reconduit | Moyenne | Élevé — la phase 3 construirait sur un modèle incomplet | D-C4 : L3 traite chaque constat nommément avec preuve ; L6 vérifie point par point |
| Divergence structure/contenu entre le modèle v2 (L3) et la nomenclature (L5) | Moyenne | Moyen — reprise du schéma plus tard | D-C1 : format imposé, écrit dans les deux cartes ; arbitrage explicite (L3 fait foi pour la structure) |
| Divergence stack/modèle entre L1 et L3, lancés en parallèle | Moyenne | Moyen — traduction de persistance à refaire | D-C5 : modèle portable, aucun moteur présupposé ; L6 vérifie la cohérence |
| Une option de confidentialité est tranchée par un agent au lieu d'être proposée à Anthony | Moyenne | Moyen — décision structurante prise sans le décideur | D-C6 ; chaque carte exige une section « décision demandée à Anthony » |
| Prix d'hébergeur ou de modèle d'IA inventés faute de budget connu | Élevée | Moyen — chiffrage faux, décision faussée | Règle de sourçage dans chaque carte : source exacte ou « à vérifier » ; question 3 posée à Anthony ; fourchettes assumées comme telles |
| L6 lancée trop tôt et revue faite sur un modèle ou une option encore mouvants | Faible (chaînage en place) | Faible — travail à refaire | Parents L2 et L3 posés sur la carte |
| Données réelles d'entreprise (bilan, CV, SIRET, IBAN) déposées dans le dépôt | Faible | Élevé — RGPD, secret des affaires | Règle « exemples fictifs signalés » dans chaque carte ; `data/` déjà ignoré par git |
| Conflit d'intérêts du porteur (agent de la collectivité / éditeur de l'outil) perdu de vue | Faible | Élevé — risque juridique réel, bloquant à la commercialisation | D4 : risque réaffirmé dans ce plan, dans `docs/REVUE-SECURITE.md` et à chaque fin de phase ; validation juriste reportée en fin de projet, séparation des casquettes immédiate |

---

## 6. Inconnues à lever auprès d'Anthony

Ces questions **ne bloquent pas** le lancement de la phase 2 : chaque lot a de quoi
travailler en posant les options. Elles bloquent la **validation** de la phase 2 et, pour
certaines, la phase 3.

**Bloquantes pour clore la phase 2**

1. **Option de confidentialité retenue (A, B ou C de `docs/DECISIONS.md` § D6).** Et si
   l'option retenue est l'option B : acceptez-vous la formulation honnête, c'est-à-dire
   écrire noir sur blanc que le serveur — et le prestataire technique — peuvent
   techniquement accéder aux documents pendant le traitement ? Le cas échéant, la phrase
   « seul le client a accès à ses données » devra être remplacée partout.
2. **Fournisseur du modèle d'IA.** Acceptez-vous qu'un prestataire hors Union européenne
   reçoive les documents du client (sous clauses contractuelles), ou imposez-vous un
   fournisseur européen ou français — au prix éventuel d'une qualité d'analyse ou d'un
   coût différents ? Ce point est aussi structurant que le chiffrement pour D6.
3. **Budget mensuel cible** (hébergement + consommation du modèle d'IA), même en
   fourchette large. Sans lui, les options ne sont comparables qu'en ordres de grandeur
   non validés, et les lots écriront « à vérifier » partout.
4. **Entité qui portera le contrat et facturera** (personne physique, société en cours de
   constitution ?). D4 renvoie le portage juridique à la fin du projet, mais l'entité
   détermine le responsable de traitement RGPD et le rattachement de la facturation (D3).

**Ne bloquent pas la phase 2, mais la phase 3**

5. **Ambition commerciale de départ** : le produit est-il vendu aux seules entreprises du
   bâtiment (D1) alors que la bibliothèque est généraliste (D2) ? Quelle formulation
   retenir publiquement ?
6. **Seuil d'alerte d'échéance** (nombre de jours avant expiration d'une assurance ou
   d'une certification) ou décision de ne pas fixer de seuil. Constat ouvert en phase 1
   (`docs/DATA-MODEL.md` § 16 point 3).
7. **Mémoire technique type dans le MVP** : collectée et stockée, ou hors MVP ? Constat C6
   du plan de test, resté non tranché.
8. **Durée de conservation** des documents et de la bibliothèque après résiliation d'un
   client, et sort des données à la résiliation (export, suppression). À faire trancher
   par le juriste avec D4, mais le modèle v2 doit au moins en prévoir le champ.

**Dépendance externe non maîtrisée (à signaler maintenant)**

- **L'expertise juridique (D4)** n'est pas planifiable ici : elle est reportée à la fin du
  projet par décision d'Anthony. Elle reste **bloquante pour la commercialisation**, pas
  pour le développement. Elle est réaffirmée dans `docs/REVUE-SECURITE.md`.
- **Les tarifs des hébergeurs et des fournisseurs de modèles** sont des données publiques
  qui évoluent : toute fourchette citée doit être datée et « à revérifier » avant décision.

---

## 7. Estimation

Estimée en **passes d'agent** (une passe = un tour de travail effectif), comme en phase 1 :
la phase 2 n'a pas de calendrier fixé.

- L1 (stack) : 1 à 2 passes. Base : dossier déjà écrit, comparaison de scénarios.
- L2 (confidentialité) : 2 à 3 passes. Le plus lourd : il doit tracer le chemin réel de
  la donnée jusqu'au fournisseur du modèle, sourcer les prix ou écrire « à vérifier », et
  rédiger pour un non-spécialiste.
- L3 (modèle v2) : 3 à 4 passes. Le plus lourd techniquement : multiplie le modèle v1 par
  multi-client, chiffrement, double facturation, métier-agnostique, plus six constats à
  traiter.
- L4 (spec v2) : 1 à 2 passes.
- L5 (nomenclature) : 1 à 2 passes. Base : `docs/DONNEES-METIER-BATIMENT.md` existe déjà,
  il s'agit de le reformater en jeu de référence et d'ouvrir la porte aux autres métiers.
- L6 (revue) : 2 à 3 passes. Analyse de menace, cloisonnement, RGPD, confrontation des
  formulations.

Total : **10 à 16 passes**, deux vagues. Aucune dépendance externe maîtrisable n'est
requise ; le seul tiers nécessaire est le juriste, et il est reporté par décision.

---

## 8. Suivi

Chaque lot est une tâche du board `ia-consultations`, liée à la tâche racine
`Phase 2 — architecture technique et décisions structurantes`, avec le dossier de travail
`/Users/pause/Projets/ia-consultations-publiques`. Les livrables arrivent dans ce dossier.
`plan` relit et arbitre en fin de phase, en confrontant les livrables à
`docs/DECISIONS.md` et aux constats de `docs/PLAN-DE-TEST.md`.

**À faire en fin de phase 2, pour ne pas perdre D4 de vue :** réaffirmer que le portage
juridique reste ouvert, documenté et bloquant pour la commercialisation, et que la
séparation des casquettes (aucune donnée ni influence issue de la collectivité) reste une
règle immédiate.
