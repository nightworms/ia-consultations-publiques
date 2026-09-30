# Décisions de cadrage

*Réponses d'Anthony aux questions ouvertes du plan de phase 1, recueillies le
30 septembre 2026. Ce document fait foi : en cas de contradiction avec
`PROJECT.md`, c'est celui-ci qui est à jour.*

---

## D1 — Client cible

**Entreprises du bâtiment souhaitant répondre à des consultations publiques.**

Le client n'est pas l'acheteur public. L'acheteur public est la source des
consultations, pas l'utilisateur du produit. L'utilisateur est l'entreprise
candidate.

Conséquence pour la conception : tout ce qui concerne les besoins de l'acheteur
(profil d'acheteur, portail côté mairie) est **hors périmètre**. Le produit est
un outil d'entreprise.

## D2 — Périmètre métier

**Généraliste dès le départ**, adapté aux offres proposées.

Conséquence : la bibliothèque d'entreprise ne peut pas présumer d'un métier. Le
modèle de données doit rester métier-agnostique dans sa structure, avec des
nomenclatures et des champs de référence extensibles. Le contenu métier spécifique
(éléments propres à l'étanchéité, au gros œuvre, à l'électricité, à la menuiserie…)
est un **jeu de données de référence**, pas une hypothèse de schéma.

Le travail de l'agent `batiment` reste valable comme **premier jeu de référence**,
pas comme structure imposée.

## D3 — Modèle économique

**Abonnement mensuel** *ou* **facturation ponctuelle d'un projet déposé**.

Les deux, donc : un socle fonctionnel accessible par abonnement, et une
facturation à l'acte pour un dossier déposé. Le produit doit savoir compter les
deux et rattacher un dossier à sa facturation.

Hors périmètre phase 1/2 : l'implémentation du paiement lui-même. Ce qui est
requis maintenant, c'est que le modèle de données **prévoie** les deux modes.

## D4 — Portage juridique et conflit d'intérêts

**Validation par un juriste à la fin du projet.**

Décision d'Anthony : ne pas traiter le sujet maintenant, le faire expertiser quand
le produit sera abouti.

Conséquence : le risque reste ouvert et documenté (`PROJECT.md` § 6, `docs/PLAN.md`
risques). Il **bloque toute commercialisation**, pas le développement. À reaffirmer
à chaque fin de phase pour ne pas le perdre de vue. La séparation des casquettes
reste une règle de conduite immédiate : aucune donnée, aucun document et aucune
influence issue de la collectivité ne doit entrer dans ce projet.

## D5 — Stack technique

**L'équipe propose, Anthony valide.**

Conséquence : la phase 2 produit une **proposition de stack documentée**, avec ses
justifications et ses alternatives écartées. Aucune implémentation structurante
avant validation. Un document `docs/STACK-PROPOSAL.md` est requis, lisible par un
non-spécialiste.

## D6 — Hébergement et confidentialité

**Serveur sécurisé, chiffré, hébergé en France** (fournisseur type OVH ou
équivalent). **Seul le client a accès à ses données.**

C'est la contrainte la plus structurante du projet, et elle contient une tension
technique qu'il faut traiter en transparence plutôt que promettre à la légère :

> Le service doit **lire** les documents du client (DCE, bilans, références, CV)
> pour produire une analyse et un dossier. Or « seul le client a accès à ses
> données » signifie, au sens strict, que le serveur ne peut pas les déchiffrer.
> Les deux ne peuvent pas être vrais simultanément sans un choix explicite.

Trois familles de solutions existent, avec des compromis réels :

- **Chiffrement côté client + traitement local** — le serveur ne voit jamais les
  documents en clair. La confidentialité est maximale, mais le service perd la
  capacité de traiter côté serveur : l'analyse tourne sur le poste du client.
- **Chiffrement au repos + isolation stricte côté serveur** — le serveur détient
  la clé, les données sont chiffrées sur disque et cloisonnées par client, mais
  le personnel technique a un accès théorique. C'est ce que fait la majorité des
  SaaS. « Seul le client a accès » y est **faux au sens strict**.
- **Chiffrement avec clés détenues par le client et déverrouillage à la demande**
  — compromis intermédiaire : le serveur reçoit une clé de session uniquement
  pendant le traitement, ne la stocke pas.

**Exigence pour la phase 2 :** poser les trois options, leurs compromis, et une
recommandation argumentée — **sans promettre une confidentialité que
l'architecture ne peut pas tenir.** Si la réponse honnête est « le serveur devra
voir les documents pendant le traitement », il faut le dire à Anthony maintenant,
pas après la commercialisation.

Contraintes fermes : hébergement en France, chiffrement au repos, cloisonnement
strict entre clients, aucune donnée client dans un entraînement de modèle.

---

## Ce que ces décisions changent dans le projet

| Sujet | Avant | Après décision |
|---|---|---|
| Cible | indécis (collectivités ou bailleurs) | **entreprises du bâtiment** (D1) |
| Métier | un seul métier ou généraliste | **généraliste**, jeux de référence extensibles (D2) |
| Modèle économique | non tranché, risquait de figer la spec | **abonnement + à l'acte**, à prévoir dans le modèle (D3) |
| Juridique | à cadrer en priorité | **expertise en fin de projet**, risque documenté et bloquant pour la commercialisation (D4) |
| Stack | inconnue | **proposition de l'équipe, validation d'Anthony** (D5) |
| Hébergement | inconnu, bloquait le modèle de données | **France, chiffré, isolation client** — tension à trancher (D6) |

D2 et D6 invalident partiellement l'hypothèse mono-métier qui sous-tendait le travail
de l'agent `batiment` : son livrable reste la **première** nomenclature de référence,
pas la structure du produit.

---

# Décisions de phase 3

*Recueillies le 30 septembre 2026, à l'issue de la phase 2.*

## D7 — Option de confidentialité

**Option B retenue** : chiffrement au repos, cloisonnement strict côté serveur,
hébergement en France, **formulation publique honnête**.

Conséquence assumée : le serveur peut lire les documents pendant le traitement.
La phrase « seul le client a accès à ses données » n'est **pas** reprise dans la
communication du produit. Elle ne serait vraie qu'en option A, qui n'est pas retenue.

Une trajectoire vers l'option C est à prévoir, sans être construite maintenant
(voir `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 9).

## D8 — Fournisseur du modèle d'IA

**Décision prise par délégation** (Anthony : « décide pour moi et avance »).

**Fournisseur établi en France ou dans l'UE uniquement.** Cibles : Mistral AI,
OVHcloud AI Endpoints, ou un modèle ouvert auto-hébergé sur le même serveur.

Raison : c'est le seul moyen de rendre « hébergé en France » vrai **de bout en bout**.
Avec un fournisseur hors UE, le document du client quitte l'Union, et la promesse
d'hébergement français devient fausse au sens strict — exactement ce que D7 interdit.

Exigence technique qui en découle : la couche d'appel au modèle doit être **abstraite**
(un adaptateur), pour pouvoir changer de fournisseur sans réécrire le produit.

## D9 — Budget mensuel cible

**150 à 500 € par mois**, hébergement et consommation du modèle compris.

Conséquence : le socle technique peut viser une **base de données managée en France**
plutôt que SQLite, sans que le coût devienne un obstacle. Le budget laisse aussi de la
marge pour la consommation du modèle, qui est la vraie dépense variable.

## D10 — Matériau de test

**Aucun DCE réel disponible à ce jour.** Anthony n'en a pas fourni.

Conséquence : les tests d'analyse de DCE se feront sur des **documents fictifs et
signalés comme tels**, ou sur des documents publics librement diffusés si l'occasion
se présente. Aucun document interne de collectivité ne doit entrer dans le projet.

## Conséquence sur la stack (décision d'architecture)

Au vu de D7 (isolation stricte entre clients) et D9 (budget disponible), la cible
retenue est :

- **Python 3.12 + FastAPI** — confirmé par la phase 1 et la proposition de stack ;
- **PostgreSQL managé en France** (Scaleway ou OVHcloud) plutôt que SQLite —
  parce que l'isolation stricte par client et le chiffrement des champs sensibles
  sont plus solides sur PostgreSQL (cloisonnement au niveau des lignes, chiffrement
  applicatif) que sur un fichier SQLite filtré côté application ;
- **chiffrement au repos du volume et chiffrement applicatif des champs sensibles**
  (bilans, IBAN, CV) ;
- **abstraction du fournisseur de modèle** (D8) ;
- migrations SQL numérotées et réversibles, portables (D-C5 conservé).

Cette décision reste **révisable** : elle est écrite ici pour être contestée, pas pour
être subie.
