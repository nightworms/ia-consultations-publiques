# UI-SAISIE — Maquette fonctionnelle de l'interface de saisie

*Lot L3 — agent `dev-web`. Phase 1 : cadrage. Ce document **décrit** une interface,
il ne contient aucun composant, aucune page HTML/CSS/JS et aucun code exécutable.*

*Sources de référence : `PROJECT.md` § 3 (les neuf familles d'informations),
`PROJECT.md` § 5 et § 6 (ligne rouge, points de vigilance), `README.md` (périmètre
MVP). Le modèle de données technique produit par le lot L2 (`docs/DATA-MODEL.md`)
existait au moment de la rédaction : ce document **s'aligne sur lui** — numérotation
des neuf familles, énumérations de traçabilité (`origine_valeur`, `etat_verification`,
`statut_validite`, `sensibilite`), entité `document`, versionnement de la fiche
(voir § 10 et § 13 point 6). Il ne fige en revanche **aucun choix de type technique**,
aucun format de stockage et aucune structure de base de données : c'est L2 qui fait foi
pour la structure. Les champs sont regroupés par famille métier, conformément à
`PROJECT.md` § 3.*

*Les exemples de contenu affichés dans ce document sont **fictifs et signalés comme
tels**. Aucune donnée réelle d'entreprise, aucun document confidentiel n'y figure.*

---

## 1. Objet et périmètre

Cette maquette couvre **la bibliothèque d'entreprise** : la saisie guidée des
informations de l'entreprise, une fois, structurées et réutilisables. C'est le
premier livrable du MVP (`PROJECT.md` § 7).

Dans le périmètre de ce document :

- le parcours de saisie pas à pas (écrans, champs, ordre de saisie) ;
- ce qui est obligatoire et ce qui peut être complété plus tard ;
- la sauvegarde et la reprise d'une saisie incomplète ;
- la gestion des échéances (certificats, assurances) ;
- la restitution de ce qui manque ;
- le moment de **relecture humaine bloquante**.

Hors périmètre — ce document n'écrit rien sur : mémoire technique rédigé
automatiquement, veille et détection d'appels d'offres, dépôt de pli, signature
électronique, connexion aux plateformes d'achat public, chiffrage / prix / marge,
authentification multi-utilisateurs, paiement, facturation, mise en production.
Ces sujets n'apparaissent donc dans aucun écran décrit ici.

---

## 2. Principes de conception

Cinq principes contraignent toute la maquette. Ils découlent directement de la
ligne rouge du projet (`PROJECT.md` § 5) et des points de vigilance (§ 6).

**P1 — Traçabilité visible de chaque donnée.** Toute information affichée dans la
fiche porte son **origine** (`origine_valeur` de `docs/DATA-MODEL.md` § 2.2 :
`document_extrait` ou `saisie_entreprise`), le libellé du document source quand il
existe, et, quand elle en a une, sa **date de validité** et la **date de dernière
modification** (`docs/DATA-MODEL.md` § 4). Aucune valeur n'apparaît « nue ». L'IA ne
remplit
jamais un champ à partir de rien : elle peut proposer une valeur **lue dans un
document fourni par l'utilisateur**, et cette proposition est toujours accompagnée
de la source exacte et reste éditable par l'humain.

**P2 — Relecture humaine bloquante.** Une famille d'informations ou une fiche ne
passe à l'état « validée » que par une **action humaine explicite**, horodatée et
attribuée. L'outil ne pose jamais cet état lui-même. Aucun élément ne peut être
présenté comme utilisable dans un dossier sans cette validation (voir § 9).

**P3 — Saisie progressive.** On n'exige jamais tout d'un coup. Le socle minimal est
petit, puis la fiche se complète par vagues. Un champ non encore renseigné n'est pas
une erreur : c'est un manque **nommé et localisé**, visible dans le récapitulatif
(§ 8).

**P4 — Rien n'est inventé, rien n'est garanti.** L'interface n'affiche aucune norme,
aucun seuil et aucune durée de validité qu'elle n'aurait pas lus dans un document
fourni. Quand une obligation est connue mais que sa source n'est pas dans la
bibliothèque, le champ est marqué **« à vérifier »** et non rempli d'office. L'outil
signale et fait dire ; il ne certifie pas. Il ne fixe aucun prix et n'affiche aucun
champ de chiffrage.

**P5 — Sobriété.** Pas de dépendance, pas de framework imposé par ce document. La
maquette se décrit en HTML sémantique natif (formulaires, listes, tableaux,
titres hiérarchisés) ; toute bibliothèque future devra être justifiée en une phrase.

---

## 3. Vue d'ensemble du parcours

### 3.1 Arborescence des écrans

```
Bibliothèque d'entreprise
│
├── E0 · Tableau de bord de la bibliothèque        (état global, reprise, manques)
│
├── E1 · Fiche entreprise                          (identité — socle)
│   ├── E1a · Identité légale et coordonnées
│   └── E1b · Représentant légal
│
├── E2 · Espace d'une famille                      (gabarit réutilisé 8 fois)
│   ├── E2-F2 · Capacités financières
│   ├── E2-F3 · Assurances
│   ├── E2-F4 · Certifications et qualifications
│   ├── E2-F5 · Références de chantiers
│   ├── E2-F6 · Moyens humains
│   ├── E2-F7 · Moyens matériels
│   ├── E2-F8 · Fiches techniques produits
│   └── E2-F9 · Mémoire technique type
│       (Famille 1 — Identité — a son propre écran, E1)
│
├── E3 · Formulaire de saisie d'un élément         (référence, personne, produit…)
├── E4 · Dépôt d'un justificatif                   (pièce + source + validité)
├── E5 · Échéances                                 (certificats, assurances)
├── E6 · Récapitulatif des manques
└── E7 · Relecture humaine bloquante               (séquence finale, non court-circuitable)
```

### 3.2 Chemin nominal (saisie d'une entreprise)

```
   E0 Tableau de bord
        │  « Compléter la fiche »
        ▼
   E1 Identité ───────────► socle enregistré (auto-save) ──┐
        │                                                   │
        ▼                                                   │
   E2-F5 Références de chantiers  ◄── famille la plus        │
        │   (répétable, E3/E4)        rentable, en premier   │
        ▼                                                   │
   E2-F3 Assurances + F4 Certifications                     │
        │   (chacune crée une échéance, E5)                  │
        ▼                                                   │
   E2-F2 Capacités financières                              │
        ▼                                                   │
   E2-F6 Humains · F7 Matériels · F8 Produits · F9 Mémoire  │
        │   (complétables plus tard, jamais bloquants ici)   │
        ▼                                                   │
   E6 Récapitulatif des manques  ◄──────────────────────────┘
        │   « relire et valider »
        ▼
   E7 Relecture humaine bloquante ──► état « relue et validée »
```

Le parcours est **non linéaire** : depuis E0, l'utilisateur ouvre n'importe quelle
famille dans n'importe quel ordre. Le chemin ci-dessus n'est qu'un **ordre conseillé**
(voir § 6). Seul E7 est un passage obligé, et il vient **après** E6.

---

## 4. Niveaux d'exigence d'un champ

Chaque champ porte un niveau d'exigence, visible à l'écran par un marqueur textuel
(pas seulement par une couleur — voir § 11).

| Niveau | Libellé affiché | Signification |
|---|---|---|
| **N1 — socle** | « obligatoire » | Nécessaire pour créer et identifier l'entreprise. La fiche ne peut pas être enregistrée sans. |
| **N2 — requis à l'usage** | « requis pour un dossier » | Non exigé pour exister, mais **bloquant pour la relecture** (E7) dès lors que la fiche est destinée à alimenter un dossier. |
| **N3 — complétable** | « facultatif — à compléter plus tard » | N'empêche ni l'enregistrement ni la validation. Reste listé comme manque non bloquant (§ 8). |

Les niveaux d'exigence (N1/N2/N3) sont propres à la **saisie** et ne figurent pas dans
le modèle de données. Deux vocabulaires de L2 décrivent, eux, l'état d'une valeur, et
l'écran doit les afficher sans les confondre :

- `etat_verification` (`docs/DATA-MODEL.md` § 2.2) — où en est la **confiance** :
  `verifie` · `declare_non_verifie` · `a_verifier`. Un champ vide n'a pas de
  `confiance` : il est simplement **non renseigné**.
- `statut_validite` (`docs/DATA-MODEL.md` § 2.2) — où en est la **date** :
  `valide` · `echeance_proche` · `expire` · `non_renseigne`.

Une valeur `a_verifier` porte la mention « à vérifier » et **ne propose aucune valeur
par défaut** : l'outil ne comble pas un vide par une supposition (P4).

Un champ N2 vide n'empêche pas de travailler : il empêche de **valider** (§ 9).

---

## 5. Écrans détaillés

### E0 — Tableau de bord de la bibliothèque

Premier écran à l'ouverture. Il répond à trois questions : *où en est la fiche, que
manque-t-il, que puis-je reprendre.*

Zones :

1. **Bandeau d'état de la fiche** — un état unique parmi :
   `Vierge` · `En cours de saisie` · `Socle complet (non relue)` ·
   `En relecture` · `Relue et validée` · `Validée puis modifiée (à relire)`.
   Le dernier état est important : **toute modification après validation fait
   retomber la fiche en relecture** (P2).
2. **Progression par famille** — huit lignes (les familles de `PROJECT.md` § 3 hors
   identité, qui a son propre écran), chacune avec : nombre d'éléments, nombre de
   champs N2 manquants, présence d'échéance proche ou dépassée.
3. **Reprise** — bouton « Reprendre là où j'en étais », qui rouvre le dernier
   formulaire interrompu (§ 7).
4. **Alertes d'échéance** — compteur des certificats et assurances dont la date de
   validité est `echeance_proche` ou `expire` (écran E5, § 5).
5. **Accès E6** — « Voir ce qui manque ».
6. **Accès E7** — « Relire et valider », actif seulement si le socle est complet.
   Aucun libellé de type « déposer » ou « envoyer » n'apparaît : le dépôt et la
   signature sont hors périmètre.

### E1 — Fiche entreprise (identité)

Deux onglets internes : **E1a Identité légale et coordonnées**, **E1b Représentant légal**.

**E1a — champs**

| Champ | Niveau | Notes d'écran |
|---|---|---|
| Raison sociale | N1 | Texte libre |
| Forme juridique | N1 | Liste déroulante de formes juridiques **génériques** ; la liste exacte des formes est à valider (voir § 13, point ouvert 1 ; aucune liste inventée) |
| Numéro SIRET | N1 | Texte. L'outil **ne valide pas** le format et **ne déduit rien** de ce numéro (pas d'appel externe) ; il stocke ce qui est saisi |
| Adresse (rue, complément, code postal, ville, pays) | N1 | |
| Téléphone, courriel de contact | N1 | |
| Effectif (nombre) | N3 | Complétable plus tard |
| Coordonnées bancaires (IBAN, BIC) | N3 | Champ **sensible** : masqué à l'affichage par défaut, révélé à la demande. À compléter plus tard ; sa présence n'est jamais requise pour valider |

