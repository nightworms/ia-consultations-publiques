#!/usr/bin/env bash
# charger_demo_phase4.sh — charge le jeu de DÉMONSTRATION FICTIF de la phase 4 (lot L7).
#
# Usage :  bash scripts/jeu-de-test/charger_demo_phase4.sh
#
# Ce que fait ce script, dans l'ordre :
#   1. charge le .env (variables obligatoires) ;
#   2. applique les migrations en attente ;
#   3. passe le fichier SQL du jeu (données non chiffrées, UUID fixes, idempotent) ;
#   4. appelle completer_demo_phase4.py : champs chiffrés par client, hachage
#      Argon2id du mot de passe de démonstration (saisie masquée), écriture des
#      pièces sources sur disque.
#
# AUCUN mot de passe n'est passé en argument ni écrit dans un fichier : il est
# demandé deux fois, en saisie masquée, par le script Python.
#
# Rien n'est exposé sur Internet. Le jeu est entièrement FICTIF (décision D10).

set -euo pipefail

PROJET="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJET"

if [ ! -f .env ]; then
  echo "ERREUR : le fichier .env est absent (copie .env.example et renseigne-le)." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

for v in DATABASE_URL CLE_CHIFFREMENT_MAITRESSE CLE_SESSION; do
  eval "valeur=\${$v:-}"
  if [ -z "$valeur" ]; then
    echo "ERREUR : variable obligatoire absente du .env : $v" >&2
    exit 1
  fi
done

echo "== 1/3  migrations =="
( cd src && ../.venv/bin/python -m app.storage.migrations up )

echo "== 2/3  jeu de démonstration (SQL) =="
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/jeu-de-test/0002_jeu_demo_phase4.sql

echo "== 3/3  champs chiffrés, compte de démonstration et pièces =="
.venv/bin/python scripts/jeu-de-test/completer_demo_phase4.py

cat <<'FIN'

------------------------------------------------------------
Jeu de démonstration chargé.

  Identifiant de connexion : demo@exemple.invalid
  Mot de passe             : celui que vous venez de saisir (il n'est écrit nulle part)

  Lancez l'application :  bash demarrer.sh
  Puis ouvrez           :  http://127.0.0.1:8000/connexion

  Mode opératoire en 6 étapes : scripts/jeu-de-test/DEMONSTRATION.md
------------------------------------------------------------
FIN
