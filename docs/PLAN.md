# PLAN — Phase 1 : cadrage technique du projet IA consultations publiques

*Écrit par l'agent `plan` le 30 septembre 2026. Board : `ia-consultations`.
Dossier de travail : `/Users/pause/Projets/ia-consultations-publiques`.*

---

## 1. Résultat visé de la phase 1

**Critère vérifiable de fin de phase :** les six fichiers de cadrage
(`docs/SPEC-MVP.md`, `docs/DATA-MODEL.md`, `docs/UI-SAISIE.md`,
`docs/CONFORMITE-COMMANDE-PUBLIQUE.md`, `docs/DONNEES-METIER-BATIMENT.md`,
`docs/PLAN-DE-TEST.md`) existent dans le dépôt, chacun écrit en français, chacun
décrivant un périmètre strictement limité au MVP (bibliothèque d'entreprise, analyse
de DCE, checklist de conformité), **et** le squelette de code sous `src/` existe avec
ses points d'entrée vides ou minimaux, **et** aucun livrable ne contient de donnée
réelle d'entreprise ni ne dépasse le périmètre de la phase 1.

Ce qui **n'est pas** un critère : que le logiciel fonctionne. La phase 1 ne livre
aucun produit fini.

---

## 2. Les lots

| # | Lot | Agent | Livrable (chemin exact) | Dépend de |
|---|---|---|---|---|
| L1 | Spécification fonctionnelle du MVP | `docs` | `docs/SPEC-MVP.md` | — |
| L2 | Modèle de données + squelette de code | `dev-back` | `docs/DATA-MODEL.md` + `src/` | — |
| L3 | Maquette fonctionnelle de l'interface de saisie | `dev-web` | `docs/UI-SAISIE.md` | — |
| L4 | Pièces exigées et mentions obligatoires | `collectivite` | `docs/CONFORMITE-COMMANDE-PUBLIQUE.md` | — |
| L5 | Éléments métier à collecter (étanchéité) | `batiment` | `docs/DONNEES-METIER-BATIMENT.md` | — |
| L6 | Plan de test de la phase 1 | `qa` | `docs/PLAN-DE-TEST.md` | L1, L2, L3 |

Aucun lot hors de cette liste : le périmètre de la phase 1 s'arrête au cadrage et aux
squelettes (voir « hors périmètre » du brief racine : pas de mémoire technique
automatique, pas de veille, pas de dépôt de pli, pas de chiffrage, pas
d'authentification multi-utilisateurs, pas de mise en production).

---

## 3. Ordre d'exécution et parallélisme

**Vague 1 — en parallèle, immédiatement :** L1, L2, L3, L4, L5.
Ces cinq lots n'ont aucune dépendance entre eux et n'écrivent pas dans les mêmes
fichiers. Ils peuvent tous démarrer en même temps.

**Vague 2 — après L1, L2 et L3 :** L6 (plan de test).
Le plan de test a besoin de la spécification, du modèle de données et de l'interface
pour savoir quoi tester. Il est chaîné par dépendance de tableau : il reste en `todo`
jusqu'à ce que L1, L2 et L3 soient terminés.

**Point de recouvrement à surveiller :** L2 (dev-back) et L5 (batiment) traitent tous
les deux des données à collecter, sous deux angles différents — L2 en structure
technique, L5 en contenu métier. Le partage est explicite : **L5 dit *quoi* collecter
pour une entreprise d'étanchéité, L2 dit *comment* le structurer**. Les deux ne doivent
pas redéfinir le même schéma ; en cas de divergence, c'est `docs/DATA-MODEL.md` qui
fait foi pour la structure.

**Ordre d'écriture des fichiers :** chaque lot écrit uniquement ses propres chemins.
Aucun lot ne modifie un fichier d'un autre lot. `README.md` et `PROJECT.md` ne sont
modifiés par personne dans cette phase.

---

## 4. Risques

| Risque | Probabilité | Impact | Parade |
|---|---|---|---|
| Un lot dépasse le périmètre de la phase 1 (rédige un mémoire technique, conçoit un dépôt de pli, chiffre) | Élevée | Moyen — le cadrage devient incohérent avec le MVP | Le hors-périmètre est recopié dans le corps de chaque tâche enfant ; `plan` arbitre à la relecture |
| Un lot invente une norme, un seuil ou une référence juridique | Moyenne | Élevé — un cadrage faux se propage jusqu'au produit | Règle inscrite dans chaque tâche : citer la source exacte, ou écrire « à vérifier » |
| Données réelles d'entreprise (bilans, CV, SIRET, IBAN) déposées dans le dépôt | Moyenne | Élevé — confidentialité, RGPD, secret des affaires | Règle « exemples fictifs signalés comme tels » dans chaque tâche ; `.gitignore` couvre déjà `data/` et les secrets |
| Divergence de structure entre L2 (modèle de données) et L5 (données métier) | Moyenne | Moyen — reprise du schéma plus tard | Arbitrage explicite écrit ci-dessus : L2 fait foi pour la structure |
| L6 (plan de test) lancé trop tôt et testant un cadrage encore mouvant | Faible (chaînage en place) | Faible — travail à refaire | Dépendance de tableau : L6 reste bloqué jusqu'à la fin de L1-L3 |
| Modèle économique et acheteur cible non tranchés, alors que la spécification en dépend | Élevée | Moyen — `docs/SPEC-MVP.md` risque de figer un choix non validé | Le lot L1 doit poser les options, pas trancher ; Anthony arbitre (questions § 5) |
| Conflit d'intérêts du porteur (agent de la collectivité / éditeur de l'outil) | Certaine (connue) | Élevé — risque juridique réel (favoritisme) | Reste **hors phase 1** : à cadrer et faire valider par un juriste avant toute commercialisation. Signalé ici pour ne pas être perdu de vue |

