-- 0001_init_socle.sql — L1 : socle technique
-- Tables racines et transverses, conformes à docs/DATA-MODEL-V2.md.
--
-- Conventions (annexe A § A2) :
--   identifiants techniques  -> uuid (v4, gen_random_uuid())
--   texte_court              -> varchar(255)      texte_long -> text
--   horodatage               -> timestamptz       date       -> date
--   booleen                  -> smallint 0/1 (CHECK)
--   code_reference           -> varchar(100)  (valeur d'un jeu de référence ; le
--                               contenu du jeu appartient à L5, JAMAIS au schéma)
--   empreinte                -> varchar(128)
--
-- Cloisonnement (annexe A § A1) : `client_id` est présent sur toute entité de
-- contenu, y compris lorsqu'il serait déductible par jointure. Les jeux de
-- référence (§ 8) sont globaux et ne portent aucun `client_id` (invariant I5).
--
-- Aucune donnée réelle : ce fichier ne crée que des structures.

-- +migrate up

-- 1. client — la partie contractante, racine du cloisonnement (§ 5.1)
CREATE TABLE client (
    id                uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    libelle           varchar(255) NOT NULL,
    statut            varchar(100) NOT NULL DEFAULT 'actif',      -- jeu client.statut
    date_creation     timestamptz  NOT NULL DEFAULT now(),
    date_resiliation  date,
    sensibilite       varchar(100) NOT NULL DEFAULT 'interne'     -- jeu securite.sensibilite
);

-- 2. utilisateur — le compte d'accès (§ 5.2). Un utilisateur = un client (MVP).
CREATE TABLE utilisateur (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    identifiant_connexion  varchar(255) NOT NULL,
    nom_affichage          varchar(255) NOT NULL,
    statut                 varchar(100) NOT NULL DEFAULT 'actif', -- jeu utilisateur.statut
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT utilisateur_identifiant_unique UNIQUE (identifiant_connexion)
);
CREATE INDEX idx_utilisateur_client ON utilisateur (client_id);

-- 2bis. authentification — secret d'authentification, SÉPARÉ des tables de contenu.
-- Motif : docs/DATA-MODEL-V2.md § 5.2 exclut tout mot de passe des tables de contenu ;
-- ce secret vit donc dans cette table dédiée, jamais dans un dépôt (annexe A § A5).
CREATE TABLE authentification (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    utilisateur_id         uuid         NOT NULL REFERENCES utilisateur (id),
    mot_de_passe_empreinte varchar(255) NOT NULL,   -- Argon2id, jamais en clair
    algorithme             varchar(100) NOT NULL DEFAULT 'argon2id',
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    date_modification      timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT authentification_utilisateur_unique UNIQUE (utilisateur_id)
);
CREATE INDEX idx_authentification_client ON authentification (client_id);

-- 3. entreprise — l'ancre stable (§ 5.3), le contenu d'identité est versionné.
CREATE TABLE entreprise (
    id                      uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               uuid         NOT NULL REFERENCES client (id),
    libelle_court           varchar(255) NOT NULL,
    statut                  varchar(100) NOT NULL DEFAULT 'active', -- jeu entreprise.statut
    date_creation           timestamptz  NOT NULL DEFAULT now(),
    date_derniere_version   timestamptz
);
CREATE INDEX idx_entreprise_client ON entreprise (client_id);

-- 4. fiche_version — l'axe de versionnement (§ 6.1). Elle porte client_id et
-- entreprise_id mais pas fiche_version_id (constat C10, § 3.2).
CREATE TABLE fiche_version (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    entreprise_id          uuid         NOT NULL REFERENCES entreprise (id),
    numero_version         integer      NOT NULL,
    statut                 varchar(100) NOT NULL DEFAULT 'vierge', -- jeu fiche.statut_version
    version_parente_id     uuid         REFERENCES fiche_version (id),
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    date_derniere_ecriture timestamptz  NOT NULL DEFAULT now(),
    commentaire            text,
    CONSTRAINT fiche_version_numero_unique UNIQUE (entreprise_id, numero_version)
);
CREATE INDEX idx_fiche_version_client ON fiche_version (client_id);
CREATE INDEX idx_fiche_version_entreprise ON fiche_version (entreprise_id);

