# t_1c7d0532 — le texte du mémoire ne parle plus en code (critère 6)

**Agent** : `dev-back` · **Date** : 01/10/2026 · **Carte parente** : `t_ebbaac86`
**Périmètre** : `src/app/services/memoire_technique.py` (générateur du mémoire).
Les écrans (`src/app/web/`) n'ont **pas** été touchés (ils appartiennent à `dev-web`).

## Ce qui était mesuré avant

Sur `/consultations/{id}/memoire`, le texte produit par le générateur portait les codes
de nomenclature de la bibliothèque (`materiel_mise_en_oeuvre`, `engin_elevation`,
`vehicule_chantier`, `materiel_chantier`, `chef_equipe`, `conducteur_travaux`,
`responsable_qse`) et les crochets de validité (`[valide]`, `[expire]`), dans le texte
**visible** et dans l'emplacement de source **persisté puis exporté**.

## Ce qui a changé

Un seul fichier de production : `src/app/services/memoire_technique.py`.

| Point | Avant | Après |
|---|---|---|
| `libelle_source` (`moyen_materiel`, `effectif_metier`) | libellé **et** code concaténés (`Groupe d'étanchéité à air chaud materiel_mise_en_oeuvre`) | libellé métier (`designation`, `metier_libelle`) ; le code ne sert que de **repli**, et rendu lisible |
| `_phrase_element` (`effectif_metier`) | `Effectif Chef d'équipe étanchéité, chef_equipe : 4.` | `Effectif Chef d'équipe étanchéité : 4.` |
| `_phrase_element` (`moyen_materiel`) | `Moyen matériel Nacelle élévatrice (engin_elevation)` | `Moyen matériel Nacelle élévatrice (engin elevation)` |
| `_lignes_element` (pages du générateur) | valeurs de code brutes | valeurs de code rendues lisibles |
| `emplacement_source` | `bibliothèque — Moyens matériels / moyen_materiel [valide]` | `bibliothèque — Moyens matériels / Moyen matériel — validité : valide` ; `statut_validite` dit en métier (`valide`, `échéance proche`, `échéance dépassée`) |

Ajouts de code :

* `CHAMPS_CODE` — les champs `code_reference` du modèle (`categorie_code`, `metier_code`,
  `forme_juridique_code`, `effectif_source_code`, `famille_code`, `nature_travaux_code`,
  `domaine_code`, `type_assurance`, `type_attestation`, `type_document`, `propriete`,
  `statut`). Leur valeur ne sort jamais telle quelle.
* `_code_lisible()` — `materiel_mise_en_oeuvre` → « materiel mise en oeuvre »,
  `metier.etancheite` → « metier etancheite ». Une valeur qui n'est pas un code est rendue
  inchangée : **aucune valeur n'est inventée**.
* `_libelle_validite()` — traduction métier des statuts calculés.
* `_valeur_champ()` — point unique : code → lisible, sinon valeur telle quelle.

## Ce qui a été exécuté, et avec quel résultat

1. **Suite de tests du dépôt** — `.venv/bin/python -m pytest src/tests -q`
   → **265 passed, 0 échec** (259 avant cette carte ; **6 tests ajoutés** :
   `_code_lisible`, `_libelle_validite`, `libelle_source` (libellé gardé / repli sur le
   code), `emplacement_source`, et un test **de bout en bout** sur le jeu L7 qui contrôle
   texte, sources et export Markdown d'un seul tenant :
   `src/tests/test_memoire_technique.py` § « 4ter »).
2. **Application réellement servie** — `uvicorn` sur `127.0.0.1:8098`, base **jetable**
   `ia_consultations_c6demo` (jeu L7), compte de démonstration :
   * mémoire **régénéré** par `POST /consultations/{id}/memoire` (le texte est persisté :
     régénérer fait partie de la vérification) ;
   * écran `/consultations/{id}/memoire` relu, blocs repliés retirés :
     **aucun code, aucun crochet** — texte visible *et* blocs repliés
     (`docs/RAPPORTS/captures-c6/t_1c7d0532/verif-ecran-memoire.txt`) ;
   * libellés métier retrouvés : `Effectif Étancheur : 16.`,
     `Moyen matériel Nacelle élévatrice (engin elevation)`,
     `Votre source : Chef d'équipe étanchéité — Moyens humains` ;
   * **export** Markdown du mémoire persisté (lot L6) : 25 585 caractères, 5 sections,
     1 manque — aucun code, aucun crochet (`verif-export.txt`, `memoire-export.md`) ;
   * **balayage des 16 écrans** servis (script du critère 6) : plus aucune anomalie, le
     mémoire n'est plus l'écran rouge (`verif-16-ecrans.txt`).
3. **Persistance** — contrôle en base, après régénération, sur le jeu de démonstration :

   | Dossier de mémoire | Sections portant un code | Sources à code dans l'emplacement |
   |---|---|---|
   | `a7b81dbe…` (30/09 20:05, **avant** correctif) | 5 / 6 | 32 / 75 |
   | `ab182ad2…` (01/10 09:55, **après** correctif) | 0 / 5 | 0 / 69 |

   → un mémoire **déjà en base** garde son ancien texte jusqu'à régénération ; c'est bien
   le générateur qui a changé, pas les données.

## Réserves et suites

* La régénération de démonstration a créé un **nouveau** dossier dans la base jetable
  `ia_consultations_c6demo` ; l'ancien y reste (c'est la preuve du point 3). Aucune base
  partagée n'a été touchée.
* Le mot de passe du compte de démonstration de cette base jetable a été **réinitialisé
  temporairement** pour la vérification live (`scripts/jeu-de-test/reinitialiser_mot_de_passe_demo.py`
  en pose un autre à la demande) ; il n'est écrit nulle part dans le dépôt.
* Cinq URL de famille (`moyens-materiels`, `moyens-humains`, `references-chantiers`,
  `fiches-produits`, `capacites-financieres`) répondent toujours 404 sur ce jeu : réserve
  déjà consignée par `dev-web`, hors périmètre de cette carte.
* Reste à faire, hors périmètre : les **mémoires déjà générés** en production ne sont pas
  réécrits. Si Anthony veut que les dossiers existants affichent le texte corrigé, il faut
  les **régénérer** — la régénération crée un nouveau dossier, elle ne modifie pas
  l'ancien (comportement voulu par le lot L2 : on ne réécrit pas un contenu relu).
