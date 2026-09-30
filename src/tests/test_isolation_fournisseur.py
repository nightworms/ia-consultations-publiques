"""Verrou d'isolation de la suite — correctif C2.

Ces tests ne vérifient pas le produit : ils vérifient **la suite de tests
elle-même**. Sans eux, rien n'empêcherait la garde posée dans `conftest.py`
d'être retirée un jour sans que personne ne s'en aperçoive.

Ce qui est verrouillé :

1. `MODELE_FOURNISSEUR` vaut `factice` pendant les tests, quelle que soit la
   valeur demandée par le `.env` local ;
2. la suite **refuse de démarrer** (`pytest.UsageError`) si cette propriété
   n'est pas tenue — le cas est provoqué ici pour de vrai ;
3. aucun appel réseau sortant n'est possible : connexion brute, résolution de
   nom, envoi UDP et client HTTP `httpx` échouent tous bruyamment ;
4. le bouclage reste autorisé, sinon PostgreSQL local serait injoignable.

Aucune donnée réelle, aucune clé, aucun appel réseau réel n'est utilisé ici :
les cibles sont des adresses de documentation (RFC 5737) et un domaine
`.invalid` (RFC 2606), qui ne peuvent par construction être joignables.
"""

from __future__ import annotations

import os
import socket

import httpx
import pytest

import garde_isolation
from app.services.extraction_pdf import ExtractionPdf, PageExtraite
from app.services.fournisseur_modele import (
    ErreurFournisseurModele,
    FournisseurFactice,
    creer_fournisseur,
)
from app.services.fournisseur_modele.fournisseur_ue import FournisseurUe

#: Adresse de documentation RFC 5737 — jamais routable, jamais jointe.
ADRESSE_EXTERIEURE = ("192.0.2.1", 80)
#: Domaine réservé RFC 2606 — jamais résoluble.
HOTE_EXTERIEUR = "exemple-fictif.invalid"


def _extraction() -> ExtractionPdf:
    return ExtractionPdf(
        source="fictif.txt",
        pages=(
            PageExtraite(
                numero=1,
                texte="DOCUMENT FICTIF — DÉMONSTRATION\nARTICLE 2 — PIÈCES EXIGÉES\n"
                "- Attestation d'assurance décennale\n",
                methode="texte",
                analyseable=True,
            ),
        ),
    )


# --------------------------------------------------------------------------- #
# 1 et 2. Le fournisseur est imposé, et la suite refuse de tourner sans cela
# --------------------------------------------------------------------------- #
def test_la_suite_impose_le_fournisseur_factice():
    """Le `.env` local ne décide pas du verdict : la suite tranche."""
    etat = garde_isolation.etat_fournisseur()
    assert etat["applique"] is True, (
        "Le forçage du fournisseur n'a pas été appliqué : src/tests/conftest.py "
        "doit appeler garde_isolation.forcer_fournisseur_factice()."
    )
    assert garde_isolation.FOURNISSEUR_IMPOSE == "factice"

    valeur_effective = os.environ.get(garde_isolation.NOM_VARIABLE_FOURNISSEUR)
    assert valeur_effective == "factice", (
        f"Pendant les tests, MODELE_FOURNISSEUR doit valoir 'factice' (imposé par la "
        f"suite), reçu {valeur_effective!r}. Valeur demandée par l'environnement avant "
        f"forçage : {etat['demande']!r}. Un fournisseur réel configuré dans le .env "
        "rendrait la suite non reproductible et pourrait joindre un service extérieur."
    )

    assert isinstance(creer_fournisseur(), FournisseurFactice), (
        "creer_fournisseur() doit rendre le fournisseur factice pendant les tests, "
        "même si le .env local configure un fournisseur réel "
        f"(demandé : {etat['demande']!r})."
    )


def test_le_verrou_arrete_la_suite_si_le_fournisseur_change(monkeypatch):
    """Le contrôle de démarrage échoue réellement si l'isolation est défaite.

    On simule ce qu'un `.env` ferait : `MODELE_FOURNISSEUR=ue` au démarrage des
    tests. `verifier_isolation()` (appelé par `pytest_sessionstart`) doit lever
    `pytest.UsageError` — c'est-à-dire arrêter la suite — et expliquer pourquoi.
    """
    monkeypatch.setenv(garde_isolation.NOM_VARIABLE_FOURNISSEUR, "ue")
    with pytest.raises(pytest.UsageError) as exc:
        garde_isolation.verifier_isolation()

    message = str(exc.value)
    assert "ISOLATION DES TESTS NON APPLIQUÉE" in message
    assert garde_isolation.NOM_VARIABLE_FOURNISSEUR in message
    assert "ue" in message
    assert "reproductible" in message or "reproducti" in message


