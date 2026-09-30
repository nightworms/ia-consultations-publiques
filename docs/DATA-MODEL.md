# DATA-MODEL — Modèle de données de la bibliothèque d'entreprise

*Lot L2. Écrit le 30 septembre 2026. Board : `ia-consultations`.
Périmètre : phase 1 — cadrage. Ce document décrit **comment** l'information est
structurée ; il ne dit pas **quoi** collecter pour un métier donné (c'est le rôle de
`docs/DONNEES-METIER-BATIMENT.md`, lot L5). En cas de divergence de structure,
**ce document fait foi**.*

> **Statut du document.** Modèle proposé, non définitif. Aucune base n'est créée,
> aucun schéma n'est appliqué, aucune dépendance n'est installée. Les points marqués
> « à valider » ou « à vérifier » restent ouverts et doivent être tranchés par Anthony
> ou par un juriste avant toute implémentation.

---

## 0. Proposition de stack technique — *proposition à valider par Anthony*

Anthony n'a pas tranché la stack (voir `docs/PLAN.md` § 5, question 5). Pour que le
squelette existe malgré tout, une proposition simple et **réversible** est retenue.
Elle est explicitement une proposition, pas une décision.

| Brique | Proposition | Pourquoi | Coût de sortie si rejetée |
|---|---|---|---|
| Langage | **Python 3.12** | Écosystème mûr pour lire des PDF (DCE) et appeler un LLM ; le squelette n'utilise que la bibliothèque standard | Faible : le squelette est isolé sous `src/` |
| Persistance | **SQLite** (fichier unique) | Zéro serveur, zéro coût, fichier unique sauvegardable et chiffrable, adapté à une PME mono-utilisateur au MVP | Faible : le schéma est décrit ici, indépendant du moteur |
| API | **FastAPI** (phase 2) | HTTP léger, typé, documentation automatique, écosystème Python | Moyen : concernerait la couche `api/` |
| Migrations | **Fichiers SQL numérotés** (`src/migrations/000N_*.sql`) | Versionnées, réversibles (`_up` / `_down`), lisibles sans outil | Faible |

**Alternatives écartées explicitement** (elles pourront être reconsidérées) :

- Node / TypeScript : viable, mais moins direct pour l'extraction PDF et l'appel LLM.
- PostgreSQL / serveur de base : surdimensionné au MVP, introduit une infra à héberger.
- ORM lourd (SQLAlchemy/Django) : dette prématurée pour un schéma encore mouvant.

**Contrainte de phase 1 respectée** : le squelette `src/` n'importe **rien** hors de la
bibliothèque standard Python. FastAPI et SQLite sont mentionnés comme cible, pas
installés. Rien n'est exécutable comme une application complète.

**Décision ouverte liée** : l'hébergement et la localisation des données de la
bibliothèque (bilans, CV, coordonnées bancaires) ne sont pas tranchés
(`docs/PLAN.md` § 5, question 6). Le modèle est conçu pour fonctionner avec SQLite
local **ou** un SGBD hébergé, sans changement de schéma.

---

## 1. Principes de conception

1. **Traçabilité intégrale.** Chaque information de la bibliothèque porte le lien vers
   le document source dont elle provient, ou son origine déclarée. Aucun chiffre,
   aucune référence, aucun certificat n'existe sans une source identifiable.
   C'est la traduction technique de la ligne rouge de `PROJECT.md` § 5.
2. **L'IA n'écrit pas de valeur métier.** Le modèle distingue l'origine d'une valeur :
   *extraite d'un document* ou *saisie par l'entreprise*. Il n'existe pas de valeur
   « générée par l'IA » sans source.
3. **Versionnement.** La fiche entreprise est versionnée ; une version publiée est
   immuable (voir § 5).
4. **Dates surveillées.** Tout élément à échéance (assurance, certification,
   attestation) porte une date de fin et un statut calculable (valide / à échéance
   proche / expiré).
5. **Confidentialité par conception.** Les données sensibles (coordonnées bancaires,
   CV, bilans) sont identifiées comme telles dans le modèle, pour permettre
   chiffrement au repos et cloisonnement par entreprise (`PROJECT.md` § 6).
6. **Séparation des responsabilités.** Les entités vivent dans `src/app/domain/`, la
   persistance dans `src/app/storage/`, la logique dans `src/app/services/` — aucune
   autre couche n'accède directement aux données.

