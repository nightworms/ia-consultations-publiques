# DATA-MODEL-V2 — Modèle de données v2

*Lot L3 — agent `dev-back`. Phase 2 du projet *IA consultations publiques*. Écrit le
30 septembre 2026.*

**Ce document remplace `docs/DATA-MODEL.md` (v1, phase 1).** La v1 reste **intacte**
dans le dépôt : c'est une archive de phase 1, pas un document à corriger. Le § 1 dit
précisément ce qui change entre v1 et v2.

> **Statut du document.** Conception sur le papier, non définitive. **Aucun schéma
> n'est appliqué, aucune base n'est créée, aucune migration n'est écrite, aucun code
> n'accompagne ce document.** Les indications de type sont **indicatives** (§ 3.1).
> Les points marqués « à valider », « à vérifier » ou « à compléter » restent ouverts
> et doivent être tranchés par Anthony ou par un juriste avant toute implémentation.

**Autorités, en cas de contradiction :**

| Sujet | Document qui fait foi |
|---|---|
| Décisions de cadrage (D1 à D6) | `docs/DECISIONS.md` |
| **Structure** des données (tables, champs, invariants) | **ce document** |
| **Contenu** des jeux de référence (nomenclatures, listes métier) | `docs/NOMENCLATURE-REFERENCE.md` (lot L5) |
| Énoncé d'une garantie de confidentialité | `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` (lot L2) |
| Proposition de moteur et de stack | `docs/STACK-PROPOSAL.md` (lot L1) |
| Spécification fonctionnelle | `docs/SPEC-MVP-V2.md` (lot L4) |

**Hors périmètre de ce document, et non traité ici :** écriture de code, création de
base, écriture de migration, modification de `src/`, de `README.md`, de `PROJECT.md`
ou de `docs/DATA-MODEL.md` v1 ; installation ou déploiement ; intégration d'un
prestataire de paiement ; veille ; mémoire technique rédigé automatiquement ; dépôt
de pli ; portail côté acheteur public. Le **paiement** est hors périmètre : le § 11
prévoit la structure qui permet de **compter** et de **rattacher**, sans montant, sans
tarif et sans prestataire.

**Ligne rouge rappelée (`PROJECT.md` § 5).** L'IA ne signe rien, n'invente aucune
référence ni aucun chiffre, ne fixe aucun prix, ne garantit aucune conformité. Le
modèle ne porte **aucune valeur « générée par l'IA »** : toute valeur a une origine
déclarée et, si elle est extraite, un document source (§ 7).

---

## Sommaire

0. Comment lire ce document
1. Ce qui change par rapport à la v1
2. Principes de conception
3. Conventions du modèle
4. Cloisonnement multi-client (D1)
5. Racines : `client`, `utilisateur`, `entreprise`, `entreprise_version`
6. Versionnement, états et relecture humaine (C3, C9, C10)
7. Traçabilité au niveau de la valeur (C2)
8. Conteneur de jeux de référence (D2, décision D-C1)
9. Documents et pièces
10. Familles de contenu (F1 à F9)
11. Facturation — abonnement et à l'acte (D3)
12. Traitement nommé des constats de la phase 1 (C1, C2, C3, C4, C9, C10)
13. Points dépendant de l'option de confidentialité retenue
14. Portabilité du modèle (décision D-C5)
15. Points ouverts
16. Rappels de sécurité et de dépôt

---

## 0. Comment lire ce document

Les entités sont décrites par des **tableaux de champs**, jamais par du SQL
exécutable. Trois lectures sont possibles et complémentaires :

- **conception** — § 2 à § 11 : le modèle lui-même ;
- **vérification** — § 12 : chaque constat de la phase 1, ce qui a été décidé, et
  où la décision est visible dans le modèle ;
- **décision** — § 13 : ce qui dépend de l'option de confidentialité, et § 15 : ce
  qui reste ouvert.

Convention de notation d'un champ : `` `nom_champ` `` (type logique) — obligatoire ou
non — rôle. Le symbole « + techniques » renvoie aux colonnes communes décrites en
§ 3.2 et « + traçabilité » à celles décrites en § 7.

---

## 1. Ce qui change par rapport à la v1

| # | Modèle v1 | Modèle v2 | Motif | Constat traité |
|---|---|---|---|---|
| 1 | `entreprise` est la racine **non versionnée** ; `fiche_version_id` « obligatoire pour toute entité de contenu » mais absent de la racine | scission : `entreprise` = ancre stable, `entreprise_version` = contenu identité **versionné** | en v1, une modification d'identité mutait une fiche publiée, ce qui contredit l'immuabilité affirmée v1 § 5 ; le cas de la racine disparaît | **C10** |
| 2 | traçabilité (`origine`, `confiance`, `source_document_id`) **par enregistrement** | traçabilité **par valeur** (table `tracabilite_valeur`), avec héritage depuis l'enregistrement | l'interface affiche la traçabilité **par champ** et un même enregistrement peut être nourri par plusieurs documents | **C2** |
| 3 | aucun support du verrou de relecture | entité `validation_relecture` : relecteur, horodatage, état, empreinte du contenu validé, révocation | la ligne rouge « la relecture humaine est un blocage technique » n'était pas représentable | **C3** |
| 4 | `fiche_version.statut` : 3 états (`brouillon`, `publiee`, `archivee`) | 7 états alignés sur l'interface + table `fiche_famille` pour l'avancement par famille | deux vocabulaires pour la même chose, granularité de validation non tranchée | **C9** |
| 5 | `type_document` : énumération de 14 valeurs « indicative » écrite dans le modèle | **jeu de référence** `document.type_document`, une seule liste pour le modèle **et** l'interface | deux listes divergentes (14 vs 6) ; et D2 exige que les listes soient des données, pas des colonnes | **C4** |
| 6 | `entreprise` sans `iban`, `bic`, `effectif` | `entreprise_version` porte `iban`, `bic`, `effectif`, `date_effectif`, `piece_rib` | champs saisis par l'utilisateur sans emplacement dans le modèle | **C1** |
| 7 | une seule entreprise implicite ; cloisonnement non modélisé | entité `client` + colonne de cloisonnement `client_id` **sur toute entité de contenu** | D1 : le client est l'entreprise candidate, et D6 exige une isolation stricte | D1, D6 |
| 8 | aucune notion de facturation | `abonnement`, `dossier`, `evenement_facturation`, `evenement_facturation_dossier` | D3 : prévoir abonnement **et** facturation d'un dossier déposé | D3 |
| 9 | énumérations métier figées dans le schéma (`type_assurance`, `categorie`, `famille` produit…) | valeurs portées par des **jeux de référence** `metier.*` | D2 : généraliste dès le départ, le métier est une donnée | D2 |
| 10 | § 0 « Proposition de stack — Python / SQLite / FastAPI » | **supprimé** ; renvoi à `docs/STACK-PROPOSAL.md` | la v1 figeait une stack non validée (D5) | D5, D-C5 |
| 11 | champs calendaires dispersés, seuils implicites | statuts calculés documentés (§ 3.3), seuils toujours non fixés | aucun seuil ne doit être inventé | v1 § 15 |

Ce qui **ne change pas** : l'unité versionnée (la fiche entreprise), l'immuabilité
d'une version validée, l'interdiction des valeurs « générées par l'IA », la
distinction *document extrait* / *saisie entreprise*, et le principe « aucune valeur
sans source ».

---

## 2. Principes de conception

1. **Traçabilité à la valeur.** Chaque **valeur** exposée porte son origine, son
   niveau de vérification et, si elle est extraite, le document et l'emplacement
   exacts dont elle provient (§ 7). C'est la traduction technique de la ligne rouge.
2. **Aucune valeur produite par l'IA.** `origine` ne prend que deux valeurs :
   `document_extrait` ou `saisie_entreprise`. Une proposition faite par le service
   n'est enregistrable qu'après confirmation humaine, et reste une valeur
   `document_extrait` si elle a été lue dans un document.
3. **Généraliste par construction.** La structure ne connaît aucun métier. Tout
   vocabulaire métier (types de travaux, familles de produits, catégories d'engins,
   domaines de certification) est un **jeu de référence** (§ 8), jamais une colonne
   ni une table dédiée.
4. **Cloisonnement vérifiable.** Toute entité de contenu porte `client_id` et se
   rattache à une racine elle-même cloisonnée (§ 4). Aucune entité orpheline.
5. **Versionnement et relecture.** Rien n'est modifié « en place » ; toute
   modification après validation crée une nouvelle version et **révoque** la
   validation (§ 6).
6. **Relecture humaine bloquante.** Une fiche ne peut pas être *relue et validée*
   sans une action humaine nommée et horodatée. L'application ne pose jamais cet
   état (§ 6).
7. **Aucun seuil, aucune norme, aucun prix dans le modèle.** Le modèle **rend le
   calcul possible** ; il ne fixe aucune valeur de seuil, aucune durée de validité,
   aucun montant (§ 3.3 et § 15).
8. **Portabilité.** Le modèle ne présuppose aucun moteur (§ 14).

---

## 3. Conventions du modèle

### 3.1 Types logiques

Les types ci-dessous sont **logiques**. La colonne « traduction indicative » donne
un ordre de grandeur pour un moteur relationnel **quel qu'il soit** ; elle ne fige
aucun moteur et n'est pas une spécification de type.

| Type logique | Description | Traduction indicative |
|---|---|---|
| `identifiant` | clé technique opaque, jamais un numéro métier | texte, UUID v4 |
| `texte_court` | chaîne courte (≤ 255 caractères) | texte |
| `texte_long` | texte libre sans limite pratique | texte |
| `entier` | nombre entier | entier |
| `decimal` | nombre décimal | décimal |
| `montant` | montant + devise obligatoire | décimal + code devise ISO 4217 (3 caractères) |
| `date` | date seule, format `AAAA-MM-JJ` | texte ISO 8601 |
| `horodatage` | date **et heure**, avec fuseau | texte ISO 8601 ou type date-heure |
| `booleen` | vrai / faux | entier 0/1 |
| `code_reference` | code d'une valeur d'un jeu de référence (§ 8) | texte |
| `reference` | clé étrangère vers une entité de ce document | texte + intégrité référentielle |
| `piece` | référence vers un `document` (§ 9) | texte + intégrité référentielle |
| `liste` | références multiples | table de liaison |
| `empreinte` | empreinte cryptographique d'un contenu | texte hexadécimal |

### 3.2 Colonnes techniques communes

**Toute entité de contenu** porte ces colonnes ; elles ne sont pas répétées dans les
tableaux de familles.

