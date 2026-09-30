# DONNÉES MÉTIER — Éléments à collecter pour une entreprise d'étanchéité

*Livrable du lot **L5** (agent `batiment`), phase 1 — cadrage. Board : `ia-consultations`.
Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*

> **Rôle de ce document.** Il dit **quoi** collecter sur une entreprise du bâtiment
> spécialisée **étanchéité**, tel qu'un professionnel du métier le formulerait, pour
> alimenter la bibliothèque d'entreprise et préparer une réponse à une consultation
> publique. Il **ne dit pas comment** ces informations sont structurées techniquement :
> c'est le rôle de `docs/DATA-MODEL.md` (lot L2), qui **fait foi pour la structure**.
> En cas de divergence entre les deux documents sur la forme des données, c'est
> `DATA-MODEL.md` qui l'emporte ; le présent document conserve la primauté sur le
> **contenu métier**.

> **Ce que ce document n'est pas.** Il ne rédige aucun mémoire technique, ne propose
> aucun modèle de réponse type et ne chiffre rien. Il ne fixe ni prix, ni marge, ni
> seuil. Il liste des éléments à collecter et explique, métier, pourquoi ils comptent.

---

## Avertissement — exemples fictifs et ligne rouge

**Tous les exemples de ce document sont fictifs et signalés comme tels.** Aucun nom de
client, aucune référence de chantier, aucun montant, aucune surface réelle ne figure
ici. Les valeurs entre crochets `[…]` ne sont que des ordres de grandeur de *format* :
elles n'ont pas de valeur métier et ne doivent pas être reprises telles quelles.

Règles applicables à toute la collecte décrite ci-dessous (ligne rouge du projet,
voir `README.md` et `PROJECT.md` § 5) :

- l'IA **n'invente aucune référence, aucun certificat, aucun chiffre** ; tout élément
  saisi doit pouvoir **pointer vers sa source** (document, attestation, facture, photo) ;
- l'IA **ne signe rien**, **ne fixe pas de prix**, **ne garantit aucune conformité** ;
- **aucune donnée réelle d'entreprise ni document confidentiel** ne va dans le dépôt
  (bilans, CV nominatifs, SIRET, IBAN, attestations nominatives). La bibliothèque
  contiendra ces pièces en production ; en phase 1 et dans ce dépôt, on ne décrit que
  les **champs à collecter**, pas les valeurs.

---

## 1. Références de chantiers — le poste le plus rentable

C'est la matière première du mémoire technique : la commission juge d'abord la
**capacité de l'entreprise à refaire ce qu'on lui demande**, sur la base de chantiers
similaires déjà livrés. Un référentiel de références bien tenu, c'est ce qui se réutilise
à chaque consultation au lieu d'être reconstitué de mémoire. C'est le poste où l'écart
entre une entreprise outillée et une entreprise non outillée est le plus grand.

### 1.1 Champs à collecter, référence par référence

Le tableau ci-dessous liste les champs métier. La colonne « pourquoi » explique l'usage
en commission — c'est ce qui justifie de les collecter dès la première saisie.

