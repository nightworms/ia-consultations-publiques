# DESIGN — direction de design de l'interface

*Rédigé par `designer` le 30 septembre 2026, lot L4 de la phase 4 du projet
`ia-consultations-publiques`. Ce document fait autorité sur ce qui se voit : il
ne dit rien de la logique métier ni des routes, qui appartiennent à
`docs/DECISIONS.md` et à `docs/PLAN-PHASE-4.md`.*

---

## 0. Ce que ce document est, et ce qu'il n'est pas

Il **est** : les principes visuels retenus, les maquettes écran par écran
(`docs/maquettes/*.html`), les captures qui prouvent qu'elles ont été regardées
(`docs/maquettes/captures/`), la liste avant / après des textes d'interface, et
la feuille de style et le gabarit de base **prêts à copier**.

Il **n'est pas** : une modification du produit. Aucun fichier de
`src/app/web/` n'a été touché. `src/app/web/static/style.css` et les gabarits
restent l'écriture de `dev-web` (règle § 2.E du plan de phase 4). Ici, on
livre la matière ; `dev-web` la pose.

Les contenus des maquettes sont **entièrement fictifs et signalés** : ils
servent à juger une mise en page, pas à annoncer des données.

---

## 1. En dix lignes

1. Le problème n'était pas la couleur : c'était le **vocabulaire**. L'écran
   parlait le langage du code (`non_commencee`, `Vierge (vierge)`,
   `54498bc1-7868-…`, « annexe C § C2 »).
2. Chaque écran a maintenant **une seule action principale**, en bleu plein, en
   haut à droite — et **pleine largeur sur téléphone**.
3. L'accueil ne montre plus une liste de familles vides : il montre **ce que la
   plateforme apporte** et **où en est l'utilisateur**, en trois étapes.
4. L'avancement se dit en métier : « 6 familles sur 9 renseignées », « ce qui
   vous manque pour être prêt à concourir » — plus jamais « complétude
   structurelle ».
5. Tout ce qui est technique (identifiants, empreintes, noms de tables) est
   **replié** dans un bloc « Références techniques », fermé par défaut.
6. Les explications longues passent derrière un **« Pourquoi ? »** : une phrase
   dans l'écran, le reste sur demande.
7. Le pied de page dit **d'abord ce que l'outil fait**, ensuite ses limites. Le
   bandeau jaune « brouillon » qui traînait en haut de chaque écran disparaît.
8. Rien n'est chargé depuis l'extérieur : **aucun JavaScript, aucune police
   distante, aucune icône, aucune animation**. Un seul fichier CSS.
9. Le mobile est traité à égalité : **capture à 390 px pour chaque écran**,
   aucun défilement horizontal dès 320 px.
10. Les contrastes sont **mesurés**, pas estimés (tableau § 3) : le plus faible
    texte est à 6,4:1, la norme AA en demande 4,5:1.

---

## 2. Les six règles tenues partout

**Règle 1 — une action principale, jamais deux.** Elle est identifiée dans le
code par la classe `btn--action`. À l'écran de bibliothèque, l'action principale
est « Importer vos documents existants » ; « Ajouter une information à la main »
est secondaire, et le formulaire de relecture est tertiaire. S'il fallait en
garder une seule, c'est toujours celle-là.

**Règle 2 — le vocabulaire du métier.** Verbe à l'infinitif pour les actions
(« Déposer le dossier de consultation », « Relancer la vérification »). Aucun
état de code, aucun nom de table, aucun nom de fournisseur à l'écran. Voir la
liste complète au § 5.

**Règle 3 — pas de mur de texte.** Une phrase par idée. Le développement long
va dans `<details class="pourquoi">`, fermé par défaut, résumé par une question
que l'utilisateur se pose vraiment (« Pourquoi une section peut-elle
manquer ? »).

**Règle 4 — montrer l'avancement.** Trois primitives suffisent : la liste
d'étapes `.progression` (où j'en suis, combien d'étapes), la jauge `.jauge`
(combien il reste), et la liste « ce qui vous manque pour être prêt à
concourir » avec **une action par manque**. L'avancement n'est jamais un
pourcentage nu : il est toujours accompagné de sa phrase.

**Règle 5 — hiérarchie visuelle réelle.** Un seul niveau de titre fort (h1,
24 px), des sections à 16,8 px, du texte à 16 px. Les espacements séparent
(1,25 rem entre les blocs) plus qu'ils ne décorent. La couleur est réservée au
signal : le gris porte le texte, le bleu porte l'action, le vert / orange /
rouge portent l'état — et chaque état porte aussi **son mot**.

**Règle 6 — erreur utile.** Trois questions, trois réponses : ce qui s'est
passé, pourquoi, quoi faire maintenant. Une erreur sans solution n'est pas un
message, c'est une plainte.

---

## 3. Le système visuel

### Couleurs — contrastes mesurés (WCAG 2.1, ratio texte/fond)

| Usage | Couleur | Fond | Ratio |
|---|---|---|---|
| Texte principal | `#16202b` | blanc | **16,5:1** |
| Texte principal | `#16202b` | `#f2f4f7` | **14,9:1** |
| Texte secondaire | `#4a5768` | blanc | **7,4:1** |
| Texte secondaire | `#4a5768` | `#f2f4f7` | **6,7:1** |
| Bandeau, blanc sur | `#0d3554` | — | **12,7:1** |
| Bouton principal, blanc sur | `#14507a` | — | **8,5:1** |
| Liens | `#14507a` | blanc | **8,5:1** |
| État « fait » | `#125c37` | `#e6f4ec` | **7,1:1** |
| État « à compléter » | `#7a4f00` | `#fdf3e0` | **6,5:1** |
| État « manquant » | `#9b2c12` | `#fdeee9` | **6,7:1** |
| Bordure de champ (non textuel) | `#788799` | blanc | **3,7:1** |

Le seuil AA est 4,5:1 pour le texte, 3:1 pour les éléments non textuels
(bordures de champs, contours). Tous les couples sont au-dessus. Les bordures
décoratives (`--bord`, `#c9d2dc`) ne servent qu'à séparer deux blocs de même
fond : elles ne portent aucune information.

### Typographie

