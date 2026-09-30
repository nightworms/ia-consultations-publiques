# DEMONSTRATION — jeu fictif de la phase 4 (lot L7)

*Mode opératoire en 6 étapes, aligné sur les critères d'acceptation du
`docs/PLAN-PHASE-4.md` § 1. Rédigé par l'agent `docs` le 30 septembre 2026, après
exécution réelle du jeu : les résultats annoncés ici sont **observés**, pas prévus
(§ « Ce qui a été réellement exécuté » en fin de document).*

**Tout est FICTIF.** Aucune entreprise, aucune collectivité, aucun marché, aucun
assureur, aucun organisme certificateur réel (décision D10). L'acheteur de la
consultation déposable est entièrement inventé : *Syndicat Intercommunal Fictif des
Écoles de la Plaine des Filaos (S.I.F.E.P.F.)*.

---

## 0. Prérequis et installation du jeu

| À vérifier | Comment |
|---|---|
| PostgreSQL répond | `pg_isready -h 127.0.0.1 -p 5432` |
| `.env` renseigné | `DATABASE_URL`, `CLE_CHIFFREMENT_MAITRESSE`, `CLE_SESSION` présents |
| Migrations appliquées | fait par le chargeur, étape 1 |

**Une seule commande** charge tout le jeu (migrations, données, pièces, compte) :

```bash
bash scripts/jeu-de-test/charger_demo_phase4.sh
```

Le script **demande deux fois, en saisie masquée**, le mot de passe du compte de
démonstration (**12 caractères minimum**). Il n'est jamais passé en argument, jamais
écrit dans un fichier, jamais affiché. **Notez-le : il sera demandé à l'étape 1.**
Aucun mot de passe — même fictif — ne figure dans un fichier versionné.

Ce que le chargeur pose, dans l'ordre :

1. `src/migrations/` → `python -m app.storage.migrations up` ;
2. `scripts/jeu-de-test/0002_jeu_demo_phase4.sql` → données non chiffrées, UUID
   fixes, idempotent ;
3. `scripts/jeu-de-test/completer_demo_phase4.py` → champs **chiffrés par client**
   (`entreprise_version`, `representant_legal`, `exercice_comptable`, montants des
   références), **hachage Argon2id** du mot de passe, écriture des 6 pièces sources
   chiffrées sous `data/clients/<client_id>/` (répertoire réellement configuré :
   `REPERTOIRE_DOCUMENTS` du `.env`).

Puis lancez l'application :

```bash
bash demarrer.sh          # http://127.0.0.1:8000/connexion
```

**Identités du jeu (UUID fixes)** — identiques dans le SQL, dans le compléteur et ici :

| Objet | Valeur |
|---|---|
| `client_id` | `d0000000-0000-4000-8000-000000000001` |
| `utilisateur_id` | `d0000000-0000-4000-8000-000000000002` |
| identifiant de connexion | `demo@exemple.invalid` |
| `entreprise_id` | `d0000000-0000-4000-8000-000000000003` |
| `fiche_version_id` | `d0000000-0000-4000-8000-000000000004` |

### Contenu de la bibliothèque posée par le jeu

