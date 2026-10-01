"""Fournisseur **factice** — déterministe, sans réseau, utilisé par les tests.

**Avertissement explicite : ce n'est pas une intelligence artificielle.** Ce
fournisseur ne « comprend » rien : il applique des règles de lecture mécaniques sur
du texte, et ne produit jamais autre chose que ce qui est écrit dans le document.

- Aucun réseau, aucun modèle, aucune clé. Le résultat est reproductible au caractère
  près, ce qui est exactement ce qu'un test exige.
- Il ne remplit **jamais** un vide : si une section attendue est absente, il ne renvoie
  rien pour cette catégorie (l'orchestration écrira « non trouvé dans le document »).
- Chaque proposition porte l'extrait littéral de la ligne lue et son emplacement
  (page + section), donc chaque proposition survive au contrôle de source de
  `base.verifier_propositions`.

Règles appliquées (documentées pour être contestables) :

``R1 — pièces exigées``
    Dans une section dont le titre contient « pièce » et « exig », chaque ligne
    commençant par « - » donne une pièce exigée.
``R2 — critères``
    Dans une section dont le titre contient « critère », chaque ligne de la forme
    « - libellé : NN % » donne un critère, avec la pondération **telle qu'écrite**.
``R3 — date limite``
    Dans une section dont le titre contient « date limite », la première date
    reconnue (ISO `AAAA-MM-JJ` ou `JJ mois AAAA` en français) donne la date limite,
    convertie en ISO 8601. Le libellé reprend la ligne littérale : aucune tournure
    n'est inventée.
``R4 — import guidé`` (voir `proposer_elements`)
    Une ligne ``Entité : <nom_entite>`` ouvre un bloc ; chaque ligne
    ``- <champ> : <valeur>`` du bloc alimente un élément proposé pour cette entité,
    avec l'extrait littéral du bloc comme source. Aucun bloc, aucune proposition.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from app.domain.familles import FAMILLE_VERS_ENTITES, definition_entite, type_champ
from app.services.extraction_pdf import ExtractionPdf, PageExtraite
from app.services.fournisseur_modele.base import (
    FournisseurModele,
    PropositionElement,
    PropositionImport,
    ResultatAnalyse,
)

#: Titres de section reconnus. Volontairement grossiers : une règle de lecture, pas
#: une compréhension.
_MOTIF_SECTION_PIECES = re.compile(r"pi[eè]ces?.{0,20}exig", re.IGNORECASE)
_MOTIF_SECTION_CRITERES = re.compile(r"crit[eè]res?", re.IGNORECASE)
_MOTIF_SECTION_DATE = re.compile(r"date\s+limite", re.IGNORECASE)

#: Une ligne de liste : « - texte » (tiret simple, en début de ligne).
_MOTIF_LIGNE_LISTE = re.compile(r"^\s*[-•]\s*(?P<contenu>.+?)\s*$")
#: Un critère pondéré : « libellé : 40 % » (la pondération vient du document).
_MOTIF_CRITERE = re.compile(
    r"^\s*[-•]\s*(?P<libelle>.+?)\s*:\s*(?P<ponderation>\d{1,3})\s*%\s*$"
)
#: Une ligne de titre de section, ex. « Article 4 — Pièces exigées ».
_MOTIF_TITRE = re.compile(r"^\s*(ARTICLE\b.*|[IVX]+\.\s+.*|[0-9]+\.\s+.*)$")

#: Import guidé — une ligne « Entité : <nom_entite> » ouvre un bloc.
_MOTIF_ENTITE_IMPORT = re.compile(
    r"^\s*entit[eé]s?\s*:\s*(?P<entite>[A-Za-z_][A-Za-z0-9_]*)\s*$", re.IGNORECASE
)
#: Import guidé — une ligne « - champ : valeur » (nom de champ en identifiant).
_MOTIF_CHAMP_IMPORT = re.compile(
    r"^\s*[-•]\s*(?P<champ>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<valeur>.+?)\s*$"
)

# --------------------------------------------------------------------------- #
# Import guidé — lecture d'un document courant écrit en français métier (I4)
# --------------------------------------------------------------------------- #
#: Règle ``I4 — français métier`` (ajoutée le 30/09/2026, correctif du défaut B1).
#:
#: Un document réel n'est jamais écrit dans le micro-format ``Entité : …``. Le
#: lecteur de démonstration reconnaît donc aussi les écritures courantes d'un
#: document d'entreprise : lignes ``Libellé : valeur`` (plaquette, attestation) et
#: sections titrées (``QUALIFICATIONS ET CERTIFICATIONS``, ``ASSURANCES``,
#: ``MOYENS HUMAINS``, ``MOYENS MATÉRIELS``, ``RÉFÉRENCES``, chapitres numérotés
#: d'un ancien mémoire). **Aucune valeur n'est devinée** : chaque proposition ne
#: porte que du texte réellement présent, et son ``source_extrait`` est la portion
#: littérale du document dont elle vient — le garde-fou ``source_presente`` est
#: appliqué tel quel par le service (aucun abaissement).
#:
#: La lecture est **orientée par ``famille_cible``** : seules les entités de la
#: famille visée sont proposées, comme pour n'importe quel fournisseur.

#: Une ligne de champ en français : « Libellé : valeur » (puce « - »/« • » tolérée).
_MOTIF_CHAMP_FR = re.compile(
    r"^\s*[-•]?\s*(?P<libelle>[^:]{1,80}?)\s*:\s*(?P<valeur>.+?)\s*$"
)

#: Un titre de section numéroté : « 1. COMPRÉHENSION DE L'OPÉRATION ».
_MOTIF_TITRE_NUMEROTE = re.compile(r"^\s*(?P<ordre>\d{1,2})[.)]\s+(?P<titre>.+?)\s*$")

#: Mots qui ouvrent une section (comparaison sans accent ni casse).
_MOTS_SECTIONS: tuple[str, ...] = (
    "reference",
    "qualification",
    "certification",
    "assurance",
    "moyens humains",
    "moyens materiels",
    "moyens affectes",
    "equipes",
    "activites",
    "activite",
    "presentation",
    "identite",
    "raison sociale",
    "entreprise",
    "fiche technique",
    "produit",
    "exercice",
    "capacite",
    "effectif",
    "avertissement",
)

#: Nombres écrits en toutes lettres (le document les écrit, on les relit tels quels).
_NOMBRES_FR: dict[str, int] = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
    "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
}

#: Un montant suivi de sa devise : « 412 000 EUR », « 1 500 000 EUR (FICTIF) ».
#: Le nombre ne franchit jamais une virgule de liste : « 2023, 195 000 EUR » donne
#: bien « 195 000 », pas « 2023,195000 ».
_MOTIF_MONTANT = re.compile(
    r"(?P<montant>\d{1,3}(?:[\s\u00a0\u202f]\d{3})+|\d+(?:[.,]\d+)?)"
    r"\s*(?P<devise>EUR|€|euros?)",
    re.IGNORECASE,
)
_MOTIF_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_MOTIF_TELEPHONE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

#: Valeurs qui ne portent aucune information : elles ne sont jamais proposées.
_VALEURS_VIDES: frozenset[str] = frozenset(
    {"non renseigne", "non renseignee", "sans objet", "n/a", "na", "aucun", "aucune",
     "-", "—", "neant", "à completer"}
)

#: Libellés français d'un document d'entreprise → champ du registre des entités.
#: Un champ absent de cette table n'est jamais proposé : aucune valeur n'est devinée.
_LIBELLES_VERS_CHAMP: dict[str, dict[str, str]] = {
    "entreprise_version": {
        "raison sociale": "raison_sociale",
        "denomination": "raison_sociale",
        "forme juridique": "forme_juridique_code",
        "siege social": "adresse_siege",
        "adresse du siege": "adresse_siege",
        "adresse": "adresse_siege",
        "telephone": "telephone",
        "tel": "telephone",
        "courriel": "email",
        "email": "email",
        "e-mail": "email",
        "site": "site_web",
        "site web": "site_web",
        "code ape": "code_ape_naf",
        "code ape/naf": "code_ape_naf",
        "code naf": "code_ape_naf",
        "effectif": "effectif",
        "date de creation": "date_creation_entreprise",
        "date de creation de l'entreprise": "date_creation_entreprise",
        "capital social": "capital_social_montant",
        "siren": "siren",
        "siret du siege": "siret_siege",
        "siret": "siret_siege",
        "numero tva intracommunautaire": "numero_tva_intracommunautaire",
        "tva intracommunautaire": "numero_tva_intracommunautaire",
    },
    "assurance": {
        "type d'assurance": "type_assurance",
        "type assurance": "type_assurance",
        "assureur": "assureur",
        "compagnie": "assureur",
        "numero de contrat": "numero_contrat",
        "numero de police": "numero_contrat",
        "police": "numero_contrat",
        "date d'effet": "date_debut",
        "date de debut": "date_debut",
        "date d'echeance": "date_echeance",
        "date de fin": "date_echeance",
        "activites couvertes": "activites_couvertes",
        "montant de garantie": "montant_garantie_montant",
        "garantie": "montant_garantie_montant",
        "franchise": "franchise_montant",
    },
    "certification": {
        "intitule": "intitule",
        "organisme": "organisme",
        "organisme certificateur": "organisme",
        "numero de certificat": "numero_certificat",
        "numero": "numero_certificat",
        "date d'obtention": "date_obtention",
        "obtenue le": "date_obtention",
        "date d'echeance": "date_echeance",
        "domaine": "domaine_code",
    },
    "attestation": {
        "type d'attestation": "type_attestation",
        "emetteur": "emetteur",
        "date d'emission": "date_emission",
        "date de fin de validite": "date_validite_fin",
        "montant engage": "montant_engage_montant",
    },
    "produit": {
        "fournisseur": "fournisseur",
        "reference produit": "reference_produit",
        "reference": "reference_produit",
        "designation": "designation",
        "domaine d'application": "domaine_application",
        "date de validite": "date_validite_document",
    },
}


def _cle(texte: str) -> str:
    """Normalise un libellé pour comparaison : sans accent, sans casse, espaces écrasés."""
    texte = texte.replace("\u2019", "'").replace("\u2018", "'")
    decompose = unicodedata.normalize("NFKD", texte)
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sans_accents).strip().casefold()


def _est_titre_section(ligne: str) -> bool:
    """Vrai si la ligne ouvre une section (titre en capitales, numéroté, ou mot connu)."""
    texte = ligne.strip()
    if not texte or len(texte) > 90:
        return False
    if ":" in texte and not _MOTIF_TITRE_NUMEROTE.match(texte):
        return False
    if _MOTIF_TITRE_NUMEROTE.match(texte):
        return True
    lettres = [c for c in texte if c.isalpha()]
    if len(lettres) >= 4 and not any(c.islower() for c in lettres):
        return True
    cle = _cle(texte)
    # Un titre qui commence par un mot de section : « RÉFÉRENCES (résumé — …) ».
    # On exige que le mot soit **seul** ou suivi d'une parenthèse : une phrase métier
    # (« Qualification « étanchéité… » — organisme certificateur … ») n'est pas un titre.
    for mot in _MOTS_SECTIONS:
        for forme in (mot, mot + "s"):
            if cle == forme or cle.startswith(forme + " (") or cle.startswith(forme + "("):
                return True
    return False


def _titre_contient(titre: Optional[str], mot: str) -> bool:
    return bool(titre) and mot in _cle(titre or "")


def _montant_texte(brut: str) -> str:
    """« 1 500 000 » → « 1500000 » ; « 412,5 » → « 412.5 ». Aucun arrondi, aucune invention."""
    texte = re.sub(r"[\s\u00a0\u202f]", "", brut.strip()).rstrip(".,")
    if "," in texte and "." in texte:
        texte = texte.replace(",", "")
    elif "," in texte:
        texte = texte.replace(",", ".")
    return texte


def _valeur_champ(entite: str, champ: str, valeur: str) -> Optional[dict[str, str]]:
    """Valeur proposée pour un champ, ou `None` si le document n'en donne pas d'exploitable."""
    brut = valeur.strip()
    if not brut or _cle(brut) in _VALEURS_VIDES:
        return None
    type_connu = type_champ(entite, champ)
    if type_connu == "date":
        iso = _date_iso(brut)
        return {champ: iso} if iso else None
    if type_connu == "entier":
        nombre = re.search(r"\d[\d\s]*", brut)
        return {champ: re.sub(r"\s", "", nombre.group(0))} if nombre else None
    if champ.endswith("_montant"):
        montant = _MOTIF_MONTANT.search(brut)
        if not montant:
            return None
        sortie = {champ: _montant_texte(montant.group("montant"))}
        base_devise = champ[: -len("_montant")] + "_devise"
        if definition_entite(entite).champ_autorise(base_devise):
            devise = montant.group("devise")
            sortie[base_devise] = (
                "EUR" if devise.casefold() in {"eur", "€", "euro", "euros"} else devise
            )
        return sortie
    if champ in ("siren", "siret_siege"):
        chiffres = re.search(r"\d[\d\s]*", brut)
        return {champ: re.sub(r"\s", "", chiffres.group(0))} if chiffres else None
    if champ == "telephone":
        numero = _MOTIF_TELEPHONE.search(brut)
        return {champ: numero.group(0).strip()} if numero else None
    if champ in ("email", "courriel"):
        courriel = _MOTIF_EMAIL.search(brut)
        return {champ: courriel.group(0)} if courriel else None
    if champ == "code_ape_naf":
        return {champ: re.split(r"[\s—–(]", brut, maxsplit=1)[0]}
    return {champ: brut}

#: Dates reconnues.
_MOTIF_DATE_ISO = re.compile(r"\b(?P<annee>\d{4})-(?P<mois>\d{2})-(?P<jour>\d{2})\b")
_MOTIF_DATE_FR = re.compile(
    r"\b(?P<jour>\d{1,2})\s+(?P<mois>janvier|février|fevrier|mars|avril|mai|juin|juillet|"
    r"août|aout|septembre|octobre|novembre|décembre|decembre)\s+(?P<annee>\d{4})\b",
    re.IGNORECASE,
)

_MOIS_FR = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}

MENTION_FICTIF = "DOCUMENT FICTIF — DÉMONSTRATION"


def _titre_section(ligne: str) -> bool:
    return bool(_MOTIF_TITRE.match(ligne))


def _date_iso(ligne: str) -> Optional[str]:
    """Première date reconnue d'une ligne, en ISO 8601. `None` si aucune."""
    trouve = _MOTIF_DATE_ISO.search(ligne)
    if trouve:
        return f"{trouve.group('annee')}-{trouve.group('mois')}-{trouve.group('jour')}"
    trouve = _MOTIF_DATE_FR.search(ligne)
    if trouve:
        mois = _MOIS_FR[trouve.group("mois").casefold()]
        return f"{trouve.group('annee')}-{mois:02d}-{int(trouve.group('jour')):02d}"
    return None


