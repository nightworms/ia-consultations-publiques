"""Contrôles transverses : fuites de données et dépassement de périmètre.

Deux exigences du lot L8 :

* **contrôle de fuite** — rechercher dans le dépôt les motifs qui trahiraient une
  donnée réelle ou un secret (SIRET à 14 chiffres, IBAN, clés privées, mots de
  passe, en-têtes de documents réels). Le **résultat est joint**, y compris si un
  motif est trouvé : un motif non expliqué fait **échouer** le test ;
* **contrôle de périmètre** — rechercher les fonctionnalités hors périmètre
  (paiement, veille, dépôt de pli, signature, tarifs) dans le code livré. Toute
  occurrence doit être un **refus** ou un renvoi « hors périmètre », jamais une
  fonctionnalité.

Le test échoue s'il trouve une valeur suspecte : c'est le comportement voulu — un
défaut se rapporte, il ne se contourne pas.
"""

from __future__ import annotations

import re
from pathlib import Path

from .conftest import MOT_DE_PASSE_FICTIF

RACINE = Path(__file__).resolve().parents[3]

#: Dossiers exclus du balayage (dépendances, cache, données hors dépôt).
_EXCLUS = {".venv", ".git", "__pycache__", ".pytest_cache", "data", "node_modules"}

#: Extensions textuelles balayées (les binaires — PDF — sont hors périmètre de motifs).
_EXTENSIONS = {".py", ".md", ".txt", ".sql", ".sh", ".html", ".css", ".toml", ".cfg", ".ini", ".example"}

_MOTIFS = {
    "SIRET_14_chiffres": re.compile(r"\b(\d{14})\b"),
    "IBAN": re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b"),
    "cle_privee": re.compile(r"-----BEGIN [A-Z ]*(PRIVATE KEY|RSA|OPENSSH)[A-Z ]*-----"),
    "entete_html_reelle": re.compile(r"<!DOCTYPE\s+html", re.IGNORECASE),
}


def _fichiers() -> list[Path]:
    fichiers: list[Path] = []
    ce_fichier = Path(__file__).resolve()
    for chemin in RACINE.rglob("*"):
        if any(part in _EXCLUS for part in chemin.parts):
            continue
        if chemin.is_file() and chemin.suffix.casefold() in _EXTENSIONS:
            # Le scanner lui-même contient les motifs recherchés : il s'auto-exclut.
            if chemin.resolve() == ce_fichier:
                continue
            fichiers.append(chemin)
    return sorted(fichiers)


def _valeur_fictive(motif: str, valeur: str) -> bool:
    """Vrai si la valeur trouvée est **manifestement** fictive (donc tolérée)."""
    if motif == "SIRET_14_chiffres":
        return set(valeur) == {"0"}
    if motif == "IBAN":
        return set(valeur[4:]) == {"0"}
    return False


def test_controle_de_fuite_dans_le_depot():
    suspects: list[str] = []
    examinees = 0
    for chemin in _fichiers():
        try:
            texte = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:  # pragma: no cover
            continue
        examinees += 1
        suffixe = chemin.suffix.casefold()
        for nom, motif in _MOTIFS.items():
            # Un `<!DOCTYPE html>` dans un vrai gabarit HTML est légitime : on ne
            # cherche un en-tête de document que là où il n'a rien à faire.
            if nom == "entete_html_reelle" and suffixe in {".html", ".htm"}:
                continue
            for correspondance in motif.finditer(texte):
                valeur = (
                    correspondance.group(1)
                    if motif.groups
                    else correspondance.group(0)
                )
                if _valeur_fictive(nom, valeur):
                    continue
                ligne = texte[: correspondance.start()].count("\n") + 1
                suspects.append(
                    f"{chemin.relative_to(RACINE)}:{ligne} [{nom}] {valeur}"
                )

    # Mot de passe de test éventuellement recopié hors du fichier de fixtures :
    # sa présence n'est pas un secret (valeur fictive), mais on la compte.
    occurrences_mdp = 0
    for chemin in _fichiers():
        try:
            occurrences_mdp += chemin.read_text(encoding="utf-8", errors="ignore").count(
                MOT_DE_PASSE_FICTIF
            )
        except OSError:  # pragma: no cover
            continue

    print(f"\n[fuite] fichiers textuels examinés : {examinees}")
    print(f"[fuite] occurrences du mot de passe de test (fictif) : {occurrences_mdp}")
    print(f"[fuite] motifs non expliqués : {len(suspects)}")
    for suspect in suspects:
        print("   -", suspect)

    assert suspects == [], (
        "motif pouvant trahir une donnée réelle ou un secret : " + "; ".join(suspects)
    )


