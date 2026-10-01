# MÉMOIRE-ATTENDU — Ce qu'un jury note réellement dans un mémoire technique

*Livrable du lot **L1** (agent `batiment`), phase 4 — chantier A. Board : `ia-consultations`.
Dossier : `/Users/pause/Projets/ia-consultations-publiques`. Écrivain unique de ce fichier.*

> **Rôle de ce document.** Il décrit **ce qu'un mémoire technique de bâtiment / étanchéité
> doit contenir, dans quel ordre, et de quoi la bibliothèque d'entreprise a besoin pour
> l'étayer** — pour qu'une commission d'appel d'offres lui attribue des points. C'est la
> **matière métier** du moteur de génération (lot L2) et de la grille de relecture.
>
> **Ce que ce document n'est pas.** Il ne rédige pas un mémoire, ne propose aucun modèle
> prêt à recopier, ne chiffre rien, ne fixe ni prix, ni marge, ni seuil, ni tolérance. Il
> ne dit rien de la **notation côté acheteur** (c'est le rôle de `docs/JURY-ACHETEUR.md`,
> lot L1b). Il ne dit rien de la **structure technique** des données (c'est `docs/DATA-MODEL-V2.md`,
> qui fait foi ; en cas de divergence, c'est lui qui l'emporte).

---

## Avertissement — exemples fictifs, périmètre générique, ligne rouge

**Tous les exemples de ce document sont fictifs et signalés comme tels.** Aucun nom de
client, aucune référence de chantier, aucun montant, aucune surface, aucune date réelle
ne figure ici. Les valeurs entre crochets `[…]` ne sont que des ordres de grandeur de
*format* : elles n'ont aucune valeur métier et ne doivent pas être reprises.

Périmètre : ce document est **générique** (décision D2 — client cible = entreprises du
bâtiment, généraliste). Le vocabulaire d'étanchéité y est employé comme **premier jeu de
référence**, jamais comme une hypothèse de structure. Il ne contient **aucune donnée issue
d'un marché réel, d'un document d'acheteur réel ni de la collectivité** (D4, D10) : le lot
M 240219 et les écoles du Brûlé / La Source sont un contexte de vocabulaire, pas un contenu.

Règles applicables à tout ce qui suit (ligne rouge du projet, `PROJECT.md` § 5) :

- l'IA peut **argumenter** et **valoriser** ; elle **n'invente** aucune référence, aucun
  certificat, aucun chiffre, aucun prix, aucune conformité ;
- **chaque affirmation d'un mémoire doit être rattachable à un élément réel de la
  bibliothèque du client** (`memoire_section_source`). Ce qui ne peut pas l'être est
  **signalé comme manquant** (`memoire_manque`), jamais comblé par du texte plausible ;
- l'IA **ne signe rien** : un mémoire ne devient « validé » que par une action humaine
  nommée et horodatée.

---

## 1. Ce qu'est un mémoire technique — et ce qu'il n'est pas

Un mémoire technique est la **réponse écrite au jugement de valeur** d'une consultation :
il ne dit pas *combien* (c'est l'offre financière, hors périmètre de la phase 4), il dit
**comment l'entreprise va faire, avec quels moyens, sur la base de quoi on peut le croire**.

Trois distinctions à ne jamais perdre de vue dans la rédaction :

1. **Un mémoire n'est pas une plaquette commerciale.** Le jury cherche des faits
   vérifiables et appariables au DCE, pas une présentation d'entreprise.
2. **Un mémoire n'est pas une offre financière.** Aucun prix, aucun montant de l'offre,
   aucune décomposition du prix ne figure dans le mémoire (le prix reste humain, phase 4
   § 7). Les montants qui apparaissent sont ceux de **références passées**, cadrés en € HT.
3. **Un mémoire n'est pas un document juridique d'engagement.** La signature et l'acte
   d'engagement sont hors périmètre ; ici, on s'arrête à une **validation nommée et
   horodatée** (Phase 4 § 2.C).

Corollaire pour le moteur : la sortie est un **dossier structuré**, chaque section portant
sa source ; les manques sont **un résultat affiché**, pas une erreur (Phase 4 § 2.B, L2 § 3).

---

## 2. Structure attendue : l'ordre des chapitres, et pourquoi cet ordre

### 2.1 La règle d'ordre qui prime sur toutes les autres

**Le plan du mémoire se calque sur les critères du DCE, dans l'ordre de pondération
décroissante.** Le critère le plus lourd ouvre le mémoire et reçoit le développement le
plus long ; un critère sans pondération connue passe en fin, avec sa raison affichée
(Phase 4 § 3, L2 § 2.1).

Conséquences pratiques :

- chaque section porte, en tête, **le libellé du critère** auquel elle répond et, si elle
  est connue, sa **pondération** : le lecteur n'a jamais à deviner à quoi la page répond ;
- un **sommaire paginé** et une **table de correspondance critère → section** ouvrent le
  document ; c'est ce qui permet à un relecteur pressé de vérifier que rien n'est omis ;