| Colonne | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | identifiant technique de l'enregistrement |
| `client_id` | `reference` `client.id` | **oui** | **cloisonnement** — voir § 4 |
| `entreprise_id` | `reference` `entreprise.id` | oui | entreprise propriétaire du contenu |
| `fiche_version_id` | `reference` `fiche_version.id` | **oui, sans exception** | rattachement à la version de fiche (§ 6) |
| `date_creation` | `horodatage` | oui | création de la ligne |
| `date_modification` | `horodatage` | oui | dernière écriture |
| `sensibilite` | `code_reference` `securite.sensibilite` | oui | `publique` \| `interne` \| `confidentiel` (§ 3.3) |
| `statut_enregistrement` | `code_reference` `commun.statut_enregistrement` | oui | `actif` \| `archive` (un enregistrement n'est jamais supprimé en dur : il est archivé, cf. UI E3 « Archiver ») |

**Exception documentée — et unique :** l'entité `fiche_version` elle-même ne porte pas
`fiche_version_id` : elle **est** l'axe de versionnement. Elle porte en revanche
`client_id` et `entreprise_id`. C'est le traitement du constat **C10** (§ 12).

### 3.3 Statuts calculés (jamais stockés) et seuils

Les statuts suivants sont **dérivés à la lecture**, jamais écrits en base : les
stocker créerait une valeur que le temps rendrait fausse.

| Nom | Entrée | Valeurs | Règle |
|---|---|---|---|
| `statut_validite` | date de fin de validité d'une pièce ou d'un élément | `valide` \| `echeance_proche` \| `expire` \| `non_renseigne` | comparaison de la date à la date du jour ; la **fenêtre d'alerte** qui sépare `valide` de `echeance_proche` est un **réglage produit utilisateur**, pas une règle réglementaire |
| `completude_famille` | présence des champs de niveau N1/N2 de l'interface | `complete` \| `incomplete` | recalculé à chaque lecture |

> **Aucun seuil n'est fixé dans ce document.** La question « à combien de jours avant
> échéance passe-t-on en `echeance_proche` ? » reste une décision d'Anthony
> (`docs/DATA-MODEL.md` § 16 point 3, `docs/UI-SAISIE.md` § 13 point 3). Le modèle se
> contente de **rendre le calcul possible**. De même, **aucune durée de validité
> légale n'est écrite en dur** : la date se lit sur le document ; à défaut, elle est
> `non_renseigne`.

Les niveaux d'exigence N1/N2/N3 de l'interface (`docs/UI-SAISIE.md` § 4) restent
**propres à l'interface** : ils ne sont pas stockés (ce sont des règles d'écran), et
l'application les applique pour calculer la complétude. Point ouvert § 15.

### 3.4 Invariants d'intégrité

Ces invariants sont **énoncés pour être vérifiables** ; l'application les fait
respecter, et un contrôle périodique les compte (résultat attendu : zéro ligne en
écart).

| # | Invariant | Contrôle attendu |
|---|---|---|
| I1 | `client_id` est non nul sur **toute** entité de contenu | compter les lignes où `client_id` est nul : doit être 0 |
| I2 | le `client_id` d'un enregistrement est **égal** à celui de son `entreprise`, lequel est égal à celui de sa `fiche_version` | compter les lignes de chaque entité dont le `client_id` diffère du `client` de la racine — doit être 0 |
| I3 | aucune entité orpheline : tout enregistrement référence un `entreprise_id` et un `fiche_version_id` existants | compter les références non satisfaites — doit être 0 |
| I4 | une valeur de contenu extraite d'un document référence un `document` **du même client** | compter les `tracabilite_valeur` dont le document source appartient à un autre client — doit être 0 |
| I5 | un jeu de référence **global** ne contient aucune donnée client | contrôle de structure : les jeux `metier.*` et les autres jeux globaux ne portent pas de `client_id` (contrairement au modèle optionnel de § 8.4) |
| I6 | une validation `validee` n'est valide que si l'empreinte enregistrée correspond au contenu courant (§ 6.4) | recalculer l'empreinte du périmètre validé et compter les écarts — doit être 0 |

