# SPEC-MVP-V2 — Spécification fonctionnelle du MVP, mise à jour (D1, D2, D3)

> **Statut : phase 2 — architecture technique et décisions structurantes.**
> Ce document met à jour `docs/SPEC-MVP.md` (phase 1), qui **reste intact et archivé**.
> Il ne décrit aucun code livré, aucun déploiement, aucune mise en production.
> Auteur : agent `docs`. Date : 30 septembre 2026.

Ce document **remplace** `docs/SPEC-MVP.md` comme référence fonctionnelle à partir de la
phase 2. La v1 est conservée : elle trace l'état du raisonnement avant les décisions d'Anthony.

Ce qui change par rapport à la v1, en trois lignes : la cible est réécrite pour
l'**entreprise candidate** (D1), la bibliothèque devient **métier-agnostique** à
nomenclatures extensibles (D2), et le modèle économique **abonnement + facturation au
dossier** est intégré côté utilisateur (D3). Les trois briques et la ligne rouge ne bougent pas.

---

## Sources de ce document

Toute source citée ici est **un fichier du dépôt** (ou une URL stable). Aucun identifiant de
carte Kanban n'est utilisé comme source — voir la note de correction C7 plus bas.

| Affirmation de ce document | Source (fichier du dépôt) |
|---|---|
| Trois briques du MVP, ligne rouge, périmètre | `PROJECT.md` § 2, § 5, § 7 ; `README.md` « Ligne rouge », « Périmètre du MVP » |
| Informations à collecter sur l'entreprise (neuf familles) | `PROJECT.md` § 3 |
| Parcours de bout en bout d'origine (6 étapes) | `PROJECT.md` § 4 |
| Cible « entreprise candidate » ; acheteur public hors périmètre | `docs/DECISIONS.md` § D1 |
| Bibliothèque généraliste, nomenclatures extensibles | `docs/DECISIONS.md` § D2 |
| Double mode de facturation | `docs/DECISIONS.md` § D3 |
| Portage juridique, stack, hébergement/confidentialité | `docs/DECISIONS.md` § D4, § D5, § D6 |
| Constats C5, C6, C7 | `docs/PLAN-DE-TEST.md` § 11 |
| Contraintes de phase 2 (hors-périmètre, décisions d'orchestrateur D-C1 à D-C6, questions ouvertes) | `docs/PLAN-PHASE-2.md` § 2, § 3, § 5, § 6 |
| Maquette de l'interface de saisie | `docs/UI-SAISIE.md` |
| Spécification antérieure (archive) | `docs/SPEC-MVP.md` |

**Note de correction du constat C7.** La v1 citait, dans son tableau de sources, un
identifiant de carte Kanban (« carte Kanban L1 `t_1c466d22` »), qui n'est **pas un fichier
du dépôt** et n'est donc pas vérifiable par un relecteur. La v2 ne cite que des fichiers du
dépôt. Voir aussi § 9.

**Aucune norme, aucun seuil, aucun délai légal, aucun prix n'est cité dans ce document.**
Là où une telle source serait nécessaire, il est écrit « à vérifier » et le renvoi au
document compétent (`docs/CONFORMITE-COMMANDE-PUBLIQUE.md` pour les sources administratives)
est indiqué. Ce document n'est pas habilité à énoncer une règle juridique.

---

## 1. Résultat visé et périmètre du MVP

### 1.1 Ce que le MVP doit prouver

Prouver la valeur de l'outil **en supprimant les oublis et les relectures inutiles**, pas en
écrivant à la place de l'entreprise (`PROJECT.md` § 7). Le MVP **ne rédige rien d'engageant** :
il structure la matière existante de l'entreprise, lit un DCE déposé par l'utilisateur, et
signale ce qui manque avant remise.

### 1.2 Les trois briques (inchangées)

| Brique | Nom fonctionnel | Rôle |
|---|---|---|
| A | Bibliothèque d'entreprise | Saisir une fois les informations de l'entreprise, de façon structurée et réutilisable |
| B | Analyse d'un DCE | Lire un DCE déposé par l'utilisateur : pièces exigées, critères, date limite |
| C | Checklist de conformité | Générer la liste des pièces exigées et signaler ce qui manque |

### 1.3 Qui est l'utilisateur — décision D1

**L'utilisateur du produit est l'entreprise candidate** (une entreprise qui répond à des
consultations publiques). C'est une décision d'Anthony (`docs/DECISIONS.md` § D1).

Conséquences tenues par cette spécification :

- L'**acheteur public** (mairie, collectivité, bailleur) est la **source** des consultations.
  Ce n'est **jamais l'utilisateur du produit**.
- Tout ce qui viserait l'acheteur est **hors périmètre** : pas de profil d'acheteur, pas de
  portail côté collectivité, pas de tableau de bord du service acheteur, pas de dépôt de
  consultation côté acheteur. Ces éléments **n'apparaissent dans aucun écran de ce document**.
- Le vocabulaire de la spécification désigne l'utilisateur par « **l'entreprise candidate** »
  (ou « l'entreprise »), et non par « le candidat », « l'acheteur » ou « la collectivité ».

> Ce que la v1 appelait « Acheteur public visé en premier » (§ 7.1 de la v1, options
> collectivités / bailleurs) **disparaît** : la question est tranchée par D1 et n'a plus lieu
> d'être. Il en va de même de la v1 § 7.2 (métier, tranché par D2), § 7.3 (modèle économique,
> tranché par D3), § 7.4 (portage juridique, cadré par D4), § 7.5 (stack, cadrée par D5),
> § 7.6 (hébergement, cadré par D6 et analysé par `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`).

### 1.4 Hors périmètre du MVP (le périmètre ne s'élargit pas)

Ne sont **pas** dans le MVP, ni décrits comme fonctionnalités :

- mémoire technique **rédigée automatiquement** ou assemblée automatiquement ;
- veille et détection d'appels d'offres ;
- dépôt de pli et signature électronique ;
- connexion aux plateformes d'achat public (le DCE est déposé par l'utilisateur) ;
- chiffrage, prix, marge ;
- authentification multi-utilisateurs ;
- **paiement et intégration de paiement** (voir § 5 : D3 est décrit côté utilisateur, sans
  paiement) ;