**E1b — champs**

| Champ | Niveau | Notes d'écran |
|---|---|---|
| Nom et prénom du représentant légal | N2 | Requis pour un dossier |
| Fonction | N2 | |
| Qualité pour engager l'entreprise | N2 | Texte libre ; aucune interprétation juridique automatique |

Aucun bouton de signature n'existe dans cet écran.

### E2 — Espace d'une famille (gabarit réutilisé huit fois)

Le même gabarit sert aux huit familles. Structure type :

```
┌ E2 · Références de chantiers ──────────────────────────────┐
│ État : 3 éléments · 1 champ « requis » manquant · 0 échéance │
│ [ Ajouter une référence ]   [ Importer depuis un document ]  │
├─────────────────────────────────────────────────────────────┤
│ ▸ EXEMPLE FICTIF — Chantier « Toiture bâtiment communal »   │
│    maître d'ouvrage : Commune fictive de Démonstration      │
│    année : 2024 · nature : étanchéité toiture               │
│    origine : saisie_entreprise · modifié le 30/09/2026      │
│    [ ouvrir ] [ dupliquer ] [ archiver ]                    │
│ ▸ EXEMPLE FICTIF — Chantier « Réfection terrasse école »    │
│    …                                                         │
└─────────────────────────────────────────────────────────────┘
   ▲ les libellés ci-dessus sont des exemples fictifs inventés
     pour la maquette, aucun client réel n'est représenté.
```

