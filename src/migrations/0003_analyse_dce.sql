-- 0003_analyse_dce.sql — L3 : analyse d'un DCE (brique B)
-- Implémentation littérale de l'annexe B du plan de phase 3 (docs/PLAN-PHASE-3.md),
-- blocs B1 (extension de `document`), B2 (`consultation`), B3 (`extraction_element`)
-- et B6 (jeux de référence associés).
--
-- Conventions : celles de 0001_init_socle.sql (annexe A § A2).
-- Cloisonnement : `client_id` non nul sur toute entité de contenu (annexe A § A1).
--
-- Aucune donnée réelle : les seules lignes insérées ici sont les VALEURS des jeux de
-- référence décidées en annexe B § B6 — des codes de nomenclature, jamais un contenu
-- de client.
--
-- Invariant I7 (annexe B § B1) : un document de nature `piece_bibliotheque` porte
-- obligatoirement `entreprise_id` et `fiche_version_id` ; un document de nature `dce`
-- porte obligatoirement `consultation_id`.

-- +migrate up

-- ---------------------------------------------------------------------------
-- B2. consultation — le DCE déposé et analysé.
-- Créée AVANT l'extension de `document` : c'est la cible de sa clé étrangère.
-- ---------------------------------------------------------------------------
CREATE TABLE consultation (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    entreprise_id          uuid         NOT NULL REFERENCES entreprise (id),
    dossier_id             uuid         REFERENCES dossier (id),
    libelle                varchar(255) NOT NULL,
    reference_consultation varchar(255),   -- saisie par l'humain ; l'outil ne va rien chercher
    maitre_ouvrage_declare varchar(255),   -- saisi par l'humain, jamais déduit
    statut                 varchar(100) NOT NULL DEFAULT 'deposee',   -- jeu consultation.statut
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    date_modification      timestamptz  NOT NULL DEFAULT now(),
    sensibilite            varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement  varchar(100) NOT NULL DEFAULT 'actif'
);
CREATE INDEX idx_consultation_client ON consultation (client_id);
CREATE INDEX idx_consultation_entreprise ON consultation (entreprise_id);

-- ---------------------------------------------------------------------------
-- B3. extraction_element — un élément proposé puis vérifié par un humain.
-- Aucune valeur sans source : `source_document_id` et `source_emplacement` sont
-- NON nuls. C'est la traduction technique de la ligne rouge (annexe B § B7).
-- ---------------------------------------------------------------------------
CREATE TABLE extraction_element (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id            uuid         NOT NULL REFERENCES client (id),
    consultation_id      uuid         NOT NULL REFERENCES consultation (id),
    categorie            varchar(100) NOT NULL,   -- jeu consultation.categorie_element
    libelle              text         NOT NULL,   -- l'élément tel qu'extrait
    valeur               text,                    -- pondération, date ISO 8601, précision
    source_document_id   uuid         NOT NULL REFERENCES document (id),
    source_emplacement   varchar(255) NOT NULL,   -- page ou section
    source_extrait       text,                    -- extrait littéral du document
    confiance            varchar(100) NOT NULL DEFAULT 'a_verifier', -- jeu tracabilite.confiance
    statut_verification  varchar(100) NOT NULL DEFAULT 'propose',    -- jeu consultation.statut_verification
    verificateur_nom     varchar(255),            -- obligatoire si valide / corrige (CHECK ci-dessous)
    date_verification    timestamptz,
    date_extraction      timestamptz  NOT NULL DEFAULT now(),
    moteur_fournisseur   varchar(255),            -- ex. `factice`, `mistral`, `ovh`
    moteur_modele        varchar(255),
    date_creation        timestamptz  NOT NULL DEFAULT now(),
    date_modification    timestamptz  NOT NULL DEFAULT now(),
    sensibilite          varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT extraction_element_source_emplacement_non_vide
        CHECK (length(btrim(source_emplacement)) > 0),
    CONSTRAINT extraction_element_verificateur_requis CHECK (
        statut_verification NOT IN ('valide', 'corrige')
        OR (verificateur_nom IS NOT NULL AND length(btrim(verificateur_nom)) > 0)
    )
);
CREATE INDEX idx_extraction_element_client ON extraction_element (client_id);
CREATE INDEX idx_extraction_element_consultation ON extraction_element (consultation_id);
CREATE INDEX idx_extraction_element_document ON extraction_element (source_document_id);
-- La brique C ne lit que les éléments validés : l'index sert ce filtre précis.
CREATE INDEX idx_extraction_element_statut
    ON extraction_element (consultation_id, statut_verification);

-- ---------------------------------------------------------------------------
-- B1. document — extension : nature du document, rattachement à un DCE.
-- ---------------------------------------------------------------------------
ALTER TABLE document
    ADD COLUMN nature varchar(100) NOT NULL DEFAULT 'piece_bibliotheque';  -- jeu document.nature
ALTER TABLE document
    ADD COLUMN consultation_id uuid REFERENCES consultation (id);

-- Un document de bibliothèque n'a pas de consultation ; un DCE n'a pas de version de
-- fiche (il appartient à l'acheteur, pas à la bibliothèque de l'entreprise). Le DCE
-- conserve `entreprise_id` : c'est l'espace de travail qui l'a déposé.
ALTER TABLE document ALTER COLUMN entreprise_id DROP NOT NULL;
ALTER TABLE document ALTER COLUMN fiche_version_id DROP NOT NULL;