- mise en production, déploiement ;
- **portail côté acheteur public** (D1, voir § 1.3).

Source : `PROJECT.md` § 7, `README.md` « Périmètre du MVP », `docs/DECISIONS.md` § D1, et le
hors-périmètre recopié dans chaque tâche de phase 2 (`docs/PLAN-PHASE-2.md` § 2).

---

## 2. La frontière entre l'IA et l'humain (ligne rouge)

Cette frontière est une **contrainte de conception**, pas une recommandation. Elle s'applique
aux trois briques.

| L'IA **propose** (brouillon, jamais engageant) | L'humain **valide** (blocage technique) |
|---|---|
| Structurer et ranger les informations saisies | Corriger toute information fausse ou incomplète |
| Extraire d'un DCE les pièces exigées, les critères et la date limite | Vérifier chaque extraction contre le DCE d'origine |
| Signaler une pièce manquante ou une échéance proche | Décider de répondre ou non, et de la suite |
| Proposer un squelette de dossier à pré-remplir | Relire, corriger et **signer** le dossier |

**Ce que le système refuse de faire** (ligne rouge — `PROJECT.md` § 5, `README.md`) :

- Il **ne signe rien** et **ne dépose rien** à la place de l'entreprise.
- Il **n'invente aucune référence, aucun certificat, aucun chiffre**. Tout élément produit
  pointe vers sa source dans la bibliothèque (ou vers l'emplacement du DCE d'origine).
- Il **ne fixe pas le prix**. Le chiffrage reste humain.
- Il **ne garantit aucune conformité**. Il signale des risques.

**La relecture humaine est un blocage technique, pas une recommandation.** Deux verrous la
matérialisent dans le MVP :

1. **Validation de la bibliothèque** : aucun élément de la bibliothèque n'est utilisable dans
   un dossier sans une action humaine explicite (maquette `docs/UI-SAISIE.md` § 9, écran E7).
2. **Validation de l'extraction d'un DCE** : aucun élément extrait par la brique B n'alimente
   la checklist (brique C) avant validation humaine de cet élément (§ 3.3).

**Portée technique du blocage.** Toute sortie de nature à engager l'entreprise (dossier
pré-rempli, exports) porte la mention « brouillon — à relire et signer » et reste inutilisable
comme document final tant qu'un humain ne l'a pas validée. La conception exacte de ce verrou
appartient au modèle (`docs/DATA-MODEL-V2.md`) et à l'interface (`docs/UI-SAISIE.md` et sa
mise à jour) ; ce document en pose l'exigence, pas l'implémentation.

---

## 3. Parcours utilisateur — entreprise candidate

### 3.1 Vue d'ensemble