| Champ | Formulation métier | Pourquoi ça compte |
|---|---|---|
| Intitulé / objet | Désignation courte et parlante de l'opération (« réfection de l'étanchéité de la toiture-terrasse du bâtiment X ») | Première ligne lue ; sert à apparier une référence avec le besoin du DCE |
| Maître d'ouvrage | **Public** (collectivité, bailleur, établissement) ou **privé** (copropriété, promoteur, industriel) | Un marché public veut souvent des références **chez d'autres maîtres d'ouvrage publics** — le distinguer est décisif |
| Maître d'œuvre / AMO | Le cas échéant, qui pilotait | Permet de retrouver une référence auprès d'un interlocuteur connu |
| Nature des travaux | Vocabulaire métier (voir § 1.2) : étanchéité de toiture, relevés, réfection, isolation rapportée, etc. | C'est le critère d'appariement le plus fin : « surface » seule ne dit pas la compétence |
| Technique / système mis en œuvre | Bitumineux en feuilles, synthèse (PVC/TPO), asphalte coulé, SEL (étanchéité liquide), TAN, toiture-terrasse spécialisée… | Relie la référence aux certifications (§ 2) et aux avis techniques (§ 6) |
| Type d'ouvrage | Toiture-terrasse, toiture inclinée, plancher intermédiaire, cuvelage, réservoir/bassin | Le DTU applicable et la difficulté changent complètement |
| Surface | m² — préciser **quelle surface** : surface de toiture, surface développée (relevés, émergences incluses), ou surface utile | Les métrés se trompent presque toujours là ; une surface annoncée sans définition n'est pas exploitable |
| Linéaire de relevés / points singuliers | ml de relevés, nombre de boîtes à eau, crapaudines, joints de dilatation, pénétrations | Le poste « points singuliers » est ce qui fait la technicité réelle, bien plus que la surface |
| Nature et épaisseur de l'isolant | Type (PIR, laine minérale…), épaisseur, pare-vapeur | Distingue une réfection simple d'un complexe isolant complet |
| Montant | En € **HT**, en précisant la **tranche** (travaux seuls, ou avec échafaudage, dépose, évacuation) | Un montant non cadré est inutilisable ; préciser HT et l'assiette |
| Année de réalisation | Année d'**exécution**, et si possible **année de réception** | Un DCE demande souvent « chantiers achevés depuis moins de N ans » ; c'est la date de réception qui compte — le seuil N reste à vérifier dans chaque règlement de consultation |
| Durée | Durée d'exécution (mois), et le cas échéant **phasage** (travaux en site occupé, par tranches) | La capacité à tenir un planning en site occupé est un critère fréquent (écoles, bâtiments en activité) |
| Conditions d'exécution | Site occupé ou non, école en période de vacances, travail en hauteur, accès difficile, grue/monter-charge | Ce sont les contraintes qui prouvent l'expérience réelle |
| Difficultés rencontrées et solutions | Récit court : support dégradé, fuites multiples, éléments porteurs bois, humidité résiduelle, surcharge limitée | La commission attend précisément ça : ce que l'entreprise a su résoudre, pas un catalogue |
| Photos | Vues avant / pendant / après, points singuliers, détails de relevés | Preuve visuelle ; indispensable pour un mémoire technique lisible |
| Documents joints | PV de réception, attestation de bonne exécution, fiche d'ouvrage achevé, référence de facture | C'est la **preuve** de la référence : sans pièce, la référence reste déclarative |
| Le cas échéant — sous-traitance | Part réalisée en propre vs sous-traitée | Une commission peut vouloir savoir ce qui a été réellement exécuté par l'entreprise |

### 1.2 Vocabulaire métier à utiliser pour la « nature des travaux »

Pour que les références s'apparient correctement avec un DCE, la saisie doit s'appuyer
sur le vocabulaire du métier, pas sur des formulations vagues. Termes à prévoir (liste
non exhaustive, à compléter par Anthony) :

- **Étanchéité de toiture-terrasse** (neuve ou en réfection) ;
- **Réfection d'étanchéité** : avec ou sans dépose de l'ancien revêtement, avec ou sans
  conservation de l'existant (procédé de réfection selon DTU 43.5 — référence à vérifier,
  voir § 6 et § 10) ;
- **Relevés d'étanchéité** : remontées en périphérie, autour des émergences,
  acrotères ; c'est un poste à part, souvent oublié au chiffrage ;
- **Points singuliers** : boîtes à eau, crapaudines, joints de dilatation, pénétrations
  (ventilations, gaines), dispositifs d'évacuation des eaux pluviales ;
- **Isolation thermique rapportée** sous étanchéité (complexe isolant + étanchéité +
  protection) ;
- **Protection** : gravillon, dallettes, autoprotégé, végétalisation ;
- **Étanchéité liquide (SEL)** : balcons, terrasses de faible surface, salles d'eau ;
- **Cuvelage / étanchéité enterrée** : réservoirs, cuves, bassins, ouvrages enterrés ;
- **Étanchéité de plancher intermédiaire** (locaux humides) ;
- **Raccord d'étanchéité sur support particulier** : bois, bac acier (TAN), béton.

### 1.3 Exemples fictifs (signalés comme tels)