| Famille | Contenu fictif |
|---|---|
| Identité | `OCÉAN ÉTANCHÉITÉ (FICTIF)`, SAS, SIREN/SIRET fictifs, siège, effectif 24 + représentant légal |
| Capacités financières | exercices 2024 et 2025 (CA 3,8 M€ puis 4,12 M€), 2 capacités de production |
| Assurances | RC décennale (**échéance 2026-10-15**) et RC professionnelle (échéance 2027-01-31) |
| Certifications | qualification étanchéité (**échéance 2026-09-15, dépassée**) + habilitation travaux en hauteur |
| Références de chantiers | **4 chantiers comparables** (412 000 / 268 000 / 195 000 / 156 000 EUR) |
| Moyens humains | 4 effectifs par métier (16 étancheurs, 4 chefs d'équipe, 2 conducteurs, 1 QSE) + organigramme |
| Moyens matériels | 4 moyens (groupe à air chaud, nacelle, camion-benne, monte-charge) |
| Fiches produits | 2 produits (membrane bitumineuse autoprotégée, membrane synthétique) |
| Mémoire technique type | 2 chapitres réutilisables (méthode d'exécution, site occupé) |

**Le mémoire technique de la consultation n'est pas semé** : il se génère par le
parcours (étape 4). Sinon la démonstration ne démontrerait rien.

---

## 1. Se connecter et voir ce que la plateforme apporte

*Critère 1 — un écran qui dit ce que la plateforme fait pour lui, avec une action principale évidente.*

1. Ouvrir `http://127.0.0.1:8000/connexion`.
2. Identifiant `demo@exemple.invalid`, mot de passe choisi à l'étape 0.
3. Après connexion, on arrive sur l'écran principal.

**À quoi s'attendre à ce jour** : la redirection après connexion pointe encore sur
`/bibliotheque` (état du code au 30/09/2026). La cible `/accueil` — l'écran « ce que
la plateforme apporte + action principale » — est livrée par le lot **L5a**
(`docs/PLAN-PHASE-4.md` § 2.D). Tant que L5a n'a pas écrit `accueil.html`, le
critère 1 n'est **pas** satisfait : c'est un point de vérification de L8, pas un
oubli de ce document.

À contrôler sur cet écran : aucune valeur technique, aucun jargon d'architecture,
aucun identifiant interne (critère 6).

---

## 2. Créer l'entreprise, importer deux ou trois documents

*Critère 2 — la bibliothèque se remplit sans saisie champ par champ.*

**Deux variantes, à choisir selon ce qu'on veut montrer :**

- **Variante A — le chemin « page blanche »** : avec un compte neuf (aucune
  entreprise), `/bibliotheque` affiche l'écran de première utilisation
  (`/entreprises/nouvelle`). On crée l'entreprise, on ouvre sa première fiche, puis
  on importe les documents.
- **Variante B — le compte de démonstration est déjà rempli** (ce que pose le jeu) :
  l'entreprise et sa bibliothèque existent, ce qui permet d'aller **directement** au
  mémoire (étape 4) sur une bibliothèque fournie. C'est la variante qui démontre la
  valeur du produit ; la variante A démontre le **parcours de remplissage**.

**Documents à importer** (`scripts/jeu-de-test/fictif/`, format `.txt` accepté par
la brique d'analyse — `.pdf` accepté aussi) :

| Fichier | Ce que l'import doit en tirer |
|---|---|
| `fictif/plaquette-presentation-FICTIF.txt` | identité, qualifications, assurances, moyens, résumé des références |
| `fictif/memoire-technique-anterieur-FICTIF.txt` | chapitres réutilisables (méthode d'exécution, planning, site occupé) |
| `fictif/attestation-assurance-RCD-FICTIF.txt` | attestation d'assurance (échéance 2026-10-15, type, assureur, montant) |

Écran attendu : `/bibliotheque/import` (lot **L3** pour le service et la route,
lot **L5b** pour l'écran). Ce que la démonstration doit montrer :

- des **propositions sourcées** — chacune avec son emplacement et son extrait
  littéral ;
- **rien n'entre dans la bibliothèque sans validation humaine nommée** ;
- un élément accepté est écrit en `origine = document_extrait`,
  `confiance = a_verifier`, avec son `source_document_id` ;
- l'écran dit, par famille, **ce qui manque pour être prêt à concourir**.

Si L3/L5b ne sont pas encore livrés au moment de la démonstration, la
bibliothèque du jeu reste utilisable : passez directement à l'étape 3.

---

## 3. Déposer le DCE fictif et lire l'analyse

*Critère 3 — pièces exigées, critères pondérés et date limite, chacun avec sa source.*

1. Aller sur `/consultations`.
2. Déposer le fichier `scripts/jeu-de-test/fictif/DCE-FICTIF-DEMO-2026-ETN-001.txt`.
3. Renseigner le formulaire (champs saisis par l'humain, jamais déduits du document) :

| Champ | Valeur à saisir |
|---|---|
| Libellé | `FICTIF — réfection étanchéité toitures-terrasses (2 groupes scolaires fictifs)` |
| Référence de consultation | `FICTIF-DEMO-2026-ETN-001` |
| Maître d'ouvrage déclaré | `S.I.F.E.P.F. (maître d'ouvrage FICTIF)` |
| Entreprise | `FICTIF — Océan Étanchéité` |

**Résultat observé** (analyse hors ligne, exécutée réellement — voir en fin de
document) : **15 éléments extraits, 0 catégorie non trouvée** — 8 pièces exigées,
6 critères, 1 date limite.

Pièces exigées lues (extrait littéral, source « page 1, ARTICLE 3 ») :

- Attestation d'assurance responsabilité civile décennale en cours de validité
- Attestation d'assurance responsabilité civile professionnelle en cours de validité
- Certificat de qualification professionnelle de l'entreprise dans le domaine de l'étanchéité
- Fiche technique du procédé d'étanchéité proposé (référence fournisseur exacte)
- Liste des moyens humains affectés au marché (effectifs, qualification, encadrement)
- Liste des moyens matériels affectés au marché (engins, matériel de mise en oeuvre)
- Trois références de chantiers comparables au maximum, avec montant, année et maître d'ouvrage
- Attestation de bonne exécution d'un chantier comparable, délivrée par son maître d'ouvrage

Critères pondérés (source « page 1, ARTICLE 5 ») — **le critère lourd est à 40 %** :

| Critère | Pondération |
|---|---|
| **Étanchéité de toitures-terrasses sur bâtiments scolaires** | **40 %** |
| Traitement des relevés d'étanchéité et des points singuliers | 20 % |
| Exécution en site occupé et planning par phases | 15 % |
| Moyens humains et matériels affectés au marché | 10 % |
| Expérience en toitures-terrasses végétalisées | 10 % |
| Délai d'exécution et engagement de planning | 5 % |

Date limite : ligne littérale « Date limite de remise des offres : 12 décembre 2026
à 12 h 00 (heure locale) », valeur lue **2026-12-12** (source « page 1, ARTICLE 6 »).

Chaque élément est **`propose`** tant qu'un humain ne l'a pas validé : les états
« à vérifier » doivent être visibles à l'écran, et l'action de validation demandée
un **nom**.

### Checklist de conformité (bonus, brique C déjà livrée)

Après avoir validé les 8 pièces exigées (nom obligatoire), la checklist croise ces
pièces avec les documents de la bibliothèque. **Résultat observé** : 4 `presente`,
3 `a_verifier`, **1 `manquante`**. Détail :

| Statut | Pièce exigée | Motif affiché |
|---|---|---|
| presente | Fiche technique du procédé d'étanchéité proposé | pièce de la bibliothèque retenue |
| presente | Attestation d'assurance RC professionnelle | pièce retenue |
| presente | Attestation d'assurance RC décennale | pièce retenue |
| presente | Attestation de bonne exécution d'un chantier comparable | pièce retenue |
| a_verifier | Certificat de qualification professionnelle | pièce présente **mais échéance dépassée** (2026-09-15) |
| a_verifier | Trois références de chantiers comparables | correspondance incertaine |
| a_verifier | Liste des moyens humains affectés au marché | correspondance incertaine |
| **manquante** | **Liste des moyens matériels affectés au marché** | **aucune pièce correspondante ; le système ne fabrique rien** |

À vérifier à l'écran : la pièce `manquante` ne porte **aucun** document, et aucune
conclusion de conformité n'est écrite nulle part (« outil d'aide à la relecture,
pas un certificat »).

---

## 4. Demander le mémoire technique

*Critère 4 — mémoire structuré suivant l'ordre et la pondération des critères, chaque argument rattaché à la bibliothèque, manques listés avec l'action à mener.*

1. Sur la consultation, demander la génération : `POST /consultations/{id}/memoire`
   (service et schéma : lot **L2**, écran : lot **L5b**).
2. Lire l'écran `/consultations/{id}/memoire`.

Ce qui doit être visible, et qui est le cœur du produit :

- le plan suit **l'ordre de pondération décroissante** : le critère à 40 % ouvre le
  mémoire et reçoit le développement le plus long ;
- **chaque argument renvoie à un élément réel** de la bibliothèque du client
  (table source + libellé + emplacement) ;
- **les manques sont un résultat, pas une erreur** : libellé du critère, constat,
  et **action à mener** ;
- tout sort en `brouillon` ; un statut validé n'est posé que par une validation
  humaine nommée et horodatée.

### Manque volontaire — ce que la démonstration doit faire apparaître

Le jeu est construit pour que **le critère lourd soit satisfaisable** et pour qu'
**au moins un manque soit visible**. Les deux manques prévus :

1. **Critère sans référence — « Expérience en toitures-terrasses végétalisées »
   (10 %)**. Aucune des 4 références de la bibliothèque ne porte « végétalisé »
   (vérifiable par la requête ci-dessous). C'est le manque principal : le mémoire
   doit le lister comme une **ligne de manque avec l'action à mener**, jamais comme
   une section vide ni comme une phrase inventée.
2. **Pièce exigée sans pièce dans la bibliothèque — « Liste des moyens matériels
   affectés au marché »**. Observé en checklist (tableau ci-dessus) ; la brique
   existante le prouve déjà.

Le critère lourd à 40 % (*étanchéité de toitures-terrasses sur bâtiments
scolaires*) est, lui, couvert par la référence `d0000000-0000-4000-8000-000000000901`
(« groupe scolaire Les Filaos », 412 000 EUR, 2024), dont la description et les
compétences reprennent le vocabulaire du critère (toitures-terrasses, bâtiments
scolaires, relevés et points singuliers, site occupé par phases).

### Vérifier ces deux affirmations soi-même (SQL, lecture seule)

```bash
psql "$DATABASE_URL" -c "
SELECT id, intitule_operation, montant_montant IS NOT NULL AS montant_chiffre, nature_travaux_libelle
FROM reference_chantier WHERE client_id='d0000000-0000-4000-8000-000000000001' ORDER BY id;"

# Le critère lourd (végétalisées) n'est couvert par AUCUNE référence :
psql "$DATABASE_URL" -c "
SELECT count(*) AS references_couvrant_le_manque FROM reference_chantier
WHERE client_id='d0000000-0000-4000-8000-000000000001'
  AND (intitule_operation || ' ' || coalesce(description,'') || ' ' || coalesce(competences_appliquees,''))
      ILIKE '%végétalis%';"          -- attendu : 0
```

---

## 5. Exporter le mémoire

*Critère 5 — un fichier ouvrable dans un traitement de texte.*

1. Valider nommément le mémoire (`POST /consultations/{id}/memoire/validation`).
2. Télécharger : `/consultations/{id}/memoire/export?format=md` — **Markdown,
   format canonique, sans dépendance** (lot **L6**).
3. `format=docx` est le format confort (dépendance `python-docx`, annoncée et
   justifiée dans `docs/MEMOIRE-TECHNIQUE.md`). **Sans validation nommée et
   horodatée, l'export est refusé** — avec un message qui dit quoi faire, pas une
   erreur technique.

---

## 6. Relire chaque écran (contrôle final)

*Critère 6 — aucun écran n'affiche de valeur technique, de jargon d'architecture ni
d'identifiant interne.*

Ouvrir **chaque** page et la regarder, en desktop **et** en fenêtre étroite :
connexion, accueil (L5a), bibliothèque, une famille, import guidé, consultations,
consultation (analyse), checklist, mémoire, export, page d'erreur.
À chercher, et à **prouver par capture** si un reste subsiste : un `client_id`, un
nom de table, un code d'état interne (`non_commencee`, `a_verifier`), une référence
à une annexe. C'est le contrôle assigné au lot **L8**.

---

## Recharger ou retirer le jeu

- **Recharger** : relancer `bash scripts/jeu-de-test/charger_demo_phase4.sh`. Tout
  est idempotent (UUID fixes, `ON CONFLICT DO NOTHING`) : rien n'est dupliqué. Le
  mot de passe saisi remplace le précédent.
- **Retirer le jeu** : le bloc de nettoyage est **commenté à la fin de
  `0002_jeu_demo_phase4.sql`** (ordre inverse des dépendances, filtré par le
  `client_id` de démonstration). Le décommenter et l'exécuter explicitement, puis
  supprimer les pièces :
  `rm -rf "$REPERTOIRE_DOCUMENTS/clients/d0000000-0000-4000-8000-000000000001"`.
- **Où atterrissent les pièces** : sous `$REPERTOIRE_DOCUMENTS/clients/<client_id>/`
  (voir le `.env` ; sur cette machine `REPERTOIRE_DOCUMENTS` vaut `verif-data`).
  Attention : contrairement à `data/`, **`verif-data/` n'est pas dans
  `.gitignore`** — 4 `.bin` chiffrés de la base de vérification de la phase 3 y
  sont déjà suivis par git. Les 6 pièces de ce jeu apparaissent donc comme
  **nouveaux fichiers non suivis** : à committer ou non, c'est un choix
  d'exploitant à faire explicitement (recommandation : ne pas les committer, ils
  sont régénérés par le chargeur ; ou déplacer `REPERTOIRE_DOCUMENTS` hors du
  dépôt). Aucun fichier de `verif-data/` n'a été ajouté à git par le lot L7.

## Réglage optionnel : faire apparaître l'alerte « échéance proche »

Le projet ne fixe **aucun seuil dans le code** : sans réglage, seul un document
déjà **expiré** déclenche une alerte. Dans ce jeu, la certification à échéance
2026-09-15 est déjà dépassée (alerte garantie) ; l'assurance RC décennale à
échéance **2026-10-15** n'apparaît « échéance proche » que si la fenêtre est
réglée. Pour la montrer :

```bash
echo 'FENETRE_ALERTE_JOURS=60' >> .env     # puis relancer bash demarrer.sh
```

## Fournisseur de lecture du DCE

Le jeu est conçu pour fonctionner **hors ligne** : déposer le DCE avec le
fournisseur `factice` (règles de lecture, aucun réseau) suffit à produire les 15
éléments. Si le `.env` configure un fournisseur réel (`MODELE_FOURNISSEUR`), c'est
lui qui lit le DCE — et il découpe différemment le libellé et la « valeur » de
chaque pièce, ce qui fait **augmenter le nombre de lignes `a_verifier`** en
checklist (observé : 2 `presente` sur 8 au lieu de 4, les deux attestations
d'assurance se retrouvant alors en correspondance multiple). Les deux
comportements sont légitimes ; c'est le fournisseur qui change, pas le jeu.

---

## Écarts constatés, et ce qui reste à confirmer

Ce document ne lisse aucun écart. Chacun porte sa preuve.

1. **`entreprise_version.capital_social_montant` : registre et schéma se
   contredisent.** `app/domain/securite.py` le déclare **chiffré** (entité
   `entreprise_version`), mais la migration `0002_bibliotheque.sql` le type
   `numeric(18,2)` — donc non chiffrable. Écrire une charge `v1:<base64>` y est
   refusé par PostgreSQL ; lire un nombre en clair y provoque
   `ErreurDechiffrement` (le déchiffreur exige le préfixe `v1:`). Le jeu laisse
   donc ce champ **NULL** (et la devise avec lui, la contrainte de paire l'exige) :
   l'identité s'affiche, mais **sans capital social**.
   *Preuve* : `psql "$DATABASE_URL" -f` du jeu → `ERROR: invalid input syntax for
   type numeric: "v1:..."` (observé au premier passage) ; et
   `SELECT data_type FROM information_schema.columns WHERE table_name='entreprise_version'
   AND column_name='capital_social_montant';` → `numeric`.
   **À corriger par le lot propriétaire de la migration** (L1/`batiment` ou le
   `dev-back` qui détient `0002`) : soit typer la colonne `varchar(2048)` comme les
   autres champs chiffrés, soit retirer le champ du registre sensible. Le lot L7
   n'a pas le droit d'écrire dans `0002_bibliotheque.sql`.
2. **`attestation` et `cv` sont laissées vides.** Leur pièce justificative est un
   champ **chiffré** qui référence un `document.id` : les remplir aurait exigé deux
   documents fictifs de plus sans rien apporter à la démonstration. Les familles
   n'en sont pas moins remplies (`capacites_financieres` : 2 exercices + 2 capacités
   de production ; `moyens_humains` : 4 effectifs + 1 organigramme — vérifié).
   *À confirmer par Anthony* : veut-on un CV et une attestation fictifs de plus ?
3. **Le critère 1 dépend du lot L5a.** Après connexion, la redirection pointe
   encore vers `/bibliotheque` au 30/09/2026 ; l'écran `/accueil` est livré par L5a.
   Le critère 1 ne peut pas être coché avant.
4. **Le critère 2 dépend des lots L3 et L5b** (écran `/bibliotheque/import`). Le jeu
   fournit les documents à importer ; l'écran, non.
5. **Un mot de passe en clair subsiste dans un fichier versionné — pas le mien.**
   `demarrer.sh` affiche `verif@exemple.test / MotDePasseVerif!2026` (compte de la
   base de vérification de la phase 3). Ce n'est pas le compte de démonstration de
   ce lot (le mien est `demo@exemple.invalid`, mot de passe saisi au chargement et
   haché en Argon2id), mais c'est une entorse à la règle « aucun mot de passe en
   clair dans un fichier versionné ». **À corriger par le lot propriétaire de
   `demarrer.sh`** — je ne l'ai pas touché.
6. **Le premier passage de vérification a utilisé le fournisseur configuré dans le
   `.env`** (appel de modèle réel), parce que le fournisseur par défaut du dépôt est
   celui du `.env`. Les passages suivants ont forcé le fournisseur `factice` pour
   rester hors ligne. Conclusion pratique : l'analyse fonctionne dans les deux
   configurations, avec les nuances du paragraphe « Fournisseur de lecture ».
7. **Le mémoire n'est pas semé**, conformément au plan : la valeur du produit se
   démontre en le générant (étapes 4 et 5), pas en le lisant dans le jeu.

---

## Ce qui a été réellement exécuté pour écrire ce document

- `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0002_jeu_demo_phase4.sql`
  → `BEGIN … INSERT … COMMIT`, 13 tableaux de contrôle, **0 erreur**. Relancé une
  seconde fois : **aucun doublon** (comptages identiques).
- `python scripts/jeu-de-test/completer_demo_phase4.py` → 1 `entreprise_version`,
  2 `exercice_comptable`, 1 `representant_legal`, montants des 4 références, 1
  empreinte Argon2id, 6 pièces chiffrées écrites ; **SIRET relu et déchiffré** :
  `00000000000000`. Relancé : **aucun doublon**.
- `ServiceAuthentification.authentifier("demo@exemple.invalid", <mot de passe>)` →
  identité trouvée (`client_id d0000000-…-0001`) ; mot de passe erroné → refus.
- Lecture des **9 familles** via `ServiceBibliotheque.consulter_famille` →
  tout est déchiffré sans erreur ; statut de la fiche calculé : `socle_complet` ;
  validités observées : assurance 1×`valide`… certification `['expire','valide']`
  (alerte visible sans réglage).
- `analyse_dce.deposer_et_analyser(..., fournisseur=FournisseurFactice())` sur le
  DCE fictif → `statut = analysee`, **15 éléments** (8 pièces, 6 critères, 1 date
  limite `2026-12-12`), **0 catégorie non trouvée**.
- Validation humaine nommée des 15 éléments, puis
  `checklist.executer_checklist` → **4 `presente`, 3 `a_verifier`, 1 `manquante`**
  (« Liste des moyens matériels affectés au marché »).
- Nettoyage final : la consultation de vérification, ses éléments, son document et
  son fichier chiffré ont été retirés. **Le jeu de démonstration repart sans
  consultation** (contrôle : `consultation = 0`), pour que le critère 3 soit
  réellement déroulé par la personne qui démontre.
- **Passage par la vraie couche web** (serveur `uvicorn` sur `127.0.0.1:8123`, jeu
  chargé) : `GET /connexion` → `200` ; `POST /connexion` avec
  `demo@exemple.invalid` → **`303`** (session ouverte, redirection) ;
  `GET /bibliotheque` → `200` et l'écran affiche bien `Océan Étanchéité` et les
  neuf familles ; `GET /bibliotheque/assurances` → `200` avec
  `ASSURANCES-FICTIVES OCÉANE` et les deux échéances (2026-10-15, 2027-01-31) ;
  `GET /bibliotheque/identite`, `/bibliotheque/references_chantiers` et
  `/consultations` → `200`. Le serveur a été arrêté après le contrôle.
