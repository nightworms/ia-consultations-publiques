# PLAN-PHASE-4 — le mémoire technique argumenté, l'import guidé et la refonte de l'interface

*Rédigé par `plan` le 30 septembre 2026, à partir du cadrage d'Anthony, de
`PROJECT.md`, de `docs/DECISIONS.md` (D1 à D10), et de la lecture du code livré en
phase 3 (185 tests collectés, tous verts au 30/09). Ce document est le plan
d'exécution de la phase 4 ; il ne remplace pas `docs/DECISIONS.md`, qui reste
seul juge en cas de contradiction.*

---

## 1. Résultat visé

**La phase 4 est terminée quand la démonstration suivante s'exécute réellement,
en local via `bash demarrer.sh`, et que le parcours a été déroulé jusqu'au fichier
exporté :**

1. Un utilisateur se connecte et arrive sur un écran qui dit **ce que la
   plateforme fait pour lui**, avec **une action principale évidente**.
2. Il crée son entreprise, **importe deux ou trois documents existants** et
   obtient des **propositions à valider** — la bibliothèque se remplit sans saisie
   champ par champ.
3. Il **dépose un DCE** (jeu fictif) et voit les pièces exigées, les critères
   pondérés et la date limite, **chacun avec sa source**.
4. Il demande le **mémoire technique** et obtient un dossier **structuré suivant
   l'ordre et la pondération des critères du DCE**, où **chaque argument renvoie à
   un élément réel de sa bibliothèque**, et où **les manques sont listés avec
   l'action à mener**.
