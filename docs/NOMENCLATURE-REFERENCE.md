# NOMENCLATURE DE RÉFÉRENCE — les jeux de référence du produit

*Livrable du lot **L5** (agent `batiment`), phase 2 — architecture technique et décisions
structurantes. Tâche : `t_6a41441a`. Board : `ia-consultations`.
Dossier : `/Users/pause/Projets/ia-consultations-publiques`.*

> **Rôle de ce document.** Il décrit **le contenu** des jeux de référence du produit :
> le premier jeu métier (`metier.etancheite`), le patron qui permet d'en ajouter d'autres
> sans rien changer à la base, et la liste des jeux transverses encore à fournir.
> Il **ne décrit pas comment** ces valeurs sont stockées : la structure (tables, types,
> relations, versionnage, chargement) appartient à `docs/DATA-MODEL-V2.md` (lot L3).

> **Autorité en cas de divergence.**
> - **Structure** (le conteneur générique, les types, les contraintes) :
>   `docs/DATA-MODEL-V2.md` fait foi. En cas de divergence de forme entre les deux
>   documents, c'est lui qui l'emporte.
> - **Contenu métier** (les valeurs, leurs libellés, leurs codes, leur sourçage) :
>   le présent document fait foi.
> - Au moment de la rédaction, `docs/DATA-MODEL-V2.md` est produit **en parallèle** par le
>   lot L3. La présente nomenclature n'attend pas son contenu pour exister : elle respecte
>   le format imposé par l'orchestrateur (décision **D-C1**, voir § 0).

> **Lien avec la phase 1.** `docs/DONNEES-METIER-BATIMENT.md` (v1) reste **intact** : c'est
> un document de cadrage de phase 1, il dit *quoi* collecter sur une entreprise
> d'étanchéité. Le présent document ne le réécrit pas : il **reprend son contenu métier**
> et l'exprime en **valeurs de nomenclature**, pour que la bibliothèque d'entreprise ne
> présume plus d'un métier (décision **D2** de `docs/DECISIONS.md`).

---

## Avertissement — exemples fictifs, ligne rouge, données réelles

**Tous les exemples de ce document sont fictifs et signalés comme tels.** Aucun nom de
client, aucune référence de chantier réelle, aucun montant réel, aucune donnée d'entreprise
n'y figure. Les valeurs entre crochets `[…]` sont des ordres de grandeur de *format*, sans
valeur métier.

Rappels applicables à tout le document (ligne rouge du projet, voir `README.md` et
`PROJECT.md` § 5) :

- l'IA **n'invente aucune référence, aucun code, aucun chiffre, aucune norme** ; toute
  valeur de nomenclature doit pouvoir **pointer vers sa source** ;
- l'IA **ne signe rien**, **ne fixe aucun prix**, **ne garantit aucune conformité** ;
- une valeur de nomenclature est **proposée** ; c'est **l'entreprise** qui valide ce qu'elle
  détient réellement. Une valeur présente dans cette liste ne signifie **jamais** qu'une
  entreprise possède la qualification, l'assurance ou le matériel correspondant ;
- **aucune donnée réelle d'entreprise ni document confidentiel** dans ce dépôt.

**Confidentialité.** Ce document n'énonce **aucune** garantie de confidentialité. Sur ce
sujet, le seul document habilité est `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` (lot L2,
décision **D-C2**) — *à compléter après validation*. Aucune phrase de ce document ne doit
être lue comme un engagement de confidentialité.

---

## 0. Comment lire ce document

### 0.1 Le format imposé (D-C1)

Un **jeu de référence** est identifié par un **namespace** : une chaîne en minuscules,
avec `.` comme séparateur. Les jeux métier sont préfixés `metier.` — le premier est
`metier.etancheite`.

Ses valeurs sont décrites par **sept champs** :

| Champ | Ce qu'il porte |
|---|---|
| `code` | Identifiant de la valeur **à l'intérieur du jeu**. Stable, court, en minuscules (`nt.terrasse.refection`, `321`). C'est lui qu'on stocke dans les données d'entreprise. |
| `libelle` | Le texte lisible par un professionnel, tel qu'il doit apparaître à l'écran et dans un document. |
| `parent_code` | Le `code` de la valeur parente, quand la valeur est **hiérarchiquement rattachée** à une autre (vide = valeur racine). |
| `ordre` | Entier d'affichage, pour trier la liste dans un menu déroulant sans dépendre de l'alphabet. |
| `domaine` | L'**axe métier** auquel appartient la valeur à l'intérieur du jeu (`nature_travaux`, `type_ouvrage`, `technique`…). Voir § 0.2. |
| `source` | D'où vient la valeur : document officiel cité précisément, document de phase 1, ou « décision d'Anthony ». Voir § 4. |
| `statut` | Niveau de confiance de la valeur. Voir § 0.3. |

**Ce document ne définit aucun schéma.** Il n'invente ni table, ni type, ni contrainte :
il remplit des valeurs dans ce format. Le conteneur générique appartient à
`docs/DATA-MODEL-V2.md`.

### 0.2 Ce qu'est le champ `domaine` — et ce qu'il n'est pas

Le namespace `metier.etancheite` regroupe **plusieurs axes métier**. Chaque axe est
présenté ci-dessous comme **une table de lecture**. Ces tables sont des **vues de
lecture d'un même namespace**, pas des tables de base de données : découper en axes est
une décision de **contenu** (quels sont les axes du métier), pas une décision de
**structure**. Si le modèle v2 organise le stockage autrement, c'est lui qui fait foi et
ces valeurs s'y chargent sans changement de sens.