-- 5. document — le document source (§ 9.1). En 0001, entreprise_id et
-- fiche_version_id sont NON nuls ; L3 (migration 0003) les rend NULL-ables pour
-- les DCE (annexe B § B1). Aucun format n'est fixé ici (points ouverts § 15).
CREATE TABLE document (
    id                      uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               uuid         NOT NULL REFERENCES client (id),
    entreprise_id           uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id        uuid         NOT NULL REFERENCES fiche_version (id),
    type_document           varchar(100) NOT NULL,   -- jeu document.type_document
    libelle                 varchar(255) NOT NULL,
    emetteur                varchar(255),
    date_emission           date,
    date_validite_debut     date,
    date_validite_fin       date,
    reference_document      varchar(255),
    chemin_stockage         varchar(255) NOT NULL,   -- préfixé par le client, hors dépôt
    deposant                varchar(100) NOT NULL,   -- jeu document.deposant
    empreinte_sha256        varchar(128),
    taille_octets           integer,
    mime_type               varchar(255),
    sensibilite             varchar(100) NOT NULL DEFAULT 'interne',
    stockage_client_seulement smallint   NOT NULL DEFAULT 0,
    date_creation           timestamptz  NOT NULL DEFAULT now(),
    date_modification       timestamptz  NOT NULL DEFAULT now(),
    statut_enregistrement   varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT document_stockage_client_seulement_bool CHECK (stockage_client_seulement IN (0, 1))
);
CREATE INDEX idx_document_client ON document (client_id);
CREATE INDEX idx_document_fiche_version ON document (fiche_version_id);

-- 6. fiche_famille — l'avancement par famille (§ 6.3).
CREATE TABLE fiche_famille (
    id                uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id         uuid         NOT NULL REFERENCES client (id),
    entreprise_id     uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id  uuid         NOT NULL REFERENCES fiche_version (id),
    famille_code      varchar(100) NOT NULL,   -- jeu fiche.famille (9 familles)
    statut            varchar(100) NOT NULL DEFAULT 'non_commencee',
    date_maj          timestamptz  NOT NULL DEFAULT now(),
    date_creation     timestamptz  NOT NULL DEFAULT now(),
    date_modification timestamptz  NOT NULL DEFAULT now(),
    sensibilite       varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT fiche_famille_version_famille_unique UNIQUE (fiche_version_id, famille_code)
);
CREATE INDEX idx_fiche_famille_client ON fiche_famille (client_id);

-- 7. validation_relecture — le verrou de relecture humaine (§ 6.4).
CREATE TABLE validation_relecture (
    id                        uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                 uuid         NOT NULL REFERENCES client (id),
    entreprise_id             uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id          uuid         NOT NULL REFERENCES fiche_version (id),
    cible_type                varchar(100) NOT NULL,   -- jeu validation.cible : fiche|famille
    famille_code              varchar(100),            -- obligatoire si cible_type = famille
    relecteur_nom             varchar(255) NOT NULL,   -- saisi par l'humain
    relecteur_utilisateur_id  uuid         REFERENCES utilisateur (id),
    date_validation           timestamptz  NOT NULL DEFAULT now(),
    attestation_cochee        smallint     NOT NULL DEFAULT 0,
    statut                    varchar(100) NOT NULL DEFAULT 'validee', -- jeu validation.statut
    date_revocation           timestamptz,
    motif_revocation          varchar(255),
    empreinte_contenu         varchar(128) NOT NULL,
    empreinte_algorithme      varchar(100) NOT NULL,
    commentaire               text,
    date_creation             timestamptz  NOT NULL DEFAULT now(),
    date_modification         timestamptz  NOT NULL DEFAULT now(),
    sensibilite               varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement     varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT validation_attestation_bool CHECK (attestation_cochee IN (0, 1)),
    CONSTRAINT validation_famille_requise CHECK (
        cible_type <> 'famille' OR famille_code IS NOT NULL
    )
);
CREATE INDEX idx_validation_relecture_client ON validation_relecture (client_id);
CREATE INDEX idx_validation_relecture_fiche ON validation_relecture (fiche_version_id);