> **Le cloisonnement par `client_id` est une condition nécessaire, pas une garantie
> suffisante.** Il rend l'isolation **vérifiable par le modèle**, mais la résistance
> réelle (chiffrement, séparation des clés, accès de l'exploitant) dépend de l'option
> de confidentialité retenue : voir § 13 et `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`,
> à compléter après validation de ce document. **Ce document n'énonce aucune garantie
> de confidentialité.**

---

## 4. Cloisonnement multi-client (D1)

### 4.1 Pourquoi un `client` distinct de l'`entreprise`

D1 pose que **le client est l'entreprise candidate**. Techniquement, deux notions
doivent pourtant rester distinctes :

- le **client** est la partie contractante : c'est lui qui détient le compte, les
  utilisateurs, l'abonnement et les événements de facturation (D3) ;
- l'**entreprise** est l'entité juridique candidate dont la bibliothèque est décrite
  (SIREN, SIRET, KBIS, assurances, références).

Un client unique peut avoir besoin de décrire **plusieurs entités juridiques** (un
groupe, une holding, un mandataire). Le cas courant reste 1 client ↔ 1 entreprise.
La facturation, elle, est **du côté client** : elle ne se rattache pas à une entité
juridique décrite. C'est ce qui justifie la séparation.

### 4.2 Le champ de cloisonnement

- `client.id` est la **racine unique** du cloisonnement.
- **Toute** entité de contenu porte `client_id` (I1), **y compris** lorsqu'il serait
  déductible par jointure. Le champ est volontairement redondant : c'est cette
  redondance qui rend le cloisonnement **vérifiable requête par requête**, sans
  dépendre de la présence correcte d'une jointure dans le code applicatif.
- La redondance est tenue par l'invariant **I2** : la valeur doit être cohérente avec
  la racine. Elle n'est donc pas une source de vérité concurrente.

### 4.3 Mécanisme de séparation

| Plan | Mécanisme | Niveau de garantie |
|---|---|---|
| **Données** | colonne `client_id` sur toute entité de contenu, invariants I1 à I5, contexte client obligatoire par requête applicative | **vrai par construction** dans le modèle : le cloisonnement est représenté et contrôlable |
| **Données (renforcement)** | base ou schéma **distinct par client** ; c'est une option d'exploitation, pas une contrainte du modèle — le modèle est identique dans les deux cas, sans changement de structure | dépend de l'option de confidentialité (§ 13) |
| **Fichiers** | les pièces (`document`, § 9) sont stockées **hors base** sous un chemin préfixé par le client (ex. `clients/<client_id>/<document.id>`), le chemin étant porté par le champ `chemin_stockage` ; aucun nom de fichier fourni par l'utilisateur n'est utilisé tel quel | vrai par construction : le préfixe est obligatoire, l'`entreprise_id` et le `client_id` sont vérifiables |
| **Accès** | identité applicative rattachée à un seul `client` au MVP ; toute lecture écrit le client dans le contexte et toute requête filtre dessus | vrai par construction, à condition que le code respecte la règle — à vérifier par les tests d'isolation (lot L6) |
| **Chiffrement** | hors de ce document | **dépend entièrement de l'option retenue** — § 13 et `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`, à compléter après validation de ce document |

### 4.4 Aucune entité orpheline

Sont cloisonnées par `client_id` **direct** (ce sont des racines de leur plan) :
`utilisateur`, `entreprise`, `abonnement`, `evenement_facturation`.

Sont cloisonnées **via leur entreprise et leur fiche** (elles portent néanmoins
`client_id` en propre, I1) : `entreprise_version`, `representant_legal`,
`exercice_comptable`, `attestation`, `capacite_production`, `assurance`,
`certification`, `reference_chantier`, `effectif_metier`, `organigramme`, `cv`,
`moyen_materiel`, `produit`, `chapitre_memoire`, `document`, `tracabilite_valeur`,
`validation_relecture`, `fiche_famille`, `dossier`.

Sont **globaux** (aucun `client_id`) : `jeu_reference`, `valeur_reference`, et toute
table de service sans donnée client. Ils ne contiennent aucune donnée d'entreprise
(I5) : ce sont des nomenclatures.

> Cas particulier : `dossier` porte à la fois `client_id` et `entreprise_id` — un
> dossier est un projet **d'une entreprise**, facturé **au client**. C'est le seul
> endroit où les deux plans se rejoignent, et il est explicite dans le modèle (§ 11).

---

## 5. Racines : `client`, `utilisateur`, `entreprise`, `entreprise_version`

### 5.1 `client` — la partie contractante

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | racine de cloisonnement |
| `libelle` | `texte_court` | oui | nom d'usage du compte (ex. exemple fictif : « Entreprise de démonstration ») |
| `statut` | `code_reference` `client.statut` | oui | `actif` \| `suspendu` \| `resilie` |
| `date_creation` | `horodatage` | oui | — |
| `date_resiliation` | `date` | non | renseigné à la résiliation ; conditionne le **sort des données** (§ 13.4) |
| `sensibilite` | `code_reference` `securite.sensibilite` | oui | `interne` par défaut |

### 5.2 `utilisateur` — le compte d'accès

L'authentification multi-utilisateurs est **hors périmètre du MVP**
(`docs/UI-SAISIE.md` § 7 et § 13 point 2). L'entité est néanmoins **prévue**, pour
une raison précise et non négociable : le § 6 exige **l'identité du relecteur**. Deux
champs distincts coexistent donc :

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | un utilisateur appartient à un seul client au MVP |
| `identifiant_connexion` | `texte_court` | oui | à fixer (courriel, identifiant interne) |
| `nom_affichage` | `texte_court` | oui | nom présenté dans l'horodatage |
| `statut` | `code_reference` `utilisateur.statut` | oui | `actif` \| `archive` |
| `date_creation` | `horodatage` | oui | — |

**Aucun mot de passe, aucun secret d'authentification n'est décrit dans ce document.**
Ils ne vivront de toute façon jamais dans les tables de contenu, et jamais dans le
dépôt.

### 5.3 `entreprise` — l'ancre stable (modifiée en v2)

En v1, `entreprise` était à la fois l'ancre **et** le contenu. En v2 elle ne porte
plus que ce qui ne se versionne pas.

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `libelle_court` | `texte_court` | oui | nom d'usage dans l'interface (valeur d'affichage, pas une donnée légale) |
| `statut` | `code_reference` `entreprise.statut` | oui | `active` \| `archivee` |
| `date_creation` | `horodatage` | oui | — |
| `date_derniere_version` | `horodatage` | non | confort d'affichage ; la vérité est dans `fiche_version` |

**Pourquoi ce changement.** En v1, modifier la raison sociale ou le SIRET modifiait
la ligne unique `entreprise`, donc **une fiche publiée** — en contradiction directe
avec l'immuabilité affirmée en v1 § 5 règle 1. Le contenu d'identité devient une
entité de contenu versionnée comme les autres.

### 5.4 `entreprise_version` — le contenu d'identité (famille F1)

Racine de la famille Identité. Porte les colonnes techniques communes (§ 3.2) **dont
`fiche_version_id`** — ce qui referme le constat **C10**.

| Champ | Type | Oblig. | Description / source |
|---|---|---|---|
| `raison_sociale` | `texte_court` | oui | KBIS / avis SIRENE |
| `siren` | `texte_court` (9 chiffres) | oui | avis SIRENE (INSEE) |
| `siret_siege` | `texte_court` (14 chiffres) | oui | avis SIRENE — identifiant public d'établissement |
| `forme_juridique_code` | `code_reference` `entreprise.forme_juridique` | oui | liste **de référence**, à remplir à la source (insee) — **aucune liste inventée ici** |
| `capital_social` | `montant` | non | statuts |
| `date_creation_entreprise` | `date` | non | KBIS |
| `code_ape_naf` | `texte_court` | non | avis SIRENE |
| `numero_tva_intracommunautaire` | `texte_court` | non | avis SIRENE |
| `adresse_siege` | `texte_long` | oui | KBIS — rue, complément, code postal, commune, pays |
| `adresse_etablissement_principal` | `texte_long` | non | justificatif |
| `telephone` | `texte_court` | non | déclaratif |
| `email` | `texte_court` | non | déclaratif |
| `site_web` | `texte_court` | non | déclaratif |
| **`effectif`** | `entier` | non | **ajouté (C1)** — effectif total déclaré, à la `date_effectif` |
| **`date_effectif`** | `date` | non | **ajouté (C1)** — date à laquelle l'effectif est constaté : sans elle, l'effectif est ininterprétable |
| **`effectif_source_code`** | `code_reference` `rh.origine_effectif` | non | **ajouté (C1)** — d'où vient le chiffre : avis SIRENE, déclaration, DSN… (contenu du jeu : à la source, non inventé ici) |
| **`iban`** | `texte_court` | non | **ajouté (C1)** — champ **confidentiel**, masqué par défaut dans l'interface |
| **`bic`** | `texte_court` | non | **ajouté (C1)** — champ **confidentiel** |
| **`piece_rib`** | `piece` | non | **ajouté (C1)** — justificatif bancaire (`document` de type `rib`), pièce maîtresse : c'est la pièce qui a valeur, le `iban` structuré n'est qu'un confort de remplissage |

**Arbitrage sur les trois « effectifs » (demandé par C1).** Trois notions, trois
emplacements, aucune confusion possible :

| Notion | Où | Ce que c'est | Période | Usage |
|---|---|---|---|---|
| `effectif` + `date_effectif` | `entreprise_version` (F1 Identité) | effectif **total à une date donnée**, déclaré ou lu (SIRENE) | instantané daté | identifier l'entreprise (demandé par `PROJECT.md` § 3) |
| `effectif_moyen` | `exercice_comptable` (F2) | effectif **moyen de l'exercice**, issu des comptes | un exercice clos | capacité financière, critères de sélection |
| `effectif_metier` (`nombre`) | `effectif_metier` (F6) | effectif **par métier** | à la date de saisie | moyens humains, réponse technique |

Décision : **ce ne sont pas les mêmes grandeurs et elles ne doivent pas être
confondues.** Aucune n'écrase l'autre. Le modèle n'impose pas de cohérence
arithmétique entre elles ; si l'application affiche une incohérence, elle **signale**
(mention « à vérifier ») et n'arbitre pas à la place de l'humain.

**Coordonnées bancaires et ligne rouge.** L'IBAN est saisi pour **remplir une annexe**
d'un dossier, jamais pour prélever quoi que ce soit : **le module de paiement est hors
périmètre (D3)** et le modèle ne contient ni identifiant de prestataire, ni mandat de
prélèvement, ni moyen de paiement. Le champ est `confidentiel` ; en aucun cas un IBAN
réel ne doit entrer dans le dépôt (§ 16).

### 5.5 `representant_legal` (F1)

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `nom` | `texte_court` | oui | **donnée personnelle** |
| `prenom` | `texte_court` | oui | **donnée personnelle** |
| `fonction` | `texte_court` | oui | — |
| `qualite_engagement` | `texte_court` | non | libellé repris du document ; **aucune interprétation juridique automatique** |
| `date_nomination` | `date` | non | PV de nomination |
| `date_cessation` | `date` | non | — |
| `statut` | `code_reference` `rh.statut_mandat` | oui | `en_exercice` \| `cesse` |
| `piece` | `piece` | non | justificatif (KBIS, statuts, PV) |

---

## 6. Versionnement, états et relecture humaine (C3, C9, C10)

### 6.1 `fiche_version` — l'axe de versionnement

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | — |
| `numero_version` | `entier` | oui | 1, 2, 3… croissant par entreprise |
| `statut` | `code_reference` `fiche.statut_version` | oui | **7 valeurs** — § 6.2 |
| `version_parente_id` | `reference` `fiche_version.id` | non | version dont celle-ci dérive |
| `date_creation` | `horodatage` | oui | — |
| `date_derniere_ecriture` | `horodatage` | oui | sert au calcul de révocation (§ 6.4) |
| `commentaire` | `texte_long` | non | motif de la version |

*Elle ne porte pas `fiche_version_id` : elle est l'axe de versionnement (§ 3.2).*

**Règles (inchangées sur le fond depuis la v1) :**

1. Une version `validee` (ex-`publiee`) est **immuable**. Toute correction crée une
   **nouvelle** version.
2. Un enregistrement modifié crée une nouvelle ligne rattachée à la nouvelle
   `fiche_version_id` ; l'ancienne ligne reste rattachée à la version précédente.
3. Une version `archivee` reste lisible : elle prouve ce qui a été fourni pour une
   consultation donnée.
4. Chaque entité de contenu référence **une et une seule** `fiche_version_id`.

### 6.2 `fiche.statut_version` — les états, alignés sur l'interface (C9)

Le modèle adopte **les six états de l'interface** (`docs/UI-SAISIE.md` E0,
lignes 184-186) plus un état technique d'archivage.

| État du modèle (code) | Libellé affiché (interface) | Source de la vérité |
|---|---|---|
| `vierge` | Vierge | aucune entité de contenu rattachée |
| `en_saisie` | En cours de saisie | au moins une entité de contenu, socle N1 incomplet |
| `socle_complet` | Socle complet (non relue) | socle N1 complet, aucune validation en cours de validité |
| `en_relecture` | En relecture | la fiche a été ouverte en relecture (E7) ou une validation a été révoquée |
| `validee` | Relue et validée | une `validation_relecture` `validee` sur `cible_type = fiche` **et** empreinte concordante |
| `validee_puis_modifiee` | Validée puis modifiée (à relire) | une validation existe mais l'empreinte ne concorde plus (§ 6.4) |
| `archivee` | *(non affiché en E0)* | archivage explicite ; les six états de l'interface sont donc **tous couverts** |

**Table de correspondance inverse.** Les 3 états de la v1 (`brouillon`, `publiee`,
`archivee`) se projettent ainsi : `brouillon` recouvrait en réalité **quatre** états
distincts de l'interface (`vierge`, `en_saisie`, `socle_complet`, `en_relecture`) —
c'est précisément l'incohérence relevée par C9 ; `publiee` → `validee` (+
`validee_puis_modifiee` quand le contenu a bougé) ; `archivee` → `archivee`.

### 6.3 `fiche_famille` — l'avancement par famille

L'interface est explicite : « une famille peut être validée pendant qu'une autre reste
vierge : la progression est par famille, pas globale » (`docs/UI-SAISIE.md` § 7,
lignes 486-495). Le modèle le représente.

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | — |
| `fiche_version_id` | `reference` `fiche_version.id` | oui | — |
| `famille_code` | `code_reference` `fiche.famille` | oui | `identite` \| `capacites_financieres` \| `assurances` \| `certifications` \| `references_chantiers` \| `moyens_humains` \| `moyens_materiels` \| `fiches_produits` \| `memoire_technique` |
| `statut` | `code_reference` `fiche.statut_famille` | oui | `non_commencee` \| `demarree` \| `socle_complet` \| `validee` (4 états de l'interface, § 7 lignes 488-492) |
| `date_maj` | `horodatage` | oui | — |

Contrainte : un seul enregistrement par (`fiche_version_id`, `famille_code`).

### 6.4 `validation_relecture` — le verrou de relecture humaine (C3)

**Décision de granularité, prise ici et assumée :** la validation est **représentée à
deux niveaux** (`famille` et `fiche`), comme l'interface le décrit, mais **le niveau
qui fait foi pour un dossier est la fiche**. Une famille validée est une **étape de
progression** : elle ne dispense jamais de l'écran final E7 ni de la validation de
fiche. Motif : c'est la fiche entière qui est fournie à un dossier, et c'est
l'ensemble qui est présenté à la relecture en E7 (« seul E7 demande l'ensemble »).

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | — |
| `fiche_version_id` | `reference` `fiche_version.id` | oui | la version sur laquelle porte la validation |
| `cible_type` | `code_reference` `validation.cible` | oui | `fiche` \| `famille` |
| `famille_code` | `code_reference` `fiche.famille` | oui si `cible_type = famille` | — |
| **`relecteur_nom`** | `texte_court` | **oui** | **saisi par l'humain** (« le nom du relecteur », E7 point 4). Obligatoire en toutes circonstances : c'est la trace exigée par la ligne rouge |
| `relecteur_utilisateur_id` | `reference` `utilisateur.id` | non | renseigné **plus tard**, quand l'authentification multi-utilisateurs existera. Absent au MVP : c'est le nom saisi qui fait foi, et ce document ne prétend pas le contraire |
| **`date_validation`** | `horodatage` | **oui** | posé **automatiquement** au moment de l'action humaine, jamais saisi à la main |
| **`attestation_cochee`** | `booleen` | oui | « j'ai relu et corrigé les informations ci-dessus » (E7 point 4) |
| `statut` | `code_reference` `validation.statut` | oui | `validee` \| `revoquee` |
| `date_revocation` | `horodatage` | non | renseigné à la première modification (§ 6.5) |
| `motif_revocation` | `texte_court` | non | ex. « écriture sur un champ de la famille Assurances » |
| `empreinte_contenu` | `empreinte` | oui | empreinte du périmètre validé au moment de la validation — voir ci-dessous |
| `empreinte_algorithme` | `texte_court` | oui | nom de l'algorithme employé ; **aucun algorithme n'est imposé ici** (point ouvert § 15) |
| `commentaire` | `texte_long` | non | — |

**Le libellé de l'état est contraint par la ligne rouge :** « relue et validée par
humain ». Jamais « conforme », « validée par l'IA » ni « certifiée »
(`docs/UI-SAISIE.md` § 9).

### 6.5 Révocation à la première modification — comment c'est rendu vérifiable

Le verrou doit être **opposable**, pas déclaratif. Trois mécanismes se combinent :

1. **Écriture applicative.** Toute écriture sur un champ d'un périmètre validé écrit
   `statut = revoquee`, `date_revocation`, `motif_revocation` sur les
   `validation_relecture` concernées, et fait passer `fiche_version.statut` à
   `en_relecture` (fiche) ou `demarree` (famille).
2. **Empreinte de contenu (contrôle indépendant de l'écriture).** À la validation,
   l'application calcule une empreinte du périmètre validé (contenu canonique de la
   cible) et la stocke dans `empreinte_contenu`. À tout moment, **recalculer
   l'empreinte** et la comparer suffit à savoir si une validation « validee » est
   encore valable. C'est le point I6. C'est ce qui fait qu'un défaut de code
   (écriture qui oublie de révoquer) **ne suffit pas** à produire une validation
   indûment valable : le contrôle par empreinte le détecte.
3. **Immuabilité de la version.** Une version `validee` n'est pas modifiable : la
   correction passe par une **nouvelle** version (§ 6.1 règle 1), donc par une
   nouvelle fiche, avec sa propre validation. La révocation concerne le cas où la
   fiche est encore ouverte (états `en_saisie`, `en_relecture`, `socle_complet`).

**Ce que le modèle ne fait pas.** Il ne dit pas *quel* algorithme d'empreinte, ni
*quelle* sérialisation canonique : ce sont des choix d'implémentation, laissés
ouverts (§ 15). Il ne prétend pas non plus que le contrôle par empreinte empêche une
écriture : il la **rend détectable**.

---

## 7. Traçabilité au niveau de la valeur (C2)

### 7.1 La décision

**Décision : traçabilité portée au niveau de la valeur** (une ligne par champ
réellement tracé), **avec héritage par défaut depuis l'enregistrement.**

Pourquoi ce choix plutôt qu'une simple règle de projection :

- Les champs d'un même enregistrement viennent souvent de **sources différentes**.
  Une assurance : `assureur` et `numero_contrat` lus sur l'attestation, `montant_garantie`
  lu sur un avenant, `activites_couvertes` déclarées par l'entreprise. Une traçabilité
  par enregistrement **ne peut pas** répondre à « où cette valeur-là a-t-elle été lue ? »,
  qui est exactement la question de la ligne rouge et de l'écran E4.
- Le cas de l'identité est encore plus net : `entreprise_version` est **une seule
  ligne** portant des champs lus sur le KBIS, l'avis SIRENE et les statuts. La v1
  demandait elle-même « chaque champ d'identité pointe vers sa source » (v1 § 6,
  lignes 238-239) **sans que sa structure le permette** — c'est le cœur du constat C2.
