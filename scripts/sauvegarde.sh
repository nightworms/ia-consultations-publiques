#!/usr/bin/env bash
# =============================================================================
# sauvegarde.sh — sauvegarde CHIFFRÉE de la base PostgreSQL et des fichiers.
#
# Lot L7. Ce script ne déploie rien et n'ouvre aucun port. Il produit, dans un
# répertoire HORS DÉPÔT, une sauvegarde horodatée :
#
#   <SAUVEGARDE_REPERTOIRE>/AAAAMMJJ-HHMMSS/
#       base.dump.enc            pg_dump (format custom) chiffré
#       documents.tar.gz.enc     documents chiffrés, lus en place
#       manifeste.tar.gz.enc     manifeste de contrôle chiffré (comptages de
#                                lignes par table + empreinte de chaque fichier)
#       empreintes.sha256        empreintes SHA-256 des trois archives ci-dessus
#   <SAUVEGARDE_REPERTOIRE>/derniere -> (lien vers la sauvegarde la plus récente)
#
# Aucun fichier en clair de la base n'est écrit : pg_dump écrit sur sa sortie
# standard, directement dans le chiffreur (`openssl enc`). Les documents sont
# empaquetés par `tar` sur sa sortie standard, puis chiffrés de la même façon.
#
# CHIFFREMENT : AES-256-CBC, dérivation PBKDF2-HMAC-SHA256 (200 000 itérations),
# sel aléatoire par archive — `openssl enc`, présent sur macOS comme sur Linux.
# LIMITE ASSUMÉE : `openssl enc` chiffre mais n'AUTHENTIFIE pas le chiffré (pas
# d'AEAD). L'intégrité est portée par l'empreinte SHA-256 de chaque archive
# (`empreintes.sha256`, en clair, sans secret), VÉRIFIÉE avant tout déchiffrement
# par restauration.sh. Cela détecte la corruption et l'altération ; cela ne
# protège pas d'un adversaire capable de réécrire l'archive ET son empreinte.
# Alternative écartée : GPG (MDC intégré) — voir docs/DEPLOIEMENT-FRANCE.md.
#
# LA CLÉ N'EST JAMAIS DANS LE DÉPÔT. Elle est lue dans le fichier désigné par
# $SAUVEGARDE_CLE_FICHIER (défaut : $HOME/.config/ia-consultations/cle-sauvegarde,
# permissions 600 exigées). Ce script ne CRÉE JAMAIS de clé : une clé créée
# silencieusement rendrait les sauvegardes précédentes indéchiffrables.
#
# IDEMPOTENT : relancer le script crée une sauvegarde supplémentaire horodatée et
# ne touche à aucune sauvegarde existante. Il ne supprime jamais rien.
#
# Usage :
#   scripts/sauvegarde.sh [--repertoire DEST] [--documents DIR] [--base URL] [-h]
# =============================================================================

set -Eeuo pipefail
umask 077

RACINE_DEPOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${SAUVEGARDE_REPERTOIRE:=$HOME/sauvegardes-ia-consultations}"
: "${SAUVEGARDE_CLE_FICHIER:=$HOME/.config/ia-consultations/cle-sauvegarde}"
: "${REPERTOIRE_DOCUMENTS:=$RACINE_DEPOT/data}"

REPERTOIRE_DEST=""
REPERTOIRE_DOC="$REPERTOIRE_DOCUMENTS"
URL_BASE="${DATABASE_URL:-}"

erreur() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }
info()   { printf '[sauvegarde] %s\n' "$*" >&2; }

