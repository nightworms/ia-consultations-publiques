# Déploiement en France — procédure de mise en service

*Lot L7, phase 3. Rédigé le 30 septembre 2026.*

## 0. Statut de ce document, et ce qui n'a **pas** été fait

**Rien n'a été provisionné.** Aucun compte n'a été ouvert, aucun service n'a été
commandé, aucune dépense n'a été engagée, aucun port n'a été ouvert sur Internet,
aucun nom de domaine n'a été réservé, aucun DNS n'a été modifié. Ce document est
une **procédure** : elle décrit ce qu'il faudra faire le jour où Anthony donnera
un feu vert explicite. Elle n'est pas un compte rendu de déploiement.

Ce qui a réellement été exécuté pendant ce lot est décrit dans
`docs/RAPPORTS/L7-deploiement.md` : les deux scripts de sauvegarde et de
restauration, lancés sur la **base PostgreSQL locale** de la machine de
développement. C'est tout. Aucun serveur distant n'a été touché.

**Région française retenue : Scaleway `fr-par` (Paris).** C'est la seule région
d'hébergement cible nommée dans ce document ; les alternatives sont en § 2.

### Ce que ce document n'est pas

- Ce n'est pas une garantie de conformité. Aucune conformité RGPD, SecNumCloud ou
  autre n'est affirmée ici : les questions juridiques sont listées en § 11 et
  **restent à la charge d'un juriste**.
- Ce n'est pas une promesse de confidentialité que l'architecture ne tient pas.
  La formulation publique autorisée est en § 4 ; celle interdite aussi.
- Ce n'est pas un devis. Les prix cités sont sourcés, datés et marqués
  **« à revérifier »** (§ 10). Là où je n'ai pas pu vérifier un prix, je l'écris
  plutôt que de l'estimer.

---

## 1. Ce qu'on déploie

Trois briques, plus leur chaîne de sauvegarde :

| Brique | Rôle | Où |
|---|---|---|
| **Application** (Python 3.12 + FastAPI + uvicorn) | sert l'interface web et l'API | instance applicative, région `fr-par` |
| **Base PostgreSQL managée** | données du produit, cloisonnées par `client_id` | service managé, région `fr-par` |
| **Stockage des pièces** | fichiers déposés, chiffrés applicativement | volume attaché à l'instance, région `fr-par` |
| **Sauvegardes** | base + fichiers, chiffrées | objet de stockage, **région française**, hors du serveur |
| **Fournisseur de modèle** | analyse de DCE (brique B) | France ou UE **uniquement** (D8) |

