-- 0002_jeu_demo_phase4.sql — jeu de DÉMONSTRATION FICTIF de la phase 4 (lot L7).
--
-- ============================================================================
-- CRITÈRES D'ACCEPTATION DE LA PHASE 4 (docs/PLAN-PHASE-4.md § 1) — À DÉROULER
-- AVEC CE JEU. La phase est terminée quand, en local (`bash demarrer.sh`) :
--
--   1. un utilisateur se connecte et arrive sur un écran qui dit CE QUE LA
--      PLATEFORME FAIT POUR LUI, avec une action principale évidente ;
--   2. il crée son entreprise, importe deux ou trois documents existants et
--      obtient des PROPOSITIONS À VALIDER (la bibliothèque se remplit sans
--      saisie champ par champ) ;
--   3. il dépose un DCE (le DCE fictif de `scripts/jeu-de-test/fictif/`) et voit
--      les PIÈCES EXIGÉES, les CRITÈRES PONDÉRÉS et la DATE LIMITE, chacun avec
--      sa source ;
--   4. il demande le MÉMOIRE TECHNIQUE et obtient un dossier structuré suivant
--      l'ordre et la pondération des critères du DCE, où chaque argument renvoie
--      à un élément réel de sa bibliothèque, et où LES MANQUES SONT LISTÉS avec
--      l'action à mener ;
--   5. il EXPORTE ce mémoire dans un fichier ouvrable dans un traitement de
--      texte ;
--   6. aucun écran n'affiche de valeur technique, de jargon d'architecture ni
--      d'identifiant interne (contrôle par capture d'écran).
--
-- Mode opératoire complet, étape par étape : `scripts/jeu-de-test/DEMONSTRATION.md`.
-- ============================================================================
--
-- AVERTISSEMENT : AUCUNE DONNÉE RÉELLE. Tous les libellés portent la mention
-- « FICTIF ». Aucune entreprise, aucune collectivité, aucun marché, aucun
-- assureur, aucun organisme certificateur réel n'est employé (décision D10).
-- L'acheteur et tous les maîtres d'ouvrage sont entièrement inventés.
--
-- Ce que ce fichier contient
--   * le compte de démonstration (`client` + `utilisateur`) ;
--   * l'entreprise fictive, sa version de fiche et ses 9 familles ;
--   * une bibliothèque réellement remplie : 4 références de chantiers comparables,
--     2 assurances, 2 certifications, 2 capacités de production, 4 moyens
--     matériels, 4 effectifs par métier, 1 organigramme, 2 produits, 2 chapitres
--     de mémoire type, et 6 documents sources ;
--   * un manque volontaire : voir DEMONSTRATION.md § « Manque volontaire ».
--
-- Ce que ce fichier NE contient PAS, et pourquoi
--   * le MÉMOIRE TECHNIQUE n'est pas semé : il se génère par le parcours
--     (lots L2 / L5b), sinon la démonstration ne démontre rien ;
--   * le DCE n'est pas semé : il se DÉPOSE depuis `fictif/` (critère 3) ;
--   * les champs CHIFFRÉS par client (annexe A § A6) ne peuvent pas être écrits
--     en SQL : leur charge est `v1:<base64>` produite par la clé maîtresse du
--     `.env`, dérivée par `client_id`. Les lignes concernées — `entreprise_version`,
--     `representant_legal`, `exercice_comptable`, ainsi que
--     `reference_chantier.montant_montant` / `contact_reference` — sont écrites par
--     `scripts/jeu-de-test/completer_demo_phase4.py`, appelé par
--     `scripts/jeu-de-test/charger_demo_phase4.sh`, avec le hachage Argon2id du mot
--     de passe de démonstration ;
--   * la table `authentification` reste VIDE dans ce fichier : aucun mot de passe,
--     même fictif, n'a sa place dans un fichier versionné.
--
-- Idempotence : UUID fixes + `ON CONFLICT DO NOTHING`. Relancer ce fichier ne
-- duplique rien et ne détruit rien.
--
-- Usage :
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0002_jeu_demo_phase4.sql
--   (ou, recommandé, le chargeur complet : bash scripts/jeu-de-test/charger_demo_phase4.sh)

\set ON_ERROR_STOP on

