# STACK-PROPOSAL — Proposition de stack technique

*Lot L1 de la phase 2. Écrit le 30 septembre 2026. Board : `ia-consultations`.
Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*

> **Statut du document : proposition, non décision** (c'est la décision **D5** de
> `docs/DECISIONS.md` : « l'équipe propose, Anthony valide »). Rien n'est installé, rien
> n'est déployé, aucun code n'est écrit ici. Ce document décrit une **cible** ; il ne
> tranche ni la confidentialité ni l'hébergement (voir
> `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`).

Textes de référence qui font foi : `docs/DECISIONS.md` (D1 à D6). Ce document respecte
D1 (client = entreprise candidate), D2 (généraliste), D3 (abonnement + à l'acte),
D5 (stack proposée, non décidée), D6 (France, chiffré, isolation par client — tension
traitée ailleurs). Il respecte aussi la décision d'orchestrateur **D-C5** : la cible ne
présuppose **aucun** moteur de base de données et reste portable entre SQLite et un SGBD
hébergé.

---

## 1. Ce qu'on demande à la stack, en une page et sans jargon

Le produit fait cinq choses. La stack doit les rendre possibles, sans plus.

1. **Lire un PDF long.** Un DCE (dossier de consultation) fait plusieurs dizaines de
   pages, parfois plus de cent, avec des tableaux, des annexes et des pièces
   hétérogènes. Il faut extraire le texte et, au besoin, les images ou les pages
   scannées.
2. **Stocker une bibliothèque d'entreprise.** Identité, bilans, assurances,
   certifications, références de chantiers, CV, fiches produits : des informations
   saisies une fois, structurées, retrouvables, versionnées.
3. **Appeler un modèle d'IA.** Envoyer le texte du DCE à un modèle de langage pour en
   extraire les pièces exigées, les critères, les échéances, et proposer un squelette de
   réponse. **L'IA ne signe rien, n'invente aucune référence ni aucun chiffre, ne fixe
   aucun prix, ne garantit aucune conformité** (ligne rouge de `PROJECT.md` § 5).
4. **Servir une interface web.** Une application accessible dans un navigateur, où
   l'entreprise dépose un DCE et relit ce qui a été préparé.
5. **Cloisonner les clients entre eux.** Les données d'une entreprise ne doivent jamais
   se mélanger avec celles d'une autre, ni alimenter l'entraînement d'un modèle.

Et une contrainte de forme : **rester maintenable par une petite équipe, voire une seule
personne.** Concrètement : peu de briques, peu de serveurs à surveiller, des sauvegardes
simples, des mises à jour qui ne cassent pas tout, et une documentation qui permet de
reprendre le code sans son auteur.

Ce qu'on **ne** demande pas encore : la haute disponibilité, le passage à l'échelle pour
des milliers d'utilisateurs, ni une application mobile.

Le coût d'exploitation réel a deux parties : un **serveur** (fixe, mensuel) et la
**consommation du modèle d'IA** (variable, par dossier traité). Les deux sont chiffrés
plus bas, avec leur source et leur date.

---

## 2. La proposition de la phase 1, et son évaluation

`docs/DATA-MODEL.md` § 0 avait retenu, à titre provisoire : **Python 3.12 / SQLite /
FastAPI / migrations SQL numérotées**, avec Node/TypeScript, PostgreSQL et un ORM lourd
explicitement écartés.

**Évaluation.** Cette base est saine, et trois de ses quatre choix méritent d'être
confirmés :

- **Python** est le bon choix pour lire des PDF et appeler un modèle d'IA :
  l'écosystème y est le plus mûr (extraction de texte, OCR, clients d'API). Confirmé.
- **FastAPI** est un framework web léger et documenté, adapté à une petite équipe.
  Confirmé comme cible de la couche `api/`.
- **Migrations SQL numérotées et réversibles** (convention déjà décrite dans
  `src/migrations/README.md`) : simples, lisibles sans outil, réversibles. Confirmé.
- **SQLite** est le point à discuter. Imbattable au démarrage (un fichier, zéro serveur,
  zéro coût), il devient un choix discutable dès que plusieurs clients actifs et
  plusieurs traitements simultanés coexistent. Ce n'est pas une erreur, c'est un
  **point de bascule** : voir § 3, scénarios A et B.