- L'interface affiche la traçabilité **par champ** sous chaque valeur
  (`docs/UI-SAISIE.md` § 10, lignes 555-563). Le modèle doit donc porter la
  granularité que l'interface expose, pas une granularité qu'elle devrait deviner.
- L'héritage évite l'explosion documentaire : on n'écrit une ligne que pour les champs
  qui **dérivent** du niveau enregistrement. Un enregistrement entièrement extrait du
  même document n'a besoin d'**aucune** ligne de détail.

### 7.2 `tracabilite_valeur`

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement (I1) |
| `entite` | `code_reference` `tracabilite.entite` | oui | nom **logique** de l'entité concernée, pris dans une liste fermée de référence (ex. `entreprise_version`, `assurance`, `reference_chantier`…) |
| `enregistrement_id` | `identifiant` | oui | identifiant de la ligne concernée |
| `champ` | `texte_court` | oui | nom du champ concerné |
| `origine` | `code_reference` `tracabilite.origine` | oui | `document_extrait` \| `saisie_entreprise` — **jamais `genere_ia`** |
| `confiance` | `code_reference` `tracabilite.confiance` | oui | `verifie` \| `declare_non_verifie` \| `a_verifier` |
| `source_document_id` | `reference` `document.id` | oui si `origine = document_extrait` | document source (I4) |
| `source_emplacement` | `texte_court` | non | page, section, ligne |
| `source_date_extraction` | `horodatage` | non | quand la valeur a été extraite |
| `source_commentaire` | `texte_long` | non | ex. « montant garanti hors franchise » |
| `date_creation` | `horodatage` | oui | — |
| `date_modification` | `horodatage` | oui | — |

Contrainte : un seul enregistrement par (`entite`, `enregistrement_id`, `champ`).

### 7.3 Règle de projection (le compromis, écrit noir sur blanc)

| Cas | Ce qui est stocké | Ce que l'interface affiche |
|---|---|---|
| Tous les champs de l'enregistrement viennent de la **même** source | **aucune** ligne de détail : les colonnes de synthèse de l'enregistrement suffisent | la même source pour tous les champs |
| Un champ vient d'une **autre** source que le reste | une ligne `tracabilite_valeur` **pour ce champ seul** | la source du champ pour ce champ, celle de l'enregistrement pour les autres |
| Un champ **n'a aucune** source (ni détail, ni synthèse renseignée) | rien | « source non renseignée », `confiance` au mieux `a_verifier` — **jamais `verifie`** |

### 7.4 Colonnes de synthèse (conservées, rôle redéfini)

Chaque entité de contenu porte les colonnes suivantes, qui ne sont **plus** la source
de vérité mais un **résumé** de la traçabilité des valeurs :

| Colonne | Type | Oblig. | Rôle |
|---|---|---|---|
| `origine` | `code_reference` `tracabilite.origine` | oui | `document_extrait` \| `saisie_entreprise` \| **`mixte`** (nouvelle valeur : plusieurs origines dans l'enregistrement) |
| `confiance` | `code_reference` `tracabilite.confiance` | oui | **la plus faible** des confiances de l'enregistrement (règle : la confiance d'un ensemble ne peut pas dépasser celle de son maillon le plus faible) |
| `source_document_id` | `reference` `document.id` | non | renseigné **uniquement** si l'enregistrement entier vient d'un seul document. Obligatoire si `origine = document_extrait` |

### 7.5 Règles de traçabilité (opposables)

