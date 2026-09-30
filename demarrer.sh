#!/usr/bin/env bash
#  demarrer.sh — lance l'application en local, en une seule commande.
#
#  Usage :  bash demarrer.sh          (puis Ctrl-C pour arrêter)
#
#  Ce que fait ce script, dans l'ordre :
#    1. charge le fichier .env (les variables obligatoires)
#    2. vérifie que la base de données répond
#    3. applique les migrations en attente
#    4. démarre le serveur sur la boucle locale uniquement (127.0.0.1)
#    5. affiche l'adresse à ouvrir dans le navigateur
#
#  Rien n'est exposé sur Internet : le serveur n'écoute que sur ta machine.

set -eu

PROJET="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJET"

# --- 1. variables d'environnement -------------------------------------------
if [ ! -f .env ]; then
  echo "ERREUR : le fichier .env est absent."
  echo "        Copie .env.example vers .env et renseigne les variables obligatoires."
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

MANQUANTES=""
for v in DATABASE_URL CLE_CHIFFREMENT_MAITRESSE CLE_SESSION; do
  eval "valeur=\${$v:-}"
  [ -n "$valeur" ] || MANQUANTES="$MANQUANTES $v"
done
if [ -n "$MANQUANTES" ]; then
  echo "ERREUR : variables obligatoires absentes du .env :$MANQUANTES"
  exit 1
fi

PORT="${PORT_API:-8000}"
HOTE="${HOTE_API:-127.0.0.1}"

# --- déjà en marche ? --------------------------------------------------------
if curl -s --max-time 3 "http://${HOTE}:${PORT}/" 2>/dev/null | grep -q "ia-consultations-publiques"; then
  echo
  echo "   ------------------------------------------------"
  echo "   L'APPLICATION TOURNE DÉJÀ."
  echo
  echo "        http://${HOTE}:${PORT}/connexion"
  echo
  echo "   Rien à faire d'autre. Si tu veux la relancer, arrête d'abord"
  echo "   l'instance en cours (Ctrl-C dans sa fenêtre Terminal)."
  echo "   ------------------------------------------------"
  echo
  exit 0
fi


# --- 2. la base répond-elle ? ------------------------------------------------
echo "== 1/4  base de données =="
if command -v pg_isready >/dev/null 2>&1; then
  if ! pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
    echo "   PostgreSQL ne répond pas sur 127.0.0.1:5432."
    echo "   Démarre Postgres.app puis relance ce script."
    exit 1
  fi
  echo "   PostgreSQL répond."
else
  echo "   (pg_isready absent — on continue sans vérification préalable)"
fi

# --- 3. migrations -----------------------------------------------------------
echo "== 2/4  migrations =="
cd src
../.venv/bin/python -m app.storage.migrations up

# --- 4. serveur --------------------------------------------------------------
echo "== 3/4  serveur =="
echo
echo "   ------------------------------------------------"
echo "   OUVRE CETTE ADRESSE DANS TON NAVIGATEUR :"
echo
echo "        http://${HOTE}:${PORT}/connexion"
echo
echo "   Identifiant de démonstration (base de vérification) :"
echo "        verif@exemple.test    /    MotDePasseVerif!2026"
echo
echo "   Documentation technique de l'API : http://${HOTE}:${PORT}/docs"
echo "   Arrêt : Ctrl-C"
echo "   ------------------------------------------------"
echo
echo "== 4/4  démarrage =="

exec ../.venv/bin/python -m uvicorn app.main:app --host "$HOTE" --port "$PORT"