Le squelette `src/` (20 modules, bibliothèque standard uniquement) reste un
**squelette** : il n'importe ni FastAPI, ni SQLite, ni ORM. Ce document ne le modifie
pas (voir § 6).

---

## 3. Trois scénarios de stack

Trois scénarios réalistes, du plus simple au plus exigeant. Chacun décrit les mêmes
briques (langage, framework web, base de données, stockage des fichiers, lecture des
PDF, appel du modèle d'IA, authentification et séparation des clients, sauvegardes,
migrations), puis ce qu'il permet, ce qu'il coûte, ce qu'il ferme.

### Scénario A — Socle minimal : un serveur, SQLite

Le prolongement direct de la proposition de phase 1.

| Brique | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework web | FastAPI + un serveur applicatif (Uvicorn) |
| Base de données | **SQLite**, fichier unique, hors dépôt (sous `data/`, ignoré par git) |
| Stockage des fichiers | Dossier local sur le serveur (documents joints : DCE, bilans, CV) |
| Lecture des PDF | Bibliothèque Python d'extraction (texte puis OCR si page scannée) |
| Appel du modèle d'IA | Appel HTTP à l'API d'un fournisseur, **à choisir** (voir § 5) |
| Authentification | Comptes locaux, mots de passe hachés, sessions ; un compte = une entreprise |
| Séparation des clients | Colonne `entreprise_id` présente partout (déjà prévue au modèle) + filtrage dans la couche `storage/` |
| Sauvegardes | Copie chiffrée du fichier SQLite + du dossier documents, planifiée |
| Migrations | Fichiers SQL numérotés, réversibles (`up` / `down`) |

**Ce qu'il permet.** Démarrer vite, pour un coût fixe minimal. Une seule machine à
administrer, une sauvegarde à gérer, aucune base de données réseau à maintenir. Adapté à
un MVP avec peu d'entreprises clientes et un traitement à la fois.

**Ce qu'il coûte.** Serveur : un petit serveur en France. Ordre de grandeur, **daté et à
revérifier** — OVHcloud, page « Public Cloud — Tarifs »
(`https://www.ovhcloud.com/fr/public-cloud/prices/`, consultée le 30/09/2026) : instance
`b2-7` (2 vCores, 7 Go de mémoire, 50 Go SSD) annoncée à **25,17 €/mois**, instance
`b2-15` à **48,05 €/mois**. Soit une fourchette d'exploitation serveur de l'ordre de
**25 à 50 €/mois** au démarrage. Compétences : Python et un peu d'administration Linux,
accessibles à une personne motivée. Consommation du modèle : voir § 5.

**Ce qu'il ferme comme portes.** Plusieurs traitements lourds simultanés (SQLite écrit en
série), une base volumineuse (des dizaines de milliers de documents), et la haute
disponibilité. Ce n'est pas bloquant au MVP, mais il faudra migrer avant que la charge
ne le justifie — donc **prévoir la sortie dès le départ**, ce que permet D-C5.

### Scénario B — Socle serveur avec base managée

Même application, mais la base et les fichiers sont confiés à des services hébergés en
France dès le début.

| Brique | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework web | FastAPI + Uvicorn |
| Base de données | **PostgreSQL managé**, hébergé en France (OVHcloud ou Scaleway) |
| Stockage des fichiers | Stockage objet compatible S3, hébergé en France, chiffré |
| Lecture des PDF | Identique au scénario A |
| Appel du modèle d'IA | Identique au scénario A (fournisseur à choisir, § 5) |
| Authentification | Comptes locaux + un cloisonnement renforcé côté base (filtrage systématique par `entreprise_id`, au besoin une règle de sécurité appliquée par la base elle-même) |
| Séparation des clients | `entreprise_id` **plus** cloisonnement au niveau de la base et du stockage |
| Sauvegardes | Gérées par l'hébergeur, plus une copie hors site chiffrée |
| Migrations | Fichiers SQL numérotés, identiques (le schéma reste portable) |

**Ce qu'il permet.** Plusieurs clients actifs en parallèle sans dégradation, sauvegardes
et réplication prises en charge par l'hébergeur, montée en charge naturelle, base
volumineuse. C'est la cible naturelle quand le nombre de clients dépasse la poignée.