Le point à ne pas rater : **les sauvegardes et la réplication comptent dans la
région.** Une base à Paris et une sauvegarde à Amsterdam, c'est un hébergement
hors de France qui ne dit pas son nom
(`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 8.1).

### 1.1 Schéma

```
                        Internet
                           │  HTTPS (443) — seul port ouvert
                           ▼
        ┌──────────────────────────────────────────────┐
        │  Scaleway fr-par (Paris)                     │
        │                                              │
        │  ┌────────────────────────┐                  │
        │  │ Instance applicative   │                  │
        │  │  uvicorn / FastAPI     │                  │
        │  │  HOTE_API=0.0.0.0      │                  │
        │  │  port 8000 en local    │                  │
        │  └───────┬────────────────┘                  │
        │          │  réseau privé (pas d'IP publique) │
        │          ▼                                   │
        │  ┌────────────────────────┐                  │
        │  │ PostgreSQL managé      │  réplication     │
        │  │  chiffré au repos      │──────┐           │
        │  └────────────────────────┘      │           │
        │                                  ▼           │
        │                        ┌──────────────────┐  │
        │                        │ nœud de secours  │  │
        │                        │ (même région)    │  │
        │                        └──────────────────┘  │
        │                                              │
        │  Volume des pièces (chiffré au repos)        │
        └──────────────────────────────────────────────┘
                           │
                           │  sauvegardes chiffrées (hors serveur)
                           ▼
              Stockage objet — région française
```

Puis, **hors du serveur applicatif** mais dans l'UE/France (D8), l'appel au
fournisseur de modèle — c'est le maillon décrit en § 4.

---

## 2. La région : `fr-par` (Paris), et pourquoi

**Région retenue : Scaleway `fr-par` (Paris)**, zones `fr-par-1`, `fr-par-2`,
`fr-par-3`.

Trois raisons, dans l'ordre d'importance :

1. **Le prix est public et vérifiable.** Les tarifs Scaleway des bases managées
   sont publiés, en euros, hors taxes (§ 10) : ils tiennent dans le budget cible
   de 150 à 500 €/mois (D9) sans négociation ni devis. C'est le seul des deux
   fournisseurs pour lequel j'ai pu **lire un prix** au lieu de l'estimer.
2. **Trois zones de disponibilité en France.** Paris offre trois zones : une
   réplication intra-région est possible sans sortir de France, ce qui est
   exactement ce que demande l'exigence « sauvegardes et réplication en région
   française ».
3. **Rien n'oblige à mélanger les fournisseurs.** Le fournisseur de modèle peut
   être Mistral AI ou un modèle ouvert auto-hébergé (D8) : la base n'a pas besoin
   d'être chez le même prestataire que le modèle.

### 2.1 Alternatives écartées, et pourquoi

| Option | Verdict | Motif |
|---|---|---|
| **OVHcloud `eu-west-gra` (Gravelines)** | **retenue en second choix** | Région française valide ; à préférer **si** le fournisseur de modèle est OVHcloud AI Endpoints (servi depuis Gravelines, `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 3), car on réduit alors le nombre de sous-traitants. Écartée ici parce que je n'ai pas pu lire un prix public de base managée OVHcloud depuis les pages accessibles (§ 10) : la décision de prix serait un devis, pas un fait. |
| **OVHcloud `eu-west-par` (Paris)** | écartée pour l'instant | Même raison de prix non vérifié. Géographiquement équivalente à `fr-par`. |
| Scaleway `nl-ams` (Amsterdam), `pl-waw` (Varsovie), `it-mil` (Milan) | **hors sujet** | UE, mais **hors France** : contredit D6 et D7. C'est le piège classique — la même offre, mal configurée, sort de France. |
| OVHcloud `eu-west-rbx`, `eu-west-sbg` | recevables | Régions françaises. Écartées pour les mêmes raisons de prix que Gravelines. |
| Tout hébergeur hors UE | **exclu** | Contredit D6, D7 et D8. |

**Piège à retenir :** la région se choisit **à la création du service** et se
vérifie **après** création, dans l'inventaire, pas seulement dans le panier. Un
service créé par défaut atterrit parfois ailleurs.

---

## 3. Chiffrement

Trois couches distinctes. Les confondre est l'erreur la plus fréquente.

### 3.1 Chiffrement au repos (disque, base, volume)

- **Volumes et base managée** : chiffrés au repos par l'hébergeur. Le **point
  honnête** : dans ce cas c'est **l'hébergeur** qui détient la clé de disque, pas
  nous (`docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 8.2). C'est acceptable, mais
  cela doit être écrit et non présenté comme un chiffrement dont nous seuls
  aurions la clé.
- **À vérifier au moment du provisionnement** : que le chiffrement au repos est
  bien activé sur la base, le volume et le stockage de sauvegardes — et pas
  seulement sur le volume de l'instance.

### 3.2 Chiffrement applicatif des champs sensibles

Décidé en annexe A § A6 et **implémenté** (L1) : AES-256-GCM via `cryptography`,
une **clé maîtresse** lue dans l'environnement, une **clé de données dérivée par
`client_id`** (HKDF, sel = `client_id`). Le chiffrement est **par client, jamais
global**. Champs concernés : IBAN, BIC, pièces RIB, SIRET, TVA, identité du
représentant légal, montants et pièces des exercices, attestations, contacts et
montants des références, CV, et les fichiers de `document` marqués
`sensibilite = confidentiel`.

C'est **ce** chiffrement qui a une valeur de confidentialité réelle : il est fait
par l'application, avec une clé que l'hébergeur ne détient pas. Sa limite est en
§ 4.

### 3.3 Chiffrement des sauvegardes

Assuré par `scripts/sauvegarde.sh` : AES-256-CBC, dérivation PBKDF2-HMAC-SHA256
(200 000 itérations), sel aléatoire par archive. La clé vit **hors dépôt**,
dans un fichier à permissions 600 ; **aucune sauvegarde non chiffrée n'est
produite** — le script s'arrête s'il ne trouve pas la clé.

**Limite assumée et documentée** : `openssl enc` n'authentifie pas le chiffré. La
détection d'altération repose sur une empreinte SHA-256 de chaque archive,
vérifiée **avant** tout déchiffrement. Cela couvre la corruption et l'altération
accidentelle ; cela ne couvre pas un adversaire capable de réécrire l'archive
*et* son empreinte. Alternatives écartées en § 13.

---

## 4. Le maillon du fournisseur de modèle, et la formulation publique

C'est le point dur du projet, tranché en D7 (option B). Rappel sans détour :

> Le service **lit** les documents pendant le traitement. Le serveur peut donc
> lire les documents du client pendant qu'il les analyse.

**Exigences fermes :**

- Fournisseur de modèle **établi en France ou dans l'UE** (D8) : Mistral AI,
  OVHcloud AI Endpoints, ou un modèle ouvert auto-hébergé sur le serveur.
- Couche d'appel **abstraite** (annexe A § A7), pour changer de fournisseur sans
  réécrire le produit.
- Aucune donnée client dans un entraînement de modèle : c'est une **exigence
  contractuelle** (DPA + clause de non-entraînement + rétention), jamais vraie
  par défaut (§ 11).

**Interdit d'écrire**, dans la documentation comme dans la communication :

> « Seul le client a accès à ses données. »

Cette phrase n'est vraie qu'en option A, qui n'est pas retenue. Utiliser la
formulation de `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 10, qui dit
explicitement que le service et son fournisseur de modèle **lisent les documents
pendant le traitement**.

---

## 5. Cloisonnement entre clients

La clé de cloisonnement est **`client_id`** (annexe A § A1), jamais
`entreprise_id`. Trois niveaux à tenir, dans cet ordre :

1. **Données** : `client_id` est présent sur **toute** entité de contenu, y
   compris quand il serait déductible par jointure. Toute requête est filtrée par
   `client_id`. Les deux points d'entrée SQL hors contexte client sont nommés et
   bornés (décision L1).
2. **Fichiers** : préfixe de chemin par client, aucun fichier partagé entre deux
   clients, aucun nom de fichier utilisateur utilisé tel quel.
3. **Accès** : une identité technique par client pour les traitements, aucun
   compte d'administration partagé entre clients, **journalisation des accès**
   (§ 6).

Le cloisonnement est **démontré par test**, pas affirmé : L1 a produit
`test_lecture_impossible_des_donnees_d_un_autre_client` et
`test_falsifier_client_id_est_sans_effet`, et L8 est chargé de chercher à les
faire échouer sur du code plus complet.

---

## 6. Journalisation des accès

À activer **avant** la mise en service. Contenu minimal, à conserver **hors du
serveur applicatif** (pour qu'un incident sur le serveur ne détruise pas la
preuve) :

| Événement | Champs à journaliser |
|---|---|
| Authentification | horodatage, identifiant, `client_id`, résultat (succès/échec), adresse IP — **jamais** le mot de passe ni le cookie |
| Accès à un document | horodatage, `client_id`, identifiant de document, utilisateur, action (lecture, dépôt, suppression) |
| Appel au fournisseur de modèle | horodatage, fournisseur, modèle, identifiant de traitement — **jamais** le contenu envoyé |
| Action d'administration | horodatage, opérateur, nature de l'action, cible |
| Sauvegarde et restauration | horodatage, répertoire de sauvegarde, résultat, empreintes |

Deux règles : **aucune donnée cliente dans les journaux** (un journal est un
fichier non chiffré qui vit longtemps — c'est le point de fuite classique), et
**la durée de conservation des journaux se décide** (§ 11) au lieu de croître
sans fin.

---

## 7. Variables d'environnement à définir

**Noms uniquement. Aucune valeur dans ce document, aucune valeur dans le dépôt.**
Les secrets se créent sur le serveur et ne quittent jamais le serveur (sauf la
clé de sauvegarde, conservée hors du serveur dans un coffre).

### 7.1 Application (lues par `src/app/config.py`)

| Variable | Obligatoire | Rôle |
|---|---|---|
| `DATABASE_URL` | **oui** | chaîne de connexion PostgreSQL managée (TLS exigé en production) |
| `CLE_CHIFFREMENT_MAITRESSE` | **oui** | clé maîtresse AES-256, 32 octets en base64 ; sert à dériver les clés par `client_id` |
| `CLE_SESSION` | **oui** | secret de signature du cookie de session |
| `HOTE_API` | non | `0.0.0.0` derrière le proxy en production (défaut local : `127.0.0.1`) |
| `PORT_API` | non | port d'écoute d'uvicorn (défaut 8000) |
| `REPERTOIRE_DOCUMENTS` | non | répertoire des pièces, **hors dépôt** |
| `DUREE_SESSION_SECONDES` | non | durée de vie d'une session |

### 7.2 Fournisseur de modèle (annexe A § A7)

| Variable | Rôle |
|---|---|
| `MODELE_FOURNISSEUR` | sélection de l'adaptateur (`factice`, `ue`, …) |
| `MODELE_CLE_API` | clé du fournisseur France/UE — **créée sur le serveur, jamais dans le dépôt** |
| `MODELE_URL_BASE` | adresse du fournisseur |
| `MODELE_NOM` | modèle employé |

### 7.3 Sauvegarde et restauration (scripts L7)

| Variable | Rôle | Défaut |
|---|---|---|
| `SAUVEGARDE_REPERTOIRE` | répertoire de sauvegarde, **hors dépôt** | `$HOME/sauvegardes-ia-consultations` |
| `SAUVEGARDE_CLE_FICHIER` | fichier contenant la clé de sauvegarde, **hors dépôt**, permissions 600 | `$HOME/.config/ia-consultations/cle-sauvegarde` |
| `RESTAURATION_REPERTOIRE` | répertoire de restauration des fichiers (en clair), **hors dépôt** | `$HOME/restauration-ia-consultations` |

**Règles tenues par les scripts eux-mêmes** : la clé et le répertoire de
sauvegarde hors du dépôt sont **vérifiés**, pas simplement recommandés. Un chemin
qui tombe dans le dépôt est refusé, et les permissions de la clé doivent être
`600`.

---

## 8. Sauvegarde et restauration

### 8.1 Ce que font les scripts livrés

```
scripts/sauvegarde.sh   [--repertoire DEST] [--documents DIR] [--base URL]
scripts/restauration.sh [--sauvegarde DIR] [--base-cible NOM] [...] 
```

`scripts/sauvegarde.sh` produit, dans un répertoire horodaté hors dépôt :

| Fichier | Contenu |
|---|---|
| `base.dump.enc` | `pg_dump` (format custom) chiffré — écrit en flux, jamais en clair sur disque |
| `documents.tar.gz.enc` | répertoire des pièces chiffré, lu en place (pas de copie en clair) |
| `manifeste.tar.gz.enc` | manifeste chiffré : comptage de lignes par table + empreinte SHA-256 de chaque fichier |
| `empreintes.sha256` | empreintes SHA-256 des trois archives (aucun secret dedans) |

`scripts/restauration.sh` vérifie d'abord les empreintes, restaure dans une base
de **test**, puis compare **table par table** les comptages sauvegardés /
source / restaurés et **fichier par fichier** les empreintes. Il sort en code 2
si un seul contrôle échoue.

**Garde-fous intégrés** : refus de restaurer dans la base source ; refus de tout
chemin de sauvegarde, de clé ou de restauration situé dans le dépôt ;
sauvegarde impossible sans clé ; refus explicite d'un fichier de sauvegarde non
chiffré (l'archive ne doit pas commencer par la magie `PGDMP`).

**Idempotence** : relancer la sauvegarde crée une sauvegarde de plus et ne
touche à aucune existante ; relancer la restauration recrée la base de test
(ou échoue proprement avec `--sans-suppression`). Aucun script ne supprime quoi
que ce soit dans les sauvegardes.

### 8.2 Planification proposée (à valider par Anthony)

| Quoi | Fréquence proposée | Où |
|---|---|---|
| `sauvegarde.sh` | quotidienne | automatisme sur le serveur, sortie hors dépôt |
| Copie de la sauvegarde vers le stockage objet | quotidienne, après la sauvegarde | région française |
| Exercice de restauration (`restauration.sh`) | mensuelle, sur une base de test | recette |
| Conservation | 30 jours glissants + 12 sauvegardes mensuelles | à confirmer avec le juriste (§ 11) |

**Objectifs proposés, à valider — ce ne sont pas des engagements de service :**
RPO visé ≤ 24 h (une sauvegarde par jour), RTO visé ≤ 4 h (restauration
automatisée + reprise applicative). Ces deux nombres sont des **propositions**
d'exploitation, pas une mesure : aucun n'a été éprouvé sur un serveur réel, qui
n'existe pas.

### 8.3 Procédure de restauration (pas à pas)

**Cas normal — restaurer pour vérifier ou revenir en arrière sur la base :**

1. Choisir la sauvegarde : `--sauvegarde <répertoire>` (par défaut `derniere`).
2. S'assurer que la clé est disponible et lisible :
   `stat -f '%Lp' "$SAUVEGARDE_CLE_FICHIER"` doit afficher `600`.
3. Lancer la restauration vers une base de test :
   `scripts/restauration.sh --base-cible ia_consultations_restauration_test --base "$DATABASE_URL"`.
4. **Lire la sortie** : chaque table doit afficher `identique`, et la ligne
   finale doit dire `RESTAURATION VÉRIFIÉE`. Un code de retour non nul signifie
   qu'il ne faut **pas** continuer.
5. Revenir en arrière : `DROP DATABASE "ia_consultations_restauration_test";`.

**Incident réel — la base de production est perdue ou corrompue :**

1. **Arrêter l'application** (aucune écriture pendant la restauration).
2. **Ne pas** restaurer par-dessus la base abîmée sans l'avoir isolée :
   la renommer ou la conserver telle quelle, c'est la seule copie des données
   récentes.
3. Créer une base neuve, y restaurer la sauvegarde, vérifier les comptages
   (`restauration.sh` sait le faire sur une base cible quelconque).
4. Reconstituer les pièces à partir de `documents.tar.gz.enc` vers le répertoire
   de production.
5. Vérifier l'application par une **vraie requête** (connexion, ouverture d'un
   document), pas seulement par « le service a démarré ».
6. Consigner l'incident : ce qui s'est passé, quelle sauvegarde a servi, quel
   écart de données a été perdu, et pourquoi.

### 8.4 Ce que la sauvegarde ne protège pas

- Elle ne protège pas d'une **clé perdue** : sans la clé, aucune sauvegarde
  n'est déchiffrable. La clé doit être conservée dans un coffre, séparément des
  sauvegardes, et son accès documenté. C'est le point de défaillance unique de
  tout le dispositif.
- Elle ne protège pas d'une **suppression logique** faite par erreur il y a plus
  longtemps que la rétention choisie.
- Elle ne protège pas d'une **compromission du serveur** : un attaquant qui a la
  clé de sauvegarde a les sauvegardes.

---

## 9. Procédure de mise en service (à exécuter plus tard, avec accord explicite)

**Aucune de ces étapes n'a été exécutée.** Elles sont listées pour que la mise en
service soit une suite de gestes connus, pas une improvisation.

**Phase 0 — décisions et préparation (aucun compte ouvert)**

1. Anthony valide : la région `fr-par`, le budget, la personne qui détient la clé
   de sauvegarde.
2. Le juriste est saisi (§ 11) — **avant** la mise en ligne, pas après.
3. Préparer un **chemin de retour** : site non public au départ, DNS non pointé.

**Phase 1 — provisionnement (compte à ouvrir, dépense à engager : accord requis)**

4. Créer le compte chez l'hébergeur retenu, activer la double authentification.
5. Créer le projet **dans la région `fr-par`**, puis **relire l'inventaire** pour
   confirmer la région.
6. Créer la base PostgreSQL managée : chiffrement au repos activé, sauvegardes
   automatiques activées **dans la même région**, réseau privé, **aucune IP
   publique**.
7. Créer l'instance applicative (Debian/Ubuntu à jour), la placer dans le réseau
   privé, ne lui donner **aucune** adresse publique.
8. Créer le volume des pièces et l'activer en chiffrement au repos.
9. Créer le compartiment de stockage objet pour les sauvegardes, **région
   française**, accès privé.

**Phase 2 — installation**

10. Paquets : Python 3.12, PostgreSQL **client** (`pg_dump`, `pg_restore`,
    `psql`), `openssl`, `tar`. Rien de plus.
11. Créer un **utilisateur système non privilégié** pour l'application. Aucun
    service ne tourne en `root`.
12. Déployer le code **sans** `.env` : les secrets sont injectés par
    l'environnement du service, pas par un fichier du dépôt.
13. Appliquer les migrations (`0001`…`000N`) dans l'ordre, puis vérifier les
    tables.
14. Créer la **clé de sauvegarde sur le serveur**, hors du dépôt, permissions
    600, puis la copier dans le coffre.
15. Installer `scripts/sauvegarde.sh` et `scripts/restauration.sh` sur le
    serveur, planifier la sauvegarde quotidienne.
16. **Éprouver la restauration sur le serveur**, avant d'ouvrir quoi que ce soit
    au public.

**Phase 3 — mise en ligne**

17. Reverse-proxy TLS (le certificat, pas la clé privée, est le seul élément
    public) ; **seuls 443 et 22 restent ouverts** ; la base et le port 8000 ne
    sont **jamais** exposés sur Internet.
18. Vérifier après ouverture : une requête HTTP réelle, une connexion valide, un
    dépôt de document fictif, un refus d'accès croisé entre deux clients.
19. Activer la journalisation (§ 6) et la supervision (disque, service,
    sauvegarde **non effectuée** — une sauvegarde silencieusement absente est
    l'incident le plus courant).

**Chemin de retour de chaque phase**

| Phase | Retour en arrière |
|---|---|
| Provisionnement | supprimer les ressources créées ; rien n'a été exposé |
| Installation | l'application n'est pas encore joignable : arrêter le service |
| Mise en ligne | retirer l'entrée DNS ; l'application redevient injoignable en quelques minutes |
| Données | restaurer la sauvegarde précédente (§ 8.3) |

---

## 10. Prix et caractéristiques — sourcés, datés, **à revérifier**

*Toutes les pages ci-dessous ont été consultées le **30 septembre 2026**. Les
tarifs changent : **chaque chiffre doit être revérifié** avant toute décision ou
toute commande.*

| Élément | Valeur | Source | Statut |
|---|---|---|---|
| Scaleway — base managée PostgreSQL « Cost Optimized », nœud principal, **Paris** | `DB-DEV-S` 2 vCPU / 2 Go : **0,0156 €/h HT** (≈ 11,39 €/mois à 730 h) | scaleway.com/en/pricing/managed-databases | **à revérifier** |
| idem | `DB-PLAY2-PICO` 1 vCPU / 2 Go : **0,0233 €/h HT** (≈ 17,01 €/mois) | idem | **à revérifier** |
| idem | `DB-PLAY2-NANO` 2 vCPU / 4 Go : **0,0432 €/h HT** (≈ 31,54 €/mois) | idem | **à revérifier** |
| idem | `DB-PRO2-XXS` 2 vCPU / 8 Go : **0,11 €/h HT** (≈ 80,30 €/mois) | idem | **à revérifier** |
| Scaleway — stockage bloc 5K | **0,0993 €/Go/mois** (≈ 0,99 € pour 10 Go) | idem | **à revérifier** |
| Scaleway — sauvegardes et instantanés | **0,03 €/Go/mois** (≈ 0,60 € pour 20 Go) | idem | **à revérifier** |
| Scaleway — nœud supplémentaire / réplique | `DB-PLAY2-NANO` : 0,0376 €/h HT ; option multi-AZ : 0,0222 €/h HT | idem | **à revérifier** |
| OVHcloud — instance b3-8 (2 vCore / 8 Go / 50 Go NVMe) | **0,0512 €/h HT** ; **plan 12 mois 31,77 €/mois HT** | ovhcloud.com/fr/public-cloud/prices | **à revérifier** ; à noter : OVHcloud a annoncé qu'**à partir du 1er octobre 2026** le stockage local et l'IPv4 des instances b3 ne sont plus inclus dans le prix |
| OVHcloud — base managée PostgreSQL | **prix non vérifié** | les pages tarifaires consultées ne publient pas de prix lisible pour ce service (tableau rendu côté navigateur) ; les prix se lisent dans l'espace client | **absent volontairement** : je n'ai pas lu de prix, je n'en écris pas |
| OVHcloud — régions `eu-west-par`, `eu-west-gra`, `eu-west-rbx`, `eu-west-sbg` | régions françaises | help.ovhcloud.com — « Public Cloud Databases for PostgreSQL : capabilities and limitations » | **à revérifier** ; par ailleurs signalé : la même page liste aussi DE (Francfort), UK, PL, CA, SG, IN — la région doit être choisie explicitement |
| OVHcloud — région Paris `eu-west-par` en 3 zones de disponibilité | 3 zones, ~30 km d'écart | source tierce (outacloud.com) | **à revérifier** auprès d'OVHcloud |
| OVHcloud — base managée PostgreSQL « Discovery » | à partir de **64,24 $/mois/nœud** (1 nœud, rétention 48 h) | **source tierce** (sliplane.io) | **à revérifier** : chiffre tiers, converti en dollars, non confirmé par OVHcloud |
| Mistral AI, OVHcloud AI Endpoints — tarifs de consommation | **non repris ici** | voir `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 13 | **à revérifier** au contrat |

### 10.1 Estimation d'ensemble, à titre indicatif seulement

Sur la base des seuls prix que j'ai pu **lire** (Scaleway, région Paris, HT) :

- base managée `DB-PLAY2-NANO` (2 vCPU / 4 Go) : ≈ 31,54 €/mois ;
- 10 Go de stockage bloc : ≈ 0,99 €/mois ;
- 20 Go de sauvegardes : ≈ 0,60 €/mois ;
- instance applicative : **prix non vérifié dans ce document** (les tarifs
  d'instance Scaleway n'ont pas été lus ici) ;
- consommation du modèle : **poste variable non chiffré ici** — c'est la vraie
  dépense variable, et elle dépend de l'usage.

**Ce que je peux dire** : la partie base et stockage tient largement dans le
budget cible de 150 à 500 €/mois (D9). **Ce que je ne peux pas dire** : le coût
total, tant que le prix de l'instance et la consommation du modèle ne sont pas
relevés. L'honnêteté commande de ne pas afficher un total inventé.

---

## 11. Ce qui reste à la charge du juriste

**Rien dans ce document n'est un avis juridique, et aucune conformité n'est
affirmée.** Les points suivants **bloquent la commercialisation** (D4) et
doivent être traités par un juriste :

1. **Qui est responsable de traitement, qui est sous-traitant.** Le produit
   traite des documents d'entreprise : il faut trancher et le documenter
   (registre des traitements, rôles, base légale).
2. **Accords de traitement (DPA, article 28 RGPD)** avec **chaque** sous-traitant :
   hébergeur, fournisseur de modèle, et tout service de sauvegarde ou de
   supervision. Liste des sous-traitants ultérieurs à exiger.
3. **Clause de non-entraînement explicite** avec le fournisseur de modèle :
   « les données client ne sont pas utilisées pour entraîner, affiner ou
   améliorer des modèles ».
4. **Rétention** : durée de conservation des documents, des analyses, des
   journaux, des sauvegardes — et suppression effective (art. 17).
5. **Transferts hors UE** : à interdire ou à encadrer. Un fournisseur de modèle
   hors UE rend fausse la promesse « hébergé en France » (D8).
6. **Information des personnes** : les CV contiennent des données personnelles
   (et parfois des données sensibles par déduction). Information, droits,
   minimisation sont à cadrer.
7. **Analyse d'impact (AIPD)** : à évaluer, compte tenu du volume et de la
   nature des documents traités.
8. **Sécurité et violation de données** : procédure de notification (art. 33/34),
   et obligations contractuelles envers les clients.
9. **Conservation de la clé de sauvegarde** : qui la détient, à quelles
   conditions, que se passe-t-il en cas de départ de cette personne.
10. **Le conflit d'intérêts** (D4) : la séparation des casquettes doit être
    confirmée par écrit.

---

## 12. Ce que cette procédure ne prouve pas

- Elle ne prouve **aucune** conformité : voir § 11.
- Elle ne prouve pas que l'architecture tient sa promesse de confidentialité
  au-delà de ce qui est écrit en § 3 et § 4.
- Elle n'a **pas** été éprouvée sur un serveur : les scripts ont été exécutés sur
  une base PostgreSQL **locale**, pas sur la base managée visée. Les commandes
  utilisées (`pg_dump`, `pg_restore`, `openssl`, `tar`) sont les mêmes, mais
  l'environnement managé ajoute des contraintes non testées ici : droits,
  authentification, TLS obligatoire, réseau privé, limites de taille.
- Elle ne remplace pas un exercice de restauration sur l'infrastructure réelle,
  qui est la seule preuve qui compte (prévu en § 8.2).

---

## 13. Alternatives écartées

| Alternative | Écartée parce que |
|---|---|
| **SQLite** au lieu de PostgreSQL managé | cloisonnement par lignes et chiffrement applicatif par client plus solides sur PostgreSQL (décision de phase 3) |
| **GPG** (`--symmetric`, MDC intégré) au lieu d'`openssl enc` | apporte une authentification cryptographique, mais ajoute une dépendance dont la présence n'est pas garantie sur toute cible. Retenue comme évolution possible si l'on veut authentifier les archives ; `openssl` est présent partout |
| **`age`** au lieu d'`openssl enc` | même motif : dépendance supplémentaire à installer et à maintenir |
| Chiffrer **la sauvegarde une seule fois** pour toutes les archives | une archive par nature (base, fichiers, manifeste) permet de vérifier et de restaurer indépendamment ; une archive unique obligerait à tout déchiffrer pour lire un comptage |
| Rendre le manifeste **en clair** à côté des archives | un manifeste en clair révèle les noms de tables, les volumes et l'arborescence des clients. Il est donc chiffré, et seules les empreintes (sans information exploitable) restent lisibles |
| Sauvegarder **par `pg_dump` en clair puis chiffrer** | laisse un fichier en clair sur le disque, ne serait-ce que quelques secondes. Le script écrit en flux |
| Héberger base et sauvegardes dans des régions différentes | annule le bénéfice de l'hébergement en France (L2 § 8.1) |
| Fournisseur de modèle hors UE | contredit D6, D7 et D8 : le document sortirait de l'Union |

---

## 14. Sources consultées (30 septembre 2026)

Toutes consultées le **30 septembre 2026**. **À revérifier avant toute
décision** : tarifs et offres évoluent.

- **Scaleway**, « Managed Databases Tarifs — Data & Analytics Pricing »,
  `scaleway.com/en/pricing/managed-databases/` : grille « Managed PostgreSQL /
  MySQL — Cost Optimized », filtres région **Paris** ; stockage bloc 5K
  `0,0993 €/Go/mois` ; sauvegardes/instantanés `0,03 €/Go/mois` ; prix HT.
- **OVHcloud**, « Tarif Cloud : comparatif des offres Public Cloud »,
  `ovhcloud.com/fr/public-cloud/prices/` : instances General Purpose (b3, b2),
  annonce de facturation séparée du stockage local et de l'IPv4 des instances
  b3 **à partir du 1er octobre 2026**.
- **OVHcloud**, « Capabilities and Limitations of Public Cloud Databases for
  PostgreSQL », `help.ovhcloud.com` : régions `GRA`, `SBG`, `EU-WEST-PAR`,
  `RBX`, `DE`, `UK`, `WAW`, `BHS`, `SGP`, `AP-SOUTH-MUM` ; les nœuds d'une base
  restent dans la même région.
- **Sliplane**, « 5 Best Managed Postgres Providers in Europe in 2026 » et
  articles voisins, `sliplane.io` : **source tierce**, plans OVHcloud
  « Discovery / Production / Advanced » et leurs prix en dollars — non confirmés
  par OVHcloud, à revérifier.
- **OutaCloud**, « OVHcloud 3-AZ region Paris », `outacloud.com` : **source
  tierce** sur les trois zones de disponibilité de `eu-west-par` — à revérifier.
- Sources hébergement, fournisseurs de modèles et conformité déjà rassemblées
  dans `docs/CONFIDENTIALITE-ET-HEBERGEMENT.md` § 13 (Mistral AI, OVHcloud AI
  Endpoints, OpenAI, Anthropic, SecNumCloud OVHcloud et Scaleway).

---

*Fin du document. Rien n'est provisionné. Prochaine étape : validation par
Anthony (§ 9, phase 0), puis mise en service sous accord explicite.*