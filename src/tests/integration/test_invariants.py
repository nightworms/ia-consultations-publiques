"""Invariants du modèle I1 à I8 — contrôlés **par comptage**.

Références : `docs/DATA-MODEL-V2.md` § 3.4 (I1…I6) et § 17.8 (I7, I8),
annexe B du plan de phase 3. Chaque invariant est vérifié par une **requête de
comptage** ; le résultat attendu est **zéro ligne en écart**. Les comptages réels
sont imprimés et repris dans `docs/RAPPORT-TESTS-PHASE-3.md`.

Pour que le comptage ne porte pas sur du vide, un jeu fictif est chargé avant les
contrôles (client A peuplé : identité, assurances, référence, DCE analysé, élément
validé, checklist, validation de relecture). Aucune donnée réelle (« DÉMONSTRATION »).
"""

from __future__ import annotations

from app.config import charger_config
from app.services.versionnement import ServiceVersionnement
from app.storage.connexion import ContexteClient

from .conftest import MENTION, tables_avec_client_id
from .test_isolation import _preparer_donnees_a


def _compte(connexion_admin, sql: str) -> int:
    return int(connexion_admin.lire(sql)[0][0])


def _colonnes(connexion_admin, table: str) -> set[str]:
    return {
        ligne[0]
        for ligne in connexion_admin.lire(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table,),
        )
    }


def test_invariants_i1_a_i8_par_comptage(connexion, connexion_admin, contexte_a, contexte_b):
    # Jeu fictif : deux clients, un peuplé (A), un vide (B), pour ne pas compter du vide.
    _preparer_donnees_a(connexion, contexte_a)
    # Un second client, avec une entreprise/fiche, pour éprouver le cloisonnement des comptages.
    from app.services.bibliotheque import ServiceBibliotheque

    service_b = ServiceBibliotheque(
        connexion, charger_config().cle_chiffrement_maitresse, contexte_b
    )
    entreprise_b = service_b.creer_entreprise(f"Entreprise fictive B — {MENTION}")
    connexion.valider()
    service_b.ouvrir_fiche(entreprise_b)
    connexion.valider()

    tables = tables_avec_client_id(connexion_admin)
    colonnes = {table: _colonnes(connexion_admin, table) for table in tables}
    ecarts: dict[str, int] = {}
    details: dict[str, object] = {}

    # -- I1 : client_id non nul sur toute entité de contenu ------------------ #
    i1 = sum(
        _compte(connexion_admin, f"SELECT count(*) FROM {t} WHERE client_id IS NULL;")
        for t in tables
    )
    ecarts["I1"] = i1

    # -- I2 : client_id cohérent avec l'entreprise et la fiche_version ------- #
    i2 = 0
    for t in tables:
        if "entreprise_id" in colonnes[t]:
            i2 += _compte(
                connexion_admin,
                f"SELECT count(*) FROM {t} x JOIN entreprise e ON e.id = x.entreprise_id "
                "WHERE x.entreprise_id IS NOT NULL AND x.client_id <> e.client_id;",
            )
        if "fiche_version_id" in colonnes[t]:
            i2 += _compte(
                connexion_admin,
                f"SELECT count(*) FROM {t} x JOIN fiche_version f ON f.id = x.fiche_version_id "
                "WHERE x.fiche_version_id IS NOT NULL AND x.client_id <> f.client_id;",
            )
    ecarts["I2"] = i2

    # -- I3 : aucune entité orpheline --------------------------------------- #
    i3 = 0
    for t in tables:
        if "entreprise_id" in colonnes[t]:
            i3 += _compte(
                connexion_admin,
                f"SELECT count(*) FROM {t} x WHERE x.entreprise_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM entreprise e WHERE e.id = x.entreprise_id);",
            )
        if "fiche_version_id" in colonnes[t]:
            i3 += _compte(
                connexion_admin,
                f"SELECT count(*) FROM {t} x WHERE x.fiche_version_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM fiche_version f WHERE f.id = x.fiche_version_id);",
            )
    ecarts["I3"] = i3

    # -- I4 : source d'une valeur du même client ---------------------------- #
    ecarts["I4"] = _compte(
        connexion_admin,
        "SELECT count(*) FROM tracabilite_valeur t JOIN document d ON d.id = t.source_document_id "
        "WHERE t.source_document_id IS NOT NULL AND t.client_id <> d.client_id;",
    )

    # -- I5 : les jeux de référence globaux ne portent aucun client_id ------- #
    i5 = _compte(
        connexion_admin,
        "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' "
        "AND table_name IN ('jeu_reference', 'valeur_reference') AND column_name = 'client_id';",
    )
    ecarts["I5"] = i5

    # -- I6 : une validation `validee` dont l'empreinte ne concorde plus ----- #
    fiches = connexion_admin.lire("SELECT id, client_id FROM fiche_version;")
    i6 = 0
    for fiche_id, client_id in fiches:
        svc = ServiceVersionnement(
            connexion, charger_config().cle_chiffrement_maitresse, ContexteClient(str(client_id))
        )
        i6 += len(svc.controler_validations(str(fiche_id)))
    ecarts["I6"] = i6

    # -- I7 : cohérence nature ⇔ rattachements de `document` ---------------- #
    ecarts["I7"] = _compte(
        connexion_admin,
        "SELECT count(*) FROM document WHERE NOT ( "
        "(nature = 'piece_bibliotheque' AND entreprise_id IS NOT NULL "
        "AND fiche_version_id IS NOT NULL) OR "
        "(nature = 'dce' AND consultation_id IS NOT NULL) );",
    )

    # -- I8 : cohérence statut ⇔ document_id des lignes de checklist --------- #
    i8 = _compte(
        connexion_admin,
        "SELECT count(*) FROM checklist_ligne l WHERE "
        "(l.statut = 'presente' AND l.document_id IS NULL) OR "
        "(l.statut = 'manquante' AND l.document_id IS NOT NULL);",
    )
    i8 += _compte(
        connexion_admin,
        "SELECT count(*) FROM checklist_ligne l JOIN document d ON d.id = l.document_id "
        "WHERE l.document_id IS NOT NULL AND d.client_id <> l.client_id;",
    )
    ecarts["I8"] = i8

    # -- Volume réellement contrôlé (pour que le comptage ne soit pas vide) -- #
    volumes = {
        t: _compte(connexion_admin, f"SELECT count(*) FROM {t};")
        for t in ("entreprise", "fiche_version", "assurance", "document",
                  "consultation", "extraction_element", "checklist_ligne",
                  "validation_relecture")
    }
    details["volumes"] = volumes
    details["nb_tables_portant_client_id"] = len(tables)

    print("\n[invariants] volume contrôlé :", volumes)
    print(f"[invariants] tables portant client_id : {len(tables)}")
    print("[invariants] écarts par invariant :", ecarts)

    assert volumes["checklist_ligne"] > 0, "le comptage I8 porterait sur du vide"
    assert volumes["validation_relecture"] > 0, "le comptage I6 porterait sur du vide"
    assert ecarts == {k: 0 for k in ecarts}, f"invariants en écart : {ecarts}"


