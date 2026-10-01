-- 0006_import_guide.sql — L3 (phase 4) : import guidé de documents existants
--
-- Implémentation littérale de `docs/PLAN-PHASE-4.md` § 2.A (décision **gelée**) :
-- deux tables, `import_document` et `import_proposition`, réversibles.
--
-- Conventions : celles de `0001_init_socle.sql` et `0002_bibliotheque.sql`.
-- Cloisonnement : `client_id` non nul sur chaque table, indexé (`annexe A § A1`).
--
-- Contraintes copiées du modèle de phase 3 (`0003_analyse_dce.sql`,
-- `extraction_element`) : aucune proposition sans source — `source_emplacement` et
-- `source_extrait` sont NON nuls et non vides —, et une décision humaine est
-- horodatée et **nommée** (`date_decision` + `decide_par`) dès qu'elle quitte l'état
-- `propose`. Aucune proposition sans source ne peut donc exister, même « à vérifier ».
--
-- Aucune donnée réelle, aucune clé, aucun `DROP` d'une table existante.

-- +migrate up

-- ---------------------------------------------------------------------------
-- Import d'un document existant vers une famille de la bibliothèque.
-- Le fichier lui-même vit dans `document` (nature `piece_bibliotheque`, chiffré
-- hors dépôt) ; cette table porte le suivi de l'import guidé.
-- ---------------------------------------------------------------------------
CREATE TABLE import_document (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    document_id        uuid         NOT NULL REFERENCES document (id),
    -- Famille de `app.domain.familles` visée par l'import (ex. `assurances`).
    famille_cible      varchar(100) NOT NULL,
    statut             varchar(100) NOT NULL DEFAULT 'en_attente',
    moteur_fournisseur varchar(255),   -- ex. `factice`
    moteur_modele      varchar(255),
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    date_modification  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT import_document_statut CHECK (
        statut IN ('en_attente', 'traite', 'abandonne')
    ),
    CONSTRAINT import_document_famille_non_vide CHECK (length(btrim(famille_cible)) > 0),
    -- Un document n'est l'objet que d'un seul import (le fichier est immuable).
    CONSTRAINT import_document_document_unique UNIQUE (document_id)
);
CREATE INDEX idx_import_document_client ON import_document (client_id);
CREATE INDEX idx_import_document_document ON import_document (document_id);
CREATE INDEX idx_import_document_statut ON import_document (client_id, statut);

-- ---------------------------------------------------------------------------
-- Proposition d'élément de bibliothèque, en attente de décision humaine.
-- Rien n'entre dans la bibliothèque sans passer par une ligne de cette table et
-- une décision nommée (`propose` -> `acceptee` / `refusee`).
-- ---------------------------------------------------------------------------
CREATE TABLE import_proposition (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid         NOT NULL REFERENCES client (id),
    import_document_id uuid         NOT NULL REFERENCES import_document (id),
    -- Famille visée et entité logique de `app.domain.familles` (ex. `assurance`).
    famille            varchar(100) NOT NULL,
    entite_cible       varchar(100) NOT NULL,
    champs_proposes    jsonb        NOT NULL,
    source_emplacement varchar(255) NOT NULL,   -- page / section, jamais vide
    source_extrait     text         NOT NULL,   -- extrait littéral du document lu
    statut             varchar(100) NOT NULL DEFAULT 'propose',
    date_decision      timestamptz,             -- posée par la base au moment du geste
    decide_par         varchar(255),            -- nom de l'humain qui a décidé
    -- Identifiant de l'élément écrit dans une table de contenu (aucune FK : la table
    -- cible dépend de l'entité). Renseigné uniquement à l'acceptation.
    element_cree_id    uuid,
    date_creation      timestamptz  NOT NULL DEFAULT now(),
    date_modification  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT import_proposition_statut CHECK (
        statut IN ('propose', 'acceptee', 'refusee')
    ),
    CONSTRAINT import_proposition_champs_objet CHECK (jsonb_typeof(champs_proposes) = 'object'),
    CONSTRAINT import_proposition_source_emplacement_non_vide CHECK (
        length(btrim(source_emplacement)) > 0
    ),
    CONSTRAINT import_proposition_source_extrait_non_vide CHECK (
        length(btrim(source_extrait)) > 0
    ),
    -- Toute sortie de l'état `propose` exige une décision humaine nommée et horodatée.
    CONSTRAINT import_proposition_decision_requise CHECK (
        statut = 'propose'
        OR (date_decision IS NOT NULL
            AND decide_par IS NOT NULL
            AND length(btrim(decide_par)) > 0)
    ),
    -- Une proposition acceptée a nécessairement écrit un élément de bibliothèque.
    CONSTRAINT import_proposition_acceptee_element CHECK (
        statut <> 'acceptee' OR element_cree_id IS NOT NULL
    )
);
CREATE INDEX idx_import_proposition_client ON import_proposition (client_id);
CREATE INDEX idx_import_proposition_document ON import_proposition (import_document_id);
CREATE INDEX idx_import_proposition_statut ON import_proposition (client_id, statut);

-- +migrate down

-- Réversibilité : les deux tables créées ici sont retirées (les propositions
-- d'abord — elles référencent `import_document`).
--
-- Les lignes de `document` créées par un import **ne sont pas supprimées** : un
-- élément de bibliothèque accepté les référence (`source_document_id`), et les
-- effacer casserait cette référence tant que les tables de contenu existent. Elles
-- restent donc des documents de bibliothèque ordinaires, comme les fichiers restent
-- sur disque (même choix que `0003_analyse_dce.sql` pour ses fichiers).
DROP TABLE IF EXISTS import_proposition;
DROP TABLE IF EXISTS import_document;