-- 8. tracabilite_valeur — traçabilité au niveau de la valeur (§ 7.2).
-- Aucune valeur sans source : origine document_extrait exige source_document_id.
CREATE TABLE tracabilite_valeur (
    id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid         NOT NULL REFERENCES client (id),
    entite                varchar(100) NOT NULL,   -- jeu tracabilite.entite
    enregistrement_id     uuid         NOT NULL,
    champ                 varchar(255) NOT NULL,
    origine               varchar(100) NOT NULL,   -- jeu tracabilite.origine (jamais genere_ia)
    confiance             varchar(100) NOT NULL DEFAULT 'a_verifier',
    source_document_id    uuid         REFERENCES document (id),
    source_emplacement    varchar(255),
    source_date_extraction timestamptz,
    source_commentaire    text,
    date_creation         timestamptz  NOT NULL DEFAULT now(),
    date_modification     timestamptz  NOT NULL DEFAULT now(),
    sensibilite           varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement varchar(100) NOT NULL DEFAULT 'actif',
    CONSTRAINT tracabilite_valeur_unique UNIQUE (entite, enregistrement_id, champ),
    CONSTRAINT tracabilite_source_obligatoire CHECK (
        origine <> 'document_extrait' OR source_document_id IS NOT NULL
    )
);
CREATE INDEX idx_tracabilite_valeur_client ON tracabilite_valeur (client_id);
CREATE INDEX idx_tracabilite_valeur_enregistrement
    ON tracabilite_valeur (entite, enregistrement_id);

-- 9. jeu_reference — conteneur de jeux de référence (§ 8.2). Global (I5).
CREATE TABLE jeu_reference (
    namespace         varchar(255) PRIMARY KEY,       -- minuscules, '.' séparateur
    libelle           varchar(255) NOT NULL,
    description       text,
    domaine           varchar(255),
    portee            varchar(100) NOT NULL DEFAULT 'global',   -- jeu referentiel.portee
    source            varchar(255) NOT NULL,
    statut            varchar(100) NOT NULL DEFAULT 'actif',    -- jeu referentiel.statut
    version           varchar(255),
    date_creation     timestamptz  NOT NULL DEFAULT now(),
    date_modification timestamptz  NOT NULL DEFAULT now()
);

-- 10. valeur_reference — les valeurs d'un jeu (§ 8.3). Global (I5).
CREATE TABLE valeur_reference (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace           varchar(255) NOT NULL REFERENCES jeu_reference (namespace),
    code                varchar(255) NOT NULL,
    libelle             varchar(255) NOT NULL,
    parent_code         varchar(255),
    ordre               integer      NOT NULL DEFAULT 0,
    domaine             varchar(255),
    source              varchar(255) NOT NULL,
    statut              varchar(100) NOT NULL DEFAULT 'actif',
    date_debut_validite date,
    date_fin_validite   date,
    date_creation       timestamptz  NOT NULL DEFAULT now(),
    date_modification   timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT valeur_reference_unique UNIQUE (namespace, code)
);
CREATE INDEX idx_valeur_reference_namespace ON valeur_reference (namespace);