Pour chaque famille, la liste affiche pour chaque élément : un titre court, l'origine
de la donnée (`document_extrait` avec libellé du document / `saisie_entreprise`), la date de dernière
modification, et un marqueur d'échéance s'il y en a une.

**Contenu par famille** (numérotation alignée sur `docs/DATA-MODEL.md` § 6 à § 14 ;
les niveaux d'exigence indiqués sont les valeurs proposées ; ils restent à confirmer,
voir § 13) :

**Famille 2 — Capacités financières**

| Champ | Niveau |
|---|---|
| Chiffre d'affaires par exercice (valeur, exercice, devise) | N2 |
| Bilan / liasse fiscale (justificatif déposé — E4) | N2 |
| Attestations fiscales et sociales (justificatif — E4) | N2 |
| Capacité de production (texte libre) | N3 |

Aucun calcul, aucune moyenne, aucun ratio n'est produit par l'outil. Seuls les
montants **saisis ou lus dans un document** sont affichés, avec leur source.

**Famille 3 — Assurances**

| Champ | Niveau |
|---|---|
| Type d'assurance (décennale, responsabilité civile…) | N2 |
| Assureur | N2 |
| Numéro de police | N2 |
| Date de début / date de fin de validité | N2 → crée une échéance (E5) |
| Montant de garantie (valeur + devise) | N2 |