1. `origine = document_extrait` **exige** un `source_document_id` (au niveau de la
   valeur ou de l'enregistrement). Sans document, l'origine est `saisie_entreprise`.
2. `origine = saisie_entreprise` sans document plafonne la confiance à
   `declare_non_verifie`.
3. `confiance = verifie` n'est possible que si une source existe **et** a été
   contrôlée par un humain.
4. Aucune valeur n'existe sans origine : une valeur « proposée » par le service et
   non confirmée n'est **pas** enregistrée comme une valeur — elle vit dans l'écran
   (E4 : « proposition à confirmer »), pas dans le modèle.

### 7.6 Verrouillage de l'entité racine (C10, complément)

`entreprise` (l'ancre, § 5.3) ne porte **aucun** champ de valeur métier : elle n'a donc
pas besoin de traçabilité et reste en dehors. Tout ce qui a une valeur à tracer vit dans
`entreprise_version`, qui porte `fiche_version_id`. **Le constat C10 disparaît parce
que le « cas de la racine » n'existe plus.**

*L'ancre `entreprise` ne porte pas non plus les colonnes de synthèse de traçabilité :
elle ne décrit aucun fait, seulement une existence et un libellé d'affichage.*

---

## 8. Conteneur de jeux de référence (D2, décision D-C1)

### 8.1 Décision D-C1, appliquée telle quelle

Un **jeu de référence** est identifié par un **namespace** : chaîne en **minuscules**,
`. ` comme séparateur ; les jeux métier sont préfixés **`metier.`** (ex.
`metier.etancheite`). Ses valeurs sont décrites par **exactement** les champs :
`code`, `libelle`, `parent_code`, `ordre`, `domaine`, `source`, `statut`.

Les jeux métier sont **des données** : jamais des colonnes, jamais des tables dédiées.

Le **contenu** des jeux appartient à `docs/NOMENCLATURE-REFERENCE.md` (lot L5).
**La structure appartient à ce document** et fait foi en cas de divergence.

### 8.2 `jeu_reference`

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `namespace` | `texte_court` | oui | **clé** — minuscules, `.` comme séparateur (ex. `metier.etancheite`, `document.type_document`) |
| `libelle` | `texte_court` | oui | nom lisible du jeu |
| `description` | `texte_long` | non | à quoi sert le jeu |
| `domaine` | `texte_court` | non | regroupement fonctionnel (ex. `document`, `securite`, `metier`) |
| `portee` | `code_reference` `referentiel.portee` | oui | `global` (au MVP, tous les jeux livrés) \| `client` (voir § 8.4) |
| `source` | `texte_court` | oui | origine du jeu : organisme, référentiel externe, ou « interne, proposition » |
| `statut` | `code_reference` `referentiel.statut` | oui | `actif` \| `deprecie` |
| `version` | `texte_court` | non | version du jeu, pour l'audit |
| `date_creation` | `horodatage` | oui | — |
| `date_modification` | `horodatage` | oui | — |

### 8.3 `valeur_reference`

Les sept champs imposés par D-C1, plus la clé et les colonnes techniques. **Ils ne
sont ni renommés ni complétés dans leur sens.**

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | identifiant technique |
| `namespace` | `reference` `jeu_reference.namespace` | oui | jeu auquel la valeur appartient |
| **`code`** | `texte_court` | oui | code stable de la valeur (jamais affiché tel quel : le libellé l'est) |
| **`libelle`** | `texte_court` | oui | libellé affiché, en français |
| **`parent_code`** | `texte_court` | non | code de la valeur parente **dans le même jeu** (hiérarchie) |
| **`ordre`** | `entier` | oui | ordre d'affichage |
| **`domaine`** | `texte_court` | non | sous-domaine fonctionnel |
| **`source`** | `texte_court` | oui | d'où vient cette valeur précise (organisme, document, ou « proposition interne à valider ») |
| **`statut`** | `code_reference` `referentiel.statut_valeur` | oui | `actif` \| `deprecie` |
| `date_debut_validite` | `date` | non | début de validité de la valeur dans le référentiel |
| `date_fin_validite` | `date` | non | fin ; une valeur périmée passe en `deprecie`, elle n'est **jamais supprimée** (les données historiques la référencent) |
| `date_creation` | `horodatage` | oui | — |
| `date_modification` | `horodatage` | oui | — |

Contraintes : un seul enregistrement par (`namespace`, `code`) ; `parent_code`
appartient au même `namespace` (intégrité à vérifier par l'application, une clé
étrangère ne pouvant pas exprimer « même namespace » de façon portable).

### 8.4 Portée `client` — réservée, non utilisée au MVP

Le champ `portee` existe pour ne pas se peindre dans un coin : un client pourrait un
jour vouloir son propre vocabulaire (ses appellations de produits, ses catégories
internes). **Au MVP, tous les jeux sont `global` et ne contiennent aucune donnée
client** (invariant I5). Si une portée `client` est ouverte plus tard, elle prendra un
`client_id` **sur la table de valeurs**, jamais sur les jeux globaux — et ce sera une
évolution de structure, donc une décision (point ouvert § 15).

### 8.5 Comment on ajoute un métier ou une valeur — **sans migration destructive**

**Ajouter un métier** (`metier.gros_oeuvre`, `metier.electricite`…) :

- une ligne dans `jeu_reference` (nouveau `namespace`) ;
- des lignes dans `valeur_reference` pour ce `namespace` ;
- **aucune** modification de table, **aucune** colonne, **aucune** migration.

**Ajouter une valeur** dans un métier existant ou dans une liste commune (ex. un
nouveau type de pièce) :

- une ligne dans `valeur_reference` avec un nouveau `code` ;
- **aucune** modification de table.

**Retirer une valeur :**

- `statut = deprecie` (+ `date_fin_validite`). **Jamais de suppression** : les
  enregistrements qui l'utilisent restent lisibles et traçables. Une suppression
  casserait la traçabilité historique, donc la ligne rouge.

**Corriger un libellé :**

- modification du `libelle` **sans toucher au `code`** : les données pointent le code,
  l'affichage suit. C'est pourquoi le code et le libellé sont deux champs distincts.

**Conséquence pour le schéma :** une seule structure générique porte tout le
vocabulaire du produit et de tous ses métiers. Rien de métier n'entre jamais dans le
schéma — c'est la traduction structurelle de D2.

### 8.6 Jeux de référence livrés avec le modèle (structure seulement)

Ce document **fixe la structure**, pas la liste. Les jeux ci-dessous sont **attendus**
par le modèle (chaque colonne `code_reference` ci-dessus pointe vers l'un d'eux) ; leur
**contenu** est à produire par `docs/NOMENCLATURE-REFERENCE.md` (L5) ou, pour les jeux
administratifs, à lire à la source.

| Namespace | Contenu attendu | Qui remplit |
|---|---|---|
| `securite.sensibilite` | `publique`, `interne`, `confidentiel` | ce document (fermé) |
| `commun.statut_enregistrement` | `actif`, `archive` | ce document (fermé) |
| `tracabilite.origine` | `document_extrait`, `saisie_entreprise`, (`mixte` pour la synthèse) | ce document (fermé) |
| `tracabilite.confiance` | `verifie`, `declare_non_verifie`, `a_verifier` | ce document (fermé) |
| `tracabilite.entite` | noms logiques des entités de contenu | ce document (fermé, recopié du § 10) |
| `referentiel.portee`, `referentiel.statut`, `referentiel.statut_valeur` | voir § 8.2-8.3 | ce document (fermé) |
| `fiche.famille` | les 9 familles § 10 | ce document (fermé) |
| `fiche.statut_version`, `fiche.statut_famille` | § 6.2 et § 6.3 | ce document (fermé) |
| `validation.cible`, `validation.statut` | § 6.4 | ce document (fermé) |
| `client.statut`, `utilisateur.statut`, `entreprise.statut` | § 5 | ce document (fermé) |
| `document.type_document` | types de pièces (**résout C4**) | **L5** + sources administratives ; l'ancienne liste v1 est reprise telle quelle comme point de départ |
| `entreprise.forme_juridique` | formes juridiques | **à la source (INSEE)** — aucune liste inventée |
| `rh.statut_mandat`, `rh.origine_effectif` | mandats, origine d'un effectif | **L5** + source |
| `attestation.type`, `assurance.type`, `certification.domaine`, `moyen.categorie`, `produit.famille`, `reference.nature_travaux` | vocabulaires métier | **L5** (`metier.*` quand le contenu est propre à un métier) |
| `facturation.formule`, `facturation.type_evenement`, `facturation.statut_evenement` | § 11 | ce document (structures ; **contenu commercial à valider par Anthony**) |

---

## 9. Documents et pièces

### 9.1 `document` — le document source

C'est la brique de traçabilité : toute valeur extraite pointe vers un document de
cette table.

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | — |
| `fiche_version_id` | `reference` `fiche_version.id` | oui | un document est rattaché à la version dans laquelle il a été déposé |
| `type_document` | `code_reference` `document.type_document` | oui | **jeu de référence unique** (résout C4) — plus d'énumération en dur |
| `libelle` | `texte_court` | oui | nom lisible, ex. (fictif) « Attestation décennale 2026 » |
| `emetteur` | `texte_court` | non | qui a émis le document |
| `date_emission` | `date` | non | date portée par le document |
| `date_validite_debut` | `date` | non | — |
| `date_validite_fin` | `date` | non | échéance à surveiller |
| `reference_document` | `texte_court` | non | numéro du document |
| `chemin_stockage` | `texte_court` | oui | emplacement **préfixé par le client** (§ 4.3), hors dépôt |
| `deposant` | `code_reference` `document.deposant` | oui | `entreprise` \| `service` — qui a déposé la pièce |
| `empreinte_sha256` | `empreinte` | non | intégrité du fichier |
| `taille_octets` | `entier` | non | — |
| `mime_type` | `texte_court` | non | format déclaré ; **aucun format accepté n'est fixé ici** (voir points ouverts) |
| `sensibilite` | `code_reference` `securite.sensibilite` | oui | `confidentiel` par défaut pour CV, bilan, RIB |
| `stockage_client_seulement` | `booleen` | oui | **nouveau** — vrai si le fichier n'existe **que** chez le client (cas de l'option A, § 13.1). Permet au modèle de décrire une bibliothèque dont le service ne détient aucun fichier |

> **Champs d'écran E4 non couverts par le modèle.** L'écran E4 demande une « origine
> (`origine_valeur`) » au dépôt de la pièce : c'est le champ `origine` de synthèse
> (§ 7.4), qui décrit d'où vient **l'information** ; pour la pièce elle-même, c'est
> `deposant` qui répond. Les deux notions sont voisines mais distinctes, et le modèle
> les sépare explicitement pour éviter de confondre « qui a déposé le fichier » et
> « d'où vient la valeur ».

### 9.2 Formats acceptés et export — points ouverts reportés

C5 (délégations sans destinataire) **ne relève pas de ce document** : la v1 ne
tranchait effectivement ni le format d'export de la liste des manques ni les formats
de DCE acceptés. Le modèle v2 les **nomme** pour qu'ils ne soient plus perdus, sans
les trancher : voir points ouverts § 15 (points 8 et 9). Le champ `mime_type` existe
pour rendre la contrainte représentable quand elle sera tranchée.

---

## 10. Familles de contenu (F1 à F9)

Chaque entité porte les colonnes communes (§ 3.2) et les colonnes de synthèse de
traçabilité (§ 7.4). « + traçabilité » renvoie à § 7.

### F1 — Identité → `entreprise_version` (§ 5.4) + `representant_legal` (§ 5.5)

Champs sensibles : `siret_siege` (identification publique mais donnée d'entreprise),
`iban`, `bic`, `piece_rib` (**confidentiel**), `representant_legal.*` (données
personnelles, **confidentiel**).

### F2 — Capacités financières

**`exercice_comptable`** (1 par année, ≥ 3 dernières) :

| Champ | Type | Oblig. | Description / source |
|---|---|---|---|
| `annee_exercice` | `entier` | oui | bilan / liasse fiscale |
| `date_cloture` | `date` | non | bilan |
| `chiffre_affaires` | `montant` | oui | liasse fiscale |
| `resultat_net` | `montant` | non | bilan |
| `capitaux_propres` | `montant` | non | bilan |
| `total_bilan` | `montant` | non | bilan |
| `effectif_moyen` | `entier` | non | **distinct de `effectif`** (§ 5.4) — source : déclaration sociale |
| `piece` | `piece` | non | → `document` (`bilan`, `liasse_fiscale`) |
| `sensibilite` | — | oui | `confidentiel` |

**`attestation`** — pièces justificatives à durée de validité :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `type_attestation` | `code_reference` `attestation.type` | oui | jeu de référence (contenu : L5 et source) |
| `emetteur` | `texte_court` | oui | organisme émetteur |
| `date_emission` | `date` | oui | — |
| `date_validite_fin` | `date` | non | échéance à surveiller |
| `montant_engage` | `montant` | non | ex. capacité financière |
| `piece` | `piece` | oui | → `document` |

> **À vérifier.** La durée de validité dépend de l'émetteur et de la nature de la
> pièce : elle n'est **pas** codée en dur, elle est lue sur le document, et à défaut
> `non_renseigne`. **Aucun seuil, aucune durée n'est inventé ici.**

**`capacite_production`** : `description` (`texte_long`), `unite` (`texte_court`),
`valeur` (`decimal`), `commentaire` (`texte_long`).

### F3 — Assurances

**`assurance`** :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `type_assurance` | `code_reference` `assurance.type` | oui | jeu de référence (contenu : L5) |
| `assureur` | `texte_court` | oui | attestation |
| `numero_contrat` | `texte_court` | non | attestation |
| `montant_garantie` | `montant` | non | attestation |
| `franchise` | `montant` | non | attestation |
| `date_debut` | `date` | oui | attestation |
| `date_echeance` | `date` | oui | échéance **critique** |
| `activites_couvertes` | `texte_long` | non | étendue et nature des travaux garantis |
| `piece` | `piece` | oui | → `document` de type `attestation_assurance` |

`statut_validite` est **calculé** (§ 3.3), jamais stocké.

### F4 — Certifications et qualifications

**`certification`** : `intitule` (`texte_court`, **repris du certificat, jamais
reconstitué**), `organisme` (`texte_court`, repris du certificat),
`domaine_code` (`code_reference` `certification.domaine`, jeu de référence — remplace
le champ libre `domaine_metier` de la v1 pour rester métier-agnostique tout en restant
filtrable), `numero_certificat` (`texte_court`), `date_obtention` (`date`),
`date_echeance` (`date`), `piece` (`piece` → `document` de type `certificat`).

### F5 — Références de chantiers

**`reference_chantier`** : `intitule_operation`, `maitre_ouvrage` (`texte_court`),
`nature_travaux_code` (`code_reference` `reference.nature_travaux` — jeu de référence,
le texte libre de la v1 est conservé **en plus**, sous `nature_travaux_libelle`, pour
ne rien perdre), `lieu_commune`, `lieu_departement` (`texte_court`), `date_debut`,
`date_fin` (`date`), `montant` (`montant`), `duree_mois` (`entier`),
`surface_traitee` (`decimal`) + `surface_unite` (`texte_court`), `description`
(`texte_long`), `competences_appliquees` (`texte_long`, pour le rapprochement avec un
DCE), `attestation_bonne_execution` (`piece`), `photos` (`liste` de `piece`),
`contact_reference` (`texte_court`, **donnée personnelle — confidentiel**).

### F6 — Moyens humains

- **`effectif_metier`** : `metier_code` (`code_reference` `metier.*` ou
  `rh.metier`), `metier_libelle` (`texte_court`, libellé tel que saisi),
  `nombre` (`entier`), `commentaire` (`texte_long`).
- **`organigramme`** : `piece` (`piece`), `description` (`texte_long`),
  `date_maj` (`date`).
- **`cv`** : `nom`, `prenom` (`texte_court`, **données personnelles**), `fonction`
  (`texte_court`), `diplomes` (`texte_long`), `annees_experience` (`entier`),
  `cv_piece` (`piece` → `document` de type `cv`), `sensibilite = confidentiel`.
  `annees_experience` est **saisi ou lu** : jamais déduit d'une date par l'outil.

> **RGPD — à cadrer hors modèle.** Base légale, information des personnes, durée de
> conservation et sort des données ne sont **pas** tranchés ici (point ouvert § 15).

### F7 — Moyens matériels

**`moyen_materiel`** : `categorie_code` (`code_reference` `moyen.categorie`),
`designation` (`texte_court`), `quantite` (`entier`), `marque_modele` (`texte_court`),
`annee` (`entier`), `propriete` (`code_reference` `moyen.propriete` :
`propre` \| `location`), `disponibilite` (`texte_court`), `justificatif` (`piece`).

### F8 — Fiches techniques produits

**`produit`** : `fournisseur` (`texte_court`), `reference_produit` (`texte_court`,
**référence exacte du fournisseur, jamais reconstituée**), `designation`
(`texte_court`), `famille_code` (`code_reference` `produit.famille` — jeu de
référence, remplace l'énumération v1), `domaine_application` (`texte_long`),
`fiche_technique` (`piece`), `certificats` (`liste` de `piece`), `avis_technique`
(`piece`), `date_validite_document` (`date`).

> **Ligne rouge.** Un avis technique ou un certificat est stocké **tel quel** : le
> modèle ne présume ni sa validité ni sa portée. La référence produit est recopiée du
> document fournisseur.

### F9 — Mémoire technique type

**`chapitre_memoire`** : `titre` (`texte_court`), `ordre` (`entier`),
`contenu_texte` (`texte_long`), `statut` (`code_reference`
`memoire.statut_chapitre` : `brouillon` \| `accepte` \| `archive`),
`date_redaction` (`date`), `references_liees` (`liste` de `reference`
`reference_chantier.id`), `documents_associes` (`liste` de `piece`).

> **Périmètre strict.** Ce modèle **stocke** un mémoire technique type réutilisable ;
> il ne décrit **pas** la rédaction automatique d'un mémoire (hors périmètre, et
> question d'Anthony § 15). Un chapitre réutilisé dans un dossier reste traçable
> jusqu'à sa source et exige la relecture humaine (§ 6.4) : **la signature n'est
> jamais automatisée.**

---

## 11. Facturation — abonnement et à l'acte (D3)

**Ce que D3 demande :** le modèle doit **prévoir** l'abonnement mensuel **et** la
facturation ponctuelle d'un projet déposé, savoir **compter** les deux et **rattacher**
un dossier à sa facturation. **Ce que ce document ne fait pas :** aucun prestataire de
paiement, aucun montant, aucun tarif, aucune devise de prix, aucune intégration.
**Statut de cette section : à valider.**

### 11.1 `abonnement`

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement — c'est le **client** qui s'abonne |
| `formule_code` | `code_reference` `facturation.formule` | oui | identification de la formule. **Le contenu commercial de ce jeu n'est pas défini ici** : à valider par Anthony (aucun tarif dans ce document) |
| `statut` | `code_reference` `facturation.statut_abonnement` | oui | `actif` \| `suspendu` \| `resilie` |
| `date_debut` | `date` | oui | — |
| `date_fin` | `date` | non | — |
| `periodicite` | `code_reference` `facturation.periodicite` | oui | ex. `mensuelle` — pas de montant associé |
| `commentaire` | `texte_long` | non | — |

### 11.2 `dossier` — le projet déposé

Le modèle n'avait **aucune** notion de dossier en v1 : D3 en exige une, puisqu'il
faut rattacher « un projet déposé » à sa facturation.

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `entreprise_id` | `reference` `entreprise.id` | oui | l'entreprise qui répond |
| `fiche_version_id` | `reference` `fiche_version.id` | oui | **quelle fiche a servi** (§ 6.1 règle 4) |
| `reference_consultation` | `texte_court` | non | identifiant de la consultation **saisi par l'humain** ; l'outil ne va rien chercher et ne déduit rien |
| `objet` | `texte_long` | non | objet de la consultation, saisi par l'humain |
| `statut` | `code_reference` `facturation.statut_dossier` | oui | `en_preparation` \| `pret` \| `depose` \| `abandonne` |
| `date_depot` | `date` | non | renseignée **par l'humain** au moment du dépôt réel (le dépôt du pli est hors périmètre du produit) |
| `commentaire` | `texte_long` | non | — |

**Aucun prix, aucun montant, aucune marge, aucune grille de notation** dans cette
entité : la ligne rouge interdit au produit de fixer un prix.

### 11.3 `evenement_facturation` — ce qui doit être compté

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `id` | `identifiant` | oui | — |
| `client_id` | `reference` `client.id` | oui | cloisonnement |
| `type_evenement` | `code_reference` `facturation.type_evenement` | oui | `abonnement` \| `projet` — **les deux modes de D3, représentés par une seule table** |
| `abonnement_id` | `reference` `abonnement.id` | oui si `type_evenement = abonnement` | — |
| `date_evenement` | `horodatage` | oui | quand l'événement est constaté |
| `periode_debut`, `periode_fin` | `date` | oui si `type_evenement = abonnement` | période couverte par l'échéance d'abonnement |
| `source_declenchement` | `texte_court` | oui | ce qui a produit l'événement, en clair : ex. « échéance mensuelle » ou « dépôt du dossier » |
| `statut` | `code_reference` `facturation.statut_evenement` | oui | **`a_valider`** (valeur initiale) \| `constate` \| `annule` |
| `reference_externe` | `texte_court` | non | numéro d'une pièce comptable **externe** au produit, s'il en existe un ; le produit ne génère aucune facture |
| `commentaire` | `texte_long` | non | — |

**Aucun champ de montant, de tarif, de devise, de TVA ni d'identifiant de prestataire
de paiement.** Le produit **compte et rattache** ; il ne facture pas.

### 11.4 `evenement_facturation_dossier` — le rattachement dossier ↔ facturation

C'est la table de liaison exigée par D3.

| Champ | Type | Oblig. | Rôle |
|---|---|---|---|
| `evenement_facturation_id` | `reference` `evenement_facturation.id` | oui | — |
| `dossier_id` | `reference` `dossier.id` | oui | — |
| `role` | `code_reference` `facturation.role_rattachement` | oui | `principal` \| `complementaire` |
| `date_rattachement` | `horodatage` | oui | — |

Contrainte de comptage, à faire respecter par l'application (une clé étrangère ne
peut pas l'exprimer) : **un dossier ne peut être rattaché qu'à un seul événement de
type `projet` en rôle `principal`.** Un dossier déjà compté ne peut pas l'être deux
fois ; un second rattachement doit être `complementaire` **et** justifié par un
commentaire. C'est la règle qui rend le comptage fiable.

### 11.5 Ce qui reste à valider (statut D3 sur ce point)

- le contenu des jeux `facturation.*` (formules, périodicités) : **décision
  commerciale d'Anthony**, aucun tarif dans ce document ;
- la personne morale ou physique qui portera le contrat et facturera : décision
  ouverte (question 4 de `docs/PLAN-PHASE-2.md`), qui conditionne le RGPD et la
  facturation ;
- l'articulation entre abonnement et paiement à l'acte (un dossier déposé pendant un
  abonnement actif est-il facturé ?) : **règle de gestion à trancher**, le modèle
  permet les deux.

---

## 12. Traitement nommé des constats de la phase 1 (C1, C2, C3, C4, C9, C10)

Les constats C1, C2, C3, C4, C9, C10 de `docs/PLAN-DE-TEST.md` § 11 sont des
**exigences d'entrée** de ce document (décision D-C4). Traitement, un par un.

### C1 [majeur] — champs d'identité absents du modèle : **traité**

- **Constat.** `PROJECT.md` § 3 et `SPEC-MVP.md` § 3.3 listent effectivement l'« effectif »
  et les « coordonnées bancaires » dans l'Identité ; `UI-SAISIE.md` lignes **213-214**
  les présentent en champs de saisie ; `DATA-MODEL.md` § 3.1 n'a **aucun** champ
  `iban`, `bic` ni `effectif`.
- **Décision.** Les champs sont **ajoutés au modèle** (pas déclarés hors modèle) :
  `iban`, `bic` (`texte_court`, **confidentiel**), `piece_rib` (`piece`, la pièce
  justificative), `effectif` (`entier`), `date_effectif` (`date`) et
  `effectif_source_code` (`code_reference`).
- **Arbitrage `effectif` / `effectif_moyen`.**
  **Ce ne sont pas les mêmes grandeurs, et on ne les fusionne pas.**
  `effectif` (F1, identité) est un **instantané total à une date** (`date_effectif`) ;
  `effectif_moyen` (F2, `exercice_comptable`) est une **moyenne sur un exercice clos**.
  Supports, périodes, sources et usages diffèrent : identité vs capacité financière.
  Un troisième champ, `effectif_metier.nombre` (F6), décrit l'effectif **par métier**.
  Tableau des trois notions : § 5.4.
- **Où c'est visible.** § 5.4 (`entreprise_version`) pour `iban`, `bic`, `piece_rib`,
  `effectif`, `date_effectif`, `effectif_source_code` ; § 5.4 et § 10 F2 pour la
  distinction des effectifs ; § 16 pour la ligne rouge sur l'IBAN (jamais de donnée
  réelle dans le dépôt) ; § 11 pour l'absence de tout usage bancaire de type paiement.
- **Note de périmètre assumée.** L'`iban` est saisi pour **remplir une annexe** d'un
  dossier, jamais pour un prélèvement : **le paiement est hors périmètre (D3)**.

### C2 [majeur] — granularité de traçabilité : **traité**

- **Constat confirmé.** `DATA-MODEL.md` v1 § 2.3 / § 4 portait la traçabilité **par
  enregistrement** (lignes 103-114, 173) tandis que v1 § 6 demandait que « chaque champ
  d'identité pointe vers sa source » (lignes 238-239), ce que la structure de
  `entreprise`, ligne unique, ne permettait pas ; l'interface affiche la traçabilité
  **par champ** (`UI-SAISIE.md` § 10, lignes 555-563).
- **Décision.** **Traçabilité au niveau de la valeur**, portée par la table
  `tracabilite_valeur` (une ligne par champ, `entite` + `enregistrement_id` + `champ`),
  **avec héritage** : une ligne n'est écrite que pour les champs qui ne partagent pas
  la source de l'enregistrement. Les colonnes de synthèse de l'enregistrement
  subsistent, avec un rôle **redéfini** (résumé : `origine` peut valoir `mixte`,
  `confiance` = la plus faible des valeurs) et une règle de projection écrite (§ 7.3).
- **Pourquoi ce choix, et non une simple projection.** Parce que la projection seule
  **ne peut pas répondre** à la question que la ligne rouge rend opposable : *où
  cette valeur-là a-t-elle été lue ?* Elle est incapable de décrire un enregistrement
  nourri par plusieurs documents (assurance lue sur attestation + avenant) ni la ligne
  unique `entreprise_version` (KBIS + avis SIRENE + statuts). L'héritage évite en
  revanche le coût d'une ligne par champ partout où c'est inutile.
- **Limite assumée.** `(entite, enregistrement_id)` est une référence **polymorphe** :
  aucune clé étrangère portable ne peut la garantir (SQLite comme la plupart des
  moteurs hébergés). L'intégrité est donc **applicative**, contrôlée par la liste
  fermée `tracabilite.entite` et par le contrôle I4 (§ 3.4). C'est un point ouvert
  assumé, pas un oubli (§ 15, point 11).
- **Où c'est visible.** § 7 en entier ; § 3.2 (colonnes de synthèse) ; § 3.4 inv. I4 ;
  § 5.4 (l'identité devient une entité versionnée, donc traçable champ par champ).

### C3 [majeur] — verrou de relecture humaine non représentable : **traité**

- **Constat confirmé.** `UI-SAISIE.md` § 9 et E7 point 4 exigent : case cochée, **nom
  du relecteur**, **horodatage**, **révocation à la première modification**. Rien de
  tel n'existe dans la v1 (seuls `date_creation`/`date_modification` génériques).
- **Décision.** L'entité `validation_relecture` est créée (§ 6.4) avec :
  `relecteur_nom` (**obligatoire, saisi par l'humain**),
  `relecteur_utilisateur_id` (facultatif, pour plus tard), `date_validation`
  (**horodatage posé automatiquement**), `attestation_cochee`, `statut`
  (`validee` | `revoquee`), `date_revocation`, `motif_revocation`, et
  `empreinte_contenu` + `empreinte_algorithme`.
- **Granularité tranchée.** Deux niveaux sont représentés — `fiche` et `famille` —
  mais **le niveau qui fait foi pour un dossier est la fiche** (écran E7, « seul E7
  demande l'ensemble »). Une famille validée est une progression, pas un acquis pour
  le dossier.
- **Révocation.** À la première modification : écriture applicative de `revoquee` +
  horodatage + motif, **et** contrôle indépendant par **empreinte de contenu** : une
  validation n'est valide que si l'empreinte recalculée concorde (invariant I6). Un
  oubli dans le code ne suffit donc pas à laisser une validation valable.
- **Ligne rouge traduite techniquement.** Aucun chemin applicatif ne pose `validee`
  sans action humaine ; le libellé produit est « relue et validée par humain »,
  jamais « conforme » ni « certifiée ».
- **Où c'est visible.** § 6.4 (entité), § 6.5 (mécanisme de révocation), § 6.2 (états
  `en_relecture`, `validee`, `validee_puis_modifiee`), § 3.4 inv. I6.

### C4 [mineur] — deux listes pour `type_document` : **traité**

- **Constat confirmé.** `DATA-MODEL.md` ligne **154** : 14 valeurs ; `UI-SAISIE.md`
  ligne **346** (E4) : `attestation, certificat, bilan, CV, photo, autre` — dont
  « bilan », absent de la liste du modèle.
- **Décision.** **Une seule liste de référence** : le jeu de référence
  `document.type_document` (namespace, § 8). Le modèle ne porte plus aucune
  énumération de types de pièces en dur ; l'écran E4 ne définit plus sa propre liste,
  il **affiche** celle du référentiel, **regroupée par `parent_code`** (familles de
  pièces : identité, comptes, attestations, technique, personnel, exécution, visuel,
  autre). Les 14 valeurs de la v1 sont reprises **comme point de départ** ; l'ajout de
  « bilan » (déjà présent en v1) et la correspondance `CV` → `cv` sont explicitement
  listés comme valeurs à confirmer par L5 au titre du **contenu**.
- **Effet de bord positif.** `type_document` étant un jeu de référence, ajouter un
  type de pièce se fait **sans migration** (§ 8.5) — ce qui sert directement D2.
- **Où c'est visible.** § 9.1 (`document.type_document` en `code_reference`),
  § 8.6 (jeu attendu), § 8.5 (ajout sans migration).

### C9 [mineur] — états de fiche et granularité de validation : **traité**

- **Constat confirmé.** `UI-SAISIE.md` E0 lignes **184-186** : 6 états ;
  `DATA-MODEL.md` § 5 : `fiche_version.statut` à 3 valeurs. L'interface valide **par
  famille** (§ 7, lignes 486-495) ; le modèle versionnait **la fiche entière** (§ 5,
  ligne 198).
- **Décision (table de correspondance).** Le modèle adopte les **6 états de
  l'interface** plus un état technique d'archivage, avec la table de correspondance
  complète § 6.2 (et la projection inverse des 3 états v1 : `brouillon` recouvrait
  quatre états d'interface — c'est l'incohérence relevée).
- **Niveau de validation tranché.** Le modèle **versionne la fiche entière** (unité
  de versionnement inchangée) **et** suit l'avancement **par famille** dans
  `fiche_famille` (§ 6.3, 4 états d'interface). **La validation qui compte est celle
  de la fiche** ; la validation de famille est une étape de progression enregistrée,
  qui ne remplace pas E7. Motif : c'est la fiche entière qui alimente un dossier, et
  c'est l'ensemble qui est relu en E7.
- **Où c'est visible.** § 6.2, § 6.3, § 6.4 (colonne `cible_type`).

### C10 [mineur] — `fiche_version_id` obligatoire mais absent de la racine : **traité**

- **Constat confirmé.** v1 § 2.3 déclare `fiche_version_id` obligatoire pour « toute
  entité de contenu » (ligne 109) ; l'entité `entreprise` (§ 3.1) ne le porte pas.
- **Décision.** La racine de contenu devient `entreprise_version` (§ 5.4), qui porte
  **`fiche_version_id`**, `client_id` et `entreprise_id` comme toute entité de
  contenu. `entreprise` (§ 5.3) devient une **ancre stable**, sans contenu métier, donc
  sans besoin de versionnement ni de traçabilité. La règle « `fiche_version_id`
  obligatoire » s'applique alors **sans exception**, ce qui est plus simple et plus
  solide qu'une exception documentée.
- **Exception unique, explicite, et qui n'est pas un contenu :** `fiche_version`
  elle-même porte `client_id` et `entreprise_id` mais pas son propre
  `fiche_version_id` — **elle est l'axe de versionnement** (§ 3.2, § 6.1).
- **Effet de bord nécessaire.** Ce découpage corrige aussi une contradiction de la v1 :
  celle-ci affirmait l'immuabilité d'une version publiée tout en laissant l'identité
  hors versionnement — une correction d'identité mutait donc une fiche publiée.
- **Où c'est visible.** § 5.3, § 5.4, § 6.1, § 3.2 (exception), § 1 ligne 1.

### Constats hors de mon périmètre

| Constat | Pourquoi il n'est pas traité ici |
|---|---|
| **C5** (format d'export, formats de DCE acceptés) | sujet d'interface/implémentation : **nommé** en § 9.2 et reporté en points ouverts § 15 (points 8 et 9), avec un champ `mime_type` qui rendra la contrainte représentable |
| **C6** (mémoire technique type dans le MVP) | question d'Anthony, non tranchée : le modèle **stocke** la famille F9 sans rien décider de son inclusion ; point ouvert § 15 |
| **C7** (source de traçabilité non consultable dans le dépôt) | traité par le lot L4 (`docs/SPEC-MVP-V2.md`) : il porte sur la rédaction d'un autre document |
| **C8** (références au monde réel) | cosmétique, décision d'assumer : rien à changer au modèle |

### Un constat que je ne réfute pas

Je n'ai trouvé **aucun** des six constats qui me sont confiés infondé. Les six sont
confirmés par les lignes citées, et les six sont traités ci-dessus. En particulier,
**C1, C2 et C3 sont confirmés sans réserve** : les deux premiers sont des
contradictions internes démontrables entre le modèle v1 et l'interface, et le
troisième est l'absence pure et simple d'un mécanisme que la ligne rouge exige.

---

## 13. Points dépendant de l'option de confidentialité retenue

> **Ce document ne tranche aucune option** (décision D-C6) et **n'énonce aucune garantie
> de confidentialité** (décision D-C2). Les trois variantes sont décrites ci-dessous
> pour que le modèle puisse être **ajusté** une fois l'option choisie, et rien de plus.
> **La référence est `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`, à compléter après
> validation de ce document** et la décision d'Anthony. Si les noms des options
> diffèrent entre les deux documents, **c'est `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`
> qui fait foi** pour leur intitulé ; les descriptions ci-dessous reprennent les trois
> familles posées par D6.

Les trois variantes de D6 (reprises dans l'ordre de D6) :

| Repère | Variante (D6) | Ce qu'elle implique pour le modèle |
|---|---|---|
| **A** | chiffrement côté client + traitement local ; le serveur ne voit jamais les documents en clair | le service cesse d'être le lieu du traitement : la bibliothèque décrite ici peut rester **locale au poste du client**, aucun contenu n'est écrit côté serveur |
| **B** | chiffrement au repos + isolation stricte côté serveur ; le serveur détient la clé | l'isolation par `client_id` (§ 4) devient la base, le chiffrement s'ajoute **par-dessus**, et l'accès théorique de l'exploitant subsiste |
| **C** | clés détenues par le client, déverrouillage à la demande ; clé de session non stockée par le serveur | compromis : le traitement serveur redevient possible pendant la session, avec une clé qui ne doit jamais toucher le disque |

### 13.1 Chiffrement au repos — quels champs, quelles tables

Réponse **par variante**, à partir de la liste des champs déclarés sensibles (§ 13.2) :

| Variante | Tables concernées | Champs concernés | Remarque de structure |
|---|---|---|---|
| **A** | en pratique **aucune** table serveur de contenu : les données de bibliothèque restent chez le client | — | le modèle de ce document décrit le **modèle logique** ; en option A, une partie des tables vit dans un magasin local. Le modèle ne change pas, le **lieu d'exécution** change. `document.stockage_client_seulement = vrai` prend tout son sens (§ 9.1) |
| **B** | toutes les entités de contenu portant des champs `confidentiel` : `entreprise_version` (iban, bic, siret, pièces), `exercice_comptable`, `attestation`, `assurance`, `cv`, `representant_legal`, `reference_chantier.contact_reference`, `document` (fichiers), `tracabilite_valeur` (par ricochet, si elle cite un emplacement dans un document sensible) | liste exhaustive § 13.2 | chiffrement **par client** et non global, sinon le cloisonnement est décoratif : deux clients ne doivent pas partager un même domaine de clés |
| **C** | mêmes tables qu'en B **pendant la session de traitement** | mêmes champs | s'ajoute un marqueur de traitement : il faut pouvoir dire **quels traitements** ont eu lieu avec une clé de session (§ 13.3) |

**Ce que le modèle doit pouvoir changer** — et qu'il ne porte pas aujourd'hui, faute
d'option tranchée :

- un **registre des champs chiffrés** (table ou fichier de configuration) : c'est
  l'usage d'un jeu de référence ou d'une table de paramètres, pas un changement de
  schéma des familles ;
- un **identifiant de domaine de clé par client** (`client.id` peut servir de
  référence, mais le modèle ne stocke **aucune** clé) ;
- pour l'option A, la possibilité qu'un `document` n'ait **aucune copie serveur**
  (champ déjà prévu, § 9.1) et qu'une valeur soit tracée vers un document non détenu
  par le service : `source_emplacement` reste renseigné, `document.chemin_stockage`
  décrit un emplacement local. **Point à vérifier** avec l'option retenue.

### 13.2 Registre des champs déclarés sensibles (`confidentiel`)

C'est l'entrée du chiffrement : c'est cette liste, et pas une autre, qui dit quoi
protéger. Elle est **exhaustive à ce jour** et devra être tenue à jour avec le modèle.

| Entité | Champs | Nature de la donnée |
|---|---|---|
| `entreprise_version` | `iban`, `bic`, `piece_rib` | coordonnées bancaires |
| `entreprise_version` | `siret_siege`, `numero_tva_intracommunautaire` | identification de l'entreprise |
| `representant_legal` | `nom`, `prenom`, `date_nomination`, `piece` | données personnelles |
| `exercice_comptable` | tous les `montant`, `piece` | comptes annuels |
| `attestation` | `piece`, `montant_engage` | pièces fiscales et sociales |
| `reference_chantier` | `contact_reference`, `montant` | données personnelles, affaires |
| `cv` | `nom`, `prenom`, `cv_piece`, `diplomes` | données personnelles |
| `document` | le fichier lui-même quand `sensibilite = confidentiel` | pièces justificatives |
| `client`, `abonnement`, `evenement_facturation` | identité du client, contrat | relation commerciale |

*Le contenu exact à protéger dépend de l'option ; cette liste est l'entrée, pas la
décision. Les durées de conservation, elles, relèvent du juriste (§ 15).*

### 13.3 Données en clair pendant le traitement — et journalisation

| Question | Variante A | Variante B | Variante C |
|---|---|---|---|
| Les documents sont-ils en clair côté serveur pendant l'analyse ? | **non** — le traitement se fait chez le client | **oui** pendant le traitement serveur, et le personnel technique a un accès théorique | **oui pendant la session seulement** ; la clé de session n'est pas stockée |
| Où passe la frontière de confiance ? | chez le client | chez l'hébergeur | chez le client pour la clé, chez l'hébergeur pour le calcul |
| Journalisation / piste d'audit à prévoir | journal **local** chez le client : qui a lu quoi, quand | journal **serveur** par client : accès aux documents, déverrouillages, exports, tentatives hors cloisonnement | journal serveur **sans contenu** : identifiant de session, client, périmètre traité, jamais la clé ni le document |
| Ce que le modèle peut porter | `tracabilite_valeur.source_date_extraction` et `date_modification` donnent déjà qui/quand au niveau valeur | idem + table de journal **hors** structure de contenu (à spécifier avec l'option) | idem + marqueur de traitement par clé de session |

**Point de méthode.** La journalisation n'est pas un champ des familles : c'est une
préoccupation transversale. Le modèle **facilite** la piste d'audit (horodatages,
`relecteur_nom`, traçabilité par valeur) mais **ne remplace pas** un journal
d'exploitation. À traiter dans `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.

### 13.4 Conservation et sort des données à la résiliation

Aucune durée n'est fixée ici : **aucune durée légale ne doit être inventée**
(`docs/DATA-MODEL.md` § 16 point 6). Ce que le modèle doit prévoir, et prévoit :

- `client.date_resiliation` et `client.statut = resilie` existent (§ 5.1) : la
  résiliation est **représentable** ;
- l'archivage (`statut_enregistrement = archive`, `fiche_version.archivee`) conserve
  la trace sans supprimer : une suppression en dur casserait la traçabilité des
  dossiers passés ;
- le **sort** (anonymisation ? suppression ? export ?) dépend de la durée de
  conservation retenue, donc du juriste, et de l'option : en A et C, la clé peut être
  détruite pour rendre les données inexploitables ; en B, la destruction passe par
  l'exploitant.

**Renvoi.** Ces quatre points (13.1 à 13.4) sont à **confirmer ou corriger** après
lecture de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` — et ce document ne prétend pas
répondre à leur place.

---

## 14. Portabilité du modèle (décision D-C5)

**Le modèle ne présuppose aucun moteur.** Il doit rester valable sur SQLite comme sur
un SGBD hébergé (décision D-C5, motif : D5 n'est pas tranché et `docs/STACK-PROPOSAL.md`
avance en parallèle).

| Règle | Pourquoi |
|---|---|
| Toute indication de type dans ce document est **indicative** | les types logiques (§ 3.1) se traduisent différemment selon le moteur ; ce document ne fige aucune correspondance |
| Identifiants **opaques** (UUID, jamais de séquence métier) | une séquence auto-incrémentée n'est pas portable entre moteurs, et n'a aucune valeur métier |
| Dates en **ISO 8601**, en texte ou en type date selon le moteur | format stable et comparable, sans dépendance à une fonction de formatage propriétaire |
| Booléens représentables en **0/1** | évite de dépendre d'un type booléen natif absent chez certains moteurs |
| **Aucune** fonctionnalité propriétaire présumée (type JSON natif, recherche plein texte, séquence, déclencheur, contrainte d'exclusion) | le modèle doit rester lisible et implémentable partout |
| Contraintes inter-lignes ou inter-tables (I1 à I6, `parent_code` de même namespace, unicité du rattachement de comptage § 11.4) exprimées comme **règles applicatives documentées**, pas comme objets de schéma | SQLite ne les exprime pas toutes ; les décrire comme exigences garantit qu'elles survivent au changement de moteur |
| Le champ `client_id` reste la base du cloisonnement quel que soit le moteur | une **base ou un schéma par client** est une option d'exploitation (§ 4.3) ; elle ne change **aucune** structure |
| Références polymorphes assumées (`tracabilite_valeur`) : intégrité applicative | § 7.6 et C2 : aucune clé étrangère portable ne peut couvrir `(entite, enregistrement_id)` ; on le dit au lieu de le promettre |

**Ce que ce paragraphe ne fait pas :** il ne recommande ni SQLite ni un SGBD hébergé.
C'est le rôle de `docs/STACK-PROPOSAL.md` (lot L1). Le modèle est conçu pour que ce
choix n'ait pas à être connu de lui.

---

## 15. Points ouverts

Reprise des points ouverts de la v1 (§ 16) qui tiennent encore, plus les nouveaux.
Colonne « qui tranche » : aucune de ces lignes n'est de mon ressort.

| # | Point | Qui tranche | Impact sur le modèle |
|---|---|---|---|
| 1 | **Stack technique** | Anthony (D5) — proposition en cours : `docs/STACK-PROPOSAL.md` | aucun sur la structure (§ 14) ; conditionne l'exploitation |
| 2 | **Option de confidentialité (A, B ou C)** | Anthony, sur recommandation de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` | § 13.1 à 13.4 : chiffrement, lieu des clés, journalisation, conservation |
| 3 | **Seuil d'alerte d'échéance** | Anthony | valeur de `echeance_proche` (§ 3.3). Aucun seuil n'est inventé ici |
| 4 | **Contenu des listes fermées** (formes juridiques, types de documents, catégories, types d'assurance…) | Anthony + lot L5, **à la source** quand elle existe | **contenu** des jeux de référence (§ 8.6) ; la structure est déjà là |
| 5 | **Durées de validité des attestations** | source juridique / document | jamais codées en dur ; lues sur le document (§ 10 F2) |
| 6 | **RGPD** : CV, coordonnées bancaires, base légale, information des personnes, durée de conservation | **juriste** | § 10 F6, § 5.4, § 13.4 |
| 7 | **Portage juridique / conflit d'intérêts** | juriste (`PROJECT.md` § 6) | hors modèle, mais conditionne la commercialisation (D4) |
| **8** | **Formats de DCE et de pièces acceptés** (constat C5) | Anthony / lot d'implémentation | champ `document.mime_type` (§ 9.2) ; liste de formats à fixer |
| **9** | **Format d'export de la liste des manques** (constat C5) | Anthony / lot d'implémentation | l'écran E6 est une **vue calculée** : aucune table à changer, mais un format à décider |
| **10** | **Inclusion de la famille « mémoire technique type » dans le MVP** (constat C6) | Anthony | la famille F9 est modélisée et stockable ; son **périmètre d'usage** est la question |
| **11** | **Intégrité des références polymorphes** de `tracabilite_valeur` (constat C2, limite assumée) | décision de mise en œuvre | contrôle applicatif (invariant I4) ; un moteur supportant une contrainte composite pourrait l'exprimer, mais la portabilité l'interdit de présumer |
| **12** | **Algorithme et sérialisation canonique de l'empreinte de validation** | décision de mise en œuvre, avec le lot sécurité | champs `empreinte_contenu` et `empreinte_algorithme` (§ 6.4) ; **aucun algorithme n'est imposé ici** |
| **13** | **Portée `client` des jeux de référence** (vocabulaire propre à un client) | Anthony | aujourd'hui tous les jeux sont `global` (§ 8.4) ; ouvrir la portée `client` est une évolution de structure, donc une décision |
| **14** | **Nombre d'entreprises par client et rattachement d'un utilisateur à plusieurs clients** | Anthony | le modèle le permet (1..n) ; la règle d'usage et d'isolation doit être écrite |
| **15** | **Authentification multi-utilisateurs et identification du relecteur** | Anthony (`UI-SAISIE.md` § 13 point 2) | `relecteur_nom` est obligatoire dès aujourd'hui ; `relecteur_utilisateur_id` deviendra utilisable quand les comptes existeront (§ 5.2, § 6.4) |
| **16** | **Niveaux d'exigence N1/N2/N3 par champ** | Anthony + lots L4 et L5 | restent **propres à l'interface** (§ 3.3) ; ils conditionnent `completude_famille` et l'état `socle_complet`, donc l'écran E0 |
| **17** | **Règle d'articulation abonnement / paiement à l'acte** | Anthony (D3) | § 11.5 ; le modèle porte les deux, la règle de gestion reste à écrire |
| **18** | **Sort des données à la résiliation** (voir § 13.4) | juriste | `client.date_resiliation` existe ; le traitement reste à définir |
| **19** | **Durée de conservation** | juriste | aucune durée n'est écrite dans le modèle |

---

## 16. Rappels de sécurité et de dépôt

- **Aucune donnée réelle d'entreprise** dans le dépôt : ni SIRET, ni IBAN, ni bilan,
  ni CV réel. Les exemples cités dans ce document (nom d'entreprise, libellé de pièce)
  sont **fictifs et signalés comme tels** quand ils apparaissent.
- **Aucun secret dans le modèle** : aucune clé, aucun mot de passe, aucun jeton, aucun
  identifiant de prestataire. Ce document décrit des **emplacements**, jamais des
  valeurs.
- **Aucun fichier client versionné** : `data/` est ignoré par git (`.gitignore`) ; les
  pièces vivent hors dépôt, référencées par `document.chemin_stockage`, préfixé par le
  client (§ 4.3).
- **Confidentialité** : ce document **n'énonce aucune garantie**. Toute formulation de
  garantie appartient à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`, à compléter après
  validation de ce document. Ce qui est **vrai par construction** ici est limité au
  cloisonnement représentable et contrôlable (§ 4, invariants § 3.4) ; cela **ne
  constitue pas** un engagement d'isolation cryptographique.
- **Ligne rouge** (§ 2, § 7.5, § 6.4) : l'IA ne signe rien, n'invente aucune valeur,
  ne fixe aucun prix, ne garantit aucune conformité ; aucune valeur sans origine ;
  aucune validation sans action humaine nommée et horodatée.
- **Aucun entraînement de modèle sur les données client** (D6) : le modèle ne décrit
  ni export ni jeu d'entraînement ; la règle est reproduite ici comme contrainte, sa
  mise en œuvre relève de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.

---

*Fin du modèle v2. Lot L3 — `dev-back`. Conception sur le papier : aucun schéma
appliqué, aucune migration écrite, aucun code produit. Toute évolution ultérieure de
structure passe par une migration versionnée et réversible, jamais par une
modification en place d'un schéma appliqué — et toute évolution de contenu de
référence se fait par ajout de lignes, sans migration destructive (§ 8.5).*
