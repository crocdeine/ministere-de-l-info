#!/usr/bin/env bash
#
# Télécharge la DB DuckDB depuis une release GitHub et la place dans data/.
# Usage : ./scripts/download_db.sh [tag]
#
# Sans argument : release la plus récente contenant l'asset ministere.duckdb.gz
#                 (quel que soit le préfixe du tag : v*, db-*...)
# Avec argument : ./scripts/download_db.sh v0.5-economie-legislatif
#
# Requiert GITHUB_TOKEN dans .env ou dans l'environnement.
# Scope minimal : "public_repo" (dépôt public) ou "repo" (dépôt privé)
#
# Empreinte (voir deploy/README-deploy.md) : ministere.duckdb.gz.sha256 contient
# le SHA256 de l'archive compressée. Le format historique (SHA256 de la base
# décompressée) est aussi accepté.

set -euo pipefail

REPO="crocdeine/ministere-de-l-info"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_DIR/data"
ENV_FILE="$REPO_DIR/.env"
DB_FILE="$DATA_DIR/ministere.duckdb"
ASSET="ministere.duckdb.gz"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

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

# Résoudre la release
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
    log "Recherche de la dernière release contenant $ASSET..."
    ALL_RELEASES=$(curl -fsS \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        "$API_BASE/releases?per_page=30")
    RELEASE_JSON=$(python3 -c "
import json, sys
releases = json.load(sys.stdin)
avec_db = [
    r for r in releases
    if not r.get('draft') and any(a.get('name') == '$ASSET' for a in r.get('assets', []))
]
if not avec_db:
    sys.exit(1)
print(json.dumps(avec_db[0]))
" <<< "$ALL_RELEASES") || {
        echo "ERREUR : aucune release contenant $ASSET dans $REPO" >&2
        exit 2
    }
    TAG=$(python3 -c "import json,sys; print(json.loads(sys.stdin.read())['tag_name'])" <<< "$RELEASE_JSON")
    log "Release retenue : $TAG"
fi

# Extraire les URLs d'API des assets (asset.url, pas browser_download_url)
# browser_download_url renvoie 404 sur les repos privés même avec un token Bearer.
# La méthode correcte est d'utiliser l'URL API avec Accept: application/octet-stream.
asset_url() {
    python3 -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('assets', []):
    if a['name'] == sys.argv[1]:
        print(a['url'])
        break
" "$1" <<< "$RELEASE_JSON"
}
GZ_URL=$(asset_url "$ASSET")
SHA_URL=$(asset_url "$ASSET.sha256")

if [ -z "$GZ_URL" ]; then
    echo "ERREUR : asset $ASSET absent de la release $TAG" >&2
    exit 3
fi

mkdir -p "$DATA_DIR"
WORK_DIR=$(mktemp -d "$DATA_DIR/.telechargement.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT
GZ_FILE="$WORK_DIR/$ASSET"

# Télécharger la DB compressée via l'API (Accept: application/octet-stream obligatoire)
log "Téléchargement $GZ_URL..."
curl -fSL \
    -H "$AUTH_HEADER" \
    -H "Accept: application/octet-stream" \
    --progress-bar \
    -o "$GZ_FILE" \
    "$GZ_URL"

gzip -t "$GZ_FILE" || {
    echo "ERREUR : archive corrompue (gzip -t)" >&2
    exit 4
}

log "Décompression..."
gunzip -c "$GZ_FILE" > "$WORK_DIR/ministere.duckdb"

# Vérifier l'empreinte si disponible
if [ -n "$SHA_URL" ]; then
    log "Vérification SHA256..."
    EXPECTED_SHA=$(curl -fsSL \
        -H "$AUTH_HEADER" \
        -H "Accept: application/octet-stream" \
        "$SHA_URL" | awk 'NR==1 {print tolower($1)}')

    if [ -z "$EXPECTED_SHA" ]; then
        log "Avertissement : fichier .sha256 vide, vérification ignorée"
    else
        GZ_SHA=$(sha256_of "$GZ_FILE")
        if [ "$EXPECTED_SHA" = "$GZ_SHA" ]; then
            log "SHA256 OK (archive)"
        elif [ "$EXPECTED_SHA" = "$(sha256_of "$WORK_DIR/ministere.duckdb")" ]; then
            log "SHA256 OK (base décompressée, format historique)"
        else
            echo "ERREUR : SHA256 invalide (publié : $EXPECTED_SHA, archive : $GZ_SHA)" >&2
            echo "La base existante $DB_FILE n'a pas été modifiée." >&2
            exit 4
        fi
    fi
else
    log "Avertissement : pas de fichier .sha256 dans la release, vérification ignorée"
fi

mv -f "$WORK_DIR/ministere.duckdb" "$DB_FILE"

SIZE=$(du -h "$DB_FILE" | cut -f1)
log "OK : $DB_FILE ($SIZE, release $TAG)"
log "Étape suivante : copier dans le volume Docker (voir docs/deployment.md)"

exit 0