-- Invariant I7, exprimé comme contrainte de schéma.
ALTER TABLE document ADD CONSTRAINT document_nature_coherence CHECK (
    (nature = 'piece_bibliotheque'
        AND entreprise_id IS NOT NULL AND fiche_version_id IS NOT NULL)
    OR (nature = 'dce' AND consultation_id IS NOT NULL)
);
CREATE INDEX idx_document_consultation ON document (consultation_id);

-- ---------------------------------------------------------------------------
-- B6. Jeux de référence associés à la brique B.
-- Le contenu de ces jeux est décidé en annexe B § B6 ; aucune valeur n'est inventée
-- ici (source = la décision gelée). Le jeu `checklist.statut_ligne` appartient à L4.
-- ---------------------------------------------------------------------------
INSERT INTO jeu_reference (namespace, libelle, description, domaine, portee, source, statut)
VALUES
    ('document.nature',
     'Nature du document',
     'Sépare une pièce de la bibliothèque d''entreprise d''un DCE déposé par l''utilisateur.',
     'document', 'global',
     'docs/PLAN-PHASE-3.md annexe B § B1 (décision gelée)', 'actif'),
    ('consultation.statut',
     'Statut d''une consultation',
     'États d''avancement d''un DCE déposé.',
     'consultation', 'global',
     'docs/PLAN-PHASE-3.md annexe B § B2 (décision gelée)', 'actif'),
    ('consultation.categorie_element',
     'Catégorie d''un élément extrait',
     'Les trois natures d''éléments que la brique B extrait : pièce exigée, critère, date limite.',
     'consultation', 'global',
     'docs/PLAN-PHASE-3.md annexe B § B3 (décision gelée)', 'actif'),
    ('consultation.statut_verification',
     'Statut de vérification d''un élément extrait',
     'Un élément proposé par la machine n''est utilisable par la checklist qu''après validation humaine.',
     'consultation', 'global',
     'docs/PLAN-PHASE-3.md annexe B § B3 (décision gelée)', 'actif');

INSERT INTO valeur_reference (namespace, code, libelle, ordre, domaine, source, statut)
VALUES
    -- document.nature
    ('document.nature', 'piece_bibliotheque', 'Pièce de la bibliothèque d''entreprise', 10, 'document',
     'docs/PLAN-PHASE-3.md annexe B § B1', 'actif'),
    ('document.nature', 'dce', 'Dossier de consultation déposé (DCE)', 20, 'document',
     'docs/PLAN-PHASE-3.md annexe B § B1', 'actif'),
    -- consultation.statut
    ('consultation.statut', 'deposee', 'Déposée', 10, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B2', 'actif'),
    ('consultation.statut', 'analysee', 'Analysée', 20, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B2', 'actif'),
    ('consultation.statut', 'verifiee', 'Vérifiée par un humain', 30, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B2', 'actif'),
    ('consultation.statut', 'abandonnee', 'Abandonnée', 40, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B2', 'actif'),
    -- consultation.categorie_element
    ('consultation.categorie_element', 'piece_exigee', 'Pièce exigée', 10, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    ('consultation.categorie_element', 'critere', 'Critère d''attribution', 20, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    ('consultation.categorie_element', 'date_limite', 'Date limite de remise', 30, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    -- consultation.statut_verification
    ('consultation.statut_verification', 'propose', 'Proposé — non vérifié', 10, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    ('consultation.statut_verification', 'valide', 'Validé par un humain nommé', 20, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    ('consultation.statut_verification', 'corrige', 'Corrigé par un humain nommé', 30, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif'),
    ('consultation.statut_verification', 'supprime', 'Supprimé par un humain nommé', 40, 'consultation',
     'docs/PLAN-PHASE-3.md annexe B § B3', 'actif');

-- +migrate down

-- Ordre inverse strict.
-- (a) Les éléments extraits disparaissent : ils référencent `document` et `consultation`.
DROP TABLE IF EXISTS extraction_element;

-- (b) Un document de nature `dce` ne peut plus exister une fois `consultation_id` retiré
--     (invariant I7) : les lignes correspondantes sont supprimées avant la remise en
--     NOT NULL, sinon l'annulation serait impossible. Opération explicite et bornée aux
--     lignes créées par cette migration. Les fichiers restent sur disque, hors dépôt.
DELETE FROM document WHERE nature = 'dce';

DROP INDEX IF EXISTS idx_document_consultation;
ALTER TABLE document DROP CONSTRAINT IF EXISTS document_nature_coherence;
ALTER TABLE document DROP COLUMN IF EXISTS consultation_id;
ALTER TABLE document DROP COLUMN IF EXISTS nature;
ALTER TABLE document ALTER COLUMN fiche_version_id SET NOT NULL;
ALTER TABLE document ALTER COLUMN entreprise_id SET NOT NULL;

DROP TABLE IF EXISTS consultation;

-- (c) Jeux de référence ajoutés par cette migration.
DELETE FROM valeur_reference
 WHERE namespace IN ('document.nature', 'consultation.statut',
                     'consultation.categorie_element', 'consultation.statut_verification');
DELETE FROM jeu_reference
 WHERE namespace IN ('document.nature', 'consultation.statut',
                     'consultation.categorie_element', 'consultation.statut_verification');