Aucune police distante. Pile système : `-apple-system, BlinkMacSystemFont,
"Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`. Corps à 16 px,
interligne 1,55. Trois tailles seulement : 24 px (titre d'écran), 18,9 px
(section), 16 px (texte). Les titres de bloc dans une carte sont à 16,8 px,
gras.

### Espacements

Une seule unité, le rem. 1,25 rem entre deux blocs, 1,1 rem à l'intérieur d'une
carte, 0,95 rem entre deux champs. Aucun margin négatif, aucun positionnement
absolu en dehors du lien d'évitement.

### Composants livrés (à reprendre tels quels)

| Classe | Rôle |
|---|---|
| `.bandeau`, `.bandeau__int`, `.bandeau__marque` | barre du haut : nom du produit, navigation |
| `.entete-ecran`, `.entete-ecran__texte`, `.entete-ecran__action` | titre d'écran + action principale (côte à côte, puis empilés en mobile) |
| `.btn`, `.btn--principal`, `.btn--secondaire`, `.btn--discret`, `.btn--action` | boutons. `.btn--action` = l'action principale, une seule par écran |
| `.carte`, `.carte--plate`, `.carte__titre` | bloc de contenu |
| `.encart`, `.encart--ok`, `.encart--attention`, `.encart--erreur` | message encadré (information, réussite, attention, erreur) |
| `.etat`, `.etat--ok`, `.etat--attente`, `.etat--erreur`, `.etat--info` | pastille d'état — **toujours accompagnée de son mot** |
| `.progression` (+ `.fait`, `.encours`) | liste d'étapes numérotées |
| `.jauge`, `.jauge__part`, `.jauge-legende` | barre d'avancement, toujours suivie de sa phrase |
| `.liste`, `.liste__principal`, `.liste__fin` | liste de lignes (remplace les tableaux) |
| `.fiche-ligne`, `.fiche-ligne__tete`, `.fiche-ligne__titre` | ligne détaillée avec sources |
| `.sources`, `.source-etiquette` | liste des sources d'un élément |
| `details.pourquoi`, `details.references` | pliage des explications longues et des références techniques |
| `.champ`, `.aide`, `.grille`, `.pleine`, `.case` | formulaires |
| `.pied`, `.pied__int` | pied de page |
| `.lien-evitement`, `.visuellement-cache` | accessibilité |

**Pourquoi des listes plutôt que des tableaux.** Les tableaux de la phase 3
(cinq colonnes) deviennent illisibles sur un téléphone : soit ils débordent,
soit les colonnes s'écrasent. Toutes les informations tabulaires ont été
réécrites en `.liste` et `.fiche-ligne`, qui se replient naturellement en une
colonne. Aucune maquette ne contient de `<table>`.

---

## 4. Avant / après, écran par écran

Les captures de l'existant ont été prises sur l'application réelle
(`bash demarrer.sh`, compte de démonstration, `http://127.0.0.1:8099`) ; les
captures d'après sur les maquettes ouvertes dans le navigateur. Les deux jeux
sont dans `docs/maquettes/captures/avant/` et
`docs/maquettes/captures/apres/`.

| Écran | Avant (application réelle) | Après (maquette) |
|---|---|---|
| Connexion | `avant/01-connexion-desktop.png` | `apres/01-connexion-desktop.png` |
| Accueil | *n'existe pas* | `apres/02-accueil-desktop.png` |
| Bibliothèque | `avant/02-bibliotheque-desktop-pleine.png` | `apres/03-bibliotheque-desktop.png` |
| Bibliothèque (mobile) | `avant/07-bibliotheque-mobile.png` | `apres/03-bibliotheque-mobile.png` |
| Import guidé | *n'existe pas* | `apres/04-import-guide-desktop.png` |
| Dépôt d'un DCE | `avant/04-consultations-desktop.png` | `apres/05-depot-dce-desktop.png` |
| Analyse d'une consultation | `avant/05-consultation-analyse-desktop.png` | `apres/06-consultation-desktop.png` |
| Checklist | `avant/06-checklist-desktop.png` | `apres/07-checklist-desktop.png` |
| Mémoire technique | *n'existe pas* | `apres/08-memoire-desktop.png` |
| Export | *n'existe pas* | `apres/09-export-desktop.png` |
| Erreur | `avant/09-erreur-404-desktop.png` | `apres/10-erreur-desktop.png` |
| Saisie d'une famille | `avant/03-famille-identite-desktop.png` | `apres/11-famille-desktop.png` |

### 4.1 Connexion

**Constat sur l'existant.** L'écran est correct, mais il expose `annexe C § C2`,
`scripts/provisionnement.py` et le mot « périmètre » — trois choses qui ne
concernent pas l'utilisateur. Le titre du navigateur est « Connexion —
ia-consultations-publiques ».

**Ce qui change.** Barre du haut allégée : plus de navigation tant qu'on n'est
pas connecté. Un seul bouton, « Se connecter ». Une seule question repliée :
« Pourquoi je ne peux pas créer mon compte ici ? ».

### 4.2 Accueil (nouveau — `GET /accueil`)

**Constat.** L'écran n'existait pas : après connexion, l'utilisateur tombait sur
la bibliothèque, c'est-à-dire sur une liste de familles à zéro. Il voyait un
travail à faire, pas une promesse.

**Ce qui change.** Le titre dit ce que la plateforme apporte. L'action
principale est unique : « Déposer un dossier de consultation ». Ensuite
seulement, trois étapes numérotées disent où en est l'utilisateur. Puis trois
cartes disent ce que la plateforme fait — dont la plus utile : « Elle dit ce qui
manque, et quoi faire ».

### 4.3 Bibliothèque d'entreprise

**Constat sur l'existant (relevé à l'écran).** On y lit, dans l'ordre :
`Version de fiche :1`, `État :Vierge (vierge)`,
`Identifiant :54498bc1-7868-45c3-ac93-ab9b53a0379c`, un paragraphe sur
« l'état « Relue et validée » ... action humaine nommée et horodatée », puis
neuf lignes `non_commencee` dans une colonne « État d'avancement », une colonne
« Complétude » qui affiche `aucun élément`, une note sur la « complétude
structurelle seulement », un bloc « Relecture humaine bloquante » expliquant
« deux verrous distincts », et enfin un tableau de cinq lignes identiques
« Entreprise Fictive de Verification SARL — active — n°1 — vierge ».