```
   Brique A                          Brique B                       Brique C
 Bibliothèque                     Analyse du DCE                 Checklist
 d'entreprise                     (déposé par l'utilisateur)     de conformité
      │                                  │                            │
  saisie guidée ───┐               extraction pièces/             croisement
  structurée       │               critères/date limite           + détection
  exportable       │                     │                        des manques
      │            │                     │                            │
      └────────────┴──── validation humaine ────┴────────────────────┘
                                   │
                          relire, corriger et signer
                             par l'entreprise
                          (blocage technique)
```

L'entreprise candidate suit ce parcours. Les étapes « Veille » et « Pré-sélection » de
`PROJECT.md` § 4 restent **hors périmètre du MVP** : l'entreprise apporte elle-même la
consultation qu'elle veut traiter.

### 3.2 Brique A — Bibliothèque d'entreprise

**But.** Recueillir **une fois**, de façon guidée et structurée, la matière première de
l'entreprise, et la rendre exportable et réutilisable (`PROJECT.md` § 3).

**Écrans** (maquette détaillée dans `docs/UI-SAISIE.md`, non réécrite ici) :

| Écran | Rôle |
|---|---|
| E0 | Tableau de bord de la bibliothèque : état global, progression, reprise, manques |
| E1 | Fiche entreprise (identité — socle) |
| E2 | Espace d'une famille d'informations (gabarit) |
| E3 | Formulaire de saisie d'un élément |
| E4 | Dépôt d'un justificatif (pièce + source + validité) |
| E5 | Échéances (certifications, assurances) |
| E6 | Récapitulatif des manques |
| E7 | Relecture humaine bloquante (séquence finale, non court-circuitiable) |

**Parcours.** L'entreprise ouvre sa bibliothèque, remplit les familles une à une (saisie
guidée, reprise possible), joint une pièce quand une preuve est attendue, et peut exporter la
bibliothèque. L'ordre de saisie est **conseillé** (références de chantiers en premier — le
poste le plus rentable, `PROJECT.md` § 3), jamais imposé. Seul l'enchaînement E6 → E7 est
contraint.

**Entrées.** Saisies manuelles guidées ; pièces jointes rattachées à une information ; reprise
d'une saisie enregistrée.

**Sorties.** Bibliothèque structurée et persistée ; un **export** réutilisable ; un état
d'avancement (sections remplies / vides / manquantes).

**Ce que la brique A refuse de faire.** Deviner une valeur manquante ; recalculer ou inventer
un chiffre ; extraire automatiquement une donnée d'un document sans validation humaine ;
afficher les données d'une **autre** entreprise.

> La structure technique de la bibliothèque (champs, types, relations) et le sort de chaque
> famille ne sont **pas définis ici** : ils appartiennent à `docs/DATA-MODEL-V2.md` (structure)
> et à `docs/NOMENCLATURE-REFERENCE.md` (contenu de référence). Voir § 4.

### 3.3 Brique B — Analyse d'un DCE déposé par l'utilisateur

**But.** Lire un DCE (dossier de consultation des entreprises) fourni par l'entreprise
candidate et en extraire trois éléments exploitables : **les pièces exigées**, **les critères**,
**la date limite**.

