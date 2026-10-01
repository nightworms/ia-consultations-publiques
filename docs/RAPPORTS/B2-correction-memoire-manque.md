# B2 — Correction bloquante : une section ne peut plus être produite pour un critère que la bibliothèque ne couvre pas

*Rapport du lot de correction `t_21fffbbc` (`dev-back`), 30 septembre 2026. Tout ce qui
suit a été **exécuté** ; les sorties brutes sont dans `docs/RAPPORTS/captures-B2/`.*

---

## 1. Ce qui était cassé (rappel du constat L8)

Sur le jeu L7, bibliothèque **remplie**, le mémoire produisait **6 sections et 0 manque**.
La section du critère « Expérience en toitures-terrasses **végétalisées** » (10 %) citait
quatre chantiers de toitures-terrasses **ordinaires** et deux certifications, alors
qu'`ILIKE '%végétalis%'` ne renvoyait **aucune** référence. L'écran affichait « 0 critère
sans référence dans votre bibliothèque » et l'export affirmait « Aucun manque signalé ».

Cause : la production d'une section ne dépendait que du **nombre** de sources mobilisables.
Le repli `FAMILLES_DEFAUT` — non vide dès qu'une source du lot existe — suffisait donc à
fabriquer un développement pour n'importe quel libellé.

## 2. Ce qui a changé (5 fichiers, un seul écrivain)

| Fichier | Changement |
|---|---|
| `src/app/domain/memoire_technique_genere.py` | `correspondance_pour_critere()` rend les familles **et les mots-clés qui les justifient** (`CorrespondanceCritere`, `familles_pour_critere` reste le raccourci). Nouveaux : `MOTS_VIDES`, `TERMES_GENERIQUES`, `termes_sujet()`, `couverture_sujet()` → `CouvertureSujet`, `_radical()` (singulier/pluriel), `constat_manque_sujet()`. `FAMILLES_DEFAUT` documenté : il **collecte**, il ne **produit** plus. |
| `src/app/services/memoire_technique.py` | `section_ou_manque()` ajoute un **troisième refus** après le garde-fou de source : si le sujet du critère n'est pas corroboré par les éléments cités → **manque** (constat nommant le terme absent + action). `composer_section()` accepte les sources déjà vérifiées et écrit la **trace** de correspondance dans la section. |
| `src/tests/test_memoire_technique.py` | 5 tests neufs : couverture du sujet (absente / établie), repli `FAMILLES_DEFAUT` qui ne fabrique plus, **cas L7 complet** (1 manque, 5 sections), contre-épreuve (critère couvert → section). Fixtures du **jeu L7** : `_bibliotheque_l7()` et `_ajouter_criteres_valides()`. |
| `src/tests/integration/test_memoire_ligne_rouge.py` | 1 test d'intégration : la source qui existe mais ne parle pas du critère ne produit **aucune** ligne `memoire_section` ni `memoire_section_source`, seulement un `memoire_manque`. |
| `docs/MEMOIRE-TECHNIQUE.md` | § 1 « deux conditions, pas une », § 3 étapes 6-7, **§ 4bis** (règle, trace, exemple, cas limite), § 9 limite 2. |

**Rien n'a été affaibli** : le garde-fou de source (`source_presente`) est réutilisé tel
quel, aucune section sans `memoire_section_source` du même `client_id`, aucune phrase non
rattachable, aucune conformité promise, aucun prix.

## 3. Ce qui a été exécuté, et ce que ça a donné

### 3.1 Serveur réel, base migrée, jeu L7 — le défaut ne se reproduit plus

Application lancée sur une base dédiée (`ia_consultations_b2demo`, migrations 0001→0006),
jeu de démonstration L7 chargé, fournisseur `factice`, DCE fictif déposé par le parcours
(`DCE-FICTIF-DEMO-2026-ETN-001`), ses **6 critères validés nommément**, puis génération du
mémoire. Sortie brute : `captures-B2/verif-memoire-l7-b2.txt`.

```
 nb_manques
------------
          1
```

| ordre | critère | poids | longueur | sources |
|---|---|---|---|---|
| 0 | Étanchéité de toitures-terrasses sur bâtiments scolaires | 40.00 | 5317 | 19 |
| 1 | Traitement des relevés d'étanchéité et des points singuliers | 20.00 | 3901 | 19 |
| 2 | Exécution en site occupé et planning par phases | 15.00 | 2566 | 10 |
| 3 | Moyens humains et matériels affectés au marché | 10.00 | 1570 | 11 |
| 5 | Délai d'exécution et engagement de planning | 5.00 | 1829 | 10 |

Le critère à 10 % sort en **manque** :

