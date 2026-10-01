# L5a — Refonte des écrans existants et écran d'accueil

*Rédigé par `dev-web` le 30 septembre 2026, lot L5a de la phase 4. Ce rapport ne
remplace pas le code : il dit ce qui a été regardé, et ce qu'on y a vu.*

---

## 1. Ce qui a été livré

| Fichier | Nature |
|---|---|
| `src/app/web/static/style.css` | refonte complète : reprise du système visuel du lot L4 (`docs/DESIGN.md` § 6) |
| `src/app/web/templates/base.html` | bandeau sans `h1` de produit, navigation Accueil / Bibliothèque / Consultations, pied de page qui dit d'abord ce que l'outil fait |
| `src/app/web/templates/connexion.html` | un seul bouton, note de compte repliée |
| `src/app/web/templates/accueil.html` | **nouveau** — ce que la plateforme apporte + où en est l'utilisateur + une action principale |
| `src/app/web/templates/bibliotheque.html` | manques en tête, jauge, neuf familles avec état en français, relecture, références techniques repliées |
| `src/app/web/templates/famille.html` | éléments en fiches, libellés métier, sources lisibles, formulaires allégés |
| `src/app/web/templates/consultations.html` | écran de dépôt : fournisseur retiré, champs renommés, dossiers déposés en liste |
| `src/app/web/templates/consultation.html` | analyse : « l'essentiel » puis le contenu, chaque ligne avec sa source |
| `src/app/web/templates/checklist.html` | manques en tête, un seul état par pièce, compteurs repliés |
| `src/app/web/templates/premiere_utilisation.html` | état vide pensé comme un écran, pas comme un cul-de-sac |
| `src/app/web/templates/erreur.html` | titre qui parle, code replié |
| `src/app/web/routes_web.py` | route `GET /accueil`, redirection après connexion vers `/accueil`, vocabulaire métier traduit au rendu |

Aucun autre fichier n'a été touché. Les services et les routes `/api/v1` sont
inchangés ; les écrans continuent d'appeler les **services** en processus.

## 2. Cadre technique tenu

- HTML servi côté serveur, Jinja2, **aucun JavaScript**, aucune ressource
  chargée depuis un tiers : la feuille de style est le seul fichier externe.
- `client_id` toujours pris dans la session ; un écran sans session redirige
  vers `/connexion` ; la cible d'un autre client répond **404**.
- Les deux verrous humains sont conservés : validation de la bibliothèque
  (`POST /bibliotheque/validation`) et validation des éléments extraits d'un
  DCE (`POST /consultations/{id}/elements/{element_id}`). Aucun chemin ne pose
  un état validé sans action humaine nommée.
- Ligne rouge tenue : aucune valeur sans origine, aucune exigence comblée, aucun
  prix, aucun bouton de dépôt, d'envoi ou de signature.

---

## 3. Écran par écran, ce qui a été vu

Les captures sont dans `docs/RAPPORTS/captures-L5a/`, en desktop (1280 px) et en
fenêtre étroite (390 px). L'application a été démarrée par `bash demarrer.sh`
(port 8099) et chaque écran a été ouvert dans un navigateur réel, puis regardé.

### 01 — Connexion

**Constat desktop.** Un titre qui dit à quoi sert l'écran, un seul bouton bleu
plein « Se connecter », large et visible. La note sur la création de compte est
repliée derrière « Pourquoi je ne peux pas créer mon compte ici ? ». Plus aucune
trace de `annexe C § C2` ni de `scripts/provisionnement.py` : le vocabulaire est
celui de l'utilisateur. La barre du haut ne porte aucune navigation tant qu'on
n'est pas connecté.

**Constat mobile.** Le formulaire reste dans une carte, les deux champs et le
bouton occupent toute la largeur utile ; rien ne déborde (largeur de page 390 px
pour une fenêtre de 390 px).

### 02 — Accueil (nouveau, `GET /accueil`)

**Constat desktop.** Le `h1` annonce ce que la plateforme apporte. **Une seule
action principale**, en bleu plein, en haut à droite : « Déposer un dossier de
consultation ». En dessous, la carte « Où vous en êtes » montre trois étapes
numérotées avec une pastille par étape : « Terminé », « 9 à compléter »,
« 4 dossiers déposés » — chacune avec sa phrase. Puis trois cartes disent ce que
la plateforme fait, dont « Elle dit ce qui manque, et quoi faire ». Aucun
identifiant, aucun nom de table, aucun état de code.

**Constat mobile.** Le titre et l'action principale s'empilent, l'action passe en
pleine largeur ; la progression reste lisible sur une seule colonne.

### 03 — Bibliothèque d'entreprise

