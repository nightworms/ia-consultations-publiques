#!/usr/bin/env bash
# =============================================================================
# restauration.sh — restauration d'une sauvegarde chiffrée et VÉRIFICATION.
#
# Lot L7. Ce script ne déploie rien et n'ouvre aucun port. Il :
#   1. vérifie l'empreinte SHA-256 des archives AVANT de les déchiffrer ;
#   2. restaure la base dans une base de TEST distincte (jamais la base source) ;
#   3. compare, table par table, les comptages de lignes sauvegardés / sources /
#      restaurés ;
#   4. restaure les fichiers dans un répertoire de test et vérifie l'empreinte
#      SHA-256 de CHAQUE fichier contre le manifeste de la sauvegarde.
#
# Il échoue bruyamment si un seul contrôle ne passe pas. Un code de retour 0
# signifie : la sauvegarde est lisible, complète, et son contenu correspond.
#
# GARDE-FOUS :
#   - la base cible ne peut pas être la base source ;
#   - la base cible est SUPPRIMÉE puis recréée (idempotence), sauf avec
#     --sans-suppression, qui refuse alors d'écraser une base existante ;
#   - la clé est lue hors dépôt, permissions 600 exigées ; jamais en clair ici.
#
# Usage :
#   scripts/restauration.sh [--sauvegarde DIR] [--base-cible NOM]
#                           [--repertoire-fichiers DIR] [--base URL]
#                           [--sans-suppression] [-h]
# =============================================================================

set -Eeuo pipefail
umask 077

RACINE_DEPOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${SAUVEGARDE_REPERTOIRE:=$HOME/sauvegardes-ia-consultations}"
: "${SAUVEGARDE_CLE_FICHIER:=$HOME/.config/ia-consultations/cle-sauvegarde}"

DIR_SAUVEGARDE=""
BASE_CIBLE=""
REPERTOIRE_FICHIERS=""
URL_BASE="${DATABASE_URL:-}"
SUPPRIMER_EXISTANTE=1

erreur() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }
info()   { printf '[restauration] %s\n' "$*" >&2; }
echec()  { printf 'ÉCHEC DE VÉRIFICATION : %s\n' "$*" >&2; exit 2; }

usage() {
    cat <<'FIN'
Usage : scripts/restauration.sh [options]

  --sauvegarde DIR          répertoire de sauvegarde
                            (défaut : $SAUVEGARDE_REPERTOIRE/derniere)
  --base-cible NOM          base de TEST à recréer
                            (défaut : <base source>_restauration_test)
  --repertoire-fichiers DIR répertoire de restauration des fichiers, HORS dépôt
                            (défaut : $HOME/restauration-ia-consultations/documents)
  --base URL                chaîne de connexion PostgreSQL source
                            (défaut : $DATABASE_URL, sinon DATABASE_URL de .env)
  --sans-suppression        refuser d'écraser une base cible existante
  -h, --help                cette aide

Clé de chiffrement : $SAUVEGARDE_CLE_FICHIER (permissions 600 exigées).
FIN
    exit "${1:-0}"
}

outil_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then printf 'sha256sum'; else printf 'shasum -a 256'; fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sauvegarde)          DIR_SAUVEGARDE="${2:?argument manquant}";    shift 2 ;;
        --base-cible)          BASE_CIBLE="${2:?argument manquant}";        shift 2 ;;
        --repertoire-fichiers) REPERTOIRE_FICHIERS="${2:?argument manquant}"; shift 2 ;;
        --base)                URL_BASE="${2:?argument manquant}";          shift 2 ;;
        --sans-suppression)    SUPPRIMER_EXISTANTE=0;                       shift   ;;
        -h|--help)             usage 0 ;;
        *)                     erreur "argument inconnu : $1 (voir --help)" ;;
    esac
done

for outil in pg_restore psql openssl tar awk diff; do
    command -v "$outil" >/dev/null 2>&1 || erreur "outil requis absent : $outil"