**Ce qu'il coûte.** Plus cher et plus complexe à administrer : une base managée en France
et un stockage objet s'ajoutent au serveur. Ordre de grandeur **daté et à revérifier**
(OVHcloud, même page que ci-dessus, consultée le 30/09/2026) : les offres de bases
managées PostgreSQL de la gamme « Enterprise / Advanced » démarrent à plusieurs centaines
d'euros par mois selon la taille, très au-dessus d'un serveur nu. Pour un MVP à faible
volume, c'est **surdimensionné** ; c'est justifié à partir d'un usage réel. Compétences :
les mêmes, plus la gestion d'un service managé.

**Ce qu'il ferme comme portes.** Un peu de simplicité : plus de services à comprendre et à
surveiller. Rien d'irréversible pour autant — le schéma étant portable (D-C5), on peut
rester sur SQLite puis basculer sur PostgreSQL par migration, sans réécrire le modèle.

### Scénario C — Traitement sur le poste du client (local d'abord)

Ici, l'intelligence du traitement tourne **sur le poste de l'entreprise**, pas sur un
serveur. La stack n'est plus seulement un site web : c'est une application que l'on
installe, qui ouvre les documents localement.

| Brique | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework web | Interface locale (FastAPI servi sur `localhost`, ou une interface de bureau) |
| Base de données | SQLite, sur le poste du client |
| Stockage des fichiers | Disque du poste du client |
| Lecture des PDF | Identique, locale |
| Appel du modèle d'IA | **Modèle auto-hébergé localement**, ou appel sortant — mais alors le document quitte le poste (ce qui réduit l'intérêt du scénario) |
| Authentification | Celle du poste (compte utilisateur de la machine) |
| Séparation des clients | Naturelle : chaque entreprise a son installation, sur sa machine |
| Sauvegardes | À la charge du client (copie du dossier local) |
| Migrations | Identiques, locales |

**Ce qu'il permet.** La confidentialité la plus forte, obtenue **par construction** : si
rien ne sort du poste, rien ne peut fuiter par le serveur. À noter : c'est la famille
d'options décrite comme « chiffrement côté client et traitement local » dans D6. Le
verdict sur la phrase « seul le client a accès à ses données » pour cette famille
appartient à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` — **à compléter après validation de
ce document**.

**Ce qu'il coûte.** Le plus lourd à faire vivre : il faut installer et mettre à jour un
logiciel chez chaque client (support, versions, systèmes d'exploitation différents). Et
pour garder la promesse de confidentialité, le modèle d'IA doit tourner **sur le poste**,
ce qui suppose une machine puissante ou un modèle local plus modeste en qualité. Le coût
fixe serveur disparaît, mais un coût matériel et de support apparaît chez le client.

**Ce qu'il ferme comme portes.** Le modèle SaaS pur : plus de mise à jour centralisée, plus
de correction déployée en une fois pour tout le monde, et une barrière à l'entrée pour
l'utilisateur (installer un logiciel). Difficile de facturer un abonnement pour un
logiciel que le client héberge lui-même.

> **Note de méthode.** Ces trois scénarios ne tranchent **pas** la confidentialité : ils
> décrivent des architectures, chacune compatible avec une ou plusieurs options de D6. Le
> choix de l'option, le verdict sur « seul le client a accès à ses données », l'hébergeur
> et le chiffrement sont traités dans `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` (agent
> `infra`). Ce document-ci **y renvoie** et n'énonce **aucune garantie de
> confidentialité** propre (conformément à la décision d'orchestrateur D-C2).

---

## 4. Tableau comparatif

Lu par un non-développeur. Les coûts sont des **fourchettes**, datées, à revérifier avant
décision.

| Critère | A — Un serveur, SQLite | B — Base managée | C — Sur le poste du client |
|---|---|---|---|
| Simplicité (pour l'équipe) | ★★★ Élevée : une machine, un fichier | ★★ Moyenne : plusieurs services | ★ Faible : installation chez chaque client |
| Simplicité (pour le client) | ★★★ Élevée : un navigateur | ★★★ Élevée : un navigateur | ★ Faible : installer et maintenir un logiciel |
| Coût fixe mensuel (serveur) | ≈ 25–50 € (source OVHcloud, 30/09/2026, cf. § 3) | Nettement plus élevé (base managée) | ≈ 0 € côté serveur ; coût matériel chez le client |
| Coût variable (modèle d'IA) | Idem dans A et B (par dossier) ; **à vérifier** pour C (modèle local) | Idem A | Modèle local : coût matériel, pas de facture par dossier |
| Confidentialité possible | Voir `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` — **à compléter après validation de ce document** | Idem | Idem (famille « traitement local » de D6) |
| Vitesse de mise en œuvre | ★★★ Rapide | ★★ Plus lente (base + stockage à monter) | ★★ Moyenne sur le papier, lourde en déploiement réel |
| Dépendance à un prestataire | Hébergeur unique + fournisseur du modèle | Hébergeur (base + stockage) + fournisseur du modèle | Faible côté serveur, mais dépendance au poste du client |
| Réversibilité | ★★★ Élevée : le modèle est portable, on peut migrer | ★★★ Élevée : schéma portable (D-C5) | ★★★ Données chez le client, mais coûteux à changer de modèle de distribution |

Aucune étoile n'est un prix : la colonne coût renvoie aux sources datées, les cases
« confidentialité » renvoient au document `infra`.

---

## 5. La question du fournisseur du modèle d'IA

**Le point à ne pas manquer.** Pour analyser un DCE, il faut envoyer son **texte** à un
modèle de langage. Si ce modèle est hébergé hors de France — et le plus souvent hors de
l'Union européenne — alors le document du client voyage jusque chez ce prestataire. C'est
un **maillon du chemin de la donnée**. Promettre « hébergé en France » sans le dire serait
faux au sens strict. Ce document signale le point ; il **ne tranche pas** (c'est la
question 2 posée à Anthony, et le traçage complet du chemin de la donnée appartient à
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`).