usage() {
    cat <<'FIN'
Usage : scripts/sauvegarde.sh [options]

  --repertoire DEST   répertoire de destination, HORS dépôt
                      (défaut : $SAUVEGARDE_REPERTOIRE)
  --documents DIR     répertoire des fichiers à sauvegarder
                      (défaut : $REPERTOIRE_DOCUMENTS, soit <dépôt>/data)
  --base URL          chaîne de connexion PostgreSQL
                      (défaut : $DATABASE_URL, sinon DATABASE_URL de <dépôt>/.env)
  -h, --help          cette aide

Clé de chiffrement : fichier désigné par $SAUVEGARDE_CLE_FICHIER
(défaut $HOME/.config/ia-consultations/cle-sauvegarde, permissions 600).
Sans clé, le script ÉCHOUE : il ne produit jamais de sauvegarde non chiffrée.
FIN
    exit "${1:-0}"
}

outil_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then printf 'sha256sum'; else printf 'shasum -a 256'; fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repertoire) REPERTOIRE_DEST="${2:?argument manquant}"; shift 2 ;;
        --documents)  REPERTOIRE_DOC="${2:?argument manquant}";  shift 2 ;;
        --base)       URL_BASE="${2:?argument manquant}";        shift 2 ;;
        -h|--help)    usage 0 ;;
        *)            erreur "argument inconnu : $1 (voir --help)" ;;
    esac
done

# --- Dépendances : aucune installation, tout est déjà présent -----------------
for outil in pg_dump psql openssl tar awk; do
    command -v "$outil" >/dev/null 2>&1 || erreur "outil requis absent : $outil"
done
SHA256="$(outil_sha256)"

# --- Chaîne de connexion : jamais en dur --------------------------------------
if [[ -z "$URL_BASE" && -f "$RACINE_DEPOT/.env" ]]; then
    URL_BASE="$(sed -n 's/^[[:space:]]*DATABASE_URL[[:space:]]*=[[:space:]]*//p' "$RACINE_DEPOT/.env" \
                | tail -n 1 | sed "s/^\"//; s/\"$//; s/^'//; s/'$//")"
    [[ -n "$URL_BASE" ]] && info "chaîne de connexion lue depuis $RACINE_DEPOT/.env"
fi
[[ -n "$URL_BASE" ]] || erreur "DATABASE_URL est vide : renseignez-le, ou passez --base <url>."

# --- La clé : présente, hors dépôt, lisible par son seul propriétaire ---------
[[ -n "${SAUVEGARDE_CLE_FICHIER:-}" ]] || erreur "SAUVEGARDE_CLE_FICHIER est vide."
if [[ ! -f "$SAUVEGARDE_CLE_FICHIER" ]]; then
    erreur "clé de sauvegarde absente : $SAUVEGARDE_CLE_FICHIER
AUCUNE sauvegarde n'a été produite : une sauvegarde non chiffrée est interdite.
Générez la clé UNE SEULE FOIS, hors dépôt, et conservez-la :
  install -d -m 700 \"\$(dirname \"$SAUVEGARDE_CLE_FICHIER\")\"
  openssl rand -base64 48 > \"$SAUVEGARDE_CLE_FICHIER\"
  chmod 600 \"$SAUVEGARDE_CLE_FICHIER\"
Sans cette clé, aucune sauvegarde existante n'est déchiffrable."
fi
[[ -s "$SAUVEGARDE_CLE_FICHIER" ]] || erreur "clé de sauvegarde vide : $SAUVEGARDE_CLE_FICHIER"

