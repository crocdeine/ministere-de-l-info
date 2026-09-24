#!/usr/bin/env bash
#
# Sauvegarde de la base DuckDB réellement utilisée par l'application
# (fichier désigné par MINISTERE_DB_PATH), avec rotation.
#
# Usage manuel      : ./scripts/backup_db.sh
# Usage automatique : LaunchAgent com.crocdeine.ministere-info.backup
#                     (installé par deploy/native/install-native.sh)
#
# Paramètres (variable d'environnement > ~/.config/ministere-info/native.conf > défaut) :
#   MINISTERE_DB_PATH      base à sauvegarder   (défaut : <projet>/data/ministere.duckdb)
#   BACKUP_DEST            dossier destination  (défaut : <projet>/data/backups)
#                          ex. disque externe : /Volumes/MonDisque/ministere-info-sauvegardes
#                          ex. iCloud Drive   : ~/Library/Mobile Documents/com~apple~CloudDocs/ministere-info-sauvegardes
#   BACKUP_RETENTION_DAYS  conservation en jours (défaut : 7)
#   BACKUP_LOG             journal (défaut : ~/Library/Logs/ministere-info/backup.log)
#   MINISTERE_PROJECT_DIR  dossier du projet (défaut : dossier parent de scripts/)
#   MINISTERE_PYTHON       Python avec duckdb (défaut : <projet>/.venv/bin/python)
#
# Méthode (copie à chaud cohérente) :
#   1. Un petit programme Python ouvre la base en LECTURE SEULE. DuckDB pose
#      alors un verrou partagé sur le fichier : les lecteurs (l'application)
#      restent autorisés, mais aucun écrivain (ETL) ne peut l'ouvrir tant que
#      la copie dure. Si un ETL écrit déjà, l'ouverture échoue : la sauvegarde
#      est abandonnée proprement (code 4) plutôt que de copier une base en cours
#      d'écriture.
#   2. Pendant que le verrou est tenu, `cp` (processus séparé, pour ne pas
#      libérer le verrou POSIX du programme Python en fermant le fichier)
#      copie la base (et son journal .wal s'il existe) vers un fichier temporaire.
#   3. La copie est rouverte en lecture seule et comparée à l'original
#      (nombre et taille estimée des tables, nombre de vues).
#   4. Seule une copie vérifiée prend son nom définitif ; la rotation ne
#      supprime des sauvegardes anciennes qu'après ce succès.
#   Restauration = copie d'un fichier (voir docs/deployment.md).
#   EXPORT DATABASE a été écarté : plus lent, restauration en plusieurs étapes
#   et dépendante de l'extension spatial pour les géométries.
#
# Codes de sortie :
#   0 succès · 2 base absente · 3 Python/duckdb indisponible · 4 base en cours
#   d'écriture (ETL) ou copie invalide · 5 succès mais destination indisponible
#   (sauvegarde faite dans <projet>/data/backups) · 6 espace disque insuffisant

set -euo pipefail

# ── Paramètres ───────────────────────────────────────────────────────────
PROJECT_DIR_DEFAUT="$(cd "$(dirname "$0")/.." && pwd)"
CONF="${MINISTERE_NATIVE_CONF:-${HOME}/.config/ministere-info/native.conf}"

conf_valeur() {
  # conf_valeur <CLE> : valeur de la clé dans le fichier de conf (vide sinon)
  [ -f "$CONF" ] || return 0
  awk -v cle="$1" 'index($0, cle "=") == 1 { print substr($0, length(cle) + 2); exit }' "$CONF"
}

# REPO_DIR : nom historique de la variable, conservé pour compatibilité
PROJECT_DIR="${MINISTERE_PROJECT_DIR:-${REPO_DIR:-$(conf_valeur PROJECT_DIR)}}"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_DIR_DEFAUT}"
DB_PATH="${MINISTERE_DB_PATH:-$(conf_valeur MINISTERE_DB_PATH)}"
DB_PATH="${DB_PATH:-${PROJECT_DIR}/data/ministere.duckdb}"
DEST="${BACKUP_DEST:-$(conf_valeur BACKUP_DEST)}"
DEST="${DEST:-${PROJECT_DIR}/data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-$(conf_valeur BACKUP_RETENTION_DAYS)}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
PYTHON="${MINISTERE_PYTHON:-${PROJECT_DIR}/.venv/bin/python}"
LOG_FILE="${BACKUP_LOG:-${HOME}/Library/Logs/ministere-info/backup.log}"
DEST_SECOURS="${PROJECT_DIR}/data/backups"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
  local msg
  msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$LOG_FILE"
}