**Ce qui change, dans l'ordre.** (1) Ce qui manque pour concourir. (2) Les neuf
familles avec un état en français et une action. (3) La relecture. (4) Un bloc
replié « Références techniques » qui contient, lui, la version de fiche et
l'identifiant. Le tableau des entreprises disparaît de cet écran : il ne
portait aucune décision.

### 4.4 Import guidé (nouveau — `GET/POST /bibliotheque/import`)

**Constat.** Aucune interface n'existait pour remplir la bibliothèque sans
saisir champ par champ — c'est le risque R1 du plan (mémoire creux parce que la
bibliothèque est vide).

**Ce qui change.** Trois étapes annoncées, un dépôt, puis des propositions
**chacune avec son extrait littéral et son emplacement**. Deux boutons nets :
« Accepter » / « Refuser », et un troisième discret « Corriger avant
d'accepter ». La mention « rien n'entre dans votre bibliothèque sans votre
accord » est répétée une fois, en clair.

### 4.5 Dépôt d'un dossier de consultation

**Constat sur l'existant.** L'écran affiche `Générateur d'analyse : ue` — le nom
du fournisseur de modèle, sans intérêt pour l'utilisateur. Il affiche aussi
`src/tests/fixtures/dce_fictif.pdf`, et parle d'« OCR », de « formats
bureautiques refusés explicitement ». Trois paragraphes expliquent ce que
l'outil ne fait pas **avant** de dire ce qu'il fait.

**Ce qui change.** Le fournisseur disparaît. La phrase d'entrée dit en une ligne
d'où vient le document. « Ce que vous obtiendrez » arrive après le formulaire,
en trois puces. Les dossiers déjà déposés s'affichent avec un état en français
(« Analysé », « Analyse en cours ») et une date lisible.

### 4.6 Analyse d'une consultation

**Constat sur l'existant.** L'écran s'ouvre sur `Identifiant : 74531431-…`,
`Statut : analysee`, `Document : dce-fictif.txt — 862 octets — empreinte SHA-256
6b921f8f2a…`, et une catégorie « Catégories restituées « non trouvé dans le
document » » avec `document a127c830-…` en source.

**Ce qui change.** L'identifiant, l'empreinte et le nom du fichier disparaissent
du corps. L'essentiel est en trois lignes en haut : date limite, nombre de
pièces exigées, nombre de critères — chacun avec un lien vers sa source.
L'action principale est « Demander le mémoire technique ». Les sources se lisent
en clair : « dossier de consultation, page 14, « Critères d'attribution » ».

### 4.7 Checklist

**Constat sur l'existant.** Le résumé affiche `Version de fiche croisée :
bc815c1f-…` et sept compteurs techniques (`Exigences comparées`, `Pièces de la
bibliothèque examinées`). Chaque ligne de statut affiche **deux fois** l'état :
la pastille « présente » et, dessous, le code `presente`. La pièce retenue est
suivie de `[reference_chantier]`, un nom de table.

**Ce qui change.** Les manques passent en tête, chacun avec son action
(« Ajouter l'attestation »). Les compteurs techniques partent. Le statut
s'affiche une seule fois, en français. Le nom de table disparaît.

### 4.8 Mémoire technique (nouveau — `GET /consultations/{id}/memoire`)

**Constat.** N'existait pas. C'est pourtant la valeur du produit.

**Ce qui change.** Les sections suivent l'ordre de pondération (40 %, 30 %,
20 %, 10 %) ; le critère « prix » est explicitement mis de côté, avec sa raison.
Chaque section porte **ses sources**, nommées en clair. Un critère sans
référence ne produit pas de section : il produit un **encart orange** qui dit ce
qui manque et ce qu'il faut faire, avec un bouton pour le faire. L'état de
relecture est visible section par section.

### 4.9 Export (nouveau — `GET /consultations/{id}/memoire/export`)

**Constat.** N'existait pas.

**Ce qui change.** L'écran commence par ce qui bloque, s'il y a quelque chose à
bloquer : « Il reste 1 section à relire avant de pouvoir exporter. » Puis il
demande qui valide — nom, fonction — et propose le format. Aucun bouton
d'envoi, de dépôt ou de signature : télécharger un fichier sur son propre
ordinateur, rien de plus.

### 4.10 Erreur

**Constat sur l'existant.** `Erreur 404` puis `Famille inconnue :
famille_inconnue`. Cela décrit le code, pas la situation de l'utilisateur, et ne
dit pas quoi faire.

**Ce qui change.** Un titre qui parle : « Cette page n'existe pas ». Puis trois
blocs : ce qui s'est passé, ce que vous pouvez faire, et le code technique
replié dans « Références techniques ».

### 4.11 Saisie d'une famille

**Constat sur l'existant.** L'écran de saisie affiche les libellés de champs
tels quels quand ils ne sont pas dans la table de traduction (par exemple
`photos`, `references_liees`, `documents_associes`, ou
« Photos (identifiants de documents) »).

**Ce qui change.** Chaque champ porte un libellé métier et, quand il faut, une
aide courte (« Le montant de vos travaux réalisés, pas le prix de votre
offre »). Les champs de liaison technique (« identifiants de documents ») sont
remplacés par un dépôt de fichier ou sortent de l'écran. La règle est simple :
**si un libellé affiché contient un nom de colonne, c'est un défaut.**

---

## 5. Liste avant / après des textes d'interface

C'est la partie la plus visible du travail : ce sont les phrases que
l'utilisateur lit. Les lignes sont classées par écran.

### Barre du haut (tous les écrans)

| Avant | Après |
|---|---|
| `ia-consultations-publiques — brouillon de travail` | `Consultations publiques` |
| `Connecté : Compte de verification (client 3782bb9d…)` | le nom de la personne, seul (`Anthony P.`) — l'identifiant de client disparaît |
| `Fermer la session` | `Se déconnecter` |

### Connexion

| Avant | Après |
|---|---|
| `Ouvrir la session` | `Se connecter` |
| `Le compte est créé par l'exploitant (scripts/provisionnement.py), jamais depuis cette interface : aucune inscription spontanée, aucune réinitialisation de mot de passe (annexe C § C2, hors périmètre de la phase 3).` | replié : « Pourquoi je ne peux pas créer mon compte ici ? » → « Le compte est ouvert par la personne qui installe le service pour vous. Cette page ne crée aucun compte et ne réinitialise aucun mot de passe. » |