5. Il **exporte** ce mémoire dans un fichier ouvrable dans un traitement de texte.
6. **Aucun écran n'affiche de valeur technique, de jargon d'architecture, ni
   d'identifiant interne visible sans action de l'utilisateur** — contrôle fait en
   ouvrant chaque page et en la regardant (capture d'écran), sans déplier les blocs
   « Références techniques » (arbitrage `docs/DECISIONS.md` D11 : ces blocs restent
   admis, repliés par défaut, conformément à `DESIGN.md` § 5).

Critère de non-régression, à vérifier en même temps : **les 185 tests de la phase 3
restent verts**, l'analyse de DCE, l'isolation par client, le chiffrement et la
vérification de source sont inchangés dans leur comportement.

Une seule phrase pour trancher les arbitrages de la phase : **ce qui se voit et ce
qui démontre la valeur passe avant la perfection interne.**

---

## 2. Décisions gelées par `plan` avant répartition

Ces décisions sont **opposables** : les agents les appliquent, ils ne les
rediscutent pas entre eux. Elles existent pour qu'aucun lot n'ait à trancher à la
place d'un autre.

### A. Modèle de données — deux migrations, numérotées à la suite

- **`src/migrations/0005_memoire_technique.sql`** (`dev-back`, lot L2) crée :
  - `memoire_dossier` : `id`, `client_id`, `consultation_id`, `fiche_version_id`,
    `titre`, `statut` (`brouillon` \| `en_relecture` \| `valide`), `moteur_fournisseur`,
    `moteur_modele`, `avertissement`, `date_creation`, `date_modification` ;
  - `memoire_section` : `id`, `client_id`, `memoire_dossier_id`, `ordre`,
    `critere_code` (nullable), `critere_libelle`, `critere_poids` (nullable),
    `titre`, `contenu`, `statut` (`brouillon` \| `relue` \| `validee`),
    `origine`, `confiance`, `date_creation`, `date_modification` ;
  - `memoire_section_source` : `id`, `client_id`, `memoire_section_id`,
    `table_source` (nom de la table de bibliothèque citée), `element_id`,
    `libelle_source`, `emplacement_source` ;
  - `memoire_manque` : `id`, `client_id`, `memoire_dossier_id`, `critere_code`,
    `critere_libelle`, `critere_poids`, `constat`, `action_attendue` ;
  - `memoire_validation` : `id`, `client_id`, `memoire_dossier_id`,
    `nom_validateur`, `fonction_validateur`, `horodatage`, `empreinte_contenu`
    (SHA-256 du contenu validé), `format_export`, `nom_fichier`.
- **`src/migrations/0006_import_guide.sql`** (`dev-back`, lot L3) crée :
  - `import_document` : `id`, `client_id`, `document_id`, `famille_cible`,
    `statut` (`en_attente` \| `traite` \| `abandonne`), `moteur_fournisseur`,
    `moteur_modele`, `date_creation` ;
  - `import_proposition` : `id`, `client_id`, `import_document_id`,
    `famille`, `entite_cible` (nom de l'entité de `app.domain.familles`),
    `champs_proposes` (jsonb), `source_emplacement`, `source_extrait`,
    `statut` (`propose` \| `acceptee` \| `refusee`), `date_decision`,
    `decide_par`, `element_cree_id` (nullable).

Les deux migrations sont **réversibles** (`down` complet) et portent les mêmes
verrous que l'existant : `client_id` sur chaque table, index par `client_id`,
contraintes d'origine/confiance copiées du modèle de la phase 3. Aucune clé, aucune
donnée réelle, aucun `DROP` d'une table existante.

### B. La règle centrale de la phase, traduite en code

> L'IA peut **argumenter** et **valoriser** ; elle ne peut écrire que ce qui est
> rattachable à un élément réel de la bibliothèque du client. Ce qui ne l'est pas
> est **signalé comme manquant**, jamais inventé.

Traduction technique, non négociable :

- une section de mémoire est **produite seulement** si elle porte au moins une ligne
  dans `memoire_section_source` pointant un élément de bibliothèque **du même
  `client_id`** ; sinon elle n'existe pas : elle devient une ligne de
  `memoire_manque` avec le constat et l'action à mener ;
- `origine = document_extrait` exige `source_document_id`, `confiance = verifie`
  exige un contrôle humain nommé — règles déjà en place, réutilisées telles quelles ;
- **le contrôle de source existant est réutilisé, pas réécrit** :
  `app.services.fournisseur_modele.base.source_presente` et `verifier_propositions`
  restent la référence. Pour le mémoire, la source n'est pas un extrait de DCE mais
  un **élément de bibliothèque** : la même mécanique (*rien sans source vérifiable,
  refus explicite sinon*) s'applique, avec `memoire_section_source` comme support ;
- **aucun prix, aucun chiffre inventé, aucune conformité promise** nulle part dans
  les sorties du générateur (`PROJECT.md` § 5).

### C. Export — deux formats, une seule dépendance annoncée

- **Markdown (`.md`) = format canonique**, produit sans aucune dépendance nouvelle.
  C'est lui qui est testé et vérifié.
- **DOCX = format confort**, produit par la bibliothèque `python-docx` — pure
  Python, sans compilation, licence permissive, aucune ressource externe. Dépendance
  **annoncée et justifiée dans `docs/MEMOIRE-TECHNIQUE.md`** avant installation
  (exigence du cadrage). Si son installation échoue ou est refusée, l'export
  Markdown reste valide à lui seul et le lot n'est pas bloqué : le DOCX est alors
  écrit en « non disponible » avec sa raison.
- L'export **exige** une validation nommée et horodatée (ligne
  `memoire_validation` renseignée) ; sans elle, l'export est **refusé** avec un
  message qui dit quoi faire — pas une erreur technique.
- L'export est servi par un **fichier de routes dédié**
  (`src/app/api/routes_export.py`) : aucun lot ne modifie `routes_web.py` pour ça.

### D. Écrans — chemins gelés de la phase 4

Ajouts uniquement ; aucune route existante n'est renommée ni supprimée, aucune
route `/api/v1` n'est modifiée (contrat gelé en annexe C du plan de phase 3) :

| Chemin | Rôle | Lot |
|---|---|---|
| `GET /accueil` | écran d'accueil : ce que la plateforme apporte + action principale | L5a |
| `GET/POST /bibliotheque/import` | import guidé, propositions à valider | L5b |
| `GET /consultations/{id}/memoire` | mémoire généré, sections et manques | L5b |
| `POST /consultations/{id}/memoire` | demande de génération | L5b |
| `POST /consultations/{id}/memoire/sections/{sid}` | relire / corriger / valider une section | L5b |
| `POST /consultations/{id}/memoire/validation` | validation nommée et horodatée | L5b |
| `GET /consultations/{id}/memoire/export?format=md\|docx` | téléchargement | L6 |

**Après connexion, la cible est `/accueil`** (et non plus `/bibliotheque`) : c'est
le point 1 des critères d'acceptation. HTML servi côté serveur, Jinja2, **aucun
JavaScript**, aucune ressource chargée depuis un tiers (pas de CDN, pas de police
externe) : on reste dans le cadre de la phase 3 et dans l'hébergement France de D7.

### E. Répartition des fichiers — un seul écrivain par fichier

| Fichier | Écrivain unique |
|---|---|
| `docs/MEMOIRE-ATTENDU.md` | `batiment` (L1) |
| `docs/JURY-ACHETEUR.md` | `collectivite` (L1b) |
| `docs/MEMOIRE-TECHNIQUE.md`, `src/app/services/memoire_technique.py`, `src/app/domain/memoire_technique_genere.py`, migration `0005` | `dev-back` (L2) |
| `docs/IMPORT-GUIDE.md`, `src/app/services/import_guide.py`, `src/app/api/routes_import.py`, migration `0006` | `dev-back` (L3) |
| `docs/DESIGN.md`, `docs/maquettes/*.html` | `designer` (L4) |
| `src/app/web/static/style.css`, `src/app/web/templates/*.html`, `src/app/web/routes_web.py` | `dev-web` (L5a puis L5b, séquentiels) |
| `src/app/services/export_memoire.py`, `src/app/api/routes_export.py` | `dev-back` (L6) |
| `scripts/jeu-de-test/0002_jeu_demo_phase4.sql`, `scripts/jeu-de-test/fictif/*` | `docs` (L7) |

Note d'exécution : `src/app/api/routes.py` (agrégateur) est modifié par L3 puis L6 —
L6 a L3 comme parent, ils ne tournent jamais ensemble. Si L3 constate que cet
agrégateur est déjà un point de collision avec un autre lot, il le signale par un
`kanban_comment` préfixé `hotspot:` plutôt que d'empiler.

**Hotspot connu, signalé d'avance :** `src/app/web/templates/*.html` et
`routes_web.py` sont touchés par les deux lots `dev-web` (L5a, L5b) et par aucun
autre. C'est voulu : L5b a L5a pour parent, ils sont séquentiels, pas concurrents.
Aucun troisième lot ne doit y écrire.

---

## 3. Les lots

Estimation en **passes d'agent** (une passe = une exécution complète d'un profil) ;
fourchettes fondées sur le volume réel comparable des lots de la phase 3
(`docs/RAPPORTS/`).