### Trois familles d'options

**1. Fournisseur européen / français.** Modèles servis depuis l'UE, par exemple
Scaleway (Generative APIs, serveurs en France), Mistral (éditeur français), OVHcloud.
- *Qualité* : bonne à très bonne ; l'écart avec les tout meilleurs modèles mondiaux se
  réduit, mais existe encore sur les tâches les plus fines.
- *Coût* : souvent compétitif. Exemple **daté et à revérifier** — Scaleway, page
  « Model-as-a-service Pricing »
  (`https://www.scaleway.com/en/pricing/model-as-a-service/`, consultée le 30/09/2026) :
  modèle `mistral-small-3.2-24b` à **0,15 €/million de jetons en entrée / 0,35 €/million
  en sortie** ; `llama-3.3-70b` à **0,90 €/million** entrée et sortie. Un palier gratuit
  de 1 million de jetons est annoncé.
- *Souveraineté* : la plus forte des options « en ligne ». Le document reste dans l'UE.

**2. Fournisseur hors UE, avec clauses contractuelles.** Modèles de pointe américains,
encadrés par un contrat de sous-traitance et des clauses de transfert.
- *Qualité* : la plus élevée aujourd'hui.
- *Coût* : variable. Exemple **daté et à revérifier** — OpenAI, page « Pricing » de l'API
  (`https://platform.openai.com/docs/pricing`, consultée le 30/09/2026) : modèle
  `gpt-5-mini` à **0,25 $/million** en entrée / **2 $/million** en sortie ;
  `gpt-4o-mini` à **0,15 $/million** / **0,60 $/million**. Des options de « résidence des
  données » dans plusieurs régions sont annoncées sur l'offre entreprise — **à vérifier**
  au cas par cas.
- *Souveraineté* : la plus faible. Le document sort de l'UE ; la protection repose sur un
  contrat, pas sur l'architecture (un engagement **commercial**, pas une garantie
  technique).

**3. Modèle auto-hébergé.** Un modèle « ouvert » (poids publics) exécuté sur du matériel
loué en France, ou sur le poste du client (scénario C).
- *Qualité* : dépend du modèle et de la machine ; en dessous des deux options ci-dessus
  pour l'analyse fine, sauf matériel coûteux.