### Bibliothèque

| Avant | Après |
|---|---|
| `Bibliothèque d'entreprise — état d'avancement` | `Votre bibliothèque d'entreprise` |
| `État de la fiche courante` | supprimé (remplacé par le bloc d'avancement) |
| `Version de fiche : 1` | supprimé → replié dans « Références techniques » |
| `État : Vierge (vierge)` | `Aucune information enregistrée pour l'instant` |
| `Identifiant : 54498bc1-7868-45c3-ac93-ab9b53a0379c` | supprimé → replié dans « Références techniques » |
| `L'état « Relue et validée » ne peut être posé que par une action humaine nommée et horodatée, depuis le formulaire de validation en bas de page. Aucun chemin automatique n'y mène.` | `La relecture porte toujours le nom de la personne qui l'a faite et la date.` |
| `non_commencee` (colonne « État d'avancement ») | `À compléter` (pastille) |
| `aucun élément` / `au moins un élément` (colonne « Complétude ») | `0 information` / `3 informations` |
| `Complétude structurelle seulement : l'outil n'affirme pas qu'une famille est complète au sens réglementaire, il constate qu'elle contient au moins un élément.` | replié : « Pourquoi ? » |
| `Relecture humaine bloquante` / `Deux verrous distincts : la validation de la bibliothèque (ce formulaire) et la validation des éléments extraits d'un DCE (écran d'analyse). Aucun des deux ne se court-circuite.` | `Valider votre bibliothèque` + « La relecture porte toujours le nom de la personne qui l'a faite et la date. » |
| `Nom du relecteur (obligatoire)` | `Votre nom` |
| `Le nom de l'humain qui a relu. Une validation sans nom est refusée.` | `La personne qui a relu. Une validation sans nom n'est pas enregistrée.` |
| `Périmètre de la validation` | `Ce que vous validez` |
| `J'ai relu et corrigé les informations ci-dessus (attestation obligatoire)` | `J'ai relu et corrigé ces informations.` |
| `Enregistrer la relecture humaine` | `Enregistrer la relecture` |
| `Entreprises et versions de fiche` + lignes `active` / `n°1 — vierge` | supprimé de cet écran |

### Dépôt d'un dossier de consultation

| Avant | Après |
|---|---|
| `Consultations — analyse d'un DCE` | `Déposer le dossier de consultation` |
| `brouillon — à relire et à signer` (bandeau jaune en haut de l'écran) | déplacé dans le pied de page, en une phrase |
| `Générateur d'analyse : ue` (+ paragraphe sur le fournisseur factice, le modèle de langage, la clé d'API) | **supprimé** |
| `Vous fournissez vous-même le document : l'outil ne va rien chercher, ne consulte aucune plateforme d'achat et ne dépose aucun pli à votre place. Il lit le document et propose des éléments avec leur source ; seul un élément validé par un humain alimente ensuite la checklist.` | `Le dossier vient de vous : l'outil ne va rien chercher sur une plateforme d'achat et ne dépose aucun pli à votre place.` |
| `Formats acceptés : PDF (y compris scanné, via OCR) et texte brut. Les formats bureautiques sont refusés explicitement.` | `PDF, y compris un document scanné, ou texte brut.` |
| `Fournir un document de consultation` | `Le dossier` |
| `Libellé de la consultation` | `Nom donné à ce dossier` |
| `Document (PDF ou .txt)` | `Le dossier de consultation` |
| `Jeu de démonstration fictif disponible dans le dépôt : src/tests/fixtures/dce_fictif.pdf` | supprimé de l'écran |
| `Référence de la consultation (saisie par l'humain)` | `Référence du marché — facultatif` |
| `Maître d'ouvrage déclaré (saisi par l'humain, jamais déduit)` | `Maître d'ouvrage — facultatif` + « Ce que vous saisissez ici est repris tel quel. L'outil ne le devine pas. » |
| `Analyser ce document` | `Analyser le dossier` |
| `Statut : analysee` | état `Analysé` |
| `Créée le 2026-09-30 14:01:02.431206+04:00` | `Déposé le 30/09/2026` |

### Analyse d'une consultation

| Avant | Après |
|---|---|
| `Analyse de la consultation — {{ libellé }}` | le titre du dossier + `Demander le mémoire technique` |
| `Identifiant : 74531431-788e-44e4-a66e-c4c201d10115` | supprimé → « Références techniques » |
| `Document : dce-fictif.txt — 862 octets — empreinte SHA-256 6b921f8f2a…` | supprimé → « Références techniques » |
| `Statut : analysee` | `Document fictif` / état en français |
| `Éléments proposés, avec leur source` + paragraphe pédagogique de six lignes | sections par catégorie ; le paragraphe passe derrière « Pourquoi ? » |
| `Catégories restituées « non trouvé dans le document »` | `non trouvé dans le document` (dans le flux, pas à part) |
| `(source : document a127c830-…, emplacement : absent du document)` | `Source : dossier de consultation, page 14, « Critères d'attribution »` |
| `Vérifier le dossier — checklist de conformité` | `Vérifier le dossier` |
| `Nom de l'humain qui lance la vérification (obligatoire)` | `Votre nom` |
| `Valider cet élément` / `Enregistrer la correction` / `Marquer comme supprimé` | `Accepter` / `Corriger avant d'accepter` / `Refuser` |

### Checklist

| Avant | Après |
|---|---|
| `Version de fiche croisée : bc815c1f-…` | supprimé |
| `Exigences comparées / Présentes / Manquantes / À vérifier / Pièces de la bibliothèque examinées` (5 compteurs bruts) | `Ce qui manque pour être prêt à concourir`, chaque ligne avec son action |
| `Le système ne fabrique aucune pièce manquante.` | remplacé par l'action à mener, ligne par ligne |
| pastille `présente` **et** code `presente` en dessous | un seul état : `Présente` |
| `Pièce retenue : … [reference_chantier]` | `Pièce retenue : …` (nom de table retiré) |
| `Valeurs contradictoires — le système ne choisit pas` | conservé, replié derrière « Pourquoi ? » |
| `Relancer la vérification — nom de l'humain (obligatoire)` | `Votre nom` |

### Erreur

| Avant | Après |
|---|---|
| `Erreur 404` | `Cette page n'existe pas` |
| `Famille inconnue : famille_inconnue` | `L'adresse que vous avez ouverte ne correspond à aucun écran de votre espace.` + ce qui s'est passé + ce que vous pouvez faire |
| `(aucun code technique à l'écran)` | code et adresse repliés dans « Références techniques » |

### Pied de page (tous les écrans)

| Avant | Après |
|---|---|
| `Outil d'aide à la relecture. L'outil ne signe rien, n'invente aucune référence ni aucun chiffre, ne fixe aucun prix et ne garantit aucune conformité. Toute sortie de nature à engager l'entreprise reste un brouillon — à relire et à signer par un humain.` puis `Aucune donnée réelle : les jeux de démonstration sont fictifs et signalés.` | `Ce que fait l'outil : il lit les dossiers que vous déposez et rédige votre mémoire technique à partir de vos propres références.` puis `Il ne dépose aucun pli, ne signe rien, ne fixe aucun prix et ne garantit aucune conformité. Ce que vous produisez reste un brouillon à relire et à signer.` |

**Deux règles à ne pas perdre en appliquant cette liste.** D'abord, aucune
information utile n'est supprimée : tout ce qui part du corps de l'écran
(identifiants, empreintes, version de fiche, compteurs techniques) est replié
dans « Références techniques », pas effacé. Ensuite, aucun texte nouveau
n'affirme un fait : les phrases ajoutées décrivent ce que l'utilisateur peut
faire, pas ce que le produit garantit.

---

## 6. La feuille de style, à copier telle quelle

À enregistrer dans `src/app/web/static/style.css` (fichier de `dev-web`, lot
L5a). C'est **exactement** le CSS embarqué dans les onze maquettes : aucune
ressource externe, aucun JavaScript, aucun `@import`.

```css
/* ==========================================================================
   Feuille de style unique — interface de réponse aux consultations publiques.
   Livrée par le lot L4 (designer) pour être reprise telle quelle par dev-web.

   Principes tenus ici :
   - HTML servi côté serveur, aucun JavaScript, aucune ressource externe ;
   - une action principale par écran (classe .btn--action), une seule ;
   - aucun état porté par la couleur seule : chaque couleur accompagne un mot ;
   - contrastes vérifiés (WCAG AA / RGAA), focus visible partout ;
   - mobile d'abord : la mise en page tient à 320 px sans défilement horizontal.
   ========================================================================== */

:root {
  --encre:        #16202b;   /* texte principal          — 16,5:1 sur blanc */
  --encre-2:      #4a5768;   /* texte secondaire         —  7,4:1 sur blanc */
  --fond:         #f2f4f7;
  --carte:        #ffffff;
  --bord:         #c9d2dc;
  --bord-fort:    #788799;   /* bordures de champs        —  3,7:1 sur blanc */
  --accent:       #14507a;   /* bouton principal         —  8,5:1 sur blanc */
  --accent-fonce: #0d3554;   /* bandeau, survols         — 12,7:1 sur blanc */
  --accent-clair: #e8f0f7;
  --ok-t:         #125c37;   --ok-f:  #e6f4ec;   --ok-b:  #9fd0b4;
  --att-t:        #7a4f00;   --att-f: #fdf3e0;   --att-b: #e6c489;
  --err-t:        #9b2c12;   --err-f: #fdeee9;   --err-b: #e9b3a3;
  --info-f:       #eef3f8;
  --rayon:        8px;
  --rayon-s:      6px;
  --ombre: 0 1px 2px rgba(16,32,48,.06), 0 2px 10px rgba(16,32,48,.05);
}

* { box-sizing: border-box; }
html { font-size: 100%; -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--fond);
  color: var(--encre);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  font-size: 1rem;
  line-height: 1.55;
}

/* --- Accessibilité : lien d'évitement, focus visible, contenu réservé ------ */
.lien-evitement {
  position: absolute; left: -9999px; top: 0; z-index: 20;
  background: var(--accent-fonce); color: #fff; padding: .6rem 1rem;
}
.lien-evitement:focus { left: 0; }
a:focus-visible, button:focus-visible, input:focus-visible,
select:focus-visible, textarea:focus-visible, summary:focus-visible,
[tabindex]:focus-visible {
  outline: 3px solid var(--accent-fonce); outline-offset: 2px;
}
.visuellement-cache {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

/* --- Bandeau -------------------------------------------------------------- */
.bandeau { background: var(--accent-fonce); color: #fff; }
.bandeau__int {
  max-width: 68rem; margin: 0 auto; padding: .6rem 1rem;
  display: flex; flex-wrap: wrap; gap: .5rem 1rem;
  align-items: center; justify-content: space-between;
}
.bandeau__marque {
  color: #fff; text-decoration: none; font-weight: 700; font-size: 1.05rem;
  padding: .3rem 0;
}
.bandeau nav { display: flex; flex-wrap: wrap; gap: .15rem; align-items: center; }
.bandeau nav a {
  color: #fff; text-decoration: none; padding: .45rem .6rem;
  border-radius: var(--rayon-s); font-size: .95rem;
}
.bandeau nav a:hover { background: rgba(255,255,255,.14); }
.bandeau nav a[aria-current="page"] {
  background: rgba(255,255,255,.2); text-decoration: underline;
}
.bandeau nav .lien-quitter { border: 1px solid rgba(255,255,255,.55); }
.bandeau nav form { margin: 0; display: inline; }
.bandeau nav button {
  font: inherit; font-size: .95rem; cursor: pointer;
  background: none; color: #fff; border: 1px solid rgba(255,255,255,.55);
  border-radius: var(--rayon-s); padding: .45rem .6rem;
}
.bandeau nav button:hover { background: rgba(255,255,255,.14); }
.bandeau__qui { font-size: .95rem; opacity: .95; }

/* --- Mise en page --------------------------------------------------------- */
.page { max-width: 68rem; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
.bandeau-mention {
  background: #e8ecf1; color: var(--encre-2); font-size: .85rem;
  text-align: center; padding: .35rem 1rem;
}

/* Titre d'écran + action principale, côte à côte puis empilés en mobile */
.entete-ecran {
  display: flex; flex-wrap: wrap; gap: 1rem;
  align-items: flex-start; justify-content: space-between;
  margin: 0 0 1.25rem;
}
.entete-ecran__texte { flex: 1 1 22rem; }
.entete-ecran h1 { margin: 0; font-size: 1.5rem; line-height: 1.25; }
.entete-ecran .sous-titre {
  margin: .4rem 0 0; color: var(--encre-2); max-width: 44rem;
}
.entete-ecran__action { flex: 0 0 auto; }

h2 { font-size: 1.18rem; margin: 1.75rem 0 .6rem; }
h3 { font-size: 1rem; margin: 1.15rem 0 .4rem; }
h4 { font-size: .95rem; margin: 1rem 0 .3rem; text-transform: uppercase;
     letter-spacing: .04em; color: var(--encre-2); }
p { margin: .5rem 0; }
ul, ol { margin: .5rem 0; padding-left: 1.15rem; }
li { margin: .2rem 0; }

/* --- Cartes --------------------------------------------------------------- */
.carte {
  background: var(--carte); border: 1px solid var(--bord);
  border-radius: var(--rayon); padding: 1.1rem; margin: 0 0 1.25rem;
  box-shadow: var(--ombre);
}
.carte > :first-child { margin-top: 0; }
.carte > :last-child { margin-bottom: 0; }
.carte--plate { box-shadow: none; }
.carte__titre { font-size: 1.05rem; margin: 0 0 .5rem; }

/* --- Boutons -------------------------------------------------------------- */
.btn {
  display: inline-block; font: inherit; font-weight: 600; cursor: pointer;
  padding: .6rem 1.1rem; border: 2px solid transparent; border-radius: var(--rayon-s);
  text-decoration: none; text-align: center; line-height: 1.3;
}
.btn--principal { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn--principal:hover { background: var(--accent-fonce); border-color: var(--accent-fonce); }
.btn--secondaire { background: #fff; color: var(--accent-fonce); border-color: var(--accent); }
.btn--secondaire:hover { background: var(--accent-clair); }
.btn--discret {
  background: transparent; color: var(--accent-fonce); border-color: transparent;
  text-decoration: underline; padding: .4rem .3rem;
}
.btn--action { font-size: 1.05rem; padding: .8rem 1.3rem; }
.actions { display: flex; flex-wrap: wrap; gap: .6rem 1rem; align-items: center; margin-top: 1rem; }
@media (max-width: 30rem) {
  .btn--action { display: block; width: 100%; }
  .entete-ecran__action { flex: 1 1 100%; }
}

/* --- Encarts (information, attention, réussite, erreur) ------------------- */
.encart {
  border-left: 5px solid var(--bord-fort); background: var(--info-f);
  padding: .85rem 1rem; margin: 0 0 1.25rem;
  border-radius: 0 var(--rayon-s) var(--rayon-s) 0;
}
.encart__titre { font-weight: 700; margin: 0 0 .25rem; }
.encart p:last-child, .encart ul:last-child { margin-bottom: 0; }
.encart--ok       { border-left-color: var(--ok-t);  background: var(--ok-f);  color: #0d3d26; }
.encart--attention{ border-left-color: var(--att-t); background: var(--att-f); color: #5a3a00; }
.encart--erreur   { border-left-color: var(--err-t); background: var(--err-f); color: #7d2410; }

/* --- États textuels ------------------------------------------------------- */
.etat {
  display: inline-block; font-size: .85rem; font-weight: 600;
  padding: .1rem .55rem; border-radius: 999px; border: 1px solid;
  white-space: nowrap;
}
.etat--ok       { color: var(--ok-t);  background: var(--ok-f);  border-color: var(--ok-b); }
.etat--attente  { color: var(--att-t); background: var(--att-f); border-color: var(--att-b); }
.etat--erreur   { color: var(--err-t); background: var(--err-f); border-color: var(--err-b); }
.etat--info     { color: var(--accent-fonce); background: var(--accent-clair); border-color: #a8c4da; }

/* --- Avancement ----------------------------------------------------------- */
.progression { list-style: none; margin: 0; padding: 0; display: grid; gap: .8rem; }
.progression > li { display: grid; grid-template-columns: 2rem 1fr; gap: .8rem; align-items: start; margin: 0; }
.progression .puce {
  width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center;
  font-weight: 700; font-size: .9rem;
  border: 2px solid var(--bord-fort); background: #fff; color: var(--encre-2);
}
.progression .fait .puce    { background: var(--ok-t);  border-color: var(--ok-t);  color: #fff; }
.progression .encours .puce { background: var(--accent); border-color: var(--accent); color: #fff; }
.progression .titre { font-weight: 600; }
.progression .detail { margin: .1rem 0 0; color: var(--encre-2); font-size: .95rem; }

.jauge { height: .8rem; background: #e3e8ee; border: 1px solid var(--bord);
         border-radius: 999px; overflow: hidden; margin: .5rem 0 .3rem; }
.jauge__part { height: 100%; background: var(--accent); }
.jauge-legende { margin: 0; color: var(--encre-2); font-size: .95rem; }

/* --- Listes --------------------------------------------------------------- */
.liste { list-style: none; margin: 0; padding: 0; }
.liste > li {
  display: flex; flex-wrap: wrap; gap: .3rem 1rem;
  align-items: baseline; justify-content: space-between;
  padding: .8rem 0; border-bottom: 1px solid #e4e9ef; margin: 0;
}
.liste > li:last-child { border-bottom: 0; }
.liste__principal { flex: 1 1 16rem; }
.liste__libelle { font-weight: 600; }
.liste__complement { display: block; color: var(--encre-2); font-size: .95rem; }
.liste__fin { display: flex; flex-wrap: wrap; gap: .5rem .9rem; align-items: center; }

/* Ligne « fiche » : un titre, un état, des sources */
.fiche-ligne {
  border: 1px solid var(--bord); border-radius: var(--rayon-s);
  padding: .85rem .95rem; margin: 0 0 .7rem; background: var(--carte);
}
.fiche-ligne__tete {
  display: flex; flex-wrap: wrap; gap: .4rem .9rem;
  align-items: baseline; justify-content: space-between;
}
.fiche-ligne__titre { font-weight: 600; }

/* --- Sources -------------------------------------------------------------- */
.sources { list-style: none; margin: .6rem 0 0; padding: 0; font-size: .92rem; color: var(--encre-2); }
.sources li { margin: .15rem 0; }
.sources .source-etiquette { font-weight: 600; color: var(--encre); }

/* --- Plier / déplier ------------------------------------------------------ */
details.pourquoi { margin: .6rem 0 0; }
details.pourquoi > summary {
  cursor: pointer; color: var(--accent-fonce); font-weight: 600;
  font-size: .95rem; padding: .3rem 0; display: inline-block;
}
details.pourquoi > summary::marker { color: var(--accent-fonce); }
details.pourquoi .reponse {
  margin: .4rem 0 0; padding: .8rem 1rem; background: var(--info-f);
  border-radius: var(--rayon-s); color: var(--encre-2);
  max-width: 46rem; font-size: .95rem;
}
details.references { margin: 1rem 0 0; }
details.references > summary { cursor: pointer; color: var(--encre-2); font-size: .9rem; }
details.references .reponse { font-size: .9rem; color: var(--encre-2); margin: .4rem 0 0; }
details.references code { font-size: .9rem; word-break: break-all; }

/* --- Formulaires ---------------------------------------------------------- */
fieldset {
  border: 1px solid var(--bord); border-radius: var(--rayon);
  padding: .9rem 1rem 1.1rem; margin: 0 0 1.25rem; background: var(--carte);
}
legend { font-weight: 700; padding: 0 .4rem; }
.champ { margin: 0 0 .95rem; }
.champ:last-child { margin-bottom: 0; }
.champ > label { display: block; font-weight: 600; margin-bottom: .25rem; }
.champ .aide { margin: 0 0 .35rem; color: var(--encre-2); font-size: .9rem; }
input[type="text"], input[type="password"], input[type="email"],
input[type="search"], input[type="file"], select, textarea {
  width: 100%; max-width: 100%; font: inherit; padding: .55rem .6rem;
  border: 1px solid var(--bord-fort); border-radius: var(--rayon-s);
  background: #fff; color: var(--encre);
}
textarea { min-height: 6rem; }
.grille { display: grid; gap: 0 1.25rem; grid-template-columns: 1fr; }
.grille .pleine { grid-column: 1 / -1; }
@media (min-width: 48rem) {
  .grille { grid-template-columns: 1fr 1fr; }
}
.case { display: flex; gap: .6rem; align-items: flex-start; margin: 0 0 .6rem; }
.case input { margin-top: .3rem; flex: 0 0 auto; width: 1.1rem; height: 1.1rem; }
.case label { font-weight: 400; }

/* --- Pied de page --------------------------------------------------------- */
.pied {
  border-top: 1px solid var(--bord); background: #fff;
  margin-top: 2rem; padding: 1.25rem 1rem; color: var(--encre-2); font-size: .92rem;
}
.pied__int { max-width: 68rem; margin: 0 auto; }
.pied p { margin: .3rem 0; }
```

---

## 7. Le gabarit de base, à copier tel quel

Proposition pour `src/app/web/templates/base.html`. Elle conserve la structure
Jinja2 existante (`{% raw %}{% block titre %}{% endraw %}`,
`{% raw %}{% block contenu %}{% endraw %}`, `url_for('statique', …)`), et
n'ajoute qu'une variable : `ecran`, qui sert à marquer l'onglet courant
(`aria-current="page"`).

```jinja
{# Gabarit de base — HTML rendu côté serveur, aucun JavaScript.
   Structure de titres : h1 = écran, h2 = section, h3 = sous-section.

   Les deux premières lignes du document — la déclaration de type de document
   et la balise d'ouverture avec la langue — restent celles de `base.html`
   actuel : elles ne changent pas et ne sont pas recopiées ici. #}
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block titre %}Mon espace{% endblock %} — Consultations publiques</title>
  <link rel="stylesheet" href="{{ url_for('statique', path='style.css') }}">
</head>
<body>
<a class="lien-evitement" href="#contenu">Aller au contenu principal</a>
<header class="bandeau">
  <div class="bandeau__int">
    <a class="bandeau__marque" href="/accueil">Consultations publiques</a>
    <nav aria-label="Navigation principale">
      {% if identite %}
      <a href="/accueil"{% if ecran == 'accueil' %} aria-current="page"{% endif %}>Accueil</a>
      <a href="/bibliotheque"{% if ecran == 'bibliotheque' %} aria-current="page"{% endif %}>Bibliothèque</a>
      <a href="/consultations"{% if ecran == 'consultations' %} aria-current="page"{% endif %}>Consultations</a>
      <span class="bandeau__qui">{{ identite.nom_affichage }}</span>
      <form method="post" action="/deconnexion">
        <button type="submit">Se déconnecter</button>
      </form>
      {% else %}
      <a href="/connexion" aria-current="page">Connexion</a>
      {% endif %}
    </nav>
  </div>
</header>

<main id="contenu" class="page">
  {% block contenu %}{% endblock %}
</main>

<footer class="pied">
  <div class="pied__int">
    <p><strong>Ce que fait l'outil :</strong> il lit les dossiers que vous
       déposez et rédige votre mémoire technique à partir de vos propres
       références.</p>
    <p>Il ne dépose aucun pli, ne signe rien, ne fixe aucun prix et ne garantit
       aucune conformité. Ce que vous produisez reste un brouillon à relire et
       à signer.</p>
  </div>
</footer>
</body>
</html>
```

**Pourquoi la déclaration de type de document n'est pas recopiée ici.** Le
contrôle de fuite du dépôt (`src/tests/integration/test_fuite_et_perimetre.py`)
refuse cette déclaration en dehors des fichiers `.html`, pour qu'un vrai
document ne se cache pas dans une note. Je ne contourne pas ce contrôle : le
gabarit ci-dessus commence après elle, et `dev-web` garde les deux premières
lignes de `base.html` telles quelles.

**Deux points d'attention pour `dev-web`.** Le `h1` du bandeau disparaît : le
titre de niveau 1 devient le **titre de l'écran** (classe `entete-ecran`), ce
qui répare une structure de titres qui commençait chaque page par
« ia-consultations-publiques — brouillon de travail ». Et le nom affiché dans
`bandeau__qui` doit être `identite.nom_affichage` **seul** : le fragment
d'identifiant de client (`client {{ identite.client_id[:8] }}…`) disparaît.

---

## 8. Correspondance maquette → gabarit, pour `dev-web`

Chaque maquette est la référence visuelle du gabarit correspondant. Les
formulaires des maquettes ne sont pas branchés : les `action` reprennent les
routes existantes ou celles gelées au § 2.D du plan.

| Maquette | Gabarit à écrire | Route |
|---|---|---|
| `maquettes/01-connexion.html` | `connexion.html` | `GET/POST /connexion` |
| `maquettes/02-accueil.html` | `accueil.html` **(nouveau)** | `GET /accueil` |
| `maquettes/03-bibliotheque.html` | `bibliotheque.html` et `premiere_utilisation.html` (état vide) | `GET /bibliotheque` |
| `maquettes/04-import-guide.html` | `import.html` **(nouveau)** | `GET/POST /bibliotheque/import` |
| `maquettes/05-depot-dce.html` | `consultations.html` | `GET/POST /consultations` |
| `maquettes/06-consultation.html` | `consultation.html` | `GET /consultations/{id}` |
| `maquettes/07-checklist.html` | `checklist.html` | `GET /consultations/{id}/checklist` |
| `maquettes/08-memoire.html` | `memoire.html` **(nouveau)** | `GET/POST /consultations/{id}/memoire` |
| `maquettes/09-export.html` | bloc d'export de `memoire.html` | `GET /consultations/{id}/memoire/export` |
| `maquettes/10-erreur.html` | `erreur.html` | toutes |
| `maquettes/11-famille.html` | `famille.html` | `GET/POST /bibliotheque/{famille}` |

**Ce que chaque écran doit contenir, minimalement, pour rester conforme à cette
direction :** un `h1` (le titre de l'écran), un `.entete-ecran` avec exactement
un `.btn--action`, et un pied de page unique. Le reste est décrit au § 4.

**Écarts attendus, à signaler plutôt qu'à improviser.** Trois points du modèle
ne se transposent pas directement : les champs de type liste (`photos`,
`references_liees`, `documents_associes`) sont des identifiants de documents,
pas des dépôts de fichiers ; la table de libellés `LIBELLES_CHAMPS` de
`routes_web.py` est incomplète et laisse passer des noms de colonnes ; et
certains statuts renvoyés par les services sont des codes
(`non_commencee`, `a_verifier`, `presente`) qu'il faut traduire au moment du
rendu, pas dans le gabarit. Ces trois points sont des **corrections à faire dans
`routes_web.py`**, pas des choix de design : si `dev-web` ne peut pas les
traiter dans son lot, c'est un défaut à remonter à l'ordonnanceur.

---

## 9. Accessibilité : ce qui est tenu, et comment le vérifier

| Exigence (RGAA / WCAG AA) | Ce qui est fait | Comment le vérifier |
|---|---|---|
| Contraste du texte | tous les couples ≥ 6,4:1 (tableau § 3) | relire le tableau ; le script de mesure est donné en bas de cette section |
| Contraste des éléments non textuels | bordures de champs à 3,7:1 | idem |
| Information non portée par la couleur seule | chaque pastille d'état contient son libellé en toutes lettres | ouvrir une maquette, regarder une pastille |
| Structure de titres | un seul `h1` par page, aucun niveau sauté | vérifié sur les 11 maquettes (`h1` = 1, séquences `122333`, `1223`, `1232`…) |
| Libellés de formulaires | chaque champ a un `<label for>` ; les aides sont liées par `aria-describedby` | vérifié : 0 champ sans libellé sur les 11 maquettes |
| Navigation au clavier | ordre du DOM = ordre visuel, aucun `tabindex` positif, aucun piège | tabuler dans une maquette |
| Focus visible | contour 3 px hors du bloc, sur tous les éléments interactifs | tabuler |
| Langue de la page | `<html lang="fr">` sur les 11 maquettes | — |
| Lien d'évitement | `.lien-evitement` en tête de chaque page | tabuler une fois |
| Alternative aux images | aucune image : aucune icône, aucun pictogramme | — |
| Aucun défilement horizontal | vérifié à **320 px** sur les écrans les plus larges | redimensionner la fenêtre |
| Contenu replié accessible | `<details>` / `<summary>` natifs, atteignables et activables au clavier | tabuler jusqu'à « Pourquoi ? », appuyer sur Entrée |

**Ce qui n'est pas revendiqué.** Aucun test avec lecteur d'écran n'a été mené,
et aucune conformité RGAA n'est certifiée par ce document : la déclaration
d'accessibilité, si elle est faite un jour, relève d'un audit, pas d'une
intention.

**Mesurer les contrastes (script de contrôle, hors dépôt) :**

```python
def luminance(hexadecimal: str) -> float:
    n = hexadecimal.lstrip("#")
    composantes = [int(n[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    corriger = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, v, b = (corriger(c) for c in composantes)
    return 0.2126 * r + 0.7152 * v + 0.0722 * b


def contraste(texte: str, fond: str) -> float:
    a, b = luminance(texte), luminance(fond)
    clair, sombre = max(a, b), min(a, b)
    return round((clair + 0.05) / (sombre + 0.05), 2)
```

---

## 10. Ce que je n'ai pas décidé, et qui vous appartient

1. **Le nom du produit.** Les maquettes affichent « Consultations publiques »
   comme titre de travail, parce qu'il faut bien quelque chose dans la barre du
   haut. Ce n'est pas une proposition de marque : c'est un espace réservé.
2. **Ce que devient la page « première utilisation ».** J'ai traité l'état vide
   de la bibliothèque comme une variante du même écran (avec l'action principale
   « Créer mon entreprise »), plutôt qu'une page séparée. À confirmer.
3. **La place de la relecture sur l'écran de bibliothèque.** Elle est
   aujourd'hui en bas de page, comme un formulaire de plus. Si elle devient un
   geste fréquent, elle méritera peut-être un écran propre.
4. **Le niveau de détail des sources.** J'affiche « dossier de consultation,
   page 14, « Critères d'attribution » ». Si le découpage des pages n'est pas
   fiable, il faudra dire autrement — et le dire à l'utilisateur, pas le
   supprimer silencieusement.
5. **Les écrans qui n'existent pas encore** (import guidé, mémoire, export) sont
   maquettés sur la base des services décrits dans le plan, pas sur du code
   livré : `dev-web` devra ajuster au contact du réel, en gardant les principes
   du § 2. Si un ajustement contredit une règle, c'est un commentaire sur la
   carte, pas une décision silencieuse.