class FournisseurFactice(FournisseurModele):
    """Fournisseur déterministe, **sans aucune capacité d'interprétation**."""

    nom = "factice"
    modele = "regles-de-lecture-v1"

    @property
    def avertissement(self) -> str:
        return (
            "Fournisseur factice — non-IQ réel : règles de lecture mécaniques, sans modèle "
            "de langage. Aucun élément n'est compris ni déduit ; les tests ne prouvent donc "
            "pas la qualité d'une analyse par un vrai modèle (risque R3)."
        )

    def description(self) -> str:
        return f"{self.nom} ({self.modele}) — non-IQ réel, hors réseau"

    # -- analyse ---------------------------------------------------------------
    def analyser(self, extraction: ExtractionPdf) -> ResultatAnalyse:
        propositions: list[PropositionElement] = []
        for page in extraction.pages:
            propositions.extend(self._lire_page(page))
        return ResultatAnalyse(
            propositions=tuple(propositions),
            fournisseur=self.nom,
            modele=self.modele,
            avertissement=self.avertissement,
        )

    # -- import guidé ---------------------------------------------------------- #
    def proposer_elements(
        self, extraction: ExtractionPdf, *, famille_cible: str
    ) -> tuple[PropositionImport, ...]:
        """Lit un document existant et propose des éléments de bibliothèque sourcés.

        Règles de lecture (mécaniques, jamais d'interprétation) :

        ``I1 — entité``
            une ligne ``Entité : <nom_entite>`` ouvre un bloc pour cette entité ;
        ``I2 — champs``
            dans un bloc, chaque ligne ``- <champ> : <valeur>`` ajoute un champ ;
            les champs consécutifs forment **un seul** élément proposé ;
        ``I3 — rien d'autre``
            hors d'un bloc d'entité, aucune ligne n'est lue ; un champ non reconnu du
            domaine n'est pas filtré ici (le service le refuse), et un bloc sans champ
            ne produit rien.
        ``I4 — français métier``
            si le document n'est pas au micro-format, il est relu comme un document
            d'entreprise courant (voir `_LecteurFrancais`) : lignes ``Libellé : valeur``
            et sections titrées, **orientées par `famille_cible`**.

        `famille_cible` **oriente** la lecture : seules les entités de cette famille
        sont proposées (c'est aussi ce que le service accepte). Le factice ne voit que
        le texte extrait, jamais le fichier.
        """
        micro = self._propositions_micro(extraction)
        if micro:
            return micro
        entites_admises = FAMILLE_VERS_ENTITES.get(famille_cible, ())
        lecteur = _LecteurFrancais(extraction)
        propositions: list[PropositionImport] = []
        for entite in entites_admises:
            propositions.extend(lecteur.propositions(entite))
        return tuple(propositions)

    def _propositions_micro(self, extraction: ExtractionPdf) -> tuple[PropositionImport, ...]:
        """Micro-format ``Entité : …`` / ``- champ : valeur`` (règles I1–I3)."""
        propositions: list[PropositionImport] = []
        for page in extraction.pages:
            propositions.extend(self._lire_import_page(page))
        return tuple(propositions)

    def _lire_import_page(self, page: PageExtraite) -> list[PropositionImport]:
        if not page.analyseable:
            return []

        resultats: list[PropositionImport] = []
        entite: Optional[str] = None
        champs: dict[str, str] = {}
        lignes_bloc: list[str] = []

        def vider() -> None:
            if entite and champs:
                resultats.append(
                    PropositionImport(
                        entite_cible=entite,
                        champs_proposes=dict(champs),
                        source_emplacement=f"page {page.numero} — entité « {entite} »",
                        source_extrait="\n".join(lignes_bloc),
                        libelle=(f"{entite} : {', '.join(champs)}")[:255],
                    )
                )

        for brute in page.texte.splitlines():
            ligne = brute.rstrip()
            entite_lue = _MOTIF_ENTITE_IMPORT.match(ligne)
            if entite_lue:
                vider()
                entite = entite_lue.group("entite")
                champs = {}
                lignes_bloc = []
                continue
            if entite is None:
                continue
            champ = _MOTIF_CHAMP_IMPORT.match(ligne)
            if not champ:
                continue
            champs[champ.group("champ")] = champ.group("valeur")
            lignes_bloc.append(ligne.strip())

        vider()
        return resultats

    # -- lecture d'une page ---------------------------------------------------- #
    def _lire_page(self, page: PageExtraite) -> list[PropositionElement]:
        if not page.analyseable:
            # Une page non analysable ne produit rien : elle n'est jamais devinée.
            return []

        resultats: list[PropositionElement] = []
        section: Optional[str] = None
        type_section: Optional[str] = None
        date_limite_vue = False

        for brute in page.texte.splitlines():
            ligne = brute.rstrip()
            if _titre_section(ligne):
                section = ligne.strip()
                if _MOTIF_SECTION_PIECES.search(section):
                    type_section = "pieces"
                elif _MOTIF_SECTION_CRITERES.search(section):
                    type_section = "criteres"
                elif _MOTIF_SECTION_DATE.search(section):
                    type_section = "date"
                else:
                    type_section = None
                continue

            if type_section is None:
                continue

            emplacement = (
                f"page {page.numero} — section « {section} »" if section
                else f"page {page.numero}"
            )

            if type_section == "pieces":
                liste = _MOTIF_LIGNE_LISTE.match(ligne)
                if liste:
                    resultats.append(
                        PropositionElement(
                            categorie="piece_exigee",
                            libelle=liste.group("contenu"),
                            source_emplacement=emplacement,
                            source_extrait=liste.group("contenu"),
                        )
                    )
                continue

            if type_section == "criteres":
                critere = _MOTIF_CRITERE.match(ligne)
                if critere:
                    resultats.append(
                        PropositionElement(
                            categorie="critere",
                            libelle=critere.group("libelle"),
                            valeur=f"{critere.group('ponderation')} %",
                            source_emplacement=emplacement,
                            source_extrait=ligne.strip(),
                        )
                    )
                continue

            if type_section == "date" and not date_limite_vue:
                date_iso = _date_iso(ligne)
                if date_iso:
                    date_limite_vue = True
                    resultats.append(
                        PropositionElement(
                            categorie="date_limite",
                            libelle=ligne.strip(),
                            valeur=date_iso,
                            source_emplacement=emplacement,
                            source_extrait=ligne.strip(),
                        )
                    )
        return resultats