-- 11. abonnement — l'abonnement du client (§ 11.1).
CREATE TABLE abonnement (
    id            uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     uuid         NOT NULL REFERENCES client (id),
    formule_code  varchar(100) NOT NULL,   -- jeu facturation.formule (contenu = décision d'Anthony)
    statut        varchar(100) NOT NULL DEFAULT 'actif',
    date_debut    date         NOT NULL,
    date_fin      date,
    periodicite   varchar(100) NOT NULL,   -- jeu facturation.periodicite
    commentaire   text,
    date_creation timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX idx_abonnement_client ON abonnement (client_id);

-- 12. dossier — le projet déposé (§ 11.2). Aucun prix, aucun montant (ligne rouge).
CREATE TABLE dossier (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id              uuid         NOT NULL REFERENCES client (id),
    entreprise_id          uuid         NOT NULL REFERENCES entreprise (id),
    fiche_version_id       uuid         NOT NULL REFERENCES fiche_version (id),
    reference_consultation varchar(255),   -- saisi par l'humain, jamais déduit
    objet                  text,
    statut                 varchar(100) NOT NULL DEFAULT 'en_preparation',
    date_depot             date,
    commentaire            text,
    date_creation          timestamptz  NOT NULL DEFAULT now(),
    date_modification      timestamptz  NOT NULL DEFAULT now(),
    sensibilite            varchar(100) NOT NULL DEFAULT 'interne',
    statut_enregistrement  varchar(100) NOT NULL DEFAULT 'actif'
);
CREATE INDEX idx_dossier_client ON dossier (client_id);
CREATE INDEX idx_dossier_entreprise ON dossier (entreprise_id);

-- 13. evenement_facturation — ce qui doit être compté (§ 11.3). Aucun montant.
CREATE TABLE evenement_facturation (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id            uuid         NOT NULL REFERENCES client (id),
    type_evenement       varchar(100) NOT NULL,   -- jeu facturation.type_evenement
    abonnement_id        uuid         REFERENCES abonnement (id),
    date_evenement       timestamptz  NOT NULL DEFAULT now(),
    periode_debut        date,
    periode_fin          date,
    source_declenchement varchar(255) NOT NULL,
    statut               varchar(100) NOT NULL DEFAULT 'a_valider',
    reference_externe    varchar(255),
    commentaire          text,
    date_creation        timestamptz  NOT NULL DEFAULT now(),
    date_modification    timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT evenement_abonnement_requis CHECK (
        type_evenement <> 'abonnement' OR abonnement_id IS NOT NULL
    )
);
CREATE INDEX idx_evenement_facturation_client ON evenement_facturation (client_id);

-- 14. evenement_facturation_dossier — rattachement dossier <-> facturation (§ 11.4).
-- `client_id` est ajouté ici par application de l'annexe A § A1 (présent sur toute
-- entité de contenu, y compris déductible par jointure) — voir commentaire de carte.
CREATE TABLE evenement_facturation_dossier (
    evenement_facturation_id uuid         NOT NULL REFERENCES evenement_facturation (id),
    dossier_id               uuid         NOT NULL REFERENCES dossier (id),
    client_id                uuid         NOT NULL REFERENCES client (id),
    role                     varchar(100) NOT NULL DEFAULT 'principal',
    date_rattachement        timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (evenement_facturation_id, dossier_id)
);
CREATE INDEX idx_efd_client ON evenement_facturation_dossier (client_id);

-- +migrate down

DROP TABLE IF EXISTS evenement_facturation_dossier;
DROP TABLE IF EXISTS evenement_facturation;
DROP TABLE IF EXISTS dossier;
DROP TABLE IF EXISTS abonnement;
DROP TABLE IF EXISTS valeur_reference;
DROP TABLE IF EXISTS jeu_reference;
DROP TABLE IF EXISTS tracabilite_valeur;
DROP TABLE IF EXISTS validation_relecture;
DROP TABLE IF EXISTS fiche_famille;
DROP TABLE IF EXISTS document;
DROP TABLE IF EXISTS fiche_version;
DROP TABLE IF EXISTS entreprise;
DROP TABLE IF EXISTS authentification;
DROP TABLE IF EXISTS utilisateur;
DROP TABLE IF EXISTS client;
