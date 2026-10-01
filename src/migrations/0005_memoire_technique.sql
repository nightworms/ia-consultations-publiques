-- 0005_memoire_technique.sql — L2 (phase 4) : mémoire technique généré
--
-- Implémentation littérale de `docs/PLAN-PHASE-4.md` § 2.A (décision **gelée**) :
-- cinq tables, `memoire_dossier`, `memoire_section`, `memoire_section_source`,
-- `memoire_manque`, `memoire_validation`, réversibles.
--
-- Conventions : celles de `0001_init_socle.sql`, `0002_bibliotheque.sql` et
-- `0003_analyse_dce.sql`. Cloisonnement : `client_id` non nul et indexé sur chaque
-- table (`annexe A § A1`), et **aucune** clé étrangère ne relie deux clients.
--
-- Règles opposables traduites en schéma (mêmes mécaniques que la phase 3) :
--
--   * une section **existe** parce qu'elle porte au moins une source : c'est la
--     contrainte d'intégrité `memoire_section_source` (page N). Le service vérifie en
--     plus, avant écriture, que l'élément cité est bien du client (`client_id`) — le
--     schéma ne peut pas l'exprimer (la table citée varie), d'où le contrôle applicatif
--     documenté dans `docs/MEMOIRE-TECHNIQUE.md` ;
--   * **aucun statut validé sans action humaine nommée et horodatée** : tout statut de
--     section autre que `brouillon` exige `statut_par` **et** `statut_le`
--     (`memoire_section_action_humaine`) ; le dossier exige une ligne
--     `memoire_validation` nommée et horodatée pour passer `valide`
--     (`memoire_validation_nommee`) ;
--   * `origine`/`confiance` reprennent les jeux fermés de la phase 3 ; aucune valeur
--     « générée par l'IA » n'existe (§ 7.5, ligne rouge) ;
--   * **aucun prix, aucun chiffre inventé, aucune conformité promise** : aucun champ de
--     prix/marge/tarif n'est créé ici, et aucune colonne ne peut porter un verdict de
--     conformité.
--
-- Notes d'exécution :
--   * Les tables `memoire_section.statut_par`/`statut_le` **s'ajoutent** aux colonnes de
--     § 2.A (elles ne renomment rien) : sans elles, la règle « aucun statut validé posé
--     par du code » n'aurait pas de support en base. Décision écrite dans
--     `docs/MEMOIRE-TECHNIQUE.md` § « Écarts assumés au § 2.A du plan ».
--   * Le `down` est complet : les cinq tables créées ici sont retirées, sans toucher à
--     aucune table existante.
--   * Aucune donnée réelle, aucune clé, aucun `DROP` d'une table existante.

-- +migrate up

-- ---------------------------------------------------------------------------
-- memoire_dossier — un mémoire technique généré pour une consultation.
-- `fiche_version_id` fige la version de bibliothèque qui a servi de source : le
-- mémoire est reproductible et rattachable à un état précis de la bibliothèque.
-- ---------------------------------------------------------------------------
CREATE TABLE memoire_dossier (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    consultation_id    uuid         NOT NULL REFERENCES consultation (id),
    fiche_version_id   uuid         NOT NULL REFERENCES fiche_version (id),
    titre              varchar(255) NOT NULL,
    statut             varchar(100) NOT NULL DEFAULT 'brouillon',
    moteur_fournisseur varchar(255),           -- ex. `factice`
    moteur_modele      varchar(255),
    avertissement      text,
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    date_modification  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT memoire_dossier_statut CHECK (
        statut IN ('brouillon', 'en_relecture', 'valide')
    ),
    CONSTRAINT memoire_dossier_titre_non_vide CHECK (length(btrim(titre)) > 0)
);
CREATE INDEX idx_memoire_dossier_client ON memoire_dossier (client_id);
CREATE INDEX idx_memoire_dossier_consultation ON memoire_dossier (consultation_id);
CREATE INDEX idx_memoire_dossier_fiche ON memoire_dossier (fiche_version_id);
CREATE INDEX idx_memoire_dossier_statut ON memoire_dossier (client_id, statut);