def test_verifier_isolation_ne_se_plaint_pas_quand_tout_est_en_place():
    garde_isolation.verifier_isolation()  # ne doit rien lever


def test_la_configuration_reelle_du_fournisseur_n_entre_pas_dans_les_tests():
    """La clé (et l'URL, le nom de modèle) du `.env` local ne sont pas dans le processus.

    On ne lit ni n'affiche jamais la valeur : on vérifie seulement son **absence**.
    Un test ne doit pas pouvoir consommer la clé d'Anthony par accident.
    """
    presentes = [nom for nom in garde_isolation.VARIABLES_FOURNISSEUR_REEL if nom in os.environ]
    assert presentes == [], (
        f"Variables du fournisseur réel encore présentes dans le processus de test : "
        f"{presentes}. Le `conftest.py` doit les retirer : une clé du `.env` local ne "
        "doit jamais être chargée par la suite."
    )


# --------------------------------------------------------------------------- #
# 3. Aucun appel réseau sortant n'est possible
# --------------------------------------------------------------------------- #
def test_connexion_sortante_brute_refusee():
    with pytest.raises(garde_isolation.ReseauInterdit) as exc:
        socket.create_connection(ADRESSE_EXTERIEURE, timeout=1)
    assert "192.0.2.1" in str(exc.value)


def test_socket_brut_sortant_refuse():
    with pytest.raises(garde_isolation.ReseauInterdit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect(ADRESSE_EXTERIEURE)


def test_envoi_udp_sortant_refuse():
    with pytest.raises(garde_isolation.ReseauInterdit):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b"x", ADRESSE_EXTERIEURE)


def test_resolution_d_un_nom_externe_refusee():
    """Bloquer la résolution coupe court à tout appel HTTP par nom d'hôte."""
    with pytest.raises(garde_isolation.ReseauInterdit) as exc:
        socket.getaddrinfo(HOTE_EXTERIEUR, 443)
    assert HOTE_EXTERIEUR in str(exc.value)


def test_client_http_python_ne_peut_pas_sortir():
    """Le chemin réellement utilisé par le fournisseur `ue` : `httpx`."""
    with pytest.raises((garde_isolation.ReseauInterdit, httpx.HTTPError)):
        httpx.post(f"https://{HOTE_EXTERIEUR}/v1/chat/completions", json={}, timeout=1)


def test_un_fournisseur_ue_configure_ne_peut_atteindre_aucun_reseau():
    """Même en configurant un fournisseur réel, l'appel échoue bruyamment.

    C'est la contre-épreuve du point 2 du correctif : un test ne doit jamais
    pouvoir joindre un vrai fournisseur, même si un `.env` en configure un.
    """
    fournisseur = FournisseurUe(
        url=f"https://{HOTE_EXTERIEUR}/v1/chat/completions",
        cle="cle-fictive-de-test",  # FICTIF — aucun secret ici
        modele="modele-fictif",
        organisme="Fournisseur fictif (UE)",
    )
    with pytest.raises((garde_isolation.ReseauInterdit, ErreurFournisseurModele)):
        fournisseur.analyser(_extraction())


# --------------------------------------------------------------------------- #
# 4. Le bouclage reste autorisé : PostgreSQL local en a besoin
# --------------------------------------------------------------------------- #
def test_le_bouclage_reste_autorise():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        # Port fermé : `connect_ex` rend un code d'erreur, il ne lève pas.
        code = sock.connect_ex(("127.0.0.1", 1))
    assert code != 0  # rien n'écoute sur ce port, mais la tentative n'est pas bloquée

    assert socket.getaddrinfo("localhost", None), "localhost doit rester résoluble"
    assert socket.getaddrinfo("127.0.0.1", 5432)


def test_le_poste_parle_toujours_a_postgresql():
    """La garde ne doit pas casser l'accès à la base de test locale."""
    from app.storage.connexion import ConnexionAdministration

    url = os.environ.get("DATABASE_URL", "")
    assert "127.0.0.1" in url or "localhost" in url, (
        "le test suppose la base locale ; vu : " + url.split("@")[-1]
    )
    conn = ConnexionAdministration(url).ouvrir()
    try:
        assert conn.lire("SELECT 1") == [(1,)]
    finally:
        conn.fermer()
