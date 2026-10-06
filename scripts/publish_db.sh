#!/usr/bin/env bash
#
# Prépare la DB DuckDB pour publication sur une release GitHub.
# Compresse data/ministere.duckdb, génère l'empreinte SHA256, affiche la commande gh.
#
# Usage : ./scripts/publish_db.sh [tag-de-release]
#   ex.  : ./scripts/publish_db.sh v0.6-description
#
# Le script N'exécute PAS gh — la publication reste manuelle.
#
# Convention d'empreinte (partagée avec deploy/install.sh, deploy/update.sh,
# scripts/download_db.sh — voir deploy/README-deploy.md) :
#   ministere.duckdb.gz.sha256 = SHA256 du fichier COMPRESSÉ, au format
#   « <hash>  ministere.duckdb.gz » (nom de fichier sans chemin, vérifiable
#   par `shasum -a 256 -c ministere.duckdb.gz.sha256` dans le dossier de l'archive).

set -euo pipefail

REPO="crocdeine/ministere-de-l-info"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_DIR/data"
DB_NAME="ministere.duckdb"
GZ_NAME="$DB_NAME.gz"
SHA_NAME="$GZ_NAME.sha256"
DB_FILE="$DATA_DIR/$DB_NAME"
GZ_FILE="$DATA_DIR/$GZ_NAME"
SHA_FILE="$DATA_DIR/$SHA_NAME"
MAX_SIZE_BYTES=$((2 * 1024 * 1024 * 1024))  # 2 Go = limite d'un asset de release GitHub
TAG="${1:-<tag-de-release>}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

file_size() {
    # macOS : stat -f%z ; Linux : stat -c%s
    stat -f%z "$1" 2>/dev/null || stat -c%s "$1"
}

# Vérifier que la DB source existe
if [ ! -f "$DB_FILE" ]; then
    echo "ERREUR : $DB_FILE introuvable" >&2
    echo "Lancer l'ETL d'abord : uv run python scripts/etl_territoires.py --yes" >&2
    exit 1
fi

DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
log "DB source : $DB_FILE ($DB_SIZE)"

# Compresser (-n : sans nom ni horodatage dans l'en-tête → archive reproductible)
log "Compression gzip..."
gzip -n -c "$DB_FILE" > "$GZ_FILE.tmp"
mv -f "$GZ_FILE.tmp" "$GZ_FILE"

GZ_SIZE=$(du -h "$GZ_FILE" | cut -f1)
log "Compressé : $GZ_FILE ($GZ_SIZE)"

ORIG_BYTES=$(file_size "$DB_FILE")
GZ_BYTES=$(file_size "$GZ_FILE")
log "Taille : $((ORIG_BYTES / 1024 / 1024)) Mo → $((GZ_BYTES / 1024 / 1024)) Mo"

# Vérifier la limite GitHub Releases (2 Go)
if [ "$GZ_BYTES" -gt "$MAX_SIZE_BYTES" ]; then
    echo "ERREUR : fichier compressé ($GZ_BYTES octets) dépasse la limite GitHub (2 Go)" >&2
    rm -f "$GZ_FILE"
    exit 2
fi
log "Taille OK (< 2 Go, limite GitHub Releases)"

# Générer l'empreinte du fichier COMPRESSÉ, nom de fichier sans chemin
log "Génération SHA256 (archive compressée)..."
SHA=$(sha256_of "$GZ_FILE")
printf '%s  %s\n' "$SHA" "$GZ_NAME" > "$SHA_FILE"
log "SHA256 : $SHA"
log "Fichier checksum : $SHA_FILE"

# Auto-vérification : l'archive se décompresse et restitue la base à l'identique
log "Auto-vérification (intégrité gzip + contenu)..."
gzip -t "$GZ_FILE"
if [ "$(gunzip -c "$GZ_FILE" | sha256_of /dev/stdin)" != "$(sha256_of "$DB_FILE")" ]; then
    echo "ERREUR : l'archive ne restitue pas la base à l'identique" >&2
    exit 3
fi
log "Auto-vérification OK"

echo ""
echo "========================================================"
echo " Commande à exécuter manuellement (release existante) :"
echo "========================================================"
echo ""
echo "gh release upload $TAG \\"
echo "  --repo $REPO --clobber \\"
echo "  '$GZ_FILE' \\"
echo "  '$SHA_FILE'"
echo ""
echo "Vérification après publication (le digest GitHub de l'asset .gz doit valoir sha256:$SHA) :"
echo "  gh release view $TAG --repo $REPO --json assets"
echo ""
echo "Nettoyer après publication :"
echo "  rm -f '$GZ_FILE' '$SHA_FILE'"

exit 0