> **Expérience en toitures-terrasses végétalisées — 10 %**
> *Constat* : « Aucun élément de votre bibliothèque ne porte « végétalisées » : le sujet du
> critère n'est pas couvert. Le mémoire ne peut pas présenter une expérience ou un moyen
> que votre bibliothèque ne démontre pas. »
> *Pour renforcer ce critère* : « Ajouter un chantier comparable (nature de travaux, maître
> d'ouvrage, montant € HT, année de réception, difficulté traitée). »

Contrôles complémentaires, mêmes preuves brutes :

- `SELECT count(*) … ILIKE '%végétalis%'` → **0** (la contre-épreuve du constat L8) ;
- **0** section sans source (`LEFT JOIN memoire_section_source`) ;
- `position('Correspondance établie' IN contenu) > 0` → **vrai pour les 5 sections**.

### 3.2 Captures d'écran

| Fichier | Ce qu'on y voit |
|---|---|
| `captures-B2/01-memoire-manque-vegetalisees-10-desktop.png` | l'écran mémoire : « Ce qui manque, et ce que vous pouvez faire » → **Expérience en toitures-terrasses végétalisées — 10 %**, son constat, l'action « Ajouter un chantier comparable (…) » et le bouton « Ajouter une information — Références de chantiers » |
| `captures-B2/02-memoire-avancement-5-sections-desktop.png` | l'en-tête : **5 sections rédigées**, **1 critère sans référence dans votre bibliothèque** |
| `captures-B2/03-section-40-correspondance-tracee-desktop.png` | la section à 40 % avec sa **trace** : « Correspondance établie : le sujet du critère est corroboré par les éléments cités (termes retrouvés dans votre bibliothèque : « Étanchéité », « toitures », « terrasses », « bâtiments », « scolaires »). » |

L'écran est à `dev-web` et **n'a eu besoin d'aucune modification** : il affichait déjà les
manques avec leur action, il ne lui manquait que la donnée. **Aucune carte `dev-web` n'est
donc créée pour ce défaut.**

### 3.3 Tests

```
$ cd src && TEST_DATABASE_URL=…/ia_consultations_devback ../.venv/bin/python -m pytest -q
259 passed, 1 warning in 18.40s
```

(preuve brute : `captures-B2/pytest-suite-complete.txt` ; sortie ciblée :
`captures-B2/pytest-memoire-cible.txt` — `test_memoire_technique.py` (20),
`integration/test_memoire_ligne_rouge.py` (11), `test_export_memoire.py` (15) : 46 verts.)

Les 6 tests ajoutés couvrent exactement le cas de la carte :

1. `test_couverture_sujet_distingue_le_sujet_de_la_presence_d_un_element`
2. `test_couverture_sujet_etablie_quand_la_bibliotheque_porte_le_sujet`
3. `test_repli_familles_defaut_ne_fabrique_plus_une_section`
4. `test_critere_du_jeu_l7_non_couvert_produit_un_manque_et_cinq_sections` (**1 manque, 5 sections**)
5. `test_critere_du_jeu_l7_couvert_par_la_bibliotheque_produit_une_section`
6. `test_la_source_qui_ne_parle_pas_du_critere_ne_produit_pas_de_section` (intégration, en base)

## 4. Vérifié / supposé — la part d'honnêteté

**Vérifié par exécution** : le cas L7 de bout en bout sur serveur réel (5 sections, 1 manque
nommant « végétalisées », action présente, écrit en base) ; la non-régression (suite
complète verte) ; les invariants (aucune section sans source, trace de correspondance
écrite, aucun prix, aucune conformité) ; le fait que l'écran affiche le manque sans
changement côté `dev-web`.

**Non couvert / supposé** :

- Le contrôle de couverture est **lexical** (mots entiers, singulier/pluriel repliés). Deux
  formulations sans mot commun (« toiture végétalisée » vs « toiture verte ») donnent un
  **manque**. C'est le sens prudent, mais c'est une **limite**, écrite au § 4bis du
  document de référence. Aucun test ne mesure le taux de faux manques sur un corpus réel :
  le jeu L7 n'a qu'un cas.
- Le fournisseur de modèle réel (`ue`) n'est pas appelé : `MODELE_FOURNISSEUR=factice`.
- Le vocabulaire de `TERMES_GENERIQUES`/`MOTS_VIDES` est **curé à la main** pour les
  libellés rencontrés (fixture de test + jeu L7). Un libellé inhabituel peut produire un
  manque inattendu ; le constat nomme alors le terme concerné, ce qui rend le cas
  diagnosticable.
- La suite complète compte **259** tests (244 lors de la vérification L8) : l'écart vient
  des lots voisins en cours dans l'arbre partagé (correctif B1 côté import guidé, correctif
  du critère 6 côté `dev-web`), pas de ce lot, qui en ajoute 6.
- Les deux échecs observés d'abord (`test_provisionnement`, `test_provisionnement_parcours`)
  étaient dus à la **base de tests partagée** (`ia_consultations_test`) utilisée
  simultanément par un autre agent (interblocage PostgreSQL, messages 404 d'API écrasés par
  un état transitoire). Rejoués sur une base dédiée, ils passent. **Non imputables à ce
  lot** — mais à surveiller : deux agents qui lancent la suite en même temps sur la même
  base se gênent.

## 5. Reste à faire

- Relire `scripts/jeu-de-test/DEMONSTRATION.md` § 4 (défaut m6 de la vérification L8) : ce
  fichier annonçait le manque du critère à 10 % ; **il est désormais conforme au
  comportement réel**, mais il appartient à `docs`, pas à ce lot.
- Décider si `FAMILLES_DEFAUT` doit encore exister : aujourd'hui il ne sert plus qu'à
  collecter des candidats pour un libellé inconnu, ce qui reste utile (c'est lui qui permet
  de trouver les éléments que le constat de manque pourra citer). À trancher en phase de
  relecture si le taux de faux manques se révèle gênant.
