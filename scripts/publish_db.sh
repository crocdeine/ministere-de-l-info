#!/usr/bin/env bash
#
# Prépare la DB DuckDB pour publication sur GitHub Releases.
# Compresse data/ministere.duckdb, génère le SHA256, affiche la commande gh.
#
# Usage : ./scripts/publish_db.sh
#
# Le script N'exécute PAS gh release create — la publication reste manuelle.
# Format du tag : db-YYYY-MM (ex: db-2026-05)

set -euo pipefail

REPO="crocdeine/ministere-de-l-info"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_DIR/data"
DB_FILE="$DATA_DIR/ministere.duckdb"
GZ_FILE="$DATA_DIR/ministere.duckdb.gz"
SHA_FILE="$DATA_DIR/ministere.duckdb.gz.sha256"
MAX_SIZE_BYTES=$((2 * 1024 * 1024 * 1024))  # 2 GB = limite GitHub Releases

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Vérifier que la DB source existe
if [ ! -f "$DB_FILE" ]; then
    echo "ERREUR : $DB_FILE introuvable" >&2
    echo "Lancer l'ETL d'abord : uv run python scripts/etl_territoires.py --yes" >&2
    exit 1
fi

DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
log "DB source : $DB_FILE ($DB_SIZE)"

# Compresser
log "Compression gzip..."
gzip -kf "$DB_FILE"

GZ_SIZE=$(du -h "$GZ_FILE" | cut -f1)
log "Compressé : $GZ_FILE ($GZ_SIZE)"

# Ratio de compression
if command -v python3 &>/dev/null; then
    python3 -c "
import os
orig = os.path.getsize('$DB_FILE')
comp = os.path.getsize('$GZ_FILE')
ratio = orig / comp
print(f'Ratio de compression : {ratio:.1f}x ({orig // 1024 // 1024} MB → {comp // 1024 // 1024} MB)')
"
fi

# Vérifier la limite GitHub Releases (2 GB)
if command -v stat &>/dev/null; then
    # macOS: stat -f%z, Linux: stat -c%s
    GZ_BYTES=$(stat -f%z "$GZ_FILE" 2>/dev/null || stat -c%s "$GZ_FILE")
    if [ "$GZ_BYTES" -gt "$MAX_SIZE_BYTES" ]; then
        echo "ERREUR : fichier compressé ($GZ_BYTES bytes) dépasse la limite GitHub (2 GB)" >&2
        rm -f "$GZ_FILE"
        exit 2
    fi
    log "Taille OK (< 2 GB limite GitHub Releases)"
fi

# Générer le SHA256
log "Génération SHA256..."
if command -v sha256sum &>/dev/null; then
    sha256sum "$GZ_FILE" > "$SHA_FILE"
else
    shasum -a 256 "$GZ_FILE" > "$SHA_FILE"
fi
SHA=$(awk '{print $1}' "$SHA_FILE")
log "SHA256 : $SHA"
log "Fichier checksum : $SHA_FILE"

# Tag suggéré
TAG="db-$(date '+%Y-%m')"

# Afficher la commande à exécuter
echo ""
echo "========================================================"
echo " Commande gh release create à exécuter manuellement :"
echo "========================================================"
echo ""
echo "gh release create $TAG \\"
echo "  --repo $REPO \\"
echo "  --title 'DB $TAG — $(date '+%Y-%m-%d')' \\"
echo "  --notes 'Base DuckDB : régions, départements, EPCI, communes, arrondissements, circonscriptions, populations 2013/2018/2023' \\"
echo "  '$GZ_FILE#ministere.duckdb.gz' \\"
echo "  '$SHA_FILE#ministere.duckdb.gz.sha256'"
echo ""
echo "Fichiers créés :"
echo "  $GZ_FILE"
echo "  $SHA_FILE"
echo ""
echo "Nettoyer après publication :"
echo "  rm -f $GZ_FILE $SHA_FILE"

exit 0