BEGIN;

-- ===========================================================================
-- 0. Repères du jeu — mêmes UUID fixes dans le SQL, dans le compléteur et dans
--    DEMONSTRATION.md. Ne pas les changer sans changer les trois.
--      client_id            d0000000-0000-4000-8000-000000000001
--      utilisateur_id       d0000000-0000-4000-8000-000000000002
--      entreprise_id        d0000000-0000-4000-8000-000000000003
--      fiche_version_id     d0000000-0000-4000-8000-000000000004
-- ===========================================================================

-- 1. client — le locataire de démonstration (racine du cloisonnement)
INSERT INTO client (id, libelle, statut) VALUES
    ('d0000000-0000-4000-8000-000000000001',
     'FICTIF — Client de démonstration phase 4 (étanchéité)', 'actif')
ON CONFLICT (id) DO NOTHING;

-- 2. utilisateur — le compte de démonstration (empreinte posée par le compléteur)
INSERT INTO utilisateur (id, client_id, identifiant_connexion, nom_affichage) VALUES
    ('d0000000-0000-4000-8000-000000000002',
     'd0000000-0000-4000-8000-000000000001',
     'demo@exemple.invalid', 'Compte de démonstration (FICTIF)')
ON CONFLICT (identifiant_connexion) DO NOTHING;

-- 3. entreprise + 4. fiche_version
INSERT INTO entreprise (id, client_id, libelle_court) VALUES
    ('d0000000-0000-4000-8000-000000000003',
     'd0000000-0000-4000-8000-000000000001',
     'FICTIF — Océan Étanchéité')
ON CONFLICT (id) DO NOTHING;

INSERT INTO fiche_version (id, client_id, entreprise_id, numero_version, statut, commentaire) VALUES
    ('d0000000-0000-4000-8000-000000000004',
     'd0000000-0000-4000-8000-000000000001',
     'd0000000-0000-4000-8000-000000000003', 1, 'en_saisie',
     'FICTIF — première version de la fiche de démonstration')
ON CONFLICT (entreprise_id, numero_version) DO NOTHING;

-- 5. fiche_famille — l'avancement des neuf familles (états d'interface)
INSERT INTO fiche_famille (id, client_id, entreprise_id, fiche_version_id, famille_code, statut) VALUES
    ('d0000000-0000-4000-8000-000000000501','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','identite','demarree'),
    ('d0000000-0000-4000-8000-000000000502','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','capacites_financieres','demarree'),
    ('d0000000-0000-4000-8000-000000000503','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','assurances','demarree'),
    ('d0000000-0000-4000-8000-000000000504','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','certifications','demarree'),
    ('d0000000-0000-4000-8000-000000000505','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','references_chantiers','demarree'),
    ('d0000000-0000-4000-8000-000000000506','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','moyens_humains','demarree'),
    ('d0000000-0000-4000-8000-000000000507','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','moyens_materiels','demarree'),
    ('d0000000-0000-4000-8000-000000000508','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','fiches_produits','demarree'),
    ('d0000000-0000-4000-8000-000000000509','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004','memoire_technique','demarree')
ON CONFLICT (fiche_version_id, famille_code) DO NOTHING;

