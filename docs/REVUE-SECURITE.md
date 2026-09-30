# REVUE-SECURITE — revue de sécurité et de conformité des choix

*Lot **L6** — agent `qa`. Phase 2 du projet *IA consultations publiques*. Écrit le
30 septembre 2026. Board : `ia-consultations`. Dossier :
`/Users/pause/Projets/ia-consultations-publiques`. Dépend de
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` (lot L2) et de `docs/DATA-MODEL-V2.md` (lot L3).
Référence de cadrage : `docs/DECISIONS.md` (D1 à D6).*

> **Ce document ne corrige rien : il constate.** Les corrections appartiennent aux
> propriétaires des livrables (L1, L2, L3, L4, L5) et à Anthony pour les décisions.
> **Il n'énonce aucune garantie de confidentialité** : seul
> `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` est habilité à le faire (décision
> d'orchestrateur **D-C2**). Cette revue **cite** son verdict et **confronte** ce que les
> autres documents en disent.

---

## 0. Comment lire cette revue

Quatre lectures : **théorie de la menace** (§ 2), **preuve** (§ 3, § 5, § 6, § 7),
**décision** (§ 4, ce qui doit être tranché par un juriste), **synthèse** (§ 9 constats
`S1`…`S13`, § 10 bilan par gravité). Ce que je n'ai **pas** couvert est écrit en § 11.

Treize constats sont relevés, dont **trois majeurs**. Aucun n'est bloquant.

---

## 1. Méthode et commandes réellement exécutées

Exécutées le 30 septembre 2026 depuis `/Users/pause/Projets/ia-consultations-publiques`.
Aucune installation, aucun appel réseau, aucun déploiement. Outils : lecture de fichier,
`grep`, `find`, `git`.

### 1.1 Chemins, volumes, état du dépôt

```bash
find . -type f -not -path './.git/*' | sort
wc -l docs/*.md ; git status --porcelain=v1 ; git log --oneline -n 5
git diff --stat HEAD ; git ls-files docs/ src/
```

- `wc -l docs/*.md` → 14 documents, **6 850 lignes**. Les six livrables de phase 2 sont aux
  chemins attendus : `CONFIDENTIALITE-ET-HEBERGEMENT.md` 651 l., `DATA-MODEL-V2.md` 1 329 l.,
  `SPEC-MVP-V2.md` 521 l., `STACK-PROPOSAL.md` 408 l., `NOMENCLATURE-REFERENCE.md` 590 l.,
  `PLAN-PHASE-2.md` 238 l.
- `git status --porcelain=v1` → **six lignes**, toutes `?? docs/<livrable>.md`. Aucun
  fichier modifié, aucun supprimé, aucun créé hors `docs/`.
- `git log` → `fc2585d`, `d122b4c`, `2137c4c`. La phase 2 **n'a rien committé**.
- `git diff --stat HEAD` → **vide**. `docs/DATA-MODEL.md` (v1), `PROJECT.md`, `README.md`,
  tout `src/` sont **suivis et non modifiés**.

### 1.2 Fraîcheur : squelette et v1 intacts

```bash
stat -f "%Sm %N" -t "%Y-%m-%d %H:%M" docs/*.md PROJECT.md README.md \
  src/app/main.py src/app/domain/entreprise.py src/migrations/README.md
```

Les livrables de phase 2 portent des horodatages **10:24 → 10:33**. Ce qui devait rester
intact porte un horodatage de phase 1 : `PROJECT.md` 09:56, `README.md` 09:56,
`docs/DATA-MODEL.md` (v1) **09:58**, `src/app/main.py` 09:59,
`src/app/domain/entreprise.py` 09:58, `src/migrations/README.md` 09:59. **Le squelette et
la v1 n'ont pas été touchés** (ni horodatage, ni `git diff`).

### 1.3 Hygiène des données et des secrets

```bash
find . -type f \( -name "*.pdf" -o -name "*.docx" -o -name "*.xlsx" -o -name "*.zip" \
  -o -name "*.sql" -o -name "*.env" -o -name "*.key" -o -name "*.pem" \) -not -path './.git/*'
ls -la data/ scripts/ src/migrations/
grep -rnoE "FR[0-9]{2}[ ]?([0-9A-Z]{4}[ ]?){4}[0-9A-Z]{2,3}|[0-9]{14}\b|\b0[1-9]([ .-]?[0-9]{2}){4}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" docs/*.md README.md PROJECT.md src -r
```

- **Aucun** `*.pdf`, `*.docx`, `*.xlsx`, `*.zip`, `*.sql`, `*.env`, `*.key`, `*.pem`.
  `data/` et `scripts/` **vides**. `src/migrations/` ne contient que `README.md` :
  **aucune migration écrite ni appliquée**.
- Recherche d'identifiants réalistes : **une seule occurrence**, `00000000000000`, dans
  `docs/PLAN-DE-TEST.md:224` et `src/app/domain/entreprise.py:7` (docstring « EXEMPLE
  FICTIF »). **Aucun IBAN réel, aucun SIRET réaliste, aucun courriel, aucun téléphone.**
- `.gitignore` couvre `data/`, `.env`, `.secret`, `*.key`, `*.pem`, `__pycache__/`,
  `.DS_Store`, `*.log`, `tmp/`.

### 1.4 Formulations de confidentialité et périmètre

```bash
grep -rnoE "seul le client a accès à ses données|aucun autre client[^.]*|hébergé[e]? en France[^.]*|chiffré[a-z]*[^.,]*" docs/*.md README.md PROJECT.md
grep -rniE "inviolable|sécurité absolue|100 ?%|ne quittent jamais|aucun humain|par construction|garantie de confidentialité" docs/*.md README.md PROJECT.md
grep -rniE "stripe|paypal|prestataire de paiement|intégration de paiement|pip install|déployé|en production" docs/*.md
```

Les occurrences de « seul le client a accès à ses données » se trouvent **uniquement** dans
`docs/DECISIONS.md` (D6 : tension posée ligne 70, qualifiée lignes 74-97), dans
`docs/PLAN-PHASE-2.md` (risque, ligne 141), dans `docs/STACK-PROPOSAL.md` (lignes 178 et
195, qui **renvoient** au verdict de L2) et dans `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`
(le verdict). **Aucun document ne l'énonce comme un fait non qualifié.** Détail en § 5.
Pas de `Stripe`, ni d'intégration de paiement. Les mots « production » ne figurent qu'en
sens négatif (« ne pas charger en production »).

### 1.5 Vérifications structurelles du modèle

```bash
grep -niE "iban|bic|effectif" docs/DATA-MODEL-V2.md
grep -c "client_id" docs/DATA-MODEL-V2.md      # → 59
grep -c "entreprise_id" docs/DATA-MODEL-V2.md  # → 17
grep -ci "checklist" docs/DATA-MODEL-V2.md     # → 0
grep -ci "critere" docs/DATA-MODEL-V2.md       # → 0
grep -noE "^\| \`[a-z]+\.[a-z_.]+\`" docs/NOMENCLATURE-REFERENCE.md
```

`client_id` : **59** occurrences ; `entreprise_id` : **17**. `checklist` et `critere` :
**zéro** (constat **S2**). Les namespaces de la nomenclature (`type.document`,
`forme.juridique`…) divergent de ceux attendus par le modèle (**S6**).

---

## 2. Analyse de menace

### 2.1 Actifs à protéger

| Actif | Où il vit (preuve) | Sensibilité |
|---|---|---|
| Documents du client (DCE déposés, KBIS, bilans, attestations) | hors base, `document.chemin_stockage` préfixé par client (`DATA-MODEL-V2.md` § 4.3) | secret des affaires ; pièces fiscales et sociales |
| Bibliothèque d'entreprise | entités de contenu `client_id` (`DATA-MODEL-V2.md` § 10) | savoir-faire, marges, historique de chantiers |
| Données personnelles (CV, représentant légal, contact de référence chez un maître d'ouvrage) | `cv`, `representant_legal`, `reference_chantier.contact_reference` (§ 10 F1/F5/F6) | RGPD |
| Coordonnées bancaires (IBAN, BIC, RIB) | `entreprise_version` (§ 5.4, lignes 356-358) | fraude bancaire |
| Identifiants et accès | entité `utilisateur` (§ 5.2, lignes 294-312) | pivot d'accès |
| Dossier de réponse en cours | **non modélisé** (voir S2) | secret des affaires, égalité des candidats |

### 2.2 Adversaires retenus

Candidat concurrent ; salarié indélicat ; attaquant externe ; **l'éditeur / administrateur
technique lui-même** ; sous-traitant (hébergeur, fournisseur du modèle d'IA).

### 2.3 Couples actif / adversaire — scénario, mesure attendue, ce qui reste ouvert

**M1 — Candidat concurrent → dossier et bibliothèque d'un autre concurrent.**
*Scénario :* énumération d'identifiants, requête omettant le filtre de client.
*Mesure attendue :* `client_id` redondant partout (§ 4.2), chemins préfixés (§ 4.3),
invariants I1-I5 (§ 3.4), séparation des accès (§ 4.3).
*Reste ouvert :* aucun test d'isolation n'existe ; un chemin de croisement résiduel subsiste
(**S4**) ; l'autorisation par requête n'est pas conçue.

**M2 — Salarié indélicat du client → exfiltration de l'intérieur.**
*Scénario :* téléchargement de la bibliothèque, validation d'une fiche non lue.
*Mesure attendue :* `confidentiel` masqué par défaut (`UI-SAISIE.md` § 10 ligne 553) ;
`relecteur_nom` obligatoire et horodaté (§ 6.4) ; révocation à la première modification
(§ 6.5).
*Reste ouvert :* le nom du relecteur est **auto-déclaré** (pas d'authentification au MVP,
§ 15 point 15) — c'est une déclaration, pas une preuve ; pas de piste d'audit
d'exploitation (§ 13.3, reconnu).

**M3 — Attaquant externe → accès, vol de volume, injection.**
*Scénario :* attaque du serveur ; vol de disque ou de sauvegarde ; **document piégé**
contenant des consignes.
*Mesure attendue :* chiffrement au repos (L2 § 8.2), région française (§ 8.1), cloisonnement
(§ 8.3), pas d'entraînement (§ 8.4).
*Reste ouvert :* en B, un volume volé **avec** la clé est lisible ; en B et C, la donnée est
en clair pendant le traitement ; l'**injection par le contenu d'un document** n'est traitée
par aucun livrable (**S11**).

**M4 — Éditeur / administrateur → lecture des données de tous les clients.**
*Scénario :* l'exploitant, un mainteneur ou l'hébergeur lit n'importe quel document.
Aggravant : **le porteur est un agent de la Mairie de Saint-Denis, acheteur public** (D4,
`PROJECT.md` § 6).
*Mesure attendue :* aucune architecture de la phase 2 ne l'empêche (L2 l'écrit : § 1 étape 3,
§ 5, § 6) ; la parade est contractuelle et organisationnelle.
*Reste ouvert :* **le croisement « administrateur peut lire » × « conflit d'intérêts » n'est
nommé nulle part** (**S3**) — c'est la menace la plus grave du produit.

**M5 — Sous-traitant → transfert et rétention.**
*Scénario :* le DCE part hors UE, y est journalisé 30 jours, ou sert à entraîner un modèle ;
un sous-traitant ultérieur le reçoit.
*Mesure attendue :* chemin de la donnée tracé jusqu'à l'étape 7-8 (L2 § 1-2) ; DPA art. 28,
non-entraînement, rétention zéro (§ 8.4) ; fournisseur UE recommandé (§ 9).
*Reste ouvert :* dépend du choix d'Anthony (question 2). **Deux points non nommés** : le
fournisseur unique voit les DCE de **tous les candidats** d'une même consultation ; sa
liste de sous-traitants ultérieurs n'est pas obtenue (**S11**).

### 2.4 Menaces explicitement non couvertes

1. Conflit d'intérêts × accès administrateur (**S3**) — le plus structurant.
2. Chemin de croisement entre deux clients par la table de liaison de facturation (**S4**).
3. Injection de consignes via le contenu d'un DCE (**S11**).
4. Exposition croisée chez un fournisseur de modèle unique (**S11**).
5. Volume volé avec la clé en option B — limite **assumée et écrite** par L2, ce n'est pas un
   constat.

---

## 3. Cloisonnement entre clients — vérification

### 3.1 Présence du champ de cloisonnement

**Oui sur le papier.** `DATA-MODEL-V2.md` § 3.2 (l. 162-171) déclare `client_id`
**obligatoire** sur toute entité de contenu ; § 4.2 (l. 241-247) explique la redondance :
« *c'est cette redondance qui rend le cloisonnement vérifiable requête par requête* ».
§ 4.4 (l. 261-273) partitionne : cloisonnées directement (`utilisateur`, `entreprise`,
`abonnement`, `evenement_facturation`), cloisonnées via l'entreprise et la fiche mais portant
`client_id` en propre (19 entités), globales sans `client_id` (`jeu_reference`,
`valeur_reference`).

**Ce qui manque à cette partition :**

- **`evenement_facturation_dossier`** (§ 11.4, l. 967-982) ne figure dans aucune des trois
  listes et ne porte pas `client_id` (**S4**).
- **`fiche_version`** ne figure pas non plus, mais c'est l'**exception documentée et unique**
  (§ 3.2 l. 173-175, § 6.1 l. 411) : elle **est** l'axe de versionnement. Correct.
- **`tracabilite_valeur`** (§ 7.2, l. 546-564) et **`validation_relecture`** (§ 6.4,
  l. 471-488) listent `client_id` mais **omettent** `entreprise_id` et `fiche_version_id`,
  que § 3.2 déclare obligatoires « sans exception » (**S5**).

### 3.2 Entité orpheline ou chemin croisé ?

Aucune entité orpheline, sauf le cas de liaison ci-dessus. Le modèle **ferme** ce qu'il
pouvait fermer : I4 (l. 209) interdit qu'une valeur soit tracée vers un document d'un autre
client ; I5 (l. 210) interdit qu'un jeu global porte une donnée client ; I2 (l. 207) tient la
cohérence du `client_id` avec la racine. **Il reste un chemin** : la table de liaison de
facturation (S4). Les références **polymorphes** de `tracabilite_valeur` sont une limite
**assumée et écrite** (§ 7.6, § 14, point ouvert 11) : le cloisonnement y est **applicatif**,
donc prouvable seulement par un test d'isolation qui n'existe pas encore.

### 3.3 Une information d'un candidat peut-elle nourrir un autre candidat ?

**Non par la structure, sauf par les deux fuites nommées.** Les jeux de référence sont
globaux et **sans donnée client** (I5, § 8.4) : du vocabulaire, jamais une donnée
d'entreprise. `SPEC-MVP-V2.md` § 3.3 (l. 259-261) interdit explicitement de « croiser les
DCE de plusieurs entreprises candidates ». **Le seul vecteur d'échange entre candidats n'est
pas dans le modèle mais dans la chaîne de traitement** : le fournisseur de modèle unique
(S11) et l'administrateur (S3). Ces deux points sont **absents** de L2 et de L3.

**Conclusion.** Le cloisonnement **par la structure** est réel et vérifiable requête par
requête — un vrai progrès sur la v1 — avec **deux réserves** (S4, S5). Il **ne constitue pas**
une garantie d'isolation cryptographique : L3 le dit lui-même (§ 3.4 note l. 213-218), et je
le confirme.

---

## 4. Note RGPD — trois listes

*Avertissement : je ne suis pas juriste. Je documente, je signale, je ne tranche ni la base
légale, ni la durée de conservation, ni la qualification responsable/sous-traitant. Ces
points relèvent de **D4** (juriste, fin de projet) et sont **bloquants pour la
commercialisation**, pas pour le développement.*

### 4.1 Ce qui est traité (avec preuve)

| Catégorie | Emplacement (preuve) | Nature |
|---|---|---|
| CV nominatifs | `cv.nom`, `cv.prenom`, `cv_piece`, `diplomes` (`DATA-MODEL-V2.md` § 10 F6, l. 864-867) | donnée personnelle |
| Représentant légal | `representant_legal.nom`, `prenom`, `date_nomination` (§ 5.5, l. 380-391) | donnée personnelle |
| Contact de référence chez un maître d'ouvrage | `reference_chantier.contact_reference` (§ 10 F5, l. 855) | donnée personnelle **de tiers** |
| Coordonnées bancaires | `entreprise_version.iban`, `bic`, `piece_rib` (§ 5.4) | donnée confidentielle |
| Comptes annuels, bilans | `exercice_comptable.*`, `attestation.*` (§ 10 F2) | données d'entreprise |
| Identification de l'entreprise | `siret_siege`, `numero_tva_intracommunautaire` (§ 5.4) | donnée d'entreprise |
| Documents déposés | `document` (§ 9.1) | secret des affaires |

### 4.2 Ce qui est traité « pour le compte de qui » — **à trancher**

L2 § 11 (l. 563-593) pose deux affirmations qui **doivent être articulées par un juriste** :

- « Responsable de traitement : l'entité qui porte le produit et facture — à trancher »
  (l. 569-571) — donc l'éditeur serait responsable de traitement ;
- « les CV des salariés du client sont des données personnelles traitées par l'éditeur **pour
  le compte du client** — l'information des salariés relève du client en tant que responsable
  de traitement de ses propres salariés » (l. 590-593) — donc l'éditeur serait sous-traitant.

Ces deux qualifications coexistent sans être articulées (**S8**). La distinction
responsable/sous-traitant conditionne le registre, les mentions, **et l'exercice des droits**
(à qui un salarié s'adresse pour accéder à son CV). À faire trancher : juriste.

### 4.3 Ce qui est traité (fait) ; ce qui n'est pas traité ; ce qui bloque

**Est traité :**

- l'inventaire des catégories de données (L2 § 11, complété ici § 4.1) ;
- la chaîne des sous-traitants à contractualiser : hébergeur, fournisseur de modèle, outil de
  supervision, service d'e-mail (L2 § 11, l. 572-574) ;
- le régime des **transferts hors UE** (L2 § 11, l. 575-579) : aucun transfert identifié si
  fournisseur français/UE ; transfert **caractérisé** sinon ;
- la représentation de la **résiliation** et du sort des données dans le modèle
  (`client.date_resiliation`, § 5.1 ; § 13.4).

**N'est pas traité :**

- **base légale du traitement** — non choisie (L2 § 11 ne la nomme pas ; point ouvert 6 de
  L3) ;
- **durée de conservation** — non fixée (point ouvert 19) ; le modèle dit seulement qu'aucune
  durée n'est inventée ;
- **registre des traitements** — non tenu ;
- **AIPD** (analyse d'impact) — « probablement nécessaire… à confirmer par le juriste »
  (L2 § 11, l. 588-589) ;
- **droits des personnes** (accès, rectification, effacement) — **aucun mécanisme** n'est
  représenté dans le modèle : rien ne relie un CV ou un représentant légal à une demande
  d'exercice de droits ; le sort d'un CV après départ d'un salarié n'est pas défini ;
- **information des personnes** — renvoyée au client (L2 § 11, l. 590-593), sans procédure.

**Bloque :**

- la **qualification responsable / sous-traitant** (S8) ;
- la **base légale** et la **durée de conservation** : bloquent la mise en service ;
- l'**entité porteuse du contrat** (personne physique ou société) : conditionne registre,
  mentions légales et facturation (L2 § 12) ;
- le **fournisseur du modèle** (UE ou hors UE) : détermine s'il y a un transfert hors UE.

**Catégories manquantes à l'inventaire de L2, repérées par confrontation au modèle :** le
**contact de référence chez un maître d'ouvrage** (§ 10 F5) — donnée personnelle de tiers —
et les **contacts des maîtres d'ouvrage passés** ne figurent pas dans la liste de L2 § 11
(**S8**).

---

## 5. Honnêteté des formulations — confrontation (vérification prioritaire)

### 5.1 Le verdict de référence (L2)

| Option D6 | Verdict de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` | Preuve |
|---|---|---|
| **A** — chiffrement côté client + traitement local | **Vraie par construction** | § 4, l. 253-260 ; § 0 tableau l. 47 |
| **B** — chiffrement au repos + isolation serveur | **Fausse au sens strict** | § 5, l. 294-300 ; § 0 l. 48 |
| **C** — clés du client, déverrouillage à la demande | **Vraie sous conditions** (vraie au repos, fausse pendant la fenêtre de traitement) | § 6, l. 334-348 ; § 0 l. 49 |

Règle **D-C2** (PLAN-PHASE-2 § 3) : seul L2 peut énoncer une garantie ; tout autre document
ne peut qu'en **citer un extrait** ou écrire « à compléter après validation ». Règle de L2
§ 0 (l. 51-52) : « recopier “seul le client a accès à ses données” sans le verdict qui la
qualifie » est **interdit partout**.

### 5.2 Confrontation, document par document

| Document | Phrase / passage concerné | Preuve | Conforme au verdict ? |
|---|---|---|---|
| `docs/DECISIONS.md` (D6) | « Seul le client a accès à ses données » | l. 70 | **Conforme** — la phrase est posée comme **objectif** et la tension est explicitée l. 74-97 (« faux au sens strict » l. 88) |
| `docs/PLAN-PHASE-2.md` | « seul le client a accès à ses données est techniquement intenable » | l. 141, 168 | **Conforme** — c'est un **risque**, pas une promesse |
| `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` | les trois verdicts | l. 47-49, 255, 296, 336 | **Référence** — le verdict lui-même |
| `docs/STACK-PROPOSAL.md` | « le verdict… appartient à L2 — à compléter » | l. 178-180, 193-198, 213 | **Conforme** — renvoie, n'affirme pas |
| `docs/STACK-PROPOSAL.md` | « confidentialité maximale, obtenue **par construction** » (scénario C) | l. 175 | **Compatible mais à surveiller** — scénario C = famille A, verdict « vraie par construction » ; la juxtaposition avec la note « n'énonce aucune garantie » (l. 193-198) frôle la limite (**S12**) |
| `docs/STACK-PROPOSAL.md` | fournisseur hors UE : « engagement **commercial**, pas une garantie technique » | l. 256-258 | **Conforme** — honnête |
| `docs/SPEC-MVP-V2.md` | « À COMPLÉTER après validation de L2 » ; « le serveur voit donc les documents pendant le traitement » | l. 389-414 | **Conforme sur le fond** — n'affirme rien, dit la vérité ; mais affirme que L2 « n'existe pas encore » (l. 392) alors qu'il existe (**S10**) |
| `docs/DATA-MODEL-V2.md` | « Ce document n'énonce aucune garantie » ; renvoi à L2 | l. 216-218, 1311-1315 | **Conforme** — renvoie |
| `docs/NOMENCLATURE-REFERENCE.md` | « n'énonce aucune garantie de confidentialité » | l. 49-52, 514-516 | **Conforme** — renvoie |
| `docs/DATA-MODEL.md` (v1) | « les champs `confidentiel`… devront être chiffrés au repos et cloisonnés » | l. 516-517 | **Conforme** — c'est une **obligation future**, pas une promesse ; archive de phase 1 |
| `PROJECT.md` § 6 | « Chiffrement au repos, cloisonnement par entreprise, aucune donnée client dans un modèle d'entraînement » | l. 80-82 | **Conforme** — ce sont les **contraintes fermes** de D6 (objectifs), pas la phrase « seul le client ». Nuance de vocabulaire : « par entreprise » vs « par client » (**S13**) |

### 5.3 Verdict de la chasse aux écarts

**Aucun constat majeur sur ce point.** Aucune phrase du dépôt n'affirme une confidentialité
que l'architecture ne tient pas : la règle **D-C2** est respectée **en négatif** (aucun
document n'usurpe l'autorité de L2). Deux réserves mineures :

- **S12** — le libellé « confidentialité maximale par construction » de `STACK-PROPOSAL.md`
  § 3.C, juxtaposé à la note qui prétend n'énoncer aucune garantie.
- **S10** — la règle D-C2 est **non satisfaite en positif** : aucun document ne **cite**
  encore L2 ; tous écrivent « à compléter ». `SPEC-MVP-V2.md` § 6 (l. 389-399) va jusqu'à
  affirmer que L2 « n'existe pas encore ». Les extraits citables sont pourtant fournis par L2
  § 10. Ce n'est pas un écart de promesse — c'est un renvoi à mettre à jour.

---

## 6. Traitement des constats de la phase 1 (C1…C10)

Source : `docs/PLAN-DE-TEST.md` § 11. Statut vérifié dans les livrables de phase 2.

| Constat | Gravité (phase 1) | Statut en phase 2 | Preuve | Réserve |
|---|---|---|---|---|
| **C1** — coordonnées bancaires et effectif absents du modèle | majeur | **Traité** | `DATA-MODEL-V2.md` § 5.4 (l. 353-358) : `iban`, `bic`, `piece_rib`, `effectif`, `date_effectif`, `effectif_source_code` ; arbitrage des trois effectifs § 5.4 (l. 360-372) ; § 12/C1 | aucun résidu — champs effectivement présents (`grep -niE "iban\|bic\|effectif"`) |
| **C2** — granularité de traçabilité incohérente | majeur | **Traité** | § 7 : table `tracabilite_valeur` (l. 546-564), règle de projection § 7.3 (l. 566-572), colonnes de synthèse redéfinies § 7.4, règle § 7.5 ; § 12/C2 | **réserve S5** : `tracabilite_valeur` n'a ni `entreprise_id` ni `fiche_version_id` — traçabilité de valeur **non versionnée** |
| **C3** — verrou de relecture non représentable | majeur | **Traité** | § 6.4 : `relecteur_nom` **obligatoire** (l. 479), `date_validation` **automatique** (l. 481), `statut validee\|revoquee` (l. 483), `date_revocation` + `motif_revocation` (l. 484-485) ; révocation § 6.5 ; contrôle indépendant par empreinte (I6, l. 211) ; § 12/C3 | le relecteur est **auto-déclaré** (sans authentification) — L3 l'écrit honnêtement (S3/M2) |
| **C4** — deux listes pour `type_document` | mineur | **Partiellement traité** | structure : `document.type_document` en `code_reference` (§ 9.1 l. 741) ; une seule liste attendue § 8.6 (l. 720) | **la liste unique n'existe dans aucun livrable** ; le namespace diverge de L5 (`type.document`) — **S6** |
| **C5** — délégations sans destinataire (export, formats de DCE) | mineur | **Nommé, non tranché** | § 9.2 (l. 763-769) + points ouverts 8 et 9 (§ 15, l. 1285-1286) ; `SPEC-MVP-V2.md` § 7.2 et § 8 | conforme à l'attendu : la délégation a maintenant un **destinataire nommé** (Anthony / lot d'implémentation) |
| **C6** — mémoire technique type dans le MVP | mineur | **Ouvert** | § 15 point 10 (l. 1287) ; `SPEC-MVP-V2.md` § 7.1 (l. 422-432) pose deux options | décision d'Anthony, non tranchée — **ce n'est pas un défaut** |
| **C7** — source de traçabilité non vérifiable (carte Kanban) | mineur | **Traité par L4** | `SPEC-MVP-V2.md` § « Sources » (l. 20-21) et note de correction (l. 37-40) : plus aucun identifiant Kanban | — |
| **C9** — états de fiche et granularité non alignés | mineur | **Traité** | § 6.2 : 7 états alignés sur les 6 de l'interface + archivage, avec table de correspondance (l. 423-442) ; progression par famille § 6.3 (`fiche_famille`, l. 444-460, 4 états, cohérents avec `UI-SAISIE.md` § 7 l. 488-492) | — |
| **C10** — `fiche_version_id` obligatoire absent de la racine | mineur | **Traité** | racine de contenu = `entreprise_version` (§ 5.4), qui porte `fiche_version_id` ; `entreprise` devient ancre stable (§ 5.3) ; exception unique documentée § 3.2 (l. 173-175) ; § 7.6 | — |

### 6.1 C1, C2, C3 : résolus ou simplement mentionnés ?

Vérification demandée explicitement (item 5). **Les trois sont résolus, pas seulement
mentionnés :**

- **C1** — les six champs `iban`, `bic`, `piece_rib`, `effectif`, `date_effectif`,
  `effectif_source_code` figurent dans le tableau de `entreprise_version` (§ 5.4). L'arbitrage
  « trois effectifs » (identité / exercice / métier) est écrit et motivé. Résolu.
- **C2** — la table `tracabilite_valeur` **existe** dans le document, avec sa contrainte
  d'unicité `(entite, enregistrement_id, champ)`, sa règle de projection et son invariant
  I4. Résolu — **avec la réserve S5** sur les colonnes de rattachement manquantes.
- **C3** — l'entité `validation_relecture` **existe**, avec `relecteur_nom` obligatoire,
  `date_validation` posée automatiquement, `statut`, `date_revocation`, et un contrôle
  **indépendant** par empreinte (I6) qui rend la révocation opposable même si le code oublie
  d'écrire. Résolu. Le point de granularité (fiche vs famille) est tranché explicitement
  (« le niveau qui fait foi est la fiche ») — c'est une décision, assumée et motivée.

**Aucun des six constats confiés à L3 n'est reconduit** : c'est un progrès mesurable. Deux
constats mineurs (C4, C6) et deux constats « nommés non tranchés » (C5, C6) subsistent, ce qui
est conforme à l'attendu.

---

## 7. Cohérence stack ↔ modèle (L1 ↔ L3)

`docs/STACK-PROPOSAL.md` et `docs/DATA-MODEL-V2.md` ont été écrits en parallèle. Points de
recouvrement vérifiés.

| Point | STACK-PROPOSAL | DATA-MODEL-V2 | Verdict |
|---|---|---|---|
| **Champ de cloisonnement** | « colonne `entreprise_id` présente partout » (l. 101) ; « filtrage systématique par `entreprise_id` dans la couche `storage/` » (l. 399) ; « filtrage systématique par `entreprise_id` » au niveau base (l. 135-136) | `client_id` **obligatoire et redondant** sur toute entité de contenu (§ 3.2, § 4.2) ; `entreprise_id` est une **autre notion** (entité juridique, § 4.1) | **DIVERGENCE — S1 (majeur)** |
| **Modèle de compte** | « un compte = une entreprise » (l. 100) | `client` (partie contractante) ≠ `entreprise` (entité juridique) ; un client peut avoir **plusieurs** entreprises (§ 4.1) | **divergence — incluse dans S1** |
| **Document de référence de la structure** | « `docs/DATA-MODEL.md` reste la référence de la structure » (l. 311-312) | `docs/DATA-MODEL-V2.md` **remplace** la v1 (§ 6-8) | **divergence — S7** |
| Portabilité du modèle | modèle portable, sortie SQLite → PostgreSQL (l. 140-141, 314-316) | aucune fonctionnalité propriétaire présumée (§ 14) | **cohérent** |
| Migrations | SQL numérotées, réversibles (l. 68-69, 103) | hors de son objet ; convention rappelée en fin de document | **cohérent** |
| Stockage des fichiers | dossier local / stockage objet S3 (l. 97, 132) | hors base, chemin préfixé par client (§ 4.3) | **cohérent** |
| Sécurité au niveau des lignes | « au besoin une règle de sécurité appliquée par la base elle-même » (l. 135) | contraintes exprimées comme **règles applicatives**, aucune fonctionnalité propriétaire présumée (§ 14) | **compatible** (formule conditionnelle « au besoin ») |
| Fourchettes de coût | OVH `b2-7` 25,17 €/mois (l. 110-114) | — | pas de recouvrement ; L2 cite des prix d'une **autre gamme** (VPS 6,49 €) — non contradictoire |

**Conclusion section 7.** Un écart **majeur** (S1 : clé de cloisonnement `entreprise_id` vs
`client_id` — c'est la clé dont dépend D6) et un écart mineur (S7 : renvoi à la v1 comme
référence de structure). Le reste est cohérent.

---

## 8. Conformité au périmètre de la phase

| Interdit de phase 2 | Vérifié ? | Preuve |
|---|---|---|
| Implémentation, code | **Non fait** | `git status` : aucun fichier de code créé ; `src/` non modifié (mtimes 09:58-09:59) |
| Migration appliquée / écrite | **Non fait** | `src/migrations/` ne contient que `README.md` ; aucun `*.sql` |
| Modification de `src/` | **Non fait** | `git diff HEAD` vide ; mtimes de phase 1 |
| Installation, déploiement, mise en production | **Non fait** | aucune dépendance, aucun `*.env`, aucun appel réseau dans les livrables |
| Intégration d'un paiement ou prestataire de paiement | **Non fait** | `grep` : aucun `Stripe`/`PayPal`/prestataire ; `DATA-MODEL-V2.md` § 11 décrit une structure **sans** montant ni prestataire |
| Mémoire technique rédigée automatiquement | **Non fait** | `DATA-MODEL-V2.md` § 10 F9 (l. 892-904) : **stocke** sans rédiger ; `SPEC-MVP-V2.md` § 1.4 |
| Veille / dépôt de pli / portail acheteur public | **Non fait** | exclus nommément (`SPEC-MVP-V2.md` § 1.4 ; `DATA-MODEL-V2.md` § 0) |
| `docs/DATA-MODEL.md` (v1) intact | **Oui** | suivi par git, `git diff` vide, mtime 09:58 |
| Aucune donnée réelle dans le dépôt | **Oui** | seul `00000000000000`, signalé fictif ; `data/` vide |

**Conclusion section 8.** Le périmètre d'une phase documentaire est **respecté** : rien n'a
été installé, déployé, codé ni appliqué ; la v1 est intacte ; le dépôt ne contient aucune
donnée réelle.

---

## 9. Constats (par gravité)

### Bloquants

**Aucun.** Rien n'empêche la phase 2 d'être considérée comme livrée sur le plan documentaire.

### Majeurs

**S1 [majeur] — La clé de cloisonnement diverge entre la stack et le modèle
(`entreprise_id` vs `client_id`).**
*Preuve.* `docs/STACK-PROPOSAL.md` l. 101 (« colonne `entreprise_id` présente partout »),
l. 399 (« filtrage systématique par `entreprise_id` »), l. 135-136, l. 100 (« un compte = une
entreprise ») — contre `docs/DATA-MODEL-V2.md` § 3.2 (l. 165 : `client_id` obligatoire) et
§ 4.1-4.2 (un client peut avoir plusieurs entreprises ; `client_id` est la clé du
cloisonnement).
*Attendu.* Une seule clé de cloisonnement, citée à l'identique dans les deux documents.
*Observé.* Deux clés différentes pour le même rôle.
*Gravité.* Majeur — D6 fait du cloisonnement la contrainte structurante ; une implémentation
qui filtre sur `entreprise_id` (clé de l'entité **juridique**) n'isole pas ce qui est cloisonné
au niveau **client** (utilisateurs, abonnements, événements de facturation) et peut être
trompée par un client à plusieurs entreprises.
*Recommandation.* Aligner `STACK-PROPOSAL.md` sur `DATA-MODEL-V2.md` (qui fait foi pour la
structure) : parler de `client_id` partout, et non d'`entreprise_id`.

**S2 [majeur] — Les briques B et C (analyse du DCE, checklist) n'ont aucune représentation
dans `DATA-MODEL-V2.md`.**
*Preuve.* `grep -ci "checklist"` → **0** ; `grep -ci "critere"` → **0**. Aucune entité ne
représente les **pièces exigées**, les **critères**, la **date limite extraite** ni les
**manques**. Le seul objet proche, `dossier` (§ 11.2, l. 929-944), ne porte qu'un
`reference_consultation` **saisi par l'humain** et n'est relié à aucun de ses documents.
`document` (§ 9.1, l. 730-754) impose `fiche_version_id` **et** `entreprise_id`
**obligatoires** : structurellement, un DCE déposé (document de l'acheteur, extérieur à la
bibliothèque de l'entreprise) ne peut pas y être rangé sans fausser le modèle.
*Attendu.* Le modèle représente la sortie de la brique B (éléments extraits, chacun avec sa
source) et de la brique C (checklist, manques), puisque D6 et la ligne rouge exigent que
**toute valeur extraite porte sa source**.
*Observé.* Deux des trois briques du MVP n'ont ni table, ni champ, ni point ouvert dédié.
*Gravité.* Majeur — la phase 3 implémenterait la brique B/C sans support de données ; le
principe « aucune valeur sans source » n'a nulle part où s'appliquer pour l'extraction d'un
DCE.
*Recommandation.* L3 (ou un lot de phase 3) ajoute les entités de l'extraction et de la
checklist, **ou** écrit explicitement que les briques B et C sont **hors** du périmètre du
modèle v2. En l'état, le silence n'est pas une décision.

**S3 [majeur] — Menace non nommée : l'exploitant peut lire tous les clients, et le porteur
est un agent de l'acheteur (conflit d'intérêts, D4).**
*Preuve.* `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 1 étape 3 (l. 75) : « il **est ici que
“seul le client” devient faux** » ; § 5 (l. 286-288) et § 6 (l. 327-328) : le serveur et son
personnel lisent pendant le traitement. `docs/DECISIONS.md` D4 (l. 45-56) et `PROJECT.md` § 6
(l. 80) : le porteur a un lien avec la Mairie de Saint-Denis, acheteur public. **Aucun
livrable de la phase 2 ne relie ces deux faits.**
*Attendu.* Que l'analyse de menace nomme le cas où un agent de l'acheteur exploite la
plateforme et peut lire les dossiers de candidats concurrents sur des marchés de son
employeur.
*Observé.* Les deux faits coexistent dans deux documents différents, sans être rapprochés.
*Gravité.* Majeur — c'est le scénario de conflit d'intérêts le plus concret du produit, et il
n'est pas couvert.
*Recommandation.* Ajouter ce couple actif/adversaire à l'analyse de L2 (et le réaffirmer
dans la présente revue) : aucune architecture de la phase 2 ne l'empêche ; seule la
séparation des casquettes et un contrôle humain l'atténuent. À traiter avec le juriste (D4).

### Mineurs

**S4 [mineur] — Chemin de croisement résiduel entre deux clients : `evenement_facturation_dossier`.**
*Preuve.* `DATA-MODEL-V2.md` § 11.4 (l. 967-982) : la table de liaison ne porte **pas**
`client_id` et ne figure dans **aucune** des trois listes de § 4.4 ; sa seule contrainte
(§ 11.4, l. 978-982) porte sur l'unicité du rattachement `principal`, **pas** sur l'égalité des
clients. Les invariants I1-I6 (§ 3.4, l. 204-211) ne la couvrent pas.
*Attendu.* Un invariant interdisant de rattacher un dossier à un événement de facturation d'un
**autre** client.
*Observé.* Rien ne l'interdit ; c'est le seul chemin de croisement identifié (§ 3.2).
*Gravité.* Mineur — données de facturation, pas contenu de documents ; mais c'est bien un
« chemin qui permettrait de croiser deux clients ».
*Recommandation.* Ajouter un invariant (par exemple I7) : les deux lignes liées appartiennent
au même `client_id`.

**S5 [mineur] — Colonnes techniques obligatoires « sans exception » absentes de plusieurs
tableaux.**
*Preuve.* § 3.2 (l. 162-171) déclare obligatoires, sur toute entité de contenu, `id`,
`client_id`, `entreprise_id`, `fiche_version_id`, `date_creation`, `date_modification`,
`sensibilite`, `statut_enregistrement`. Or `tracabilite_valeur` (§ 7.2, l. 546-564) omet
`entreprise_id` et `fiche_version_id` ; `validation_relecture` (§ 6.4, l. 471-488) et
`fiche_famille` (§ 6.3, l. 450-458) omettent `sensibilite` et `statut_enregistrement` ;
`document` (§ 9.1, l. 735-754) omet `statut_enregistrement`.
*Attendu.* Une règle unique et appliquée, ou la répétition explicite de la liste des colonnes
héritées dans chaque tableau d'entité.
*Observé.* La convention « ces colonnes ne sont pas répétées » est appliquée de façon
incohérente.
*Gravité.* Mineur — mais deux colonnes manquantes sur `tracabilite_valeur`
(`entreprise_id`, `fiche_version_id`) contredisent directement les invariants I2 et I3, et
laissent une traçabilité de valeur **non rattachée à une version de fiche**.
*Recommandation.* Trancher : soit rappeler la liste des colonnes héritées dans chaque
tableau, soit une phrase unique qui dise lesquelles sont implicites partout, sans exception
autre que `fiche_version`.

**S6 [mineur] — Divergence de nommage des jeux de référence entre L3 et L5 ; la « liste
unique » de C4 n'existe nulle part.**
*Preuve.* `DATA-MODEL-V2.md` § 8.6 (l. 720-723) attend les namespaces `document.type_document`,
`entreprise.forme_juridique`, `rh.statut_mandat`, `rh.origine_effectif`, `attestation.type`,
`assurance.type`, `certification.domaine`, `moyen.categorie`, `produit.famille`,
`reference.nature_travaux`. `docs/NOMENCLATURE-REFERENCE.md` § 3 (l. 452-461) propose
`type.document`, `forme.juridique`, `unite.mesure`, `signe.qualite`… **sans** les jeux
`assurance.type`, `certification.domaine`, `moyen.categorie`, `produit.famille`,
`reference.nature_travaux`, `attestation.type`. La liste unique de types de pièces promise
par C4 **n'apparaît dans aucun livrable** : elle est déclarée « à fournir » par L5 § 4.1.
*Attendu.* Un nom unique par jeu, et la liste effectivement produite (ou explicitement
renvoyée à une source administrative datée).
*Observé.* Deux noms pour le même jeu (`document.type_document` vs `type.document` ;
`entreprise.forme_juridique` vs `forme.juridique`) ; six jeux attendus par le modèle non
listés par L5.
*Gravité.* Mineur (C4 était mineur) — mais D-C1 impose un format commun et L3 fait foi pour
la structure : l'écart est réel et vérifiable.
*Recommandation.* L5 aligne ses en-têtes sur les namespaces de L3 ; L3 ou L5 produisent
effectivement la liste `document.type_document`, à la source.

**S7 [mineur] — La stack désigne la v1 comme référence de structure.**
*Preuve.* `docs/STACK-PROPOSAL.md` l. 311-312 : « Le document `docs/DATA-MODEL.md` **reste**
la référence de la structure » ; l. 57 : « `docs/DATA-MODEL.md` § 0 avait retenu… ». Or
`docs/DATA-MODEL-V2.md` (l. 6-8) annonce qu'il **remplace** la v1.
*Attendu.* Un renvoi vers `docs/DATA-MODEL-V2.md`.
*Observé.* Le renvoi pointe l'archive de phase 1.
*Gravité.* Mineur — un relecteur pourrait implémenter sur la v1.
*Recommandation.* Mettre à jour le renvoi (L1), ou écrire que la v1 est archivée et que la v2
fait foi.

**S8 [mineur] — RGPD : catégories incomplètes et qualification responsable/sous-traitant
non articulée.**
*Preuve.* `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 11 : liste « CV nominatifs, représentant
légal, salariés », **sans** le `reference_chantier.contact_reference` (donnée personnelle de
tiers, `DATA-MODEL-V2.md` § 10 F5, l. 855) ; et pose deux qualifications concurrentes
(l. 569-571 éditeur **responsable** ; l. 590-593 éditeur **sous-traitant** pour les CV).
*Attendu.* Un inventaire complet des catégories et une qualification unique à faire trancher.
*Observé.* Une catégorie manquante et une ambiguïté non signalée.
*Gravité.* Mineur (la note RGPD de L2 se déclare courte et renvoie au juriste), mais les
droits des personnes dépendent de cette qualification.
*Recommandation.* Compléter l'inventaire ; faire trancher par le juriste la qualité
(responsable / sous-traitant) et l'articulation avec l'information des salariés.

**S9 [mineur] — Trois trames A/B/C différentes pour un même décideur.**
*Preuve.* `DECISIONS.md` D6 : options A/B/C = familles de confidentialité ; `STACK-PROPOSAL.md`
§ 3 et § 7 : scénarios A/B/C = socle applicatif ; `SPEC-MVP-V2.md` § 7.1 (l. 424-431) :
options A/B pour la mémoire technique. Anthony est invité à répondre « A, B ou C » à deux
questions distinctes, avec des contenus différents.
*Attendu.* Des libellés non ambigus (par exemple « option de confidentialité 1/2/3 »).
*Observé.* Trois jeux A/B/C.
*Gravité.* Mineur — risque de confusion, pas de sécurité.
*Recommandation.* Renommer les variantes (L1, L4) pour éviter toute méprise dans la feuille de
décision.

**S10 [mineur] — D-C2 satisfait en négatif, non en positif : aucun document ne cite L2.**
*Preuve.* `grep -nE "à compléter|n'existe pas"` → `SPEC-MVP-V2.md` l. 389-392 (affirme que L2
« n'existe pas encore »), `DATA-MODEL-V2.md` l. 217, 257, 1156, 1312, `STACK-PROPOSAL.md`
l. 179, 213, `NOMENCLATURE-REFERENCE.md` l. 51, 515. Aucun de ces documents ne reprend
l'extrait citable pourtant fourni par L2 § 10 (l. 516-538).
*Attendu (D-C2).* Citer un extrait textuel de L2, ou écrire « à compléter après validation ».
*Observé.* Tous écrivent « à compléter » ; la citation n'a pas encore été faite.
*Gravité.* Mineur — ce n'est pas un écart de promesse, c'est un renvoi périmé (les documents
ont été écrits en parallèle).
*Recommandation.* Après validation de l'option par Anthony, remplacer les « à compléter » par
l'extrait cité de L2 § 10.

**S11 [mineur] — Deux menaces non nommées par la phase 2 : injection via le contenu d'un
document, et exposition croisée chez un fournisseur de modèle unique.**
*Preuve.* Aucune occurrence de « injection », « consigne » ou équivalent dans
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` ; § 1 étape 7 (l. 79) et § 2 ne mentionnent pas le
fait que le **même** fournisseur traite les DCE de **plusieurs** candidats d'une même
consultation (secret des affaires / égalité des candidats).
*Attendu.* Nommer ces deux menaces dans l'analyse, avec la mesure attendue (défense contre
l'injection ; clause d'isolation et rétention zéro par client chez le fournisseur).
*Observé.* Absentes.
*Gravité.* Mineur (rétention zéro et non-entraînement sont par ailleurs exigés), mais ce sont
des menaces réelles non couvertes.
*Recommandation.* Compléter L2 § 2 et la § 2.4 de la présente revue.

### Cosmétiques

**S12 [cosmétique] — « Confidentialité maximale, obtenue par construction » dans la stack,
juxtaposée à « ce document n'énonce aucune garantie ».**
*Preuve.* `STACK-PROPOSAL.md` l. 175 contre l. 193-198.
*Gravité.* Cosmétique — compatible avec le verdict de L2 (le scénario C est la famille de
l'option A, « vraie par construction »), mais la formule frôle la limite de D-C2.
*Recommandation.* Remplacer par un renvoi explicite au verdict de L2.

**S13 [cosmétique] — « cloisonnement par entreprise » (PROJECT.md, DATA-MODEL v1) vs
« cloisonnement par client » (v2).**
*Preuve.* `PROJECT.md` § 6 l. 81 ; `docs/DATA-MODEL.md` l. 517 ; contre `DATA-MODEL-V2.md`
§ 4.2. `PROJECT.md` et la v1 ne sont pas modifiables (D-C3), mais la coexistence des deux
vocabulaires doit être connue.
*Gravité.* Cosmétique.
*Recommandation.* À l'occasion d'une future révision (phase 3), unifier le vocabulaire ;
aucune action en phase 2.

---

## 10. Bilan par gravité

| Gravité | Nombre | Constats |
|---|---|---|
| **Bloquant** | 0 | — |
| **Majeur** | 3 | **S1** (clé de cloisonnement `entreprise_id` vs `client_id`), **S2** (briques B/C absentes du modèle), **S3** (menace administrateur × conflit d'intérêts) |
| **Mineur** | 8 | S4, S5, S6, S7, S8, S9, S10, S11 |
| **Cosmétique** | 2 | S12, S13 |

**Ce qui est solide.** Le cloisonnement **par la structure** est réellement vérifiable
requête par requête (`client_id` redondant + invariants I1-I6) — progrès net sur la v1. Les
**trois constats majeurs de la phase 1 (C1, C2, C3) sont effectivement résolus**, pas seulement
mentionnés. Aucune formulation de confidentialité du dépôt n'affirme une garantie que
l'architecture ne tient pas : la règle D-C2 est respectée en négatif. Le périmètre d'une phase
documentaire est strictement tenu : rien n'est installé, déployé, codé ni appliqué ; la v1 est
intacte ; le dépôt ne contient aucune donnée réelle.

**Ce qui doit être corrigé avant la phase 3.** S1 (une seule clé de cloisonnement), S2 (le
modèle doit dire ce qu'il fait, ou ne fait pas, des briques B et C), S3 (nommer le conflit
d'intérêts × accès administrateur). S4 et S5 sont des correctifs de structure peu coûteux.

---

## 11. Ce que cette vérification ne couvre pas

Honnêtement, pour éviter tout faux sentiment de complétude :

1. **Je ne teste aucune fonctionnalité.** Rien n'est implémenté ; ma revue porte sur des
   documents. Aucun comportement réel (analyse de DCE, checklist, export, persistance,
   isolation) n'a été exercé.
2. **Je n'ai pas vérifié les sources externes de L2.** Les prix d'hébergeurs et de modèles, la
   rétention zéro, la résidence UE, les engagements de non-entraînement ne sont **pas**
   revérifiés à la source ; L2 les date et les marque « à vérifier ». Leur exactitude reste à
   confirmer — et leur volatilité est réelle.
3. **Je ne suis pas juriste.** Base légale, durée de conservation, qualification
   responsable/sous-traitant, AIPD, information des personnes : je les **documente** et les
   **signale**, je ne les tranche pas (D4).
4. **Le contenu métier de L5 n'est pas vérifié** sur la source (Qualibat, DTU, avis
   techniques) : L5 le marque lui-même `a_verifier`. Je n'ai pas de compétence métier pour
   juger de sa complétude.
5. **Je n'ai pas évalué la sécurité applicative réelle** (injection, authentification,
   sessions, chiffrement effectif) : il n'y a pas de surface d'attaque, rien n'est codé.
6. **Je n'ai testé aucun chemin de croisement entre clients de façon dynamique** : je n'ai
   constaté le cloisonnement que **par lecture de la structure**. Le test dynamique promis par
   L2 § 8.3 point 4 (« c'est le rôle de L6 ») **reste impossible** sans implémentation ; je le
   signale ici plutôt que de prétendre l'avoir fait.
7. **L'accessibilité de l'interface** n'est pas testable (aucune page n'existe).
8. **L'état du board Kanban** n'est pas vérifié : je n'ai examiné que le dépôt. Les douze
   risques de `docs/PLAN-PHASE-2.md` § 5 ne sont donc pas tous évalués ici.

---

*Fin de la revue. Lot L6 — `qa`. 13 constats (0 bloquant, 3 majeurs, 8 mineurs,
2 cosmétiques), chaque constat avec sa preuve (fichier, ligne, commande). Les corrections
appartiennent aux propriétaires des livrables : L1 (S1, S7, S9), L2 (S3, S8, S11), L3 (S2,
S4, S5, S6), L4 (S9, S10). Les points relevant du juriste (base légale, durée de
conservation, qualification responsable/sous-traitant, conflit d'intérêts) restent ouverts et
bloquants pour la commercialisation (D4), pas pour le développement.*
