-- 0002_bibliotheque.sql — L2 : bibliothèque d'entreprise (familles F1 à F9)
-- Conforme à docs/DATA-MODEL-V2.md § 5, § 6, § 7, § 10 et à l'annexe A du
-- plan de phase 3. Tables racines et transverses : voir 0001_init_socle.sql.
--
-- Conventions (annexe A § A2), identiques à 0001 :
--   identifiant technique -> uuid (v4)     texte_court -> varchar(255)
--   texte_long -> text                     horodatage  -> timestamptz
--   date -> date (ISO 8601)                booleen     -> smallint 0/1 (CHECK)
--   code_reference -> varchar(100)         empreinte   -> varchar(128)
--   montant -> numeric(18,2) + devise varchar(3) (ISO 4217) NON chiffré,
--              ou varchar(2048) chiffré + devise en clair (annexe A § A6)
--
-- DEUX RÈGLES STRUCTURANTES DE CE FICHIER
--
-- 1. Colonnes techniques communes (§ 3.2) sur TOUTE entité de contenu :
--    id, client_id, entreprise_id, fiche_version_id, date_creation,
--    date_modification, sensibilite, statut_enregistrement.
--    Plus les colonnes de synthèse de traçabilité (§ 7.4) : origine, confiance,
--    source_document_id (obligatoires, jamais de valeur sans origine).
--
-- 2. CHAMPS CHIFFRÉS (annexe A § A6, registre § 13.2). Le chiffrement est
--    APPLICATIF (AES-256-GCM, clé dérivée par client dans
--    app/securite/chiffrement.py, livré par L1). Les colonnes concernées sont donc
--    de type texte (varchar(2048)) et contiennent une charge `v1:<base64>`.
--    Aucune clé, aucun secret, aucune donnée réelle ne figurent dans ce fichier.
--
-- Aucune donnée réelle d'entreprise : ce fichier ne crée que des structures et
-- charge les JEUX DE RÉFÉRENCE FERMÉS du modèle (§ 8.6, jeux « ce document
-- (fermé) »). Les vocabulaires métier (metier.*, assurance.type, document.*,
-- entreprise.forme_juridique…) ne sont PAS inventés ici : leur contenu appartient
-- à docs/NOMENCLATURE-REFERENCE.md ou à la source administrative (D2, § 8.6).

-- +migrate up

-- ===========================================================================
-- F1 — IDENTITÉ
-- ===========================================================================