**Constat desktop.** L'ancien écran s'ouvrait sur `État : Vierge (vierge)`,
`Identifiant : 54498bc1-…` et neuf lignes `non_commencee` dans un tableau à cinq
colonnes. Il s'ouvre maintenant sur un encart de relecture (« Relecture de votre
bibliothèque : Socle complet (non relue) »), le bloc « Ce qui vous manque pour
être prêt à concourir », puis « Avancement par famille » : une jauge accompagnée
de sa phrase (« 9 familles renseignées sur 9. Aucune ne reste à compléter. ») et
une ligne par famille avec un état **en français** et un lien « Ouvrir » ou
« Compléter ». Le tableau des entreprises a disparu du corps ; la version de
fiche et l'identifiant sont repliés dans « Références techniques », avec le
bouton d'ouverture d'une nouvelle fiche pour ne pas perdre la fonction.

**Constat mobile.** La jauge et les neuf lignes tiennent sur une colonne ; le
tableau à cinq colonnes qui s'écrasait a disparu. Aucun défilement horizontal.

### 04 — Une famille (Références de chantiers)

**Constat desktop.** Les éléments sont des fiches : titre en clair, pastille
« Déclaré, non vérifié », puis les champs avec des libellés métier. Trois
corrections visibles par rapport à l'existant : les dates s'écrivent
`08/07/2024` et non `2024-07-08` ; les montants s'écrivent `412 000 EUR` et non
`412000.00` avec une ligne « Devise » séparée ; les `_` d'une valeur de
nomenclature ne se lisent plus dans un titre (« responsabilite civile
decennale »). Le formulaire d'ajout ne demande plus d'identifiant de document :
les champs de liaison sortent de l'écran.

**Constat mobile.** Chaque fiche passe en une colonne, le titre et la pastille
s'empilent, le formulaire reste utilisable.

### 13 — Une famille (Assurances)

**Constat desktop.** Même traitement. La ligne « Justificatif » affichait un
identifiant de document sous forme d'UUID : elle affiche désormais « pièce
fournie (document rattaché) » — le document reste rattaché, mais l'identifiant
n'est plus à l'écran. Les montants de garantie et la franchise sont lisibles.

### 05 — Déposer un dossier de consultation

**Constat desktop.** Le paragraphe « Générateur d'analyse : ue » et le chemin
`src/tests/fixtures/dce_fictif.pdf` ont quitté le corps de l'écran. Les libellés
sont ceux du métier : « Nom donné à ce dossier », « Le dossier de consultation »,
« Référence du marché — facultatif », « Maître d'ouvrage — facultatif ». « Ce que
vous obtiendrez » arrive **après** le formulaire, en trois points. Un seul bouton
d'action, « Analyser le dossier ».

**Constat mobile.** Le formulaire passe en une colonne, le bouton reste atteignable
sans zoom.

### 06 — Analyse d'une consultation

**Constat desktop.** Le `h1` est le nom du dossier, l'action principale est
« Demander le mémoire technique ». « L'essentiel » donne en trois lignes ce qui
compte : nombre de pièces exigées, nombre de critères, date limite — cette
dernière s'affiche `15/12/2026` et non `2026-12-15`. Chaque ligne porte
« Source : … , emplacement : page 1 — section … ». L'identifiant de la
consultation, l'empreinte SHA-256 et le nom du fichier ont quitté le corps : ils
sont dans « Références techniques ». Les trois boutons par ligne sont devenus
« Accepter », « Corriger avant d'accepter », « Refuser ».

**Constat mobile.** Les lignes et les formulaires se replient en une colonne.

### 07 — Vérifier le dossier (checklist)

**Constat desktop.** Le résumé affichait `Version de fiche croisée : bc815c1f-…`
et cinq compteurs techniques. Il commence maintenant par « Résumé des manques »,
avec l'action à mener. Chaque pièce s'affiche une seule fois, avec un état en
français. Le nom de table `[reference_chantier]` a disparu. Les compteurs
techniques et l'identifiant de version sont repliés dans « Références
techniques ». La phrase « C'est une aide à la relecture, pas un certificat » est
visible, et le pied de page porte la mention de brouillon.

**Constat mobile.** Un seul état par pièce, en pastille avec son mot ; rien ne
déborde.

### 08 — Erreur 404

**Constat desktop.** L'écran affichait « Erreur 404 » puis « Famille inconnue :
famille_inconnue » — du code. Il affiche « Cette page n'existe pas », « Ce qui
s'est passé », « Ce que vous pouvez faire », et une action principale « Revenir à
l'accueil ». Le message technique exact est replié dans « Références
techniques ». La chaîne `famille_inconnue` n'apparaît plus à l'écran.