### L1 — Ce qu'un jury note réellement : matière métier (`batiment`)

- **Livrable** : `docs/MEMOIRE-ATTENDU.md`.
- **Contenu exigé** : structure attendue d'un mémoire technique dans le bâtiment ;
  ce qui fait gagner des points (références comparables, moyens réellement affectés,
  méthode d'exécution, planning, sécurité, gestion des interfaces) ; les arguments
  qui **disqualifient** (promesses non étayées, copier-coller générique, absence de
  chiffres vérifiables, références hors sujet) ; pour chaque point, **de quoi la
  bibliothèque a besoin pour l'étayer** (nom exact d'une famille de la phase 3).
- **Dépendances** : aucune. **Estimation** : 1 à 2 passes.

### L1b — La vue de l'acheteur : ce que le jury regarde (`collectivite`)

- **Livrable** : `docs/JURY-ACHETEUR.md`.
- **Contenu exigé** : comment un mémoire est noté côté acheteur (grille, sous-critères,
  pondération, notation par plusieurs lecteurs), ce qui est éliminatoire et **ne
  relève pas du mémoire** (pièces administratives, forme), formulations à éviter
  parce qu'elles exposent juridiquement l'entreprise, et ce qu'un mémoire doit
  répondre **critère par critère**. Périmètre strictement générique et public :
  aucune donnée, aucun document, aucun cas réel issu de la collectivité (D4, D10).