-- entreprise_version — le contenu d'identité, versionné (§ 5.4).
-- porte fiche_version_id, ce qui referme le constat C10.
CREATE TABLE entreprise_version (
    id                                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                           uuid         NOT NULL REFERENCES client (id),
    entreprise_id                       uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id                    uuid         NOT NULL REFERENCES fiche_version (id),
    raison_sociale                      varchar(255) NOT NULL,
    siren                               varchar(255) NOT NULL,
    siret_siege                         varchar(2048) NOT NULL,   -- CHIFFRÉ (A6)
    forme_juridique_code                varchar(100) NOT NULL,    -- jeu entreprise.forme_juridique (contenu : source INSEE)
    capital_social_montant              numeric(18,2),
    capital_social_devise               varchar(3),
    date_creation_entreprise            date,
    code_ape_naf                        varchar(255),
    numero_tva_intracommunautaire       varchar(2048),            -- CHIFFRÉ (A6)
    adresse_siege                       text         NOT NULL,
    adresse_etablissement_principal     text,
    telephone                           varchar(255),
    email                               varchar(255),
    site_web                            varchar(255),
    effectif                            integer,
    date_effectif                       date,
    effectif_source_code                varchar(100),             -- jeu rh.origine_effectif
    iban                                varchar(2048),            -- CHIFFRÉ (A6)
    bic                                 varchar(2048),            -- CHIFFRÉ (A6)
    piece_rib                           varchar(2048),            -- CHIFFRÉ (A6) — référence à document.id
    date_creation                       timestamptz  NOT NULL DEFAULT now(),
    date_modification                   timestamptz  NOT NULL DEFAULT now(),
    sensibilite                         varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement               varchar(100) NOT NULL DEFAULT 'actif',
    origine                             varchar(100) NOT NULL,
    confiance                           varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id                  uuid         REFERENCES document (id),
    CONSTRAINT entreprise_version_une_par_fiche UNIQUE (fiche_version_id),
    CONSTRAINT entreprise_version_capital_devise CHECK (
        (capital_social_montant IS NULL) = (capital_social_devise IS NULL)
    ),
    CONSTRAINT entreprise_version_effectif_date CHECK (
        effectif IS NULL OR date_effectif IS NOT NULL
    ),
    CONSTRAINT entreprise_version_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT entreprise_version_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT entreprise_version_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT entreprise_version_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_entreprise_version_client ON entreprise_version (client_id);
CREATE INDEX idx_entreprise_version_fiche ON entreprise_version (fiche_version_id);

-- representant_legal — données personnelles, confidentielles (§ 5.5).
CREATE TABLE representant_legal (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    nom                   varchar(2048) NOT NULL,   -- CHIFFRÉ (A6) — donnée personnelle
    prenom                varchar(2048) NOT NULL,   -- CHIFFRÉ (A6) — donnée personnelle
    fonction              varchar(255) NOT NULL,
    qualite_engagement    varchar(255),             -- libellé repris du document, jamais interprété
    date_nomination       varchar(2048),            -- CHIFFRÉ (A6) — date ISO en clair chiffrée
    date_cessation        date,
    statut                varchar(100) NOT NULL DEFAULT 'en_exercice',  -- jeu rh.statut_mandat
    piece                 varchar(2048),            -- CHIFFRÉ (A6) — référence à document.id
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'confidentiel',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT representant_legal_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT representant_legal_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT representant_legal_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT representant_legal_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_representant_legal_client ON representant_legal (client_id);
CREATE INDEX idx_representant_legal_fiche ON representant_legal (fiche_version_id);

-- ===========================================================================
-- F2 — CAPACITÉS FINANCIÈRES
-- ===========================================================================

-- exercice_comptable — un par année (§ 10 F2). Montants CHIFFRÉS (A6).
CREATE TABLE exercice_comptable (
    id                         uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                  uuid         NOT NULL REFERENCES client (id),
    entreprise_id              uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id           uuid         NOT NULL REFERENCES fiche_version (id),
    annee_exercice             integer      NOT NULL,
    date_cloture               date,
    chiffre_affaires_montant   varchar(2048) NOT NULL,   -- CHIFFRÉ (A6)
    chiffre_affaires_devise    varchar(3)   NOT NULL,
    resultat_net_montant       varchar(2048),            -- CHIFFRÉ (A6)
    resultat_net_devise        varchar(3),
    capitaux_propres_montant   varchar(2048),            -- CHIFFRÉ (A6)
    capitaux_propres_devise    varchar(3),
    total_bilan_montant        varchar(2048),            -- CHIFFRÉ (A6)
    total_bilan_devise         varchar(3),
    effectif_moyen             integer,
    piece                      varchar(2048),            -- CHIFFRÉ (A6) — référence à document.id
    date_creation              timestamptz  NOT NULL DEFAULT now(),
    date_modification          timestamptz  NOT NULL DEFAULT now(),
    sensibilite                varchar(100) NOT NULL DEFAULT 'confidentiel',
    statut_enregistrement      varchar(100) NOT NULL DEFAULT 'actif',
    origine                    varchar(100) NOT NULL,
    confiance                  varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id         uuid         REFERENCES document (id),
    CONSTRAINT exercice_comptable_une_par_annee UNIQUE (fiche_version_id, annee_exercice),
    CONSTRAINT exercice_comptable_resultat_devise CHECK (
        (resultat_net_montant IS NULL) = (resultat_net_devise IS NULL)
    ),
    CONSTRAINT exercice_comptable_capitaux_devise CHECK (
        (capitaux_propres_montant IS NULL) = (capitaux_propres_devise IS NULL)
    ),
    CONSTRAINT exercice_comptable_bilan_devise CHECK (
        (total_bilan_montant IS NULL) = (total_bilan_devise IS NULL)
    ),
    CONSTRAINT exercice_comptable_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT exercice_comptable_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT exercice_comptable_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT exercice_comptable_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_exercice_comptable_client ON exercice_comptable (client_id);
CREATE INDEX idx_exercice_comptable_fiche ON exercice_comptable (fiche_version_id);

-- attestation — pièces justificatives à durée de validité (§ 10 F2).
CREATE TABLE attestation (
    id                        uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                 uuid         NOT NULL REFERENCES client (id),
    entreprise_id             uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id          uuid         NOT NULL REFERENCES fiche_version (id),
    type_attestation          varchar(100) NOT NULL,   -- jeu attestation.type (contenu : L5 / source)
    emetteur                  varchar(255) NOT NULL,
    date_emission             date         NOT NULL,
    date_validite_fin         date,                    -- lue sur le document, jamais déduite
    montant_engage_montant    varchar(2048),           -- CHIFFRÉ (A6)
    montant_engage_devise     varchar(3),
    piece                     varchar(2048) NOT NULL,  -- CHIFFRÉ (A6) — référence à document.id
    date_creation             timestamptz  NOT NULL DEFAULT now(),
    date_modification         timestamptz  NOT NULL DEFAULT now(),
    sensibilite               varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement     varchar(100) NOT NULL DEFAULT 'actif',
    origine                   varchar(100) NOT NULL,
    confiance                 varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id        uuid         REFERENCES document (id),
    CONSTRAINT attestation_montant_devise CHECK (
        (montant_engage_montant IS NULL) = (montant_engage_devise IS NULL)
    ),
    CONSTRAINT attestation_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT attestation_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT attestation_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT attestation_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_attestation_client ON attestation (client_id);
CREATE INDEX idx_attestation_fiche ON attestation (fiche_version_id);

-- capacite_production — description, unite, valeur (§ 10 F2).
CREATE TABLE capacite_production (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    description           text         NOT NULL,
    unite                 varchar(255),
    valeur                numeric(18,4),
    commentaire           text,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT capacite_production_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT capacite_production_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT capacite_production_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT capacite_production_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_capacite_production_client ON capacite_production (client_id);
CREATE INDEX idx_capacite_production_fiche ON capacite_production (fiche_version_id);

-- ===========================================================================
-- F3 — ASSURANCES
-- ===========================================================================

CREATE TABLE assurance (
    id                      uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               uuid         NOT NULL REFERENCES client (id),
    entreprise_id           uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id        uuid         NOT NULL REFERENCES fiche_version (id),
    type_assurance          varchar(100) NOT NULL,   -- jeu assurance.type (contenu : L5)
    assureur                varchar(255) NOT NULL,
    numero_contrat          varchar(255),
    montant_garantie_montant numeric(18,2),
    montant_garantie_devise varchar(3),
    franchise_montant       numeric(18,2),
    franchise_devise        varchar(3),
    date_debut              date         NOT NULL,
    date_echeance           date         NOT NULL,   -- échéance critique
    activites_couvertes     text,
    piece                   uuid         NOT NULL REFERENCES document (id),
    date_creation           timestamptz  NOT NULL DEFAULT now(),
    date_modification       timestamptz  NOT NULL DEFAULT now(),
    sensibilite             varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement   varchar(100) NOT NULL DEFAULT 'actif',
    origine                 varchar(100) NOT NULL,
    confiance               varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id      uuid         REFERENCES document (id),
    CONSTRAINT assurance_garantie_devise CHECK (
        (montant_garantie_montant IS NULL) = (montant_garantie_devise IS NULL)
    ),
    CONSTRAINT assurance_franchise_devise CHECK (
        (franchise_montant IS NULL) = (franchise_devise IS NULL)
    ),
    CONSTRAINT assurance_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT assurance_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT assurance_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT assurance_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_assurance_client ON assurance (client_id);
CREATE INDEX idx_assurance_fiche ON assurance (fiche_version_id);

-- ===========================================================================
-- F4 — CERTIFICATIONS ET QUALIFICATIONS
-- ===========================================================================

CREATE TABLE certification (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    intitule              varchar(255) NOT NULL,   -- repris du certificat, jamais reconstitué
    organisme             varchar(255) NOT NULL,   -- repris du certificat
    domaine_code          varchar(100) NOT NULL,   -- jeu certification.domaine (contenu : L5)
    numero_certificat     varchar(255),
    date_obtention        date,
    date_echeance         date,                    -- échéance à surveiller
    piece                 uuid         NOT NULL REFERENCES document (id),
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT certification_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT certification_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT certification_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT certification_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_certification_client ON certification (client_id);
CREATE INDEX idx_certification_fiche ON certification (fiche_version_id);

-- ===========================================================================
-- F5 — RÉFÉRENCES DE CHANTIERS
-- ===========================================================================

CREATE TABLE reference_chantier (
    id                        uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                 uuid         NOT NULL REFERENCES client (id),
    entreprise_id             uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id          uuid         NOT NULL REFERENCES fiche_version (id),
    intitule_operation        varchar(255) NOT NULL,
    maitre_ouvrage            varchar(255) NOT NULL,
    nature_travaux_code       varchar(100),            -- jeu reference.nature_travaux
    nature_travaux_libelle    varchar(255),            -- texte libre conservé en plus
    lieu_commune              varchar(255),
    lieu_departement          varchar(255),
    date_debut                date,
    date_fin                  date,
    montant_montant           varchar(2048),           -- CHIFFRÉ (A6)
    montant_devise            varchar(3),
    duree_mois                integer,
    surface_traitee           numeric(18,2),
    surface_unite             varchar(255),
    description               text,
    competences_appliquees    text,
    attestation_bonne_execution uuid       REFERENCES document (id),
    contact_reference         varchar(2048),           -- CHIFFRÉ (A6) — donnée personnelle
    date_creation             timestamptz  NOT NULL DEFAULT now(),
    date_modification         timestamptz  NOT NULL DEFAULT now(),
    sensibilite               varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement     varchar(100) NOT NULL DEFAULT 'actif',
    origine                   varchar(100) NOT NULL,
    confiance                 varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id        uuid         REFERENCES document (id),
    CONSTRAINT reference_chantier_montant_devise CHECK (
        (montant_montant IS NULL) = (montant_devise IS NULL)
    ),
    CONSTRAINT reference_chantier_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT reference_chantier_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT reference_chantier_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT reference_chantier_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_reference_chantier_client ON reference_chantier (client_id);
CREATE INDEX idx_reference_chantier_fiche ON reference_chantier (fiche_version_id);

-- ===========================================================================
-- F6 — MOYENS HUMAINS
-- ===========================================================================

CREATE TABLE effectif_metier (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    metier_code           varchar(100) NOT NULL,   -- jeu metier.* ou rh.metier
    metier_libelle        varchar(255),            -- libellé tel que saisi
    nombre                integer      NOT NULL,
    commentaire           text,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT effectif_metier_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT effectif_metier_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT effectif_metier_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT effectif_metier_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_effectif_metier_client ON effectif_metier (client_id);
CREATE INDEX idx_effectif_metier_fiche ON effectif_metier (fiche_version_id);

CREATE TABLE organigramme (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    piece                 uuid         REFERENCES document (id),
    description           text,
    date_maj              date,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT organigramme_une_par_fiche UNIQUE (fiche_version_id),
    CONSTRAINT organigramme_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT organigramme_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT organigramme_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT organigramme_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_organigramme_client ON organigramme (client_id);
CREATE INDEX idx_organigramme_fiche ON organigramme (fiche_version_id);

CREATE TABLE cv (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    nom                   varchar(2048) NOT NULL,   -- CHIFFRÉ (A6) — donnée personnelle
    prenom                varchar(2048) NOT NULL,   -- CHIFFRÉ (A6) — donnée personnelle
    fonction              varchar(255) NOT NULL,
    diplomes              varchar(2048),            -- CHIFFRÉ (A6) — donnée personnelle
    annees_experience     integer,                  -- saisi ou lu, jamais déduit d'une date
    cv_piece              varchar(2048) NOT NULL,   -- CHIFFRÉ (A6) — référence à document.id
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'confidentiel',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT cv_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT cv_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT cv_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT cv_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_cv_client ON cv (client_id);
CREATE INDEX idx_cv_fiche ON cv (fiche_version_id);

-- ===========================================================================
-- F7 — MOYENS MATÉRIELS
-- ===========================================================================

CREATE TABLE moyen_materiel (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    categorie_code        varchar(100) NOT NULL,   -- jeu moyen.categorie (contenu : L5)
    designation           varchar(255) NOT NULL,
    quantite              integer      NOT NULL,
    marque_modele         varchar(255),
    annee                 integer,
    propriete             varchar(100),            -- jeu moyen.propriete : propre | location
    disponibilite         varchar(255),
    justificatif          uuid         REFERENCES document (id),
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT moyen_materiel_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT moyen_materiel_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT moyen_materiel_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT moyen_materiel_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_moyen_materiel_client ON moyen_materiel (client_id);
CREATE INDEX idx_moyen_materiel_fiche ON moyen_materiel (fiche_version_id);

-- ===========================================================================
-- F8 — FICHES TECHNIQUES PRODUITS
-- ===========================================================================

CREATE TABLE produit (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    fournisseur           varchar(255) NOT NULL,
    reference_produit     varchar(255) NOT NULL,   -- référence exacte du fournisseur
    designation           varchar(255) NOT NULL,
    famille_code          varchar(100),            -- jeu produit.famille (contenu : L5)
    domaine_application   text,
    fiche_technique       uuid         REFERENCES document (id),
    avis_technique        uuid         REFERENCES document (id),
    date_validite_document date,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT produit_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT produit_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT produit_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT produit_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_produit_client ON produit (client_id);
CREATE INDEX idx_produit_fiche ON produit (fiche_version_id);

-- ===========================================================================
-- F9 — MÉMOIRE TECHNIQUE TYPE (stocké, jamais exploité automatiquement)
-- ===========================================================================

CREATE TABLE chapitre_memoire (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entreprise_id         uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id      uuid         NOT NULL REFERENCES fiche_version (id),
    titre                 varchar(255) NOT NULL,
    ordre                 integer      NOT NULL,
    contenu_texte         text,
    statut                varchar(100) NOT NULL DEFAULT 'brouillon',  -- jeu memoire.statut_chapitre
    date_redaction        date,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    origine               varchar(100) NOT NULL,
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    CONSTRAINT chapitre_memoire_origine CHECK (
        origine IN ('document_extrait', 'saisie_entreprise', 'mixte')
    ),
    CONSTRAINT chapitre_memoire_confiance CHECK (
        confiance IN ('verifie', 'declare_non_verifie', 'a_verifier')
    ),
    CONSTRAINT chapitre_memoire_source_si_extrait CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    ),
    CONSTRAINT chapitre_memoire_verifie_exige_source CHECK (
        confiance <> 'verifie' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_chapitre_memoire_client ON chapitre_memoire (client_id);
CREATE INDEX idx_chapitre_memoire_fiche ON chapitre_memoire (fiche_version_id);

-- ===========================================================================
-- TABLES DE LIAISON — champs de type `liste` (§ 3.1)
-- Chaque table porte `client_id` : le cloisonnement est vérifiable sans jointure (I1).
-- ===========================================================================

CREATE TABLE reference_chantier_photo (
    reference_chantier_id uuid         NOT NULL REFERENCES reference_chantier (id),
    document_id           uuid         NOT NULL REFERENCES document (id),
    client_id             uuid         NOT NULL REFERENCES client (id),
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (reference_chantier_id, document_id)
);
CREATE INDEX idx_reference_chantier_photo_client ON reference_chantier_photo (client_id);

CREATE TABLE produit_certificat (
    produit_id    uuid         NOT NULL REFERENCES produit (id),
    document_id   uuid         NOT NULL REFERENCES document (id),
    client_id     uuid         NOT NULL REFERENCES client (id),
    date_creation timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (produit_id, document_id)
);
CREATE INDEX idx_produit_certificat_client ON produit_certificat (client_id);

CREATE TABLE chapitre_memoire_reference (
    chapitre_memoire_id  uuid         NOT NULL REFERENCES chapitre_memoire (id),
    reference_chantier_id uuid        NOT NULL REFERENCES reference_chantier (id),
    client_id            uuid         NOT NULL REFERENCES client (id),
    date_creation        timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (chapitre_memoire_id, reference_chantier_id)
);
CREATE INDEX idx_chapitre_memoire_reference_client
    ON chapitre_memoire_reference (client_id);

CREATE TABLE chapitre_memoire_document (
    chapitre_memoire_id uuid         NOT NULL REFERENCES chapitre_memoire (id),
    document_id         uuid         NOT NULL REFERENCES document (id),
    client_id           uuid         NOT NULL REFERENCES client (id),
    date_creation       timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (chapitre_memoire_id, document_id)
);
CREATE INDEX idx_chapitre_memoire_document_client
    ON chapitre_memoire_document (client_id);

-- ===========================================================================
-- JEUX DE RÉFÉRENCE FERMÉS (§ 8.6, « ce document (fermé) »)
-- Ce sont des DONNÉES, jamais des colonnes ni des tables dédiées (décision D2).
-- Aucune valeur métier inventée : le contenu des jeux `metier.*`,
-- `document.type_document`, `entreprise.forme_juridique`, `assurance.type`,
-- `attestation.type`, `certification.domaine`, `moyen.categorie`,
-- `produit.famille`, `reference.nature_travaux`, `rh.origine_effectif`,
-- `facturation.formule` et `facturation.periodicite` appartient à
-- docs/NOMENCLATURE-REFERENCE.md ou à la source administrative : il n'est pas
-- chargé ici.
-- ===========================================================================

INSERT INTO jeu_reference (namespace, libelle, description, domaine, portee, source, statut)
VALUES
  ('securite.sensibilite', 'Sensibilité d''une donnée', 'Niveaux de sensibilité du modèle', 'securite', 'global', 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  ('commun.statut_enregistrement', 'Statut d''enregistrement', 'Un enregistrement est archivé, jamais supprimé en dur', 'commun', 'global', 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  ('tracabilite.origine', 'Origine d''une valeur', 'D''où vient une valeur — jamais « généré par l''IA »', 'tracabilite', 'global', 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.confiance', 'Niveau de confiance d''une valeur', 'Verifie / declare_non_verifie / a_verifier', 'tracabilite', 'global', 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.entite', 'Entités de contenu traçables', 'Noms logiques des entités de contenu (§ 10)', 'tracabilite', 'global', 'docs/DATA-MODEL-V2.md § 8.6', 'actif'),
  ('referentiel.portee', 'Portée d''un jeu de référence', 'global (MVP) ou client', 'referentiel', 'global', 'docs/DATA-MODEL-V2.md § 8.2', 'actif'),
  ('referentiel.statut', 'Statut d''un jeu de référence', 'actif ou deprecie', 'referentiel', 'global', 'docs/DATA-MODEL-V2.md § 8.2', 'actif'),
  ('referentiel.statut_valeur', 'Statut d''une valeur de référence', 'actif ou deprecie — jamais supprimée', 'referentiel', 'global', 'docs/DATA-MODEL-V2.md § 8.3', 'actif'),
  ('fiche.famille', 'Familles de la bibliothèque', 'Les neuf familles F1 à F9', 'fiche', 'global', 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.statut_version', 'États d''une version de fiche', 'Sept états alignés sur l''interface', 'fiche', 'global', 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_famille', 'États d''avancement d''une famille', 'Quatre états d''interface', 'fiche', 'global', 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('validation.cible', 'Cible d''une validation de relecture', 'fiche ou famille', 'validation', 'global', 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  ('validation.statut', 'Statut d''une validation de relecture', 'validee ou revoquee', 'validation', 'global', 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  ('client.statut', 'Statut d''un client', 'actif, suspendu, resilie', 'client', 'global', 'docs/DATA-MODEL-V2.md § 5.1', 'actif'),
  ('utilisateur.statut', 'Statut d''un utilisateur', 'actif ou archive', 'utilisateur', 'global', 'docs/DATA-MODEL-V2.md § 5.2', 'actif'),
  ('entreprise.statut', 'Statut d''une entreprise', 'active ou archivee', 'entreprise', 'global', 'docs/DATA-MODEL-V2.md § 5.3', 'actif'),
  ('rh.statut_mandat', 'Statut d''un mandat', 'en_exercice ou cesse', 'rh', 'global', 'docs/DATA-MODEL-V2.md § 5.5', 'actif'),
  ('memoire.statut_chapitre', 'Statut d''un chapitre de mémoire', 'brouillon, accepte, archive', 'memoire', 'global', 'docs/DATA-MODEL-V2.md § 10 F9', 'actif'),
  ('document.deposant', 'Déposant d''une pièce', 'entreprise ou service', 'document', 'global', 'docs/DATA-MODEL-V2.md § 9.1', 'actif'),
  ('moyen.propriete', 'Propriété d''un moyen matériel', 'propre ou location', 'moyen', 'global', 'docs/DATA-MODEL-V2.md § 10 F7', 'actif'),
  ('facturation.type_evenement', 'Type d''événement de facturation', 'abonnement ou projet', 'facturation', 'global', 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_evenement', 'Statut d''un événement de facturation', 'a_valider, constate, annule', 'facturation', 'global', 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_dossier', 'Statut d''un dossier', 'en_preparation, pret, depose, abandonne', 'facturation', 'global', 'docs/DATA-MODEL-V2.md § 11.2', 'actif');

INSERT INTO valeur_reference (namespace, code, libelle, parent_code, ordre, domaine, source, statut)
VALUES
  -- securite.sensibilite
  ('securite.sensibilite', 'publique', 'Publique', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  ('securite.sensibilite', 'interne', 'Interne', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  ('securite.sensibilite', 'confidentiel', 'Confidentiel', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  -- commun.statut_enregistrement
  ('commun.statut_enregistrement', 'actif', 'Actif', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  ('commun.statut_enregistrement', 'archive', 'Archivé', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 3.2', 'actif'),
  -- tracabilite.origine
  ('tracabilite.origine', 'document_extrait', 'Lu dans un document', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.origine', 'saisie_entreprise', 'Déclaré par l''entreprise', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.origine', 'mixte', 'Plusieurs origines dans l''enregistrement', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 7.4', 'actif'),
  -- tracabilite.confiance
  ('tracabilite.confiance', 'verifie', 'Vérifié', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.confiance', 'declare_non_verifie', 'Déclaré, non vérifié', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  ('tracabilite.confiance', 'a_verifier', 'À vérifier', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 7.2', 'actif'),
  -- tracabilite.entite (noms logiques des entités de contenu, § 10)
  ('tracabilite.entite', 'entreprise_version', 'Identité de l''entreprise (versionnée)', NULL, 10, 'F1', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'representant_legal', 'Représentant légal', NULL, 20, 'F1', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'exercice_comptable', 'Exercice comptable', NULL, 30, 'F2', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'attestation', 'Attestation justificative', NULL, 40, 'F2', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'capacite_production', 'Capacité de production', NULL, 50, 'F2', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'assurance', 'Contrat d''assurance', NULL, 60, 'F3', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'certification', 'Certification ou qualification', NULL, 70, 'F4', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'reference_chantier', 'Référence de chantier', NULL, 80, 'F5', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'effectif_metier', 'Effectif par métier', NULL, 90, 'F6', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'organigramme', 'Organigramme', NULL, 100, 'F6', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'cv', 'CV d''un profil clé', NULL, 110, 'F6', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'moyen_materiel', 'Moyen matériel', NULL, 120, 'F7', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'produit', 'Produit et fiche technique', NULL, 130, 'F8', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  ('tracabilite.entite', 'chapitre_memoire', 'Chapitre du mémoire technique type', NULL, 140, 'F9', 'docs/DATA-MODEL-V2.md § 10', 'actif'),
  -- referentiel.*
  ('referentiel.portee', 'global', 'Global (tous les clients)', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 8.2', 'actif'),
  ('referentiel.portee', 'client', 'Propre à un client (réservé, non utilisé au MVP)', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 8.4', 'actif'),
  ('referentiel.statut', 'actif', 'Actif', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 8.2', 'actif'),
  ('referentiel.statut', 'deprecie', 'Déprécié', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 8.2', 'actif'),
  ('referentiel.statut_valeur', 'actif', 'Active', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 8.3', 'actif'),
  ('referentiel.statut_valeur', 'deprecie', 'Dépréciée', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 8.3', 'actif'),
  -- fiche.famille (les neuf familles)
  ('fiche.famille', 'identite', 'Identité', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'capacites_financieres', 'Capacités financières', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'assurances', 'Assurances', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'certifications', 'Certifications et qualifications', NULL, 40, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'references_chantiers', 'Références de chantiers', NULL, 50, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'moyens_humains', 'Moyens humains', NULL, 60, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'moyens_materiels', 'Moyens matériels', NULL, 70, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'fiches_produits', 'Fiches techniques produits', NULL, 80, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.famille', 'memoire_technique', 'Mémoire technique type', NULL, 90, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  -- fiche.statut_version (7 états)
  ('fiche.statut_version', 'vierge', 'Vierge', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'en_saisie', 'En cours de saisie', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'socle_complet', 'Socle complet (non relue)', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'en_relecture', 'En relecture', NULL, 40, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'validee', 'Relue et validée par humain', NULL, 50, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'validee_puis_modifiee', 'Validée puis modifiée (à relire)', NULL, 60, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  ('fiche.statut_version', 'archivee', 'Archivée', NULL, 70, NULL, 'docs/DATA-MODEL-V2.md § 6.2', 'actif'),
  -- fiche.statut_famille (4 états)
  ('fiche.statut_famille', 'non_commencee', 'Non commencée', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.statut_famille', 'demarree', 'Démarrée', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.statut_famille', 'socle_complet', 'Socle complet', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  ('fiche.statut_famille', 'validee', 'Relue et validée (famille)', NULL, 40, NULL, 'docs/DATA-MODEL-V2.md § 6.3', 'actif'),
  -- validation.*
  ('validation.cible', 'fiche', 'La fiche entière', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  ('validation.cible', 'famille', 'Une famille', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  ('validation.statut', 'validee', 'Validée', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  ('validation.statut', 'revoquee', 'Révoquée', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 6.4', 'actif'),
  -- client.statut, utilisateur.statut, entreprise.statut
  ('client.statut', 'actif', 'Actif', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 5.1', 'actif'),
  ('client.statut', 'suspendu', 'Suspendu', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 5.1', 'actif'),
  ('client.statut', 'resilie', 'Résilié', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 5.1', 'actif'),
  ('utilisateur.statut', 'actif', 'Actif', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 5.2', 'actif'),
  ('utilisateur.statut', 'archive', 'Archivé', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 5.2', 'actif'),
  ('entreprise.statut', 'active', 'Active', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 5.3', 'actif'),
  ('entreprise.statut', 'archivee', 'Archivée', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 5.3', 'actif'),
  -- rh.statut_mandat
  ('rh.statut_mandat', 'en_exercice', 'En exercice', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 5.5', 'actif'),
  ('rh.statut_mandat', 'cesse', 'Cessé', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 5.5', 'actif'),
  -- memoire.statut_chapitre
  ('memoire.statut_chapitre', 'brouillon', 'Brouillon', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 10 F9', 'actif'),
  ('memoire.statut_chapitre', 'accepte', 'Accepté', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 10 F9', 'actif'),
  ('memoire.statut_chapitre', 'archive', 'Archivé', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 10 F9', 'actif'),
  -- document.deposant
  ('document.deposant', 'entreprise', 'L''entreprise', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 9.1', 'actif'),
  ('document.deposant', 'service', 'Le service', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 9.1', 'actif'),
  -- moyen.propriete
  ('moyen.propriete', 'propre', 'Propre', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 10 F7', 'actif'),
  ('moyen.propriete', 'location', 'Location', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 10 F7', 'actif'),
  -- facturation.* (structure seulement — aucun contenu commercial)
  ('facturation.type_evenement', 'abonnement', 'Abonnement', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.type_evenement', 'projet', 'Projet déposé', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_evenement', 'a_valider', 'À valider', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_evenement', 'constate', 'Constaté', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_evenement', 'annule', 'Annulé', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 11.3', 'actif'),
  ('facturation.statut_dossier', 'en_preparation', 'En préparation', NULL, 10, NULL, 'docs/DATA-MODEL-V2.md § 11.2', 'actif'),
  ('facturation.statut_dossier', 'pret', 'Prêt', NULL, 20, NULL, 'docs/DATA-MODEL-V2.md § 11.2', 'actif'),
  ('facturation.statut_dossier', 'depose', 'Déposé', NULL, 30, NULL, 'docs/DATA-MODEL-V2.md § 11.2', 'actif'),
  ('facturation.statut_dossier', 'abandonne', 'Abandonné', NULL, 40, NULL, 'docs/DATA-MODEL-V2.md § 11.2', 'actif');

-- +migrate down

-- Ordre inverse : d'abord les tables de liaison, puis les familles.
DROP TABLE IF EXISTS chapitre_memoire_document;
DROP TABLE IF EXISTS chapitre_memoire_reference;
DROP TABLE IF EXISTS produit_certificat;
DROP TABLE IF EXISTS reference_chantier_photo;

DROP TABLE IF EXISTS chapitre_memoire;
DROP TABLE IF EXISTS produit;
DROP TABLE IF EXISTS moyen_materiel;
DROP TABLE IF EXISTS cv;
DROP TABLE IF EXISTS organigramme;
DROP TABLE IF EXISTS effectif_metier;
DROP TABLE IF EXISTS reference_chantier;
DROP TABLE IF EXISTS certification;
DROP TABLE IF EXISTS assurance;
DROP TABLE IF EXISTS capacite_production;
DROP TABLE IF EXISTS attestation;
DROP TABLE IF EXISTS exercice_comptable;
DROP TABLE IF EXISTS representant_legal;
DROP TABLE IF EXISTS entreprise_version;

-- Les jeux de référence chargés par cette migration sont retirés dans l'ordre
-- inverse : valeurs d'abord (clé étrangère vers le jeu), puis jeux.
DELETE FROM valeur_reference WHERE namespace IN (
  'securite.sensibilite', 'commun.statut_enregistrement', 'tracabilite.origine',
  'tracabilite.confiance', 'tracabilite.entite', 'referentiel.portee',
  'referentiel.statut', 'referentiel.statut_valeur', 'fiche.famille',
  'fiche.statut_version', 'fiche.statut_famille', 'validation.cible',
  'validation.statut', 'client.statut', 'utilisateur.statut',
  'entreprise.statut', 'rh.statut_mandat', 'memoire.statut_chapitre',
  'document.deposant', 'moyen.propriete', 'facturation.type_evenement',
  'facturation.statut_evenement', 'facturation.statut_dossier'
);

DELETE FROM jeu_reference WHERE namespace IN (
  'securite.sensibilite', 'commun.statut_enregistrement', 'tracabilite.origine',
  'tracabilite.confiance', 'tracabilite.entite', 'referentiel.portee',
  'referentiel.statut', 'referentiel.statut_valeur', 'fiche.famille',
  'fiche.statut_version', 'fiche.statut_famille', 'validation.cible',
  'validation.statut', 'client.statut', 'utilisateur.statut',
  'entreprise.statut', 'rh.statut_mandat', 'memoire.statut_chapitre',
  'document.deposant', 'moyen.propriete', 'facturation.type_evenement',
  'facturation.statut_evenement', 'facturation.statut_dossier'
);
