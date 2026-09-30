# SPEC-MVP — Spécification fonctionnelle du MVP

> **Statut : phase 1 — cadrage.** Ce document décrit ce que le MVP *doit* faire.
> Il ne décrit aucun code livré, aucun déploiement, aucune mise en production.
> Auteur : agent `docs`. Date : 30 septembre 2026. Board : `ia-consultations`.

## Sources de ce document

| Affirmation de ce document | Source |
|---|---|
| Périmètre du MVP (3 briques), ligne rouge, hors-périmètre | `PROJECT.md` § 5 et § 7 ; `README.md` « Périmètre du MVP » |
| Informations à collecter sur l'entreprise | `PROJECT.md` § 3 |
| Parcours de bout en bout (6 étapes) | `PROJECT.md` § 4 |
| Décisions non tranchées (acheteur, métier, modèle économique, portage) | `PROJECT.md` § 8 ; `docs/PLAN.md` § 5 |
| Risque de confidentialité, RGPD, secret des affaires | `PROJECT.md` § 6 ; `docs/PLAN.md` § 4 |
| Contraintes de périmètre et de sources | carte Kanban L1 (`t_1c466d22`) |

**Toute référence juridique, norme ou seuil précis est volontairement absent de ce
document.** Il n'en cite aucune et n'en invente aucune. Le lot L4
(`docs/CONFORMITE-COMMANDE-PUBLIQUE.md`) est le seul habilité à citer des sources
administratives, et il doit les citer à l'identique ou écrire « à vérifier ».

---

## 1. But du MVP

Prouver la valeur de l'outil **en supprimant les oublis et les relectures**, pas en
écrivant à la place de l'entreprise (`PROJECT.md` § 7).

Autrement dit : le MVP ne rédige rien d'engageant. Il **structure** la matière
existante de l'entreprise, **lit** un DCE déposé par l'utilisateur, et **signale** les
pièces manquantes avant remise.

### 1.1 Les trois briques du MVP

| Brique | Nom fonctionnel | Rôle |
|---|---|---|
| A | Bibliothèque d'entreprise | Saisir une fois les informations de l'entreprise, de façon structurée et exportable |
| B | Analyse d'un DCE | Lire un DCE déposé par l'utilisateur : pièces exigées, critères, date limite |
| C | Checklist de conformité | Générer automatiquement la liste des pièces exigées et signaler ce qui manque |

### 1.2 Hors périmètre du MVP (à ne pas implémenter, à ne pas documenter ailleurs)

Mémoire technique rédigé automatiquement, veille et détection d'appels d'offres, dépôt
de pli, signature électronique, connexion aux plateformes d'achat public, chiffrage /
prix / marge, authentification multi-utilisateurs, paiement, facturation, mise en
production. (Liste recopiée de `PROJECT.md` § 7, `README.md`, et de la carte L1.)

---

## 2. La frontière entre l'IA et l'humain (ligne rouge)

Cette frontière est une **contrainte de conception**, pas une recommandation. Elle
s'applique aux trois briques.

| L'IA **propose** (brouillon, jamais engageant) | L'humain **valide** (blocage technique) |
|---|---|
| Structurer et ranger les informations saisies | Corriger toute information fausse ou incomplète |
| Extraire d'un DCE les pièces exigées, les critères et la date limite | Vérifier chaque extraction contre le DCE d'origine |
| Signaler une pièce manquante ou une échéance proche | Décider de répondre ou non, et de la suite |
| Proposer un squelette de dossier à pré-remplir | Relire, corriger et **signer** le dossier |

**Ce que le système refuse de faire (ligne rouge, `PROJECT.md` § 5 et `README.md`) :**