- **Dépendances** : aucune. **Estimation** : 1 à 2 passes. Parallèle avec L1.

### L2 — Moteur de génération du mémoire technique (`dev-back`) — **priorité absolue**

- **Livrables** : `src/migrations/0005_memoire_technique.sql`,
  `src/app/services/memoire_technique.py`, `src/app/domain/memoire_technique_genere.py`,
  `src/app/api/routes_memoire.py`, tests dans `src/tests/test_memoire_technique.py` et
  `src/tests/integration/test_memoire_ligne_rouge.py`, plus le document
  `docs/MEMOIRE-TECHNIQUE.md`.
- **Comportement exigé** :
  1. **Plan = critères du DCE, dans l'ordre de pondération décroissante.** Le critère
     le plus lourd ouvre le mémoire et reçoit le développement le plus long. Un critère
     sans pondération connue passe en fin, avec sa raison affichée.
  2. **Une section = au moins une source de bibliothèque**, pointeur vers une famille
     réelle (`references_chantiers`, `certifications`, `moyens_humains`,
     `moyens_materiels`, `fiches_produits`, `assurances`, `capacites_financieres`,
     `memoire_technique`). Sans source : pas de section, mais une ligne de manque.
  3. **Les manques sont un résultat, pas une erreur** : libellé du critère, constat
     (« aucune référence correspondante dans votre bibliothèque »), **action à mener**
     (« ajoutez un chantier d'étanchéité de plus de 300 000 € »). C'est la
     fonctionnalité la plus utile du produit — elle ne s'affiche jamais comme un
     échec.
  4. **Une commande de génération reproductible** lancée depuis le parcours (dépôt DCE
     analysé + bibliothèque), sans appel réseau obligatoire : le fournisseur factice
     doit produire un mémoire démontrable hors ligne. Le fournisseur réel reste
     derrière l'adaptateur existant (D8), jamais appelé par les tests.
  5. **Statuts humains** : tout sort en `brouillon` ; une section ne passe `validee`
     que par une action humaine nommée et horodatée ; le dossier ne passe `valide`
     que par la ligne `memoire_validation`. Aucun chemin de code ne pose un statut
     validé tout seul.
- **Dépendances** : L1 et L1b (la matière première). **Parents** : L1, L1b.
- **Estimation** : 3 à 4 passes (le lot le plus lourd de la phase).

### L3 — Import guidé de documents dans la bibliothèque (`dev-back`)

- **Livrables** : `src/migrations/0006_import_guide.sql`,
  `src/app/services/import_guide.py`, `src/app/api/routes_import.py`, tests,
  `docs/IMPORT-GUIDE.md`.
- **Comportement exigé** :
  1. L'utilisateur dépose ses documents existants (ancien mémoire technique,
     plaquette, attestations, CV, attestations d'assurance, fiches produits).
  2. Le fournisseur **ne voit que le texte extrait** (`extraction_pdf`, déjà en
     place) et rend des **propositions sourcées** : `source_emplacement` obligatoire,
     `source_extrait` vérifié **littéralement** via `source_presente` — réutilisé tel
     quel, non réécrit.
  3. Rien n'entre dans la bibliothèque sans **validation humaine nommée** : la
     proposition vit dans `import_proposition` jusqu'à décision ; une proposition
     acceptée écrit un élément `origine = document_extrait`,
     `confiance = a_verifier`, avec son `source_document_id`.
  4. L'écran doit dire, pour chaque famille, **ce qui manque pour être prêt à
     concourir** — pas un pourcentage de complétion structurelle. La donnée vient de
     L3, l'affichage est fait par L5b.
  5. Formats acceptés : ceux de la phase 3 (`.pdf`, `.txt`), refus **explicite** des
     autres, jamais un échec silencieux.
- **Dépendances** : aucune (parallèle avec L2). **Estimation** : 2 à 3 passes.

### L4 — Direction de design, maquettes et textes d'interface (`designer`)

- **Livrables** : `docs/DESIGN.md`, maquettes HTML autonomes sous `docs/maquettes/`.
- **Contenu exigé** : note de direction lisible par un non-designer ; maquettes
  ouvrables dans un navigateur, **regardées réellement** (capture d'écran à l'appui
  dans le rapport) pour : accueil, bibliothèque + état d'avancement, import guidé,
  dépôt et analyse de DCE, consultation, mémoire technique, export, connexion ;
  **liste avant/après des textes d'interface** ; gabarits et feuille de style
  utilisables tels quels par `dev-web`.
- **Contraintes** : HTML servi côté serveur, aucun JavaScript, aucune ressource ni
  police chargée depuis un tiers, mobile utilisable (une PME consulte depuis un
  chantier), RGAA / WCAG AA tenus (contraste, clavier, libellés, structure de
  titres), une action principale par écran, **aucun identifiant technique, aucun
  jargon d'architecture, aucune référence à une annexe interne** à l'écran.
- **Dépendances** : aucune. **Estimation** : 2 à 3 passes.
- **Fichier à ne pas écrire** : `src/app/web/static/style.css` — c'est `dev-web` qui
  l'écrit (règle § 2.E). Le designer fournit le CSS **dans ses maquettes et dans
  `docs/DESIGN.md`**.

### L5a — Application du design aux écrans existants (`dev-web`)

- **Livrable** : refonte de `src/app/web/static/style.css` et des gabarits
  `base.html`, `connexion.html`, `bibliotheque.html`, `famille.html`,
  `consultations.html`, `consultation.html`, `checklist.html`, `premiere_utilisation.html`,
  `erreur.html` ; création de `src/app/web/templates/accueil.html` et de la route
  `GET /accueil`, **cible de redirection après connexion**.
- **Preuves exigées** : une capture d'écran **par écran touché**, en desktop **et**
  en mobile (fenêtre étroite), avec le constat visuel écrit à côté. Le design se juge
  à l'écran, pas dans un document.
- **Dépendances** : L4. **Parents** : L4. **Estimation** : 2 à 3 passes.

### L5b — Écrans du mémoire et de l'import guidé (`dev-web`)

- **Livrable** : les écrans `/bibliotheque/import`, `/consultations/{id}/memoire`,
  l'affichage des manques avec leur action à mener, les actions de relecture et de
  validation nommée, l'état d'avancement « ce qui vous manque pour être prêt à
  concourir », et le **lien de téléchargement** vers l'export.
- **Contraintes** : mêmes règles que L5a ; le vocabulaire affiché est celui du
  métier (`non_commencee` → « À compléter », jamais un état de code à l'écran) ;
  aucun bouton de dépôt, d'envoi ou de signature ; toute valeur affichée porte sa
  source.
- **Dépendances** : L5a (gabarits et feuille de style), L2 et L3 (services exposés).
- **Parents** : L5a, L2, L3. **Estimation** : 2 à 3 passes.

### L6 — Export téléchargeable du mémoire (`dev-back`)

- **Livrables** : `src/app/services/export_memoire.py`, `src/app/api/routes_export.py`,
  tests (`src/tests/test_export_memoire.py`), section d'export de
  `docs/MEMOIRE-TECHNIQUE.md`.
- **Comportement exigé** : `GET /consultations/{id}/memoire/export?format=md|docx` ;
  refus explicite et pédagogique si la validation nommée/horodatée manque ; Markdown
  canonique sans dépendance ; DOCX via `python-docx` **installé après annonce et
  justification** (et dégradation propre si absent) ; le fichier exporté porte le
  contenu **validé** (empreinte SHA-256 enregistrée dans `memoire_validation`) ;
  aucune donnée d'un autre client, jamais.
- **Dépendances** : L2 (schéma et service), L3 (agrégateur de routes utilisé par le
  même fichier `src/app/api/routes.py`). **Parents** : L2, L3.
- **Estimation** : 1 à 2 passes.

### L7 — Jeu de démonstration fictif complet (`docs`)

- **Livrables** : `scripts/jeu-de-test/0002_jeu_demo_phase4.sql` et documents fictifs
  sous `scripts/jeu-de-test/fictif/`.
- **Contenu exigé** : un compte de démonstration, **une entreprise fictive du
  bâtiment / étanchéité**, sa bibliothèque **réellement remplie** (références de
  chantiers comparables, certifications, moyens humains et matériels, fiches
  produits, assurances, capacités financières, chapitres de mémoire type), et
  **un DCE fictif** déposable (pièces exigées, critères pondérés dont un critère
  lourd, date limite) — accompagné d'un mode opératoire de démonstration en 6 étapes
  reprenant les critères d'acceptation.
- **Contraintes** : tout est **fictif et signalé comme tel**, aucun document réel
  d'acheteur, aucune donnée réelle d'entreprise (D10), aucun mot de passe en clair
  versionné, idempotence (`ON CONFLICT DO NOTHING`, UUID fixes).
- **Dépendances** : aucune pour l'entreprise, la bibliothèque et le DCE (écrits tout
  de suite). **Le mémoire n'est pas seeded** : il se génère par le parcours, sinon la
  démonstration ne démontre rien. **Estimation** : 2 à 3 passes.

### L8 — Vérification indépendante des critères d'acceptation (`qa`)

- **Livrable** : `docs/RAPPORTS/P4-qa-criteres-acceptation.md` + captures.
- **Méthode imposée** : exécuter réellement `bash demarrer.sh`, **ouvrir chaque page
  et la regarder**, dérouler les **six** critères d'acceptation du § 1 dans l'ordre,
  sur le jeu de démonstration de L7 ; vérifier les migrations `0005`/`0006` en `up`
  **et** en `down` ; vérifier que **les 185 tests de la phase 3 restent verts** ainsi
  que les nouveaux ; chercher, écran par écran, un identifiant technique, un jargon
  d'architecture ou une référence à une annexe interne, et le **prouver par capture**
  s'il en reste un. Un rapport fondé sur la lecture du code **ne compte pas**.
- **Dépendances** : L2, L3, L5a, L5b, L6, L7.
- **Parents** : L2, L3, L5a, L5b, L6, L7. **Estimation** : 2 à 3 passes.

---

## 4. Ordre, parallélismes, et pourquoi

**Vague 1 — la valeur et le décor, en parallèle (aucun parent) :**

- L1 `batiment` — matière métier du mémoire
- L1b `collectivite` — vue du jury
- L3 `dev-back` — import guidé
- L4 `designer` — direction de design
- L7 `docs` — jeu de démonstration fictif

Pourquoi ensemble : aucun ne dépend d'un autre, aucun n'écrit dans le fichier d'un
autre (§ 2.E). **L1/L1b sont la matière première du chantier A : ils passent en
premier** — le moteur de mémoire en dépend, et c'est la valeur du produit.

**Vague 2 — le cœur :**

- L2 `dev-back` — moteur de génération du mémoire (après L1 et L1b)
- L5a `dev-web` — refonte des écrans existants (après L4)

Pourquoi L2 après L1/L1b et pas avant : générer une structure de mémoire sans savoir
ce qu'un jury note revient à produire des paragraphes creux — exactement le risque
principal du § 5. L2 peut être préparé (schéma, service) dès que L1/L1b ont **commencé**
à écrire, mais il ne peut pas **conclure** avant eux.

L5a peut démarrer dès que L4 a livré sa direction, sans attendre L2 : il refait des
écrans qui existent déjà.

**Vague 3 — les écrans qui dépendent des nouveaux services :**

- L5b `dev-web` — écrans mémoire et import (après L5a, L2, L3)
- L6 `dev-back` — export (après L2, L3)

L5b après L5a obligatoirement : un seul écrivain sur `templates/` et `style.css`.

**Vague 4 — la preuve :**

- L8 `qa` — parcours complet, écran par écran (après tout le reste)

**Chemin critique : L1/L1b → L2 → L5b → L8.** C'est le chemin du chantier A ; tout
retard sur L1, L2 ou L5b retarde la démonstration. Le chantier C (L4, L5a) est le
seul à pouvoir se terminer sans que le chemin critique avance — d'où son intérêt comme
travail parallèle.

---

## 5. Risques

| # | Risque | Probabilité | Impact | Parade |
|---|---|---|---|---|
| R1 | **Mémoire technique creux parce que la bibliothèque est vide** | **élevée** | **majeur** — c'est la valeur du produit qui disparaît | Traiter les manques comme un résultat (L2 § 2.B) et rendre l'import guidé (L3) jouable **avant** la démonstration ; L7 fournit une bibliothèque fictive **déjà remplie** ; L8 vérifie explicitement qu'un critère lourd sans référence produit un **manque écrit avec action**, et non une section vide ou inventée |
| R2 | Le générateur produit des phrases non rattachables à un élément réel | moyenne | majeur — violation de la ligne rouge | Aucune section sans ligne `memoire_section_source` du même `client_id` ; mécanique `verifier_propositions` / `source_presente` réutilisée ; test d'intégration dédié (`test_memoire_ligne_rouge.py`, L2) ; contrôle humain obligatoire avant export |
| R3 | Complexité du DOCX : dépendance qui refuse de s'installer ou corruption du fichier | moyenne | modéré — le critère 5 tombe | Markdown est canonique et suffit seul ; DOCX dégradé proprement en « non disponible » avec sa raison ; dépendance annoncée avant installation (§ 2.C) |
| R4 | La refonte casse les écrans existants ou l'accessibilité déjà tenue | moyenne | majeur — régression sur du code qui marche | L5a touche les gabarits sans toucher la logique de `routes_web.py` ; captures desktop **et** mobile obligatoires ; les 185 tests de la phase 3 vérifiés verts par L8 ; un seul écrivain par fichier |
| R5 | Le designer produit de belles maquettes inapplicables en HTML servi côté serveur (JS, dépendance CDN) | moyenne | modéré — perte de temps | Cadre verrouillé dans la carte L4 : aucun JS, aucune ressource tierce, gabarits et CSS utilisables tels quels ; maquettes jugées **à l'écran** avec capture |
| R6 | Fuite entre clients dans les nouvelles tables (mémoire, import) | faible | **majeur** — violation de D6/D7 | `client_id` sur chaque table, index et contraintes copiés du modèle phase 3 ; tests d'isolation pour le mémoire et l'import ajoutés aux tests existants ; L8 tente l'accès croisé |
| R7 | L'analyse de DCE ou la checklist régressent au contact des nouveaux lots | faible | majeur | Interdiction explicite de modifier le comportement des briques B et C ; L6 (export) et L3 (import) sont les seuls à toucher `src/app/api/routes.py`, et **jamais en même temps** (parent L3) |
| R8 | `docs/Model de dossier de consultation/` (exclu par `.gitignore`) est réintégré par erreur | faible | majeur — D10 | Consigne dans chaque carte : ne pas y toucher, ne pas la remettre dans git ; L8 vérifie `git status` et l'absence de nouveau fichier ignoré suivi |
| R9 | Le fournisseur factice produit un mémoire non démontrable hors ligne | moyenne | modéré — démonstration impossible chez Anthony | L2 exige une génération **reproductible sans réseau** ; L7 fournit un DCE et une bibliothèque conçus pour ce parcours ; L8 déroule la démo hors ligne |
| R10 | Les 7 lots parallèles se marchent dessus dans `templates/`, `routes.py`, `style.css` | moyenne | modéré | Répartition § 2.E : un écrivain par fichier ; les deux lots `dev-web` sont séquentiels ; les deux écrivains de `routes.py` sont séquentiels par dépendance ; tout nouveau conflit se signale par `kanban_comment` préfixé `hotspot:` |
| R11 | Anthony rentre demain matin et la refonte est finie mais la démonstration ne tourne pas | modéré | majeur — c'est ce qu'il veut voir | Ordre § 4 : le chemin critique est le chantier A ; L7 (jeu de démo) démarre en vague 1 pour que la démo soit regardable dès la fin de L2/L5b, sans attendre L8 |

---

## 6. Questions ouvertes pour Anthony

1. **Critère d'effort du mémoire.** Le mémoire suit l'ordre de pondération des
   critères, mais **quelle longueur viser** — une page par critère lourd, un
   développement proportionnel au poids, ou un plafond de pages fixé par défaut ?
   Tant qu'il n'y a pas de réponse, le défaut appliqué est *proportionnel au poids,
   sans plafond, chaque section portant sa longueur visible* pour qu'Anthony puisse
   trancher sur pièce.
2. **DOCX** — la dépendance `python-docx` est proposée (§ 2.C). Elle est légère et
   pure Python, mais elle doit être **annoncée avant installation** : Anthony
   l'accepte-t-il, ou veut-on se limiter au Markdown pour cette phase ?
3. **Identité du jeu de démonstration.** Le jeu fictif (L7) sera une entreprise
   d'étanchéité fictive à La Réunion. Veut-on **reprendre le vocabulaire du lot
   M 240219** (écoles du Brûlé et La Source) dans les libellés fictifs, ou rester
   volontairement sur un acheteur entièrement inventé pour éviter toute confusion
   avec un marché réel ? Le défaut retenu est **acheteur entièrement inventé**.
4. **Reprise du « mémoire technique type » existant.** La famille 9 de la phase 3
   stocke des chapitres réutilisables. La génération doit-elle **réutiliser ces
   chapitres** quand ils existent (au risque d'écrire du texte non spécifique au
   DCE), ou toujours repartir de la bibliothèque factuelle ? Le défaut retenu :
   les chapitres type servent de **source citée**, jamais de texte recopié sans
   source.
5. **Signature.** Le critère 5 parle d'un mémoire « relu et signé par un humain ».
   La phase 4 s'arrête à une **validation nommée et horodatée** écrite en base, sans
   signature électronique (hors périmètre, cf. cadrage). Anthony confirme-t-il que
   c'est suffisant pour cette phase ?

---

## 7. Ce que la phase 4 ne fait pas

- Pas de dépôt de pli, pas de signature électronique, pas de connexion à une
  plateforme d'achat public.
- Pas de chiffrage, pas de prix, pas de marge — le prix reste humain.
- Pas de paiement, pas de facturation (prévus dans le modèle, D3, non implémentés).
- Pas de mise en production, pas d'exposition sur Internet : tout tourne en local via
  `bash demarrer.sh`.
- Pas de veille, pas de portail acheteur (hors périmètre, D1).
- Aucune donnée réelle d'entreprise, aucun document réel d'acheteur (D10).

---

## Annexe — cartes du tableau, telles que créées

Toutes liées à la tâche racine `t_6e786df0`, **workspace (dir)
`/Users/pause/Projets/ia-consultations-publiques`** pour chacune.

| Lot | Agent | Carte | Dépend de (parents) |
|---|---|---|---|
| L1 | `batiment` | `t_9b34a954` | racine |
| L1b | `collectivite` | `t_9d4bf19f` | racine |
| L3 | `dev-back` | `t_ac37771a` | racine |
| L4 | `designer` | `t_da242ec2` | racine |
| L7 | `docs` | `t_cf9fc4fd` | racine |
| L2 | `dev-back` | `t_1980f535` | L1, L1b |
| L5a | `dev-web` | `t_68a7610d` | L4 |
| L5b | `dev-web` | `t_fc62edbd` | L5a, L2, L3 |
| L6 | `dev-back` | `t_c01dec33` | L2, L3 |
| L8 | `qa` | `t_097bbe97` | L2, L3, L5a, L5b, L6, L7 |

**Cartes à archiver par l'opérateur — doublons créés par erreur** (workspace
`scratch` au lieu du dossier du projet, puis recréés en `dir`) :
`t_113ef24f` (L1), `t_7b0ad42f` (L1b), `t_a696d085` (L3), `t_e61eda7a` (L4),
`t_a544bdf7` (L7). Chacune porte un commentaire « CARTE ANNULÉE » qui demande au
worker de se bloquer immédiatement ; **elles ne doivent pas être exécutées** —
les écrivains uniques de `docs/MEMOIRE-ATTENDU.md`, `docs/JURY-ACHETEUR.md`,
`0006_import_guide.sql`, `docs/DESIGN.md` et du jeu de démonstration sont les
cartes `dir` ci-dessus.
