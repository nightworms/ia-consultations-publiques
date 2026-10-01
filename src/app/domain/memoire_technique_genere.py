"""Objets du domaine du **mémoire technique généré** (lot L2, phase 4).

Ce module décrit ce que le moteur produit et manipule : un dossier, ses sections,
les **sources** qui adossent chaque affirmation, les **manques** signalés, et la
**validation** humaine finale. Il ne contient **aucun SQL** et ne dépend que de la
bibliothèque standard.

Il **ne remplace pas** `app.domain.memoire_technique`, qui décrit la **famille 9** de
la bibliothèque (`chapitre_memoire`, mémoire technique **type** réutilisable). Ici, il
s'agit du mémoire **généré pour une consultation** à partir de la bibliothèque et des
critères du DCE.

Règle centrale de la phase 4 (§ 2.B du plan), traduite ici :

* une section n'existe que si elle porte **au moins une** source réelle de la
  bibliothèque du client ; sinon c'est un **manque** (constat + action à mener) ;
* **la source ne suffit pas** : encore faut-il qu'elle porte le **sujet** du critère.
  Une section n'est produite que si chaque **terme de sujet** du libellé se retrouve
  dans le texte des éléments cités (`couverture_sujet`) — sinon c'est un **manque**.
  C'est la correction du défaut B2 de la vérification L8 : une section était produite
  pour le critère « Expérience en toitures-terrasses végétalisées » alors qu'aucune
  référence ne portait « végétalisé » ;
* l'IA **argumente** et **valorise** ; elle n'invente aucun chiffre, ne fixe aucun prix,
  ne garantit aucune conformité (§ 5 de `PROJECT.md`) ;
* tout sort en `brouillon` ; aucun statut validé n'est posé par du code sans une action
  humaine nommée et horodatée.

Le **mapping critère → famille** vit ici (pas dans le service) : c'est une décision de
contenu, directement dérivée de `docs/MEMOIRE-ATTENDU.md` § 5 et de
`docs/JURY-ACHETEUR.md` § 5.3, et elle est faite pour être lue et contestée.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional, Sequence

# --------------------------------------------------------------------------- #
# Statuts — chaînes gelées par `docs/PLAN-PHASE-4.md` § 2.A
# --------------------------------------------------------------------------- #

#: Statut d'une section : brouillon → relue → validee.
STATUTS_SECTION: tuple[str, ...] = ("brouillon", "relue", "validee")

#: Statut d'un dossier : brouillon → en_relecture → valide.
STATUTS_DOSSIER: tuple[str, ...] = ("brouillon", "en_relecture", "valide")

#: Transitions admises, section par section.
TRANSITIONS_SECTION: dict[str, tuple[str, ...]] = {
    "brouillon": ("relue",),
    "relue": ("brouillon", "validee"),
    "validee": ("relue",),
}

#: Mention portée par toute sortie non encore validée par un humain nommé.
MENTION_BROUILLON = "brouillon — à relire et à valider par un humain nommé"

#: Avertissement attaché au dossier généré : ce n'est ni une signature, ni une conformité.
AVERTISSEMENT_GENERATION = (
    "Mémoire technique généré automatiquement à partir de VOTRE bibliothèque et des "
    "critères du DCE. Brouillon : chaque affirmation est adossée à un élément réel "
    "(voir ses sources), mais rien n'est relu, signé ni garanti tant qu'un humain "
    "nommé ne l'a pas validé. Aucune conformité n'est promise, aucun prix n'est fixé."
)

#: Les neuf familles de bibliothèque mobilisables comme sources (§ 5 du mémoire attendu).
FAMILLES_MEMOIRE: tuple[str, ...] = (
    "identite",
    "capacites_financieres",
    "assurances",
    "certifications",
    "references_chantiers",
    "moyens_humains",
    "moyens_materiels",
    "fiches_produits",
    "memoire_technique",
)


# --------------------------------------------------------------------------- #
# Mapping critère → familles — le cœur de la décision de structuration
# --------------------------------------------------------------------------- #


def _normaliser(texte: object) -> str:
    """Minuscules, sans accents, ponctuation → espaces. Déterministe, sans locale."""
    brut = unicodedata.normalize("NFKD", str(texte or ""))
    sans_accents = "".join(c for c in brut if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sans_accents.casefold()).split())


#: Mots de liaison et mots **méta** (ils ne désignent aucun sujet technique) : ils ne
#: comptent jamais comme « terme du sujet » d'un critère. Comparaison sur le texte
#: normalisé (`_normaliser`), donc sans accent.
MOTS_VIDES: frozenset[str] = frozenset(
    {
        "avec", "afin", "ainsi", "aujourd", "aussi", "autre", "autres", "avoir",
        "cas", "celle", "celles", "ceux", "chez", "critere", "criteres", "dans",
        "depuis", "doit", "donc", "dont", "elle", "elles", "encore", "entre",
        "etait", "etre", "eux", "fait", "faire", "hors", "ici", "leurs", "lors",
        "meme", "moins", "notre", "nous", "pendant", "plus", "pour", "quand",
        "quoi", "sans", "selon", "sous", "sont", "tout", "toute", "toutes",
        "tous", "tres", "vers", "votre", "vous", "y",
    }
)

#: Mots de remplissage **de l'offre** : ils qualifient la forme d'une réponse, pas un
#: sujet technique. Vus dans des libellés de critères réels (« valeur technique de
#: l'**offre** », « moyens humains affectés **au marché** », « **engagement** de
#: planning »). Les traiter comme termes de sujet rendrait des manques à tort.
TERMES_GENERIQUES: frozenset[str] = frozenset(
    {
        "affecte", "affectee", "affectees", "affectation", "affectations",
        "affecter", "affectes", "divers", "diverse", "diverses", "ensemble",
        "engage", "engagement", "engagements", "engager", "ensemble",
        "general", "generale", "generales", "generaux", "global", "globale",
        "marche", "marches", "offre", "offres", "presente", "presentees",
        "presentes", "prestation", "prestations",
    }
)


#: Mots-clés qui signalent un critère de **prix** — hors périmètre du mémoire technique,
#: par décision (`docs/JURY-ACHETEUR.md` § 5.4) : un tel critère ne produit aucune
#: section et donne lieu à un manque explicite (hors périmètre du mémoire).
MOTS_CLES_PRIX: tuple[str, ...] = (
    "prix",  # hors périmètre du mémoire : renvoyé vers l'acte d'engagement
    "montant de l offre",
    "montant de loffre",
    "tarif",  # hors périmètre du mémoire : jamais chiffré ici
    "cout",
    "couts",
    "chiffrage",  # hors périmètre : aucun chiffrage dans le mémoire
    "remise",
)


#: Associations critère → familles mobilisables, dans l'ordre de développement (la
#: première famille est la plus lourde en preuve). Chaque entrée : (mots-clés,
#: familles). La **première** entrée dont un mot-clé apparaît dans le libellé gagne.
#: Volontairement grossier : une règle de lecture, pas une compréhension (esprit du
#: fournisseur factice).
CORRESPONDANCES_CRITERE: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    # Solidité économique / capacité financière.
    (
        ("capacite financiere", "solidite", "chiffre d affaires", "financier",
         "capacites financieres", "sante financiere"),
        ("capacites_financieres",),
    ),
    # Couverture assurantielle.
    (
        ("assurance", "garantie", "assurantiel", "responsabilite civile", "decennale"),
        ("assurances",),
    ),
    # Personnes et compétences affectées.
    (
        ("moyens humains", "personnel", "equipe", "competence", "effectif",
         "encadrement", "profils", "cv", "organisation humaine"),
        ("moyens_humains", "certifications"),
    ),
    # Matériel et logistique.
    (
        ("moyens materiels", "materiel", "logistique", "engins", "outillage"),
        ("moyens_materiels",),
    ),
    # Références, expérience, aptitude.
    (
        ("reference", "references", "experience", "aptitude", "chantiers comparables",
         "realisations", "savoir faire", "anciennete"),
        ("references_chantiers", "certifications"),
    ),
    # Sécurité / hygiène / santé.
    (
        ("securite", "hygiene", "sante", "prevention", "sps", "ppsps", "risques"),
        ("certifications", "memoire_technique", "moyens_humains"),
    ),
    # Environnement / déchets.
    (
        ("environnement", "dechets", "nuisances", "developpement durable", "carbone"),
        ("certifications", "memoire_technique"),
    ),
    # Qualité / autocontrôle.
    (
        ("qualite", "controle", "autocontrole", "essais", "tracabilite"),
        ("certifications", "memoire_technique"),
    ),
    # Planning / délais / phasage (peu de famille dédiée : souvent un manque).
    (
        ("planning", "delai", "delais", "phasage", "calendrier", "duree",
         "conditions de reprise"),
        ("references_chantiers", "memoire_technique", "moyens_materiels"),
    ),
    # Qualifications / certifications.
    (
        ("qualification", "certification", "certificat", "label", "mase", "iso"),
        ("certifications",),
    ),
    # Produits, systèmes, procédés.
    (
        ("produit", "systeme", "procede", "technique du batiment", "avis technique",
         "mise en oeuvre", "prescription"),
        ("fiches_produits", "memoire_technique", "references_chantiers"),
    ),
    # Site occupé / interfaces.
    (
        ("site occupe", "interfaces", "coordination", "coactivite", "corps d etat"),
        ("references_chantiers", "memoire_technique", "moyens_humains"),
    ),
    # Présentation de l'entreprise / identité.
    (
        ("identite", "presentation de l entreprise", "l entreprise", "signataire",
         "raison sociale", "presentation"),
        ("identite",),
    ),
    # Valeur technique en général — le fourre-tout assumé, en dernier recours.
    (
        ("valeur technique", "technique", "memoire technique", "methodologie",
         "methode", "mode operatoire"),
        (
            "fiches_produits",
            "memoire_technique",
            "references_chantiers",
            "moyens_materiels",
            "certifications",
        ),
    ),
)

#: Familles mobilisées par défaut quand aucun mot-clé ne reconnaît le critère :
#: l'ensemble de démonstration de valeur technique. Aucune famille « inventée » :
#: ce sont les neuf familles réelles, restreintes à celles qui portent une preuve.
#:
#: **Ce repli ne produit jamais une section à lui seul** : les familles servent
#: seulement à *collecter* des éléments candidats ; la section n'existe que si le
#: **sujet** du critère est corroboré par ces éléments (`couverture_sujet`). Sinon
#: c'est un **manque**. C'est ce qui empêche le repli de fabriquer un développement.
FAMILLES_DEFAUT: tuple[str, ...] = (
    "references_chantiers",
    "moyens_humains",
    "moyens_materiels",
    "fiches_produits",
    "certifications",
    "memoire_technique",
)

#: Action à mener, par famille, quand la bibliothèque ne fournit **aucune** source
#: (dernière colonne du mapping de `docs/MEMOIRE-ATTENDU.md` § 5).
ACTIONS_MANQUE: dict[str, str] = {
    "identite": "Compléter la fiche d'identité de l'entreprise (raison sociale, "
                "représentant légal).",
    "capacites_financieres": "Renseigner les exercices comptables et la capacité de "
                             "production ; joindre l'attestation de capacité.",
    "assurances": "Ajouter l'attestation d'assurance couvrant l'activité, avec sa date "
                  "d'échéance.",
    "certifications": "Ajouter la qualification ou le certificat correspondant à "
                      "l'activité, valide à la date de remise.",
    "references_chantiers": "Ajouter un chantier comparable (nature de travaux, maître "
                            "d'ouvrage, montant € HT, année de réception, difficulté "
                            "traitée).",
    "moyens_humains": "Nommer les moyens humains affectés (effectif par métier, "
                      "organigramme, CV des profils clés).",
    "moyens_materiels": "Décrire les moyens matériels mobilisés (désignation, quantité, "
                        "disponibilité, propre/location).",
    "fiches_produits": "Ajouter le produit ou système retenu et sa fiche technique "
                       "(ou son avis technique) avec sa date de validité.",
    "memoire_technique": "Rédiger le chapitre correspondant du mémoire type, ou traiter "
                         "ce point en manque assumé.",
}

#: Constat type quand aucune source de bibliothèque ne répond au critère.
CONSTAT_MANQUE_AUCUNE_REFERENCE = (
    "Aucune référence correspondante dans votre bibliothèque."
)

#: Constat spécifique du critère « prix » — hors périmètre du mémoire technique.
CONSTAT_PRIX_HORS_MEMOIRE = (
    "Le prix n'est pas un critère de mémoire technique : il se lit dans l'acte "
    "d'engagement et les pièces financières de l'offre, jamais ici."
)

#: Action spécifique du critère « prix » — hors périmètre, aucune valeur produite ici.
ACTION_PRIX_HORS_MEMOIRE = (
    "Traiter le montant dans l'acte d'engagement et les pièces financières ; "
    "n'écrire aucune valeur de prix dans le mémoire technique."
)


def est_critere_prix(libelle: object) -> bool:
    """Vrai si le libellé désigne un critère de prix — hors périmètre du mémoire."""
    normalise = _normaliser(libelle)
    return any(mot in normalise for mot in MOTS_CLES_PRIX)


@dataclass(frozen=True)
class CorrespondanceCritere:
    """Ce qui rattache un critère à des familles de bibliothèque — **traçable**.

    `familles` : les familles mobilisables, dans l'ordre de preuve.
    `mots_cles` : les termes de la table qui ont effectivement reconnu le libellé
    (vide si aucune règle n'a reconnu le critère).
    `defaut` : vrai quand le critère a été rattaché par le repli `FAMILLES_DEFAUT`,
    faute de mot-clé reconnu. Ce repli ne dispense **pas** de corroborer le sujet.
    """

    familles: tuple[str, ...]
    mots_cles: tuple[str, ...] = ()
    defaut: bool = False


def correspondance_pour_critere(libelle: object) -> CorrespondanceCritere:
    """Rattache un critère à ses familles, **avec la justification du rattachement**.

    Un critère de prix renvoie une tuple de familles vide (il n'a **pas** de section).
    Un libellé non reconnu renvoie `FAMILLES_DEFAUT` avec `defaut=True` : ces familles
    ne servent qu'à collecter des candidats, la production d'une section exigeant
    ensuite que le sujet du critère soit corroboré (`couverture_sujet`).
    """
    if est_critere_prix(libelle):
        return CorrespondanceCritere(())
    normalise = _normaliser(libelle)
    # Critère qui mêle explicitement les deux : les deux familles sont mobilisables.
    if ("materiel" in normalise) and (
        "humain" in normalise or "personnel" in normalise or "equipe" in normalise
    ):
        return CorrespondanceCritere(
            ("moyens_humains", "moyens_materiels", "certifications"),
            ("moyens humains", "materiel"),
        )
    for mots_cles, familles in CORRESPONDANCES_CRITERE:
        trouves = tuple(mot for mot in mots_cles if mot in normalise)
        if trouves:
            return CorrespondanceCritere(
                tuple(f for f in familles if f in FAMILLES_MEMOIRE), trouves
            )
    return CorrespondanceCritere(FAMILLES_DEFAUT, (), defaut=True)


def familles_pour_critere(libelle: object) -> tuple[str, ...]:
    """Familles de bibliothèque mobilisables pour un critère, dans l'ordre de preuve.

    Raccourci de `correspondance_pour_critere` (le résultat ne contient jamais qu'un
    sous-ensemble des familles réelles, `FAMILLES_MEMOIRE`).
    """
    return correspondance_pour_critere(libelle).familles


# --------------------------------------------------------------------------- #
# Couverture du sujet — la source ne suffit pas, il faut qu'elle parle du critère
# --------------------------------------------------------------------------- #
def _mots_de_correspondance(mots_cles: Sequence[str]) -> frozenset[str]:
    """Mots (≥ 4 lettres) portés par les mots-clés qui ont reconnu le critère."""
    return frozenset(
        mot for mot in _normaliser(" ".join(mots_cles)).split() if len(mot) >= 4
    )


#: Mot d'un libellé, **dans son écriture d'origine** (accents et capitales conservés) :
#: sert à réafficher les termes du sujet tels quels dans les constats et justifications.
_MOTIF_MOT = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+")


def _radical(mot: str) -> str:
    """Radical grossier d'un mot français : nombre singulier/pluriel replié.

    « toitures » → « toiture », « relevés » → « relevé », « végétalisées » →
    « végétalisée ». Suffisant pour rapprocher le vocabulaire d'un critère de DCE
    (« toitures-terrasses », « relevés ») de celui d'une fiche de bibliothèque
    (« toiture-terrasse », « relevé ») sans rien inventer.
    """
    norme = _normaliser(mot)
    if len(norme) > 4 and norme.endswith(("s", "x")):
        return norme[:-1]
    return norme


def termes_sujet(libelle: object, mots_cles: Sequence[str] = ()) -> tuple[str, ...]:
    """Termes que le critère **doit** retrouver dans la bibliothèque pour être étayé.

    Sont écartés : les mots courts, les mots de liaison (`MOTS_VIDES`), les mots de
    remplissage de l'offre (`TERMES_GENERIQUES`) et les mots déjà portés par les
    mots-clés de la correspondance (ils ont servi à rattacher les familles, ils ne
    désignent pas un sujet à corroborer). Le reste est le **sujet** du critère ; les
    termes sont rendus **tels qu'écrits** (accents conservés), pour être lisibles dans
    les constats et les justifications.
    """
    correspondance = _mots_de_correspondance(mots_cles)
    sujet: list[str] = []
    normes: list[str] = []
    for brut in _MOTIF_MOT.findall(str(libelle or "")):
        norme = _normaliser(brut)
        if len(norme) < 4 or norme in MOTS_VIDES or norme in TERMES_GENERIQUES:
            continue
        if norme in normes:
            continue
        # Variantes de nombre (« materiel » / « materiels », « humain » / « humains »).
        if any(norme.startswith(mot) or mot.startswith(norme) for mot in correspondance):
            continue
        sujet.append(brut)
        normes.append(norme)
    return tuple(sujet)


@dataclass(frozen=True)
class CouvertureSujet:
    """Le verdict de couverture du sujet d'un critère, et **sa trace**.

    `etablie` est vrai quand **aucun** terme du sujet n'est absent : c'est la condition
    pour produire une section. `termes_absents` nomme exactement ce que la bibliothèque
    ne porte pas — c'est ce que le manque écrit noir sur blanc.
    """

    termes_sujet: tuple[str, ...]
    termes_corrobore: tuple[str, ...]
    termes_absents: tuple[str, ...]

    @property
    def etablie(self) -> bool:
        return not self.termes_absents

    def justification(self) -> str:
        """Phrase de traçabilité attachée à la section quand la correspondance tient."""
        if self.termes_corrobore:
            retrouves = ", ".join(f"« {terme} »" for terme in self.termes_corrobore)
            return (
                "Correspondance établie : le sujet du critère est corroboré par les "
                f"éléments cités (termes retrouvés dans votre bibliothèque : {retrouves})."
            )
        return (
            "Correspondance établie : les mots du critère renvoient directement à des "
            "familles de votre bibliothèque ; les éléments cités sont vérifiés (aucun "
            "terme de spécialité du libellé n'y manque)."
        )


def couverture_sujet(
    libelle: object,
    mots_cles: Sequence[str],
    textes: Sequence[str],
) -> CouvertureSujet:
    """Le sujet du critère est-il porté par au moins un des textes d'éléments fournis ?

    `textes` sont les rendus « champ : valeur » des éléments **dont la source a déjà été
    vérifiée**. Un terme du sujet est *corroboré* si son **radical** apparaît comme mot
    dans l'un d'eux (le singulier et le pluriel sont rapprochés : « toitures » ↔
    « toiture »). C'est le contrôle que la vérification L8 a montré absent : le lien
    entre le **sujet** du critère et le contenu des éléments cités.
    """
    jetons = [
        _radical(mot)
        for texte in textes
        for mot in _normaliser(texte).split()
    ]
    corrobore: list[str] = []
    absents: list[str] = []
    for terme in termes_sujet(libelle, mots_cles):
        cible = corrobore if _radical(terme) in jetons else absents
        cible.append(terme)
    return CouvertureSujet(
        termes_sujet(libelle, mots_cles), tuple(corrobore), tuple(absents)
    )


def constat_manque_sujet(termes_absents: Sequence[str]) -> str:
    """Constat d'un critère dont le sujet n'est pas couvert par la bibliothèque.

    Il nomme les termes absents (vérifiables par une requête sur la bibliothèque) et
    rappelle la ligne rouge : on ne présente pas une expérience que rien n'atteste.
    """
    liste = ", ".join(f"« {terme} »" for terme in termes_absents)
    return (
        f"Aucun élément de votre bibliothèque ne porte {liste} : le sujet du critère "
        "n'est pas couvert. Le mémoire ne peut pas présenter une expérience ou un moyen "
        "que votre bibliothèque ne démontre pas."
    )


# --------------------------------------------------------------------------- #
# Lecture de la pondération
# --------------------------------------------------------------------------- #

_MOTIF_POURCENTAGE = re.compile(r"(?P<valeur>\d{1,3}(?:[.,]\d+)?)\s*%")


def poids_depuis_valeur(valeur: object) -> Optional[Decimal]:
    """Pondération `%` lue dans la valeur d'un critère de DCE, ou `None`.

    **Aucun poids n'est inventé** : si la valeur ne porte pas un pourcentage
    explicite, la fonction renvoie `None` (le critère sera traité en fin de mémoire,
    avec sa raison affichée). Une valeur hors `[0 ; 100]` est refusée (`None`) plutôt
    que normalisée.
    """
    texte = "" if valeur is None else str(valeur)
    trouve = _MOTIF_POURCENTAGE.search(texte)
    if not trouve:
        return None
    try:
        poids = Decimal(trouve.group("valeur").replace(",", "."))
    except InvalidOperation:
        return None
    if poids < 0 or poids > 100:
        return None
    return poids


# --------------------------------------------------------------------------- #
# Objets du domaine
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SourceMemoire:
    """Une preuve : un élément réel de la bibliothèque du client, cité par une section.

    `table_source` est le nom exact d'une table de contenu de `app.domain.familles` ;
    `element_id` son identifiant ; `libelle_source` un libellé lisible ; et
    `emplacement_source` l'endroit d'où vient la valeur (famille / entité / date).
    """

    table_source: str
    element_id: str
    libelle_source: str
    emplacement_source: str


@dataclass(frozen=True)
class SectionMemoire:
    """Une section du mémoire, adossée à un critère du DCE et à ses sources réelles."""

    ordre: int
    critere_code: Optional[str]
    critere_libelle: str
    critere_poids: Optional[Decimal]
    titre: str
    contenu: str
    sources: tuple[SourceMemoire, ...]
    statut: str = "brouillon"
    origine: str = "mixte"
    confiance: str = "a_verifier"

    @property
    def longueur(self) -> int:
        """Longueur visible du contenu, en caractères (pour arbitrer la mise en forme)."""
        return len(self.contenu)

    @property
    def nb_sources(self) -> int:
        return len(self.sources)


@dataclass(frozen=True)
class ManqueMemoire:
    """Un manque signalé : le critère, le constat, et **l'action à mener**.

    Ce n'est **pas** un cas d'erreur : c'est le résultat le plus utile du produit.
    """

    critere_code: Optional[str]
    critere_libelle: str
    critere_poids: Optional[Decimal]
    constat: str
    action_attendue: str


@dataclass(frozen=True)
class ValidationMemoire:
    """La validation finale : nommée, horodatée, avec l'empreinte du contenu validé."""

    nom_validateur: str
    fonction_validateur: str
    empreinte_contenu: str
    format_export: Optional[str] = None
    nom_fichier: Optional[str] = None
    horodatage: Optional[object] = None


@dataclass(frozen=True)
class DossierMemoire:
    """Le dossier généré : son en-tête, ses sections ordonnées et ses manques."""

    titre: str
    statut: str
    sections: tuple[SectionMemoire, ...] = field(default_factory=tuple)
    manques: tuple[ManqueMemoire, ...] = field(default_factory=tuple)
    avertissement: str = AVERTISSEMENT_GENERATION

    @property
    def nb_sections(self) -> int:
        return len(self.sections)

    @property
    def nb_manques(self) -> int:
        return len(self.manques)


__all__ = [
    "ACTIONS_MANQUE",
    "AVERTISSEMENT_GENERATION",
    "CONSTAT_MANQUE_AUCUNE_REFERENCE",
    "CONSTAT_PRIX_HORS_MEMOIRE",
    "ACTION_PRIX_HORS_MEMOIRE",
    "CORRESPONDANCES_CRITERE",
    "CorrespondanceCritere",
    "CouvertureSujet",
    "DossierMemoire",
    "FAMILLES_DEFAUT",
    "FAMILLES_MEMOIRE",
    "MENTION_BROUILLON",
    "MOTS_VIDES",
    "ManqueMemoire",
    "SectionMemoire",
    "SourceMemoire",
    "STATUTS_DOSSIER",
    "STATUTS_SECTION",
    "TERMES_GENERIQUES",
    "TRANSITIONS_SECTION",
    "ValidationMemoire",
    "constat_manque_sujet",
    "correspondance_pour_critere",
    "couverture_sujet",
    "est_critere_prix",
    "familles_pour_critere",
    "poids_depuis_valeur",
    "termes_sujet",
]