**Écrans** (niveau fonctionnel — la maquette de saisie `docs/UI-SAISIE.md` ne couvre pas cette
brique, qui n'existait pas en phase 1) :

| Écran | Rôle |
|---|---|
| B0 · Dépôt | L'entreprise dépose elle-même un ou plusieurs fichiers du DCE |
| B1 · Lecture | Le système indique quels fichiers sont lisibles et lesquels ne le sont pas |
| B2 · Extraction proposée | Pièces exigées, critères, date limite — **chaque élément accompagné de sa source** (fichier + emplacement) |
| B3 · Vérification | L'entreprise vérifie, corrige, supprime ou valide chaque élément, contre le DCE d'origine |

**Parcours.**

1. L'entreprise **dépose elle-même** le ou les fichiers du DCE (le système ne va rien chercher :
   pas de veille, pas de connexion à une plateforme d'achat, § 1.4).
2. Le système analyse le contenu et propose une extraction : pièces exigées, critères (et
   pondérations **si et seulement si** elles figurent au document), date limite.
3. Le système affiche, **pour chaque élément extrait, sa source** : fichier et emplacement.
4. L'entreprise **vérifie chaque élément** contre le document d'origine, puis valide, corrige
   ou supprime.
5. Seule l'extraction **validée par un humain** alimente la brique C (§ 2, verrou n° 2).

**Entrées.** Un ou plusieurs fichiers déposés par l'entreprise (DCE et annexes). Les formats
de fichiers acceptés restent **à fixer** : la v1 les déléguait au modèle de données, et le
constat **C5** (`docs/PLAN-DE-TEST.md` § 11) a relevé que la délégation n'avait pas de
destinataire. Voir § 9 (point à vérifier) et § 7 (question à Anthony).

**Sorties.**

- Liste des **pièces exigées** (administratives et techniques), chacune liée à sa source.
- Liste des **critères** d'attribution, avec pondérations si et seulement si elles figurent
  dans le DCE ; sinon la pondération est marquée « non trouvée dans le document ».
- **Date limite** de remise, avec sa source.
- Chaque sortie porte une mention de confiance ou un renvoi à sa source ; aucune sortie n'est
  présentée comme certaine avant vérification humaine.

**Cas d'erreur et comportements attendus.**

| Cas | Comportement attendu |
|---|---|
| Fichier illisible (scan sans texte exploitable) | Signalé « non analysable » ; le système **ne devine pas** le contenu et demande une version lisible |
| DCE volumineux ou en plusieurs fichiers | Chaque fichier est traité ; le système indique lesquels ont été lus et lesquels ne l'ont pas été |
| Élément introuvable (pas de date limite, pas de critères) | Le système écrit explicitement « non trouvé dans le document » ; il **ne comble pas le vide** |
| Plusieurs dates ou plusieurs jeux de critères | Le système expose les occurrences avec leur source ; l'humain tranche |
| Contenu ambigu ou contradictoire | Signalé comme point à vérifier ; le système ne tranche pas |
| Extraction incertaine | Marquée « à vérifier », jamais présentée comme un fait |

**Ce que la brique B refuse de faire.** Inventer une pièce, un critère, une pondération ou une
date absents du document ; présenter une information comme certaine sans source citée ; se
connecter à une plateforme d'achat pour récupérer un DCE ; **croiser les DCE de plusieurs
entreprises candidates** ou laisser fuiter une information d'une entreprise vers une autre
(`PROJECT.md` § 6 — secret des affaires et égalité des candidats).

### 3.4 Brique C — Checklist de conformité

**But.** Générer, à partir de l'extraction **validée** du DCE (brique B) croisée avec la
bibliothèque (brique A), la **liste des pièces exigées** et **ce qui manque** avant remise.

**Écrans** (niveau fonctionnel) :

| Écran | Rôle |
|---|---|
| C0 · Lancement | Depuis une consultation analysée, l'entreprise lance la génération de la checklist |
| C1 · Checklist | Une ligne par pièce exigée : présente / manquante / à vérifier, avec la source de l'exigence |
| C2 · Manques | Le résumé de ce qui doit encore être fourni avant remise |
| C3 · Échéances | Pièces ou informations dont la date est proche ou dépassée |

**Parcours.** L'entreprise lance la génération ; le système confronte la liste des pièces
exigées à ce que contient la bibliothèque ; l'entreprise traite les manques (compléter la
bibliothèque ou décider de ne pas répondre) puis relance la vérification.

**Entrées.** La liste validée des pièces exigées et la date limite (sortie de la brique B) ;
la bibliothèque d'entreprise (brique A).

**Sorties.** Une checklist (une ligne par pièce, avec statut et source) ; un résumé des
manques ; un signalement d'échéances.

> **Ce que cette sortie n'est pas.** La checklist est un **outil d'aide à la relecture**, pas un
> certificat de conformité. Le système ne garantit aucune conformité (`PROJECT.md` § 5).

**Cas d'erreur et comportements attendus.**

| Cas | Comportement attendu |
|---|---|
| Pièce exigée absente de la bibliothèque | Statut « manquante » ; le système **ne fabrique pas** la pièce |
| Pièce présente mais douteuse (échéance passée, incohérence) | Statut « à vérifier » avec la raison ; le système ne la déclare pas valide |
| Extraction de DCE incomplète | La checklist indique qu'elle repose sur une extraction partielle ; les éléments non lus sont signalés |
| Incohérence entre deux sources (ex. date différente) | Les deux valeurs et leur source sont exposées ; le système ne choisit pas |
| Bibliothèque vide ou très incomplète | La checklist le reflète (beaucoup de « manquante ») ; le système n'invente rien pour boucher les trous |

**Ce que la brique C refuse de faire.** Garantir ou certifier la conformité d'un dossier ;
inventer ou produire une pièce manquante ; trancher une ambiguïté à la place de l'humain ;
signer, valider juridiquement ou déposer le dossier.

