"""Contrôle du critère 6 (carte t_ebbaac86) sur l'application réellement servie.

Se connecte à l'application lancée localement (``uvicorn`` sur 127.0.0.1:8098,
base de démonstration jetable ``ia_consultations_c6demo``), ouvre chaque écran,
retire les blocs repliés « Références techniques » (``<details>``) puis cherche
dans le texte **visible sans action de l'utilisateur** :

- les codes entre crochets ``[attestation_assurance_decennale]`` ;
- les valeurs de nomenclature brutes ``responsabilite_civile_decennale``.

Critère 6 tel que reformulé par ``docs/DECISIONS.md`` D11.
"""

import os
import re
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8098"
IDENTIFIANT = "demo@exemple.invalid"
MOT_DE_PASSE = os.environ.get("MOT_DE_PASSE_DEMO") or ""
if not MOT_DE_PASSE:
    raise SystemExit(
        "MOT_DE_PASSE_DEMO absent : exportez-le (base de démonstration jetable "
        "uniquement). Aucun mot de passe n'est écrit dans ce fichier."
    )
CONSULTATION = "b3d0ff50-b7b9-457e-89f0-68415ca3cdf7"
SORTIE = Path(__file__).resolve().parents[1].parent / "docs/RAPPORTS/captures-c6/verif-live"

ECRANS = [
    ("accueil", "/accueil"),
    ("consultations", "/consultations"),
    ("analyse-dossier", f"/consultations/{CONSULTATION}"),
    ("checklist", f"/consultations/{CONSULTATION}/checklist"),
    ("memoire", f"/consultations/{CONSULTATION}/memoire"),
    ("bibliotheque", "/bibliotheque"),
    ("famille-assurances", "/bibliotheque/assurances"),
    ("famille-certifications", "/bibliotheque/certifications"),
    ("famille-moyens-materiels", "/bibliotheque/moyens-materiels"),
    ("famille-moyens-humains", "/bibliotheque/moyens-humains"),
    ("famille-references-chantiers", "/bibliotheque/references-chantiers"),
    ("famille-fiches-produits", "/bibliotheque/fiches-produits"),
    ("famille-capacites-financieres", "/bibliotheque/capacites-financieres"),
    ("import-guide", "/bibliotheque/import"),
    ("connexion", "/connexion"),
    ("page-inconnue", "/cette-page-nexiste-pas"),
]

RE_DETAILS = re.compile(r"<details\b.*?</details>", re.S | re.I)
RE_BALISE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
RE_TAG = re.compile(r"<[^>]+>")
RE_CROCHETS = re.compile(r"\[[a-z][a-z0-9_]*\]")
RE_CODE_UNDERSCORE = re.compile(r"\b(?:[a-z]{3,}_)+[a-z]{3,}\b")
# valeurs de nomenclature légitimes : SIREN, dates, UUID, empreintes, chemins
RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def texte_visible(html: str) -> str:
    sans_details = RE_DETAILS.sub(" ", html)
    sans_scripts = RE_BALISE.sub(" ", sans_details)
    return RE_TAG.sub(" ", sans_scripts)


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    anomalies: list[str] = []

    with httpx.Client(base_url=BASE, follow_redirects=True, timeout=30) as client:
        reponse = client.post(
            "/connexion", data={"identifiant": IDENTIFIANT, "mot_de_passe": MOT_DE_PASSE}
        )
        print(f"connexion : {reponse.status_code} {reponse.url}")
        assert "connexion" not in str(reponse.url), "connexion refusee"

        for nom, chemin in ECRANS:
            r = client.get(chemin)
            (SORTIE / f"{nom}.html").write_text(r.text, encoding="utf-8")
            visible = texte_visible(r.text)
            (SORTIE / f"{nom}.txt").write_text(visible, encoding="utf-8")

            crochets = RE_CROCHETS.findall(visible)
            codes = RE_CODE_UNDERSCORE.findall(visible)
            # un texte mot_a_mot est légitime s'il est un identifiant technique
            # déjà replié : ici rien ne doit rester, hors mots du dictionnaire.
            etat = "OK" if not crochets and not codes else "ANOMALIE"
            detail = ""
            if crochets:
                detail += f" crochets={sorted(set(crochets))}"
                anomalies.append(f"{nom} : crochets {sorted(set(crochets))}")
            if codes:
                detail += f" codes={sorted(set(codes))}"
                anomalies.append(f"{nom} : codes {sorted(set(codes))}")
            print(f"{etat:9s} {chemin:70s} {r.status_code} {len(visible):6d} car.{detail}")

    print()
    if anomalies:
        print("ANOMALIES (critere 6, texte visible sans deplier) :")
        for a in anomalies:
            print(" -", a)
        return 1
    print("Aucune anomalie : aucun crochet ni valeur de code dans le texte visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