### 0.3 Convention de `statut` adoptée ici

`statut` est un champ imposé par D-C1, mais ses valeurs possibles ne sont pas définies par
la structure. Convention adoptée dans ce document, **proposée** au lot L3 :

| `statut` | Sens |
|---|---|
| `propose` | Valeur proposée par l'équipe, ni confirmée par Anthony, ni vérifiée à la source à la date d'usage. C'est le statut **par défaut** de cette nomenclature. |
| `a_verifier` | Valeur dont le code, le libellé ou la validité **peut évoluer** et doit être contrôlé contre la source en vigueur avant tout usage dans un livrable produit. |
| `a_valider_anthony` | Valeur qui relève d'un choix métier qu'Anthony seul peut trancher (périmètre, priorités, habitudes de l'entreprise). |
| `valide` | Valeur confirmée par Anthony à la date indiquée, ou lue sur un document officiel cité et daté. |

> Ces quatre mots sont une **convention de lecture**, pas une contrainte technique. Le lot
> L3 peut retenir un autre vocabulaire ; il devra alors le documenter dans
> `docs/DATA-MODEL-V2.md`, qui fait foi pour la structure.

---

## 1. Premier jeu de référence métier : `metier.etancheite`

Ce jeu décrit le vocabulaire propre au **métier de l'étanchéité**, tel qu'il ressort de
`docs/DONNEES-METIER-BATIMENT.md` (phase 1). Il sert à trois usages :

1. **saisir** une référence de chantier avec le vocabulaire du métier, pas des
   formulations vagues ;
2. **apparier** une consultation (DCE) avec les références et les qualifications que
   l'entreprise détient réellement ;
3. **restituer** ces informations dans un dossier de réponse, avec un libellé lisible.

> **Aucune valeur de ce jeu ne présume qu'une entreprise détient quoi que ce soit.**
> La liste est un référentiel de vocabulaire proposé. C'est l'entreprise qui coche,
> saisit et prouve.

### 1.1 `domaine = nature_travaux` — la nature des travaux

C'est le critère d'appariement le plus fin avec un DCE : « surface » seule ne dit pas la
compétence. *Source : `DONNEES-METIER-BATIMENT.md` § 1.2 (vocabulaire métier).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `nt.terrasse.neuve` | Étanchéité de toiture-terrasse — ouvrage neuf | — | 10 | nature_travaux | DMB § 1.2 | propose |
| `nt.terrasse.refection` | Réfection d'étanchéité de toiture-terrasse (dépose ou conservation de l'existant selon le procédé) | — | 20 | nature_travaux | DMB § 1.2 | propose |
| `nt.releve` | Relevés d'étanchéité (périphérie, émergences, acrotères) | — | 30 | nature_travaux | DMB § 1.2 | propose |
| `nt.points_singuliers` | Traitement des points singuliers | — | 40 | nature_travaux | DMB § 1.2 | propose |
| `nt.isolation_rapportee` | Isolation thermique rapportée sous étanchéité (complexe isolant + étanchéité + protection) | — | 50 | nature_travaux | DMB § 1.2 | propose |
| `nt.protection` | Mise en œuvre d'une protection de l'étanchéité | — | 60 | nature_travaux | DMB § 1.2 | propose |
| `nt.sel` | Étanchéité liquide (S.E.L.) | — | 70 | nature_travaux | DMB § 1.2 | propose |
| `nt.cuvelage` | Cuvelage / étanchéité enterrée | — | 80 | nature_travaux | DMB § 1.2 | propose |
| `nt.plancher_intermediaire` | Étanchéité de plancher intermédiaire (locaux humides) | — | 90 | nature_travaux | DMB § 1.2 | propose |
| `nt.raccord_support` | Raccord d'étanchéité sur support particulier (bois, bac acier, béton) | — | 100 | nature_travaux | DMB § 1.2 | propose |
| `nt.toiture_inclinee` | Étanchéité de toiture inclinée | — | 110 | nature_travaux | DMB § 1.2 | propose |