**Constat mobile.** Titre, texte et action s'empilent proprement.

### 09 — Première utilisation

**Constat desktop.** L'écran parlait de « version de fiche » et de « annexe C
§ C2 ». Il dit maintenant « Première utilisation : créez votre entreprise », avec
une action principale « Créer mon entreprise » et l'explication que rien n'est
déduit. Les entreprises déjà déclarées s'affichent en liste, avec leur état de
fiche en français.

**Constat mobile.** L'action principale occupe toute la largeur.

### 10 à 12 — Les états vides

**Constat desktop.** Sur un espace neuf, l'accueil propose « Créer mon
entreprise » comme action principale — l'action s'adapte à l'état réel — et la
progression montre « À faire / Après l'étape 1 / À démarrer ». L'écran de
bibliothèque sans entreprise s'affiche comme l'écran de première utilisation :
il contient bien « Première utilisation ». L'écran de dépôt d'un dossier sans
entreprise dit « Aucune entreprise n'est déclarée : créez-la d'abord. » au lieu
de laisser un formulaire impossible à remplir.

**Constat mobile.** Les trois écrans tiennent en une colonne, sans débordement.

---

## 4. Textes réécrits (les plus visibles)

| Avant | Après |
|---|---|
| `ia-consultations-publiques — brouillon de travail` (h1 de chaque page) | le titre de l'écran devient le `h1` ; le bandeau ne porte plus que le nom du produit |
| `Connecté : Compte de verification (client 3782bb9d…)` | le nom de la personne seul |
| `Fermer la session` | `Se déconnecter` |
| `Ouvrir la session` | `Se connecter` |
| `Le compte est créé par l'exploitant (scripts/provisionnement.py) … (annexe C § C2…)` | replié : « Pourquoi je ne peux pas créer mon compte ici ? » |
| `Bibliothèque d'entreprise — état d'avancement` | `Votre bibliothèque d'entreprise` |
| `Version de fiche : 1` / `Identifiant : 54498bc1-…` | repliés dans « Références techniques » |
| `État : Vierge (vierge)` | état en français (« Socle complet (non relue) », « Relue et validée par humain ») |
| `non_commencee` (état de famille) | `À compléter` |
| `aucun élément` / `au moins un élément` | `aucune information` / `N informations` |
| `Complétude structurelle seulement : …` | replié : « Pourquoi ? Ce que « renseigné » veut dire ici » |
| `Relecture humaine bloquante` | `Relire et valider vos informations, c'est ce qui autorise le mémoire à s'appuyer dessus.` |
| `Périmètre de la validation` | `Ce que vous validez` |
| `Nom du relecteur (obligatoire)` | `Votre nom` |
| `J'ai relu et corrigé les informations ci-dessus (attestation obligatoire)` | `J'ai relu et corrigé ces informations.` |
| `Enregistrer la relecture humaine` | `Enregistrer la relecture` |
| `Consultations — analyse d'un DCE` | `Déposer le dossier de consultation` |
| `Générateur d'analyse : ue` + paragraphe fournisseur | supprimé |
| `Libellé de la consultation` | `Nom donné à ce dossier` |
| `Document (PDF ou .txt)` | `Le dossier de consultation` |
| `Référence de la consultation (saisie par l'humain)` | `Référence du marché — facultatif` |
| `Maître d'ouvrage déclaré (saisi par l'humain, jamais déduit)` | `Maître d'ouvrage — facultatif` + « Ce que vous saisissez ici est repris tel quel. L'outil ne le devine pas. » |
| `Analyser ce document` | `Analyser le dossier` |
| `Statut : analysee` | état `Analysé` |
| `Créée le 2026-09-30 14:01:02.431206+04:00` | `Déposé le 30/09/2026` |
| `Identifiant : 74531431-…` / `empreinte SHA-256 6b921f8f2a…` | repliés dans « Références techniques » |
| `Valider cet élément` / `Enregistrer la correction` / `Marquer comme supprimé` | `Accepter` / `Corriger avant d'accepter` / `Refuser` |
| `Vérifier le dossier — checklist de conformité` | `Vérifier le dossier` |
| `Version de fiche croisée : bc815c1f-…` + cinq compteurs | repliés dans « Références techniques » |
| pastille `présente` **et** code `presente` en dessous | un seul état : `Présente` |
| `Pièce retenue : … [reference_chantier]` | `Pièce retenue : …` |
| `Erreur 404` / `Famille inconnue : famille_inconnue` | `Cette page n'existe pas` + explication ; le code est replié |
| pied de page : « Outil d'aide à la relecture… » | « **Ce que fait l'outil :** il lit les dossiers que vous déposez et rédige votre mémoire technique à partir de vos propres références. » puis les limites |

