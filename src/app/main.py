"""Application FastAPI — point d'entrée exécutable (annexe A § A3).

Démarrage local (aucun port exposé sur Internet) :

    cd src && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

La configuration est chargée au démarrage depuis l'environnement ; une variable
obligatoire absente fait **échouer le démarrage** plutôt que de tourner avec une
valeur par défaut silencieuse.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import (
    routes_analyse,
    routes_authentification,
    routes_bibliotheque,
    routes_checklist,
    routes_provisionnement,
)
from app.config import charger_config
from app.web import routes_web

DESCRIPTION = (
    "Socle technique — bibliothèque d'entreprise et analyse de consultations "
    "publiques. Brouillon : aucune sortie du produit ne vaut signature ni "
    "garantie de conformité."
)


@asynccontextmanager
async def cycle_de_vie(app: FastAPI) -> AsyncIterator[None]:
    """Charge la configuration (échec explicite si incomplète) au démarrage."""
    app.state.config = charger_config()
    yield


app = FastAPI(
    title="ia-consultations-publiques — socle",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=cycle_de_vie,
)

app.include_router(routes_authentification.router)
app.include_router(routes_analyse.router)
app.include_router(routes_bibliotheque.router)
app.include_router(routes_provisionnement.router)
app.include_router(routes_checklist.router)

# Écrans HTML rendus côté serveur (annexe A § A8) et leur feuille de style.
# Aucune route `/api/v1` n'est créée ni modifiée ici : les écrans appellent les
# services (`app.services`) directement, comme le font les routes JSON.
app.include_router(routes_web.router)
app.mount(
    "/static",
    StaticFiles(directory=str(routes_web.REPERTOIRE_STATIQUE)),
    name="statique",
)


@app.get("/")
def racine() -> Dict[str, str]:
    """Racine de service : identifie l'application, ne révèle aucune donnée."""
    return {
        "application": "ia-consultations-publiques",
        "version": "0.1.0",
        "documentation": "/docs",
    }


def main() -> None:  # pragma: no cover — lancement manuel
    """Lance le serveur local (uvicorn)."""
    import uvicorn

    config = charger_config()
    uvicorn.run(app, host=config.hote_api, port=config.port_api)


if __name__ == "__main__":  # pragma: no cover
    main()