def test_aucun_secret_ni_fichier_sensible_versionne():
    for chemin in RACINE.rglob("*"):
        if any(part in _EXCLUS for part in chemin.parts):
            continue
        if chemin.is_file() and chemin.suffix.casefold() in {".env", ".key", ".pem", ".secret"}:
            raise AssertionError(f"fichier sensible présent dans le dépôt : {chemin}")
    # `.gitignore` doit couvrir les fichiers sensibles et `data/`.
    contenu = (RACINE / ".gitignore").read_text(encoding="utf-8")
    for attendu in ("data/", ".env", "*.key", "*.pem"):
        assert attendu in contenu, f".gitignore ne couvre pas {attendu!r}"


# --------------------------------------------------------------------------- #
# Périmètre
# --------------------------------------------------------------------------- #
#: Termes du hors-périmètre (`docs/PLAN-PHASE-3.md` § 2).
_TERMES_HORS_PERIMETRE = (
    "paiement",
    "chiffrage",
    "veille",
    "appel d'offres",
    "appels d'offres",
    "dépôt de pli",
    "depot de pli",
    "signature électronique",
    "signature electronique",
    "tarif",
    "marge",
    "prix",
)

#: Marqueurs d'un refus / renvoi hors périmètre (l'occurrence est alors légitime).
_MARQUEURS_REFUS = (
    "jamais",
    "aucun",
    "aucune",
    "hors périmètre",
    "hors perimetre",
    "interdit",
    "pas de",
    "n'est pas",
    "ne garantit",
    "refus",
    "refuse",
    "exclu",
    "ne ",
    "ni ",
    "pas un",
    "pas une",
    "n'ajoute",
    "n'existe",
    "aucun prix",
    "hors de ce",
    "sans ",
)


def test_aucune_fonctionnalite_hors_perimetre_dans_le_code():
    """Le code livré ne porte aucune fonctionnalité hors périmètre."""
    importées: list[str] = []
    for chemin in _fichiers():
        relative = chemin.relative_to(RACINE)
        # On contrôle le **code livré** et les écrans, pas la documentation ni les
        # tests (un test doit bien citer ce qu'il vérifie être refusé).
        if relative.parts[0] not in {"src", "scripts"}:
            continue
        if len(relative.parts) > 1 and relative.parts[1] == "tests":
            continue
        if chemin.suffix.casefold() not in {".py", ".html", ".css", ".sql", ".sh"}:
            continue
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        for numero, ligne in enumerate(texte.splitlines(), start=1):
            bas = ligne.casefold()
            for terme in _TERMES_HORS_PERIMETRE:
                # Correspondance sur le **mot** entier : « surveiller » ne doit pas
                # déclencher « veille ».
                if re.search(rf"\b{re.escape(terme)}\b", bas) and not any(
                    m in bas for m in _MARQUEURS_REFUS
                ):
                    importées.append(f"{relative}:{numero} [{terme}] {ligne.strip()[:120]}")

    print(f"\n[périmètre] occurrences hors-périmètre non justifiées : {len(importées)}")
    for occurrence in importées:
        print("   -", occurrence)
    assert importées == [], (
        "fonctionnalité potentiellement hors périmètre dans le code : "
        + "; ".join(importées)
    )


def test_script_provisionnement_ne_fuit_aucun_secret():
    """Le script d'exploitant ne laisse fuir aucun mot de passe."""
    import importlib.util
    import io
    from contextlib import redirect_stderr

    chemin = RACINE / "scripts" / "provisionnement.py"
    texte = chemin.read_text(encoding="utf-8")
    # Aucun mot de passe codé en dur dans la source du script.
    assert not re.search(r"mot_de_passe\s*=\s*['\"][^'\"]+['\"]", texte), (
        "un mot de passe semble codé en dur dans le script"
    )

    spec = importlib.util.spec_from_file_location("script_provisionnement_qa", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sortie_erreur = io.StringIO()
    with redirect_stderr(sortie_erreur):
        code = module.main(
            [
                "--libelle-client",
                "Client refusé — contrôle L8",
                "--identifiant",
                "refus-l8@demo.test",
                "--mot-de-passe",
                MOT_DE_PASSE_FICTIF,
            ]
        )
    assert code == 2, "le script doit refuser un mot de passe passé en argument"
    assert MOT_DE_PASSE_FICTIF not in sortie_erreur.getvalue(), (
        "le mot de passe apparaît dans la sortie du script"
    )
    print("\n[provisionnement] script : refus d'un mot de passe en argument (code 2), aucune fuite")