CHEMIN_CLE="$(cd "$(dirname "$SAUVEGARDE_CLE_FICHIER")" && pwd)/$(basename "$SAUVEGARDE_CLE_FICHIER")"
case "$CHEMIN_CLE" in
    "$RACINE_DEPOT"/*) erreur "la clé est À L'INTÉRIEUR du dépôt ($CHEMIN_CLE) : refus. Déplacez-la hors du dépôt." ;;
esac
PERMS_CLE="$(stat -f '%Lp' "$CHEMIN_CLE" 2>/dev/null || stat -c '%a' "$CHEMIN_CLE" 2>/dev/null || printf '?')"
[[ "$PERMS_CLE" == "600" ]] || erreur "permissions de la clé : $PERMS_CLE (600 exigé). Corrigez : chmod 600 \"$CHEMIN_CLE\""

# --- Destination : hors dépôt --------------------------------------------------
REPERTOIRE_DEST="${REPERTOIRE_DEST:-$SAUVEGARDE_REPERTOIRE}"
mkdir -p "$REPERTOIRE_DEST"
REPERTOIRE_DEST="$(cd "$REPERTOIRE_DEST" && pwd)"
case "$REPERTOIRE_DEST" in
    "$RACINE_DEPOT"/*) erreur "destination À L'INTÉRIEUR du dépôt ($REPERTOIRE_DEST) : refus (une sauvegarde ne se versionne pas)." ;;
esac
chmod 700 "$REPERTOIRE_DEST"

HORODATAGE="$(date '+%Y-%m-%dT%H:%M:%S%z')"
DIR_SORTIE="$REPERTOIRE_DEST/$(date '+%Y%m%d-%H%M%S')"
[[ -e "$DIR_SORTIE" ]] && erreur "destination déjà présente : $DIR_SORTIE (relancez dans une seconde)."
mkdir -p "$DIR_SORTIE"
chmod 700 "$DIR_SORTIE"

STAGING="$(mktemp -d "${TMPDIR:-/tmp}/sauvegarde-l7.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT

ARGS_CHIFFREMENT=(-aes-256-cbc -pbkdf2 -iter 200000 -salt -md sha256 -pass "file:$CHEMIN_CLE")

# --- 1. Base de données -------------------------------------------------------
NOM_BASE="$(psql -X -At "$URL_BASE" -c 'SELECT current_database()')"
info "sauvegarde de la base « $NOM_BASE »…"

pg_dump "$URL_BASE" --format=custom --no-owner --no-privileges \
    | openssl enc "${ARGS_CHIFFREMENT[@]}" -out "$DIR_SORTIE/base.dump.enc"
[[ -s "$DIR_SORTIE/base.dump.enc" ]] || erreur "archive de base vide : la sauvegarde a échoué."

# Garde-fou : le chiffré ne doit pas commencer par la magie de pg_dump.
if [[ "$(head -c 5 "$DIR_SORTIE/base.dump.enc")" == "PGDMP" ]]; then
    erreur "base.dump.enc n'est PAS chiffré (en-tête pg_dump en clair détecté)."
fi

# --- 2. Fichiers --------------------------------------------------------------
mkdir -p "$STAGING/documents-vide"
if [[ -d "$REPERTOIRE_DOC" ]]; then
    info "sauvegarde des fichiers de ${REPERTOIRE_DOC} (lus en place, jamais recopiés en clair) …"
    SOURCE_DOC="$REPERTOIRE_DOC"
else
    info "répertoire de documents absent ($REPERTOIRE_DOC) : archive de fichiers vide."
    SOURCE_DOC="$STAGING/documents-vide"
fi
SOURCE_DOC="$(cd "$SOURCE_DOC" && pwd)"

# Empreinte de chaque fichier : sert à vérifier la restauration, fichier par fichier.
( cd "$SOURCE_DOC" && find . -type f -print0 | sort -z \
    | xargs -0 $SHA256 | awk -F'  ' '{print $1 "\t" $2}' ) > "$STAGING/fichiers.sha256"

# --- 3. Manifeste de contrôle (rangé DANS une archive chiffrée) ---------------
{
    printf 'format\t1\n'
    printf 'horodatage\t%s\n' "$HORODATAGE"
    printf 'base\t%s\n' "$NOM_BASE"
    printf 'repertoire_fichiers\t%s\n' "$(basename "$SOURCE_DOC")"
    printf 'pg_dump\t%s\n' "$(pg_dump --version | head -n 1)"
    printf 'chiffrement\tAES-256-CBC/PBKDF2-HMAC-SHA256-200000\n'
    psql -X -At -F "$(printf '\t')" "$URL_BASE" -c "
        SELECT 'table', c.relname,
               (xpath('/row/c/text()',
                      query_to_xml(format('SELECT count(*) AS c FROM %I.%I', n.nspname, c.relname),
                                   false, true, '')))[1]::text::int
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'public'
        ORDER BY c.relname;"
    sed 's/^/fichier\t/' "$STAGING/fichiers.sha256"
} > "$STAGING/manifeste.tsv"

# 3a. Fichiers : `-C "$SOURCE_DOC" .` — les documents sont lus EN PLACE, jamais
# recopiés en clair sur le disque ; `tar` écrit sur sa sortie standard, qui part
# directement dans le chiffreur.
tar -czf - -C "$SOURCE_DOC" . \
    | openssl enc "${ARGS_CHIFFREMENT[@]}" -out "$DIR_SORTIE/documents.tar.gz.enc"
[[ -s "$DIR_SORTIE/documents.tar.gz.enc" ]] || erreur "archive de fichiers vide : la sauvegarde a échoué."

# 3b. Manifeste de contrôle : archive distincte, chiffrée elle aussi. Il n'est
# donc pas lisible dans le répertoire de sauvegarde.
tar -czf - -C "$STAGING" manifeste.tsv \
    | openssl enc "${ARGS_CHIFFREMENT[@]}" -out "$DIR_SORTIE/manifeste.tar.gz.enc"
[[ -s "$DIR_SORTIE/manifeste.tar.gz.enc" ]] || erreur "manifeste absent : la sauvegarde a échoué."

chmod 600 "$DIR_SORTIE"/*.enc

# --- 4. Empreintes, contrôles finals, lien « derniere » -----------------------
( cd "$DIR_SORTIE" && $SHA256 base.dump.enc documents.tar.gz.enc manifeste.tar.gz.enc > empreintes.sha256 )
chmod 600 "$DIR_SORTIE/empreintes.sha256"

if find "$DIR_SORTIE" -type f \( -name '*.dump' -o -name '*.sql' -o -name '*.tar.gz' -o -name '*.tar' \) | grep -q .; then
    erreur "des fichiers NON chiffrés subsistent dans $DIR_SORTIE : sauvegarde refusée."
fi
TAILLE_BASE_KIO="$(du -sk "$DIR_SORTIE/base.dump.enc" | cut -f1)"
TAILLE_DOC_KIO="$(du -sk "$DIR_SORTIE/documents.tar.gz.enc" | cut -f1)"
TAILLE_DOC_CLAIR_KIO="$(du -sk "$SOURCE_DOC" | cut -f1)"

ln -sfn "$DIR_SORTIE" "$REPERTOIRE_DEST/derniere"

printf 'Sauvegarde terminée.\n'
printf '  répertoire         : %s\n' "$DIR_SORTIE"
printf '  base               : %s\n' "$NOM_BASE"
printf '  base chiffrée      : %s Kio  (%s)\n' "$TAILLE_BASE_KIO" "$(cut -d' ' -f1 "$DIR_SORTIE/empreintes.sha256" | head -n 1)"
printf '  documents chiffrés : %s Kio  (%s)\n' "$TAILLE_DOC_KIO" "$(cut -d' ' -f1 "$DIR_SORTIE/empreintes.sha256" | sed -n 2p)"
printf '  documents en clair : %s Kio (lus en place, jamais recopiés en clair)\n' "$TAILLE_DOC_CLAIR_KIO"
printf '  manifeste chiffré  : manifeste.tar.gz.enc (%s)\n' "$(cut -d' ' -f1 "$DIR_SORTIE/empreintes.sha256" | sed -n 3p)"
printf '  rien en clair      : vérifié, aucun fichier non chiffré dans la destination\n'
printf '  lien de commodité  : %s/derniere\n' "$REPERTOIRE_DEST"