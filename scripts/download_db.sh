#!/usr/bin/env bash
#
# Télécharge la DB DuckDB depuis GitHub Releases et la place dans data/.
# Usage : ./scripts/download_db.sh [tag]
#
# Sans argument : cherche la dernière release dont le tag commence par "db-"
# Avec argument : ./scripts/download_db.sh db-2026-05
#
# Requiert GITHUB_TOKEN dans .env ou dans l'environnement.
# Scope minimal : "public_repo" (dépôt public) ou "repo" (dépôt privé)

set -euo pipefail

REPO="crocdeine/ministere-de-l-info"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_DIR/data"
ENV_FILE="$REPO_DIR/.env"
GZ_FILE="$DATA_DIR/ministere.duckdb.gz"
DB_FILE="$DATA_DIR/ministere.duckdb"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Charger GITHUB_TOKEN depuis .env si absent de l'environnement
if [ -z "${GITHUB_TOKEN:-}" ] && [ -f "$ENV_FILE" ]; then
    token_line=$(grep -E '^GITHUB_TOKEN=' "$ENV_FILE" 2>/dev/null || true)
    if [ -n "$token_line" ]; then
        GITHUB_TOKEN="${token_line#GITHUB_TOKEN=}"
        GITHUB_TOKEN="${GITHUB_TOKEN//\"/}"
    fi
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "ERREUR : GITHUB_TOKEN absent du .env et de l'environnement" >&2
    echo "Ajouter GITHUB_TOKEN=ghp_xxx dans .env (scope: public_repo ou repo)" >&2
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $GITHUB_TOKEN"
API_BASE="https://api.github.com/repos/$REPO"

# Résoudre le tag
TAG="${1:-}"
if [ -n "$TAG" ]; then
    log "Récupération de la release $TAG..."
    RELEASE_JSON=$(curl -fsS \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        "$API_BASE/releases/tags/$TAG") || {
        echo "ERREUR : release '$TAG' introuvable" >&2
        exit 2
    }
else
    log "Recherche de la dernière release db-*..."
    ALL_RELEASES=$(curl -fsS \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        "$API_BASE/releases?per_page=20")
    RELEASE_JSON=$(python3 -c "
import json, sys
releases = json.load(sys.stdin)
db = [r for r in releases if r.get('tag_name','').startswith('db-')]
if not db:
    print('no-release', file=sys.stderr)
    sys.exit(1)
print(json.dumps(db[0]))
" <<< "$ALL_RELEASES") || {
        echo "ERREUR : aucune release db-* trouvée dans $REPO" >&2
        exit 2
    }
    TAG=$(python3 -c "import json,sys; print(json.loads(sys.stdin.read())['tag_name'])" <<< "$RELEASE_JSON")
    log "Dernière release DB : $TAG"
fi

# Extraire les URLs de téléchargement
GZ_URL=$(python3 -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('assets', []):
    if a['name'] == 'ministere.duckdb.gz':
        print(a['browser_download_url'])
        break
" <<< "$RELEASE_JSON")

SHA_URL=$(python3 -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('assets', []):
    if a['name'] == 'ministere.duckdb.gz.sha256':
        print(a['browser_download_url'])
        break
" <<< "$RELEASE_JSON")

if [ -z "$GZ_URL" ]; then
    echo "ERREUR : asset ministere.duckdb.gz absent de la release $TAG" >&2
    exit 3
fi

mkdir -p "$DATA_DIR"

# Télécharger la DB compressée
log "Téléchargement $GZ_URL..."
curl -fSL \
    -H "$AUTH_HEADER" \
    --progress-bar \
    -o "$GZ_FILE" \
    "$GZ_URL"

# Vérifier le SHA256 si disponible
if [ -n "$SHA_URL" ]; then
    log "Vérification SHA256..."
    SHA_FILE=$(mktemp)
    curl -fsS \
        -H "$AUTH_HEADER" \
        -o "$SHA_FILE" \
        "$SHA_URL"
    EXPECTED_SHA=$(awk '{print $1}' "$SHA_FILE")
    rm -f "$SHA_FILE"

    if command -v sha256sum &>/dev/null; then
        ACTUAL_SHA=$(sha256sum "$GZ_FILE" | awk '{print $1}')
    else
        ACTUAL_SHA=$(shasum -a 256 "$GZ_FILE" | awk '{print $1}')
    fi

    if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
        echo "ERREUR : SHA256 invalide (attendu: $EXPECTED_SHA, obtenu: $ACTUAL_SHA)" >&2
        rm -f "$GZ_FILE"
        exit 4
    fi
    log "SHA256 OK"
else
    log "Avertissement : pas de fichier .sha256 dans la release, vérification ignorée"
fi

# Décompresser
log "Décompression → $DB_FILE..."
gunzip -f "$GZ_FILE"

SIZE=$(du -h "$DB_FILE" | cut -f1)
log "OK : $DB_FILE ($SIZE)"
log "Étape suivante : copier dans le volume Docker (voir docs/deployment.md)"

exit 0