def test_i6_detecte_reellement_une_validation_devenue_fausse(connexion, contexte_a):
    """Contre-épreuve : I6 n'est pas un compteur qui renvoie toujours 0.

    On valide une fiche, puis on modifie le contenu **en SQL direct**, sans passer
    par le service (donc sans révocation). Le contrôle indépendant par empreinte
    doit alors signaler l'anomalie.
    """
    from app.services.bibliotheque import ServiceBibliotheque

    config = charger_config()
    service = ServiceBibliotheque(connexion, config.cle_chiffrement_maitresse, contexte_a)
    entreprise_id = service.creer_entreprise(f"Entreprise fictive I6 — {MENTION}")
    connexion.valider()
    fiche = service.ouvrir_fiche(entreprise_id)
    connexion.valider()
    fiche_id = str(fiche["id"])

    service.saisir(
        "references_chantiers",
        "reference_chantier",
        fiche_id,
        {
            "intitule_operation": f"Chantier fictif — {MENTION}",
            "maitre_ouvrage": f"MO fictif — {MENTION}",
            "origine": "saisie_entreprise",
        },
    )
    connexion.valider()
    service.valider_fiche(
        fiche_id, relecteur_nom=f"Relecteur fictif — {MENTION}", attestation_cochee=True
    )
    connexion.valider()

    svc = ServiceVersionnement(connexion, config.cle_chiffrement_maitresse, contexte_a)
    assert svc.controler_validations(fiche_id) == [], "aucune anomalie attendue après validation"

    # Modification « discrète » du contenu, hors service (aucune révocation).
    connexion.executer(
        contexte_a,
        "UPDATE reference_chantier SET intitule_operation = %(v)s "
        "WHERE client_id = %(client_id)s AND fiche_version_id = %(fiche)s;",
        {"v": f"Chantier fictif MODIFIÉ — {MENTION}", "fiche": fiche_id},
    )
    connexion.valider()

    anomalies = svc.controler_validations(fiche_id)
    assert anomalies, "I6 aurait dû détecter une validation devenue fausse"
    assert "chang" in anomalies[0]["motif"].casefold() or "empreinte" in anomalies[0][
        "motif"
    ].casefold()