**Famille 4 — Certifications et qualifications**

| Champ | Niveau |
|---|---|
| Libellé (ex. familles citées dans `PROJECT.md` § 3 : Qualibat, RGE, MASE, ISO) | N2 |
| Référence ou numéro du certificat | N2 |
| Organisme | N3 |
| Date d'obtention | N3 |
| Date d'échéance | N2 → crée une échéance (E5) |
| Justificatif (E4) | N2 |

L'outil enregistre la date d'échéance **lue sur le document**. Il ne connaît ni ne
calcule aucune durée de validité réglementaire (P4).

**Famille 5 — Références de chantiers** (famille la plus rentable, saisie en premier)

| Champ | Niveau |
|---|---|
| Intitulé court de la référence | N1 pour l'élément |
| Maître d'ouvrage | N2 |
| Nature des travaux | N2 |
| Description | N2 |
| Année | N2 |
| Durée | N3 |
| Montant (valeur + devise) | N3 — montant d'un chantier passé, **jamais une proposition de prix** |
| Localisation | N3 |
| Photos / pièces (E4) | N3 |

**Famille 6 — Moyens humains** — organigramme (N3), effectifs par métier (N3), CV des
profils clés (N3, pièces via E4, données personnelles **sensibles** : accès restreint
et affiché comme tel).

**Famille 7 — Moyens matériels** — parc, engins, échafaudages, outillage spécifique :
liste libre d'éléments (N3), chacun avec libellé, quantité, et justificatif facultatif.

**Famille 8 — Fiches techniques produits** — fournisseur, référence produit, certificat,
avis technique (N3), avec échéance facultative si le document en porte une.

**Famille 9 — Mémoire technique type** — réponses déjà rédigées et acceptées, découpées par
chapitre (N3). Champ texte long + référence de source. **Aucune production
automatique de mémoire technique n'apparaît dans cette interface** : la famille ne
sert qu'à ranger des textes déjà écrits par l'entreprise.

### E3 — Formulaire de saisie d'un élément

Gabarit de formulaire utilisé par toutes les familles répétables.

Règles d'écran :

- **Ordre de saisie dans le formulaire** : du plus identifiant au plus détaillé —
  (1) libellé/intitulé, (2) champs N1, (3) champs N2, (4) champs N3 regroupés sous un
  dépliant « Compléter plus tard ».
- **Marqueur d'exigence** à côté de chaque libellé : « obligatoire », « requis pour un
  dossier », « facultatif ». Marqueur **textuel** (voir § 11).
- **Champ source** toujours présent : « Origine de cette donnée » — `document_extrait`
  (avec le libellé du document, E4) ou `saisie_entreprise`.
- **Bloc « date de validité »** présent uniquement quand la famille en a un sens
  (assurances, certifications, produits).
- Boutons : `Enregistrer et fermer`, `Enregistrer et ajouter un autre`,
  `Annuler`. Aucun bouton de suppression définitive : `Archiver` conserve l'élément
  et le retire des propositions.

### E4 — Dépôt d'un justificatif