- toute section se termine par **ses sources** (références, certifications, moyens, fiches
  produits cités) — la traçabilité est visible dans le document, pas seulement en base.

### 2.2 Les chapitres, dans l'ordre

Le tableau donne l'ordre de référence (générique ; le plan réel suit la pondération du DCE,
§ 2.1). La colonne « doit venir après » est la contrainte de dépendance logique : ce qui est
écrit avant sert de preuve à ce qui suit.

| # | Chapitre | Ce que le lecteur y cherche | Doit venir après |
|---|---|---|---|
| 0 | Page de garde et identification de l'offre | Qui répond, à quoi, pour quelle date limite, quel lot | — |
| 1 | Sommaire et correspondance critères → sections | Que rien n'est omis ; où trouver chaque critère | 0 |
| 2 | Analyse du besoin et du contexte d'exécution | Que l'entreprise a **lu le DCE** et compris les contraintes du site | 0–1 |
| 3 | Présentation de l'entreprise | Qui c'est, ce qu'elle sait faire, sa solidité (identité, effectifs, capacités) | 2 |
| 4 | Références de chantiers comparables | La **preuve** qu'elle a déjà fait ce qu'on demande | 2–3 |
| 5 | Moyens humains affectés au marché | **Qui**, nommément et par fonction, va travailler sur ce chantier | 4 |
| 6 | Moyens matériels et logistiques affectés | **Avec quoi** elle travaille, et que ce matériel est disponible | 5 |
| 7 | Produits, systèmes et procédés mis en œuvre | Ce qu'elle va poser, sous quelle référence technique, sous quel avis technique | 2, 6 |
| 8 | Méthode d'exécution / mode opératoire | **Comment** elle exécute, ouvrage par ouvrage, points singuliers compris | 5–7 |
| 9 | Gestion des interfaces avec les autres corps d'état | Comment elle ne bloque personne et personne ne la bloque | 8 |
| 10 | Planning d'exécution et phasage | **Quand**, en combien de temps, par tranches | 8–9 |
| 11 | Hygiène, sécurité et protection du site occupé | Comment elle protège les personnes (dont les enfants) et les biens | 8–10 |
| 12 | Contrôle qualité et autocontrôle | Comment elle prouve que c'est bien fait, et à quel moment | 8 |
| 13 | Gestion des déchets et propreté du site | Ce qu'elle enlève, où, et comment elle laisse le site | 8, 11 |
| 14 | Points de vigilance et maîtrise des risques | Qu'elle a identifié ce qui peut échouer et comment elle le traite | 8–13 |
| 15 | Annexes et pièces justificatives | Attestations, certificats, CV, fiches, PV de réception, photos | — (appelées par les chapitres) |

### 2.3 Ce qui doit être dit avant quoi — et pourquoi

- **L'analyse du besoin vient avant la méthode.** Une méthode écrite avant d'avoir montré
  qu'on a compris le besoin est un copier-coller : c'est le premier signal de disqualification.
- **Les références viennent avant les moyens.** Le jury croit d'abord à la capacité prouvée ;
  les moyens affectés deviennent crédibles quand des chantiers comparables existent.
- **Les moyens humains viennent avant la méthode.** Une méthode sans conducteur de travaux
  nommé ni équipe affectée est une méthode sans titulaire.
- **Les produits et systèmes viennent avant la méthode d'exécution**, parce que le mode
  opératoire décrit la mise en œuvre d'un système précis (et non l'inverse).
- **Les interfaces viennent après la méthode et avant le planning.** Les contraintes
  d'interface conditionnent les dates : un planning écrit sans avoir traité les interfaces
  est irréaliste, et un jury qui connaît le site le voit tout de suite.
