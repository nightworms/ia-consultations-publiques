"""Couche d'abstraction du fournisseur de modèle (décision D8, annexe A § A7).

Objectif : le produit ne dépend **d'aucun fournisseur précis**. Il dépend d'un
contrat, `FournisseurModele`, que plusieurs implémentations honorent :

* `fournisseur_factice.FournisseurFactice` — déterministe, **sans réseau**, utilisé
  par les tests. Il ne « comprend » rien : il applique des règles de lecture sur le
  texte fictif. Il est signalé comme tel partout (`avertissement`, `nom`).
* `fournisseur_ue.FournisseurUe` — appel HTTP à un fournisseur établi en France ou
  dans l'UE (Mistral AI, OVHcloud AI Endpoints, modèle auto-hébergé). Son adresse,
  sa clé et son nom de modèle viennent de l'**environnement**, jamais du dépôt.

Deux règles opposables, appliquées **avant** d'accepter la réponse d'un fournisseur
(quelle qu'elle soit, y compris un grand modèle) :

1. **Aucune proposition sans source.** `source_emplacement` est obligatoire, et
   `source_extrait` doit se retrouver **littéralement** dans le texte réellement
   extrait du document. Une proposition non adossée à un passage du document est
   rejetée : c'est la traduction technique de la ligne rouge (SPEC-MVP-V2 § 2).
2. **Aucune catégorie hors contrat.** Les seules catégories admises sont
   `piece_exigee`, `critere`, `date_limite` (annexe B § B3).

Ce module ne connaît ni le stockage, ni la base, ni le HTTP : il ne dépend que de la
bibliothèque standard et du résultat d'extraction (`extraction_pdf.ExtractionPdf`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence

from app.services.extraction_pdf import ExtractionPdf, PageExtraite

#: Les trois seules catégories que la brique B extrait (annexe B § B3).
CATEGORIES_ELEMENTS = ("piece_exigee", "critere", "date_limite")

#: Catégories pour lesquelles « rien trouvé » doit être écrit explicitement.
CATEGORIES_ATTENDUES = CATEGORIES_ELEMENTS

#: Mention portée par toute proposition non vérifiée par un humain.
MENTION_NON_VERIFIE = "proposé par la machine — à vérifier par un humain"

#: Message imposé quand un élément est absent du document (SPEC-MVP-V2 § 3.3).
MENTION_NON_TROUVE = "non trouvé dans le document"


class ErreurFournisseurModele(RuntimeError):
    """Le fournisseur est mal configuré ou n'a pas pu être appelé."""


class ReponseModeleInvalide(ErreurFournisseurModele):
    """La réponse du fournisseur viole le contrat (source absente, catégorie inconnue).

    `categorie` et `extrait` portent, quand le contrôle les connaît, l'élément
    précisément mis en cause. Ils permettent à la couche appelante d'expliquer le
    refus au client (« quelle catégorie, quel extrait introuvable ») sans avoir à
    réinterpréter le message. Le refus lui-même n'est pas négociable : ces attributs
    ne servent qu'à le rendre lisible.
    """

    def __init__(
        self,
        message: str,
        *,
        categorie: Optional[str] = None,
        extrait: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.categorie = categorie
        self.extrait = extrait


@dataclass(frozen=True)
class PropositionElement:
    """Un élément proposé par un fournisseur, avec sa source **obligatoire**.

    `source_document_id` n'est pas du ressort du fournisseur : il est posé par
    l'orchestration, qui seule connaît la base.
    """

    categorie: str
    libelle: str
    source_emplacement: str
    valeur: Optional[str] = None
    source_extrait: Optional[str] = None

    def est_piece(self) -> bool:
        return self.categorie == "piece_exigee"


@dataclass(frozen=True)
class ResultatAnalyse:
    """Ce qu'un fournisseur renvoie : des propositions, jamais une conclusion."""

    propositions: tuple[PropositionElement, ...]
    fournisseur: str
    modele: Optional[str] = None
    avertissement: Optional[str] = None

    @property
    def est_factice(self) -> bool:
        return self.fournisseur == "factice"


def _normaliser(texte: str) -> str:
    """Écrase les espaces et la casse pour comparer un extrait à sa source."""
    return " ".join(texte.split()).casefold()


def source_presente(proposition: PropositionElement, pages: Sequence[PageExtraite]) -> bool:
    """Vrai si l'extrait invoqué se retrouve réellement dans le texte extrait.

    La comparaison ignore les écarts d'espaces (mise en page) mais **rien d'autre** :
    une phrase reformulée par le modèle n'est pas une source.
    """
    if not proposition.source_extrait:
        return False
    extrait = _normaliser(proposition.source_extrait)
    if not extrait:
        return False
    return any(extrait in _normaliser(page.texte) for page in pages)


def verifier_propositions(
    propositions: Sequence[PropositionElement],
    pages: Sequence[PageExtraite],
) -> tuple[PropositionElement, ...]:
    """Applique les règles opposables aux propositions d'un fournisseur.

    Rejette (exception explicite, jamais silencieuse) toute proposition sans source
    vérifiable, sans emplacement ou de catégorie inconnue. Aucun élément n'est
    « réparé » ni complété.
    """
    retenues: list[PropositionElement] = []
    for proposition in propositions:
        if proposition.categorie not in CATEGORIES_ELEMENTS:
            raise ReponseModeleInvalide(
                f"Catégorie hors contrat : {proposition.categorie!r}. "
                f"Catégories admises : {', '.join(CATEGORIES_ELEMENTS)}.",
                categorie=proposition.categorie,
            )
        if not proposition.libelle or not proposition.libelle.strip():
            raise ReponseModeleInvalide(
                "Proposition sans libellé : refusée.", categorie=proposition.categorie
            )
        if not proposition.source_emplacement or not proposition.source_emplacement.strip():
            raise ReponseModeleInvalide(
                "Proposition sans emplacement source : refusée (aucune valeur sans source).",
                categorie=proposition.categorie,
            )
        if not source_presente(proposition, pages):
            raise ReponseModeleInvalide(
                "Proposition non adossée au document : l'extrait invoqué est introuvable "
                f"dans le texte extrait (catégorie {proposition.categorie!r}). "
                "Une valeur sans source n'est jamais acceptée.",
                categorie=proposition.categorie,
                extrait=proposition.source_extrait,
            )
        retenues.append(proposition)
    return tuple(retenues)


class FournisseurModele(ABC):
    """Contrat d'un fournisseur de modèle (D8).

    Un fournisseur reçoit **le texte extrait** (jamais le fichier) et renvoie des
    propositions sourcées. Il ne décide de rien : ni validation, ni conformité, ni
    prix, ni date « calculée ».
    """

    #: Identifiant court du fournisseur, stocké dans `extraction_element.moteur_fournisseur`.
    nom: str = "inconnu"

    #: Nom du modèle employé, stocké dans `extraction_element.moteur_modele`.
    modele: Optional[str] = None

    @abstractmethod
    def analyser(self, extraction: ExtractionPdf) -> ResultatAnalyse:
        """Analyse un texte extrait et renvoie des propositions sourcées.

        Ne lève jamais pour « rien trouvé » : l'absence est un résultat légitime,
        signalée plus haut par `MENTION_NON_TROUVE`.
        """
        raise NotImplementedError

    # -- confort ---------------------------------------------------------------
    @property
    def avertissement(self) -> Optional[str]:
        """Avertissement à afficher, par exemple « non-IQ réel »."""
        return None

    def description(self) -> str:
        return f"{self.nom}" + (f" ({self.modele})" if self.modele else "")
