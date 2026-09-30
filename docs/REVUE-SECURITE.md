# REVUE-SECURITE — revue de sécurité et de conformité des choix

*Lot **L6** — agent `qa`. Phase 2 du projet *IA consultations publiques*. Écrit le
30 septembre 2026.*

*Board : `ia-consultations`. Dossier :
`/Users/pause/Projets/ia-consultations-publiques`. Dépend de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`
(lot L2) et de `docs/DATA-MODEL-V2.md` (lot L3). Référence de cadrage : `docs/DECISIONS.md`
(D1 à D6).*

> **Ce document ne corrige rien.** Il constate. Les corrections appartiennent aux
> propriétaires des livrables (L1, L2, L3, L4, L5) et à Anthony pour les décisions.
> **Il n'énonce aucune garantie de confidentialité** : seul
> `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` est habilité à le faire (décision d'orchestrateur
> **D-C2**). Ce document ne fait que **citer** son verdict et **confronter** ce que les
> autres documents en disent.

---

## 0. Comment lire cette revue

Quatre lectures :

- **théorie de la menace** — § 2 : qui attaque quoi, ce qui protège, ce qui reste ouvert ;
- **preuve** — § 3 (cloisonnement), § 5 (honnêteté des formulations), § 6 (constats de
  phase 1), § 7 (cohérence stack ↔ modèle) : chaque affirmation porte une commande, un
  fichier et une ligne ;
- **décision** — § 4 : ce qui doit être tranché par un juriste, jamais par moi ;
- **synthèse** — § 9 (constats numérotés `S1`…`S13`) et § 10 (bilan par gravité).

Ce que je **n'ai pas** couvert est écrit noir sur blanc en § 11. Un rapport qui ne signale
rien serait suspect ; celui-ci signale treize constats, dont trois majeurs, et dit
précisément ce qu'il n'a pas pu vérifier.

---

## 1. Méthode et commandes réellement exécutées

Toutes les commandes ci-dessous ont été exécutées le 30 septembre 2026 depuis
`/Users/pause/Projets/ia-consultations-publiques`. Aucune installation, aucun appel réseau,
aucun déploiement. Quatre outils seulement : lecture de fichier, `grep`, `find`, `git`.

### 1.1 Chemins, volumes et état du dépôt

```bash
cd /Users/pause/Projets/ia-consultations-publiques
find . -type f -not -path './.git/*' | sort
wc -l docs/*.md
git status --porcelain=v1
git log --oneline -n 5
git diff --stat HEAD
git ls-files docs/ src/
```

**Résultats observés.**

- `wc -l docs/*.md` → 14 documents, **6 850 lignes** au total. Les six livrables de phase 2
  existent aux chemins attendus : `CONFIDENTIALITE-ET-HEBERGEMENT.md` (651 l.),
  `DATA-MODEL-V2.md` (1 329 l.), `SPEC-MVP-V2.md` (521 l.), `STACK-PROPOSAL.md` (408 l.),
  `NOMENCLATURE-REFERENCE.md` (590 l.), `PLAN-PHASE-2.md` (238 l.).
- `git status --porcelain=v1` → **exactement six lignes**, toutes `?? docs/<livrable>.md`.
  Aucun fichier modifié, aucun fichier supprimé, aucun fichier créé hors `docs/`.
- `git log --oneline` → `fc2585d`, `d122b4c`, `2137c4c`. La phase 2 n'a **rien committé**.
- `git diff --stat HEAD` → **vide** : aucun fichier suivi n'a bougé.
- `git ls-files docs/ src/` → `docs/DATA-MODEL.md` (v1), `PROJECT.md`, `README.md`, tout
  `src/` sont **suivis** et **non modifiés**.

### 1.2 Fraîcheur : le squelette et la v1 n'ont pas été touchés

```bash
stat -f "%Sm %N" -t "%Y-%m-%d %H:%M" docs/*.md PROJECT.md README.md \
  src/app/main.py src/app/domain/entreprise.py src/migrations/README.md
```

**Résultats observés.** Les livrables de phase 2 portent des horodatages de **10:24 à 10:33**.
Tout ce qui devait rester intact porte un horodatage de phase 1 : `PROJECT.md` 09:56,
`README.md` 09:56, `docs/DATA-MODEL.md` (v1) **09:58**, `src/app/main.py` 09:59,
`src/app/domain/entreprise.py` 09:58, `src/migrations/README.md` 09:59.

> **Conclusion de preuve.** Le squelette `src/` et `docs/DATA-MODEL.md` v1 n'ont **pas** été
> modifiés en phase 2 : ni leur horodatage, ni leur état git (`git diff` vide) ne le
> montrent.

### 1.3 Hygiène des données et des secrets

```bash
find . -type f \( -name "*.pdf" -o -name "*.docx" -o -name "*.xlsx" -o -name "*.zip" \
  -o -name "*.sql" -o -name "*.env" -o -name "*.key" -o -name "*.pem" \) -not -path './.git/*'
ls -la data/ scripts/ src/migrations/
grep -rnoE "FR[0-9]{2}[ ]?([0-9A-Z]{4}[ ]?){4}[0-9A-Z]{2,3}|[0-9]{14}\b|\b0[1-9]([ .-]?[0-9]{2}){4}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" \
  docs/*.md README.md PROJECT.md src -r
```

**Résultats observés.**

- **Aucun** fichier `*.pdf`, `*.docx`, `*.xlsx`, `*.zip`, `*.sql`, `*.env`, `*.key`,
  `*.pem` dans le dépôt. `data/` et `scripts/` sont **vides**. `src/migrations/` ne contient
  que son `README.md` : **aucune migration écrite, aucune appliquée**.
- La recherche d'identifiants réalistes ne retourne **qu'une seule occurrence** :
  `00000000000000`, dans `docs/PLAN-DE-TEST.md:224` (documentation du constat V-E1) et dans
  `src/app/domain/entreprise.py:7`, à l'intérieur d'une docstring signalée « EXEMPLE FICTIF ».
  **Aucun IBAN réel, aucun SIRET réaliste, aucun courriel, aucun téléphone.**
- `.gitignore` couvre `data/`, `.env`, `.env.*`, `*.secret`, `*.key`, `*.pem`,
  `__pycache__/`, `.DS_Store`, `*.log`, `tmp/`.

### 1.4 Recherche des formulations de confidentialité et des divergences

```bash
grep -rnoE "seul le client a accès à ses données|aucun autre client[^.]*|hébergé[e]? en France[^.]*|chiffré[a-z]*[^.,]*" \
  docs/*.md README.md PROJECT.md
grep -rniE "inviolable|sécurité absolue|100 ?%|ne quittent jamais|aucun humain|par construction|garantie de confidentialité" \
  docs/*.md README.md PROJECT.md
grep -rniE "confidentialit|héberg|chiffr|sécuris|RGPD|données personnelles" README.md PROJECT.md
grep -rniE "stripe|paypal|prestataire de paiement|intégration de paiement|installer|pip install|déployé|en production" \
  docs/CONFIDENTIALITE-ET-HEBERGEMENT.md docs/DATA-MODEL-V2.md docs/STACK-PROPOSAL.md docs/SPEC-MVP-V2.md docs/NOMENCLATURE-REFERENCE.md
```

**Résultats observés.** Les occurrences de la phrase « seul le client a accès à ses
données » se trouvent **uniquement** : dans `docs/DECISIONS.md` (D6, qui pose la tension
ligne 70 et la qualifie lignes 74-97), dans `docs/PLAN-PHASE-2.md` (risque, ligne 141),
dans `docs/STACK-PROPOSAL.md` (lignes 178 et 195, qui **renvoient** au verdict de L2) et
dans `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` (le verdict lui-même). **Aucun document
n'énonce la phrase comme un fait non qualifié.** Détail et confrontation en § 5.

Aucune occurrence de `Stripe`, `PayPal`, `prestataire de paiement`, `pip install`,
`en production` en tant que fait accompli. Les seules occurrences de « production » disent
« **ne pas** charger en production » ou « pas de mise en production ».

### 1.5 Vérifications structurelles du modèle

```bash
grep -niE "iban|bic|effectif" docs/DATA-MODEL-V2.md
grep -nE "client_id|entreprise_id" docs/DATA-MODEL-V2.md | wc -l
grep -ciE "checklist" docs/DATA-MODEL-V2.md            # → 0
grep -ciE "critere" docs/DATA-MODEL-V2.md              # → 0
grep -noE "^\| \`[a-z]+\.[a-z_.]+\`" docs/NOMENCLATURE-REFERENCE.md
```

**Résultats observés.** `client_id` apparaît **59 fois** dans `DATA-MODEL-V2.md` ;
`entreprise_id` **17 fois**. Les mots `checklist` et `critere` : **zéro occurrence** (voir
constat **S2**). La nomenclature propose des namespaces `type.document`, `forme.juridique`,
`unite.mesure`… qui **divergent** des namespaces attendus par le modèle (voir **S6**).

---

## 2. Analyse de menace

### 2.1 Les actifs à protéger

| Actif | Où il vit | Nature de la sensibilité |
|---|---|---|
| **Documents du client** (DCE déposés, pièces justificatives : KBIS, bilans, attestations) | hors base (`document.chemin_stockage`), préfixé par client (`DATA-MODEL-V2.md` § 4.3) | secret des affaires ; pièces fiscales et sociales |
| **Bibliothèque d'entreprise** (identité, capacités financières, assurances, certifications, références, moyens, produits, mémoire type) | base, entités de contenu `client_id` (`DATA-MODEL-V2.md` § 10) | savoir-faire commercial, marges, historique de chantiers |
| **Données personnelles** (CV nominatifs, représentant légal, contact de référence chez un maître d'ouvrage) | tables `cv`, `representant_legal`, `reference_chantier.contact_reference` (`DATA-MODEL-V2.md` § 10 F5/F1/F6) | RGPD |
| **Coordonnées bancaires** (IBAN, BIC, RIB) | `entreprise_version` (`DATA-MODEL-V2.md` § 5.4) | fraude bancaire ; RGPD-adjacent |
| **Identifiants et accès** (comptes utilisateurs, identités techniques) | entité `utilisateur` (`DATA-MODEL-V2.md` § 5.2) | pivot d'accès |
| **Dossier de réponse en cours** (offre, prix proposé, mémoire technique assemblé) | **non modélisé** (voir **S2**) ; l'export est une vue calculée | secret des affaires, égalité des candidats |

### 2.2 Les adversaires plausibles

Cinq familles, comme demandé : le **candidat concurrent**, le **salarié indélicat**, le
**attaquant externe**, **l'éditeur ou l'administrateur technique lui-même**, le
**sous-traitant** (hébergeur, fournisseur du modèle d'IA).

### 2.3 Couples actif / adversaire — scénario, mesure attendue, ce qui reste ouvert

**M1 — Candidat concurrent → dossier de réponse et bibliothèque d'un autre concurrent**

- *Scénario.* Le concurrent devine un identifiant de dossier, énumère des URL de pièces,
  ou tente une requête qui omet le filtre de client.
- *Mesure attendue par la phase 2.* `client_id` obligatoire sur toute entité de contenu et
  redondant (`DATA-MODEL-V2.md` § 4.2) ; chemins de fichiers préfixés par le client (§ 4.3) ;
  invariants I1-I5 (§ 3.4) ; séparation des accès (§ 4.3). C'est le mécanisme décrit.
- *Ce qui reste ouvert.* **Aucun test d'isolation n'existe** (rien n'est implémenté) : le
  durcissement est sur le papier. Un chemin de croisement **non couvert** subsiste entre
  deux clients sur la table de liaison de facturation (**S4**). L'énumération d'URL et
  l'autorisation par requête ne sont pas conçues (pas d'implementation).

**M2 — Salarié indélicat (du client) → exfiltration depuis l'intérieur**

- *Scénario.* Un salarié du client télécharge la bibliothèque complète ou l'IBAN ; un
  relecteur « valide » une fiche qu'il n'a pas lue.
- *Mesure attendue.* `sensibilite = confidentiel` masqué par défaut (`UI-SAISIE.md` § 10,
  ligne 553) ; `validation_relecture.relecteur_nom` obligatoire et horodaté
  (`DATA-MODEL-V2.md` § 6.4) ; révocation à la première modification (§ 6.5).
- *Ce qui reste ouvert.* Le **nom du relecteur est auto-déclaré** : sans authentification
  multi-utilisateurs (hors périmètre, § 15 point 15), la trace est une déclaration, pas une
  preuve d'identité. Le document L3 l'écrit honnêtement (« le nom saisi fait foi ») ; il
  n'y a **pas de piste d'audit d'exploitation** (qui a lu quoi) — reconnu § 13.3 comme
  restant à spécifier.

**M3 — Attaquant externe → accès non authentifié, vol de volume, injection**

- *Scénario.* Attaque sur le serveur ; vol du disque ou d'une sauvegarde ; injection de
  consignes par le contenu d'un document (un DCE piégé).
- *Mesure attendue.* Chiffrement au repos (§ 8.2 de L2) ; hébergement en région française
  (§ 8.1) ; cloisonnement (§ 8.3) ; aucune donnée client dans un entraînement (§ 8.4).
- *Ce qui reste ouvert.* Selon l'option retenue : en **B**, le chiffrement est géré par le
  serveur/l'hébergeur, donc un volume volé **avec** la clé est lisible ; en **B et C**, la
  donnée est en clair pendant la fenêtre de traitement. L'**injection de consignes par un
  document** n'est traitée par **aucun** document de la phase 2 (voir **S11**). Le mur
  d'authentification, les sessions et les protections applicatives ne sont pas décrits
  (aucune implémentation).

**M4 — L'éditeur ou un administrateur technique → lecture des données de tous les clients**

- *Scénario.* Anthony (ou une personne de maintenance, ou l'hébergeur en cas d'accès
  administrateur) ouvre la base ou les fichiers et lit les documents de n'importe quel
  client. Aggravant propre à ce projet : **le porteur est un agent de la Mairie de
  Saint-Denis**, acheteur public (D4, `PROJECT.md` § 6).
- *Mesure attendue.* Aucune architecture de la phase 2 **n'empêche** cet accès : en B et C,
  l'exploitant peut lire pendant le traitement — L2 l'écrit honnêtement (§ 1 étape 3,
  § 5, § 6). La parade attendue est contractuelle et organisationnelle (séparation des
  casquettes, D4), pas technique.
- *Ce qui reste ouvert.* **Le croisement « administrateur peut lire » × « conflit
  d'intérêts du porteur » n'est nommé nulle part** dans les livrables de la phase 2, alors
  qu'il est le plus grave du produit : les données d'un candidat concurrent d'un marché
  pourraient être lues par un agent de l'acheteur. Voir **S3**.

**M5 — Sous-traitant (hébergeur, fournisseur du modèle) → transfert et rétention**

- *Scénario.* Le texte d'un DCE part chez un prestataire hors UE, y est journalisé 30 jours,
  ou sert à entraîner un modèle ; un sous-traitant ultérieur du fournisseur le reçoit.
- *Mesure attendue.* L2 trace le chemin de la donnée jusqu'à l'étape 7-8 (§ 1 et § 2) ;
  exige un DPA (art. 28 RGPD), une clause de non-entraînement et une rétention zéro
  (§ 8.4) ; recommande un fournisseur français/UE (§ 9).
- *Ce qui reste ouvert.* Tout dépend du **choix d'Anthony (question 2)** : avec un
  fournisseur hors UE, le transfert est **caractérisé** et « hébergé en France » ne décrit
  que le serveur. Deux points restent **non nommés** : le **même fournisseur de modèle voit
  les documents de tous les candidats** d'une même consultation (égalité des candidats), et
  l'absence de maîtrise de sa **liste de sous-traitants ultérieurs** (§ 2 de L2 renvoie au
  Trust Center, sans engagement obtenu). Voir **S11**.

### 2.4 Menaces explicitement non couvertes (à ne pas passer sous silence)

1. **Conflit d'intérêts × accès administrateur** (S3) — le plus structurant.
2. **Chemin de croisement entre deux clients** par la table de liaison de facturation (S4).
3. **Injection de consignes via le contenu d'un DCE** (S11) — le contenu d'un document lu
   par un modèle peut contenir des instructions ; aucune défense n'est décrite.
4. **Exposition croisée côté fournisseur de modèle** (S11) — un prestataire unique traite
   les DCE de plusieurs candidats concurrents.
5. **Volume volé avec la clé** en option B — le chiffrement au repos n'est pas une garantie
   contre un accès privilégié (reconnu par L2 ; ce n'est pas un constat, c'est une limite
   assumée et écrite).

---

## 3. Cloisonnement entre clients — vérification réelle

### 3.1 Le champ de cloisonnement est-il présent partout où c'est nécessaire ?

**Oui, sur le papier, à une exception.** `DATA-MODEL-V2.md` § 3.2 (lignes 162-171) déclare
`client_id` **obligatoire** sur « toute entité de contenu », et § 4.2 (lignes 241-247)
explique la redondance volontaire : *« c'est cette redondance qui rend le cloisonnement
vérifiable requête par requête, sans dépendre de la présence correcte d'une jointure »*.
§ 4.4 (lignes 261-273) partitionne les entités en trois familles : cloisonnées
directement (`utilisateur`, `entreprise`, `abonnement`, `evenement_facturation`),
cloisonnées via l'entreprise et la fiche mais portant `client_id` **en propre**
(19 entités listées), et globales sans `client_id` (`jeu_reference`, `valeur_reference`).

**Ce qui manque à cette partition (S4 et S5).**

- **`evenement_facturation_dossier`** (`DATA-MODEL-V2.md` § 11.4, lignes 967-982) **ne
  figure dans aucune des trois listes** et **ne porte pas** `client_id`. C'est le seul
  endroit où deux lignes de clients différents pourraient être liées sans que rien ne le
  détecte. Voir **S4**.
- **`fiche_version`** ne figure pas non plus dans la partition, mais c'est une **exception
  documentée et unique** (§ 3.2 lignes 173-175, § 6.1 ligne 411) : elle **est** l'axe de
  versionnement. C'est correct.
- **`tracabilite_valeur`** (§ 7.2, lignes 546-564) et **`validation_relecture`** (§ 6.4,
  lignes 471-488) listent `client_id` mais **omettent** `entreprise_id` et
  `fiche_version_id`, que § 3.2 déclare pourtant obligatoires « sans exception ». Voir **S5**.

### 3.2 Y a-t-il une entité orpheline ou un chemin qui croise deux clients ?

- **Entité orpheline :** aucune, à l'exception du cas de liaison ci-dessus (S4). Toute
  entité de contenu référence `entreprise_id` et `fiche_version_id` existants (I3, § 3.4
  ligne 208).
- **Chemin de croisement :** le modèle **ferme** les chemins qu'il pouvait fermer —
  I4 (ligne 209) interdit qu'une valeur soit tracée vers un document d'un autre client ;
  I5 (ligne 210) interdit qu'un jeu global porte une donnée client ; I2 (ligne 207) tient la
  cohérence du `client_id` avec la racine. Il **en reste un** : la table de liaison de
  facturation (S4).
- **Références polymorphes.** `tracabilite_valeur.(entite, enregistrement_id)` est une
  référence polymorphe sans clé étrangère portable ; L3 le **dit** et renvoie à un contrôle
  applicatif (I4) — c'est une limite **assumée et écrite** (§ 7.6, § 14, point ouvert 11),
  pas un oubli. Elle affaiblit la garantie : le cloisonnement y est **applicatif**, donc
  vérifiable seulement par un test d'isolation qui n'existe pas encore.

### 3.3 Une information d'un candidat peut-elle nourrir un autre candidat ?

**Non par la structure, sauf par les deux fuites nommées ci-dessus.** Recherche faite sur
`DATA-MODEL-V2.md` et `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` :

- Les **jeux de référence** sont globaux et **sans donnée client** (I5, § 8.4 lignes
  663-670) : c'est du vocabulaire, jamais une donnée d'entreprise. Correct au regard du
  secret des affaires.
- `SPEC-MVP-V2.md` § 3.3 (ligne 259-261) interdit explicitement de « croiser les DCE de
  plusieurs entreprises candidates » : la règle est écrite.
- **Le seul vecteur d'échange entre candidats n'est pas dans le modèle mais dans la chaîne
  de traitement** : le fournisseur de modèle unique, qui reçoit les DCE de tous les
  candidats (S11), et l'administrateur qui peut tout lire (S3). Ces deux points sont
  **absents** de l'analyse de L2 et de L3.

**Conclusion section 3.** Le cloisonnement **par la structure** est réel et vérifiable
requête par requête (c'est un vrai progrès sur la v1), avec **deux réserves** : un chemin de
croisement résiduel (S4) et des colonnes d'invariants incomplètes (S5). Il **ne constitue
pas** une garantie d'isolation cryptographique — L3 le dit lui-même (§ 3.4 note lignes
213-218), et je le confirme.

---

## 4. Note RGPD — trois listes

*Avertissement : je ne suis pas juriste.** Je documente et je signale. Je ne tranche ni la
base légale, ni la durée de conservation, ni la qualification responsable/sous-traitant. Ces
points relèvent de **D4** (expertise juriste, fin de projet) et sont **bloquants pour la
commercialisation**, pas pour le développement.*

### 4.1 Ce qui est traité (et où, avec preuve)

| Catégorie | Champ / entité (preuve) | Nature |
|---|---|---|
| CV nominatifs | `cv.nom`, `cv.prenom`, `cv