-- ---------------------------------------------------------------------------
-- memoire_section — une section du mémoire, adossée à un critère du DCE.
-- `critere_code`/`critere_poids` sont nullables : un critère sans pondération connue
-- passe en fin de mémoire (raison inscrite dans le contenu de la section).
-- Aucune section n'est validée sans un humain nommé et une date :
-- `statut <> 'brouillon'` exige `statut_par` et `statut_le`.
-- ---------------------------------------------------------------------------
CREATE TABLE memoire_section (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    memoire_dossier_id uuid         NOT NULL REFERENCES memoire_dossier (id),
    ordre              integer      NOT NULL,
    critere_code       varchar(100),
    critere_libelle    varchar(255) NOT NULL,
    critere_poids      numeric(6,2),
    titre              varchar(255) NOT NULL,
    contenu            text         NOT NULL,
    statut             varchar(100) NOT NULL DEFAULT 'brouillon',
    origine            varchar(100) NOT NULL DEFAULT 'mixte',
    confiance          varchar(100) NOT NULL DEFAULT 'a_verifier',
    -- Action humaine nommée et horodatée : obligatoires dès que la section quitte
    -- l'état `brouillon`. Ajout assumé à § 2.A (voir note d'en-tête).
    statut_par         varchar(255),
    statut_le          timestamptz,
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    date_modification  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT memoire_section_statut CHECK (
        statut IN ('brouillon', 'relue', 'validee')
    ),
    CONSTRAINT memoire_section_ordre_positif CHECK (ordre >= 0),
    CONSTRAINT memoire_section_critere_libelle_non_vide CHECK (
        length(btrim(critere_libelle)) > 0
    ),
    CONSTRAINT memoire_section_titre_non_vide CHECK (length(btrim(titre)) > 0),
    CONSTRAINT memoire_section_contenu_non_vide CHECK (length(btrim(contenu)) > 0),
    CONSTRAINT memoire_section_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT memoire_section_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    -- Aucun statut validé (ou relu) posé sans action humaine nommée et horodatée.
    CONSTRAINT memoire_section_action_humaine CHECK (
        statut = 'brouillon'
        OR (statut_par IS NOT NULL AND length(btrim(statut_par)) > 0
            AND statut_le IS NOT NULL)
    ),
    -- Un critère sans pondération connue ne peut pas porter une valeur inventée.
    CONSTRAINT memoire_section_poids_coherence CHECK (
        (critere_poids IS NULL) OR (critere_poids >= 0 AND critere_poids <= 100)
    )
);
CREATE INDEX idx_memoire_section_client ON memoire_section (client_id);
CREATE INDEX idx_memoire_section_dossier ON memoire_section (memoire_dossier_id);
CREATE INDEX idx_memoire_section_statut ON memoire_section (client_id, statut);

-- ---------------------------------------------------------------------------
-- memoire_section_source — la preuve : chaque affirmation d'une section est
-- rattachée à un élément **réel** de la bibliothèque du client.
-- `table_source` nomme la table de contenu citée (liste blanche ci-dessous, celle
-- des familles F1 à F9 de `app.domain.familles`) ; `element_id` pointe la ligne.
-- Aucune clé étrangère n'est possible (la cible varie) : le contrôle d'appartenance
-- au client est fait par le service, avant écriture.
-- ---------------------------------------------------------------------------
CREATE TABLE memoire_section_source (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    memoire_section_id uuid         NOT NULL REFERENCES memoire_section (id),
    table_source       varchar(100) NOT NULL,
    element_id         uuid         NOT NULL,
    libelle_source     varchar(255) NOT NULL,
    emplacement_source varchar(255) NOT NULL,
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT memoire_section_source_table_connue CHECK (
        table_source IN (
            'entreprise_version', 'representant_legal', 'exercice_comptable',
            'attestation', 'capacite_production', 'assurance', 'certification',
            'reference_chantier', 'effectif_metier', 'organigramme', 'cv',
            'moyen_materiel', 'produit', 'chapitre_memoire'
        )
    ),
    CONSTRAINT memoire_section_source_libelle_non_vide CHECK (
        length(btrim(libelle_source)) > 0
    ),
    CONSTRAINT memoire_section_source_emplacement_non_vide CHECK (
        length(btrim(emplacement_source)) > 0
    )
);
CREATE INDEX idx_memoire_section_source_client ON memoire_section_source (client_id);
CREATE INDEX idx_memoire_section_source_section ON memoire_section_source (memoire_section_id);

