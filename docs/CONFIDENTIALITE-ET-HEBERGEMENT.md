# Confidentialité et hébergement — analyse des trois options de D6

*Rédigé par l'agent `infra` le 30 septembre 2026. Lot **L2** de la phase 2.
Référence de cadrage : `docs/DECISIONS.md` § **D6**. Plan : `docs/PLAN-PHASE-2.md`.*

**Autorité de ce document (D-C2).** C'est le **seul** document du dépôt habilité à
énoncer une garantie de confidentialité. Tout autre livrable ne peut qu'en **citer un
extrait textuel** ou écrire la mention « à compléter après validation de
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` ».

**Ce document ne tranche rien à ta place (D-C6).** Il pose les faits, rend un verdict
honnête pour chaque option et recommande. **La décision appartient à Anthony.**

**Avertissement de méthode.** Aucun prix, aucune certification et aucun engagement de
fournisseur n'est inventé ici. Chaque affirmation chiffrée porte une source et une date
de consultation (30 septembre 2026), ou la mention **« à vérifier »**. Les tarifs et les
offres des hébergeurs et des fournisseurs de modèles changent vite : **toute fourchette
de ce document doit être revérifiée avant décision.**

---

## 0. En une page — de quoi il s'agit, et le point dur

### Le problème, en clair

Le produit doit **lire** les documents du client (DCE, bilans, CV, références) pour les
analyser et pré-remplir un dossier. Or D6 demande « seul le client a accès à ses
données ». Pris au sens strict, cela veut dire que **le serveur ne peut pas déchiffrer
les documents**. Les deux ne peuvent pas être vrais en même temps sans un choix.

Il n'y a pas de contournement magique. Il y a trois familles de solutions, et chacune
paie la confidentialité d'un prix différent : soit en **expérience utilisateur**, soit en
**honnêteté de la promesse**.

### Le maillon que presque tout le monde oublie

**Héberger en France ne suffit pas.** Pour analyser un texte, il faut l'envoyer à un
modèle d'IA. Si ce modèle est servi par un prestataire américain, **le texte du DCE et
les données de l'entreprise partent aux États-Unis**, même si ton serveur est à Roubaix.
Le « chemin de la donnée » doit donc être tracé **jusqu'au fournisseur du modèle**, et
pas seulement jusqu'à l'hébergeur (§ 2).

### Les trois verdicts (le cœur du livrable)

| Option | « Seul le client a accès à ses données » | Verdict en une phrase |
|---|---|---|
| **A** — chiffrement côté client + traitement local | **Vraie par construction** | Le serveur ne reçoit jamais le clair : rien à lire, donc rien à promettre de faux. |
| **B** — chiffrement au repos + isolation côté serveur | **Fausse au sens strict** | Le serveur déchiffre pour traiter : lui, son personnel et le fournisseur du modèle peuvent techniquement lire pendant le traitement. |
| **C** — clés détenues par le client, déverrouillage à la demande | **Vraie sous conditions** (précisées § 5) | Vraie **au repos** (le serveur ne détient que du chiffré et aucune clé), fausse **pendant la fenêtre de traitement**, où le serveur et le fournisseur du modèle lisent en clair. |

**Une seule formulation est interdite partout dans le dépôt : recopier « seul le client a
accès à ses données » sans le verdict ci-dessus qui la qualifie.**

### La recommandation, en une phrase

**Option B par défaut, avec le fournisseur du modèle d'IA établi en France ou dans l'UE
(Mistral, OVHcloud AI Endpoints, ou modèle ouvert auto-hébergé)**, parce qu'elle est la
seule tenable techniquement et commercialement pour un MVP, et qu'avec un modèle
français/UE le chemin de la donnée ne sort pas de l'UE. **Option C** est une évolution
crédible au bout de quelques mois ; **Option A** est à réserver aux clients qui
l'exigent, en segment haut de gamme. Détail et coûts : § 7.

---

## 1. Le chemin réel d'une donnée, de bout en bout

Ce tableau suit **une pièce déposée par le client** (par exemple un bilan ou un CV) depuis
son poste jusqu'au fournisseur du modèle d'IA. Il décrit le cas de l'**architecture
serveur classique** (options B et C). Les différences de l'option A sont signalées après.

| # | Étape | Qui peut techniquement lire la donnée | Dans quel pays | Sous quel contrat / cadre |
|---|---|---|---|---|
| 1 | **Poste du client** (navigateur, dépôt du fichier) | Le client. Personne d'autre. | Poste du client | — |
| 2 | **Transport** (HTTPS/TLS entre navigateur et serveur) | Le client et le serveur. Un intermédiaire réseau ne lit pas (chiffré en transit). | Transit UE | TLS. Hébergeur = sous-traitant (art. 28 RGPD). |
| 3 | **Serveur applicatif** (mémoire, pendant le traitement) | L'éditeur (Anthony), ses éventuels prestataires de maintenance, l'hébergeur en cas d'accès physique ou administrateur. **La donnée y est en clair pour être traitée.** | France (voir § 3 pour les régions) | Contrat d'hébergement + DPA. **Point dur : c'est ici que « seul le client » devient faux en options B et C.** |
| 4 | **Stockage persistant** (base de données, fichiers) | Le serveur ; l'hébergeur si le chiffrement est géré par lui ; **pas le client seul** en option B. En option C : le serveur écrit du chiffré, la clé n'est pas chez lui. | France | Chiffrement au repos (§ 4). |
| 5 | **Sauvegardes** | Le serveur ; l'hébergeur. En option C : uniquement du chiffré (à condition de sauvegarder les données déjà chiffrées, jamais le clair). | France | Doivent être **chiffrées** et dans la même région. |
| 6 | **Journaux techniques** (logs applicatifs, erreurs, mesures) | L'éditeur, l'hébergeur, et tout outil de supervision utilisé. **Risque : ne doivent jamais contenir le contenu des documents.** | France, sauf outils tiers | Règle : logs sans contenu de document. |
| 7 | **Fournisseur du modèle d'IA** (l'appel API d'analyse) | **Le fournisseur lui-même et sa chaîne de sous-traitants.** C'est le maillon le plus souvent oublié. | **Dépend du fournisseur** : France (Mistral, OVHcloud AI Endpoints, Scaleway) / UE / États-Unis (OpenAI, Anthropic par défaut) | DPA + clauses de non-entraînement + (idéalement) rétention zéro. § 2. |
| 8 | **Sauvegardes et sous-traitants du fournisseur de modèle** | Les sous-traitants listés par ce fournisseur (Trust Center / liste de sous-traitants). | Variable — à lire dans le Trust Center du fournisseur. | À documenter dans le registre RGPD. |

**Deux enseignements de ce tableau :**

1. Le serveur (donc **l'éditeur et son personnel technique**) peut lire les documents
   **pendant le traitement** en options B et C. Ce n'est pas une hypothèse : c'est la
   conséquence directe de « lire le document pour l'analyser ».
2. Si l'étape 7 sort de l'UE, alors **« les données sont hébergées en France » est un
   euphémisme** : les serveurs sont en France, mais le **document**, lui, est allé
   ailleurs. C'est le point que D6 ne voit pas encore.

### Ce que change l'option A dans ce tableau

En option A, les étapes 3, 4, 5, 6 et 7 côté serveur **disparaissent** pour les
documents : l'analyse tourne **sur le poste du client**. Le serveur ne reçoit que ce que
le client décide d'y déposer (typiquement le dossier final, ou rien). Le tableau
s'arrête donc à l'étape 1. Voir § 4.

---

## 2. Le maillon oublié : le fournisseur du modèle d'IA

Analyser un DCE, c'est envoyer son texte à un modèle de langage. **Ce texte sort du
serveur.** Le choix du fournisseur de modèle est donc **aussi structurant que le choix de
l'hébergeur** pour D6.

### Les familles de fournisseurs, du plus protecteur au plus risqué

| Famille | Exemple | Où va la donnée | Entraînement | Rétention | Verdict « hébergé en France » |
|---|---|---|---|---|---|
| **Modèle ouvert auto-hébergé** | Mistral Small / Qwen / Llama auto-hébergés sur ton serveur français | **Nulle part : reste sur ton serveur** | Non (tu contrôles) | À toi de définir | **Vrai par construction.** Le plus protecteur, mais demande des compétences et du matériel. |
| **Fournisseur français** | Mistral AI (API), OVHcloud AI Endpoints, Scaleway Generative APIs | France / UE | Non (plans payants) | Rétention zéro possible (à activer, voir ci-dessous) | **Vrai**, à condition de ne pas cocher l'endpoint américain quand il existe. |
| **Fournisseur UE** | Azure OpenAI / Vertex AI avec modèles en région UE | UE (région choisie) | Non par défaut | Selon plateforme | **Vrai côté région**, mais la société mère peut être hors UE (voir ci-dessous). |
| **Fournisseur hors UE, résidence UE activée** | OpenAI « Europe » (nouveau projet) | UE pour le stockage/traitement | Non (API) | Résidence UE + rétention zéro sur les requêtes concernées | **Vrai côté données**, mais **pas au sens juridique absolu** : société de droit américain, exposition résiduelle au CLOUD Act. |
| **Fournisseur hors UE, par défaut** | OpenAI / Anthropic sans option UE, API directe | **États-Unis** | Non (API commerciale) | 30 jours par défaut | **Faux.** Le texte part aux États-Unis. |

### Faits sourcés sur les principaux fournisseurs

À reformuler pour un non-spécialiste, mais **chiffres et engagements à citer tels quels**.

**Mistral AI (France)** — *source : help.mistral.ai (pages « Où stockez-vous mes
données », « Puis-je activer le ZDR ») et docs.mistral.ai, consultées le 30 septembre
2026 ; Trust Center à vérifier.*
- Par défaut, les données sont hébergées dans l'**Union européenne** ; un **endpoint
  américain existe** et ne doit donc **pas** être utilisé (c'est un choix explicite de
  l'intégrateur).
- Certaines fonctions peuvent transférer temporairement hors UE vers des sous-traitants
  listés au Trust Center ; les contrats incluent les garanties de l'article 46 RGPD.
- Rétention zéro (**ZDR**) disponible sur l'offre payante « Scale » pour les appels
  **sans état** (`/v1/chat/completions`, embeddings, OCR…). **ZDR ne couvre pas** l'API
  Fichiers, les traitements par lots, les conversations : autrement dit, **il ne faut pas
  téléverser les documents dans l'API Fichiers** si l'on veut tenir la rétention zéro.
- ZDR et « pas d'entraînement » sont **deux réglages distincts** : il faut activer les
  deux.
- Tarifs publics indicatifs (à revérifier) : Mistral Small 4 ≈ 0,15 / 0,60 $ par million
  de tokens (entrée/sortie), Mistral Medium 3.5 ≈ 1,50 / 7,50 $, Mistral Large 3
  ≈ 0,50 / 1,50 $. *Source : pages de tarifs Mistral, consultées le 30 septembre 2026.*

**OVHcloud AI Endpoints (France)** — *source : pages OVHcloud AI Endpoints (catalogue
public), consultées le 30 septembre 2026 ; politique de données à vérifier sur la page
officielle.*
- Modèles à **poids ouverts** servis **depuis la France (Gravelines)**, facturation en
  euros, prix publics à partir d'environ **0,04 €/million de tokens en entrée**.
- OVHcloud indique que **les données client ne servent pas à entraîner les modèles**
  (engagement à vérifier sur la page officielle au moment de la souscription).
- Modèles disponibles : Llama, Mistral (Small, Codestral), Qwen, gpt-oss, entre autres.
  **Pas** les derniers modèles propriétaires américains.

**Scaleway Generative APIs (France)** — *source : pages Scaleway Generative APIs,
consultées le 30 septembre 2026.*
- Modèles servis dans des **centres de données européens** (Paris, Amsterdam, Varsovie,
  Milan), facturation au million de tokens, franc de sortie (egress) nul.

**OpenAI — résidence européenne** — *source : openai.com « Introducing data residency in
Europe », et documentation « Data controls in the OpenAI platform », consultées le
30 septembre 2026.*
- Clients éligibles : créer un **nouveau projet** en région **Europe** ; les requêtes sont
  traitées **en région**, avec **rétention zéro** (requêtes/réponses non stockées au
  repos). Un projet existant **ne peut pas** être converti.
- L'accès à une région hors États-Unis exige **l'approbation des contrôles de
  surveillance des abus** et un **avenant de rétention zéro** : ce n'est pas une case à
  cocher, c'est un contrat.
- Par défaut (sans cette option) : **30 jours** de journaux de surveillance des abus, et
  **pas d'entraînement** sur les données d'API depuis le 1er mars 2023.
- Une **majoration de prix** s'applique sur les régions de résidence pour les modèles
  sortis à partir du 5 mars 2026 : *chiffre à vérifier sur la page officielle*.

**Anthropic (Claude)** — *source : platform.claude.com « API and data retention » et
privacy.claude.com, consultées le 30 septembre 2026.*
- **L'API directe d'Anthropic n'offre pas de résidence UE** : par défaut, les données
  commerciales stockées restent **aux États-Unis**.
- Rétention standard : suppression sous **30 jours** ; **ZDR sur demande** (par
  organisation), mais Anthropic peut conserver des données signalées par ses systèmes de
  sécurité jusqu'à **2 ans**.
- Pour une résidence UE, il faut passer par **AWS Bedrock** (`eu-west-3` Paris,
  `eu-central-1` Francfort, `eu-west-1` Irlande) ou **Google Vertex AI** en région UE —
  et c'est alors le **contrat de la plateforme cloud** qui s'applique, pas celui
  d'Anthropic.

**Conclusion de cette section — à écrire noir sur blanc :** si le fournisseur du modèle
n'est pas français ou européen, alors **« hébergé en France » ne décrit que le serveur,
pas la donnée**. Le DCE et les données de l'entreprise sont transmis à un prestataire
étranger à chaque analyse. C'est exactement le risque identifié dans `docs/PLAN-PHASE-2.md`
(« sous-traitant du modèle d'IA hors UE »). **C'est une décision d'Anthony (question 2),
pas une décision technique.**

---

## 3. Hébergement en France : ce qu'il faut nommer précisément

« Hébergé en France » n'est pas une case à cocher : c'est un choix de **région**. Voici
les régions françaises des fournisseurs cités par D6 et le plan.

| Fournisseur | Régions France (codes) | Remarque |
|---|---|---|
| **OVHcloud** | `eu-west-par` (Paris, 3 zones de disponibilité), `eu-west-gra` (Gravelines), `eu-west-rbx` (Roubaix), `eu-west-sbg` (Strasbourg) | *Source : page « Infrastructure locations by region » d'OVHcloud, consultée le 30 septembre 2026.* Les offres **SecNumCloud** sont hébergées à **Roubaix, Gravelines et Strasbourg**. |
| **Scaleway** | `fr-par-1`, `fr-par-2`, `fr-par-3` (Paris) | *Source : pages Scaleway, consultées le 30 septembre 2026.* Autres régions : Amsterdam, Varsovie, Milan — toutes UE, mais **hors France**. |
| **OVHcloud AI Endpoints** | Servis depuis la **France (Gravelines)** | *À vérifier au moment de la souscription.* |

**Attention aux pièges :**
- Un hébergeur peut proposer des régions **hors France** (Francfort, Amsterdam, Milan) :
  la même offre, mal configurée, sort de France. La région doit être **choisie
  explicitement** et **vérifiée**.
- Les **sauvegardes** et la **réplication** suivent la région : une sauvegarde mal
  placée annule le bénéfice de l'hébergement en France.
- **SecNumCloud** (qualification ANSSI) est le niveau le plus élevé pour l'hébergement
  français : OVHcloud est qualifié sur certaines offres (Bare Metal Pod, VMware on
  OVHcloud, *source : pages SecNumCloud d'OVHcloud, consultées le 30 septembre 2026*) ;
  Scaleway est **HDS** et **en cours** de qualification SecNumCloud, **pas encore
  qualifié** (*source : page SecNumCloud de Scaleway, consultée le 30 septembre 2026*).
  Ce niveau n'est pas nécessaire pour ce produit aujourd'hui, mais il faut savoir qu'il
  existe et qu'il est plus cher (**sur devis**).

---

## 4. Option A — chiffrement côté client + traitement local

### Comment ça marche (5 lignes, sans jargon)

Les documents ne sont **jamais envoyés** à un serveur. Le client ouvre le site, mais
l'analyse tourne **sur son propre ordinateur** : soit dans le navigateur (des modèles
d'IA peuvent tourner directement dans la page, via WebGPU/WebAssembly — c'est le
principe de projets comme WebLLM, *source : article arXiv 2412.15803, consulté le
30 septembre 2026*), soit dans un petit logiciel installé. Les données restent sur le
disque du client, chiffrées par une clé que seul le client possède. Le serveur, s'il
existe, ne sert qu'à distribuer le logiciel et, si le client le décide, à synchroniser le
dossier final.

### Ce que ça garantit vraiment

- **Le serveur ne voit jamais les documents en clair.** C'est vrai **par construction** :
  il n'y a aucune étape où le clair transite. Ce n'est pas une promesse commerciale, c'est
  une propriété de l'architecture.
- Aucun transfert vers un fournisseur de modèle : **rien ne sort du poste** (dans la
  variante « aucun appel réseau »).
- Le cloisonnement entre clients est **trivial** : il n'y a pas de données côté serveur à
  cloisonner.

### Ce que ça ne garantit pas

- **Le poste du client doit être sûr.** Un ordinateur infecté, un navigateur piégé, un
  cloud personnel mal configuré : la donnée fuit par le poste, pas par le serveur.
- **L'éditeur contrôle le code exécuté sur le poste.** Un éditeur de mauvaise foi
  pourrait en théorie publier une version qui exfiltre. C'est une **fraude**, détectable
  et attaquable — pas une faille de l'architecture, mais ce n'est pas « par construction
  impossible » au sens absolu. À écrire honnêtement.
- **Qualité d'analyse plus faible.** Les modèles qui tournent sur un ordinateur portable
  sont plus petits que les modèles serveur : l'extraction d'un DCE complexe sera moins
  fine.
- **Expérience utilisateur dégradée.** Premier chargement long (téléchargement du
  modèle), dépendance à la machine du client (GPU, mémoire), pas de traitement en
  arrière-plan, pas d'usage multi-appareils simple.

### Verdict

> **« Seul le client a accès à ses données » : VRAIE PAR CONSTRUCTION.**

C'est la seule des trois options où la phrase est vraie sans qualificatif technique.
Réserve à mentionner : elle suppose que le poste du client est sain et que l'éditeur est
honnête. Ces deux réserves ne sont pas propres à l'option A, mais elles y remplacent
celles du serveur.

---

## 5. Option B — chiffrement au repos + isolation stricte côté serveur

### Comment ça marche (5 lignes, sans jargon)

C'est un service web classique. Le client envoie ses documents au serveur ; le serveur
les **chiffre sur le disque** (chiffrement « au repos ») et range chaque client dans un
espace séparé, étanche. Mais le serveur **détient la clé** : quand une analyse doit être
faite, il déchiffre, traite, puis re-chiffre. C'est ce que font la **majorité des SaaS**.
La confidentialité repose donc sur des **engagements** (contrats, procédures, accès
restreints) et non sur une impossibilité technique.

### Ce que ça garantit vraiment

- **Volume volé ou disque récupéré : illisible.** Le chiffrement au repos protège contre
  le vol de matériel ou de sauvegarde.
- **Cloisonnement réel entre clients** s'il est bien fait : séparation des données, des
  fichiers, des identités d'accès (§ 6). Un client ne voit pas les données d'un autre.
- **Simplicité et coût maîtrisés** : c'est le modèle d'exploitation le moins cher et le
  plus rapide à mettre en œuvre.

### Ce que ça ne garantit pas

- **Le serveur, son personnel et l'éditeur peuvent lire les documents pendant le
  traitement.** C'est mécanique : pour lire un DCE, le serveur doit le déchiffrer.
- **Le fournisseur du modèle d'IA les lit aussi**, sauf s'il est auto-hébergé sur le même
  serveur (§ 2).
- Les engagements « pas d'accès humain », « pas d'entraînement », « pas de conservation »
  sont **contractuels**, pas structurels : ils engagent la responsabilité du prestataire
  s'il les viole, ils ne l'empêchent pas techniquement.

### Verdict

> **« Seul le client a accès à ses données » : FAUSSE AU SENS STRICT.**

L'écrire tel quel serait **une promesse intenable**, exactement le risque identifié par
D6 et par le plan de phase 2. La formulation honnête doit dire que le serveur et son
prestataire peuvent techniquement accéder aux documents pendant le traitement (§ 9).

---

## 6. Option C — clés détenues par le client, déverrouillage à la demande

### Comment ça marche (5 lignes, sans jargon)

Le client garde la clé. Ses documents sont stockés **chiffrés** chez le serveur, qui ne
possède pas la clé. Quand le client lance une analyse, il **déverrouille** : une clé de
session est transmise au serveur **le temps du traitement**, puis oubliée. Le serveur ne
stocke jamais la clé. C'est le compromis intermédiaire entre A et B : la donnée au repos
est vraiment illisible par le serveur, mais pendant la fenêtre de traitement, le serveur
(et le fournisseur du modèle) voit le clair.

### Ce que ça garantit vraiment

- **Au repos : le serveur ne peut pas lire.** Disque, sauvegardes, base de données : le
  serveur ne détient que du chiffré et **aucune clé**. C'est une garantie
  **structurelle** au repos, pas une promesse.
- **Une fuite de la base ou des sauvegardes ne livre rien** à un attaquant qui ne détient
  pas la clé du client.
- **La fenêtre de traitement est bornée** : une fois le traitement fini, le serveur a
  oublié la clé.

### Ce que ça ne garantit pas

- **Pendant la fenêtre de traitement, le serveur lit en clair.** Et le fournisseur du
  modèle aussi. « Seul le client » n'est donc vrai que **hors traitement**.
- **La sécurité dépend du poste du client** pour la garde de la clé (perte de clé = perte
  des données, sauf procédure de récupération — qui est elle-même un risque).
- **Complexité de mise en œuvre** : gestion des clés, déverrouillage, récupération,
  facturation de la fenêtre. Plus de code, donc plus de bugs possibles.

### Verdict

> **« Seul le client a accès à ses données » : VRAIE SOUS CONDITIONS.**
>
> Les conditions, précisément :
> 1. **Hors fenêtre de traitement** : le serveur ne détient que du chiffré et aucune clé
>    — la phrase est vraie, structurellement.
> 2. **Pendant la fenêtre de traitement** : le serveur et le fournisseur du modèle lisent
>    le clair — la phrase est **fausse** à cet instant.
> 3. **Aucune clé n'est conservée** après la fenêtre (à vérifier par audit et par revue
>    de code, L6).
> 4. **Les sauvegardes ne contiennent que du chiffré** (jamais de clair, jamais de clé).
>
> Dit autrement : la phrase est vraie **pour les données au repos**, fausse **pendant le
> traitement**. La formulation publique doit énoncer cette limite.

---

## 7. Tableau comparatif des trois options

Fourchettes de coût **en ordre de grandeur**, prix publics consultés le 30 septembre 2026,
**à revérifier avant décision**. Le coût du modèle d'IA dépend du **volume de tokens**,
qui est une inconnue (question 3).

| Critère | **Option A** (local) | **Option B** (serveur, clé serveur) | **Option C** (serveur, clé client) |
|---|---|---|---|
| **Confidentialité réellement garantie** | Maximale : rien ne quitte le poste. | Chiffré au repos + cloisonnement ; le serveur lit pendant le traitement. | Chiffré au repos sans clé serveur ; le serveur lit pendant le traitement. |
| **Faisabilité (MVP)** | Difficile : modèle dans le navigateur ou logiciel installé, support client lourd. | **Facile** : architecture SaaS standard, maîtrisée. | Moyenne : gestion de clés à concevoir. |
| **Coût d'exploitation mensuel (fourchette)** | Faible côté serveur (≈ 0 à 15 €/mois HT) ; pas de coût de modèle, mais **coût de développement et de support élevé**. | Serveur France ≈ 7 à 45 €/mois HT (VPS OVHcloud VPS-1 6,49 € / VPS-2 9,99 € ; Scaleway DEV1-S ≈ 6,55 €, PRO2-XXS ≈ 40,95 €, hors IPv4 ≈ 2,92 € et stockage ≈ 0,095 €/GB — *sources consultées le 30 septembre 2026, à revérifier*) **+ modèle** ≈ 1 à 50 €/mois selon volume et fournisseur. | Idem B, **majoré** de la complexité de gestion des clés (temps de développement, pas de coût mensuel fixe supplémentaire connu). |
| **Impact expérience utilisateur** | Fort : premier chargement long, dépend de la machine, pas de multi-appareils simple. | **Faible** : usage web normal. | Moyen : étape de déverrouillage à chaque analyse. |
| **Impact qualité d'analyse IA** | Plus faible : modèles plus petits sur poste client. | **Meilleure** : accès aux modèles serveur les plus capables. | Meilleure (comme B). |
| **Dépendance à un prestataire** | Faible (mais dépendance au matériel du client). | Moyenne à forte : hébergeur **et** fournisseur du modèle. | Moyenne à forte (idem B). |
| **Complexité de mise en œuvre** | Élevée (client riche, distribution, mises à jour). | **Faible à moyenne**. | Moyenne à élevée (gestion des clés). |

**Coût mensuel total, en fourchette (démarrage, un à quelques clients) :** entre
**≈ 15 €/mois HT** (VPS France + modèle ouvert servi en France, faible volume) et
**≈ 150 €/mois HT** (instance plus confortable + modèle propriétaire européen + volume
notable + stockage et sauvegardes). Les offres **SecNumCloud** sont nettement au-dessus
(**sur devis, à vérifier**). Ces fourchettes **ne remplacent pas** un budget cible : sans
la réponse à la question 3, elles restent indicatives.

---

## 8. Les contraintes fermes de D6, tenues ou non, par option

D6 fixe quatre contraintes fermes. Voici ce qu'il en est pour chaque option — sans
maquillage.

### 8.1 Hébergement en France

| Option | Tenue ? |
|---|---|
| **A** | **Sans objet ou vraie** : il n'y a pas de données hébergées. Si un serveur sert le synchronisation, il doit être en région française (à vérifier). |
| **B** | **Vraie si la région est choisie** : OVHcloud `eu-west-par` / `eu-west-gra` / `eu-west-rbx` / `eu-west-sbg`, ou Scaleway `fr-par-1/2/3`. **Fausse** si l'offre atterrit à Francfort, Amsterdam ou Milan. Sauvegardes et réplication doivent suivre. |
| **C** | Idem B. |

**Rappel : cette contrainte ne couvre que le serveur.** Le fournisseur du modèle est un
autre maillon (§ 2) : héberger à Roubaix et appeler un modèle américain **contredit
l'esprit de D6**.

### 8.2 Chiffrement au repos

| Option | Quoi est chiffré | Où sont les clés | Qui y accède |
|---|---|---|---|
| **A** | Tout, sur le poste du client. | Chez le client. | Le client seul. |
| **B** | Base, fichiers, sauvegardes. | **Chez le serveur / l'hébergeur.** | Le serveur, l'hébergeur, l'éditeur. |
| **C** | Base, fichiers, sauvegardes. | **Chez le client**, clé de session non conservée. | Le client ; le serveur pendant la fenêtre de traitement seulement. |

**Point technique à ne pas oublier :** si le chiffrement est **géré par l'hébergeur**
(chiffrement managé), c'est **lui** qui détient la clé — ce qui est acceptable, mais doit
être écrit. Certains hébergeurs proposent un chiffrement de disque matériel type LUKS
(OVHcloud le propose sur certaines régions France : RBX, SBG, GRA, EU-WEST-PAR —
*source : documentation OVHcloud Managed Kubernetes, consultée le 30 septembre 2026 ;
disponibilité exacte à vérifier par offre*).

### 8.3 Cloisonnement strict entre clients

Le mécanisme doit être **décrit**, pas seulement promis. Trois niveaux à empiler :

1. **Séparation des données** : chaque enregistrement porte un identifiant de client ;
   **toute requête est filtrée par cet identifiant au niveau le plus bas** (règles de
   sécurité au niveau des lignes si le SGBD le permet), pas dans le code applicatif seul.
2. **Séparation des fichiers** : espaces de stockage distincts (préfixes/buckets par
   client), jamais de fichier partagé entre clients.
3. **Séparation des accès** : identités techniques par client pour les traitements, aucun
   compte d'administration partagé entre clients, journalisation des accès.
4. **Test du cloisonnement** : une vérification concrète qui tente d'accéder aux données
   d'un client depuis le compte d'un autre et doit échouer — c'est le rôle de **L6**
   (`docs/REVUE-SECURITE.md`).

| Option | Cloisonnement |
|---|---|
| **A** | Trivial : il n'y a pas de données serveur multi-clients à cloisonner. |
| **B** | **À construire**, faisable, à prouver par test. |
| **C** | Idem B, plus la séparation des clés par client. |

### 8.4 Aucune donnée client dans l'entraînement d'un modèle

Ce n'est **jamais vrai par défaut sur toute la chaîne** : c'est une **exigence
contractuelle** à obtenir de chaque prestataire. Ce qu'il faut exiger :

- **un accord de traitement (DPA)** conforme à l'article 28 RGPD, signé avec chaque
  sous-traitant (hébergeur, fournisseur de modèle) ;
- une **clause de non-entraînement** explicite : « les données client ne sont pas
  utilisées pour entraîner, affiner ou améliorer des modèles » ;
- une **rétention zéro** (ZDR) ou une durée de conservation minimale et documentée ;
- l'**interdiction d'accès humain** aux contenus de traitement, ou sa limitation
  documentée ;
- la **liste des sous-traitants ultérieurs** (Trust Center) et l'information en cas de
  changement.

Faits utiles : OpenAI ne s'entraîne **pas** sur les données d'API depuis le 1er mars 2023 ;
Anthropic ne s'entraîne pas sur les données commerciales ; Mistral s'engage à ne pas
s'entraîner sur les données client des **offres payantes** (sources consultées le
30 septembre 2026, à revérifier au contrat). **Attention** : « pas d'entraînement » ne
veut pas dire « pas de conservation » — ce sont deux réglages distincts, et il faut
exiger les deux.

| Option | Tenue ? |
|---|---|
| **A** | **Vraie par construction** si aucun appel réseau n'est fait. |
| **B et C** | **Vraie sous conditions contractuelles** ; **fausse** en pratique si le fournisseur de modèle n'est pas encadré. |

---

## 9. Recommandation argumentée — décision demandée à Anthony

### La recommandation

**Retenir l'option B comme base du MVP — chiffrement au repos et cloisonnement strict
côté serveur — avec trois ajouts non négociables :**

1. **Serveur en région française** explicitement choisie (OVHcloud `eu-west-par` /
   `eu-west-gra`, ou Scaleway `fr-par-1`), sauvegardes incluses.
2. **Fournisseur du modèle d'IA établi en France ou dans l'UE** : Mistral AI, OVHcloud
   AI Endpoints, ou un modèle ouvert auto-hébergé sur le même serveur. **C'est le point
   qui rend « hébergé en France » vrai de bout en bout.**
3. **Formulation publique honnête** (§ 9.2), qui dit que le serveur peut lire pendant le
   traitement.

**Et tracer dès maintenant une trajectoire vers l'option C**, à ouvrir quand le produit
aura des clients qui la demandent — ce qui est probable dans le bâtiment, où les bilans et
les CV sont sensibles.

**Réserver l'option A** aux clients qui l'exigent formellement, en segment haut de gamme,
ou comme évolution d'une partie du produit (par exemple l'analyse locale des pièces les
plus sensibles : bilan, IBAN, CV), tandis que le DCE — document public — resterait
analysé côté serveur.

### Pourquoi ce choix

- **C'est la seule option tenable pour un MVP.** L'option A est la plus protectrice mais
  la plus chère en développement et la plus fragile en expérience utilisateur : elle
  ferait échouer l'adoption avant même de tester la valeur du produit.
- **Avec un modèle français/UE, la donnée ne sort pas de l'UE**, et l'honnêteté de la
  formulation reste compatible avec une promesse forte : « vos documents sont hébergés en
  France et ne partent nulle part hors de l'UE ».
- **L'option C n'apporte rien de plus que B pendant la fenêtre de traitement** (les deux
  lisent en clair à ce moment-là), mais coûte plus cher à construire. Elle devient
  intéressante quand le client veut une garantie au repos démontrable — ce qui est un
  argument commercial fort, pas un prérequis du MVP.

### Ce que ça coûte

- **Direct :** entre ≈ 15 € et ≈ 150 €/mois HT (§ 7), hors budget cible connu (question 3).
- **Indirect :** il faudra **écrire** dans la communication que le serveur peut lire
  pendant le traitement. C'est un coût commercial, réel, à assumer.
- **Non tenable :** promettre « seul le client a accès » en option B. Si Anthony veut
  garder cette phrase, il faut choisir l'option **A** — et en accepter le prix.

### Décision demandée (à trancher par Anthony)

1. **Quelle option retenir : A, B ou C ?** La recommandation est **B**, avec un modèle
   français/UE, et une trajectoire vers C.
2. **Acceptes-tu la formulation honnête** (§ 9.2) si l'option B ou C est retenue ?
3. **Acceptes-tu qu'un fournisseur de modèle hors UE reçoive les documents** (question 2
   du plan), ou imposes-tu un fournisseur européen ou français ?
4. **Quel budget mensuel cible** (hébergement + consommation du modèle) ?
5. **Quelle entité** portera le contrat (responsable de traitement RGPD) ?

---

## 10. Formulation publique honnête (prête à recopier)

### Si les options B ou C sont retenues (formulation recommandée)

> « Vos documents sont **hébergés en France**, chiffrés au repos et cloisonnés : aucun
> autre client ne peut y accéder. Pour analyser un DCE et pré-remplir votre dossier,
> notre service — et le fournisseur du modèle d'IA qu'il utilise, établi en France ou dans
> l'Union européenne — doivent lire vos documents **pendant le traitement**. Ils ne les
> conservent pas au-delà, ne les utilisent jamais pour entraîner un modèle, et n'y
> accèdent pas en dehors du traitement. Vous pouvez demander à tout moment l'export ou la
> suppression de vos données. »

*Variante courte (3 phrases) :*
> « Vos documents sont hébergés en France, chiffrés et cloisonnés : aucun autre client n'y
> a accès. Pour analyser votre DCE, notre service et son fournisseur de modèle d'IA —
> établis en France ou dans l'UE — lisent vos documents pendant le traitement
> uniquement, sans les conserver ni les utiliser pour entraîner un modèle. Vous gardez la
> main : export et suppression à la demande. »

### Si l'option A est retenue

> « Vos documents ne quittent jamais votre ordinateur. L'analyse est réalisée localement,
> sur votre poste ; aucun document n'est envoyé à nos serveurs. »

### Si l'option B est retenue **sans** contraindre le fournisseur de modèle

> Ne pas écrire de formulation. Ce cas contredit D6 et doit être rouvert comme décision.

### Ce qu'il est interdit d'écrire (liste à opposer à toute relecture)

- « **Seul le client a accès à ses données** » — **sans** le verdict qui la qualifie.
  Interdit en options B et C, et dans tout document autre que celui-ci (D-C2).
- « Vos données ne quittent jamais la France » — faux si le fournisseur du modèle est
  hors UE.
- « Aucun humain ne peut lire vos documents » — faux en options B et C.
- « 100 % confidentiel », « sécurité absolue », « inviolable » — aucune architecture ne
  le garantit.
- « Conforme RGPD » présenté comme une **garantie** : la conformité est une démarche, pas
  un label que l'éditeur peut s'attribuer seul.
- « Certifié SecNumCloud » si l'offre retenue ne l'est pas.
- Toute mention d'une **certification**, d'un **prix** ou d'un **engagement de
  fournisseur** non sourcé et non daté.
- Toute référence, tout chiffre ou tout engagement que l'IA aurait « inventé » (ligne
  rouge du projet).

---

## 11. Note RGPD courte et factuelle

*Faits seulement. La validation juridique relève de **D4** (juriste, fin de projet). La
revue de sécurité détaillée est faite par **L6** (`docs/REVUE-SECURITE.md`, agent `qa`) :
ce document lui fournit la matière.*

- **Responsable de traitement** : l'entité qui porte le produit et facture — **à
  trancher** (question 4 du plan). Personne physique ou société en cours de constitution,
  cela change le registre et les mentions. *Ne pas trancher ici.*
- **Sous-traitants (art. 28 RGPD)** à contractualiser : l'**hébergeur** (OVHcloud ou
  Scaleway), le **fournisseur du modèle d'IA**, l'**outil de supervision/erreurs** s'il est
  utilisé, et le cas échéant le service d'**envoi d'e-mails**. Chacun doit avoir un DPA.
- **Transferts hors UE** : à éviter. Avec un fournisseur de modèle **français ou UE**,
  aucun transfert n'est identifié à ce stade. Avec **OpenAI (résidence Europe)** ou
  **Anthropic via Bedrock/Vertex UE**, les données restent en UE mais la société mère est
  hors UE : risque extraterritorial résiduel (CLOUD Act), à documenter dans l'analyse
  d'impact. Avec un fournisseur **sans option UE**, le transfert est **caractérisé**.
- **Catégories de données** : données d'entreprise (bilans, SIRET, coordonnées bancaires
  IBAN) et **données personnelles** (CV nominatifs, représentant légal, salariés). Les
  coordonnées bancaires et les données de dirigeants appellent une vigilance particulière ;
  aucune donnée sensible au sens de l'article 9 n'est attendue, mais l'IA ne doit pas en
  recevoir par accident (règle de minimisation).
- **Durée de conservation** : **à trancher** (question 8 du plan, juriste). À prévoir dès
  le modèle de données : durée de vie de la bibliothèque, des dossiers, des journaux, et
  **sort des données à la résiliation** (export puis suppression).
- **Analyse d'impact (AIPD)** : probablement nécessaire, compte tenu du volume de
  données personnelles (CV) et de l'usage d'une IA. À confirmer par le juriste.
- **Information des personnes** : les CV des salariés du client sont des données
  personnelles traitées par l'éditeur pour le compte du client — l'information des
  salariés relève du client en tant que responsable de traitement de ses propres salariés.
  Point à clarifier avec le juriste.

---

## 12. Inconnues bloquantes et ce qu'elles changent

| Inconnue | Ce qu'elle change | Statut |
|---|---|---|
| **Option retenue (A/B/C)** | Le verdict sur la phrase, la formulation publique, le modèle de données, la complexité de mise en œuvre. | Bloque la validation de la phase 2 (question 1). |
| **Fournisseur du modèle d'IA** (UE ou hors UE) | La vérité de « hébergé en France », l'existence d'un transfert hors UE, le registre RGPD, le coût. | Bloque la validation (question 2). **Aussi structurant que le chiffrement.** |
| **Budget mensuel cible** | La crédibilité des fourchettes de coût ; le choix entre modèle ouvert servi en France et modèle propriétaire. | Bloque la validation (question 3). |
| **Volume de données attendu** (nombre de clients, dossiers par mois, taille des DCE) | Le coût réel du modèle d'IA (facturé au token) ; le dimensionnement du serveur et du stockage. | Bloque la validation. |
| **Entité qui porte le contrat** | Responsable de traitement RGPD, mentions légales, facturation (D3). | Bloque la validation (question 4). |
| **Durée de conservation et sort des données à la résiliation** | Le modèle de données (champ à prévoir) et le registre. | Bloque la phase 3 (question 8). |

**Ces inconnues ne bloquent pas l'écriture de ce document** : elles bloquent la
**validation de la phase 2**. Les lots L3 (`docs/DATA-MODEL-V2.md`) et L6
(`docs/REVUE-SECURITE.md`) peuvent avancer en s'appuyant sur les trois options posées ici,
conformément à D-C6.

---

## 13. Sources consultées (30 septembre 2026)

Toutes les sources ci-dessous ont été consultées le **30 septembre 2026** depuis ce poste.
**À revérifier avant toute décision** : tarifs et offres évoluent.

**Hébergement**
- OVHcloud, « Infrastructure locations by region » et « Discover more about regions and
  availability zones » (régions `eu-west-par`, `eu-west-gra`, `eu-west-rbx`,
  `eu-west-sbg`) — ovhcloud.com.
- OVHcloud, pages SecNumCloud (datacentres Roubaix, Gravelines, Strasbourg) — ovhcloud.com.
- OVHcloud, documentation Managed Kubernetes (chiffrement LUKS par région) — docs.ovhcloud.com.
- OVHcloud, blog « Pricing changes for Public Cloud, Bare Metal and VPS » (VPS-1 6,49 €/mois
  HT, VPS-2 9,99 €/mois HT) — blog.ovhcloud.com.
- Scaleway, pages Generative APIs et Tarifs, page SecNumCloud (HDS certifié, SecNumCloud
  en cours), régions Paris/Amsterdam/Varsovie/Milan — scaleway.com.
- Sources tierces pour les prix d'instances Scaleway (DEV1-S ≈ 6,55 €, PRO2-XXS ≈ 40,95 €,
  IPv4 ≈ 2,92 €/mois, stockage ≈ 0,095 €/GB/mois) — à revérifier sur scaleway.com/pricing.

**Fournisseurs de modèles**
- Mistral AI, help.mistral.ai (« Où stockez-vous mes données », « Puis-je activer le
  ZDR »), docs.mistral.ai (rétention zéro), pages de tarifs — mistral.ai.
- OVHcloud AI Endpoints, catalogue et tarifs publics (modèles servis depuis Gravelines) —
  à revérifier sur la page officielle.
- OpenAI, « Introducing data residency in Europe » et « Data controls in the OpenAI
  platform » (rétention zéro, 30 jours par défaut, pas d'entraînement depuis mars 2023) —
  openai.com / platform.openai.com.
- Anthropic, platform.claude.com « API and data retention » et privacy.claude.com
  (30 jours, ZDR sur demande, pas de résidence UE sur l'API directe) — anthropic.com.

**Technique**
- WebLLM, « A High-Performance In-Browser LLM Inference Engine », arXiv 2412.15803
  (inférence de modèles dans le navigateur, WebGPU/WebAssembly) — arxiv.org.

---

*Fin du document. Prochain jalon : validation par Anthony (questions 1 à 5), puis revue
de sécurité L6 (`docs/REVUE-SECURITE.md`).*
