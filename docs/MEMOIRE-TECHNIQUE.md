# MEMOIRE-TECHNIQUE — moteur de génération du mémoire technique (lot L2, phase 4)

*Écrit par `dev-back` le 30 septembre 2026. Décrit ce que les lots L2 (génération) et L6
(export téléchargeable, § 8) implémentent, leurs règles opposables, leur algorithme et
leurs **limites assumées**. En cas de contradiction,
`docs/DECISIONS.md` (D1 à D10) et `docs/PLAN-PHASE-4.md` (§ 2.A, § 2.B, § 2.C, § 2.E) font
foi ; ce document les explique.*

---

## 1. Ce que fait ce lot, en une phrase

Il **structure un mémoire technique** à partir de deux matières réelles : les **critères
d'attribution du DCE** (déjà extraits et validés par la brique B) et la **bibliothèque
d'entreprise** du client. Chaque section du mémoire est **adossée à des éléments réels**
de cette bibliothèque ; ce qui n'est pas étayable devient un **manque** (constat + action
à mener), jamais du texte inventé.

C'est la traduction en code de la règle centrale de la phase 4 (`PLAN-PHASE-4.md` § 2.B) :

> L'IA peut **argumenter** et **valoriser** ; elle ne peut écrire que ce qui est
> rattachable à un élément réel de la bibliothèque du client. Ce qui ne l'est pas est
> **signalé comme manquant**, jamais inventé.

**Deux conditions, pas une.** Une section n'est produite que si (1) elle porte au moins
une source réelle **et** (2) cette source **parle du critère**. La seconde condition est
la correction du défaut B2 relevé par la vérification L8 : avec la première seule, le
mémoire produisait une section « Expérience en toitures-terrasses végétalisées » étayée
par des chantiers de toitures-terrasses **ordinaires** — l'affirmation « nous avons
l'expérience des toitures végétalisées » n'était rattachable à rien.

---

## 2. Modèle de données — migration `0005_memoire_technique.sql`

Cinq tables, réversibles (`down` complet), `client_id` non nul et indexé sur chacune.
Noms de tables et de colonnes **gelés** par `PLAN-PHASE-4.md` § 2.A.

### 2.1 `memoire_dossier` — l'en-tête du mémoire généré