- Il **ne signe rien** et **ne dépose rien** à la place de l'entreprise.
- Il **n'invente aucune référence, aucun certificat, aucun chiffre**. Tout élément
  produit pointe vers sa source dans la bibliothèque (ou vers la page du DCE d'origine).
- Il **ne fixe pas le prix**. Le chiffrage reste humain.
- Il **ne garantit aucune conformité**. Il signale des risques, il ne promet rien.
- La **relecture humaine est un blocage technique** : aucun élément engageant ne sort
  du système sans validation explicite d'un humain.

**Portée technique de ce blocage :** toute sortie de nature à engager l'entreprise
(dossier pré-rempli, exports) porte la mention « brouillon — à relire et signer » et
reste inutilisable comme document final tant qu'un humain ne l'a pas validée. La
conception exacte de ce verrou relève de L2 (`docs/DATA-MODEL.md`) et L3
(`docs/UI-SAISIE.md`) ; ce document en pose l'exigence, pas l'implémentation.

---

## 3. Brique A — Bibliothèque d'entreprise

### 3.1 But

Recueillir **une fois**, de façon guidée et structurée, la matière première de
l'entreprise, et la rendre exportable et réutilisable. C'est le poste le plus rentable
du produit (`PROJECT.md` § 3 : les références de chantiers nourrissent tout le reste).

### 3.2 Parcours utilisateur

1. L'utilisateur ouvre la bibliothèque de son entreprise.
2. Le système présente les **sections** à remplir, une par une (saisie guidée).
3. Pour chaque section, l'utilisateur saisit les informations demandées ; il peut
   joindre une pièce (fichier) lorsqu'une preuve est attendue.
4. À chaque information, le système affiche la **date de dernière mise à jour** et
   l'origine (saisie manuelle, pièce jointe).
5. L'utilisateur peut enregistrer en cours de route ; la bibliothèque se met à jour
   progressivement.
6. L'utilisateur peut **exporter** la bibliothèque dans un format réutilisable.

### 3.3 Sections de la bibliothèque

Contenu aligné sur `PROJECT.md` § 3. La **structure technique** (champs, types,
relations) appartient à L2 (`docs/DATA-MODEL.md`) ; le **contenu métier** d'une
entreprise d'étanchéité appartient à L5 (`docs/DONNEES-METIER-BATIMENT.md`). Cette
spécification ne fixe que les grandes familles.

| Famille | Ce qu'elle contient (source : `PROJECT.md` § 3) |
|---|---|
| Identité | raison sociale, SIRET, forme juridique, effectif, adresse, coordonnées bancaires, représentant légal |
| Capacités financières | CA des trois derniers exercices, bilans, attestations fiscales et sociales, capacité de production |
| Assurances | décennale, responsabilité civile, dates et montants de garantie |
| Certifications et qualifications | Qualibat, RGE, MASE, ISO — **avec leurs échéances** |
| Références de chantiers | maître d'ouvrage, montant, année, description, nature des travaux, durée, photos |
| Moyens humains | organigramme, effectifs par métier, CV des profils clés |
| Moyens matériels | parc, engins, échafaudages, outillage spécifique |
| Fiches techniques produits | fournisseurs, références, certificats, avis techniques |
| Mémoire technique type | réponses déjà rédigées et acceptées, découpées par chapitre |

> **Note de périmètre.** La ligne « mémoire technique type » figure dans `PROJECT.md`
> § 3 comme contenu de bibliothèque. Le MVP **la collecte et la stocke** (c'est de la
> matière saisie par l'humain), mais **ne la rédige pas et ne l'assemble pas
> automatiquement** : la rédaction automatique du mémoire est hors périmètre (§ 1.2).
> À confirmer par Anthony : faut-il inclure cette famille dans le MVP, ou la reporter ?

### 3.4 Entrées

- Saisies manuelles guidées, champ par champ.
- Pièces jointes (documents, photos) rattachées à une information.
- (Si l'utilisateur revient plus tard) reprise et modification d'informations déjà
  saisies.

### 3.5 Sorties

- Une bibliothèque structurée, persistée, consultable.
- Un **export** réutilisable (format à trancher par L2 — voir § 7 des décisions
  ouvertes).
- Le cas échéant, un état d'avancement : sections remplies, sections vides.

### 3.6 Cas d'erreur et comportements attendus

| Cas | Comportement attendu |
|---|---|
| Champ obligatoire vide | L'information est marquée « manquante » ; le système ne la complète pas de lui-même |
| Format invalide (ex. identifiant mal formé) | Le système refuse l'enregistrement tel quel et demande une correction ; **il ne corrige pas la valeur à la place de l'utilisateur** |
| Information dont l'échéance est dépassée (ex. assurance, certification) | Le système la signale comme « à vérifier » ; il n'invente pas de date de renouvellement |
| Pièce jointe illisible ou corrompue | Le système refuse la pièce et le signale ; il ne devine aucun contenu |
| Saisie interrompue | L'utilisateur peut reprendre plus tard sans perdre le reste |

### 3.7 Ce que la brique A refuse de faire

- Deviner une valeur manquante ou « compléter de mémoire ».
- Recalculer, arrondir ou inventer un chiffre (montant, effectif, date).
- Extraire automatiquement des informations d'un document sans validation humaine.
- Afficher les données d'une **autre** entreprise (cloisonnement par entreprise —
  exigence de `PROJECT.md` § 6).

---

## 4. Brique B — Analyse d'un DCE déposé par l'utilisateur

### 4.1 But

Lire un DCE (dossier de consultation des entreprises) fourni par l'utilisateur et en
extraire trois éléments exploitables : **les pièces exigées**, **les critères**, **la
date limite**.

### 4.2 Parcours utilisateur

1. L'utilisateur **dépose lui-même** un ou plusieurs fichiers du DCE (le système ne va
   pas les chercher : pas de veille, pas de connexion à une plateforme d'achat — § 1.2).
2. Le système analyse le contenu et propose une extraction : liste des pièces exigées,
   critères (et pondérations si elles figurent au document), date limite.
3. Le système affiche, **pour chaque élément extrait, la source** : fichier et
   emplacement dans le DCE (page, section) d'où l'élément provient.
4. L'utilisateur **vérifie chaque élément** contre le document d'origine et valide,
   corrige ou supprime.
5. L'extraction validée alimente la brique C.

### 4.3 Entrées

- Un ou plusieurs fichiers déposés par l'utilisateur (le DCE et ses annexes).
- Formats acceptés : **à fixer par L2** (ce document n'impose pas de liste de formats).

### 4.4 Sorties

- Liste des **pièces exigées** (administratives et techniques), chacune liée à sa source.
- Liste des **critères** d'attribution, avec pondérations **si et seulement si** elles
  figurent dans le DCE. Sinon, la pondération est marquée « non trouvée dans le
  document » — le système ne la reconstitue pas.
- **Date limite** de remise, avec sa source.
- Chaque sortie porte une mention de confiance ou un renvoi à sa source ; aucune sortie
  n'est présentée comme certaine sans vérification humaine.

### 4.5 Cas d'erreur et comportements attendus

| Cas | Comportement attendu |
|---|---|
| Fichier illisible, scanné sans texte exploitable | Le système le signale comme « non analysable » et demande une version lisible ; **il ne devine pas le contenu** |
| DCE volumineux ou composé de plusieurs fichiers | Chaque fichier est traité ; le système indique lesquels ont été lus et lesquels ne l'ont pas été |
| Élément introuvable (pas de date limite visible, pas de critères) | Le système écrit explicitement « non trouvé dans le document » ; **il ne comble pas le vide** |
| Plusieurs dates ou plusieurs jeux de critères | Le système expose les différentes occurrences avec leur source ; l'humain tranche |
| Contenu ambigu ou contradictoire dans le DCE | Le système le signale comme point à vérifier ; il ne tranche pas |
| Extraction incertaine | Marquée « à vérifier », jamais présentée comme un fait |

### 4.6 Ce que la brique B refuse de faire

- Inventer une pièce, un critère, une pondération ou une date absents du document.
- Reconnaître une information comme certaine sans source citée.
- Se connecter à une plateforme d'achat public ou récupérer un DCE à la place de
  l'utilisateur (hors périmètre, § 1.2).
- Croiser les DCE de plusieurs candidats ou laisser fuiter une information d'un
  candidat vers un autre (`PROJECT.md` § 6, secret des affaires et égalité des
  candidats).

---

## 5. Brique C — Checklist de conformité

### 5.1 But

Générer automatiquement, à partir de l'extraction du DCE (brique B) croisée avec la
bibliothèque (brique A), la **liste des pièces exigées** et **ce qui manque** avant
remise.

### 5.2 Parcours utilisateur

1. Depuis une consultation analysée (brique B), l'utilisateur lance la génération de la
   checklist.
2. Le système confronte la liste des pièces exigées à ce que contient la bibliothèque.
3. Le système affiche, pour chaque pièce : **présente** / **manquante** / **à vérifier**,
   avec la source de l'exigence et, si présente, la référence à l'information de
   bibliothèque utilisée.
4. L'utilisateur traite les manques (compléter la bibliothèque, ou décider de ne pas
   répondre) puis relance la vérification.
5. Le système signale également toute **échéance proche ou dépassée** parmi les pièces
   et informations datées de la bibliothèque.

### 5.3 Entrées

- La liste validée des pièces exigées et la date limite (sortie de la brique B).
- La bibliothèque d'entreprise (brique A).

### 5.4 Sorties

- Une **checklist de conformité** : une ligne par pièce exigée, avec son statut
  (présente / manquante / à vérifier) et sa source.
- Un **résumé des manques** : ce qui doit encore être fourni avant remise.
- Un **signalement d'échéances** : pièces ou informations dont la date est proche ou
  dépassée.

> **Ce que cette sortie n'est pas.** La checklist est un **outil d'aide à la
> relecture**, pas un certificat de conformité. Le système ne garantit aucune
> conformité (`PROJECT.md` § 5) : il liste ce qu'il constate, l'humain décide si le
> dossier est bon à déposer.

### 5.5 Cas d'erreur et comportements attendus

| Cas | Comportement attendu |
|---|---|
| Pièce exigée absente de la bibliothèque | Statut « manquante » ; le système **ne fabrique pas** la pièce |
| Pièce présente mais douteuse (échéance passée, incohérence) | Statut « à vérifier » avec la raison ; le système ne la déclare pas valide |
| Extraction de DCE incomplète | La checklist indique qu'elle repose sur une extraction partielle ; les éléments non lus sont signalés |
| Incohérence entre deux sources (ex. date différente) | Le système expose les deux valeurs et leur source ; il ne choisit pas |
| Bibliothèque vide ou très incomplète | La checklist le reflète (beaucoup de statuts « manquante ») ; le système n'invente rien pour « boucher les trous » |

### 5.6 Ce que la brique C refuse de faire

- Garantir ou certifier la conformité d'un dossier.
- Inventer une pièce manquante, ou la produire à partir de rien.
- Trancher une ambiguïté ou une contradiction à la place de l'humain.
- Signer, valider juridiquement ou déposer le dossier.

---

## 6. Parcours de bout en bout (les trois briques enchaînées)

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
                          relecture et signature
                             par l'humain
                          (blocage technique)
```

Étapes, alignées sur `PROJECT.md` § 4 pour la partie couverte par le MVP :

1. **Bibliothèque** (brique A) — la matière de l'entreprise est saisie, structurée.
2. **Analyse** (brique B) — le DCE est déposé, lu, extrait ; l'humain vérifie.
3. **Contrôle** (brique C) — la checklist confronte exigences et bibliothèque.
4. **Relecture et signature** — l'entreprise valide, corrige, signe. Le dossier part.
   **Cette étape est hors MVP** (pas de dépôt, pas de signature électronique) : le MVP
   s'arrête à la checklist, mais il doit laisser l'humain en position de relire.

Les étapes « Veille » et « Pré-sélection » de `PROJECT.md` § 4 sont **hors périmètre du
MVP** (§ 1.2) : pas de recherche automatique d'appels d'offres, pas de score de
pertinence dans cette version.

---

## 7. Décisions ouvertes — options et conséquences (non tranchées)

Ces points sont listés dans `PROJECT.md` § 8 et `docs/PLAN.md` § 5. **Ils ne sont pas
tranchés et ce document ne les tranche pas.** Pour chacun, options et conséquences à
l'échelle du MVP.

### 7.1 Acheteur public visé en premier

- **Option A — collectivités (mairies).** Conséquence : pièces et critères typiques des
  marchés de collectivités ; c'est le voisinage professionnel direct d'Anthony.
- **Option B — bailleurs et établissements publics.** Conséquence : autre nature de
  pièces et de vocabulaire, à refléter dans l'extraction (brique B).

Cette décision conditionne **la liste des pièces typiques et le vocabulaire d'extraction**
(brique B), donc le contenu des règles de conformité (dépendance à L4).

### 7.2 Un seul métier ou outil généraliste

- **Option A — un seul métier (étanchéité / bâtiment).** Conséquence : bibliothèque plus
  précise (champs métier définis par L5), extraction plus fiable, mais outil non
  réutilisable hors du métier.
- **Option B — généraliste dès le départ.** Conséquence : bibliothèque plus souple mais
  plus vague, extraction plus difficile à cadrer, valeur immédiate plus faible.

Conditionne principalement la **richesse de la bibliothèque** (brique A) et le niveau de
détail attendu des références de chantiers.

### 7.3 Modèle économique

- **Option A — abonnement par entreprise.** Conséquence : orienté usage répété.
- **Option B — facturation à la consultation.** Conséquence : orienté usage ponctuel ;
  suppose de compter les consultations (mais **facturation hors périmètre du MVP**).
- **Option C — freemium limité à l'analyse du DCE.** Conséquence : l'analyse (brique B)
  attire, la bibliothèque (brique A) et la checklist (brique C) deviennent la valeur
  payante.

La facturation et le paiement sont **hors périmètre du MVP** : cette décision oriente la
conception mais ne s'implémente pas en phase 1.

### 7.4 Portage juridique et conflit d'intérêts

Question **hors périmètre phase 1** et **à faire valider par un juriste** — pas à
trancher dans ce projet. `PROJECT.md` § 6 la pose en priorité : le porteur est agent
d'une collectivité *et* conçoit un outil destiné aux entreprises candidates. Rien dans
le MVP ne doit utiliser de donnée ou d'influence issue de cette position ; le périmètre
doit rester strictement générique et public. **Ce document ne formule aucun avis
juridique et n'invente aucune référence légale.**

### 7.5 Stack technique du squelette

- **Option A — stack imposée par Anthony.** Conséquence : `dev-back` (L2) l'applique
  directement.
- **Option B — choix laissé à l'équipe, proposition à valider.** Conséquence :
  `dev-back` propose, Anthony valide.

Sans réponse, ce document ne présume d'aucune technologie.

### 7.6 Hébergement et confidentialité

Les bilans, CV et coordonnées bancaires de la bibliothèque sont des données sensibles
(`PROJECT.md` § 6 : chiffrement au repos, cloisonnement par entreprise, aucune donnée
client dans un modèle d'entraînement). **La localisation d'hébergement (France / UE) et
le fournisseur restent à décider** avant que le modèle de données définitif (L2) ne soit
figé. Ce document ne recommande aucun hébergeur.

---

## 8. Exemples — explicitement fictifs

Les exemples d'illustration utilisés dans les autres livrables doivent être **fictifs et
signalés comme tels**. Aucune donnée réelle d'entreprise (raison sociale, SIRET, IBAN,
bilan, CV) ne doit figurer dans le dépôt. Cette règle est déjà posée par L1 et rappelée
par `docs/PLAN.md` § 4 et le `.gitignore` du projet (qui couvre `data/`).

Rappel : ce document lui-même ne contient aucun exemple chiffré ni aucune référence
nommée, pour ne rien inventer.

---

## 9. Points laissés ouverts / à vérifier

À trancher par Anthony ou par un lot dédié — ce document ne les invente pas :

1. **Inclure ou non la famille « mémoire technique type » dans la bibliothèque du MVP**
   (voir note § 3.3). `PROJECT.md` § 3 la liste comme contenu de bibliothèque ; § 7
   exclut la *rédaction* automatique du mémoire. Frontière à confirmer.
2. **Formats de fichiers acceptés** pour le dépôt d'un DCE (brique B) — à fixer par L2.
3. **Format d'export** de la bibliothèque (brique A) — à fixer par L2.
4. **Forme exacte du verrou de relecture humaine** (où il bloque, comment il se matérialise)
   — à fixer par L2 et L3.
5. **Liste précise des pièces exigées et du vocabulaire d'extraction** — dépend de L4
   (`docs/CONFORMITE-COMMANDE-PUBLIQUE.md`), qui doit citer ses sources ou marquer
   « à vérifier ».
6. **Champs métier précis de la bibliothèque** — dépend de L5
   (`docs/DONNEES-METIER-BATIMENT.md`).
7. Les six décisions de cadrage (§ 7 ci-dessus), qui conditionnent la phase 2.

**Aucune norme, aucun seuil et aucune référence juridique n'est cité dans ce document
faute de source vérifiée.** Là où une telle source serait nécessaire, il est écrit
explicitement « à vérifier » et renvoi au lot compétent (L4).