-- ===========================================================================
-- 6. document — les pièces sources de la bibliothèque (fictives).
-- Leurs fichiers chiffrés sont écrits par le compléteur, dans `data/` (hors
-- dépôt). Le chemin suit `clients/<client_id>/<document_id>.bin` (storage/fichiers).
-- Les libellés sont rédigés pour que la checklist les rapproche des pièces
-- exigées du DCE fictif — c'est le croisement que la démonstration montre.
-- ===========================================================================
INSERT INTO document (id, client_id, entreprise_id, fiche_version_id, type_document, libelle,
                      emetteur, date_emission, date_validite_fin, chemin_stockage, deposant,
                      empreinte_sha256, taille_octets, mime_type, sensibilite) VALUES
    ('d0000000-0000-4000-8000-000000000101','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'attestation_assurance_decennale','Attestation d''assurance responsabilité civile décennale','ASSURANCES-FICTIVES OCÉANE (FICTIF)',DATE '2026-01-01',DATE '2026-10-15',
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000101.bin','entreprise',repeat('1',64),1351,'text/plain','interne'),
    ('d0000000-0000-4000-8000-000000000102','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'attestation_assurance_professionnelle','Attestation d''assurance responsabilité civile professionnelle','ASSURANCES-FICTIVES OCÉANE (FICTIF)',DATE '2026-01-01',DATE '2027-01-31',
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000102.bin','entreprise',repeat('2',64),1280,'text/plain','interne'),
    ('d0000000-0000-4000-8000-000000000103','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'certificat_qualification','Certificat de qualification professionnelle de l''entreprise — domaine étanchéité','O.C.F.E. — Organisme Certificat Fictif Étanchéité (FICTIF)',DATE '2021-09-01',DATE '2026-09-15',
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000103.bin','entreprise',repeat('3',64),1100,'text/plain','interne'),
    ('d0000000-0000-4000-8000-000000000104','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'fiche_technique_produit','Fiche technique du procédé d''étanchéité proposé — référence fournisseur exacte','FOURNISSEUR-FICTIF (FICTIF)',DATE '2026-03-01',DATE '2027-03-01',
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000104.bin','entreprise',repeat('4',64),1500,'text/plain','interne'),
    ('d0000000-0000-4000-8000-000000000105','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'plaquette_presentation','Plaquette de présentation de l''entreprise','OCÉAN ÉTANCHÉITÉ (FICTIF)',DATE '2026-02-01',NULL,
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000105.bin','entreprise',repeat('5',64),2520,'text/plain','interne'),
    ('d0000000-0000-4000-8000-000000000106','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'attestation_bonne_execution','Attestation de bonne exécution d''un chantier comparable, délivrée par son maître d''ouvrage','S.I.F.E.P.F. (FICTIF)',DATE '2024-11-20',NULL,
     'clients/d0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-000000000106.bin','entreprise',repeat('6',64),900,'text/plain','interne')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 7. assurance — DEUX contrats dont un à échéance PROCHE (2026-10-15).
-- Le statut de validité est CALCULÉ à la lecture (`calculer_statut_validite`).
-- `FENETRE_ALERTE_JOURS` réglée (voir DEMONSTRATION.md) fait apparaître
-- « échéance proche » ; sinon l'alerte n'apparaît qu'à l'expiration.
-- ===========================================================================
INSERT INTO assurance (id, client_id, entreprise_id, fiche_version_id, type_assurance, assureur,
                       numero_contrat, montant_garantie_montant, montant_garantie_devise,
                       franchise_montant, franchise_devise, date_debut, date_echeance,
                       activites_couvertes, piece, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000201','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'responsabilite_civile_decennale','ASSURANCES-FICTIVES OCÉANE (FICTIF)','FICTIF-RCD-2026-1187',1500000.00,'EUR',5000.00,'EUR',
     DATE '2026-01-01',DATE '2026-10-15',
     'Étanchéité de toitures-terrasses, relevés et points singuliers, travaux en site occupé (FICTIF).',
     'd0000000-0000-4000-8000-000000000101','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000202','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'responsabilite_civile_professionnelle','ASSURANCES-FICTIVES OCÉANE (FICTIF)','FICTIF-RCP-2026-1188',800000.00,'EUR',2500.00,'EUR',
     DATE '2026-01-01',DATE '2027-01-31',
     'Travaux d''étanchéité et activités connexes (FICTIF).',
     'd0000000-0000-4000-8000-000000000102','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 8. certification — dont une ÉCHUE (2026-09-15) : c'est l'alerte visible sans
-- aucun réglage.
-- ===========================================================================
INSERT INTO certification (id, client_id, entreprise_id, fiche_version_id, intitule, organisme,
                           domaine_code, numero_certificat, date_obtention, date_echeance, piece,
                           origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000301','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Qualification étanchéité de toitures-terrasses','O.C.F.E. — Organisme Certificat Fictif Étanchéité (FICTIF)','etancheite','CERT-FICTIF-2021-0457',DATE '2021-09-01',DATE '2026-09-15',
     'd0000000-0000-4000-8000-000000000103','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000302','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Habilitation travaux en hauteur','ORGANISME-FICTIF (FICTIF)','travaux_en_hauteur','HAB-FICTIF-2025-3391',DATE '2025-03-10',DATE '2028-03-10',
     'd0000000-0000-4000-8000-000000000103','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- 9. capacite_production
INSERT INTO capacite_production (id, client_id, entreprise_id, fiche_version_id, description, unite, valeur, commentaire, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000401','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Surface d''étanchéité posée en moyenne par mois','m2/mois',1400.0000,'Moyenne déclarée sur les trois derniers exercices (FICTIF).','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000402','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Équipes simultanément mobilisables sur un même marché','équipes',4.0000,'Quatre équipes de deux compagnons (FICTIF).','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 10. reference_chantier — 4 chantiers comparables (FICTIFS).
-- `montant_montant` et `contact_reference` sont CHIFFRÉS : ils sont posés par le
-- compléteur (et `montant_devise` avec eux, la contrainte de paire l'exige).
-- La référence 901 est celle qui SATISFAIT le critère lourd du DCE fictif
-- (« étanchéité de toitures-terrasses sur bâtiments scolaires », 40 %).
-- AUCUNE référence ne porte « végétalisé » : c'est le manque volontaire.
-- ===========================================================================
INSERT INTO reference_chantier (id, client_id, entreprise_id, fiche_version_id, intitule_operation,
                                maitre_ouvrage, nature_travaux_code, nature_travaux_libelle,
                                lieu_commune, lieu_departement, date_debut, date_fin, duree_mois,
                                surface_traitee, surface_unite, description, competences_appliquees,
                                origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000901','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FICTIF — Réfection de l''étanchéité des toitures-terrasses — groupe scolaire « Les Filaos »',
     'S.I.F.E.P.F. (maître d''ouvrage FICTIF)','etancheite_toiture_terrasse','Étanchéité de toitures-terrasses',
     'Plaine des Filaos (FICTIF)','97 (FICTIF)',DATE '2024-07-08',DATE '2024-10-18',14,
     3200.00,'m2',
     'Réfection complète de l''étanchéité de toitures-terrasses de deux bâtiments scolaires en service. Décapage de l''ancienne protection, pose d''un complexe bitumineux, reprise des relevés d''étanchéité et traitement des points singuliers (émergences, descentes d''eaux pluviales, joints de dilatation). Travaux exécutés en site occupé, par phases pendant les vacances scolaires.',
     'Étanchéité de toitures-terrasses de bâtiments scolaires ; relevés d''étanchéité et points singuliers ; exécution en site occupé par phases.',
     'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000902','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FICTIF — Étanchéité de toiture-terrasse — collège « Les Alizés »',
     'Régie scolaire fictive du Bassin Vert (FICTIF)','etancheite_toiture_terrasse','Étanchéité de toitures-terrasses',
     'Bassin Vert (FICTIF)','97 (FICTIF)',DATE '2022-06-01',DATE '2022-08-05',9,
     2100.00,'m2',
     'Étanchéité d''une toiture-terrasse accessible sur un bâtiment d''enseignement : dépose de la protection, étanchéité bicouche, relevés d''étanchéité et reprise des joints de dilatation.',
     'Toitures-terrasses accessibles ; étanchéité bicouche ; relevés et joints de dilatation.',
     'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000903','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FICTIF — Étanchéité de bâtiments administratifs — site occupé',
     'Communauté FICTIVE des services du Plateau (FICTIF)','etancheite_site_occupe','Étanchéité en site occupé',
     'Plateau Fictif (FICTIF)','97 (FICTIF)',DATE '2023-02-13',DATE '2023-05-26',15,
     1800.00,'m2',
     'Réfection d''étanchéité de toitures-terrasses de locaux administratifs occupés pendant les travaux. Organisation en trois phases, protection des accès, mise en place de zones de travail compartimentées.',
     'Exécution en site occupé ; planning par phases ; protection des accès.',
     'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000904','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FICTIF — Réfection d''étanchéité — école « Roche-Plate »',
     'S.I.F.E.P.F. (maître d''ouvrage FICTIF)','etancheite_toiture_terrasse','Étanchéité de toitures-terrasses',
     'Roche-Plate (FICTIF)','97 (FICTIF)',DATE '2021-07-05',DATE '2021-08-20',7,
     1250.00,'m2',
     'Remise en état de l''étanchéité d''une toiture-terrasse d''école : nettoyage, réparation ponctuelle du support, étanchéité autoprotégée et reprise des relevés.',
     'Toitures-terrasses scolaires ; relevés d''étanchéité ; étanchéité autoprotégée.',
     'saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 11. effectif_metier — moyens humains (FICTIF)
-- ===========================================================================
INSERT INTO effectif_metier (id, client_id, entreprise_id, fiche_version_id, metier_code, metier_libelle, nombre, commentaire, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000601','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'etancheur','Étancheur',16,'Quatre équipes de deux compagnons, plus les remplacements (FICTIF).','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000602','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'chef_equipe','Chef d''équipe étanchéité',4,'Un chef d''équipe par équipe (FICTIF).','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000603','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'conducteur_travaux','Conducteur de travaux',2,'Suivi de chantier et planning (FICTIF).','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000604','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'responsable_qse','Responsable qualité, sécurité, environnement',1,'Préparation des plans de prévention (FICTIF).','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- 12. organigramme
INSERT INTO organigramme (id, client_id, entreprise_id, fiche_version_id, piece, description, date_maj, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000701','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'd0000000-0000-4000-8000-000000000105',
     'Direction — un dirigeant ; bureau d''études — deux conducteurs de travaux ; quatre équipes d''étanchéité ; une fonction qualité-sécurité. (FICTIF)',
     DATE '2026-02-01','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 13. moyen_materiel — moyens affectables (FICTIF)
-- ===========================================================================
INSERT INTO moyen_materiel (id, client_id, entreprise_id, fiche_version_id, categorie_code, designation, quantite, marque_modele, annee, propriete, disponibilite, justificatif, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000801','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'materiel_mise_en_oeuvre','Groupe d''étanchéité à air chaud',3,'MARQUE-FICTIVE GA-500',2023,'propre','Disponible immédiatement (FICTIF).',NULL,'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000802','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'engin_elevation','Nacelle élévatrice',2,'MARQUE-FICTIVE N-120',2022,'location','Louée à la demande (FICTIF).',NULL,'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000803','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'vehicule_chantier','Camion-benne avec grue',1,'MARQUE-FICTIVE CB-300',2021,'propre','Affecté au chantier (FICTIF).',NULL,'saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000804','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'materiel_chantier','Monte-charge de chantier et groupe électrogène',1,'MARQUE-FICTIVE MC-90',2020,'propre','Évacuation des gravats et alimentation de secours (FICTIF).',NULL,'saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- ===========================================================================
-- 14. produit — fiches techniques (FICTIF)
-- ===========================================================================
INSERT INTO produit (id, client_id, entreprise_id, fiche_version_id, fournisseur, reference_produit, designation, famille_code, domaine_application, fiche_technique, avis_technique, date_validite_document, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-0000000009a1','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FOURNISSEUR-FICTIF (FICTIF)','REF-FICTIVE-BIT-42','Membrane bitumineuse bicouche autoprotégée','membrane_bitumineuse',
     'Étanchéité de toitures-terrasses, relevés et points singuliers (FICTIF).',
     'd0000000-0000-4000-8000-000000000104',NULL,DATE '2027-03-01','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-0000000009a2','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'FOURNISSEUR-FICTIF (FICTIF)','REF-FICTIVE-SYN-17','Membrane synthétique d''étanchéité de toiture-terrasse','membrane_synthetique',
     'Toitures-terrasses exposées, protection gravillonnée (FICTIF).',
     'd0000000-0000-4000-8000-000000000104',NULL,DATE '2027-03-01','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- 15. chapitre_memoire — chapitres type réutilisables (FICTIF)
--    (Le mémoire technique de la consultation, lui, se GÉNÈRE par le parcours.)
INSERT INTO chapitre_memoire (id, client_id, entreprise_id, fiche_version_id, titre, ordre, contenu_texte, statut, date_redaction, origine, confiance) VALUES
    ('d0000000-0000-4000-8000-000000000a01','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Méthode d''exécution d''une étanchéité de toiture-terrasse',1,
     'Décapage de l''ancienne protection, contrôle et réparation du support, pose du complexe d''étanchéité, reprise des relevés et des points singuliers, contrôle final et réception. (FICTIF)',
     'brouillon',DATE '2025-11-14','saisie_entreprise','declare_non_verifie'),
    ('d0000000-0000-4000-8000-000000000a02','d0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000004',
     'Organisation d''un chantier en site occupé',2,
     'Travaux organisés par phases calées sur les périodes d''inoccupation des locaux, balisage des zones, protection des accès et des façades, évacuation des gravats par filière agréée. (FICTIF)',
     'brouillon',DATE '2025-11-14','saisie_entreprise','declare_non_verifie')
ON CONFLICT (id) DO NOTHING;

-- 16. liaisons (champs de type liste)
INSERT INTO produit_certificat (produit_id, document_id, client_id) VALUES
    ('d0000000-0000-4000-8000-0000000009a1','d0000000-0000-4000-8000-000000000103','d0000000-0000-4000-8000-000000000001')
ON CONFLICT (produit_id, document_id) DO NOTHING;

INSERT INTO chapitre_memoire_reference (chapitre_memoire_id, reference_chantier_id, client_id) VALUES
    ('d0000000-0000-4000-8000-000000000a01','d0000000-0000-4000-8000-000000000901','d0000000-0000-4000-8000-000000000001'),
    ('d0000000-0000-4000-8000-000000000a02','d0000000-0000-4000-8000-000000000903','d0000000-0000-4000-8000-000000000001')
ON CONFLICT (chapitre_memoire_id, reference_chantier_id) DO NOTHING;

COMMIT;

-- ===========================================================================
-- Contrôle immédiat : ce que le SQL vient de poser (avant le compléteur).
-- Les tables à champs chiffrés (`entreprise_version`, `representant_legal`,
-- `exercice_comptable`) sont encore vides : elles sont remplies par
-- `completer_demo_phase4.py`, qui seul détient la clé maîtresse.
-- ===========================================================================
SELECT 'client' AS table_demo, count(*) AS nb FROM client WHERE id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'utilisateur', count(*) FROM utilisateur WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'entreprise', count(*) FROM entreprise WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'fiche_famille', count(*) FROM fiche_famille WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'document', count(*) FROM document WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'reference_chantier', count(*) FROM reference_chantier WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'assurance', count(*) FROM assurance WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'certification', count(*) FROM certification WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'moyen_materiel', count(*) FROM moyen_materiel WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'effectif_metier', count(*) FROM effectif_metier WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'produit', count(*) FROM produit WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'chapitre_memoire', count(*) FROM chapitre_memoire WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
UNION ALL SELECT 'consultation (doit rester 0)', count(*) FROM consultation WHERE client_id = 'd0000000-0000-4000-8000-000000000001'
ORDER BY 1;

-- ===========================================================================
-- NETTOYAGE (commenté — à décommenter et exécuter EXPLICITEMENT pour retirer le
-- jeu de démonstration, dans l'ordre inverse des dépendances).
-- Aucune ligne d'un autre client n'est touchée : tout est filtré par le
-- client_id de démonstration.
--
-- \set ON_ERROR_STOP on
-- BEGIN;
-- DELETE FROM checklist_ligne WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM checklist_execution WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM extraction_element WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM consultation WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM memoire_section_source WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM memoire_section WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM memoire_manque WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM memoire_validation WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM memoire_dossier WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM import_proposition WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM import_document WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM chapitre_memoire_document WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM chapitre_memoire_reference WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM produit_certificat WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM reference_chantier_photo WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM chapitre_memoire WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM produit WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM moyen_materiel WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM cv WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM organigramme WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM effectif_metier WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM reference_chantier WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM certification WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM assurance WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM capacite_production WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM attestation WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM exercice_comptable WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM representant_legal WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM entreprise_version WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM validation_relecture WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM tracabilite_valeur WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM document WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM fiche_famille WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM fiche_version WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM entreprise WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM authentification WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM utilisateur WHERE client_id = 'd0000000-0000-4000-8000-000000000001';
-- DELETE FROM client WHERE id = 'd0000000-0000-4000-8000-000000000001';
-- COMMIT;
-- (Puis supprimer le répertoire de pièces, hors dépôt :
--  rm -rf data/clients/d0000000-0000-4000-8000-000000000001)
-- ===========================================================================
