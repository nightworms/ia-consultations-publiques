-- 0004_checklist.sql — L4 : checklist de conformité (brique C)
-- Implémentation littérale de l'annexe B du plan de phase 3 (docs/PLAN-PHASE-3.md),
-- blocs B4 (`checklist_execution`), B5 (`checklist_ligne`) et B6 (jeu de référence
-- `checklist.statut_ligne`).
--
-- Conventions : celles de 0001_init_socle.sql (annexe A § A2).
-- Cloisonnement : `client_id` non nul sur toute entité de contenu (annexe A § A1).
--
-- Ligne rouge : aucune sortie de cette brique ne dit « conforme ». La checklist est
-- un **outil d'aide à la relecture** ; le schéma ne porte ni garantie, ni prix, ni
-- seuil légal. Aucune valeur n'est inventée pour boucher un manque : un manque est
-- une ligne `manquante` sans document.
--
-- Invariant I8 (annexe B § B5) : une ligne `presente` référence **obligatoirement**
-- un `document_id` **du même client** ; une ligne `manquante` n'en référence aucun.
-- Une correspondance incertaine est `a_verifier`, jamais `presente`.
--   * la cardinalité (presente ⇒ document non nul ; manquante ⇒ document nul) est
--     portée par la contrainte de schéma `checklist_ligne_i8` ;
--   * l'appartenance du document au **même client** est portée par une clé étrangère
--     composite `(document_id, client_id)` : le référencement croisé entre clients
--     est donc refusé par la base, pas seulement par le code.
--
-- Aucune donnée réelle : la seule ligne insérée ici est un code de nomenclature
-- décidé en annexe B § B6.

-- +migrate up

-- ---------------------------------------------------------------------------
-- B4. checklist_execution — une exécution de la checklist.
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_execution (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    consultation_id       uuid         NOT NULL REFERENCES consultation (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),  -- quelle fiche a servi
    date_execution        timestamptz  NOT NULL DEFAULT now(),
    execute_par           varchar(255) NOT NULL,   -- nom saisi par l'humain
    nb_exigences          integer      NOT NULL,
    nb_presentes          integer      NOT NULL,
    nb_manquantes         integer      NOT NULL,
    nb_a_verifier         integer      NOT NULL,
    extraction_partielle  smallint     NOT NULL DEFAULT 0,  -- vrai si des éléments lus sont restés non validés
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT checklist_execution_extraction_partielle_bool
        CHECK (extraction_partielle IN (0, 1)),
    CONSTRAINT checklist_execution_comptes_positifs CHECK (
        nb_exigences >= 0 AND nb_presentes >= 0 AND nb_manquantes >= 0 AND nb_a_verifier >= 0
    )
);
CREATE INDEX idx_checklist_execution_client ON checklist_execution (client_id);
CREATE INDEX idx_checklist_execution_consultation ON checklist_execution (consultation_id);
-- Clé d'appartenance composite : sert la clé étrangère de `checklist_ligne`.
ALTER TABLE checklist_execution ADD CONSTRAINT checklist_execution_id_client_unique
    UNIQUE (id, client_id);

-- ---------------------------------------------------------------------------
-- B5. checklist_ligne — une ligne de résultat.
-- ---------------------------------------------------------------------------
-- Clés d'appartenance composite des tables visées par les clés étrangères
-- ci-dessous, créées AVANT la table qui les référence. `document` a été créée par
-- 0001/0003, `extraction_element` par 0003 : on ne modifie pas ces fichiers, on
-- ajoute seulement la contrainte d'unicité nécessaire, et l'annulation la retire.
ALTER TABLE document ADD CONSTRAINT document_id_client_unique UNIQUE (id, client_id);
ALTER TABLE extraction_element ADD CONSTRAINT extraction_element_id_client_unique
    UNIQUE (id, client_id);

CREATE TABLE checklist_ligne (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    checklist_execution_id uuid         NOT NULL,
    extraction_element_id  uuid         NOT NULL,   -- l'exigence comparée
    libelle_piece          varchar(255) NOT NULL,   -- l'exigence, telle que validée
    statut                 varchar(100) NOT NULL,   -- jeu checklist.statut_ligne
    justification          text         NOT NULL,   -- la pièce retenue, ou la raison du manque
    document_id            uuid,                    -- renseigné si et seulement si statut = presente
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    date_modification      timestamptz  NOT NULL DEFAULT now(),
    sensibilite            varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement  varchar(100) NOT NULL DEFAULT 'actif',

    -- Invariant I8 : cardinalité du document, et jeu de statuts fermé.
    CONSTRAINT checklist_ligne_i8 CHECK (
        statut IN ('presente', 'manquante', 'a_verifier')
        AND (statut <> 'presente' OR document_id IS NOT NULL)
        AND (statut <> 'manquante' OR document_id IS NULL)
    ),

    -- Invariant I8 (suite) : le document retenu appartient au même client.
    CONSTRAINT checklist_ligne_execution_meme_client
        FOREIGN KEY (checklist_execution_id, client_id)
        REFERENCES checklist_execution (id, client_id),
    CONSTRAINT checklist_ligne_element_meme_client
        FOREIGN KEY (extraction_element_id, client_id)
        REFERENCES extraction_element (id, client_id),
    CONSTRAINT checklist_ligne_document_meme_client
        FOREIGN KEY (document_id, client_id)
        REFERENCES document (id, client_id)
);
CREATE INDEX idx_checklist_ligne_client ON checklist_ligne (client_id);
CREATE INDEX idx_checklist_ligne_execution ON checklist_ligne (checklist_execution_id);
CREATE INDEX idx_checklist_ligne_element ON checklist_ligne (extraction_element_id);

-- ---------------------------------------------------------------------------
-- B6. Jeu de référence de la brique C.
-- ---------------------------------------------------------------------------
INSERT INTO jeu_reference (namespace, libelle, description, domaine, portee, source, statut)
VALUES
    ('checklist.statut_ligne',
     'Statut d''une ligne de checklist',
     'Une ligne de checklist est présente, manquante ou à vérifier — jamais « conforme ».',
     'checklist', 'global',
     'docs/PLAN-PHASE-3.md annexe B § B5 (décision gelée)', 'actif');

INSERT INTO valeur_reference (namespace, code, libelle, ordre, domaine, source, statut)
VALUES
    ('checklist.statut_ligne', 'presente', 'Présente dans la bibliothèque', 10, 'checklist',
     'docs/PLAN-PHASE-3.md annexe B § B5', 'actif'),
    ('checklist.statut_ligne', 'manquante', 'Manquante — rien n''est fabriqué', 20, 'checklist',
     'docs/PLAN-PHASE-3.md annexe B § B5', 'actif'),
    ('checklist.statut_ligne', 'a_verifier', 'À vérifier par un humain', 30, 'checklist',
     'docs/PLAN-PHASE-3.md annexe B § B5', 'actif');

-- +migrate down

-- Ordre inverse strict.
DROP TABLE IF EXISTS checklist_ligne;
DROP TABLE IF EXISTS checklist_execution;

ALTER TABLE extraction_element DROP CONSTRAINT IF EXISTS extraction_element_id_client_unique;
ALTER TABLE document DROP CONSTRAINT IF EXISTS document_id_client_unique;

-- Jeu de référence ajouté par cette migration.
DELETE FROM valeur_reference WHERE namespace = 'checklist.statut_ligne';
DELETE FROM jeu_reference WHERE namespace = 'checklist.statut_ligne';