Écran d'ajout d'une pièce rattachée à un champ ou à un élément de famille.

| Champ | Niveau | Notes |
|---|---|---|
| Fichier | N1 pour la pièce | Dépôt local ; le stockage relève du lot L2, non traité ici |
| Nature de la pièce | N1 | Liste : attestation, certificat, bilan, CV, photo, autre |
| Rattaché à | N1 | Champ, élément ou famille de destination |
| Date figurant sur le document | N2 | Saisie humaine ; **l'outil ne devine pas** cette date |
| Date de validité indiquée sur le document | N2 | Idem — si aucune date n'est lisible, le champ reste vide et marqué « non renseigné » |
| Origine (`origine_valeur`) | N2 | `document_extrait` ou `saisie_entreprise` |

Toute valeur que l'outil proposerait à partir d'un document est affichée comme
**proposition à confirmer**, avec la mention de la source, et n'est **jamais**
enregistrée sans validation humaine (P1).

### E5 — Échéances

Écran transversal listant toutes les dates de validité de la bibliothèque :
certificats (F4), assurances (F3), éventuellement produits (F8).

Colonnes : élément concerné, famille, type d'échéance, **date de validité**, source
(document ou saisie), jours restants, statut.

États d'un élément porteur d'échéance (vocabulaire `statut_validite` de
`docs/DATA-MODEL.md` § 2.2) :

```
   valide ──► echeance_proche ──► expire
                  ▲                 │
                  └─ renouvelée ◄───┘  (nouveau document déposé en E4,
                                        nouvelle date lue sur le document)
```

- **valide** — date de validité postérieure à la fenêtre d'alerte ;
- **echeance_proche** — entre dans la fenêtre d'alerte ;
- **expire** — date passée ; l'élément reste dans la bibliothèque mais est
  **exclu des propositions** et compté comme manque bloquant (N2) ;
- **renouvelée** — un justificatif plus récent a été déposé et validé ; l'historique
  est conservé versionné (règle de versionnement portée par `docs/DATA-MODEL.md` § 5).

**Important (P4) :** la fenêtre d'alerte (nombre de jours avant échéance) est un
**réglage produit**, choisi par l'utilisateur. Elle ne correspond à aucune règle
réglementaire et n'est présentée comme telle nulle part. Aucune durée de validité
n'est préremplie par l'outil : seules les dates lues sur les documents comptent, et
à défaut la mention « date non renseignée — à vérifier » s'affiche.

### E6 — Récapitulatif des manques

Écran de restitution. Il répond à : *qu'est-ce qui manque, et est-ce bloquant ?*

Deux sections :

1. **Manques bloquants** — champs N2 et N1 vides, échéances dépassées, éléments
   « à vérifier », éléments dont la source est absente. Chacun est **nommé et
   localisé** : famille, élément, nom du champ, et lien direct vers l'endroit à
   corriger.
2. **Manques non bloquants** — champs N3 vides, listés pour information.

Chaque ligne porte : famille · élément · champ · niveau · raison du manque
(`vide` / `à vérifier` / `source absente` / `échéance dépassée`).

Filtres : par famille, par niveau, par type de manque. Bouton
`Exporter la liste des manques` (format à fixer par L2 — non tranché ici).

**Cette liste ne propose aucune correction automatique de contenu.** Elle dit ce qui
manque ; elle ne remplit pas à la place de l'humain.

### E7 — Relecture humaine bloquante

Écran final, **passage obligé**, non court-circuitable. Il ne produit ni dépôt ni
signature : il établit que **l'humain a relu**.

Déroulé imposé, en une seule séquence :

1. **Présentation** — la fiche complète est affichée famille par famille, chaque
   valeur accompagnée de sa source et de sa date de validité (P1).
2. **Signalement des points d'attention** — manques bloquants persistants, échéances
   dépassées, champs « à vérifier », valeurs sans source. La liste est affichée même
   si l'humain veut valider malgré tout : elle est **visible, pas silencieuse**.
3. **Correction** — l'humain peut revenir sur n'importe quel champ depuis cet écran.
4. **Attestation de relecture** — trois éléments obligatoires, saisis par l'humain :
   une case à cocher « j'ai relu et corrigé les informations ci-dessus », le **nom**
   du relecteur, la **date et l'heure** posées automatiquement au moment de l'action.