---

## 5. Inconnues à lever auprès d'Anthony

Ces questions ne bloquent pas le lancement de la phase 1 — les lots ont de quoi
travailler sans réponse. Elles bloquent en revanche la phase 2.

1. **Acheteur cible prioritaire** : collectivités (mairies) ou bailleurs et
   établissements publics ? Cela change la nature des pièces exigées.
2. **Un seul métier au départ** (étanchéité / bâtiment) ou outil généraliste dès le
   départ ? La réponse conditionne la partie la plus rentable de la bibliothèque (les
   références de chantiers).
3. **Modèle économique** : abonnement par entreprise, facturation à la consultation,
   ou freemium limité à l'analyse du DCE ?
4. **Portage juridique** : qui porte le projet, et comment le conflit d'intérêts du
   § 6 de `PROJECT.md` est neutralisé ? Validation par un juriste — à ne pas trancher
   en interne.
5. **Stack technique** : le squelette produit par `dev-back` doit être posé dans un
   langage donné. Anthony impose-t-il une stack (Python, Node, autre), ou le choix est-il
   laissé à l'équipe avec une proposition à valider ?
6. **Hébergement et confidentialité** : les bilans, CV et coordonnées bancaires de la
   bibliothèque seront-ils stockés en France / UE, chez quel hébergeur ? Contrainte à
   connaître avant d'écrire le modèle de données définitif.

---

## 6. Estimation

Estimée en **passes d'agent** (une passe = un tour de travail effectif sur le lot), pas
en jours-homme : la phase 1 n'a pas de calendrier fixé à ce stade.

- L1, L3, L4, L5 : 1 à 2 passes chacune. Base de l'estimation : production de cadrage
  à partir d'un dossier déjà écrit, sans dépendance externe.
- L2 : 2 à 3 passes. Plus lourd — modèle de données *et* squelette de code.
- L6 : 1 à 2 passes, mais dépend du contenu de L1-L3.

**Dépendance externe non maîtrisée :** aucune source administrative, fournisseur ou
tiers n'est requis pour la phase 1 — les lots travaillent sur des documents publics et
sur leur propre connaissance métier. C'est précisément pour éviter d'en introduire que
le lot L4 (conformité) doit citer ses sources et marquer « à vérifier » là où elles
manquent, plutôt que d'affirmer.

---

## 7. Suivi

Chaque lot est une tâche du board `ia-consultations`, liée à la tâche racine
`Phase 1 — cadrage et lancement`. Les livrables arrivent dans le dossier de travail.
`plan` relit et arbitre en fin de phase.