```
EXEMPLE FICTIF — ne correspond à aucun chantier réel
Intitulé        : Réfection de l'étanchéité — toiture-terrasse d'un groupe scolaire [fictif]
Maître d'ouvrage: [Collectivité fictive] — public
Nature          : Réfection d'étanchéité, dépose de l'existant, isolant PIR [épaisseur à
                  préciser], relevés périphériques, 4 boîtes à eau refaites
Surface         : [valeur] m² de toiture-terrasse + [valeur] ml de relevés
Montant         : [valeur] € HT (travaux seuls, hors échafaudage)
Année           : [année] — réception [année]
Durée           : [valeur] mois, exécution en site occupé pendant les vacances scolaires
Difficultés     : support béton dégradé, humidité résiduelle dans l'ancien complexe,
                  reprise des points singuliers sans aggraver la surcharge
Documents       : PV de réception, photos avant/pendant/après [à joindre]
```

Rappel : ni le nom, ni la surface, ni le montant de cet exemple ne sont réels. Le format
est donné à titre indicatif pour la saisie.

### 1.4 Pièges à signaler à la saisie

- **Surface sans définition** : « 25 » sans unité ni nature de surface n'est pas
  exploitable. Toujours préciser m² ou ml, et *surface de quoi*.
- **Montant sans assiette ni TVA** : préciser HT et ce que le montant couvre
  (travaux seuls, avec échafaudage, avec dépose/évacuation).
- **Année d'exécution vs année de réception** : ce sont deux dates distinctes ; les DCE
  raisonnent le plus souvent en ancienneté de **réception**.
- **Référence sans pièce justificative** : une référence non justifiée est un risque en
  commission ; mieux vaut la marquer « à confirmer » que la présenter comme acquise.
- **Confusion entre « j'ai le droit de concourir » et « j'ai la référence »** : la
  pré-sélection (§ 4 du projet) a besoin de références appariables, pas d'une liste
  générique de tout ce que l'entreprise a fait.

---

## 2. Certifications et qualifications propres au métier

Ces signes de qualité sont vérifiés par les maîtres d'ouvrage publics et pèsent dans
les critères. Il faut collecter le **certificat en cours de validité**, pas seulement
l'existence du signe.

### 2.1 Qualibat — qualification des entreprises du bâtiment

Qualibat est un organisme de qualification et de certification des entreprises de la
construction. Les qualifications et certifications sont organisées en **9 familles
fonctionnelles**, codées sur **4 chiffres** : 1er chiffre = famille, 2e = métier/activité,
3e = spécialité/technique, 4e = **niveau de technicité** (courante, confirmée, supérieure,
exceptionnelle, selon le libellé de la nomenclature). *(Source : nomenclature Qualibat —
voir § 10.)*

Pour l'étanchéité, la famille concernée est la **famille 3 « Enveloppe extérieure »**,
activité **32 « Étanchéité »** et **33 « Étanchéité et imperméabilisation des cuvelages,
réservoirs, cuves et bassins »**. Codes relevés dans le tableau des échelons Qualibat
(*à re-vérifier contre la nomenclature en vigueur le jour de la saisie*, les codes et
libellés évoluent) :

- **321x** — Étanchéité en matériaux bitumineux en feuilles (technicité courante /
  confirmée / supérieure selon le dernier chiffre) ;
- **322x** — Étanchéité en matériaux de synthèse en feuilles ;
- **323x** — Étanchéité en asphaltes coulés ;
- **324x** — Étanchéité liquide (S.E.L.) ;
- **327x** — Tôle d'acier nervurée (TAN) avec étanchéité en membrane en feuilles ;
- **329x** — Toitures-terrasses spécialisées (dont végétalisées) ;
- **331x / 332x / 337x** — Étanchéité et imperméabilisation de cuvelages, réservoirs,
  cuves et bassins de piscines.

À collecter pour chaque qualification détenue :

- **le code exact** (ex. `3212`) et son **libellé** tel qu'imprimé sur le certificat ;
- **le niveau de technicité** — un niveau « courante » ne couvre pas les chantiers d'un
  niveau « supérieure » ;
- les **mentions associées** lues sur le certificat (mentions de type `E.C.`, `NAT`,
  `RGE P`… dont la signification doit être reprise du document Qualibat, non interprétée) ;
- l'**organisme** émetteur, la **date de validité** (les qualifications sont datées et à
  renouveler) ;
- les **domaines de travaux** réellement couverts, tels que Qualibat les décrit — c'est ce
  qu'on oppose à l'objet du marché.