5. **Validation** — seule une action humaine explicite fait passer la fiche à l'état
   `Relue et validée`. **L'outil ne pose jamais cet état.**

Machine à états de la fiche :

```
  Vierge
    │ saisie du socle (N1)
    ▼
  Socle complet, non relue ──────────┐
    │                                │ modification d'un champ
    ▼                                │ après validation
  En relecture ──────────────────────┤
    │ action humaine explicite       │
    ▼                                │
  Relue et validée ──────────────────┤
    │ modification                   │
    ▼                                │
  Validée puis modifiée (à relire) ◄─┘
```

Toute modification après validation **fait retomber la fiche en relecture** : la
validation est un état périssable, pas un acquis (P2).

L'écran E7 ne comporte **aucun** bouton « déposer », « envoyer », « signer » ou
« publier » : ces actions sont hors périmètre du MVP.

---

## 6. Ordre de saisie

L'ordre conseillé découle de la valeur métier et du coût d'entrée décroissant :

1. **Identité (E1a)** — socle minimum, débloque tout le reste.
2. **Références de chantiers (F5)** — *le poste le plus rentable*
   (`PROJECT.md` § 3). Il nourrit la valeur du produit ; on le propose tôt.
3. **Assurances (F3)** et **Certifications (F4)** — chacune crée une échéance : les
   saisir tôt fait vivre l'écran E5 dès le début.
4. **Capacités financières (F2)** — plus lourdes (documents à réunir).
5. **Moyens humains (F6), matériels (F7), fiches produits (F8), mémoire type (F9)** —
   complétables plus tard sans bloquer.
6. **Récapitulatif (E6)** puis **Relecture (E7)**.

Cet ordre est **conseillé, pas imposé** : l'utilisateur peut ouvrir n'importe quelle
famille depuis E0. Le seul enchaînement contraint est **E6 → E7 en fin de parcours**.

*Hors MVP, rappel :* dans le parcours de bout en bout de `PROJECT.md` § 4, la
bibliothèque alimente ensuite analyse de DCE, pré-sélection, assemblage et contrôle.
Ces étapes ne font pas partie de ce document et ne sont pas dessinées ici.

---

## 7. Sauvegarde et reprise d'une saisie incomplète

**Enregistrement continu.** Chaque formulaire enregistre son contenu sans action
explicite l'utilisateur (auto-enregistrement déclenché à la sortie d'un champ et à
l'ouverture/fermeture). `Enregistrer et fermer` est un confort, pas une nécessité.

**Brouillon.** Un élément en cours de saisie existe en état `brouillon` : il est
visible dans sa famille, marqué comme incomplet, et **n'entre pas dans les
propositions** tant qu'il n'est pas complété à son niveau N1.

**Statut par famille.** Chaque famille porte un état indépendant :

```
  non commencée ──► démarrée ──► socle complet ──► validée humainement
                                    ▲                    │
                                    └── modification ◄───┘
```

Une famille peut être validée pendant qu'une autre reste vierge : la progression est
par famille, pas globale. Seul E7 demande l'ensemble.

**Reprise.** À la réouverture, E0 affiche « Reprendre là où j'en étais » : dernier
formulaire interrompu, dernier champ actif, position dans la famille. Aucune saisie
partielle n'est perdue.

**Concurrence et conflits (question ouverte).** L'authentification
multi-utilisateurs est hors périmètre. Ce document suppose un usage mono-utilisateur
et **ne définit aucun mécanisme de fusion de saisies simultanées** ; c'est un point
ouvert (§ 13, point ouvert 2).

---

## 8. Restitution de ce qui manque

Trois lieux, du plus fin au plus global :

1. **Dans la famille (E2)** — bandeau d'en-tête : nombre de champs requis manquants,
   nombre d'échéances en alerte.
2. **Dans l'élément (E3/E4)** — marqueur textuel sur chaque champ vide ou « à
   vérifier ».
3. **Globalement (E6)** — la liste complète, filtrable, exportable.

Règle de restitution (P3, P4) : un manque est toujours décrit par
**famille · élément · champ · niveau · raison**. Jamais par une simple icône ou une
couleur seule. Un manque **non bloquant** ne se présente jamais comme une erreur : il
informe.

---

## 9. Relecture humaine bloquante — contraintes techniques de conception