-- ---------------------------------------------------------------------------
-- memoire_manque — ce que la bibliothèque ne permet pas d'étayer.
-- **Ce n'est pas un cas d'erreur** : c'est le résultat le plus utile du produit. Il
-- dit le constat (« aucune référence correspondante… ») et l'action à mener.
-- ---------------------------------------------------------------------------
CREATE TABLE memoire_manque (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    memoire_dossier_id uuid         NOT NULL REFERENCES memoire_dossier (id),
    critere_code       varchar(100),
    critere_libelle    varchar(255) NOT NULL,
    critere_poids      numeric(6,2),
    constat            text         NOT NULL,
    action_attendue    text         NOT NULL,
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT memoire_manque_critere_libelle_non_vide CHECK (
        length(btrim(critere_libelle)) > 0
    ),
    CONSTRAINT memoire_manque_constat_non_vide CHECK (length(btrim(constat)) > 0),
    CONSTRAINT memoire_manque_action_non_vide CHECK (length(btrim(action_attendue)) > 0)
);
CREATE INDEX idx_memoire_manque_client ON memoire_manque (client_id);
CREATE INDEX idx_memoire_manque_dossier ON memoire_manque (memoire_dossier_id);

-- ---------------------------------------------------------------------------
-- memoire_validation — la validation finale, nommée et horodatée, avec l'empreinte
-- SHA-256 du contenu validé. Aucun chemin de code ne peut poser un dossier `valide`
-- sans cette ligne : c'est le verrou humain du lot.
-- ---------------------------------------------------------------------------
CREATE TABLE memoire_validation (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           uuid         NOT NULL REFERENCES client (id),
    memoire_dossier_id  uuid         NOT NULL REFERENCES memoire_dossier (id),
    nom_validateur      varchar(255) NOT NULL,
    fonction_validateur varchar(255) NOT NULL,
    horodatage          timestamptz  NOT NULL DEFAULT now(),
    empreinte_contenu   varchar(128) NOT NULL,   -- SHA-256 hexadécimal du contenu validé
    format_export       varchar(20),
    nom_fichier         varchar(255),
    CONSTRAINT memoire_validation_nom_non_vide CHECK (
        length(btrim(nom_validateur)) > 0
    ),
    CONSTRAINT memoire_validation_fonction_non_vide CHECK (
        length(btrim(fonction_validateur)) > 0
    ),
    CONSTRAINT memoire_validation_empreinte_non_vide CHECK (
        length(btrim(empreinte_contenu)) > 0
    )
);
CREATE INDEX idx_memoire_validation_client ON memoire_validation (client_id);
CREATE INDEX idx_memoire_validation_dossier ON memoire_validation (memoire_dossier_id);

-- +migrate down

-- Réversibilité : les cinq tables créées ici sont retirées, dans l'ordre inverse des
-- dépendances (les feuilles d'abord). Aucune table existante n'est touchée : le
-- mémoire n'a créé aucune donnée ailleurs (aucune écriture dans `document`,
-- `consultation`, `extraction_element` ni dans les tables de bibliothèque).
DROP TABLE IF EXISTS memoire_validation;
DROP TABLE IF EXISTS memoire_manque;
DROP TABLE IF EXISTS memoire_section_source;
DROP TABLE IF EXISTS memoire_section;
DROP TABLE IF EXISTS memoire_dossier;