> **Ne jamais déduire une qualification du métier déclaré.** Une entreprise
> d'étanchéité peut détenir `3212` sans détenir `3241` (SEL) ni `3292` (terrasses
> végétalisées). La liste doit être lue **sur le certificat**, jamais complétée au
> raisonnement.

### 2.2 Mention RGE — « Reconnu Garant de l'Environnement »

La mention RGE identifie des professionnels reconnus pour la **rénovation énergétique**
et l'installation d'équipements utilisant des énergies renouvelables. Elle est **assise
sur une qualification ou une certification** métier et est **attribuée par domaine de
compétences**. Points utiles issus des sources publiques (§ 10) :

- délivrée par des organismes de qualification (Qualibat, Qualit'EnR, Qualifelec…) ou de
  certification (Certibat, Cerqual…) ayant convention avec l'État ;
- **durée de 4 ans**, avec un **suivi annuel** et des **audits de chantier** ;
- elle conditionne l'accès des clients à certaines **aides publiques** (MaPrimeRénov',
  CEE, éco-PTZ…).

À collecter : le **domaine de travaux** exact couvert par la mention (une mention RGE ne
vaut que pour le domaine indiqué), le **certificat**, la date d'échéance, et l'organisme.
**Ne pas confondre** la mention RGE et la qualification Qualibat « sèche » : la première
est une mention adossée à la seconde. La pertinence du RGE pour un marché d'étanchéité
**dépend de l'objet** (isolation de toiture, performance énergétique) : à vérifier au cas
par cas, la mention n'est pas systématiquement demandée.

### 2.3 MASE — management Santé-Sécurité-Environnement

Le **MASE** (« Manuel d'Amélioration Sécurité des Entreprises », aujourd'hui *Manuel
Amélioration Sécurité Santé Environnement Entreprises*) est un **référentiel français de
management SSE**, né dans l'industrie, très orienté terrain et coactivité/sous-traitance.
Il est **souvent exigé par les donneurs d'ordre industriels**, plus rarement sur un
marché de collectivité, mais il renforce un dossier. La certification est délivrée par
des **comités MASE régionaux** après audit externe. Le référentiel **V2024** est en
vigueur pour les audits depuis 2026 (calendrier de transition à vérifier — § 10).

À collecter : le **certificat** (organisme auditeur, comité régional, date d'obtention et
d'échéance), le périmètre couvert.

### 2.4 Normes ISO (management)

Les certifications de **système** (par exemple ISO 9001 qualité, ISO 14001 environnement,
ISO 45001 santé-sécurité au travail) ne sont **pas des qualifications métier** : elles
attestent d'un système de management, pas d'une compétence technique pour un type de
travaux. Utile en mémoire technique comme signal d'organisation, mais elles ne remplacent
jamais une qualification Qualibat.

À collecter : l'**organisme certificateur**, le **numéro de certificat**, le **périmètre**
et les **dates de validité**. Ne citer une norme ISO que par sa référence exacte lue sur
le certificat — jamais de mémoire.

### 2.5 Ce qu'il faut vérifier sur tout certificat ou qualification

- **Validité en cours** à la date de remise de l'offre (un certificat expiré ou en cours
  de renouvellement est un risque) ;
- **Code / intitulé / domaine** correspondant bien à l'objet du marché ;
- **Titulaire exact** : le certificat est-il au nom de l'entreprise candidate, de
  l'établissement, ou d'une entité du groupe ? (le porteur peut être l'établissement
  identifié par le SIRET) ;
- **Niveau de technicité** suffisant pour les travaux visés ;
- cohérence entre le certificat affiché et les **moyens** déclarés.

---

## 3. Assurances

Sur un marché de travaux, l'entreprise doit être en mesure de **justifier son assurance
avant l'ouverture du chantier**. Les attestations sont une pièce obligatoire quasi
systématique.

### 3.1 Garantie décennale (responsabilité décennale)

