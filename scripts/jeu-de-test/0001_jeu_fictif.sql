-- 0001_jeu_fictif.sql — jeu de données FICTIF pour la vérification des sauvegardes (lot L7).
--
-- AVERTISSEMENT : aucune donnée réelle. Tous les libellés portent la mention
-- « FICTIF ». Aucun identifiant, aucune référence, aucun document d'entreprise ni
-- de collectivité. Ce fichier sert uniquement à obtenir des comptages de lignes
-- non nuls pour démontrer qu'une sauvegarde puis une restauration transportent
-- bien le contenu (exigence 2 du lot L7).
--
-- Deux clients distincts (A et B) sont insérés pour que le jeu de test porte aussi
-- le cloisonnement par `client_id` (annexe A § A1) : les mêmes tables contiennent
-- des lignes de deux locataires différents.
--
-- La table `authentification` est volontairement laissée VIDE : elle contient des
-- empreintes de mots de passe, et aucune valeur de nature secrète — même fictive —
-- n'a sa place dans un fichier versionné du dépôt.
--
-- Idempotence : chaque insertion utilise ON CONFLICT DO NOTHING et des UUID fixes.
-- Relancer ce fichier ne duplique rien et ne détruit rien.
--
-- Usage : psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0001_jeu_fictif.sql

\set ON_ERROR_STOP on

BEGIN;

-- 1. client — deux locataires fictifs
INSERT INTO client (id, libelle, statut) VALUES
    ('a0000000-0000-4000-8000-000000000001', 'FICTIF — Client A (jeu de test L7)', 'actif'),
    ('b0000000-0000-4000-8000-000000000001', 'FICTIF — Client B (jeu de test L7)', 'actif')
ON CONFLICT (id) DO NOTHING;

-- 2. utilisateur
INSERT INTO utilisateur (id, client_id, identifiant_connexion, nom_affichage) VALUES
    ('a0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000001',
     'fictif.a@exemple.invalid', 'Utilisateur FICTIF A'),
    ('b0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001',
     'fictif.b@exemple.invalid', 'Utilisateur FICTIF B')
ON CONFLICT (identifiant_connexion) DO NOTHING;

-- 3. entreprise
INSERT INTO entreprise (id, client_id, libelle_court) VALUES
    ('a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001',
     'FICTIF — Entreprise A'),
    ('b0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000001',
     'FICTIF — Entreprise B')
ON CONFLICT (id) DO NOTHING;

-- 4. fiche_version
INSERT INTO fiche_version (id, client_id, entreprise_id, numero_version, statut) VALUES
    ('a0000000-0000-4000-8000-000000000004', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 1, 'en_cours'),
    ('b0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000001',
     'b0000000-0000-4000-8000-000000000003', 1, 'en_cours')
ON CONFLICT (entreprise_id, numero_version) DO NOTHING;

-- 5. document
INSERT INTO document (id, client_id, entreprise_id, fiche_version_id, type_document,
                      libelle, chemin_stockage, deposant, empreinte_sha256, taille_octets,
                      mime_type, sensibilite) VALUES
    ('a0000000-0000-4000-8000-000000000005', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'kbis', 'FICTIF — piece A', 'client-a-fictif/documents/piece-a.txt',
     'saisie_entreprise', repeat('0', 64), 128, 'text/plain', 'interne'),
    ('b0000000-0000-4000-8000-000000000005', 'b0000000-0000-4000-8000-000000000001',
     'b0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000004',
     'kbis', 'FICTIF — piece B', 'client-b-fictif/documents/piece-b.txt',
     'saisie_entreprise', repeat('1', 64), 256, 'text/plain', 'confidentiel')
ON CONFLICT (id) DO NOTHING;

-- 6. fiche_famille — trois familles pour le client A
INSERT INTO fiche_famille (id, client_id, entreprise_id, fiche_version_id, famille_code, statut) VALUES
    ('a0000000-0000-4000-8000-000000000006', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'identite_entreprise', 'renseignee'),
    ('a0000000-0000-4000-8000-000000000007', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'capacite_financiere', 'non_commencee'),
    ('a0000000-0000-4000-8000-000000000008', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'references_professionnelles', 'non_commencee')
ON CONFLICT (fiche_version_id, famille_code) DO NOTHING;

-- 7. validation_relecture — une relecture humaine attestée (fictive)
INSERT INTO validation_relecture (id, client_id, entreprise_id, fiche_version_id, cible_type,
                                  relecteur_nom, attestation_cochee, empreinte_contenu,
                                  empreinte_algorithme) VALUES
    ('a0000000-0000-4000-8000-000000000009', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'fiche', 'Relecteur FICTIF', 1, repeat('a', 64), 'sha256')