- *Coût* : pas de facture par dossier, mais du matériel à louer ou à acheter. Ordre de
  grandeur **daté et à revérifier** — OVHcloud, même page tarifaire que § 3, consultée le
  30/09/2026 : instance GPU `l4-90` à **540 €/mois**, `l40s-90` à **1 008 €/mois**. C'est
  un engagement fixe, à comparer à quelques centimes par dossier.
- *Souveraineté* : maximale ; rien ne sort du périmètre loué ou du poste.

### Ordre de grandeur de la consommation, par dossier

Chiffre **illustratif, à ajuster après mesures réelles** (hypothèses signalées). Pour un
DCE de plusieurs dizaines de pages, on peut supposer de l'ordre de **50 000 à 150 000
jetons en entrée** par analyse et quelques milliers en sortie. Avec un petit modèle
européen (0,15 €/million en entrée) : de l'ordre de **quelques centimes par dossier**.
Avec un modèle de pointe (2 $/million en entrée) : de l'ordre de **quelques dizaines de
centimes**, rarement plus d'un euro par dossier. Autrement dit, **le coût du modèle est
négligeable devant le coût fixe du serveur** au démarrage. Ce sont des hypothèses, pas des
mesures ; elles devront être confirmées sur des DCE réels.

**Conclusion partielle.** Le fournisseur du modèle est un choix de **souveraineté autant
que de qualité et de coût**, et il ne se tranche pas ici (question 2 ci-dessous). À
qualité comparable, l'écart de coût par dossier est faible et ne devrait pas être le
critère dominant.

---

## 6. Ce qui reste réversible, et à quel coût

Le squelette `src/` existe (phase 1). Voici son sort selon la décision.

**Si la stack proposée (scénario A, avec sortie vers B) est acceptée :**

- `src/app/domain/` (les entités métier) **reste tel quel** : c'est de la structure pure,
  sans dépendance externe, valable quel que soit le moteur de base et le framework.
- `src/app/storage/` : les squelettes d'accès aux données deviennent le point où l'on
  branchera la base réelle. À compléter, pas à jeter.
- `src/app/services/` et `src/app/api/` : les squelettes de logique et de routes seront
  remplis ; FastAPI sera la cible de `api/`.
- `src/migrations/` : la convention décrite reste la bonne ; on y ajoutera les premiers
  fichiers SQL au moment de l'implémentation.
- `src/tests/` : emplacement prévu, à remplir.

**Si la stack proposée est rejetée au profit de Node/TypeScript :**

- `src/app/domain/` est à **réécrire**, mais son contenu décrit la structure des données,
  qui ne change pas : le travail de modélisation reste valable, seule la syntaxe change.
  Coût faible à modéré.
- Les autres dossiers (`storage/`, `services/`, `api/`, `migrations/`) sont des squelettes
  minces : coût de reprise faible.