Fondement : **loi n° 78-12 du 4 janvier 1978 dite « loi Spinetta »**, codifiée
notamment aux **articles L241-1 et suivants du Code des assurances** (obligation
d'assurance du constructeur) et aux **articles 1792 et suivants du Code civil**
(responsabilité de plein droit des constructeurs). Le défaut d'assurance est pénalement
sanctionné (**article L243-3 du Code des assurances**). *(Sources : § 10 — textes
publics.)*

Ce que couvre la garantie décennale, dans son principe : pendant **10 ans à compter de la
réception**, les dommages qui **compromettent la solidité** de l'ouvrage ou le **rendent
impropre à sa destination** (pour une étanchéité : infiltrations, défaut d'étanchéité
affectant l'usage du bâtiment). Ne pas extrapoler : le détail des garanties et exclusions
est **dans le contrat d'assurance**, pas dans une fiche générique.

### 3.2 Responsabilité civile professionnelle (RC pro)

Couvre les dommages causés à des tiers dans le cadre de l'activité (avant ou après
réception, hors champ décennal). À collecter : assureur, numéro de police, période de
validité, activité déclarée, plafonds.

### 3.3 Côté maître d'ouvrage — assurance dommages-ouvrage (pour information)

L'**article L242-1 du Code des assurances** impose au **maître d'ouvrage** de souscrire
une assurance **dommages-ouvrage** avant l'ouverture du chantier. Ce n'est **pas** une
pièce de l'entreprise candidate : c'est mentionné ici pour ne pas confondre les deux
obligations lors de la lecture d'un DCE.

### 3.4 Ce qu'il faut vérifier sur une attestation d'assurance

Une attestation n'est pas un contrat. Les points à contrôler systématiquement :

- **identité de l'assureur** (compagnie identifiée) et **numéro de police / de contrat** ;
- **période de validité** couvrant les dates des travaux (attention aux attestations
  arrivant à échéance pendant le chantier) ;
- **nature de la garantie** : décennale **et/ou** RC pro — une attestation de RC générale
  ne vaut pas décennale ;
- **activités déclarées** : c'est le point le plus sensible. **Seules les activités
  nommées** sur l'attestation sont couvertes. Vérifier que l'activité exacte visée
  (étanchéité de toiture, SEL, cuvelage…) y figure nommément ;
- **zone géographique** couverte (France / région / DOM — La Réunion doit être
  explicitement couverte si l'attestation raisonne par zone) ;
- **montants de garantie / plafonds** ;
- **procédés ou techniques exclus** (certains procédés innovants ou non traditionnels
  peuvent être exclus) ;
- **titulaire** : attestation au nom de l'entreprise ou de l'établissement candidat ;
- distinguer une **attestation de garantie annuelle** d'un **certificat nominatif de
  chantier** — les maîtres d'ouvrage demandent souvent l'un ou l'autre selon le cas.

---

## 4. Moyens humains

L'objectif est de montrer que l'entreprise a **les hommes pour tenir le planning** et la
**compétence technique** pour les travaux visés.

À collecter :

- **Effectif global** et **effectif par métier** (compagnons étancheurs, aides, chefs
  d'équipe, conducteurs de travaux, préparateur/études, encadrement) ;
- **Organigramme** de chantier type : qui dirige, qui encadre, qui exécute ;
- **Profils clés** pressentis pour le marché (chef d'équipe, conducteur de travaux) et
  leur **CV** — au format qui sera exigé par le DCE ;
- **Formations et habilitations individuelles** utiles à l'étanchéité et au chantier :
  travail en hauteur, port du harnais, conduite d'engins / nacelle (CACES le cas échéant),
  sauveteur secouriste du travail, habilitations électriques pour interventions proches
  de réseaux, AIPR (autorisation d'intervention à proximité des réseaux) si réseaux
  enterrés — **les intitulés et numéros exacts sont à lire sur les attestations, non à
  déduire** ;
- **Politique d'embauche / apprentissage / intégration locale** — apprécié sur les
  marchés publics, en particulier à La Réunion (clause d'insertion fréquente : **à
  vérifier au cas par cas dans le règlement de consultation**) ;
- **Sous-traitants éventuels** et leurs qualifications, si le DCE autorise le recours.

> Les **CV sont des données personnelles**. En production, ils relèvent du RGPD et du
> cloisonnement par entreprise (`PROJECT.md` § 6). Dans ce dépôt de cadrage : **aucun CV
> nominatif**, on ne décrit que les champs.

---

## 5. Moyens matériels

À collecter, avec des critères d'usage concret (pas une simple liste d'achats) :

- **Parc roulant** utile au chantier : véhicules utilitaires, porteurs, moyens de levage
  (camion-grue, monte-charge, grue de chantier) ;
- **Échafaudages** : type, hauteur, capacité ; mode de montage (en propre ou
  sous-traitance) ; le marché impose parfois une **déclaration de conformité** de
  l'échafaudage — la référence normative à mentionner sera lue sur le document, non
  supposée ;
- **Nacelles et matériels de travail en hauteur** ;
- **Outillage spécifique à l'étanchéité** : brûleurs / chalumeaux gaz pour bitumineux,
  moulurière pour relevés, chaudière ou cuve d'asphalte pour l'asphalte coulé, machines
  de pose/marquage de membranes de synthèse (soudure à l'air chaud le cas échéant),
  équipements SEL (application liquide) ;
- **Équipements de sécurité et de stockage** : détecteurs, extincteurs, moyens de
  protection contre l'incendie (procédés au gaz), stockage des matériaux, bâchage ;
- **Matériel de contrôle et de diagnostic** : sondage d'humidité, humidimètre,
  caméra / recherche de fuite, essais d'étanchéité (mise en eau localisée) — utile pour
  prouver la capacité à diagnostiquer un support dégradé ;
- **Moyens logistiques propres au contexte insulaire** (La Réunion) : approvisionnement en
  matériaux importés, délais d'acheminement, capacité de stockage, continuité
  d'approvisionnement pendant les périodes cycloniques. Ces contraintes sont un facteur
  réel de différenciation sur les marchés locaux — **à formuler par Anthony**, non à
  généraliser ici.

À présenter de préférence sous la forme **« moyen → usage sur ce chantier → justificatif »**
(un équipement annoncé sans justificatif ne pèse pas).

---

## 6. Fiches techniques produits et procédés

L'étanchéité se prescrit **par système complet**, pas par produit isolé : élément
porteur, pare-vapeur, isolant, revêtement d'étanchéité, relevés, protection, et les
accessoires de fixation. La bibliothèque doit donc stocker des **systèmes**, avec leurs
documents.

À collecter par produit / système :

- **Fournisseur / fabricant** (et le cas échéant applicateur agréé) ;
- **Référence exacte** du produit ou du système, désignation telle qu'écrite au catalogue ;
- **Composition du système** : couches, nombre de feuilles, épaisseurs, pare-vapeur,
  fixations, protection ;
- **Documentation technique** : fiche technique du fabricant, fiche de données de
  sécurité (FDS) le cas échéant, **et pour les procédés concernés, l'avis technique** ;
- **Avis Technique (ATec) / Document Technique d'Application (DTA)** : numéro, groupe
  spécialisé, **période de validité**, procédé visé ;
- **Marquage CE** et classements / certifications produits pertinents (le cas échéant :
  réaction au feu, résistance, etc.) — lus sur les documents fournisseur ;
- **Conditions de mise en œuvre** : températures limites, support admissible, pente,
  climat (voir § 6.2) ;
- **Conditions d'emploi** : pour quel type de toiture / d'ouvrage le procédé est admis.

### 6.1 Ce qu'un avis technique autorise — et n'autorise pas

C'est un point de cadrage important, souvent mal compris :

- l'avis technique (ATec/DTA) est une **évaluation volontaire**, instruite par le CSTB
  pour le compte d'une commission (CCFAT), de l'**aptitude à l'emploi** d'un procédé
  **non traditionnel** ;
- il est **publié pour une durée limitée** (de l'ordre de quelques années selon le
  document) et il peut être **révisé, mis en observation, ou ne plus être en cours de
  validité** — d'où l'obligation, pour la bibliothèque, de stocker **la version et la
  date de validité** du document utilisé ;
- il **n'est pas un document réglementaire** et **ne confère aucun droit exclusif** ;
- il **n'exempte pas** les acteurs de fournir les justificatifs réglementaires requis
  pour l'ouvrage ; en clair, **on ne prescrit pas un procédé uniquement parce qu'il a un
  avis technique** : on vérifie que le domaine d'emploi visé par l'avis couvre bien le
  chantier (support, pente, climat, type d'ouvrage) ;
- l'existence d'un **DTA** (et non d'un ATec) correspond à un produit faisant l'objet
  d'un **marquage CE** ;
- les procédés bénéficiant d'un avis en cours de validité figurent dans la **« liste
  verte » de la C2P** (commission prévention produits de l'AQC) — utile comme contrôle,
  **à consulter à la date de la saisie** (voir § 10).

### 6.2 DTU et règles de l'art applicables à l'étanchéité

Les DTU (Documents Techniques Unifiés) encadrent la conception et la mise en œuvre des
ouvrages courants. Références de la série **DTU 43 — étanchéité des toitures**
(*liste à confirmer dans la nomenclature AFNOR en vigueur, § 10*) :

- **NF DTU 43.1** — étanchéité des toitures avec éléments porteurs en maçonnerie /
  climat de plaine ;
- **NF DTU 43.4** — toitures en éléments porteurs bois et dérivés avec revêtements
  d'étanchéité ;
- **NF DTU 43.5** — réfection des ouvrages d'étanchéité des toitures-terrasses ou
  inclinés ;
- **NF DTU 43.6** — étanchéité des planchers intérieurs en maçonnerie par produits
  hydrocarbonés ;
- **NF DTU 43.11** — étanchéité des toitures-terrasses et toitures inclinées ;
- d'autres parties (ex. **43.3**) existent selon les supports ; la liste complète et les
  numéros de norme (NF P 84-… ) sont **à vérifier** à la source, pas à reconstituer.

**Attention au contexte local (La Réunion).** Le DTU 43.1 est formulé « climat de
plaine » ; en **zone cyclonique**, les conditions de **vent** et les
**fixations / lestage** relèvent des règles de vent applicables (règles NV65 / Eurocode,
selon les prescriptions du maître d'ouvrage) et des contraintes locales. **Ne rien
affirmer ici** : ce point doit être traité avec le bureau d'études / le maître d'œuvre,
et chaque référence doit pointer vers le document exact. *(Point à confirmer, § 9.)*

---

## 7. Éléments qui font la différence sur un mémoire technique en étanchéité

Ce qui est attendu, et ce qui est souvent oublié. Cette section liste **des critères de
collecte**, pas des phrases à recopier dans un mémoire.

**Ce qu'une commission regarde :**

- des **références appariables** à l'objet du marché (même nature de travaux, même type
  d'ouvrage, maître d'ouvrage comparable) — pas une liste exhaustive de tout le parcours ;
- la **technicité des points singuliers** (relevés, boîtes à eau, joints, pénétrations),
  qui distingue une entreprise d'étanchéité d'un poseur de membranes ;
- la **capacité à traiter un support dégradé** : diagnostic, préparation, reprise,
  gestion de l'humidité résiduelle — c'est là que se joue la durabilité de l'ouvrage ;
- la **maîtrise du contexte d'exécution** : site occupé (écoles, bâtiments en
  fonctionnement), travail en hauteur, sécurité, phasage pendant les vacances ;
- la **cohérence qualification ↔ travaux** : la référence doit être couverte par une
  qualification détenue, et l'assurance doit couvrir l'activité ;
- le **planning réaliste** (durées, conditions météo, disponibilité des matériaux).

**Ce qui est souvent oublié — à collecter explicitement :**

- la **définition des surfaces** (toiture vs développée) : un métré incompris se paie ;
- les **photos des points singuliers** avant/pendant, pas seulement une vue d'ensemble ;
- les **documents de preuve** des références (PV de réception, attestations de bonne
  exécution) : une référence non justifiée est fragile ;
- la **validité à date des attestations** (assurance, qualifications) ;
- les **activités réellement déclarées** à l'assurance, en particulier pour les procédés
  à chaud (gaz) et les procédés particuliers (SEL, cuvelage, végétalisation) ;
- la **traçabilité des produits** utilisés par référence de chantier (quel système, quel
  avis technique) : permet de prouver la cohérence entre références, produits et
  qualifications ;
- le **traitement des déchets et l'évacuation** (dépose d'anciens revêtements,
  amiante éventuel dans les bâtiments anciens — **diagnostic préalable à vérifier**,
  jamais présumé) ;
- la **gestion de l'eau pendant les travaux** (mise hors d'eau, protection provisoire),
  souvent omise alors qu'elle conditionne la réussite d'une réfection en site occupé.

---

## 8. Hors de ce document

Conformément au brief du lot L5, **ne sont pas traités ici** (ni collectés, ni outillés) :

- la rédaction automatique d'un mémoire technique, les modèles de réponse type ;
- le chiffrage, les prix, les marges, la décomposition du prix ;
- la veille et la détection d'appels d'offres, le dépôt de pli, la signature
  électronique, la connexion aux plateformes d'achat public ;
- l'authentification multi-utilisateurs, le paiement, la facturation, la mise en
  production.

La **structure technique** de ces données (champs, types, relations, versionnage) est
décrite dans `docs/DATA-MODEL.md` (lot L2), qui fait foi. La **liste des pièces exigées
et mentions obligatoires** relève de `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` (lot L4).

---

## 9. Points laissés ouverts / à confirmer

À lever, dans l'ordre de priorité :

1. **Nomenclature Qualibat en vigueur** : les codes cités (§ 2.1) proviennent d'un
   tableau des échelons publié par Qualibat ; à **re-vérifier à la date de saisie**
   contre la nomenclature officielle (les codes, libellés et mentions évoluent).
2. **Signification exacte des mentions** (`E.C.`, `NAT`, `RGE P`…) : à reprendre
   **littéralement** du document Qualibat, aucune interprétation dans la bibliothèque.
3. **Liste et numéros exacts des DTU 43.x** et de leurs normes NF P 84-… : à confirmer
   auprès de la source AFNOR / CSTB avant toute citation dans un livrable produit.
4. **Règles de vent et de fixation en zone cyclonique (La Réunion)** : hors de la
   compétence de ce document ; à traiter avec le bureau d'études / le maître d'œuvre, et
   à documenter par une source exacte.
5. **Référentiel MASE** : version applicable (V2024) et calendrier d'audit — à confirmer
   auprès de l'association MASE, la date d'entrée en application ayant évolué.
6. **Seuils des DCE** (ex. « chantiers achevés depuis moins de N ans », montant minimum
   de référence, part en site occupé exigée) : **propres à chaque règlement de
   consultation** — à ne jamais fixer dans la bibliothèque, à lire au cas par cas.
7. **CV et pièces nominatives** : format attendu par les maîtres d'ouvrage et cadre RGPD
   de stockage — relève du lot L4 (conformité) et de la politique de confidentialité.
8. **Périmètre métier** : ce document est centré sur l'**étanchéité**. Si Anthony
   souhaite un outil plus large dès le départ (couverture, clos-couvre…), la liste des
   références et des qualifications devra être étendue — **décision d'Anthony**
   (question ouverte § 5 du PLAN).

---

## 10. Sources citées

Sources publiques, consultées le 30 septembre 2026. Chaque affirmation technique du
présent document doit rester rattachée à l'une de ces sources, ou être marquée
« à vérifier » (§ 9).

- **Qualibat** — nomenclature et niveaux de technicité :
  <https://www.qualibat.com/nomenclature-qualibat>
  *(et tableau des échelons publié par Qualibat : codes 32x / 33x pour l'étanchéité)*.
- **RGE — Reconnu Garant de l'Environnement** :
  Ministère de la Transition écologique,
  <https://www.ecologie.gouv.fr/politiques-publiques/label-reconnu-garant-lenvironnement-rge> ;
  Service Public Entreprendre, <https://entreprendre.service-public.gouv.fr/vosdroits/F32251>.
- **MASE** — référentiel V2024 et cadre :
  <https://mase-asso.fr/officiel-publication-referentiel-mase-v2024>.
- **Assurances construction** — loi n° 78-12 du 4 janvier 1978 (Spinetta) ; articles
  **L241-1**, **L242-1**, **L243-3** du Code des assurances ; articles **1792** et
  suivants du Code civil. Les textes consolidés font foi sur Légifrance
  (<https://www.legifrance.gouv.fr>).
- **DTU 43 — étanchéité des toitures** (liste des documents) :
  <https://www.batirama.com/rubrique-article/l-info-normes-liste-des-dtu/173-dtu-43-etancheite-des-toitures-page-1.html>
  *(liste de références ; faire foi : AFNOR / CSTB).*
- **Avis Techniques (ATec) et DTA** : CSTB,
  <https://www.cstb.fr/nos-offres/toutes-nos-offres/avis-technique> ;
  liste verte C2P (AQC) mentionnée sur cette page.

> **Rappel de méthode.** Ce document est un cadrage de phase 1. Il ne remplace ni un
> DTU, ni un avis technique, ni une attestation d'assurance, ni un règlement de
> consultation. Toute citation de norme, de seuil ou de référence dans un livrable
> produit devra être **revérifiée à la source** au moment de son usage.