ON CONFLICT (id) DO NOTHING;

-- 8. tracabilite_valeur — deux valeurs tracées, dont une issue d'un document
INSERT INTO tracabilite_valeur (id, client_id, entite, enregistrement_id, champ, origine,
                                confiance, source_document_id) VALUES
    ('a0000000-0000-4000-8000-00000000000a', 'a0000000-0000-4000-8000-000000000001',
     'entreprise_version', 'a0000000-0000-4000-8000-000000000003', 'siret_siege',
     'document_extrait', 'a_verifier', 'a0000000-0000-4000-8000-000000000005'),
    ('a0000000-0000-4000-8000-00000000000b', 'a0000000-0000-4000-8000-000000000001',
     'entreprise_version', 'a0000000-0000-4000-8000-000000000003', 'libelle',
     'saisie_entreprise', 'verifiee', NULL)
ON CONFLICT (entite, enregistrement_id, champ) DO NOTHING;

-- 9. jeu_reference / 10. valeur_reference — un jeu global minimal, fictif
INSERT INTO jeu_reference (namespace, libelle, source, portee) VALUES
    ('test.fictif.l7', 'FICTIF — jeu de test L7', 'jeu de test L7 (aucune source externe)', 'global')
ON CONFLICT (namespace) DO NOTHING;

INSERT INTO valeur_reference (id, namespace, code, libelle, source) VALUES
    ('a0000000-0000-4000-8000-00000000000c', 'test.fictif.l7', 'code_a', 'FICTIF — valeur A',
     'jeu de test L7'),
    ('a0000000-0000-4000-8000-00000000000d', 'test.fictif.l7', 'code_b', 'FICTIF — valeur B',
     'jeu de test L7')
ON CONFLICT (namespace, code) DO NOTHING;

-- 11. abonnement
INSERT INTO abonnement (id, client_id, formule_code, date_debut, periodicite) VALUES
    ('a0000000-0000-4000-8000-00000000000e', 'a0000000-0000-4000-8000-000000000001',
     'fictif_mensuel', DATE '2026-01-01', 'mensuelle'),
    ('b0000000-0000-4000-8000-00000000000e', 'b0000000-0000-4000-8000-000000000001',
     'fictif_mensuel', DATE '2026-02-01', 'mensuelle')
ON CONFLICT (id) DO NOTHING;

-- 12. dossier — deux dossiers fictifs (aucun montant, ligne rouge respectée)
INSERT INTO dossier (id, client_id, entreprise_id, fiche_version_id, reference_consultation,
                     objet, statut) VALUES
    ('a0000000-0000-4000-8000-00000000000f', 'a0000000-0000-4000-8000-000000000001',
     'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000004',
     'FICTIF-CONS-2026-001', 'FICTIF — objet de consultation (test L7)', 'en_preparation'),
    ('b0000000-0000-4000-8000-00000000000f', 'b0000000-0000-4000-8000-000000000001',
     'b0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000004',
     'FICTIF-CONS-2026-002', 'FICTIF — objet de consultation (test L7)', 'en_preparation')
ON CONFLICT (id) DO NOTHING;

-- 13. evenement_facturation
INSERT INTO evenement_facturation (id, client_id, type_evenement, abonnement_id,
                                   source_declenchement) VALUES
    ('a0000000-0000-4000-8000-000000000010', 'a0000000-0000-4000-8000-000000000001',
     'abonnement', 'a0000000-0000-4000-8000-00000000000e', 'jeu de test L7'),
    ('a0000000-0000-4000-8000-000000000011', 'a0000000-0000-4000-8000-000000000001',
     'dossier_depose', NULL, 'jeu de test L7')
ON CONFLICT (id) DO NOTHING;

-- 14. evenement_facturation_dossier
INSERT INTO evenement_facturation_dossier (evenement_facturation_id, dossier_id, client_id, role)
VALUES ('a0000000-0000-4000-8000-000000000011',
        'a0000000-0000-4000-8000-00000000000f',
        'a0000000-0000-4000-8000-000000000001', 'principal')
ON CONFLICT (evenement_facturation_id, dossier_id) DO NOTHING;

COMMIT;

-- Contrôle immédiat : comptage par table (doit être joint au rapport du lot).
SELECT c.relname AS table_fictive,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', n.nspname, c.relname),
                           false, true, '')))[1]::text::int AS nb_lignes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public'
ORDER BY c.relname;