# --------------------------------------------------------------------------- #
# Règle I4 — lecture d'un document courant en français métier
# --------------------------------------------------------------------------- #
def _entrees(lignes: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Découpe les lignes d'une section en entrées : une entrée s'achève au point."""
    entrees: list[list[tuple[int, str]]] = []
    courant: list[tuple[int, str]] = []
    for page, ligne in lignes:
        if not ligne.strip():
            continue
        courant.append((page, ligne.strip()))
        if ligne.rstrip().endswith("."):
            entrees.append(courant)
            courant = []
    if courant:
        entrees.append(courant)
    return entrees


def _entre_guillemets(texte: str) -> Optional[str]:
    trouve = re.search(r"«\s*(?P<contenu>[^»]+?)\s*»", texte)
    return trouve.group("contenu").strip() if trouve else None


def _intitule_reference(texte: str) -> str:
    """L'intitulé d'une référence : le texte qui précède l'année ou le montant."""
    annee = re.search(r"\b(?:19|20)\d{2}\b", texte)
    if annee:
        return texte[: annee.start()].strip(" ,;.–-")
    return texte.strip()


def _quantite_et_designation(item: str) -> tuple[Optional[int], str]:
    """« deux nacelles » → (2, « nacelles ») ; « 3 camions » → (3, « camions »)."""
    mots = item.split()
    if not mots:
        return None, item
    premier = _cle(mots[0])
    if premier in _NOMBRES_FR:
        return _NOMBRES_FR[premier], " ".join(mots[1:]).strip()
    if mots[0].isdigit():
        return int(mots[0]), " ".join(mots[1:]).strip()
    return None, item


class _LecteurFrancais:
    """Lecture mécanique d'un document d'entreprise courant (règle I4).

    Ne « comprend » rien : découpe le texte en blocs titrés, lit les lignes
    ``Libellé : valeur`` et les listes de sections connues, puis n'assemble que des
    valeurs **littéralement écrites** dans le document. Aucune proposition n'est
    produite sans extrait présent : le garde-fou de source reste appliqué par le
    service, inchangé.
    """

    def __init__(self, extraction: ExtractionPdf) -> None:
        self._blocs: list[tuple[Optional[str], int, list[tuple[int, str]]]] = []
        self._construire(extraction)

    def _construire(self, extraction: ExtractionPdf) -> None:
        titre: Optional[str] = None
        page_titre = 1
        contenu: list[tuple[int, str]] = []
        for page in extraction.pages:
            if not page.analyseable:
                continue
            for brute in page.texte.splitlines():
                ligne = brute.rstrip()
                if not ligne.strip():
                    continue  # ligne vide : simple mise en page, jamais du contenu
                if not any(c.isalnum() for c in ligne):
                    # Ligne de séparation (« ==== ») : elle ferme le bloc courant et
                    # n'appartient à aucun contenu (jamais recopiée dans un extrait).
                    if contenu:
                        self._blocs.append((titre, page_titre, contenu))
                        contenu = []
                        titre = None
                    continue
                if _est_titre_section(ligne):
                    self._blocs.append((titre, page_titre, contenu))
                    titre = ligne.strip()
                    page_titre = page.numero
                    contenu = []
                    continue
                contenu.append((page.numero, ligne.strip()))
        self._blocs.append((titre, page_titre, contenu))
        self._blocs = [bloc for bloc in self._blocs if bloc[2]]

    # -- API ---------------------------------------------------------------- #
    def propositions(self, entite: str) -> list[PropositionImport]:
        lecteurs = {
            "entreprise_version": self._champs_francais,
            "assurance": self._champs_francais,
            "attestation": self._champs_francais,
            "produit": self._champs_francais,
            "certification": self._certifications,
            "reference_chantier": self._references,
            "moyen_materiel": self._moyens_materiels,
            "organigramme": self._organigramme,
            "chapitre_memoire": self._chapitres,
        }
        lecteur = lecteurs.get(entite)
        return lecteur(entite) if lecteur else []

    # -- champs « Libellé : valeur » ---------------------------------------- #
    def _champs_francais(self, entite: str) -> list[PropositionImport]:
        correspondance = _LIBELLES_VERS_CHAMP.get(entite, {})
        if not correspondance:
            return []
        definition = definition_entite(entite)
        resultats: list[PropositionImport] = []
        for titre, page_titre, lignes in self._blocs:
            champs: dict[str, str] = {}
            for index, (_page, ligne) in enumerate(lignes):
                trouve = _MOTIF_CHAMP_FR.match(ligne)
                if not trouve:
                    continue
                champ = correspondance.get(_cle(trouve.group("libelle")))
                if not champ or not definition.champ_autorise(champ):
                    continue
                valeur = trouve.group("valeur").strip()
                # Une valeur qui se poursuit sur la ligne suivante (retour à la ligne
                # du document) : on la recolle, jamais ne l'invente.
                suivant = index + 1
                while suivant < len(lignes) and valeur and valeur[-1] not in ".!;":
                    suite = lignes[suivant][1]
                    if (
                        _MOTIF_CHAMP_FR.match(suite)
                        or _est_titre_section(suite)
                        or not suite[:1].islower()
                    ):
                        break
                    valeur = f"{valeur} {suite}"
                    suivant += 1
                ajout = _valeur_champ(entite, champ, valeur)
                if ajout:
                    champs.update(ajout)
            if champs:
                resultats.append(
                    self._proposition(entite, champs, titre, page_titre, lignes)
                )
        return resultats

    # -- sections ----------------------------------------------------------- #
    def _references(self, entite: str) -> list[PropositionImport]:
        resultats: list[PropositionImport] = []
        for titre, _page_titre, lignes in self._blocs:
            if not _titre_contient(titre, "reference"):
                continue
            for entree in _entrees(lignes):
                texte = " ".join(ligne for _p, ligne in entree)
                montant = _MOTIF_MONTANT.search(texte)
                annee = re.search(r"\b(?:19|20)\d{2}\b", texte)
                if not montant and not annee:
                    continue  # une ligne de pied de page n'est pas une référence
                intitule = _intitule_reference(texte)
                if not intitule:
                    continue
                champs = {"intitule_operation": intitule}
                if montant:
                    champs["montant_montant"] = _montant_texte(montant.group("montant"))
                    champs["montant_devise"] = "EUR"
                resultats.append(
                    PropositionImport(
                        entite_cible=entite,
                        champs_proposes=champs,
                        source_emplacement=(
                            f"page {entree[0][0]} — section « {titre} »"
                        )[:255],
                        source_extrait=texte,
                        libelle=intitule[:255],
                    )
                )
        return resultats

    def _moyens_materiels(self, entite: str) -> list[PropositionImport]:
        resultats: list[PropositionImport] = []
        for titre, page_titre, lignes in self._blocs:
            if not _titre_contient(titre, "moyens materiels"):
                continue
            paragraphe = " ".join(ligne for _p, ligne in lignes)
            for item in re.split(r"[,;]", paragraphe):
                item = item.strip().rstrip(".")
                if len(item) < 3 or not any(c.isalpha() for c in item):
                    continue
                nombre, designation = _quantite_et_designation(item)
                if not designation:
                    continue
                champs = {"designation": designation}
                if nombre is not None:
                    champs["quantite"] = str(nombre)
                resultats.append(
                    PropositionImport(
                        entite_cible=entite,
                        champs_proposes=champs,
                        source_emplacement=(
                            f"page {page_titre} — section « {titre} »"
                        )[:255],
                        source_extrait=item,
                        libelle=designation[:255],
                    )
                )
        return resultats

    def _certifications(self, entite: str) -> list[PropositionImport]:
        resultats: list[PropositionImport] = []
        for titre, _page_titre, lignes in self._blocs:
            if not (
                _titre_contient(titre, "qualification")
                or _titre_contient(titre, "certification")
            ):
                continue
            for entree in _entrees(lignes):
                texte = " ".join(ligne for _p, ligne in entree)
                champs: dict[str, str] = {}
                intitule = _entre_guillemets(texte)
                if intitule:
                    champs["intitule"] = intitule
                organisme = re.search(
                    r"organisme certificateur\s*:?\s*(?P<organisme>[^,]+)",
                    texte,
                    re.IGNORECASE,
                )
                if organisme:
                    champs["organisme"] = organisme.group("organisme").strip()
                numero = re.search(
                    r"num[eé]ro\s*:?\s*(?P<numero>[A-Za-z0-9][\w\-/]*)",
                    texte,
                    re.IGNORECASE,
                )
                if numero:
                    champs["numero_certificat"] = numero.group("numero")
                date = _date_iso(texte)
                if date:
                    champs["date_obtention"] = date
                if champs:
                    resultats.append(
                        PropositionImport(
                            entite_cible=entite,
                            champs_proposes=champs,
                            source_emplacement=(
                                f"page {entree[0][0]} — section « {titre} »"
                            )[:255],
                            source_extrait=texte,
                            libelle=(intitule or texte)[:255],
                        )
                    )
        return resultats

    def _chapitres(self, entite: str) -> list[PropositionImport]:
        """Chapitres numérotés d'un mémoire technique (« 1. OBJET … »)."""
        resultats: list[PropositionImport] = []
        for titre, page_titre, lignes in self._blocs:
            numero = _MOTIF_TITRE_NUMEROTE.match(titre or "")
            if not numero:
                continue
            titre_chapitre = numero.group("titre").strip()
            if not titre_chapitre:
                continue
            contenu = " ".join(ligne for _p, ligne in lignes)
            champs = {"titre": titre_chapitre, "ordre": numero.group("ordre")}
            if contenu:
                champs["contenu_texte"] = contenu
            resultats.append(
                PropositionImport(
                    entite_cible=entite,
                    champs_proposes=champs,
                    source_emplacement=(
                        f"page {page_titre} — section « {titre_chapitre} »"
                    )[:255],
                    source_extrait="\n".join([titre or ""] + [l for _p, l in lignes]),
                    libelle=titre_chapitre[:255],
                )
            )
        return resultats

    def _organigramme(self, entite: str) -> list[PropositionImport]:
        resultats: list[PropositionImport] = []
        for titre, page_titre, lignes in self._blocs:
            if not any(
                _titre_contient(titre, mot)
                for mot in ("moyens humains", "moyens affectes", "equipes", "effectif")
            ):
                continue
            paragraphe = " ".join(ligne for _p, ligne in lignes)
            if len(paragraphe) < 10:
                continue
            resultats.append(
                PropositionImport(
                    entite_cible=entite,
                    champs_proposes={"description": paragraphe},
                    source_emplacement=(
                        f"page {page_titre} — section « {titre} »"
                    )[:255],
                    source_extrait=paragraphe,
                    libelle=paragraphe[:255],
                )
            )
        return resultats

    # -- assemblage --------------------------------------------------------- #
    def _proposition(
        self,
        entite: str,
        champs: dict[str, str],
        titre: Optional[str],
        page: int,
        lignes: list[tuple[int, str]],
    ) -> PropositionImport:
        emplacement = f"page {page} — section « {titre} »" if titre else f"page {page}"
        return PropositionImport(
            entite_cible=entite,
            champs_proposes=dict(champs),
            source_emplacement=emplacement[:255],
            source_extrait="\n".join(ligne for _p, ligne in lignes),
            libelle=(f"{entite} : {', '.join(champs)}")[:255],
        )