- **Le phasage en site occupé est traité à deux endroits, jamais un seul** : dans la
  méthode (comment on découpe l'ouvrage) et dans le planning (quand on intervient), avec le
  rappel de sécurité dans le chapitre hygiène-sécurité.
- **La sécurité après la méthode et le planning**, parce qu'elle découle des opérations
  décrites (travaux à chaud, travail en hauteur, coactivité) et doit être cohérente avec elles.
- **Le contrôle qualité clos le « comment faire »**, avant les annexes : c'est ce qui prouve
  que l'entreprise ne se contente pas de promettre le résultat.

---

## 3. Ce qui fait gagner des points

Chaque bloc ci-dessous dit : **ce que le jury cherche**, **ce qui est attendu dans le texte**,
**le piège**. Les neuf familles de bibliothèque sont nommées dans leurs noms exacts de code
(`identite`, `capacites_financieres`, `assurances`, `certifications`, `references_chantiers`,
`moyens_humains`, `moyens_materiels`, `fiches_produits`, `memoire_technique`) ; le détail
des champs et le mapping complet sont au § 5.

### 3.1 Références de chantiers comparables

- **Ce que le jury cherche** : la preuve que l'entreprise a déjà exécuté **un ouvrage de
  même nature, sur un maître d'ouvrage comparable, à une date récente**.
- **Attendu** : pour chaque référence citée — intitulé de l'opération, **nature des
  travaux**, **maître d'ouvrage** (public / privé), **lieu**, **année de réalisation et
  année de réception** (les DCE raisonnent le plus souvent en ancienneté de **réception**),
  **durée**, **montant en € HT avec son assiette** (travaux seuls ? avec échafaudage ?
  avec dépose et évacuation ?), **surface traitée avec son unité**, et surtout la
  **difficulté rencontrée et la solution apportée** (support dégradé, humidité résiduelle,
  surcharge limitée, points singuliers complexes). Une référence non justifiée (pas de PV
  de réception, pas d'attestation) est à marquer « à confirmer », jamais à présenter comme
  acquise.
- **Le piège** : la liste exhaustive de tout ce que l'entreprise a fait. Trois références
  **appariables** valent mieux que quinze hors sujet. Un montant ou une surface sans
  assiette ni unité n'est pas exploitable.

### 3.2 Moyens humains réellement affectés

- **Ce que le jury cherche** : des **personnes nommées, avec leur fonction et leur
  expérience**, affectées **à ce marché** — pas l'effectif total de l'entreprise.
- **Attendu** : effectif **par métier** concerné par le lot ; **organigramme** avec le
  conducteur de travaux / chef de chantier / compagnons ; CV des profils clés (fonction,
  diplômes ou qualifications, **années d'expérience** — saisies ou lues, jamais déduites) ;
  et la déclaration explicite de ce qui est **réalisé en propre vs sous-traité**.
- **Le piège** : annoncer « une équipe expérimentée » sans nom, sans fonction, sans
  disponibilité. Le mot « expérimenté » sans référence vérifiable ne rapporte aucun point.

### 3.3 Moyens matériels et logistiques affectés

- **Ce que le jury cherche** : le matériel **mobilisé pour ce chantier** et sa
  **disponibilité** à la date d'exécution.
- **Attendu** : désignation, **quantité**, éventuellement marque/modèle et année,
  **propriété** (matériel propre ou location), **disponibilité**, et le justificatif
  quand il existe. Doivent apparaître les moyens propres au métier (par ex. en étanchéité :
  moyen de levage, poste de soudage à chaud / chalumeau, groupe d'extraction, matériel
  d'application liquide, échafaudage ou plateforme, camion-grue / monte-charge).
- **Le piège** : confondre le **parc** de l'entreprise et ce qui est **réellement affecté**.
  Le jury note l'affectation au marché, pas le catalogue.

### 3.4 Méthode d'exécution / mode opératoire

- **Ce que le jury cherche** : un enchaînement d'opérations **techniquement juste** et
  **adapté au support réel** décrit au DCE.
- **Attendu** : le découpage par **nature d'ouvrage** (parties courantes, relevés, points
  singuliers : boîtes à eau, crapaudines, joints de dilatation, pénétrations) ; la
  **préparation du support** (diagnostic, purge, ragréage, contrôle d'humidité) ; la
  **mise hors d'eau et la protection provisoire** pendant les travaux ; les **modalités
  d'exécution** propres au système retenu (par ex. soudage, indépendance de pose,
  application liquide) ; les **contrôles en cours d'exécution** ; les **essais** (par ex.
  essai d'étanchéité à l'eau) et le **nettoyage / repli**.
- **Le piège** : une méthode générique qui ne cite **aucun élément du DCE** (aucune
  référence au type d'ouvrage, aux contraintes du site, aux points singuliers). C'est le
  premier motif de disqualification.

### 3.5 Planning, phasage et conditions de reprise

- **Ce que le jury cherche** : un planning **réaliste et tenable**, compatible avec le site
  et les autres intervenants.
- **Attendu** : durée totale, **découpage en phases/tranches**, rappel des **conditions
  météo** et des **interruptions prévisibles**, des **délais d'approvisionnement** ou de
  fabrication, et de la **date limite contractuelle** du DCE. Le planning doit être
  cohérent avec la méthode et avec les interfaces (§ 3.6).
- **Le piège** : une durée « totale » ronde, sans phases, ni conditions de reprise, ni
  prise en compte des vacances/livraisons. Un planning déconnecté de la méthode est un
  signal d'irréalisme.

### 3.6 Gestion des interfaces avec les autres corps d'état

- **Ce que le jury cherche** : que l'entreprise **ne bloque pas le chantier** et **ne soit
  pas bloquée sans l'avoir dit**.
- **Attendu** : l'inventaire des interfaces (qui livre quoi, qui reprend quoi : supports
  préparés par le gros œuvre, réservations, gaines et émergences d'autres lots,
  évacuations d'eaux pluviales, électricité de chantier) ; les **points d'arrêt** et les
  **points de coordination** ; le **rôle du conducteur de travaux** dans la coordination ;
  les conséquences sur le planning (§ 3.5).
- **Le piège** : ne parler que de son propre lot. Un mémoire muet sur les interfaces est
  celui qui produira des retards en exécution.

### 3.7 Hygiène, sécurité et environnement

- **Ce que le jury cherche** : la maîtrise réelle des risques du chantier, en particulier
  en **site occupé**.
- **Attendu** : identification des risques (travail en hauteur, chute d'objets, travaux à
  chaud / gaz, coactivité, circulation, amiante éventuel — **diagnostic préalable à
  vérifier, jamais présumé**) ; mesures de prévention et **balisage** ; moyens de secours ;
  et, en site occupé, les dispositions pour la **sécurité des occupants et des enfants**
  (accès séparés, protection des zones de travail, éclisses et protections, consignes,
  horaires). Les certifications de management (par ex. MASE, ISO) étayent la démarche
  quand elles existent — **et seulement si elles sont valides à la date de remise**.
- **Le piège** : promettre « le respect de la réglementation » sans aucune disposition
  concrète, alors que le site est occupé. En établissement scolaire, l'absence de
  dispositions relatives aux enfants est rédhibitoire.

### 3.8 Contrôle qualité et autocontrôle

- **Ce que le jury cherche** : comment l'entreprise **prouve** que le résultat est conforme.
- **Attendu** : points de contrôle (à la réception du support, avant recouvrement, après
  achèvement), **essais** réalisés et critères d'acceptation applicables, traçabilité des
  matériaux mis en œuvre (références de produits, avis techniques), gestion des **non-
  conformités** et **levée des réserves**, dossier de fin de chantier remis au maître
  d'ouvrage (DOE : plans, fiches, PV).
- **Le piège** : annoncer un « contrôle permanent » sans définir ni les points de contrôle,
  ni les essais, ni les critères.

### 3.9 Gestion des déchets et propreté

- **Ce que le jury cherche** : que l'entreprise **évacue ce qu'elle dépose** et laisse le
  site propre.
- **Attendu** : nature des déchets (dépose d'anciens revêtements, isolants, emballages),
  **tri et filières d'évacuation**, répartition des responsabilités (qui évacue, qui
  fournit la benne), fréquence de nettoyage, et sort de la **zone de stockage** temporaire.
  Rappel : la présence d'amiante dans un bâtiment ancien est un **diagnostic à vérifier**,
  jamais une présomption.
- **Le piège** : la phrase « évacuation des déchets comprise », sans filière ni
  responsabilité.

### 3.10 Phasage en site occupé — le cas des écoles

C'est la contrainte qui distingue une offre crédible d'une offre théorique. Ce qui est
attendu, explicitement :

- **le calendrier scolaire** : interventions privilégiées pendant les **vacances
  scolaires**, ou découpage par zones/ bâtiments compatibles avec l'occupation ;
- **les accès** : itinéraires d'approche, zones de livraison et de levage distinctes des
  accès élèves et du public, protection des cheminements ;
- **la sécurité des enfants** : interdiction d'accès à la zone de travail pendant les
  heures de présence, protections physiques, consignes au personnel, coordination avec la
  direction de l'établissement ;
- **les conditions d'intervention bruyantes ou à risque** (travaux à chaud) décalées hors
  présence des élèves ;
- **la remise en état** entre deux phases (site rendu propre et sûr à chaque interruption).

Ce chapitre n'est pas un paragraphe de principe : il doit **s'appuyer sur des références
où l'entreprise a déjà tenu ce type de contrainte** (§ 3.1) et sur la méthode décrite (§ 3.4).

---

## 4. Ce qui disqualifie

1. **Les promesses non étayées.** « Nous garantissons la conformité », « qualité
   irréprochable », « meilleure entreprise du marché » : aucun point, et un effet négatif.
   Une promesse sans élément de bibliothèque à l'appui est un défaut, pas un argument.
2. **Le copier-coller générique sans référence au DCE.** Un mémoire qui pourrait être
   déposé sur n'importe quelle consultation ne démontre pas qu'on a lu celle-ci. Le jury le
   repère au premier paragraphe : aucune reprise du contexte, des ouvrages, des contraintes
   ou des critères du DCE.
3. **Les références hors sujet ou trop anciennes.** Un chantier d'un autre métier, ou dont
   la nature/le support/la taille ne se rapportent pas à l'objet du marché, n'apporte rien.
   Attention : le **seuil d'ancienneté** est fixé par chaque règlement de consultation —
   il **n'est pas une constante** et doit être lu dans le DCE, jamais présumé.
4. **L'absence de chiffres vérifiables.** Surface sans unité ni définition, montant sans
   assiette ni mention HT, durée sans phases, effectif « important », « plusieurs centaines
   de chantiers » : tout cela n'est pas exploitable et signale une entreprise qui n'a pas
   ses données.
5. **Un mémoire qui ne répond pas critère par critère.** Si le jury note six critères et
   que le mémoire n'en traite que trois, tout le reste tombe à zéro. La structure doit
   **suivre les critères du DCE dans leur ordre de pondération** (§ 2.1) et **chacun doit
   avoir sa section identifiable**.
6. **Les affirmations non rattachables à un élément réel.** C'est la violation la plus
   grave (ligne rouge) : une référence, un certificat, un avis technique, une assurance
   ou un moyen cité qui n'existe pas dans la bibliothèque du client. Le moteur doit
   refuser d'écrire une telle phrase : elle devient une **ligne de manque**.
7. **Les incohérences internes.** Moyens annoncés ≠ moyens affectés ; planning incompatible
   avec la méthode ; produits cités sans rapport avec la nature des travaux ; référence
   présentée comme couverte par une qualification qui ne l'est pas.
8. **Le mémoire qui « signe » ou promet une conformité normative.** Annoncer « conforme au
   DTU » sans que l'ouvrage relève du bon DTU, ou promettre la conformité d'un système sans
   avis technique valide, expose juridiquement l'entreprise. On cite une référence, on ne
   garantit rien.
9. **Les documents périmés.** Attestation d'assurance échue, certification expirée,
   fiche technique ou avis technique hors validité : les dates de validité doivent être
   **vérifiées à la date de remise**, et un élément périmé ne doit pas être présenté.

---

## 5. De quoi la bibliothèque a besoin : mapping exigence → famille

C'est la table qui pilote le moteur (lot L2) : pour chaque exigence de contenu, **la
famille exacte** où chercher la source, et le/les **champ(s)** à mobiliser. La dernière
colonne dit ce que le moteur fait **quand il ne trouve rien** : une **ligne de manque**
(constat + action à mener), jamais du texte inventé.

| Exigence de contenu (§) | Famille (nom exact) | Entité et champs à mobiliser | Si absent → manque (action attendue) |
|---|---|---|---|
| Identification de l'entreprise et du signataire (2, 3.1) | `identite` | `entreprise_version` : `raison_sociale`, `siren`, `siret_siege`, `forme_juridique_code`, `capital_social_montant`, `capital_social_devise`, `adresse_siege`, `effectif`, `date_effectif`, `site_web` ; `representant_legal` : `nom`, `prenom`, `fonction`, `qualite_engagement` | Compléter la fiche d'identité de l'entreprise (identité et représentant légal). |
| Solidité économique et capacité de production (3) | `capacites_financieres` | `exercice_comptable` : `annee_exercice`, `chiffre_affaires_montant`, `chiffre_affaires_devise`, `resultat_net_montant`, `capitaux_propres_montant`, `effectif_moyen` ; `capacite_production` : `description`, `unite`, `valeur` ; `attestation` : `type_attestation`, `emetteur`, `date_emission`, `date_validite_fin`, `montant_engage_montant` | Renseigner les exercices comptables et la capacité de production ; joindre l'attestation de capacité. |
| Couverture assurantielle des activités du marché (3.7) | `assurances` | `assurance` : `type_assurance`, `assureur`, `numero_contrat`, `montant_garantie_montant`, `montant_garantie_devise`, `franchise_montant`, `date_debut`, `date_echeance`, `activites_couvertes`, `piece` | Ajouter l'attestation d'assurance couvrant l'activité, avec sa date d'échéance. |
| Qualifications et certifications (3.7, 3.8) | `certifications` | `certification` : `intitule`, `organisme`, `domaine_code`, `numero_certificat`, `date_obtention`, `date_echeance`, `piece` | Ajouter la qualification ou le certificat correspondant à l'activité (et vérifier sa validité à la date de remise). |
| Références de chantiers comparables — preuve de capacité (3.1, 3.10) | `references_chantiers` | `reference_chantier` : `intitule_operation`, `maitre_ouvrage`, `nature_travaux_code`, `nature_travaux_libelle`, `lieu_commune`, `lieu_departement`, `date_debut`, `date_fin`, `duree_mois`, `montant_montant`, `montant_devise`, `surface_traitee`, `surface_unite`, `description`, `competences_appliquees`, `attestation_bonne_execution`, `contact_reference`, `photos` | Aucune référence correspondante : ajouter un chantier comparable (nature de travaux, maître d'ouvrage, montant € HT, année de réception, difficulté traitée). |
| Personnes réellement affectées au marché (3.2) | `moyens_humains` | `effectif_metier` : `metier_code`, `metier_libelle`, `nombre` ; `organigramme` : `piece`, `description`, `date_maj` ; `cv` : `nom`, `prenom`, `fonction`, `diplomes`, `annees_experience`, `cv_piece` | Nommer les moyens humains affectés (effectif par métier, organigramme, CV des profils clés). |
| Matériel et logistique affectés (3.3) | `moyens_materiels` | `moyen_materiel` : `categorie_code`, `designation`, `quantite`, `marque_modele`, `annee`, `propriete`, `disponibilite`, `justificatif` | Décrire les moyens matériels mobilisés pour ce marché (désignation, quantité, disponibilité, propre/location). |
| Produits, systèmes et procédés, avis techniques (3.4, 3.8) | `fiches_produits` | `produit` : `fournisseur`, `reference_produit`, `designation`, `famille_code`, `domaine_application`, `fiche_technique`, `avis_technique`, `date_validite_document`, `certificats` | Ajouter le produit/système et sa fiche technique (ou son avis technique) avec sa date de validité. |
| Doctrine d'entreprise réutilisable : méthode, sécurité, qualité, déchets, interfaces, site occupé (3.4–3.10) | `memoire_technique` | `chapitre_memoire` : `titre`, `ordre`, `contenu_texte`, `statut`, `date_redaction`, `references_liees`, `documents_associes` | Rédiger le chapitre correspondant du mémoire type, ou traiter le point en manque avec l'action à mener (selon le § 7). |
| Effectif total et contexte social (3.2) | `identite` | `entreprise_version` : `effectif`, `date_effectif`, `effectif_source_code` | Renseigner l'effectif et sa date de référence (sans confondre avec l'effectif par métier). |
| Titres, diplômes et expérience des profils clés (3.2) | `moyens_humains` | `cv` : `diplomes`, `annees_experience` | Renseigner diplômes et années d'expérience du profil concerné. |
| Justificatifs de référence : PV de réception, attestation de bonne exécution (3.1) | `references_chantiers` | `reference_chantier` : `attestation_bonne_execution`, `photos` | Joindre l'attestation / le PV de réception ; sinon marquer la référence « à confirmer ». |
| Traçabilité produit ↔ ouvrage (3.4, 3.8) | `fiches_produits` | `produit` : `domaine_application`, `avis_technique`, `certificats` | Relier le système retenu à son avis technique et à son domaine d'application. |
| Engagement d'entreprise, références liées aux chapitres (3) | `memoire_technique` | `chapitre_memoire` : `references_liees`, `documents_associes` | Lier les chapitres réutilisés à des éléments réels de la bibliothèque. |

**Rappel de la règle centrale pour le moteur** : une section n'est produite **que** si elle
porte au moins une ligne `memoire_section_source` pointant un élément de bibliothèque **du
même `client_id`** ; sinon elle devient une ligne `memoire_manque` (constat + action).
La famille `memoire_technique` sert de **source citée**, jamais de texte recopié sans
source (Phase 4 § 6, question 4 — défaut retenu).

---

## 6. Trois formulations exemplaires, sur le même sujet

Sujet commun : **réfection d'étanchéité d'une toiture-terrasse d'un groupe scolaire, en
site occupé**. Toutes les valeurs sont **fictives** et signalées comme telles ; elles ne
correspondent à aucun chantier réel.

### 6.1 Formulation qui gagne des points (fictive)

> Pour la réfection de la toiture-terrasse du groupe scolaire [fictif], nous mobilisons
> l'équipe qui a exécuté en [année fictive] la réfection de l'étanchéité d'un groupe
> scolaire comparable pour [maître d'ouvrage fictif public] : [surface fictive] m² de
> toiture-terrasse et [valeur fictive] ml de relevés, dépose de l'ancien revêtement, isolant
> [type à préciser] et protection [à préciser], montant [valeur fictive] € HT (travaux seuls),
> réception [année fictive]. Le chantier avait été conduit **en site occupé**, par tranches
> pendant les vacances scolaires ; les accès ont été séparés de ceux des élèves et les travaux
> à chaud réalisés hors présence des enfants. La difficulté portait sur un support béton
> dégradé et une humidité résiduelle de l'ancien complexe ; elle a été traitée par [solution
> fictive à confirmer]. Le conducteur de travaux affecté à votre marché est [nom fictif],
> [fonction fictive], [n] ans d'expérience, qui a conduit ce chantier. Le système retenu
> [référence produit fictive] est couvert par l'avis technique [référence fictive], valide à
> la date de remise.

**Pourquoi elle est bonne** : chaque affirmation renvoie à un élément **réel de la
bibliothèque** (une référence de chantier, un CV, une fiche produit, un avis technique) ;
elle nomme la difficulté et la solution ; elle répond au contexte d'exécution (site occupé,
vacances, sécurité des enfants) ; elle est cadrée en € HT avec son assiette ; elle ne
promet rien qu'elle ne peut prouver.

### 6.2 Formulation moyenne (fictive)

> Nous réaliserons la réfection de l'étanchéité de la toiture-terrasse conformément aux
> règles de l'art et aux prescriptions du marché. Notre entreprise dispose d'une équipe
> expérimentée et d'un matériel adapté. Les travaux seront exécutés en plusieurs phases afin
> de limiter la gêne pour les occupants, dans le respect de la réglementation en vigueur en
> matière de sécurité. Nous avons l'habitude d'intervenir en site occupé, notamment dans des
> établissements scolaires, et nous saurons nous adapter aux contraintes du site.

**Pourquoi elle est moyenne** : le vocabulaire est correct et le sujet est le bon, mais
**aucun chiffre vérifiable**, **aucune référence nommée**, **aucun profil affecté**, **aucune
difficulté traitée**. Les affirmations sont plausibles mais **non rattachables** à un élément
de bibliothèque : dans le produit, elles devraient être remplacées par des lignes de manque.
Elle ne disqualifie pas par elle-même, mais elle ne rapporte presque aucun point.

### 6.3 Formulation disqualifiante (fictive)

> Spécialiste reconnu de l'étanchéité depuis plus de [n] ans, nous sommes **le leader** du
> secteur et **garantissons** une étanchéité conforme à tous les DTU et **sans aucun défaut**
> pendant **[n] années**. Nos références, trop nombreuses pour être listées, couvrent tous
> types d'ouvrages. Nous utiliserons **le meilleur produit du marché**, 100 % étanche,
> **sans surcoût** pour le maître d'ouvrage. Notre planning sera respecté à la lettre, quelles
> que soient les conditions, et la sécurité des enfants sera **assurée en permanence** sans
> qu'aucune disposition particulière ne soit nécessaire, puisque nous **faisons toujours
> ainsi**.

**Pourquoi elle disqualifie** : promesses non étayées et non vérifiables (« leader »,
« meilleur produit », « 100 % étanche ») ; **garanties et conformités promues** que
l'entreprise ne peut pas prendre (exposition juridique) ; référence vague et non sourcée ;
absence de chiffres ; **affirmation de sécurité sans disposition concrète** sur un site
occupé par des enfants ; promesse de prix hors mémoire ; aucune réponse aux critères du DCE.
Chaque phrase de cet exemple est, pour le moteur, un **refus d'écriture** : sans source de
bibliothèque, elle doit devenir une ligne de manque ou être supprimée.

### 6.4 Ce que les trois exemples montrent mécaniquement

| Trait | 6.1 (bonne) | 6.2 (moyenne) | 6.3 (disqualifiante) |
|---|---|---|---|
| Rattachable à la bibliothèque | oui, élément par élément | non | non |
| Chiffres vérifiables et cadrés | oui | non | non |
| Contexte du DCE repris | oui (site occupé, école) | partiellement | non |
| Garanties / conformité promise | non | non | oui (fautif) |
| Difficile techniquement traitée | oui (support, humidité) | non | non |
| Rôle du moteur | valoriser avec sources | compléter par des manques | **refuser d'écrire** |

---

## 7. Ce que la bibliothèque ne sait pas encore étayer — à traiter en manque

Certaines exigences de contenu du § 3 **n'ont pas de famille dédiée** dans les neuf familles
de la phase 3. Ce sont des **angles morts assumés** : le moteur ne peut pas les sourcer
directement. La règle à appliquer est **manque explicite**, pas texte inventé. Le tableau
donne la famille la plus proche (à citer comme source partielle quand elle existe) et
l'action à mener.

| Exigence sans famille directe | Famille la plus proche | Traitement attendu du moteur |
|---|---|---|
| Planning détaillé et phasage (§ 3.5, 3.10) | `memoire_technique` (chapitre type « planning/phases ») ou `references_chantiers` (`duree_mois`, `description`) | Reprendre la contrainte de délai du DCE et les durées de références comparables ; **ne construire aucune durée** ; produire un manque « planning à produire » si aucune contrainte n'est sourcée. |
| PPSPS / plan particulier de sécurité et de protection de la santé (§ 3.7) | `memoire_technique` (chapitre sécurité) ; `certifications` (ex. MASE) | Rédiger à partir du chapitre type **et** des certifications valides ; sinon manque « plan de sécurité à établir ». |
| Plan de contrôle qualité et essais (§ 3.8) | `memoire_technique` (chapitre qualité) ; `certifications` | Idem : chapitre type + certifications ; sinon manque. |
| Gestion des déchets : filières et responsabilités (§ 3.9) | `memoire_technique` (chapitre environnement) ; `certifications` (démarche environnementale) | Chapitre type + certification ; sinon manque. |
| Gestion des interfaces / coordination de chantier (§ 3.6) | `memoire_technique` (chapitre interfaces) ; `moyens_humains` (`organigramme`, rôle du conducteur) | Chapitre type + organigramme ; sinon manque. |
| Part des travaux **réalisée en propre vs sous-traitée** (§ 3.2) | `references_chantiers` (`description`, `competences_appliquees`) | Aucun champ dédié : **manque** « préciser la part sous-traitée ». |
| Dispositions de sécurité pour les enfants en site occupé (§ 3.10) | `references_chantiers` (référence où la contrainte a été tenue) ; `memoire_technique` (chapitre site occupé) | Sourcer par une référence comparable + chapitre type ; sinon manque. |
| Mise hors d'eau et protection provisoire pendant les travaux (§ 3.4) | `memoire_technique` (chapitre méthode) ; `fiches_produits` (système de protection provisoire) | Chapitre type + fiche produit ; sinon manque. |

**Recommandation au lot L2** : ces angles morts ne justifient **pas** d'inventer de
nouvelles familles dans cette phase. Ils justifient que le manque soit **lisible et
actionnable** — c'est exactement le comportement attendu de `memoire_manque`
(« constat » + « action à mener »), et c'est la fonctionnalité la plus utile du produit
(Phase 4 § 3, L2 § 2.3).

---

## 8. Grille de relecture rapide (pour la relecture humaine des sections générées)

À appliquer à chaque section avant de la passer en `relue`, puis au dossier avant
`validee`. Une seule réponse « non » suffit à renvoyer la section.

1. La section **nomme le critère du DCE** auquel elle répond, et sa pondération si connue.
2. **Chaque affirmation factuelle porte une source** identifiée (référence, certification,
   moyen, produit, chapitre type) et cette source **existe dans la bibliothèque du client**.
3. Les **chiffres sont cadrés** : surface avec unité et définition, montant en € HT avec
   assiette, durée avec phases, effectif par métier et non « l'équipe ».
4. Aucune **garantie**, aucune **conformité normative**, aucun **prix**, aucun **délai
   garanti** n'est promis.
5. Le **contexte du DCE** est repris (nature d'ouvrage, contraintes du site, points
   singuliers) : la section ne pourrait pas être collée à une autre consultation.
6. Les **interfaces** et le **site occupé** sont traités quand le DCE les impose.
7. Les **documents cités sont valides à la date de remise** (assurance, certification,
   fiche, avis technique) — sinon, mention de manque.
8. La section ne contient **aucune valeur technique**, aucun identifiant interne, aucun
   jargon d'architecture (Phase 4 § 1, critère 6).

---

## 9. Références normatives citées, et leur statut

Les références ci-dessous sont mentionnées **telles qu'un mémoire peut les citer**, avec
leur intitulé de source. Elles ne sont **pas** un argument de conformité : citer un DTU
n'engage pas que l'ouvrage relève de ce DTU. Chaque usage doit **renvoyer au CCTP** de la
consultation, qui prime.

Série **NF DTU 43 — étanchéité des toitures** (intitulés vérifiés à la source le 30/09/2026) :

- **NF DTU 43.1** — Travaux de bâtiment — Étanchéité des toitures-terrasses et toitures
  inclinées avec éléments porteurs en maçonnerie en climat de plaine (indice de classement
  P84-204) ;
- **NF DTU 43.3** — Travaux de bâtiment — Mise en œuvre des toitures en tôle d'acier
  nervurées avec revêtement d'étanchéité (P84-206) ;
- **NF DTU 43.4** — Travaux de bâtiment — Toitures en éléments porteurs en bois et panneaux
  à base de bois avec revêtement d'étanchéité (P84-207) ;
- **NF DTU 43.5** — Travaux de bâtiment — Réfection des ouvrages d'étanchéité des
  toitures-terrasses ou inclinées (P84-208) ;
- **NF DTU 43.11** — Travaux de bâtiment — Étanchéité des toitures-terrasses et toitures
  inclinées avec éléments porteurs en maçonnerie en climat de montagne (P84-211).

**Contexte local (La Réunion) — point à traiter, pas à affirmer.** Les NF DTU 43.1 et
43.11 visent explicitement le **climat de plaine** et le **climat de montagne** ; leurs
domaines d'application **excluent les zones tropicales ou cycloniques**. En zone cyclonique,
les conditions de **vent** et les **fixations / lestage** relèvent des règles de vent
applicables et des prescriptions du maître d'ouvrage ; les supports en DOM renvoient au
**e-Cahier du CSTB 3644** (CPT « Supports de systèmes d'étanchéité de toitures dans les
départements d'outre-mer »). **Rien de tout cela ne doit être affirmé dans un mémoire sans
vérification à la source** avec le maître d'œuvre / le bureau d'études : c'est un point de
vigilance, pas un argument automatique.

Autres références possibles (à vérifier au cas par cas, jamais citées par défaut) :
avis techniques des procédés (liste verte C2P / CCFAT), règles professionnelles de la
famille concernée, certifications de management (par ex. MASE, ISO) — chacune **valide à
la date de remise**.

---

## 10. Points laissés ouverts / à confirmer (pour Anthony)

1. **Longueur cible par critère.** Le défaut retenu en phase 4 est « proportionnel au poids,
   sans plafond, chaque section portant sa longueur visible » (Phase 4 § 6, question 1).
   À trancher sur pièce.
2. **Reprise du mémoire type existant.** Le défaut retenu est « source citée, jamais texte
   recopié sans source » (Phase 4 § 6, question 4). À confirmer.
3. **Sous-traitance.** Aucune famille ne porte aujourd'hui la part réalisée en propre vs
   sous-traitée (§ 7). Faut-il un champ, ou un manque assumé pour cette phase ?
4. **Seuil d'ancienneté des références.** Variable selon le règlement de consultation : il
   doit être **lu dans le DCE**, jamais codé en dur. À confirmer comme règle du moteur.
5. **DTU et contexte cyclonique.** Le traitement du vent / des fixations en zone cyclonique
   est un point métier sensible : quelle formulation autorise-t-on (renvoi au CCTP, renvoi
   au bureau d'études) ?

---

*Fin du livrable L1. Ce document ne contient aucune donnée réelle, aucun prix, aucun
document d'acheteur. Les familles citées sont celles de la phase 3, dans leurs noms exacts.*