done
SHA256="$(outil_sha256)"

# --- Chaîne de connexion source ------------------------------------------------
if [[ -z "$URL_BASE" && -f "$RACINE_DEPOT/.env" ]]; then
    URL_BASE="$(sed -n 's/^[[:space:]]*DATABASE_URL[[:space:]]*=[[:space:]]*//p' "$RACINE_DEPOT/.env" \
                | tail -n 1 | sed "s/^\"//; s/\"$//; s/^'//; s/'$//")"
fi
[[ -n "$URL_BASE" ]] || erreur "DATABASE_URL est vide : renseignez-le, ou passez --base <url>."
case "$URL_BASE" in
    *"?"*) erreur "chaîne de connexion avec paramètres d'URL non gérée par ce script" ;;
esac

# --- Clé ----------------------------------------------------------------------
[[ -f "$SAUVEGARDE_CLE_FICHIER" ]] || erreur "clé de sauvegarde absente : $SAUVEGARDE_CLE_FICHIER"
CHEMIN_CLE="$(cd "$(dirname "$SAUVEGARDE_CLE_FICHIER")" && pwd)/$(basename "$SAUVEGARDE_CLE_FICHIER")"
case "$CHEMIN_CLE" in
    "$RACINE_DEPOT"/*) erreur "la clé est À L'INTÉRIEUR du dépôt ($CHEMIN_CLE) : refus." ;;
esac
PERMS_CLE="$(stat -f '%Lp' "$CHEMIN_CLE" 2>/dev/null || stat -c '%a' "$CHEMIN_CLE" 2>/dev/null || printf '?')"
[[ "$PERMS_CLE" == "600" ]] || erreur "permissions de la clé : $PERMS_CLE (600 exigé)."

# --- Sauvegarde à restaurer ----------------------------------------------------
if [[ -z "$DIR_SAUVEGARDE" ]]; then
    DIR_SAUVEGARDE="$SAUVEGARDE_REPERTOIRE/derniere"
fi
[[ -d "$DIR_SAUVEGARDE" ]] || erreur "sauvegarde introuvable : $DIR_SAUVEGARDE"
DIR_SAUVEGARDE="$(cd "$DIR_SAUVEGARDE" && pwd)"
for f in base.dump.enc documents.tar.gz.enc manifeste.tar.gz.enc empreintes.sha256; do
    [[ -s "$DIR_SAUVEGARDE/$f" ]] || erreur "pièce manquante dans la sauvegarde : $f"
done
info "sauvegarde à restaurer : $DIR_SAUVEGARDE"

# --- 1. Empreinte des archives, AVANT tout déchiffrement -----------------------
if ! ( cd "$DIR_SAUVEGARDE" && $SHA256 -c empreintes.sha256 ); then
    echec "l'empreinte SHA-256 des archives ne correspond pas : sauvegarde corrompue ou altérée."
fi

STAGING="$(mktemp -d "${TMPDIR:-/tmp}/restauration-l7.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT

ARGS_CHIFFREMENT=(-d -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -pass "file:$CHEMIN_CLE")

# --- Le manifeste est rangé DANS une archive chiffrée --------------------------
mkdir -p "$STAGING/manifeste"
openssl enc "${ARGS_CHIFFREMENT[@]}" -in "$DIR_SAUVEGARDE/manifeste.tar.gz.enc" \
    | tar -xzf - -C "$STAGING/manifeste" \
    || echec "manifeste illisible : clé incorrecte ou archive corrompue."

[[ -s "$STAGING/manifeste/manifeste.tsv" ]] || echec "manifeste absent de la sauvegarde."
MANIFESTE="$STAGING/manifeste/manifeste.tsv"

NOM_BASE_SAUVEGARDEE="$(awk -F'\t' '$1=="base"{print $2}' "$MANIFESTE")"
HORODATAGE="$(awk -F'\t' '$1=="horodatage"{print $2}' "$MANIFESTE")"
info "sauvegarde du $HORODATAGE, base « $NOM_BASE_SAUVEGARDEE »"

# --- 2. Base cible : garde-fous puis (re) création -----------------------------
NOM_BASE_SOURCE="$(psql -X -At "$URL_BASE" -c 'SELECT current_database()')"
BASE_CIBLE="${BASE_CIBLE:-${NOM_BASE_SOURCE}_restauration_test}"
[[ "$BASE_CIBLE" != "$NOM_BASE_SOURCE" ]] || erreur "la base cible ne peut pas être la base source ($NOM_BASE_SOURCE) : refus."
case "$BASE_CIBLE" in
    *';'*|*'"'*|*' '*) erreur "nom de base cible invalide : $BASE_CIBLE" ;;
esac

URL_ADMIN="${URL_BASE%/*}/postgres"
URL_CIBLE="${URL_BASE%/*}/$BASE_CIBLE"

EXISTE="$(psql -X -At "$URL_ADMIN" -c "SELECT 1 FROM pg_database WHERE datname = '$BASE_CIBLE'")"
if [[ "$EXISTE" == "1" ]]; then
    if [[ "$SUPPRIMER_EXISTANTE" -eq 0 ]]; then
        erreur "la base cible $BASE_CIBLE existe déjà (--sans-suppression) : rien n'a été modifié."
    fi
    info "base cible $BASE_CIBLE déjà présente : suppression puis recréation (idempotence)."
    psql -X -q "$URL_ADMIN" -c "DROP DATABASE IF EXISTS \"$BASE_CIBLE\" WITH (FORCE);"
fi
info "création de la base de test « $BASE_CIBLE »…"
psql -X -q "$URL_ADMIN" -c "CREATE DATABASE \"$BASE_CIBLE\";"

# --- 3. Restauration (le déchiffré ne touche pas le disque) --------------------
info "restauration de la base…"
openssl enc "${ARGS_CHIFFREMENT[@]}" -in "$DIR_SAUVEGARDE/base.dump.enc" \
    | pg_restore -d "$URL_CIBLE" --no-owner --no-privileges --exit-on-error \
    || echec "pg_restore a échoué : la base n'a pas été restaurée correctement."

# --- 4. Vérification : comptage de lignes avant / après ------------------------
SQL_COMPTAGE="
    SELECT c.relname,
           (xpath('/row/c/text()',
                  query_to_xml(format('SELECT count(*) AS c FROM %I.%I', n.nspname, c.relname),
                               false, true, '')))[1]::text::int
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r' AND n.nspname = 'public' ORDER BY c.relname;"

psql -X -At -F "$(printf '\t')" "$URL_CIBLE" -c "$SQL_COMPTAGE" > "$STAGING/comptage_restaure.tsv"
psql -X -At -F "$(printf '\t')" "$URL_BASE"   -c "$SQL_COMPTAGE" > "$STAGING/comptage_source.tsv"
awk -F'\t' '$1=="table"{print $2 "\t" $3}' "$MANIFESTE" > "$STAGING/comptage_sauvegarde.tsv"

printf '\nComptage de lignes — table par table\n'
printf '%-32s %12s %12s %12s   %s\n' 'table' 'sauvegarde' 'source(now)' 'restaurée' 'verdict'
printf -- '-------------------------------------------------------------------------------------\n'
EXIT_CODE=0
while read -r TABLE NB_SAUVEGARDE; do
    NB_SOURCE="$(awk -F'\t' -v t="$TABLE" '$1==t{print $2}' "$STAGING/comptage_source.tsv")"
    NB_RESTAURE="$(awk -F'\t' -v t="$TABLE" '$1==t{print $2}' "$STAGING/comptage_restaure.tsv")"
    NB_SOURCE="${NB_SOURCE:-absent}"
    NB_RESTAURE="${NB_RESTAURE:-absente}"
    if [[ "$NB_RESTAURE" == "$NB_SAUVEGARDE" ]]; then VERDICT='identique'; else VERDICT='DIVERGENT'; EXIT_CODE=2; fi
    printf '%-32s %12s %12s %12s   %s\n' "$TABLE" "$NB_SAUVEGARDE" "$NB_SOURCE" "$NB_RESTAURE" "$VERDICT"
done < "$STAGING/comptage_sauvegarde.tsv"

# Tables présentes après restauration mais absentes de la sauvegarde.
while read -r TABLE NB_RESTAURE; do
    awk -F'\t' -v t="$TABLE" '$1==t{found=1} END{exit !found}' "$STAGING/comptage_sauvegarde.tsv" || {
        printf '%-32s %12s %12s %12s   %s\n' "$TABLE" '-' '-' "$NB_RESTAURE" 'EN TROP'; EXIT_CODE=2; }
done < "$STAGING/comptage_restaure.tsv"

# --- 5. Vérification des fichiers, empreinte par empreinte ---------------------
REPERTOIRE_FICHIERS="${REPERTOIRE_FICHIERS:-${RESTAURATION_REPERTOIRE:-$HOME/restauration-ia-consultations}/documents}"
mkdir -p "$REPERTOIRE_FICHIERS"
REPERTOIRE_FICHIERS="$(cd "$REPERTOIRE_FICHIERS" && pwd)"
case "$REPERTOIRE_FICHIERS" in
    "$RACINE_DEPOT"/*) erreur "les fichiers restaurés sont EN CLAIR et ne doivent pas atterrir dans le dépôt ($REPERTOIRE_FICHIERS) : refus." ;;
esac
info "restauration des fichiers dans ${REPERTOIRE_FICHIERS} …"

mkdir -p "$STAGING/restaure"
openssl enc "${ARGS_CHIFFREMENT[@]}" -in "$DIR_SAUVEGARDE/documents.tar.gz.enc" \
    | tar -xzf - -C "$STAGING/restaure" \
    || echec "archive de documents illisible."

( cd "$STAGING/restaure" && find . -type f -print0 | sort -z | xargs -0 $SHA256 \
    | awk -F'  ' '{print $1 "\t" $2}' | sort ) > "$STAGING/fichiers_restaures.sha256"
awk -F'\t' '$1=="fichier"{print $2 "\t" $3}' "$MANIFESTE" | sort > "$STAGING/fichiers_attendus.sha256"

# Copie de confort des fichiers restaurés (le contrôle ci-dessus fait foi ; cette
# copie ne supprime rien dans la destination, qui doit être un répertoire de test).
cp -Rp "$STAGING/restaure/." "$REPERTOIRE_FICHIERS/" 2>/dev/null || true

NB_FICHIERS="$(wc -l < "$STAGING/fichiers_attendus.sha256" | tr -d ' ')"
printf '\nFichiers — %s fichier(s) attendu(s)\n' "$NB_FICHIERS"
if diff -u "$STAGING/fichiers_attendus.sha256" "$STAGING/fichiers_restaures.sha256" > "$STAGING/diff_fichiers.txt"; then
    printf '  tous les fichiers restaurés portent l'"'"'empreinte attendue  : identique\n'
else
    printf '  DIVERGENCE sur les fichiers :\n'
    sed 's/^/    /' "$STAGING/diff_fichiers.txt"
    EXIT_CODE=2
fi

printf '\n'
if [[ "$EXIT_CODE" -eq 0 ]]; then
    printf 'RESTAURATION VÉRIFIÉE : base « %s » restaurée depuis %s,\n' "$BASE_CIBLE" "$DIR_SAUVEGARDE"
    printf '  comptages de lignes identiques table par table, %s fichier(s) conforme(s).\n' "$NB_FICHIERS"
    printf '  Pour revenir en arrière : DROP DATABASE "%s";\n' "$BASE_CIBLE"
else
    printf 'RESTAURATION EN ÉCHEC : au moins un contrôle ne passe pas (voir ci-dessus).\n' >&2
fi
exit "$EXIT_CODE"