"""Fournisseur **réel** — appel HTTP à un fournisseur établi en France ou dans l'UE (D8).

Cibles visées par la décision D8 : Mistral AI, OVHcloud AI Endpoints, ou un modèle
ouvert auto-hébergé sur le même serveur. **Aucun secret dans le dépôt** : l'adresse,
la clé et le nom du modèle viennent de l'environnement.

Variables d'environnement lues (voir `.env.example`) :

======================  =========================================================
``MODELE_FOURNISSEUR_URL``   adresse complète de l'endroit appelé (obligatoire)
``MODELE_FOURNISSEUR_CLE``   clé d'accès (obligatoire) — jamais journalisée
``MODELE_FOURNISSEUR_NOM``   nom du modèle demandé (obligatoire)
``MODELE_FOURNISSEUR_ORGANISME``  libellé de l'organisme (facultatif, traçabilité)
``MODELE_FOURNISSEUR_DELAI``  délai d'attente en secondes (facultatif, défaut 60)
======================  =========================================================

Le format d'appel retenu est celui, très répandu, **compatible OpenAI**
(`POST` d'un objet `model` + `messages`), que Mistral AI et OVHcloud AI Endpoints
exposent tous deux. L'adapter à un autre fournisseur consiste à écrire une nouvelle
implémentation de `FournisseurModele`, sans toucher au reste du produit : c'est
l'objet même de D8.

Ce que ce module **ne promet pas** :

* il n'envoie **aucune** option de non-conservation par défaut — de telles options
  n'existent pas chez tous les fournisseurs, et prétendre le contraire serait une
  promesse non vérifiable. Le contrat de non-conservation et de non-entraînement
  (D6) doit être **vérifié à la souscription**, au niveau du compte, pas supposé ici ;
* il ne valide rien lui-même : la réponse est contrôlée par
  `base.verifier_propositions`, qui rejette toute proposition non adossée au
  document. **Un modèle ne peut donc pas faire entrer une valeur inventée.**

**Ce chemin n'est pas testé avec une vraie clé d'API** (risque R3 du plan) : aucun
appel réseau n'est effectué par la suite de tests. Les tests exercent la lecture de
la réponse et le contrôle des sources avec un transport HTTP simulé, en mémoire.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional, Sequence

import httpx

from app.services.extraction_pdf import ExtractionPdf
from app.services.fournisseur_modele.base import (
    CATEGORIES_ELEMENTS,
    ErreurFournisseurModele,
    FournisseurModele,
    PropositionElement,
    ReponseModeleInvalide,
    ResultatAnalyse,
)

NOM_VARIABLE_URL = "MODELE_FOURNISSEUR_URL"
NOM_VARIABLE_CLE = "MODELE_FOURNISSEUR_CLE"
NOM_VARIABLE_MODELE = "MODELE_FOURNISSEUR_NOM"
NOM_VARIABLE_ORGANISME = "MODELE_FOURNISSEUR_ORGANISME"
NOM_VARIABLE_DELAI = "MODELE_FOURNISSEUR_DELAI"

#: Consigne envoyée au modèle. Elle interdit explicitement l'invention et exige un
#: extrait littéral — exigence doublée, côté code, par `verifier_propositions`.
CONSIGNE = (
    "Tu extrais des éléments d'un dossier de consultation (DCE) public. Réponds "
    "UNIQUEMENT par un objet JSON de la forme "
    '{"elements":[{"categorie":"piece_exigee|critere|date_limite","libelle":"...",'
    '"valeur":"... ou null","source_emplacement":"page ou section","source_extrait":"..."}]}. '
    "Règles absolues : n'invente rien ; n'ajoute aucun élément absent du texte ; "
    "« source_extrait » doit être un extrait COPIÉ LITTÉRALEMENT du texte fourni ; "
    "si une catégorie est absente du document, ne produis aucun élément pour elle "
    "(l'absence sera signalée comme « non trouvé dans le document »). "
    "Aucune pondération, aucune date, aucun prix qui ne soit écrit dans le texte."
)


def _lire_variable(nom: str, obligatoire: bool = True, defaut: Optional[str] = None) -> Optional[str]:
    valeur = os.environ.get(nom)
    if valeur is None or not valeur.strip():
        if obligatoire:
            raise ErreurFournisseurModele(
                f"Fournisseur de modèle non configuré : variable d'environnement "
                f"{nom} absente. Voir `.env.example` — aucune valeur n'est écrite dans le code."
            )
        return defaut
    return valeur.strip()


class FournisseurUe(FournisseurModele):
    """Appel HTTP à un fournisseur France/UE. Jamais appelé par les tests."""

    nom = "ue"

    def __init__(
        self,
        *,
        url: Optional[str] = None,
        cle: Optional[str] = None,
        modele: Optional[str] = None,
        organisme: Optional[str] = None,
        delai: Optional[float] = None,
        client_http: Optional[httpx.Client] = None,
    ) -> None:
        self.url = url or _lire_variable(NOM_VARIABLE_URL)
        if not self.url:
            raise ErreurFournisseurModele(
                f"Adresse du fournisseur absente ({NOM_VARIABLE_URL})."
            )
        self._cle = cle or _lire_variable(NOM_VARIABLE_CLE)
        self.modele = modele or _lire_variable(NOM_VARIABLE_MODELE)
        self.organisme = organisme or _lire_variable(
            NOM_VARIABLE_ORGANISME, obligatoire=False, defaut="France/UE (non précisé)"
        )
        brut_delai = os.environ.get(NOM_VARIABLE_DELAI, "").strip()
        if delai is not None:
            self.delai = float(delai)
        elif brut_delai:
            try:
                self.delai = float(brut_delai)
            except ValueError as exc:
                raise ErreurFournisseurModele(
                    f"{NOM_VARIABLE_DELAI} doit être un nombre de secondes, reçu {brut_delai!r}."
                ) from exc
        else:
            self.delai = 60.0
        self._client_http = client_http

    @property
    def avertissement(self) -> Optional[str]:
        return None  # fournisseur réel : l'avertissement « factice » ne s'applique pas

    def description(self) -> str:
        return f"{self.nom} ({self.organisme}) — modèle {self.modele}"

    # -- construction de la requête -------------------------------------------
    def construire_charge_utile(self, extraction: ExtractionPdf) -> dict[str, Any]:
        """Corps de la requête. Aucune clé ici : elle part dans l'en-tête."""
        return {
            "model": self.modele,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": CONSIGNE},
                {
                    "role": "user",
                    "content": (
                        "Texte du document (les pages sont numérotées ; cite le numéro "
                        "de page dans source_emplacement) :\n\n"
                        + extraction.texte_complet
                    ),
                },
            ],
        }

    # -- lecture de la réponse -------------------------------------------------
    def lire_reponse(self, contenu: str) -> tuple[PropositionElement, ...]:
        """Transforme la réponse du modèle en propositions. Aucune donnée inventée.

        Tolère les délimiteurs de code autour du JSON (comportement fréquent des
        modèles), refuse tout le reste par une exception explicite.
        """
        if not contenu or not contenu.strip():
            raise ReponseModeleInvalide("Réponse vide du fournisseur de modèle.")
        texte = contenu.strip()
        cloture = re.match(r"```(?:json)?\s*(.*?)\s*```", texte, re.DOTALL)
        if cloture:
            texte = cloture.group(1)
        try:
            charge = json.loads(texte)
        except json.JSONDecodeError as exc:
            raise ReponseModeleInvalide(
                "Réponse du fournisseur illisible : JSON attendu, reçu "
                f"{texte[:120]!r} ({exc})."
            ) from exc
        elements = charge.get("elements") if isinstance(charge, dict) else None
        if not isinstance(elements, list):
            raise ReponseModeleInvalide(
                "Réponse du fournisseur hors contrat : clé « elements » (liste) absente."
            )
        propositions: list[PropositionElement] = []
        for brut in elements:
            if not isinstance(brut, dict):
                raise ReponseModeleInvalide("Élément de réponse non objet : refusé.")
            categorie = str(brut.get("categorie", "")).strip()
            if categorie not in CATEGORIES_ELEMENTS:
                raise ReponseModeleInvalide(
                    f"Catégorie hors contrat renvoyée par le modèle : {categorie!r}."
                )
            valeur = brut.get("valeur")
            propositions.append(
                PropositionElement(
                    categorie=categorie,
                    libelle=str(brut.get("libelle") or "").strip(),
                    valeur=None if valeur in (None, "", "null") else str(valeur).strip(),
                    source_emplacement=str(brut.get("source_emplacement") or "").strip(),
                    source_extrait=(
                        None
                        if brut.get("source_extrait") in (None, "", "null")
                        else str(brut["source_extrait"]).strip()
                    ),
                )
            )
        return tuple(propositions)

    # -- appel ---------------------------------------------------------------
    def analyser(self, extraction: ExtractionPdf) -> ResultatAnalyse:
        """Appelle le fournisseur. Ne journalise jamais la clé."""
        entetes = {
            "Authorization": f"Bearer {self._cle}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        charge = self.construire_charge_utile(extraction)
        client = self._client_http or httpx.Client(timeout=self.delai)
        proprietaire = self._client_http is None
        try:
            reponse = client.post(self.url, headers=entetes, json=charge)
        except httpx.HTTPError as exc:
            raise ErreurFournisseurModele(
                f"Appel au fournisseur {self.organisme} impossible : {type(exc).__name__}."
            ) from exc
        finally:
            if proprietaire:
                client.close()

        if reponse.status_code >= 400:
            raise ErreurFournisseurModele(
                f"Fournisseur {self.organisme} en échec (HTTP {reponse.status_code}). "
                "La clé et l'adresse ne sont jamais recopiées ici."
            )
        try:
            donnees = reponse.json()
            contenu = donnees["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ReponseModeleInvalide(
                "Réponse du fournisseur hors format (aucun contenu de message exploitable)."
            ) from exc

        propositions = self.lire_reponse(str(contenu))
        return ResultatAnalyse(
            propositions=propositions,
            fournisseur=self.nom,
            modele=self.modele,
            avertissement=None,
        )