> **Point de vocabulaire à trancher par Anthony :** la frontière entre `nt.terrasse.refection`
> et `nt.terrasse.neuve`, et la place exacte des **relevés** (ligne à part, ou sous-nature
> d'une réfection). La phase 1 les traite comme un poste à part — « souvent oublié au
> chiffrage ». À confirmer (§ 6, point 2).

### 1.2 `domaine = type_ouvrage` — le type de support / d'ouvrage

C'est ce qui détermine le **DTU applicable** et la difficulté technique.
*Source : `DONNEES-METIER-BATIMENT.md` § 1.1 (« Type d'ouvrage »).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `to.toiture` | Toiture (terrasse ou inclinée) | — | 10 | type_ouvrage | DMB § 1.1 | propose |
| `to.toiture_terrasse` | Toiture-terrasse | `to.toiture` | 20 | type_ouvrage | DMB § 1.1 | propose |
| `to.toiture_inclinee` | Toiture inclinée | `to.toiture` | 30 | type_ouvrage | DMB § 1.1 | propose |
| `to.plancher_intermediaire` | Plancher intermédiaire (locaux humides) | — | 40 | type_ouvrage | DMB § 1.1 | propose |
| `to.balcon_terrasse` | Balcon, terrasse de faible surface | — | 50 | type_ouvrage | DMB § 1.2 (SEL) | propose |
| `to.local_humide` | Local humide (salle d'eau) | — | 60 | type_ouvrage | DMB § 1.2 (SEL) | propose |
| `to.ouvrage_enterre` | Ouvrage enterré | — | 70 | type_ouvrage | DMB § 1.1 | propose |
| `to.cuvelage` | Cuvelage (réservoir, cuve, bassin) | `to.ouvrage_enterre` | 80 | type_ouvrage | DMB § 1.1 | propose |
| `to.bassin_piscine` | Bassin de piscine | `to.ouvrage_enterre` | 90 | type_ouvrage | DMB § 1.1 | propose |

> Les rattachements `to.cuvelage` / `to.bassin_piscine` sous `to.ouvrage_enterre`, et
> l'existence de `to.toiture` comme parent, sont des **propositions de rangement** : la
> phase 1 cite les types d'ouvrage sans hiérarchie. À valider (§ 6, point 2).

### 1.3 `domaine = technique` — le procédé ou le système mis en œuvre

C'est ce qui relie une référence de chantier aux **qualifications détenues** (§ 1.10) et
aux **avis techniques** des produits utilisés. Un référentiel doit citer **le système
complet**, pas le produit isolé : élément porteur, pare-vapeur, isolant, revêtement
d'étanchéité, relevés, protection, fixations.
*Source : `DONNEES-METIER-BATIMENT.md` § 1.1 et § 2.1 (découpage par technique).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `tq.bitumineux_feuilles` | Étanchéité en matériaux bitumineux en feuilles | — | 10 | technique | DMB § 1.1, § 2.1 | propose |
| `tq.synthese_feuilles` | Étanchéité en matériaux de synthèse en feuilles (ex. PVC, TPO) | — | 20 | technique | DMB § 1.1, § 2.1 | propose |
| `tq.asphalte_coule` | Étanchéité en asphalte coulé | — | 30 | technique | DMB § 1.1, § 2.1 | propose |
| `tq.sel_liquide` | Étanchéité liquide (S.E.L.) | — | 40 | technique | DMB § 1.1, § 2.1 | propose |
| `tq.tan` | Tôle d'acier nervurée (TAN) avec étanchéité en membrane en feuilles | — | 50 | technique | DMB § 1.1, § 2.1 | propose |
| `tq.terrasse_specialisee` | Toitures-terrasses spécialisées (dont végétalisées) | — | 60 | technique | DMB § 1.1, § 2.1 | propose |

> **À compléter par Anthony :** la liste des systèmes réellement pratiqués par l'entreprise,
> par fabricant et par marque de système. La nomenclature ne peut pas la deviner. La
> désignation exacte se lit au **catalogue du fabricant**, jamais de mémoire.

### 1.4 `domaine = point_singulier` — les points singuliers

C'est, techniquement, **le poste qui fait la différence** entre une entreprise d'étanchéité
et un poseur de membranes. Il est aussi le plus souvent oublié au chiffrage.
*Source : `DONNEES-METIER-BATIMENT.md` § 1.1 (« linéaire de relevés / points singuliers »),
§ 1.2 et § 7.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `ps.releve` | Relevé d'étanchéité (ml) | — | 10 | point_singulier | DMB § 1.1 | propose |
| `ps.emergence` | Émergence (remontée autour d'un élément traversant) | — | 20 | point_singulier | DMB § 1.1 | propose |
| `ps.boite_a_eau` | Boîte à eau | — | 30 | point_singulier | DMB § 1.1 | propose |
| `ps.crapaudine` | Crapaudine | — | 40 | point_singulier | DMB § 1.1 | propose |
| `ps.joint_de_dilatation` | Joint de dilatation | — | 50 | point_singulier | DMB § 1.1 | propose |
| `ps.penetration` | Pénétration (ventilation, gaine) | — | 60 | point_singulier | DMB § 1.1 | propose |
| `ps.evacuation_ep` | Dispositif d'évacuation des eaux pluviales | — | 70 | point_singulier | DMB § 1.2 | propose |

> **Unité de compte.** Ces points se comptent en **ml** (relevés, joints) ou en **nombre**
> de pièces (boîtes à eau, crapaudines, pénétrations). Cette distinction est un contenu
> métier, pas une décision de structure : elle doit rester portée par la valeur (voir le jeu
> transverse `unite.mesure`, § 3).

### 1.5 `domaine = protection` — la protection de l'étanchéité

*Source : `DONNEES-METIER-BATIMENT.md` § 1.2 (« Protection »).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `pr.gravillon` | Protection gravillon | — | 10 | protection | DMB § 1.2 | propose |
| `pr.dallettes` | Protection dallettes | — | 20 | protection | DMB § 1.2 | propose |
| `pr.autoprotege` | Complexe autoprotégé | — | 30 | protection | DMB § 1.2 | propose |
| `pr.vegetalisation` | Végétalisation | — | 40 | protection | DMB § 1.2 | propose |

### 1.6 `domaine = materiau_isolant` — l'isolant du complexe

*Source : `DONNEES-METIER-BATIMENT.md` § 1.1 (« Nature et épaisseur de l'isolant »). La
phase 1 cite deux exemples ; la liste est **ouverte**.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `is.pir` | Panneau isolant PIR | — | 10 | materiau_isolant | DMB § 1.1 (exemple) | propose |
| `is.laine_minerale` | Panneau isolant en laine minérale | — | 20 | materiau_isolant | DMB § 1.1 (exemple) | propose |
| `is.autre` | Autre isolant (à préciser : marque, référence, épaisseur) | — | 90 | materiau_isolant | décision d'Anthony (à fournir) | a_valider_anthony |

> La **valeur** `is.autre` existe exprès : le référentiel ne peut pas fermer une liste de
> matériaux qui évolue avec les catalogues. L'entreprise saisit le libellé exact du produit
> utilisé. `is.autre` doit être **reclassée** en valeur propre par Anthony quand un matériau
> revient souvent (§ 6, point 3).

### 1.7 `domaine = definition_surface` — quelle surface, et en quelle unité

C'est le piège de métré signalé dès la phase 1 : « une surface annoncée sans définition
n'est pas exploitable ». *Source : `DONNEES-METIER-BATIMENT.md` § 1.1 (« Surface ») et § 1.4.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `srf.toiture` | Surface de toiture (projection horizontale) | — | 10 | definition_surface | DMB § 1.1 | propose |
| `srf.developpee` | Surface développée (relevés et émergences inclus) | — | 20 | definition_surface | DMB § 1.1 | propose |
| `srf.utile` | Surface utile | — | 30 | definition_surface | DMB § 1.1 | propose |

### 1.8 `domaine = assiette_montant` — ce que couvre un montant déclaré

Un montant non cadré est inutilisable en commission. *Source : `DONNEES-METIER-BATIMENT.md`
§ 1.1 (« Montant ») et § 1.4.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `amt.travaux_seuls` | Prestation de travaux seule | — | 10 | assiette_montant | DMB § 1.1 | propose |
| `amt.avec_echafaudage` | Prestation avec échafaudage | — | 20 | assiette_montant | DMB § 1.1 | propose |
| `amt.avec_depose_evacuation` | Prestation avec dépose et évacuation | — | 30 | assiette_montant | DMB § 1.1 | propose |

> **Rappel de ligne rouge.** Cette nomenclature **ne fixe aucun prix** et ne porte aucun
> montant : elle décrit seulement **ce que couvre** un montant que l'entreprise déclare.
> Les montants déclarés sont en **€ HT** ; la nomenclature ne préjuge ni de la TVA, ni
> d'un taux.

### 1.9 `domaine = condition_execution` — les conditions d'exécution

Ce sont les contraintes qui prouvent l'expérience réelle, en particulier en site occupé.
*Source : `DONNEES-METIER-BATIMENT.md` § 1.1 (« Durée » et « Conditions d'exécution »).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `ce.site_occupe` | Exécution en site occupé | — | 10 | condition_execution | DMB § 1.1 | propose |
| `ce.site_libre` | Exécution en site libre | — | 20 | condition_execution | DMB § 1.1 | propose |
| `ce.travail_en_hauteur` | Travail en hauteur | — | 30 | condition_execution | DMB § 1.1 | propose |
| `ce.acces_difficile` | Accès difficile | — | 40 | condition_execution | DMB § 1.1 | propose |
| `ce.moyen_de_levage` | Recours à un moyen de levage (grue, monte-charge) | — | 50 | condition_execution | DMB § 1.1 | propose |
| `ce.vacances_scolaires` | Exécution pendant les vacances scolaires | — | 60 | condition_execution | DMB § 1.1 | propose |
| `ce.phasage_tranches` | Phasage par tranches | — | 70 | condition_execution | DMB § 1.1 | propose |

### 1.10 `domaine = qualification_qualibat` — qualifications Qualibat

**Ce bloc est le plus sensible du document.** Il ne dit **pas** ce que l'entreprise détient :
il donne le **vocabulaire des codes** pour que la saisie se fasse par lecture du certificat.
La règle de la phase 1 est reprise telle quelle : **ne jamais déduire une qualification du
métier déclaré** ; la liste se lit **sur le certificat**, jamais au raisonnement.

*Source : `DONNEES-METIER-BATIMENT.md` § 2.1, elle-même adossée à la nomenclature Qualibat
(source citée au § 7 du présent document). Codes et libellés **à re-vérifier contre la
nomenclature en vigueur** le jour de la saisie : ils évoluent.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `3` | Enveloppe extérieure (famille Qualibat) | — | 10 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `32` | Étanchéité (activité) | `3` | 20 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `33` | Étanchéité et imperméabilisation des cuvelages, réservoirs, cuves et bassins (activité) | `3` | 30 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `321` | Étanchéité en matériaux bitumineux en feuilles | `32` | 40 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `322` | Étanchéité en matériaux de synthèse en feuilles | `32` | 50 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `323` | Étanchéité en asphaltes coulés | `32` | 60 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `324` | Étanchéité liquide (S.E.L.) | `32` | 70 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `327` | Tôle d'acier nervurée (TAN) avec étanchéité en membrane en feuilles | `32` | 80 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `329` | Toitures-terrasses spécialisées (dont végétalisées) | `32` | 90 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `331` | Étanchéité et imperméabilisation de cuvelages, réservoirs, cuves et bassins de piscines | `33` | 100 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `332` | Étanchéité et imperméabilisation de cuvelages, réservoirs, cuves et bassins de piscines | `33` | 110 | qualification_qualibat | DMB § 2.1 | a_verifier |
| `337` | Étanchéité et imperméabilisation de cuvelages, réservoirs, cuves et bassins de piscines | `33` | 120 | qualification_qualibat | DMB § 2.1 | a_verifier |

> **Ne pas inventer les 4e chiffres.** Le code complet d'une qualification est écrit sur le
> certificat et se compose de quatre chiffres : famille, métier/activité, spécialité, puis
> **niveau de technicité**. La phase 1 donne un exemple de code complet — `3212` — à titre
> d'illustration de format. Le présent document **ne reconstitue pas** les codes à quatre
> chiffres : la bibliothèque stocke **le code exact tel qu'imprimé sur le certificat**,
> jamais un code complété au raisonnement.
>
> De même, les libellés ci-dessus sont ceux **du document de phase 1**. Qualibat peut les
> avoir reformulés : avant tout usage dans un livrable produit, relire la nomenclature
> officielle en vigueur (§ 4 et § 6, point 1).

### 1.11 `domaine = niveau_technicite` — le niveau de technicité Qualibat

Un niveau « courante » ne couvre pas les chantiers d'un niveau « supérieure » : c'est un
point de contrôle, pas une décoration. Les libellés exacts se lisent sur la nomenclature
Qualibat en vigueur.

*Source : `DONNEES-METIER-BATIMENT.md` § 2.1. **Aucun libellé officiel n'est reproduit ici
volontairement** : seul l'ordre des niveaux est repris du document de phase 1.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `ntc.courante` | Niveau de technicité « courante » (libellé officiel à lire à la source) | — | 10 | niveau_technicite | DMB § 2.1 | a_verifier |
| `ntc.confirmee` | Niveau de technicité « confirmée » (libellé officiel à lire à la source) | — | 20 | niveau_technicite | DMB § 2.1 | a_verifier |
| `ntc.superieure` | Niveau de technicité « supérieure » (libellé officiel à lire à la source) | — | 30 | niveau_technicite | DMB § 2.1 | a_verifier |
| `ntc.exceptionnelle` | Niveau de technicité « exceptionnelle » (libellé officiel à lire à la source) | — | 40 | niveau_technicite | DMB § 2.1 | a_verifier |

> **Mentions portées par un certificat** (ex. `E.C.`, `NAT`, `RGE P` citées par la phase 1) :
> elles ne sont pas reprises comme valeurs, car leur **signification doit être reprise
> littéralement du document Qualibat** et la phase 1 elle-même les classe « à confirmer »
> (§ 6, point 1). La bibliothèque les stockera comme **texte lu sur le certificat**, sans
> interprétation.

### 1.12 `domaine = norme_applicable` — les DTU cités par la phase 1

Ce bloc n'est **pas** une prescription : c'est le vocabulaire des références DTU citées par
le métier dans le document de phase 1, pour que la bibliothèque puisse rattacher un système
ou un ouvrage à une référence normative **lue à la source**.

*Source : `DONNEES-METIER-BATIMENT.md` § 6.2. La phase 1 demande explicitement de confirmer
la liste et les numéros de normes NF P 84-… auprès d'AFNOR / CSTB avant toute citation dans
un livrable produit (§ 6, point 4 du présent document).*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `dtu.43.1` | NF DTU 43.1 — étanchéité des toitures avec éléments porteurs en maçonnerie / climat de plaine | — | 10 | norme_applicable | DMB § 6.2 | a_verifier |
| `dtu.43.3` | DTU 43.3 — partie de la série 43 relative à d'autres supports (intitulé exact à lire à la source) | — | 20 | norme_applicable | DMB § 6.2 | a_verifier |
| `dtu.43.4` | NF DTU 43.4 — toitures en éléments porteurs bois et dérivés avec revêtements d'étanchéité | — | 30 | norme_applicable | DMB § 6.2 | a_verifier |
| `dtu.43.5` | NF DTU 43.5 — réfection des ouvrages d'étanchéité des toitures-terrasses ou inclinés | — | 40 | norme_applicable | DMB § 6.2 | a_verifier |
| `dtu.43.6` | NF DTU 43.6 — étanchéité des planchers intérieurs en maçonnerie par produits hydrocarbonés | — | 50 | norme_applicable | DMB § 6.2 | a_verifier |
| `dtu.43.11` | NF DTU 43.11 — étanchéité des toitures-terrasses et toitures inclinées | — | 60 | norme_applicable | DMB § 6.2 | a_verifier |

> **Ne pas généraliser.** Le présent document **ne dit pas** quel DTU s'applique à quel
> chantier, et **ne tranche pas** la question des **règles de vent et de fixation en zone
> cyclonique** (La Réunion) : ce point est hors de sa compétence et relève du bureau
> d'études / du maître d'œuvre, avec des documents exacts à l'appui (phase 1 § 6.2 et § 9,
> point 4 ; § 6 du présent document). La valeur `dtu.43.x` sert à **nommer** une référence,
> pas à l'imposer.

---

## 2. Le patron d'extension, démontré

La décision **D2** veut un produit **généraliste dès le départ**. Voici ce que cela signifie
concrètement : **aucune migration de base, aucun changement de schéma** pour ajouter un
métier ou une valeur.

### 2.1 Ajouter une valeur à un jeu existant

Cas le plus courant. Exemple **fictif** :

```
EXEMPLE FICTIF — aucune entreprise réelle n'est visée
Le fournisseur de l'entreprise utilise un isolant qui n'est pas dans la liste (§ 1.6).
On ajoute une valeur au jeu `metier.etancheite`, domaine `materiau_isolant` :

code        : is.exemple_fictif
libelle     : Panneau isolant [désignation exacte du catalogue] [fictif]
parent_code : (vide)
ordre       : 30
domaine     : materiau_isolant
source      : décision d'Anthony
statut      : valide
```

Ce qu'il faut faire : **une ligne**. Ce qu'il ne faut **pas** faire : toucher au code des
valeurs existantes (les données déjà saisies y font référence), ni redéfinir un champ.

### 2.2 Ajouter un métier — exemple esquissé `metier.menuiserie`

Même format, **même structure**, namespace différent. Le contenu ci-dessous est
**fictif et volontairement incomplet** : il ne montre que la mécanique, pas un vrai
référentiel de menuiserie.

*Exemple fictif — aucune donnée réelle, aucune référence de produit, aucun code de
qualification n'est affirmé.*

| code | libelle | parent_code | ordre | domaine | source | statut |
|---|---|---|---|---|---|---|
| `nt.fenetre.depose_pose` | Dépose et pose de fenêtres [exemple fictif] | — | 10 | nature_travaux | exemple fictif | propose |
| `to.fenetre` | Fenêtre [exemple fictif] | — | 20 | type_ouvrage | exemple fictif | propose |
| `tq.bois` | Menuiserie bois [exemple fictif] | — | 30 | technique | exemple fictif | propose |
| `tq.pvc` | Menuiserie PVC [exemple fictif] | — | 40 | technique | exemple fictif | propose |
| `tq.aluminium` | Menuiserie aluminium [exemple fictif] | — | 50 | technique | exemple fictif | propose |
| `is.autre` | Isolant / vitrage à préciser [exemple fictif] | — | 90 | materiau_isolant | exemple fictif | propose |

> Créer `metier.menuiserie` = **créer un namespace et y poser des lignes**. Ni la structure,
> ni le code, ni la base ne changent. C'est exactement ce que D2 exige.
>
> Le patron marche pour le gros œuvre, l'électricité, la plomberie ou tout autre métier.
> Il marche aussi pour un **métier non encore identifié** : le jour où un client arrive avec
> un lot que personne n'a anticipé, on crée son namespace et on saisit son vocabulaire —
> sans migration.

### 2.3 Ce que le patron d'extension n'exige pas

- Pas de **table** à créer par métier, pas de **colonne** à ajouter.
- Pas de **migration** : les namespaces coexistent, les données existantes restent valides.
- Pas de **redéploiement** ou de **correction de code** : c'est une opération de données.
- Pas de **décision d'architecture** : c'est une opération de **contenu**, qui appartient au
  métier et à l'entreprise, pas à l'informatique.

### 2.4 Ce que le patron d'extension exige en revanche

- **une règle de `code`** : dans un jeu donné, un `code` ne doit jamais être réutilisé pour
  un autre sens. On ajoute, on ne recycle pas. Une valeur qu'on ne veut plus est retirée de
  l'affichage par son `statut`, pas effacée ;
- **une règle de `source`** : toute valeur ajoutée porte sa source (§ 4) ;
- **une validation métier** : c'est Anthony (ou le professionnel du métier concerné) qui
  valide les libellés, pas l'IA ;
- **rien sur le juridique** : les jeux transverses de nature juridique (§ 3) ne se créent
  pas par ajout libre — ils viennent d'une source officielle ou d'un juriste.

---

## 3. Jeux de référence transverses nécessaires

Ces jeux ne sont **pas** métier : ils sont communs à toutes les entreprises, quel que soit
le métier. Ils sont **nécessaires** au produit, mais leur **contenu n'appartient pas à ce
document** : c'est de la matière juridique ou administrative, qui ne se devine pas.

**Règle posée ici : aucun contenu juridique inventé.** Pour chaque jeu, la colonne
« qui fournit » dit qui doit produire la liste, et, à défaut de source identifiée, la
mention **à vérifier**.

| namespace proposé | Ce qu'il contient | Qui doit fournir la liste | Statut |
|---|---|---|---|
| `type.document` | Types de pièces d'un dossier (attestations, CV, références, certificats, pièces administratives) | **Juriste** + `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` (lot L4) pour les pièces exigées ; source administrative officielle pour les formats | à vérifier — ne pas figer avant expertise (D4) |
| `type.marche` | Types de marchés publics (procédures, seuils, formes) | **Source administrative officielle** (textes en vigueur — base Légifrance / fiches officielles) ; **juriste** pour la lecture | à vérifier |
| `type.lot` | Types de lots / découpage en lots | **Décision d'Anthony** pour le vocabulaire métier ; nomenclature officielle (CPV) **à vérifier** si le produit s'y adosse | à vérifier |
| `forme.juridique` | Formes juridiques d'entreprise (statuts) | **Source administrative officielle** (référentiel officiel des formes juridiques — code INSEE / Sirene, à vérifier) ; **juriste** | à vérifier |
| `unite.mesure` | Unités de mesure et de métré (m², ml, m³, U, forfait, jour, ensemble) | **Décision d'Anthony** pour la liste utilisée par les métiers du bâtiment | propose — liste courte à valider |
| `famille.metier` | Familles de métiers du bâtiment (la nomenclature des namespaces `metier.*`) | **Décision d'Anthony** (périmètre commercial, D1) + rattachement éventuel à une nomenclature officielle **à vérifier** | à vérifier |
| `signe.qualite` | Signes de qualité **transverses** (Qualibat toutes familles, RGE, MASE, ISO 9001 / 14001 / 45001…) | **Sources des organismes émetteurs**, citées et datées (Qualibat, association MASE, ministère pour le RGE) ; **juriste** pour les mentions réglementaires | à vérifier contre les nomenclatures en vigueur |
| `rh.habilitation` | Habilitations et formations individuelles (travail en hauteur, CACES, SST, habilitations électriques, AIPR…) | **Source administrative officielle** pour les intitulés officiels ; **décision d'Anthony** pour celles utiles au métier | à vérifier |
| `type.maitre_ouvrage` | Nature du maître d'ouvrage (public / privé, et sous-catégories) | **Juriste** pour les catégories juridiques ; **décision d'Anthony** pour le niveau de détail utile | à vérifier |
| `parametre.fiscal` | Devises, régimes de TVA et taux applicables | **Source administrative officielle** (taux en vigueur) ; **juriste** ; au cas par cas selon le territoire et l'opération | à vérifier — aucun taux n'est écrit dans ce document |

> **Pourquoi ces jeux ne sont pas remplis ici.** Ils sont de **nature juridique,
> administrative ou fiscale**. Les inventer serait exactement l'erreur que la phase 1 a
> interdite (« n'invente aucune norme, aucun code, aucun seuil, aucune liste juridique »).
> Ils sont listés pour être **commandés nommément** à qui de droit — pas devinés.
>
> Les jeux marqués **à vérifier** bloquent tout usage en production tant que la source n'a
> pas été citée. C'est un point de contrôle pour le lot L6 (revue) et pour la phase 3.

---

## 4. Règle de sourçage de nos propres valeurs

Toute valeur de cette nomenclature porte un `source` et un `statut`. La règle est simple :

1. **Une valeur technique ne se cite jamais de mémoire.** Elle est rattachée à un document
   officiel cité précisément (organisme, document, date de consultation) — voir § 7.
2. **Une valeur de convention interne** (ordre des libellés, rangement d'un axe, choix de
   vocabulaire) est marquée **« décision d'Anthony »** ou **« décision d'équipe »**, jamais
   rattachée à une source officielle qu'elle n'a pas.
3. **Une valeur reprise de la phase 1** porte la référence `DMB § …`, c'est-à-dire
   `docs/DONNEES-METIER-BATIMENT.md`. Ce renvoi signifie « le cadrage de phase 1 disait ceci »,
   pas « la source officielle a été revérifiée aujourd'hui ».
4. **Tout code susceptible d'évoluer** (certifications, qualifications, normes, taux) est
   marqué `a_verifier`, avec la mention **« à vérifier contre la nomenclature en vigueur »**.
5. **Les codes de certification et de qualification** (Qualibat, RGE, MASE, ISO) sont
   **sourcés et datés** : la source de phase 1 est datée du 30 septembre 2026 (§ 7). Toute
   réutilisation dans un livrable produit exige une **relecture à la date de l'usage**.
6. **Aucune valeur n'est présentée comme une garantie.** Une valeur présente dans un jeu
   signifie « ce vocabulaire existe », jamais « l'entreprise possède ».

### 4.1 Statut de sourçage des jeux de ce document

| Jeu | Sourçage | Statut du document |
|---|---|---|
| `metier.etancheite` (§ 1) | `docs/DONNEES-METIER-BATIMENT.md` (phase 1, 30/09/2026), adossé aux sources listées § 7 | **proposé** — contenu métier à valider par Anthony |
| `metier.menuiserie` (§ 2.2) | **exemple fictif**, aucune source | **démonstration seulement** — ne pas charger en production |
| Jeux transverses (§ 3) | **aucun contenu produit** — listes à commanditer | **à fournir** |

---

## 5. Ce que cette nomenclature n'est pas

- **Elle ne fixe aucun prix**, aucune marge, aucun seuil, aucune durée, aucun taux de TVA.
- **Elle ne garantit aucune conformité** : ni à un DTU, ni à un avis technique, ni à un
  règlement de consultation, ni à une assurance.
- **Elle ne présume pas qu'une entreprise détient une qualification, une certification, une
  habilitation ou une assurance.** Une valeur présente dans un jeu décrit un **vocabulaire**,
  pas un **droit** ni un **fait**.
- **Elle ne remplace aucune source officielle** : ni la nomenclature Qualibat en vigueur,
  ni un DTU, ni un avis technique (ATec / DTA), ni un texte de loi, ni un règlement de
  consultation.
- **Elle n'énonce aucune garantie de confidentialité.** Sur ce sujet, seul
  `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` est habilité (D-C2) — *à compléter après
  validation*.
- **Elle ne dit rien de l'aptitude d'une entreprise à répondre à une consultation
  donnée.** La lecture d'un DCE et la décision de concourir restent humaines.

**Les valeurs sont proposées. L'entreprise valide.** Ce qui est saisi dans la bibliothèque
d'entreprise n'est opposable que si l'entreprise l'a confirmé et peut produire sa pièce
justificative (certificat, attestation, PV de réception, facture, photo).

---

## 6. Points ouverts

À confirmer par **Anthony** ou par un **juriste**. Aucun de ces points n'est tranché par le
présent document.

1. **Nomenclature Qualibat en vigueur** (juriste / vérification documentaire) : les codes
   `3`, `32`, `33`, `321`… `337` et les niveaux de technicité (§ 1.10, § 1.11) proviennent
   du document de phase 1, adossé à une nomenclature datée du 30/09/2026. À **re-vérifier
   contre la nomenclature officielle** avant tout usage produit. La signification des
   mentions portées par les certificats (`E.C.`, `NAT`, `RGE P`…) doit être reprise
   **littéralement** de la source, sans interprétation.
2. **Découpage métier et rattachements** (Anthony) : la frontière
   `nt.terrasse.neuve` / `nt.terrasse.refection`, le statut des relevés comme nature de
   travaux à part entière, et les rattachements `parent_code` proposés aux § 1.2 et § 1.1
   sont des **propositions de rangement** à valider.
3. **Liste des isolants et des systèmes** (Anthony) : les listes des § 1.3 et § 1.6 sont
   volontairement ouvertes (`is.autre`). Anthony doit fournir les matériaux et systèmes
   réellement pratiqués, par fabricant, pour remplacer les valeurs provisoires.
4. **Liste et numéros exacts des DTU 43.x** (vérification documentaire, source AFNOR / CSTB) :
   la phase 1 demande explicitement de confirmer la liste et les numéros de normes
   NF P 84-… avant toute citation dans un livrable produit (§ 1.12).
5. **Règles de vent et de fixation en zone cyclonique (La Réunion)** : **hors compétence**
   de ce document. À traiter avec le bureau d'études / le maître d'œuvre, et à documenter
   par une source exacte. Aucune règle de vent n'est citée ni appliquée ici.
6. **Vocabulaire du `statut`** (lot L3, `docs/DATA-MODEL-V2.md`) : les quatre valeurs
   proposées au § 0.3 sont une convention de lecture. Le lot L3 fait foi pour la structure
   et peut en retenir d'autres.
7. **Jeux transverses** (§ 3) : chacun est **à commanditer** — juriste, source
   administrative officielle, ou décision d'Anthony, selon la colonne « qui fournit ».
   Aucun n'est utilisable en production tant que sa source n'est pas citée et datée.
8. **Périmètre commercial** (Anthony, phase 3) : la bibliothèque est généraliste (D2) mais
   la cible commerciale de départ reste le bâtiment (D1). La liste `famille.metier` (D1)
   reste une question ouverte du plan de phase 2.
9. **Pertinence du RGE selon l'objet** (Anthony) : la mention RGE n'est pas systématiquement
   demandée sur un marché d'étanchéité ; sa pertinence dépend de l'objet (isolation de
   toiture, performance énergétique). À décider au cas par cas, dans le jeu transverse
   `signe.qualite`, jamais présumé ici.

---

## 7. Sources citées

Sources publiques, telles que citées par `docs/DONNEES-METIER-BATIMENT.md` (phase 1),
consultées le **30 septembre 2026**. Elles n'ont **pas** été re-consultées pour la rédaction
du présent document : leur contenu est repris via le document de phase 1, et chaque code ou
libellé susceptible d'évoluer est marqué `a_verifier`. Toute réutilisation en production
exige une **relecture à la date de l'usage**.

| Source | Objet | Référence |
|---|---|---|
| `docs/DECISIONS.md` (interne, 30/09/2026) | Décisions D1 à D6, dont D2 (généraliste) et D6 (hébergement / confidentialité) | Dossier projet |
| `docs/DONNEES-METIER-BATIMENT.md` (interne, phase 1, 30/09/2026) | Contenu métier étanchéité à l'origine du jeu `metier.etancheite` | Dossier projet |
| `docs/PLAN-PHASE-2.md` (interne, 30/09/2026) | Décisions d'orchestrateur D-C1 (format des jeux) et D-C2 (autorité sur la confidentialité) | Dossier projet |
| Qualibat — nomenclature et niveaux de technicité | Codes et familles de qualification (§ 1.10, § 1.11) | <https://www.qualibat.com/nomenclature-qualibat> — **à re-vérifier à la date d'usage** |
| RGE — Reconnu Garant de l'Environnement | Mention RGE et son adossement à une qualification (§ 3, § 6 point 9) | Ministère de la Transition écologique ; Service Public Entreprendre <https://entreprendre.service-public.gouv.fr/vosdroits/F32251> — **à vérifier** |
| MASE | Référentiel de management SSE, version V2024, calendrier d'audit | <https://mase-asso.fr> — **à confirmer auprès de l'association MASE** |
| Assurances construction | Loi n° 78-12 du 4 janvier 1978 (Spinetta) ; art. L241-1, L242-1, L243-3 du Code des assurances ; art. 1792 et s. du Code civil | Textes consolidés sur <https://www.legifrance.gouv.fr> |
| DTU 43 — étanchéité des toitures | Liste des documents de la série (§ 1.12) | AFNOR / CSTB font foi — liste **à vérifier** |
| Avis Techniques (ATec) et DTA | Nature et portée d'un avis technique ; liste verte C2P (AQC) | CSTB, <https://www.cstb.fr> |

> **Rappel de méthode.** Ce document est un livrable de phase 2 (conception). Il ne remplace
> ni un DTU, ni un avis technique, ni une attestation d'assurance, ni un règlement de
> consultation, ni une nomenclature officielle. Toute citation de norme, de seuil, de code
> ou de référence dans un livrable produit devra être **revérifiée à la source** au moment
> de son usage.