---

## 5. Écarts assumés, signalés plutôt qu'improvisés

1. **Deux liens mènent à des écrans livrés par le lot L5b.** L'action principale
   de la bibliothèque est « Importer vos documents existants »
   (`/bibliotheque/import`) et celle de l'analyse est « Demander le mémoire
   technique » (`/consultations/{id}/memoire`) : ce sont les chemins **gelés** du
   plan de phase 4 (§ 2.D) et les actions voulues par la direction de design.
   L5b a ce lot pour parent et les livre juste après ; jusqu'à son passage, ces
   deux liens ouvrent l'écran 404 — lui-même refondu (capture 08).
2. **Le jeu de démonstration fictif reste mentionné** sur l'écran de dépôt, mais
   **replié** dans « Références techniques ». La direction de design demandait sa
   suppression de l'écran ; le test `test_parcours_complet_web_de_bout_en_bout`
   exige la chaîne `dce_fictif.pdf` dans la page. La non-régression passe avant
   le confort : je le signale au lieu de le retirer en douce.
3. **Les champs de liaison sortent du formulaire de saisie.** `photos`,
   `references_liees`, `documents_associes` et `certificats` sont des
   identifiants de documents : on ne demande plus à un humain d'y coller un UUID
   (règle « si un libellé affiché contient un nom de colonne, c'est un défaut »).
   Les valeurs restent consultables par élément, dans « Références techniques ».
   Le dépôt de pièces lui-même appartient à l'import guidé (L5b).
4. **Nom du produit** : « Consultations publiques » — espace réservé du designer
   (`docs/DESIGN.md` § 10.1), pas une proposition de marque.
5. **`assurance.piece` reste demandé** au formulaire : la colonne est `NOT NULL`
   en base, la retirer de l'écran rendrait toute création d'assurance impossible.
   Le corriger relève du modèle de données, pas de ce lot.

---

## 6. Vérifications réellement exécutées

| Vérification | Méthode | Résultat |
|---|---|---|
| Non-régression | `python -m pytest` depuis `src/` | **240 tests verts**, 1 avertissement (dépréciation `httpx` du client de test). Les tests de la phase 3, dont `tests/test_web.py` (14 tests), sont inclus et verts. |
| Aucun identifiant technique à l'écran | 10 écrans rendus, texte visible analysé : recherche d'UUID, de codes d'état (`non_commencee`, `a_verifier`), de noms de table, de références d'annexe, de noms de fournisseur de modèle | **0 occurrence**. Une fuite a été trouvée puis corrigée : `/bibliotheque/assurances` affichait deux UUID de documents. |
| Aucun débordement horizontal | `document.documentElement.scrollWidth` comparé à `window.innerWidth` après chaque capture | **390 px = 390 px sur les 13 écrans** (26 captures). |
| Écrans atteints sans session | `tests/test_web.py` (redirection 303 vers `/connexion?suivant=…`) | vert |
| Isolation entre clients | `tests/test_web.py::test_un_client_ne_peut_pas_atteindre_les_donnees_d_un_autre` | vert |
| Aucun bouton engageant | `tests/test_web.py::test_aucun_bouton_de_depot_d_envoi_ou_de_signature` et contrôle direct des gabarits | vert |
| Contrôle de périmètre du dépôt | `tests/integration/test_fuite_et_perimetre.py` | vert (le mot « prix » introduit dans une aide a été retiré du fait de ce contrôle) |

**Comment la session de capture a été ouverte.** Aucun mot de passe n'a été
saisi : la session a été fabriquée par le service de session de l'application
lui-même (jeton signé), exactement comme le fait la page de connexion. Les
comptes utilisés sont ceux du jeu de démonstration **fictif** déjà présent en
base, plus un espace vide créé pour l'occasion et signalé « FICTIF ».

**Ce qui n'a pas été fait.** Aucun test avec lecteur d'écran : l'accessibilité
tenue est celle du tableau mesuré de `docs/DESIGN.md` § 3 et des contrôles
ci-dessus, pas une conformité RGAA certifiée. Aucun déploiement, aucune
exposition sur Internet.

## 7. Contrastes

Les couples de couleurs sont repris **tels quels** du tableau mesuré du lot L4
(`docs/DESIGN.md` § 3) : le texte le plus faible est à 6,4:1, la bordure de champ
à 3,7:1, au-dessus des seuils AA (4,5:1 pour le texte, 3:1 pour le non textuel).
Aucune couleur n'a été inventée dans ce lot.
