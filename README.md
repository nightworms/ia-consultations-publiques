# IA Consultations Publiques

Assistant IA d'aide à la réponse aux consultations publiques (appels d'offres).
Le site collecte les informations d'une entreprise **une fois**, de façon structurée,
puis s'en sert pour lire un DCE et produire un dossier de réponse pré-rempli que
l'entreprise relit, corrige et signe.

> **Statut : phase 1 — cadrage et squelette.** Aucune fonctionnalité complète.
> Voir `PROJECT.md` pour le cadrage fonctionnel de référence et
> `docs/` pour les livrables de cadrage.

## Principe

Trois briques, dans cet ordre de valeur :

1. **Bibliothèque d'entreprise** — informations saisies une fois, structurées, réutilisables.
2. **Lecteur de consultation** — lecture assistée d'un DCE : pièces exigées, critères, échéances.
3. **Générateur de dossier** — squelette de réponse pré-rempli, relu et signé par l'humain.

## Ligne rouge (non négociable, contrainte de conception)

- L'IA **ne signe rien** et ne dépose rien à la place de l'entreprise.
- L'IA **n'invente aucune référence, aucun certificat, aucun chiffre**. Tout élément
  produit doit pointer vers sa source dans la bibliothèque.
- L'IA **ne fixe pas le prix**. Le chiffrage engage l'entreprise, il reste humain.
- L'IA **ne garantit aucune conformité**. Elle signale des risques.
- La **relecture humaine est un blocage technique**, pas une recommandation.

## Périmètre du MVP

- Bibliothèque d'entreprise : saisie guidée, structurée, exportable.
- Analyse d'un DCE déposé par l'utilisateur : pièces exigées + critères + date limite.
- Checklist de conformité générée automatiquement, avec ce qui manque.

**Hors périmètre MVP** : mémoire technique automatique, veille, dépôt de pli,
chiffrage, connexion aux plateformes d'achat public.

## Structure

```
ia-consultations-publiques/
├── PROJECT.md     cadrage fonctionnel de référence
├── README.md      ce fichier
├── docs/          livrables de cadrage (produits par l'agent `docs`)
├── src/           code applicatif
├── data/          données locales de travail (non versionnées)
└── scripts/       outillage
```

## Point de vigilance juridique

Le porteur du projet est agent d'une collectivité territoriale. Toute utilisation
de données ou d'influence issue de cette position expose à un risque de favoritisme
ou de prise illégale d'intérêts. Le périmètre doit rester **strictement générique et
public**. Validation par un juriste requise avant toute commercialisation.
Voir `PROJECT.md` § 6.

## Agents

Projet piloté par les agents Hermes spécialisés, via le tableau Kanban :

| Agent | Rôle sur ce projet |
|---|---|
| `plan` | découpage, ordonnancement, arbitrage |
| `dev-back` | bibliothèque d'entreprise, API, modèle de données |
| `dev-web` | interface de saisie et de restitution |
| `qa` | revue, tests, chasse aux fuites de données |
| `docs` | spécifications et documentation |
| `collectivite` | conformité aux procédures de commande publique |
| `batiment` | domaine métier de départ (étanchéité / bâtiment) |

Board Kanban : **`ia-consultations`**
