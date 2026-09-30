# Cadrage — site IA d'assistance aux réponses aux consultations publiques

*Document de référence du projet. Créé le 30 septembre 2026. Rien n'est lancé
côté fonctionnement — ce document décrit l'intention, pas un état d'avancement.*

## 1. Le problème

Répondre à une consultation publique coûte un temps considérable à une entreprise,
pour un taux de réussite faible. Chaque dossier demande : lire un DCE de plusieurs
dizaines de pages, comprendre les critères d'attribution, réunir les pièces
administratives, rédiger un mémoire technique **réécrit à chaque fois**, et vérifier
la conformité avant remise.

La matière première existe déjà dans l'entreprise — références de chantiers, moyens,
certifications, fiches produits, CV — mais elle est éparpillée et jamais réutilisée
proprement. C'est là que se perd le temps, et c'est là que le taux de réponse s'effondre.

## 2. Le principe

Trois briques :

- **La bibliothèque d'entreprise** — les informations de l'entreprise, saisies une
  fois, structurées, réutilisables à l'infini.
- **Le lecteur de consultation** — lecture assistée du DCE : pièces exigées, critères,
  pondérations, contraintes, dates limites.
- **Le générateur de dossier** — production d'un squelette de réponse pré-rempli, que
  l'entreprise relit, corrige et signe.

## 3. Les informations à collecter sur l'entreprise

Une fiche entreprise vivante, mise à jour et versionnée :

- **Identité** : raison sociale, SIRET, forme juridique, effectif, adresse, coordonnées
  bancaires, représentant légal.
- **Capacités financières** : chiffre d'affaires des trois derniers exercices, bilans,
  attestations fiscales et sociales, capacité de production.
- **Assurances** : décennale, responsabilité civile, dates et montants de garantie.
- **Certifications et qualifications** : Qualibat, RGE, MASE, ISO — avec échéances.
- **Références de chantiers** : maître d'ouvrage, montant, année, description, nature
  des travaux, durée, photos. *Le poste le plus rentable : c'est ce qui nourrit le
  mémoire technique.*
- **Moyens humains** : organigramme, effectifs par métier, CV des profils clés.
- **Moyens matériels** : parc, engins, échafaudages, outillage spécifique.
- **Fiches techniques produits** : fournisseurs, références, certificats, avis techniques.
- **Mémoire technique type** : réponses déjà rédigées et acceptées, découpées par
  chapitre, réutilisables.

## 4. Le parcours de bout en bout

1. **Veille** — détection des consultations correspondant au profil (métier, zone
   géographique, montant).
2. **Analyse** — lecture du DCE, extraction des critères, de la grille de notation et
   de la liste des pièces exigées.
3. **Pré-sélection** — score de pertinence : ai-je le droit de concourir, ai-je les
   références et les capacités ? Ne pas répondre est aussi une bonne décision.
4. **Assemblage** — pièces administratives tirées de la bibliothèque, mémoire technique
   pré-rempli à partir des références les plus proches.
5. **Contrôle** — vérification automatique de la checklist : pièce manquante, date
   dépassée, incohérence de montant ou d'unité.
6. **Relecture et signature** — l'entreprise valide, corrige, signe. Le dossier part.

## 5. Ce que l'IA fait — et ce qu'elle ne fait pas

**Elle fait** : lire vite, extraire, classer, proposer un squelette, pré-remplir,
repérer une pièce manquante, signaler un écart.

**Elle ne fait pas** — ligne rouge à tenir techniquement, pas seulement moralement :

- Elle ne **signe rien** et ne dépose rien à la place de l'entreprise.
- Elle n'invente **aucune référence, aucun certificat, aucun chiffre**. Tout élément
  produit doit pointer vers la source dans la bibliothèque.
- Elle ne fixe pas le prix. Le chiffrage engage l'entreprise, il reste humain.
- Elle ne promet aucune conformité. Elle signale des risques, elle ne garantit rien.

## 6. Points de vigilance

- **Dossier engageant** : une réponse déposée est juridiquement contraignante. Un
  document généré qui contient une erreur expose l'entreprise. La relecture humaine
  n'est pas optionnelle — elle doit être un blocage technique dans le produit.
- **Confidentialité et RGPD** : la bibliothèque contient des bilans, des CV, des
  données bancaires. Chiffrement au repos, cloisonnement par entreprise, aucune donnée
  client dans un modèle d'entraînement.
- **Secret des affaires et égalité des candidats** : un outil qui tourne sur des DCE en
  cours ne doit jamais croiser des informations entre candidats, ni laisser fuiter
  un prix.
- **Conflit d'intérêts — à cadrer en priorité.** Le porteur du projet est agent de la
  collectivité (Mairie de Saint-Denis) *et* conçoit un outil destiné aux entreprises
  candidates. Le risque juridique est réel (favoritisme, prise illégale d'intérêts) si
  l'outil touche, de près ou de loin, une procédure sur laquelle il exerce une
  responsabilité. À clarifier avant toute commercialisation : périmètre strictement
  générique et public, aucune donnée ni influence issue de la collectivité, séparation
  nette des casquettes. À faire valider par un juriste — pas à trancher seul.

## 7. Premier livrable (MVP)

- La **bibliothèque d'entreprise** — saisie guidée, structurée, exportable.
- L'**analyse d'un DCE** déposé par l'utilisateur : liste des pièces exigées +
  critères + date limite.
- La **checklist de conformité** générée automatiquement, avec ce qui manque.

Ni mémoire technique automatique, ni veille, ni dépôt : le MVP prouve la valeur en
supprimant les oublis et les relectures, pas en écrivant à la place de l'entreprise.

## 8. Décisions à prendre

- Quel acheteur public viser en premier : collectivités (mairies) ou bailleurs et
  établissements publics ?
- Un seul métier au départ (étanchéité / bâtiment) ou un outil généraliste ?
- Modèle économique : abonnement par entreprise, facturation à la consultation, ou
  offre freemium limitée à l'analyse ?
- Qui porte le projet juridiquement — et comment le conflit d'intérêts du point 6
  est neutralisé ?