Ce n'est pas une recommandation, c'est une contrainte d'implémentation à respecter
par les lots suivants :

- **Aucun chemin ne mène à l'état `Relue et validée` sans une action humaine
  explicite** (case cochée + nom du relecteur + horodatage automatique).
- **Aucun composant automatique ne pose cet état.** Ni import, ni proposition
  automatique, ni reprise de brouillon.
- **Toute écriture sur un champ validé révoque la validation** de la famille et de la
  fiche ; le retour en relecture est obligatoire.
- **Le libellé de l'état produit est explicite** : « relue et validée par humain »,
  jamais « conforme », « validée par l'IA » ou « certifiée » (l'outil ne garantit
  aucune conformité — `PROJECT.md` § 5).
- **Aucun bouton de signature ni de dépôt** n'existe dans le périmètre du MVP.

---

## 10. Affichage de l'origine des données (motif « Source »)

Le vocabulaire ci-dessous est celui de `docs/DATA-MODEL.md` § 2.2, § 2.3 et § 4 : la
maquette ne redéfinit pas ces valeurs, elle les **affiche**.

| Élément du modèle (L2) | Valeurs | Rendu à l'écran |
|---|---|---|
| `origine` (`origine_valeur`) | `document_extrait` · `saisie_entreprise` | « extrait du document : <libellé> » · « déclaré par l'entreprise » |
| `confiance` (`etat_verification`) | `verifie` · `declare_non_verifie` · `a_verifier` | « vérifié » · « déclaré, non vérifié » · « à vérifier » |
| `statut_validite` | `valide` · `echeance_proche` · `expire` · `non_renseigne` | « valide » · « échéance proche » · « échéance dépassée » · « date non renseignée » |
| `sensibilite` | `publique` · `interne` · `confidentiel` | champ masqué par défaut si `confidentiel` |

Chaque valeur affichée porte, sous une forme compacte et cohérente :

```
   valeur
   ↳ source : libellé du document (E4)  |  déclaré par l'entreprise  |  non renseignée
   ↳ validité : date figurant sur le document  |  date non renseignée
   ↳ vérification : vérifié | déclaré, non vérifié | à vérifier
   ↳ dernière modification : 00/00/0000 par <relecteur humain>
```

Règles imposées par L2 que l'écran doit refléter :

- `origine = document_extrait` **doit** avoir un document source ; l'écran n'affiche
  jamais « extrait du document » sans nommer ce document.
- `origine = saisie_entreprise` sans document s'affiche au mieux
  « déclaré par l'entreprise, non vérifié » — jamais comme une donnée vérifiée.
- `confiance = verifie` n'est possible que si une source existe et a été contrôlée.
- Aucune valeur `genere_ia` n'existe : l'écran n'affiche donc **jamais** de mention
  « proposé par l'IA » comme origine. Une valeur lue dans un document est une donnée
  `document_extrait`, pas une production de l'IA.

La mention « à vérifier » est **obligatoire** dès qu'une valeur n'a pas de source
vérifiable dans la bibliothèque : l'outil ne comble pas le vide par une supposition.

Aucune valeur affichée dans cette maquette n'est issue d'une donnée réelle : tous les
exemples sont fictifs et signalés.

---

## 11. Contraintes d'affichage et d'accessibilité

Contraintes minimales que la maquette impose à toute implémentation ultérieure :

- **HTML sémantique** : chaque champ dans un `label` associé, hiérarchie de titres
  continue (`h1` la fiche, `h2` les familles, `h3` les éléments), tableaux de données
  en `table` avec en-têtes, listes en `ul`/`dl`.
- **Statuts non portés par la couleur seule** : chaque état (obligatoire, à vérifier,
  échéance dépassée) porte un **libellé textuel** en plus de toute couleur.
- **Navigation clavier complète** : tous les formulaires, écrans et boutons
  atteignables et utilisables sans souris ; ordre de tabulation dans l'ordre visuel.
- **Contrastes suffisants** (objectif WCAG AA / RGAA) sur les marqueurs de statut.
- **Responsive par défaut** : les formulaires à deux colonnes repassent en une colonne
  en dessous du palier étroit ; aucun écran ne casse entre deux largeurs.
- **Champ bancaire masqué** par défaut (Famille 2/E1a) ; CV (Famille 6) signalés comme
  données
  personnelles.