### 3.5 Fin de parcours

L'étape « Relecture et signature » de `PROJECT.md` § 4 (l'entreprise valide, corrige, signe,
le dossier part) est **hors MVP** : pas de dépôt de pli, pas de signature électronique. Le MVP
s'arrête à la checklist (brique C), mais il laisse l'entreprise en position de relire et de
signer **hors** l'outil, sans jamais signer à sa place.

---

## 4. Impact de D2 (généraliste) sur le parcours

**Décision.** Le produit est **généraliste dès le départ** (`docs/DECISIONS.md` § D2) : la
bibliothèque ne présume d'aucun métier. Sa structure est **métier-agnostique** ; les
nomenclatures et les champs de référence sont **extensibles**.

### 4.1 Ce que l'utilisateur voit

- **Ce qui est proposé par défaut.** L'entreprise trouve, à l'ouverture d'un champ de
  référence (familles d'activité, natures de travaux, types de certification, unités, etc.),
  un **jeu de valeurs par défaut** issu d'un jeu de référence. Le premier jeu métier est
  `metier.etancheite` (bâtiment / étanchéité, issu du travail de l'agent `batiment`) : il est
  livré dans `docs/NOMENCLATURE-REFERENCE.md` **à titre de jeu de départ, pas de structure
  imposée** (`docs/DECISIONS.md` § D2).
  Les libellés métier cités dans la maquette de saisie (par ex. Qualibat, RGE, MASE, ISO, ou
  « échafaudages ») sont des **exemples** de ce jeu, pas des champs figés.
- **Ce que l'entreprise peut étendre.** Elle peut **ajouter ses propres valeurs** à un champ
  de référence sans attendre une modification du produit. Une valeur ajoutée est marquée
  comme **proposée par l'entreprise** (elle n'est pas « standard »), et reste modifiable.
- **Ce qui n'est pas imposé.** Aucun vocabulaire métier n'est obligatoire : une entreprise
  d'un autre métier remplit la même bibliothèque avec ses propres valeurs.

### 4.2 Renvois (ce document ne définit ni la structure ni le contenu)

- **Contenu et valeurs de référence** : `docs/NOMENCLATURE-REFERENCE.md` (jeux de référence,
  dont le premier jeu métier ; format imposé par la décision d'orchestrateur **D-C1** —
  `docs/PLAN-PHASE-2.md` § 3).
- **Structure** (comment un champ de référence extensible est porté par le modèle, comment une
  valeur ajoutée par l'entreprise est stockée et tracée) : `docs/DATA-MODEL-V2.md`.

Ce document **ne redéfinit ni le schéma ni le contenu** : une autre tâche en est propriétaire
(partage explicite `docs/PLAN-PHASE-2.md` § 4 — « L3 dit comment c'est structuré, L5 dit quel
est le contenu »).

### 4.3 Ce que D2 change dans le parcours

- La valeur immédiate est plus faible au départ pour un métier non bâti (bibliothèque plus
  souple, donc plus vague) : c'est une conséquence assumée de D2.
- L'entreprise doit pouvoir **créer une valeur de référence manquante** en cours de saisie,
  sans quitter son formulaire — sinon D2 resterait théorique.
- Les listes qui étaient closes dans la maquette de saisie deviennent **extensibles** : voir
  l'annexe A.

---

## 5. Impact de D3 (double facturation) côté utilisateur, sans paiement

**Décision.** Le modèle économique combine **abonnement mensuel** et **facturation ponctuelle
d'un projet déposé** (`docs/DECISIONS.md` § D3). Le produit doit savoir **compter les deux** et
**rattacher un dossier à sa facturation**.

### 5.1 Ce que cela change pour l'entreprise candidate

- **Un abonnement** donne accès au socle fonctionnel de façon continue : la bibliothèque
  d'entreprise (brique A) et son export sont accessibles tant que l'abonnement est actif.
- **Un dossier déposé** (une consultation traitée de bout en bout — brique B puis brique C)
  est un **objet compté**, rattaché à une facturation. L'utilisateur voit que son dossier est
  rattaché à une facturation ponctuelle, en plus de son abonnement.
- **Ce qui est inclus dans l'abonnement et ce qui déclenche la facturation au dossier** doit
  être explicitable par l'outil (par ex. « ce dossier sera facturé » avant de le travailler),
  mais **le périmètre exact** (nombre de dossiers inclus, etc.) **n'est pas tranché dans cette
  phase** — voir § 7, question à Anthony.

### 5.2 Ce qui reste hors périmètre

- **Aucune intégration de paiement, aucun prestataire, aucun montant** n'est décrit ici
  (`docs/DECISIONS.md` § D3, `docs/PLAN-PHASE-2.md` § 2). Aucun prix n'est inventé.
- Aucun écran de paiement, aucun bouton d'achat, aucune page de tarifs n'existe dans le MVP.
- Le rattachement d'un dossier à sa facturation relève de la **structure** décrite par
  `docs/DATA-MODEL-V2.md` (qui prévoit les deux modes) ; ce document en décrit seulement
  l'effet visible pour l'entreprise.

---

## 6. Confidentialité

**À COMPLÉTER après validation de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`**

À la date d'écriture de ce document (30 septembre 2026), le document
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` **n'existe pas encore** : il est produit par la
tâche parallèle L2 (agent `infra`, `docs/PLAN-PHASE-2.md` § 2). Conformément à la décision
d'orchestrateur **D-C2** (`docs/PLAN-PHASE-2.md` § 3), **ce document n'énonce aucune garantie
de confidentialité** : il ne peut ni la créer ni la reformuler.

Ce qui sera intégré ici, une fois L2 livré : un **extrait textuel, mot pour mot, sans
reformulation ni extension**, de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`, portant sur le
traitement des documents de l'entreprise candidate.

**Interdiction tenue par ce document.** Aucune formulation du type « seul le client a accès à
ses données » n'est reprise ici : tant que `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` n'a pas
rendu son verdict (vraie par construction / vraie sous conditions / fausse au sens strict),
cette phrase ne peut pas être affirmée (`docs/DECISIONS.md` § D6 décrit précisément la tension ;
`docs/PLAN-PHASE-2.md` § 5 en fait un risque explicite).

**Ce qui est vrai par construction, et ce qui ne l'est pas.** Le produit, en l'état du
périmètre, **lit** les documents de l'entreprise pour produire une analyse : le serveur voit
donc les documents **pendant le traitement**. Prétendre le contraire serait une promesse que
l'architecture ne tient pas. Les contraintes fermes d'Anthony (hébergement en France,
chiffrement au repos, cloisonnement entre entreprises, aucune donnée client dans un
entraînement de modèle — `docs/DECISIONS.md` § D6) sont des **objectifs actés** ; leur tenue
technique et la formulation exacte de ce qui peut être garanti à l'entreprise candidate sont
du ressort exclusif de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.

---

## 7. Décisions demandées à Anthony

Questions restées ouvertes à l'issue de cette mise à jour. Réponse courte attendue.

1. **Mémoire technique type dans le MVP — collectée et stockée, ou hors MVP ?**
   *(constat C6, `docs/PLAN-DE-TEST.md` § 11)*
   - **Option A — incluse, collectée et stockée seulement.** L'entreprise range dans la
     bibliothèque des textes déjà rédigés (famille 9 de `PROJECT.md` § 3). Le MVP **ne les
     rédige pas** et **ne les assemble pas**. Conséquence : la valeur « bibliothèque » est plus
     complète dès le départ, mais la famille 9 reste du stockage de texte, sans effet visible
     avant la phase 3. C'est l'état actuel de la maquette `docs/UI-SAISIE.md` (Famille 9, N3).
   - **Option B — hors MVP.** La famille 9 disparaît de la bibliothèque du MVP et sera revue
     en phase 3. Conséquence : périmètre plus net, moins de champs à modéliser maintenant, mais
     l'entreprise ne pourra pas y ranger sa matière existante dès le départ.
   - **Ce que ce document ne tranche pas** : le statut de cette famille reste ouvert (C6).
2. **Formats de fichiers acceptés pour le dépôt d'un DCE** (brique B). Non fixés, et la
   délégation initiale n'avait pas de destinataire (constat **C5**). Question : contraint-on une
   liste courte (par ex. PDF, texte), ou accepte-t-on les formats « bureautiques » courants ?
   Cette réponse conditionne l'écran B0 et la robustesse de l'analyse.
3. **Fenêtre d'alerte des échéances** (nombre de jours avant expiration d'une assurance ou
   d'une certification) : fixer un seuil, ou ne fixer aucun seuil et laisser l'entreprise
   régler « combien de jours avant échéance je veux être alerté » ? Ce seuil est un **réglage
   produit**, sans valeur réglementaire (`docs/UI-SAISIE.md` § 5-E5).
4. **Formulation publique du positionnement.** D1 cible les **entreprises du bâtiment** comme
   client commercial, alors que la bibliothèque est **généraliste** (D2). Quelle formulation
   retenir publiquement (outil « bâtiment » ou outil « généraliste » servi d'abord au bâtiment) ?

> Les quatre questions bloquantes pour **clore la phase 2** (option de confidentialité
> retenue, fournisseur du modèle d'IA, budget, entité qui porte le contrat) relèvent d'autres
> documents et sont listées dans `docs/PLAN-PHASE-2.md` § 6. Ce document ne les traite pas :
> il **renvoie** à `docs/DECISIONS.md` § D4 et § D6 et à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.

---

## 8. Points marqués à vérifier

Tout ce que ce document affirme **sans source consultable au moment de l'écriture**.

| Point | Pourquoi il est à vérifier |
|---|---|
| Structure de la bibliothèque et champs extensibles (D2) | `docs/DATA-MODEL-V2.md` **n'existait pas** à la date d'écriture (tâche parallèle L3). À confronter dès qu'il est livré. |
| Contenu des jeux de référence métier | `docs/NOMENCLATURE-REFERENCE.md` (L5) a été livré **pendant** la rédaction de ce document : le premier jeu métier y est nommé `metier.etancheite`. Reste à confronter à `docs/DATA-MODEL-V2.md` (structure, non encore livré) et à compléter par les jeux transverses que la nomenclature signale comme manquants. |
| Garanties de confidentialité | `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` **n'existait pas** (tâche parallèle L2). Voir § 6. |
| Formats de fichiers acceptés pour un DCE | Non fixés (constat **C5**). Question § 7.2. |
| Format d'export de la bibliothèque et de la liste des manques | Non fixé (constat **C5**). Dépend de `docs/DATA-MODEL-V2.md`. |
| Niveaux d'exigence N1/N2/N3 par champ | Propositions fonctionnelles de `docs/UI-SAISIE.md` § 13 point 5, à confronter à `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` et à `docs/DONNEES-METIER-BATIMENT.md`. |
| Verrou de relecture humaine (support modèle) | Exigence posée ici et dans `docs/UI-SAISIE.md` § 9 ; représentable seulement si `docs/DATA-MODEL-V2.md` ajoute le relecteur, l'horodatage et l'état de validation (constat **C3**, traité par L3). |
| Écrans B0 à C3 (briques B et C) | Décrits ici au niveau fonctionnel ; **aucune maquette** correspondante n'existe (la maquette `docs/UI-SAISIE.md` ne couvre que la bibliothèque). À concevoir en phase ultérieure. |
| Nombre de dossiers inclus dans l'abonnement (D3) | Non tranché (question § 7, et périmètre exact à préciser). |
| Toute norme, tout seuil, tout délai légal, tout prix | **Aucun n'est cité** dans ce document. Là où une source serait nécessaire : « à vérifier » et renvoi à `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` (sources administratives) ou à un juriste (portage juridique, D4). |
| Pérennité des exemples | Aucun exemple réel. Toute donnée d'illustration dans le dépôt doit rester **fictive et signalée** (règle rappelée par `docs/SPEC-MVP.md` § 8 et `PROJECT.md` § 6). |

---

## Annexe A — Ce que D1 et D2 changent dans `docs/UI-SAISIE.md`

`docs/UI-SAISIE.md` **n'est pas réécrite** dans cette phase (ce n'est pas demandé ici). Cette
annexe liste les **libellés, champs et vocabulaire** à ajuster lors de sa prochaine mise à
jour, pour la rendre conforme à D1 et D2. Chaque point renvoie à sa source.

**Effet de D1 (cible entreprise candidate)**

| Élément de `docs/UI-SAISIE.md` | À ajuster |
|---|---|
| Vocabulaire général (« l'utilisateur », « la fiche ») | Désigner explicitement **l'entreprise candidate** comme utilisateur. L'acheteur public n'apparaît nulle part comme utilisateur (D1). |
| Champ « Maître d'ouvrage » (Famille 5, Références de chantiers) | **À conserver** : c'est le client passé de l'entreprise, pas l'utilisateur du produit. Aucun écran côté acheteur n'existe ni ne doit apparaître. |
| Bandeau de la bibliothèque / E0 | Vérifier qu'aucun libellé ne suggère un portail côté collectivité (D1). |
| Mentions de dépôt / signature | Déjà absentes : aucun bouton « déposer », « envoyer » ou « signer ». À maintenir (ligne rouge, § 2). |

**Effet de D2 (généraliste, valeurs extensibles)**

| Élément de `docs/UI-SAISIE.md` | À ajuster |
|---|---|
| E1a — « Forme juridique » : liste déroulante de formes juridiques **génériques**, liste à valider (§ 13 point 1) | La liste devient un **jeu de référence extensible** plutôt qu'une liste close codée en dur : l'entreprise peut ajouter une valeur (D2). Le contenu du jeu vient de `docs/NOMENCLATURE-REFERENCE.md`. |
| Famille 4 — libellés cités « Qualibat, RGE, MASE, ISO » (recopiés de `PROJECT.md` § 3) | Ce sont des **exemples du jeu de référence bâtiment**, pas des champs figés. À reformuler comme « valeurs de référence (extensibles) ». |
| Famille 3 — « Type d'assurance (décennale, responsabilité civile…) » | Idem : valeurs de référence extensibles (D2), le vocabulaire décennale/RC étant propre au bâtiment. |
| Famille 7 — « échafaudages », parc, engins | Vocabulaire métier à présenter comme **exemples** du jeu de départ, pas comme structure imposée. |
| Famille 5 — « étanchéité toiture » (exemple fictif) | Rester un exemple du jeu bâtiment ; ne pas en faire un champ de schéma. |
| E4 — « Nature de la pièce » : `attestation, certificat, bilan, CV, photo, autre` (6 valeurs) | Deux écarts déjà relevés : la liste d'écran diverge de `type_document` du modèle (constat **C4**) et, sous D2, elle doit être **extensible** (D2). À aligner sur `docs/DATA-MODEL-V2.md`. |
| Toutes les listes fermées de la maquette | Deviennent des **nomenclatures modifiables/ajoutables** par l'entreprise (D2). Le mécanisme de création d'une valeur manquante en cours de saisie reste à décrire dans l'interface. |
| Famille 9 — Mémoire technique type | Statut **non tranché** (constat **C6**) : la maquette la présente en N3 ; à aligner sur la réponse d'Anthony (§ 7.1). |
| Renvois internes à `docs/DATA-MODEL.md` (§ 2.2, § 4, § 5, § 6-14) | À reporter sur `docs/DATA-MODEL-V2.md` : la maquette s'alignait sur le modèle v1. Les points ouverts de `docs/UI-SAISIE.md` § 13 (mapping interface ↔ modèle, niveaux N1/N2/N3) restent à re-vérifier contre la v2. |

---

## Annexe B — Ce qui a changé par rapport à `docs/SPEC-MVP.md` (v1)

| Sujet | v1 (phase 1) | v2 (phase 2) |
|---|---|---|
| Utilisateur / cible | indécis ; § 7.1 proposait « acheteur public visé en premier » (collectivités ou bailleurs) | **entreprise candidate** ; l'acheteur public est hors périmètre (D1, § 1.3) |
| Métier | § 7.2 posait la question « un seul métier ou généraliste » | **généraliste**, nomenclatures extensibles (D2, § 4) |
| Modèle économique | § 7.3 posait trois options non tranchées | **abonnement + facturation au dossier**, décrit côté utilisateur, sans paiement (D3, § 5) |
| Décisions ouvertes (§ 7 de la v1) | six décisions listées comme non tranchées | **retirées** : D1 à D6 les tranchent (`docs/DECISIONS.md`) ; subsistent les questions § 7 |
| Confidentialité | § 7.6 : localisation et fournisseur « à décider » | renvoi unique à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` avec mention « à compléter » ; **aucune garantie affirmée** (§ 6) |
| Sources | citait une carte Kanban (`t_1c466d22`) — non consultable (constat C7) | **uniquement des fichiers du dépôt** |
| Brique B | formats de DCE « à fixer par L2 » | délégation sans destinataire relevée (C5) : traitée en question à Anthony et en point à vérifier (§ 7.2, § 8) |
| Mémoire technique type | note « à confirmer par Anthony » (C6) | maintenu **ouvert**, avec les deux options et leurs conséquences (§ 7.1) |
| Écrans | renvoyait à `docs/UI-SAISIE.md` (bibliothèque seulement) | écrans de la bibliothèque **+ niveau fonctionnel** des briques B et C (§ 3.3, § 3.4), maquettes à concevoir |
| Trois briques, ligne rouge, hors-périmètre | posés | **repris sans affaiblissement** |

---

*Fin du document. Lot L4 — agent `docs`. Aucun composant, aucune page et aucun code exécutable
ne fait partie de ce livrable. `docs/SPEC-MVP.md` (v1) reste intact.*