---

## 2. Conventions du modèle

### 2.1 Vocabulaire de types

| Type logique | Description | Traduction SQL cible (indicative) |
|---|---|---|
| `identifiant` | Clé technique opaque | `TEXT` — UUID v4 (jamais un numéro métier) |
| `texte_court` | Chaîne ≤ 255 caractères | `TEXT` |
| `texte_long` | Texte libre sans limite pratique | `TEXT` |
| `entier` | Nombre entier | `INTEGER` |
| `decimal` | Nombre décimal | `REAL` / `NUMERIC` |
| `montant` | Montant + devise obligatoire | `montant NUMERIC` + `devise TEXT(3)` (code ISO 4217) |
| `date` | Date seule, format `AAAA-MM-JJ` | `TEXT` (ISO 8601) |
| `booleen` | Vrai / faux | `INTEGER` 0-1 |
| `enumeration` | Liste fermée de valeurs (voir ci-dessous) | `TEXT` + contrainte de domaine |
| `reference` | Clé étrangère `table.champ` | `TEXT` + clé étrangère |
| `piece` | Référence vers un document joint (`document.id`) | `TEXT` + clé étrangère |
| `liste` | Référence multiple vers une autre entité | table de liaison |

### 2.2 Énumérations communes

- `origine_valeur` : `document_extrait` | `saisie_entreprise`
  *(aucune valeur `genere_ia` : l'IA ne produit pas de valeur métier).*
- `etat_verification` : `verifie` | `declare_non_verifie` | `a_verifier`
- `statut_validite` : `valide` | `echeance_proche` | `expire` | `non_renseigne`
- `sensibilite` : `publique` | `interne` | `confidentiel`
  (`confidentiel` impose chiffrement au repos et cloisonnement par entreprise)

> La règle de calcul qui fait passer `valide` → `echeance_proche` (combien de jours
> avant l'échéance ?) **n'est pas fixée ici** : c'est un seuil, et aucun seuil ne doit
> être inventé. Voir § 10 « Points ouverts ».

### 2.3 Colonnes techniques communes

Toute entité de contenu porte ces colonnes, non répétées dans les tableaux ci-dessous :

| Colonne | Type | Obligatoire | Rôle |
|---|---|---|---|
| `id` | identifiant | oui | identifiant technique |
| `entreprise_id` | reference `entreprise.id` | oui | cloisonnement par entreprise |
| `fiche_version_id` | reference `fiche_version.id` | oui | rattachement à la version de fiche (§ 5) |
| `date_creation` | date | oui | horodatage |
| `date_modification` | date | oui | horodatage |
| `origine` | enumeration `origine_valeur` | oui | d'où vient la valeur (§ 4) |
| `confiance` | enumeration `etat_verification` | oui | niveau de vérification |

---

## 3. Entités transverses

### 3.1 `entreprise`

L'entreprise propriétaire de la bibliothèque. Une ligne par entreprise.

| Champ | Type | Oblig. | Description / source |
|---|---|---|---|
| `id` | identifiant | oui | — |
| `raison_sociale` | texte_court | oui | KBIS / avis SIRENE |
| `siren` | texte_court (9 chiffres) | oui | avis SIRENE (INSEE) |
| `siret_siege` | texte_court (14 chiffres) | oui | avis SIRENE — **donnée d'identification, sensible** |
| `forme_juridique` | enumeration | oui | KBIS / statuts. *Liste indicative — SAS, SARL, SA, EURL, EI, SCOP, autre ; à compléter à la source, ne pas figer de liste inventée* |
| `capital_social` | montant | non | statuts |
| `date_creation_entreprise` | date | non | KBIS |
| `code_ape_naf` | texte_court | non | avis SIRENE (INSEE) |
| `numero_tva_intracommunautaire` | texte_court | non | avis SIRENE |
| `adresse_siege` | texte_long | oui | KBIS — rue, complément, code postal, commune, pays |
| `adresse_etablissement_principal` | texte_long | non | justificatif |
| `telephone` | texte_court | non | déclaratif |
| `email` | texte_court | non | déclaratif |
| `site_web` | texte_court | non | déclaratif |
| `sensibilite` | enumeration | oui | `interne` par défaut |

*Sous-entité `representant_legal` (1..n, mais un seul « représentant légal en
exercice » à un instant donné) :* `nom`, `prenom`, `fonction`, `date_nomination`,
`piece` (justificatif), tous typés. Source : KBIS / statuts / PV de nomination.

### 3.2 `document` — le document source

C'est la brique de traçabilité : **tout** élément de contenu pointe, directement ou
indirectement, vers un document de cette table.

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `id` | identifiant | oui | — |
| `entreprise_id` | reference | oui | cloisonnement |
| `type_document` | enumeration | oui | `kbis` \| `avis_sirene` \| `bilan` \| `liasse_fiscale` \| `attestation_fiscale` \| `attestation_sociale` \| `attestation_assurance` \| `certificat` \| `fiche_technique` \| `avis_technique` \| `cv` \| `attestation_bonne_execution` \| `photo` \| `autre` — *liste indicative, à compléter* |
| `libelle` | texte_court | oui | nom lisible, ex. « Attestation décennale 2026 » |
| `emetteur` | texte_court | non | qui a émis le document |
| `date_emission` | date | non | date portée par le document |
| `date_validite_debut` | date | non | le cas échéant |
| `date_validite_fin` | date | non | **échéance à surveiller** |
| `reference_document` | texte_court | non | numéro du document (contrat, attestation) |
| `chemin_stockage` | texte_court | oui | emplacement du fichier (hors dépôt : `data/` non versionné) |
| `empreinte_sha256` | texte_court | non | intégrité du fichier |
| `sensibilite` | enumeration | oui | `confidentiel` pour CV, bilan, IBAN |

### 3.3 `fiche_version` — versionnement de la fiche entreprise

Voir § 5 (versionnement explicite).

---

## 4. Traçabilité : le motif commun à toutes les familles

Chaque enregistrement de contenu (§ 6 à § 14) porte en plus des colonnes techniques :

| Colonne | Type | Oblig. | Rôle |
|---|---|---|---|
| `source_document_id` | reference `document.id` | conditionnel | obligatoire dès lors que l'information est extraite d'un document |
| `source_emplacement` | texte_court | non | localisation précise dans la source (page, section, ligne) |
| `source_date_extraction` | date | non | quand l'information a été extraite |
| `source_commentaire` | texte_long | non | précision libre, ex. « montant garanti hors franchise » |

**Règle de traçabilité :**

- Si `origine = document_extrait` → `source_document_id` **doit** être renseigné.
- Si `origine = saisie_entreprise` → l'absence de document est admise, mais
  `confiance` vaut au mieux `declare_non_verifie`. Le produit doit pouvoir afficher
  « déclaré par l'entreprise, non vérifié ».
- Une valeur `confiance = verifie` n'est possible que si une source existe et a été
  contrôlée.

C'est le point qui rend la ligne rouge *techniquement* opposable : aucune valeur ne
peut être exposée sans indiquer sa provenance et son niveau de vérification.

---

## 5. Versionnement de la fiche entreprise (traité explicitement)

**Unité versionnée :** la *fiche entreprise* = l'ensemble des enregistrements de
contenu rattachés à une entreprise à un instant donné.

Table `fiche_version` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `id` | identifiant | oui | — |
| `entreprise_id` | reference | oui | — |
| `numero_version` | entier | oui | 1, 2, 3… croissant par entreprise |
| `statut` | enumeration | oui | `brouillon` \| `publiee` \| `archivee` |
| `version_parente_id` | reference `fiche_version.id` | non | version dont celle-ci dérive |
| `date_creation` | date | oui | — |
| `date_publication` | date | non | renseignée au passage en `publiee` |
| `commentaire` | texte_long | non | motif de la version |

**Règles :**

1. Une version `publiee` est **immuable**. Toute correction crée une **nouvelle**
   version (numéro + 1, `version_parente_id` = version précédente). L'historique est
   conservé, jamais écrasé.
2. Un enregistrement de contenu modifié crée une nouvelle ligne rattachée à la
   nouvelle `fiche_version_id` ; l'ancienne ligne reste rattachée à la version
   archivée. On ne fait pas de mise à jour « en place » sur une version publiée.
3. Une version `archivee` reste lisible : elle sert de preuve de ce qui a été fourni
   pour une consultation passée (utile en cas de litige ou de contrôle).
4. Chaque entité de contenu référence **une et une seule** `fiche_version_id` :
   c'est le point qui relie versionnement et traçabilité (§ 4). On peut donc répondre
   à la question « quelle fiche exactement a servi à ce dossier ? ».

---

## 6. Famille 1 — Identité

Couvre `PROJECT.md` § 3 « Identité ».

- Entité principale : **`entreprise`** (§ 3.1).
- Sous-entité : **`representant_legal`** (§ 3.1).
- Champs sensibles : `siret_siege` (identification), adresse (données d'entreprise).

Traçabilité : chaque champ d'identité pointe vers sa source (`kbis`, `avis_sirene`,
`statuts`). Un champ non justifié est marqué `declare_non_verifie`.

Échéances : aucune échéance propre à cette famille (l'identité ne « périme » pas),
hormis la fraîcheur souhaitable de l'extrait SIRENE — **seuil à définir, non fixé ici**.

---

## 7. Famille 2 — Capacités financières

Couvre `PROJECT.md` § 3 « Capacités financières ».

### 7.1 `exercice_comptable` (1 par année, ≥ 3 dernières)

| Champ | Type | Oblig. | Description / source |
|---|---|---|---|
| `annee_exercice` | entier | oui | bilan / liasse fiscale |
| `chiffre_affaires` | montant | oui | liasse fiscale |
| `resultat_net` | montant | non | bilan |
| `capitaux_propres` | montant | non | bilan |
| `total_bilan` | montant | non | bilan |
| `effectif_moyen` | entier | non | DADS / déclaration |
| `date_cloture` | date | non | bilan |
| `sensibilite` | enumeration | oui | `confidentiel` |
| + traçabilité (§ 4) | | | `source_document_id` → type `bilan` / `liasse_fiscale` |

### 7.2 `attestation`

Regroupe les pièces justificatives à durée de validité.

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `type_attestation` | enumeration | oui | `regularite_fiscale` \| `vigilance_urssaf` \| `capacite_financiere` \| `autre` — *liste indicative* |
| `emetteur` | texte_court | oui | organisme émetteur |
| `date_emission` | date | oui | — |
| `date_validite_fin` | date | non | **échéance à surveiller** |
| `montant_engage` | montant | non | ex. capacité financière |
| `piece` | piece | oui | → `document` |
| + traçabilité (§ 4) | | | |

> **À vérifier.** La durée de validité d'une attestation dépend de l'émetteur et de la
> nature de la pièce ; elle n'est **pas codée en dur** dans le modèle — elle est lue
> sur le document, et à défaut laissée `non_renseigne`. Aucun seuil n'est inventé.

### 7.3 `capacite_production`

`description` (texte_long), `unite` (texte_court), `valeur` (decimal), `source`.

Échéances à surveiller : `attestation.date_validite_fin` (fiscale, URSSAF).

---

## 8. Famille 3 — Assurances

Couvre `PROJECT.md` § 3 « Assurances ».

Entité `assurance` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `type_assurance` | enumeration | oui | `decennale` \| `rc_professionnelle` \| `rc_exploitation` \| `tous_risques_chantier` \| `autre` — *liste indicative* |
| `assureur` | texte_court | oui | attestation |
| `numero_contrat` | texte_court | non | attestation |
| `montant_garantie` | montant | non | attestation |
| `franchise` | montant | non | attestation |
| `date_debut` | date | oui | attestation |
| `date_echeance` | date | oui | **échéance à surveiller (critique)** |
| `activites_couvertes` | texte_long | non | étendue et nature des travaux garantis |
| `piece` | piece | oui | → `document` de type `attestation_assurance` |
| + traçabilité (§ 4) | | | |

Échéance à surveiller : **`date_echeance`** → statut `statut_validite` recalculé
(valide / échéance proche / expiré).

> **À vérifier.** Le contenu exact d'une attestation décennale et les mentions
> obligatoires relèvent du lot L4 (`CONFORMITE-COMMANDE-PUBLIQUE.md`) et du lot L5.
> Le présent modèle se contente de les **stocker et tracer**, sans fixer aucune règle
> de fond.

---

## 9. Famille 4 — Certifications et qualifications

Couvre `PROJECT.md` § 3 « Certifications et qualifications ».

Entité `certification` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `intitule` | texte_court | oui | libellé **repris du certificat**, jamais reconstitué |
| `organisme` | texte_court | oui | organisme émetteur (repris du certificat) |
| `numero_certificat` | texte_court | non | numéro porté par le document |
| `domaine_metier` | texte_court | non | domaine couvert |
| `date_obtention` | date | non | — |
| `date_echeance` | date | non | **échéance à surveiller** |
| `piece` | piece | oui | → `document` de type `certificat` |
| + traçabilité (§ 4) | | | |

> **Ligne rouge appliquée.** Les intitulés et numéros de certification sont **lus sur
> le document** ; le modèle n'en présume aucun. Aucun référentiel de certification
> n'est décrit ici — cela relève du lot L5 (contenu métier).

---

## 10. Famille 5 — Références de chantiers

Couvre `PROJECT.md` § 3 et § 4 (« le poste le plus rentable » : nourrit le mémoire
technique).

Entité `reference_chantier` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `intitule_operation` | texte_court | oui | — |
| `maitre_ouvrage` | texte_court | oui | nom du maître d'ouvrage |
| `nature_travaux` | texte_long | oui | nature des travaux réalisés |
| `lieu_commune` | texte_court | non | — |
| `lieu_departement` | texte_court | non | — |
| `date_debut` | date | non | — |
| `date_fin` | date | non | — |
| `montant` | montant | non | montant des travaux |
| `duree_mois` | entier | non | — |
| `surface_traitee` | decimal | non | avec `unite` |
| `description` | texte_long | non | descriptif détaillé |
| `competences_appliquees` | texte_long | non | pour le rapprochement avec un DCE |
| `attestation_bonne_execution` | piece | non | → `document` |
| `photos` | liste de `piece` | non | → `document` de type `photo` |
| `contact_reference` | texte_court | non | **donnée personnelle** — `confidentiel` |
| `sensibilite` | enumeration | oui | — |
| + traçabilité (§ 4) | | | |

Lien avec le mémoire technique : les références sont sélectionnables par chapitre
(§ 14). Le rapprochement automatique référence ↔ DCE est **hors phase 1**.

---

## 11. Famille 6 — Moyens humains

Couvre `PROJECT.md` § 3 « Moyens humains ».

### 11.1 `effectif_metier`

`metier` (texte_court), `nombre` (entier), `commentaire` (texte_long), source.

### 11.2 `organigramme`

`piece` (→ `document`), `description` (texte_long), `date_maj` (date).

### 11.3 `cv`

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `nom` | texte_court | oui | **donnée personnelle** |
| `prenom` | texte_court | oui | **donnée personnelle** |
| `fonction` | texte_court | oui | — |
| `diplomes` | texte_long | non | — |
| `annees_experience` | entier | non | — |
| `cv_piece` | piece | oui | → `document` de type `cv` |
| `sensibilite` | enumeration | oui | `confidentiel` |
| + traçabilité (§ 4) | | | |

> **RGPD — à cadrer hors modèle.** Les CV sont des données personnelles : base légale,
> information des personnes, durée de conservation et cloisonnement ne sont **pas**
> tranchés ici. Ils doivent l'être avant toute mise en œuvre (voir § 15).

---

## 12. Famille 7 — Moyens matériels

Couvre `PROJECT.md` § 3 « Moyens matériels ».

Entité `moyen_materiel` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `categorie` | enumeration | oui | `engins` \| `echafaudages` \| `outillage_specifique` \| `vehicules` \| `autre` — *liste indicative* |
| `designation` | texte_court | oui | — |
| `quantite` | entier | oui | — |
| `marque_modele` | texte_court | non | — |
| `annee` | entier | non | — |
| `propriete` | enumeration | non | `propre` \| `location` |
| `disponibilite` | texte_court | non | — |
| `justificatif` | piece | non | → `document` (fiche, facture, contrat de location) |
| + traçabilité (§ 4) | | | |

---

## 13. Famille 8 — Fiches techniques produits

Couvre `PROJECT.md` § 3 « Fiches techniques produits ».

Entité `produit` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `fournisseur` | texte_court | oui | — |
| `reference_produit` | texte_court | oui | référence **exacte du fournisseur**, jamais reconstituée |
| `designation` | texte_court | oui | — |
| `famille` | enumeration | non | `etancheite` \| `isolation` \| `autre` — *à compléter par L5* |
| `domaine_application` | texte_long | non | — |
| `fiche_technique` | piece | non | → `document` |
| `certificats` | liste de `piece` | non | → `document` |
| `avis_technique` | piece | non | → `document` (avis technique / DTA) |
| `date_validite_document` | date | non | **échéance à surveiller** |
| + traçabilité (§ 4) | | | |

> **Ligne rouge.** Un avis technique ou un certificat est stocké **tel quel** ; le
> modèle ne présume ni sa validité ni sa portée. La référence produit est recopiée du
> document fournisseur.

---

## 14. Famille 9 — Mémoire technique type

Couvre `PROJECT.md` § 3 « Mémoire technique type ».

Entité `chapitre_memoire` :

| Champ | Type | Oblig. | Description |
|---|---|---|---|
| `titre` | texte_court | oui | — |
| `ordre` | entier | oui | ordre d'affichage |
| `contenu_texte` | texte_long | oui | texte rédigé, réutilisable |
| `statut` | enumeration | oui | `brouillon` \| `accepte` \| `archive` |
| `date_redaction` | date | non | — |
| `references_liees` | liste de `reference` | non | → `reference_chantier.id` utilisées comme appui |
| `documents_associes` | liste de `piece` | non | → `document` |
| + traçabilité (§ 4) | | | |

> **Périmètre strict.** Ce modèle **stocke** un mémoire technique type réutilisable ;
> il ne décrit **pas** la rédaction automatique d'un mémoire (hors périmètre phase 1,
> cf. brief racine). Un chapitre réutilisé dans un dossier doit rester traçable jusqu'à
> sa source et exiger la relecture humaine — la signature n'est jamais automatisée.

---

## 15. Vue transverse — dates et échéances à surveiller

Synthèse de tous les champs porteurs d'une échéance exploitable par une future alerte :

| Famille | Champ | Nature |
|---|---|---|
| Identité | `document.date_validite_fin` (extrait SIRENE) | fraîcheur — *seuil non fixé* |
| Capacités financières | `attestation.date_validite_fin` | échéance (fiscale, URSSAF) |
| Assurances | `assurance.date_echeance` | échéance **critique** |
| Certifications | `certification.date_echeance` | échéance |
| Moyens humains | `organigramme.date_maj` | fraîcheur |
| Fiches produits | `produit.date_validite_document` | échéance |
| Toutes | `document.date_validite_fin` | échéance générique |

> **Aucun seuil d'alerte n'est fixé dans ce document.** La question « à combien de
> jours avant échéance déclenche-t-on `echeance_proche` ? » est une décision d'Anthony
> (voir § 16, point ouvert). Le modèle se contente de **rendre le calcul possible**.

---

## 16. Points ouverts (à trancher, pas à deviner ici)

| # | Point | Qui tranche | Impact sur le modèle |
|---|---|---|---|
| 1 | **Stack technique** | Anthony (`PLAN.md` § 5 q5) | § 0 — aujourd'hui : proposition Python/SQLite/FastAPI |
| 2 | **Hébergement / localisation des données** | Anthony (`PLAN.md` § 5 q6) | chiffrement au repos, cloisonnement multi-entreprise |
| 3 | **Seuil d'alerte d'échéance** | Anthony | valeur de `echeance_proche` (§ 15) |
| 4 | **Listes fermées** (formes juridiques, types de documents, catégories) | Anthony + lot L5 | contenus des énumérations marquées « indicative » |
| 5 | **Durées de validité des attestations** | juridique / source | § 7.2 — non codées en dur, à lire sur le document |
| 6 | **RGPD** : CV, coordonnées bancaires, base légale, durée de conservation | juriste | § 11, § 3.1 |
| 7 | **Portage juridique / conflit d'intérêts** | juriste (`PROJECT.md` § 6) | hors modèle, mais conditionne la mise en œuvre |

---

## 17. Données dans le dépôt — rappel de confidentialité

- **Aucune donnée réelle d'entreprise** ne doit figurer dans le dépôt : ni SIRET, ni
  IBAN, ni bilan, ni CV réel.
- Les exemples de données éventuels sont **fictifs et signalés comme tels**.
- `data/` est ignoré par git (`.gitignore`) : les fichiers documents (KBIS, bilans,
  CV) vivent hors dépôt, référencés par `document.chemin_stockage`. Rien de
  confidentiel n'y est versionné non plus.
- Les colonnes `sensibilite = confidentiel` listent les champs qui devront être
  chiffrés au repos et cloisonnés par entreprise avant toute mise en œuvre réelle.

---

*Fin du modèle. Structure de référence de la phase 1 ; toute évolution ultérieure passe
par une migration versionnée (`src/migrations/`), jamais par une modification en place
du schéma appliqué.*