---

## 12. Exemple d'écran complet (fictif)

Extrait de l'écran E2 · Assurances (Famille 3). **Tout le contenu ci-dessous est
fictif et sert uniquement à illustrer la maquette.**

```
┌ Bibliothèque d'entreprise ▸ Assurances ─────────────────────────────────────┐
│ 2 éléments · échéance dépassée : 1                                           │
│                                                        [ Ajouter ]           │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▸ EXEMPLE FICTIF — Assurance décennale                                       │
│    assureur : Assureur de Démonstration (fictif)                             │
│    police : 000000000                                                        │
│    garantie : 000 000 EUR                                                    │
│    validité : 31/12/2025 .... statut expire                                 │
│    source : « attestation_decennale_exemple_fictif.pdf » (déposé 01/01/2024) │
│    origine : document_extrait · vérification : déclaré, non vérifié         │
│    dernière modification 30/09/2026 par <relecteur humain>                   │
│    [ ouvrir ] [ déposer un renouvellement ] [ archiver ]                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▸ EXEMPLE FICTIF — Responsabilité civile professionnelle                     │
│    validité : date non renseignée — À VÉRIFIER                               │
│    origine : saisie_entreprise · vérification : a_verifier                   │
│    source : non renseignée                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
   Note : aucune durée de validité n'est déduite par l'outil. La date affichée
   est celle lue sur le document ; en son absence, la mention « à vérifier »
   s'affiche et le champ reste vide.
```

---

## 13. Points laissés ouverts

1. **Liste des formes juridiques** (E1a) : la liste déroulante suppose une liste close
   des formes ; elle n'est pas arrêtée dans ce document et **ne doit pas être
   inventée**. `docs/DATA-MODEL.md` § 3.1 la marque également « à compléter à la
   source ». À fixer avec l'arbitrage d'Anthony (point ouvert 4 de L2).
2. **Usage mono- ou multi-utilisateur** : l'authentification multi-utilisateurs est
   hors périmètre ; la maquette ne définit donc aucune gestion de conflits de saisie
   simultanée. Point à trancher avant la phase 2.
3. **Fenêtre d'alerte des échéances** : réglage produit, aucune règle réglementaire
   fournie. `docs/DATA-MODEL.md` § 2.2 et § 15 laissent volontairement le seuil de
   `echeance_proche` non fixé ; même point ouvert côté interface (point ouvert 3 de L2).
4. **Format d'export** de la liste des manques (E6) : non tranché — dépend de L2 et
   reste à fixer.
5. **Niveaux d'exigence N1/N2/N3 par champ** : les affectations de ce document sont
   des propositions fonctionnelles ; elles doivent être confrontées à
   `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` (L4, pièces exigées) et à
   `docs/DONNEES-METIER-BATIMENT.md` (L5, contenu métier), puis figées avec L2.
6. **Mapping interface ↔ modèle** : la maquette a été alignée sur
   `docs/DATA-MODEL.md` (numérotation des familles, énumérations `origine_valeur`,
   `etat_verification`, `statut_validite`, `sensibilite`, entité `document`,
   versionnement de fiche). Restent à vérifier lors de l'implémentation :
   - l'écran E4 « Dépôt d'un justificatif » correspond à l'entité `document` de L2
     (§ 3.2) — les libellés d'écran devront reprendre `type_document`, `libelle`,
     `emetteur`, `date_emission`, `date_validite_debut`, `date_validite_fin` ;
   - l'écran E6 « Récapitulatif des manques » n'a **pas** d'équivalent direct dans
     L2 : c'est une vue calculée, à produire côté application, pas une table ;
   - l'écran E7 (relecture humaine) s'appuie sur le versionnement de fiche décrit par
     L2 § 5 ; le **nom du relecteur** et l'**horodatage** de validation devront être
     portés par le modèle — à confirmer avec le lot L2, ce document ne les suppose
     pas déjà présents.
7. **Champs « à vérifier »** : le comportement exact (qui lève la mention, à quelle
   condition) reste à préciser avec le lot `collectivite` (L4), qui détient la source
   des obligations, et avec L2 (`confiance = verifie`).

---

*Fin du document. Lot L3 — `dev-web`. Aucun composant, aucune page et aucun code
exécutable ne fait partie de ce livrable.*
