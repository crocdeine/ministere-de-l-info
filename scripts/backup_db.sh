#!/usr/bin/env bash
#
# Backup automatique de la DB DuckDB depuis le volume Docker.
# Usage manuel : ./scripts/backup_db.sh
# Usage automatique : déclenché par launchd (voir docs/deployment.md)
#
# Sortie : data/backups/ministere-YYYY-MM-DD_HHmm.duckdb
# Rotation : suppression des backups > 7 jours
# Log : data/backups/backup.log

set -euo pipefail

# Configuration
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BACKUP_DIR="$REPO_DIR/data/backups"
LOG_FILE="$BACKUP_DIR/backup.log"
VOLUME_NAME="ministere-info_duckdb-data"
RETENTION_DAYS=7

# Création du dossier de backup si absent
mkdir -p "$BACKUP_DIR"

# Logger qui écrit dans le log et stdout
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

# Vérifier que Docker est disponible
if ! command -v docker &> /dev/null; then
    log "ERREUR : docker non trouvé dans le PATH"
    exit 1
fi

# Vérifier que le volume existe
if ! docker volume inspect "$VOLUME_NAME" &> /dev/null; then
    log "ERREUR : volume $VOLUME_NAME introuvable"
    exit 2
fi

# Nom du fichier de backup
TIMESTAMP=$(date '+%Y-%m-%d_%H%M')
BACKUP_FILE="$BACKUP_DIR/ministere-$TIMESTAMP.duckdb"

log "Début backup → $BACKUP_FILE"

# Copie via container alpine (DuckDB peut être lu pendant la copie, c'est juste un fichier)
if docker run --rm \
    -v "$VOLUME_NAME:/data:ro" \
    -v "$BACKUP_DIR:/backup" \
    alpine cp "/data/ministere.duckdb" "/backup/$(basename "$BACKUP_FILE")"; then

    # Vérifier que le backup n'est pas vide
    if [ -s "$BACKUP_FILE" ]; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "OK : backup créé ($SIZE)"
    else
        log "ERREUR : backup vide, suppression"
        rm -f "$BACKUP_FILE"
        exit 3
    fi
else
    log "ERREUR : échec de la copie Docker"
    exit 4
fi

# Rotation : supprimer les backups > RETENTION_DAYS jours
log "Rotation : suppression des backups > $RETENTION_DAYS jours"
DELETED=$(find "$BACKUP_DIR" -name "ministere-*.duckdb" -type f -mtime +"$RETENTION_DAYS" -delete -print | wc -l | tr -d ' ')
if [ "$DELETED" -gt 0 ]; then
    log "Supprimés : $DELETED ancien(s) backup(s)"
fi

# Lister les backups actuels
COUNT=$(find "$BACKUP_DIR" -name "ministere-*.duckdb" -type f | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "État final : $COUNT backup(s), taille totale $TOTAL_SIZE"
log "---"

exit 0