TMP_DB=""
# shellcheck disable=SC2329 # appelée par trap
nettoyer() {
  if [ -n "$TMP_DB" ]; then
    rm -f "$TMP_DB" "${TMP_DB}.wal"
  fi
}
trap nettoyer EXIT

case "$RETENTION_DAYS" in
  '' | *[!0-9]* | 0)
    log "ERREUR : BACKUP_RETENTION_DAYS invalide ('$RETENTION_DAYS'), 7 utilisé"
    RETENTION_DAYS=7
    ;;
esac

log "Début sauvegarde de $DB_PATH"

# ── 1. Base source ───────────────────────────────────────────────────────
if [ ! -s "$DB_PATH" ]; then
  log "ERREUR : base absente ou vide : $DB_PATH"
  exit 2
fi

# ── 2. Python avec duckdb ────────────────────────────────────────────────
if [ ! -x "$PYTHON" ] || ! "$PYTHON" -c "import duckdb" >/dev/null 2>&1; then
  log "ERREUR : Python avec duckdb introuvable ($PYTHON). Lancer « uv sync --frozen » dans $PROJECT_DIR"
  exit 3
fi

# ── 3. Destination ───────────────────────────────────────────────────────
CODE_FINAL=0
destination_disponible() {
  local d="$1" volume
  case "$d" in
    /Volumes/*)
      # Disque externe : ne jamais créer de dossier sous /Volumes si le disque
      # est débranché (on écrirait sur le disque interne).
      volume="$(echo "$d" | cut -d/ -f1-3)"
      [ -d "$volume" ] || return 1
      ;;
  esac
  mkdir -p "$d" 2>/dev/null || return 1
  [ -w "$d" ]
}

if ! destination_disponible "$DEST"; then
  log "ATTENTION : destination indisponible ($DEST) — sauvegarde de secours dans $DEST_SECOURS"
  DEST="$DEST_SECOURS"
  CODE_FINAL=5
  if ! destination_disponible "$DEST"; then
    log "ERREUR : dossier de secours inaccessible : $DEST"
    exit 5
  fi
fi

# Même disque que la base ? (une panne disque emporterait base et sauvegardes)
PERIPH_BASE="$(df -P "$DB_PATH" 2>/dev/null | awk 'NR==2{print $1}')"
PERIPH_DEST="$(df -P "$DEST" 2>/dev/null | awk 'NR==2{print $1}')"
if [ -n "$PERIPH_BASE" ] && [ "$PERIPH_BASE" = "$PERIPH_DEST" ]; then
  log "ATTENTION : sauvegarde sur le même disque que la base (définir BACKUP_DEST vers un disque externe ou iCloud Drive)"
fi

# Espace libre : taille de la base (+ .wal) + 5 %
BESOIN_KO=$(($(wc -c <"$DB_PATH" | tr -d ' ') / 1024))
if [ -f "${DB_PATH}.wal" ]; then
  BESOIN_KO=$((BESOIN_KO + $(wc -c <"${DB_PATH}.wal" | tr -d ' ') / 1024))
fi
BESOIN_KO=$((BESOIN_KO + BESOIN_KO / 20 + 1))
LIBRE_KO="$(df -Pk "$DEST" 2>/dev/null | awk 'NR==2{print $4}')"
if [ -n "$LIBRE_KO" ] && [ "$LIBRE_KO" -lt "$BESOIN_KO" ]; then
  log "ERREUR : espace insuffisant dans $DEST (${LIBRE_KO} Ko libres, ${BESOIN_KO} Ko nécessaires)"
  exit 6
fi

# ── 4. Copie cohérente et vérification ───────────────────────────────────
HORODATAGE="$(date '+%Y-%m-%d_%H%M')"
FINAL="${DEST}/ministere-${HORODATAGE}.duckdb"
if [ -e "$FINAL" ]; then
  FINAL="${DEST}/ministere-$(date '+%Y-%m-%d_%H%M%S').duckdb"
fi
TMP_DB="${DEST}/.ministere-en-cours-$$.duckdb"

# Code Python lu hors de toute substitution $( ) : bash 3.2 (macOS) analyse
# mal un heredoc contenant des parenthèses à l'intérieur de $( ).
CODE_COPIE=""
read -r -d '' CODE_COPIE <<'PY' || true
"""Copie cohérente d'une base DuckDB sous verrou partagé, puis vérification."""

import os
import subprocess
import sys

import duckdb

source, copie = sys.argv[1], sys.argv[2]


def sql_chaine(chemin: str) -> str:
    """Littéral SQL pour un chemin (apostrophes doublées)."""
    return "'" + chemin.replace("'", "''") + "'"


REQ = (
    "SELECT (SELECT count(*) FROM duckdb_tables() WHERE database_name = '{db}'),"
    " (SELECT coalesce(sum(estimated_size), 0) FROM duckdb_tables()"
    "  WHERE database_name = '{db}'),"
    " (SELECT count(*) FROM duckdb_views() WHERE database_name = '{db}' AND NOT internal)"
)

con = duckdb.connect(":memory:")
try:
    # Les géométries nécessitent parfois l'extension ; absence tolérée
    con.execute("LOAD spatial")
except duckdb.Error:
    pass

try:
    con.execute(f"ATTACH {sql_chaine(source)} AS src (READ_ONLY)")
except duckdb.Error as exc:
    if "lock" in str(exc).lower():
        print(f"VERROU {exc}")
        sys.exit(10)
    raise

empreinte_src = con.execute(REQ.format(db="src")).fetchone()

# Copie par un processus séparé : fermer un descripteur du fichier dans CE
# processus libérerait le verrou POSIX posé par DuckDB.
subprocess.run(["cp", source, copie], check=True)
if os.path.exists(source + ".wal"):
    subprocess.run(["cp", source + ".wal", copie + ".wal"], check=True)

con.execute(f"ATTACH {sql_chaine(copie)} AS cpy (READ_ONLY)")
empreinte_cpy = con.execute(REQ.format(db="cpy")).fetchone()
con.close()

if empreinte_src != empreinte_cpy or empreinte_src[0] == 0:
    print(f"DIFFERENCE source={empreinte_src} copie={empreinte_cpy}")
    sys.exit(11)
print(f"tables={empreinte_src[0]} vues={empreinte_src[2]} lignes_estimees={empreinte_src[1]}")
PY

set +e
RESULTAT="$("$PYTHON" -c "$CODE_COPIE" "$DB_PATH" "$TMP_DB" 2>&1)"
CODE_PY=$?
set -e

case "$CODE_PY" in
  0) ;;
  10)
    log "ERREUR : base en cours d'écriture (ETL en cours ?) — sauvegarde reportée"
    log "        détail : $(echo "$RESULTAT" | tail -n 1)"
    exit 4
    ;;
  *)
    log "ERREUR : copie ou vérification échouée (code $CODE_PY)"
    log "        détail : $(echo "$RESULTAT" | tail -n 1)"
    exit 4
    ;;
esac

mv "$TMP_DB" "$FINAL"
if [ -f "${TMP_DB}.wal" ]; then
  mv "${TMP_DB}.wal" "${FINAL}.wal"
fi
TMP_DB=""
log "OK : $(basename "$FINAL") ($(du -h "$FINAL" | cut -f1), $(echo "$RESULTAT" | tail -n 1))"

# ── 5. Rotation ──────────────────────────────────────────────────────────
SUPPRIMES=0
while IFS= read -r ancien; do
  [ -n "$ancien" ] || continue
  [ "$ancien" = "$FINAL" ] && continue
  rm -f "$ancien" "${ancien}.wal"
  SUPPRIMES=$((SUPPRIMES + 1))
done <<EOF
$(find "$DEST" -maxdepth 1 -type f -name 'ministere-*.duckdb' -mtime +"$RETENTION_DAYS" 2>/dev/null)
EOF
if [ "$SUPPRIMES" -gt 0 ]; then
  log "Rotation : $SUPPRIMES sauvegarde(s) de plus de $RETENTION_DAYS jours supprimée(s)"
fi

NOMBRE="$(find "$DEST" -maxdepth 1 -type f -name 'ministere-*.duckdb' | wc -l | tr -d ' ')"
log "État : $NOMBRE sauvegarde(s) dans $DEST"
log "---"

exit "$CODE_FINAL"