| Colonne | Type | Rôle |
|---|---|---|
| `id` | uuid | identifiant technique |
| `client_id` | uuid NOT NULL → client | cloisonnement (jamais d'accès croisé) |
| `consultation_id` | uuid NOT NULL → consultation | le DCE dont on suit les critères |
| `fiche_version_id` | uuid NOT NULL → fiche_version | la version de bibliothèque **citée**, figée : reproductibilité |
| `titre` | varchar(255) | libellé affiché |
| `statut` | varchar(100) | `brouillon` \| `en_relecture` \| `valide` |
| `moteur_fournisseur`, `moteur_modele` | varchar(255) | provenance du moteur, si connue |
| `avertissement` | text | rappel « brouillon, rien n'est garanti » |
| `date_creation`, `date_modification` | timestamptz | horodatage |

### 2.2 `memoire_section` — une section, adossée à un critère

| Colonne | Type | Rôle |
|---|---|---|
| `ordre` | integer ≥ 0 | rang = **ordre de notation du DCE** (pondération décroissante) |
| `critere_code` | varchar(100) | identifiant de l'élément `extraction_element` (critère) |
| `critere_libelle` | varchar(255) | le mot du RC, repris tel quel |
| `critere_poids` | numeric(6,2) | pondération `%` lue dans le DCE, **nullable** |
| `titre`, `contenu` | varchar(255), text | texte de la section |
| `statut` | varchar(100) | `brouillon` \| `relue` \| `validee` |
| `origine` | varchar(100) | `mixte` (synthèse de plusieurs éléments), sinon les jeux de la phase 3 |
| `confiance` | varchar(100) | la **plus faible** des confiances des sources citées |
| `statut_par`, `statut_le` | varchar(255), timestamptz | **action humaine nommée et horodatée** — voir § 6 |
| `date_creation`, `date_modification` | timestamptz | horodatage |

### 2.3 `memoire_section_source` — la preuve

| Colonne | Type | Rôle |
|---|---|---|
| `table_source` | varchar(100) | nom de la table de contenu citée (liste blanche des familles F1–F9) |
| `element_id` | uuid | l'élément réel cité (même `client_id` — contrôle applicatif) |
| `libelle_source` | varchar(255) | libellé lisible, tiré d'un champ réel |
| `emplacement_source` | varchar(255) | famille / entité / échéance d'où vient la valeur |

Aucune clé étrangère vers la table citée : la cible **varie** selon `table_source`. Le
contrôle « l'élément appartient bien au client de la session » est donc fait **par le
service, avant écriture** (§ 4), et vérifié par un test d'intégration.

### 2.4 `memoire_manque` — ce qui ne peut pas être étayé

`critere_code`, `critere_libelle`, `critere_poids`, **`constat`**, **`action_attendue`**.
C'est **la fonctionnalité la plus utile du produit** : elle dit au client quoi ajouter à
sa bibliothèque pour gagner des points. **Ce n'est pas un cas d'erreur.**

### 2.5 `memoire_validation` — la validation finale

`nom_validateur`, `fonction_validateur`, `horodatage`, **`empreinte_contenu`** (SHA-256 du
contenu validé), `format_export`, `nom_fichier`. Aucun dossier ne passe `valide` sans
cette ligne : c'est le verrou humain du lot.

### 2.6 Écarts assumés au § 2.A du plan

Deux colonnes **s'ajoutent** à la liste gelée (sans rien renommer) :

- `memoire_section.statut_par` et `memoire_section.statut_le`.

Raison : la règle « aucun statut de section validé n'est posé par du code sans action
humaine **nommée et horodatée** » (exigence 4 de la carte L2) n'avait, sans elles, aucun
support en base. Une contrainte `CHECK` garantit qu'une section ne peut pas quitter
`brouillon` sans ces deux valeurs. Les noms de tables et de colonnes du § 2.A sont tous
présents, inchangés.

---

## 3. Algorithme de structuration

Entrées : la consultation (DCE analysé), la fiche de bibliothèque du client, les
**critères validés**, la bibliothèque elle-même. Sortie : sections + manques.

1. **Lire le plan** : les critères d'attribution **validés** de la consultation
   (`extraction_element`, `categorie = 'critere'`, `statut_verification = 'valide'`). Même
   verrou que la checklist. Aucun critère validé → **refus explicite** (il n'y a pas de
   plan à suivre).
2. **Ordonner** les critères par **pondération décroissante** (`poids_depuis_valeur` lit
   le `%` tel qu'écrit dans le DCE). Tri **stable** : à poids égal, l'ordre du DCE est
   conservé. Un critère **sans pondération connue** passe **en fin**, avec sa raison
   affichée dans le contenu de la section (ou du manque).
3. **Associer chaque critère à des familles** de bibliothèque mobilisables
   (`correspondance_pour_critere`) : table de mots-clés → familles, dérivée de
   `docs/MEMOIRE-ATTENDU.md` § 5 et de `docs/JURY-ACHETEUR.md` § 5.3. Le rattachement est
   **tracé** : la fonction rend les familles **et** les mots-clés qui les ont justifiées.
   Un libellé non reconnu mobilise un ensemble de démonstration de valeur technique
   (`FAMILLES_DEFAUT`, `defaut=True`) : ces familles ne servent qu'à **collecter** des
   candidats, elles ne produisent **jamais** une section à elles seules (§ 4bis).
   Un critère de **prix** ne mobilise **aucune** famille : il produit un **manque** (§ 5).
4. **Collecter les éléments réels** de ces familles (via `ServiceBibliotheque`, donc
   chiffrement et cloisonnement de la phase 3). Chaque élément est rendu en lignes
   « champ : valeur » — **jamais un identifiant interne** (les UUID sont écartés).
5. **Vérifier chaque source** avec le **garde-fou de la phase 3** (§ 4). Une source
   invérifiable fait **refuser** la section, qui devient un **manque**.
6. **Vérifier que le sujet du critère est couvert** (§ 4bis) : chaque terme de sujet du
   libellé doit être retrouvé, au singulier comme au pluriel, dans le texte d'au moins un
   élément cité. Un seul terme absent → **manque**, jamais de section. Le constat **nomme
   le terme absent** (vérifiable par une requête sur la bibliothèque).
7. **Composer** le texte de chaque section : un cadrage du critère (mot du RC + poids),
   la **trace de la correspondance** (§ 4bis), puis une phrase **factuelle par élément
   cité**, dont chaque valeur vient d'un champ réel. Le **développement est proportionnel
   à la pondération** (§ 3.1).
8. **Écrire** dossier, sections, sources et manques, en **une transaction**. Le dossier
   sort en `brouillon`.

### 3.1 Développement proportionnel au poids

Défaut retenu faute d'arbitrage (question ouverte n° 1 du plan) : le développement suit la
pondération, **sans plafond**, et chaque section expose sa longueur.

| Pondération | Niveau | Effet |
|---|---|---|
| ≥ 30 % | `complet` | la phrase mobilise tous les champs réels disponibles |
| 10–29 % | `essentiel` | les champs clés seulement |
| < 10 % ou inconnue | `mention` | l'élément est cité (libellé + source), sans détail |

Le critère le plus lourd reçoit donc bien le développement le plus long. La longueur
effective reste fonction du **nombre d'éléments réels** : on n'ajoute jamais de texte pour
remplir. Chaque section porte sa longueur dans `resume.longueurs` de la réponse d'API,
pour qu'Anthony puisse trancher sur pièce.

---

## 4. Règles de source

**Le contrôle existant est réutilisé, jamais réécrit** : `source_presente`
(`app.services.fournisseur_modele.base`) est appliqué tel quel, avec
`memoire_section_source` comme support.

- Pour chaque élément candidat, le service produit une « page » (le rendu « champ :
  valeur » de l'élément) et un **extrait invoqué** (la première ligne non vide).
- `verifier_sources` exige que l'extrait se retrouve **littéralement** dans la page — la
  comparaison ignore les écarts d'espaces, **rien d'autre**.
- Deux refus explicites (`SourceMemoireInvalide`, jamais un succès partiel) :
  1. l'élément cité n'appartient pas à la bibliothèque du client de la session
     (croisement entre clients) ;
  2. l'extrait invoqué est introuvable dans l'élément cité (affirmation non adossée).
- En cas de refus, `section_ou_manque` **transforme la section en manque** — la section
  n'est **jamais** produite. C'est le comportement prouvé par
  `src/tests/integration/test_memoire_ligne_rouge.py`.

**Isolation.** Tout le SQL passe par `storage.connexion.Connexion` : le filtre
`client_id` est imposé par le contexte de session. Aucun élément d'un autre client
n'alimente un mémoire (vérifié par les tests d'isolation).

---

## 4bis. Le sujet du critère — « la source existe » ne suffit pas (correction B2)

La vérification indépendante L8 a trouvé ce défaut, **reproduit sur le jeu L7** :

> Le critère « Expérience en toitures-terrasses **végétalisées** » (10 %) produisait une
> section étayée par quatre chantiers d'étanchéité de toitures-terrasses **ordinaires** et
> deux certifications. Aucune référence ne portait « végétalisé ». `memoire_manque` était
> vide et l'export affirmait « Aucun manque signalé ». Le repli `FAMILLES_DEFAUT`, non vide
> dès qu'une source du lot existait, faisait produire une section pour **n'importe quel**
> libellé : seul le *nombre* de sources comptait, jamais le lien avec le **sujet**.

**Règle ajoutée, appliquée après le garde-fou de source.** Pour chaque critère :

1. on extrait les **termes du sujet** (`termes_sujet`) : les mots du libellé de 4 lettres
   ou plus, diminués des mots de liaison (`MOTS_VIDES`), des mots de remplissage de
   l'offre (`TERMES_GENERIQUES` : « offre », « marché », « affecté », « engagement »…) et
   des mots **déjà portés par les mots-clés** qui ont rattaché les familles — ceux-là ont
   servi à choisir les familles, ils ne désignent pas un sujet à corroborer ;
2. on exige que **chaque** terme du sujet soit retrouvé, **au singulier comme au pluriel**
   (`_radical` : « toitures » ↔ « toiture »), dans le texte « champ : valeur » d'au moins
   un élément cité (`couverture_sujet`) ;
3. sinon la section **n'est pas produite** : `memoire_manque` reçoit le critère, un **constat
   qui nomme le terme absent** et **l'action à mener** de la famille la plus parlante.

Deux conséquences voulues :

- **le repli `FAMILLES_DEFAUT` ne fabrique plus rien** : il collecte des candidats, mais
  une section exige la corroboration du sujet ;
- **la correspondance est tracée** dans le contenu de la section
  (« Correspondance établie : … termes retrouvés dans votre bibliothèque : « … » »), pour
  qu'un relecteur puisse contester sur pièce.

Exemple de manque produit (jeu L7, bibliothèque **remplie**) :

> **Expérience en toitures-terrasses végétalisées — 10 %**
> *Constat* : « Aucun élément de votre bibliothèque ne porte « végétalisées » : le sujet du
> critère n'est pas couvert. Le mémoire ne peut pas présenter une expérience ou un moyen
> que votre bibliothèque ne démontre pas. »
> *Pour renforcer ce critère* : « Ajouter un chantier comparable (nature de travaux, maître
> d'ouvrage, montant € HT, année de réception, difficulté traitée). »

**Cas limite assumé :** la correspondance est lexicale, donc grossière (esprit du
fournisseur factice, cf. § 9). Si un critère emploie un terme de spécialité qu'aucun
élément ne reprend littéralement, il devient un **manque** — c'est le comportement voulu
(le manque dit quoi ajouter) ; mais un vocabulaire métier trop éloigné peut produire un
manque là où un humain aurait reconnu une correspondance. C'est **toujours le sens
prudent** : un manque de trop coûte une relecture, une section non étayée coûte le marché.

---

## 5. Le critère « prix » et la ligne rouge

Conformément à `docs/JURY-ACHETEUR.md` § 5.4, **le prix n'est pas un critère de mémoire
technique**. Le moteur le traite donc comme un manque explicite :

> **Constat** : « Le prix n'est pas un critère de mémoire technique : il se lit dans
> l'acte d'engagement et les pièces financières de l'offre, jamais ici. »
> **Action** : « Traiter le montant dans l'acte d'engagement et les pièces financières ;
> n'écrire aucune valeur de prix dans le mémoire technique. »

Aucune section ne porte de prix, aucun chiffre n'est inventé, aucune conformité n'est
promise. La phrase de cadrage de chaque section rappelle elle-même : « aucune valeur n'est
ajoutée, aucun prix n'est fixé, aucune conformité n'est promise ». Vérifié par des tests.

---

## 6. Statuts — le verrou humain

Aucun chemin de ce lot ne pose un statut validé **tout seul**.

```
section : brouillon → relue → validee        (statut_par + statut_le obligatoires)
dossier : brouillon → en_relecture → valide  (ligne memoire_validation obligatoire)
```

- La génération écrit **`brouillon`** partout.
- `changer_statut_section` exige un **nom** (`statut_par`) ; la transition
  `brouillon → validee` directe est **refusée**. Toute action de relecture ramène le
  dossier à `en_relecture` (une validation antérieure ne vaut plus pour un contenu
  modifié).
- `valider_dossier` exige un **nom** et une **fonction**, refuse si une section est encore
  `brouillon`, écrit une ligne `memoire_validation` avec l'**empreinte SHA-256** du contenu
  validé, et ne se rejoue pas.

L'empreinte est calculée sur une sérialisation **déterministe** du contenu métier
(titre, critère, texte, statut, sources, manques) — elle ne dépend ni d'un identifiant
interne ni d'un horodatage : deux contenus identiques donnent la même empreinte.

La **signature électronique** reste hors périmètre (cf. `PLAN-PHASE-4.md` § 6, question 5) :
la phase 4 s'arrête à une validation nommée et horodatée écrite en base.

---

## 7. API JSON

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/api/v1/consultations/{id}/memoire` | générer (corps : `fiche_version_id`, `titre` optionnels) |
| `GET`  | `/api/v1/consultations/{id}/memoire` | lire le dernier mémoire |
| `POST` | `/api/v1/memoire/sections/{id}` | relire / valider une section (`statut`, `par`) |
| `POST` | `/api/v1/memoire/{id}/validation` | valider le mémoire (`nom_validateur`, `fonction_validateur`) |

Codes : `404` mémoire introuvable pour ce client ; `422` source invérifiable (refus
explicite) ; `400` autre refus métier. Les **manques** sont un résultat **`200`/`201`**,
jamais une erreur. La réponse porte `sections` (avec `sources`), `manques`, `resume`,
`avertissement` et la mention « brouillon ».

Aucune route `/api/v1` existante n'est renommée ni modifiée.

---

## 8. Export téléchargeable du mémoire (lot L6)

**Un mémoire qu'on ne peut pas sortir du site ne sert à rien.** Ce lot rend le mémoire
téléchargeable, dans un fichier ouvrable dans un traitement de texte. Il est servi par un
**fichier de routes dédié** (`src/app/api/routes_export.py`), monté par l'agrégateur
`app.api.routes` : `routes_web.py` n'est pas touché.

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/consultations/{id}/memoire/export?format=md\|docx` | télécharger le mémoire **du client de la session** |

### 8.1 Les deux formats

- **Markdown (`.md`) = format canonique.** Produit **sans aucune dépendance nouvelle**
  (bibliothèque standard seule : assemblage de texte). C'est **lui** qui est testé et
  vérifié. Titres hiérarchisés dans l'ordre des critères pondérés, **source citée pour
  chaque argument**, manques listés avec **leur action à mener**, en-tête portant la
  relecture humaine et l'empreinte du contenu validé.
- **DOCX (`.docx`) = format de confort**, produit par `python-docx`.

### 8.2 Dépendance annoncée et justifiée — `python-docx`

**Annonce, faite AVANT l'installation** (exigence du cadrage, § 2.C du plan) :

| Critère | Valeur |
|---|---|
| Bibliothèque | `python-docx` (import `docx`), version **1.2.0** |
| Nature | **pure Python** — aucune compilation ; elle dépend de `lxml` (6.1.3), extension installée depuis un **roue précompilée** : aucun compilateur requis sur le poste |
| Licence | MIT (permissive) |
| Ressources externes | **aucune** : ni réseau, ni service, ni police distante |
| Exposition à un tiers | **aucune** : la génération est locale |
| Rôle | écrire un `.docx` lisible dans Word / LibreOffice |

*Précision honnête* : la carte annonçait `python-docx` comme « pure Python ». C'est vrai du
paquet lui-même ; sa dépendance `lxml` est une extension native, mais elle s'installe
**depuis une roue précompilée** sur macOS — donc aucun compilateur, et rien qui sorte du
poste. Dépendance ajoutée à `src/requirements.txt`, épinglée.

**Défaut de repli si l'installation échoue ou est refusée : le lot n'est pas bloqué.** Le
format DOCX répond alors « **non disponible** » avec **sa raison**, en `409`, et l'export
Markdown reste valide à lui seul. Le Markdown n'importe **jamais** `docx` au chargement du
module : la sonde `docx_disponible()` fait l'import à la demande.

### 8.3 La règle du lot : rien ne sort sans validation humaine

1. Le mémoire doit exister **pour le client de la session** — sinon `404`, jamais `403`,
   jamais le contenu d'un autre client.
2. Une ligne **`memoire_validation`** (nom, fonction, horodatage) doit exister. Sans elle,
   la réponse n'est **pas une erreur technique** mais un **message qui dit quoi faire**
   (`409`) : « le mémoire doit d'abord être relu et validé par une personne nommée »,
   suivi du chemin à suivre (relire les sections, puis valider avec un nom et une
   fonction). **Rien ne sort sans relecture humaine.**
3. Le fichier porte **le contenu validé**. L'empreinte SHA-256 enregistrée dans
   `memoire_validation` est **recalculée** sur le contenu actuel puis comparée.

### 8.4 Choix sur l'empreinte : la divergence **refuse** l'export

Deux comportements étaient possibles (exigence 5 de la carte L6) : refuser, ou signaler la
divergence. **Choix retenu : refuser.**

- Si l'empreinte recalculée **égale** celle enregistrée → le fichier est produit.
- Si elle **diffère** (une section a été modifiée après la validation, son statut a
  changé, ou un manque a bougé) → l'export est **refusé** (`409`) par un message explicite,
  et une **nouvelle relecture puis validation** est exigée.

Raison : un fichier qui part avec un contenu non relu est exactement le risque que la
ligne rouge interdit. Signaler la divergence sans la bloquer laisserait sortir un document
dont personne n'a répondu.

**Point de vigilance technique.** L'empreinte est calculée sur une sérialisation **dont
l'ordre compte** : `valider_dossier` trie les sections par `ordre, id` et les manques par
`id`. L'export relit donc avec **les mêmes tris** (`_lire_pour_empreinte`) ; utiliser
l'ordre d'affichage des manques (par pondération) produirait une fausse divergence.

### 8.5 Codes de réponse

| Code | Cas | Corps |
|---|---|---|
| `200` | export autorisé | le fichier, `Content-Disposition: attachment` |
| `303` | aucune session | redirection vers `/connexion?suivant=…` |
| `404` | mémoire introuvable **pour ce client** | message lisible (jamais `403`) |
| `400` | format inconnu | message rappelant les formats admis |
| `409` | validation manquante / contenu modifié depuis la validation / DOCX indisponible | **message pédagogique** en français |

Les refus renvoient un **message en texte brut, en français** — lisible par un humain
comme par un outil, jamais une trace technique — et **sans aucun bouton** de dépôt,
d'envoi ou de signature : l'export ne transmet rien à personne, il produit un fichier.

### 8.6 Ce que le fichier exporté ne contient pas

**Aucun prix, aucun chiffre inventé, aucune conformité garantie.** Le rendu ne fait que
reprendre le contenu du mémoire (dont chaque affirmation est déjà adossée à un élément
réel). Les montants qui apparaissent sont ceux de la bibliothèque du client, jamais des
valeurs calculées ici. L'en-tête du fichier le rappelle lui-même.

---

## 9. Limites assumées

1. **Le fournisseur de modèle n'est pas appelé pour rédiger.** Un fournisseur **factice**
   ne sait pas argumenter ; un modèle réel reste derrière l'adaptateur (D8), hors de ce
   chemin. La composition est **déterministe** : des phrases-cadres dont chaque valeur
   vient d'un champ réel. Une rédaction assistée par un vrai modèle pourra être ajoutée
   plus tard **derrière le même garde-fou de source**, sans changer le modèle de données.
2. **Le mapping critère → familles est une heuristique de mots-clés**, volontairement
   grossière (esprit du fournisseur factice). Un critère exotique tombe sur
   `FAMILLES_DEFAUT` — ces familles servent à **collecter** des candidats, jamais à
   produire une section sans corroboration du sujet (§ 4bis). Le contrôle de couverture
   est lui aussi **lexical** (mots entiers, singulier/pluriel repliés) : deux façons de
   dire la même chose sans mot commun donnent un manque. Il vaut mieux enrichir la table
   des mots-clés ou la bibliothèque que deviner.
3. **Les angles morts sans famille dédiée** (planning, PPSPS, déchets, interfaces,
   sous-traitance, site occupé) sont traités en **manques** quand la bibliothèque ne les
   étaye pas, conformément à `docs/MEMOIRE-ATTENDU.md` § 7. Aucune famille n'est inventée.
4. **Les champs de type `uuid`** (pièces jointes, avis technique, photos) sont **écartés**
   du texte : ce sont des références à des documents, pas du contenu, et un mémoire ne
   contient aucun identifiant technique. Le mémoire cite donc le produit et sa date de
   validité, pas le numéro d'avis (qui vit dans le document joint).
5. **Le développement proportionnel au poids** est un défaut, pas un arbitrage
   (`PLAN-PHASE-4.md` § 6). La longueur visible par section est exposée pour trancher.
6. **Une seule dépendance nouvelle, portée par le lot L6 (export) : `python-docx`**, pour
   le seul format de confort `.docx` — annoncée et justifiée au § 8.2 **avant**
   installation. Le format canonique (`.md`) et ce lot L2 ne dépendent d'aucune
   bibliothèque nouvelle.

---

## 10. Ce que ce lot ne fait pas

Pas de dépôt de pli, pas de signature électronique, pas de connexion à une plateforme
d'achat public, pas de prix, pas de facturation. Aucune donnée réelle : tous les jeux de
test sont **fictifs et signalés**. Rien n'est déployé ni exposé sur Internet.
