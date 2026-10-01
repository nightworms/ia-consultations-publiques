# Import guidé — remplir la bibliothèque sans saisie fastidieuse

*Mode d'emploi, en français. Concerne le lot L3 de la phase 4 du projet
`ia-consultations-publiques`. Pour Anthony, et pour toute personne qui utilise
l'outil.*

---

## 1. À quoi ça sert

Vous possédez déjà vos documents : un ancien mémoire technique, une plaquette, des
attestations d'assurance, des CV, des fiches produits. L'import guidé les lit et
vous propose, **à partir de ce qui est réellement écrit dedans**, des éléments à
ranger dans votre bibliothèque d'entreprise.

Vous ne saisissez rien champ par champ : **vous validez ou vous refusez** des
propositions. Rien n'entre dans votre bibliothèque sans votre décision, et votre
nom est enregistré avec elle.

## 2. Ce qui est accepté, ce qui est refusé

- **Formats acceptés** : `.pdf` et `.txt` — les mêmes que l'analyse de DCE.
- **Tout autre format est refusé explicitement** (`.docx`, `.xlsx`, images…), avec
  un message qui dit quoi faire : convertir le document en PDF ou en texte, puis
  recommencer. Un refus n'est jamais silencieux, et rien n'est enregistré.

## 3. Le parcours, étape par étape

1. **Déposer un document** sur l'écran d'import, en précisant la **famille visée**
   (Assurances, Certifications, Références de chantiers, Moyens humains…).
2. L'outil **extrait le texte** (page par page ; un PDF scanné passe par l'OCR si la
   reconnaissance de caractères est installée sur la machine). Le fournisseur de
   modèle ne voit **jamais** votre fichier : seulement le texte extrait.
3. L'outil affiche des **propositions sourcées**. Pour chacune, vous voyez :
   - l'**entité** visée (« Contrat d'assurance », « Certification »…),
   - les **champs** proposés avec leurs valeurs,
   - l'**emplacement** (« page 1 — entité « assurance » »),
   - l'**extrait littéral** du document qui justifie la proposition.
4. Chaque proposition reste **en attente** (`propose`). Vous **acceptez** ou vous
   **refusez**, en laissant votre nom.
5. Une proposition **acceptée** écrit un élément de bibliothèque marqué
   `origine = document_extrait` et `confiance = à vérifier`, rattaché à son document
   source. Une proposition **refusée** n'écrit rien.

## 4. La règle qui ne se négocie pas

> **Aucune proposition sans source.**

Une proposition doit citer un extrait que l'on **retrouve littéralement** dans le
texte du document. Si l'extrait invoqué n'y est pas, l'import entier est refusé, et
le dépôt est annulé : rien n'est conservé. C'est la même mécanique que l'analyse de
DCE — le contrôle de source est le même code, pas une copie.

Deux conséquences pratiques :

- un document illisible (scan sans OCR, fichier vide) ne produit **aucun** élément
  inventé : il produit zéro proposition, et on vous le dit ;
- `confiance = vérifié` n'est jamais posé par l'import. Un élément importé est
  toujours **à vérifier** jusqu'à ce que quelqu'un le relise.

## 5. « Ce qui vous manque pour être prêt à concourir »

L'outil sait dire, **famille par famille**, ce qu'il manque concrètement pour
répondre à un marché — et non un pourcentage de remplissage. Exemples :

- « Aucune référence de chantier comparable : le jury n'a rien à comparer à l'objet
  du marché. »
- « Des références existent, mais aucune ne porte de montant : la comparabilité avec
  le marché n'est pas démontrable. »
- « Contrat d'assurance « responsabilité décennale » : expire dans 40 jour(s), le
  15/11/2026. »
- « Aucun moyen humain décrit (effectif par métier, CV des profils clés). »

Chaque ligne nomme le manque **et l'action** qu'il appelle. C'est cette donnée que
l'écran de bibliothèque affiche.

## 6. Comment lire un document que l'outil peut exploiter

Le fournisseur **factice** (celui qui tourne sans réseau, pour la démonstration et
les tests) applique une règle de lecture volontairement simple. Pour qu'un document
produise des propositions, écrivez-le ainsi :

```
DOCUMENT FICTIF — DÉMONSTRATION — AUCUNE DONNÉE RÉELLE

Entité : assurance
- type_assurance : responsabilite_decennale
- assureur : Assureur Fictif SA
- numero_contrat : FICTIF-2026-001
- date_debut : 2026-01-01
- date_echeance : 2026-11-10
```

- une ligne `Entité : <nom_entite>` ouvre un bloc ;
- chaque ligne `- <champ> : <valeur>` du bloc remplit un champ ;
- les champs consécutifs forment **un seul** élément proposé ;
- hors d'un bloc d'entité, rien n'est lu ; aucun bloc, aucune proposition.

Avec un vrai fournisseur de modèle (configuré par l'administrateur derrière le même
adaptateur), la lecture n'a pas besoin de cette mise en forme : le modèle comprend le
document. La **règle de source**, elle, ne change pas.

## 7. Ce que l'import ne fait pas

- Il n'invente **aucune** valeur : ce qui n'est pas dans le document n'existe pas.
- Il ne pose **aucune** validation : la décision reste humaine et nommée.
- Il ne produit **aucun** prix, aucune conformité garantie.
- Il ne dépose aucun pli et ne signe rien.

## 8. Sous le capot (pour le développeur)

- Table `import_document` (suivi du dépôt) et `import_proposition` (propositions en
  attente de décision) — migration `src/migrations/0006_import_guide.sql`,
  réversible (`up` / `down`).
- Service d'orchestration : `src/app/services/import_guide.py`.
- Routes JSON : `src/app/api/routes_import.py` (`/api/v1/import/...`).
- Contrôle de source réutilisé : `app.services.fournisseur_modele.base.source_presente`
  et `verifier_propositions_import` (même mécanique que `verifier_propositions`).
- Isolation par client : tout passe par `storage.connexion.Connexion` et le
  `client_id` de la session. Un client ne voit jamais les imports d'un autre.