- Le document `docs/DATA-MODEL.md` **reste** la référence de la structure (il ne dépend
  d'aucun langage).

**Si un SGBD hébergé est choisi (scénario B) au lieu de SQLite :** aucun jetage. Le
schéma est portable par construction (D-C5) ; on remplace le moteur, on garde le modèle et
les migrations, qui restent des SQL standards.

**Coût de sortie, en une phrase.** Tout ce qui a été produit en phase 1–2 est
**documentaire et structurel** : il survit à un changement de moteur ou de fournisseur de
modèle. Le seul vrai point de non-retour serait un investissement d'implémentation
structurante avant validation — c'est précisément ce que D5 interdit, et ce document ne le
demande pas.

---

## 7. Décision demandée à Anthony

Trois questions, formulées pour une réponse simple. Chacune indique ce qu'elle change
concrètement. Les options de confidentialité (question distincte, portée par
`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`) ne sont pas répétées ici.

**Question 1 — Le socle applicatif. A, B ou C ?**
- **A. Un serveur, SQLite** (le plus simple, le moins cher, à faire évoluer plus tard).
- **B. Base de données managée en France dès le départ** (plus robuste, plus cher, plus
  complexe).
- **C. Traitement sur le poste du client** (confidentialité maximale par construction,
  mais installation et support chez chaque client).

*Ce que ça change :* A démarre en quelques semaines pour environ 25–50 €/mois de serveur ;
B ajoute une base managée et son coût dès le premier jour ; C impose de distribuer un
logiciel et de renoncer à la mise à jour centralisée. **Recommandation : A**, avec la
sortie vers B déjà prévue (voir § 8).

**Question 2 — Le fournisseur du modèle d'IA. A, B ou C ?**
- **A. Fournisseur européen / français imposé** (le document reste dans l'UE).
- **B. Fournisseur hors UE avec clauses contractuelles** (meilleure qualité, mais le
  document sort de l'UE ; protection contractuelle, pas technique).
- **C. Modèle auto-hébergé** (souveraineté maximale, coût matériel fixe, qualité moindre).

*Ce que ça change :* la qualité de l'analyse, le coût, et surtout **le chemin de la
donnée**. Choisir B revient à accepter que le DCE parte chez un prestataire hors UE ; ce
n'est pas neutre vis-à-vis de « hébergé en France » et devra être dit au client.
**Recommandation : A** au démarrage, à qualité jugée suffisante ; réévaluer ensuite.

**Question 3 — Le budget mensuel cible, en fourchette.** Par exemple : moins de 50 €,
entre 50 et 200 €, ou plus de 200 € par mois (hébergement + consommation du modèle).

*Ce que ça change :* sans budget connu, les options ne sont comparables qu'en ordres de
grandeur non validés, et les documents de la phase 2 écriront « à vérifier » partout. Ce
chiffre permet de trancher entre A et B, et de fixer un plafond de dépense.

---

## 8. Recommandation argumentée

**Recommandation : scénario A, avec une sortie vers B déjà dessinée.**

Raisonnement :

1. **Le produit n'a pas encore de clients.** Au MVP, le nombre d'entreprises et le volume
   de traitements simultanés ne justifient pas une base managée. Payer une base managée
   avant d'avoir un usage, c'est de la dette d'exploitation payée d'avance.
2. **Une petite équipe doit pouvoir tout tenir.** Un serveur unique, un fichier de base,
   une sauvegarde chiffrée : c'est administrable par une personne. C'est exactement la
   contrainte posée en § 1.
3. **La sortie vers B est réversible et peu coûteuse.** D-C5 garantit que le schéma ne
   dépend d'aucun moteur. Passer de SQLite à PostgreSQL managé sera une migration, pas
   une réécriture. On ne s'enferme pas.
4. **Le coût fixe est faible** (≈ 25–50 €/mois de serveur, source OVHcloud datée du
   30/09/2026, à revérifier) et **le coût du modèle par dossier est négligeable**
   (quelques centimes à moins d'un euro, estimation à confirmer). La stack ne devrait pas
   être un poste de dépense structurant tant que le produit n'est pas vendu.
5. **Python + FastAPI + SQLite** est l'ensemble le plus rapide à mettre en œuvre pour une
   personne, avec le meilleur écosystème pour lire des PDF et appeler un modèle.

**Ce que cette recommandation rend difficile ou impossible plus tard :**

- **Plusieurs traitements lourds réellement simultanés** : SQLite écrit en série. Il
  faudra basculer sur B avant que la charge ne gêne.
- **Une base très volumineuse** (des dizaines de milliers de documents) : le fichier SQLite
  devient lourd à sauvegarder et à déplacer.
- **La haute disponibilité** : un seul serveur, une seule base — une panne arrête le
  service. Acceptable au MVP, à traiter plus tard.
- **Le passage à l'échelle géographique** (plusieurs régions) : non prévu.
- **Rien qui engage la confidentialité ou le choix de l'hébergeur** : ces décisions
  restent entières et renvoyées à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.

**Point de vigilance.** Cette recommandation suppose que la séparation des clients est
faite **dès la première ligne de code** (filtrage systématique par `entreprise_id` dans la
couche `storage/`), même avec SQLite. Rattraper un cloisonnement oublié après coup est
beaucoup plus coûteux que de l'écrire au départ.

---

*Fin de la proposition. Statut : proposition, non décision (D5). Aucune dépendance
installée, aucun code écrit, aucun déploiement. Toute fourchette de prix citée est datée
et doit être revérifiée avant décision. Sur la confidentialité, ce document ne fait que
renvoyer à `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md`.*
