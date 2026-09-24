#!/usr/bin/env bash
set -euo pipefail

# ── Couleurs et helpers ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }

REPO="crocdeine/ministere-de-l-info"
DATA_DIR="${HOME}/.ministere-info/data"
COMPOSE_DIR="${HOME}/.ministere-info"
STATE_FILE="${COMPOSE_DIR}/db-release.state"

# ── Synchronisation de la base (bloc identique dans install.sh et update.sh) ──
#
# Convention d'empreinte (voir deploy/README-deploy.md) :
#   ministere.duckdb.gz.sha256 = SHA256 du fichier COMPRESSÉ ministere.duckdb.gz
#   (format « <hash>  ministere.duckdb.gz » ; seul le premier champ est lu).
# Rétrocompatibilité : une empreinte égale au SHA256 de la base DÉCOMPRESSÉE
# (variante historique) est aussi acceptée.
# L'état local (STATE_FILE) conserve l'empreinte publiée de la release
# installée : update.sh compare cette valeur, sans re-hacher la base.

GITHUB_API="https://api.github.com"
DB_ASSET="ministere.duckdb.gz"
DB_FILE="${DATA_DIR}/ministere.duckdb"
DB_TAG=""
DB_URL=""
NEW_GZ_SHA=""
NEW_DB_SHA=""
DL_DIR=""

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

state_get() {
  [[ -f "$STATE_FILE" ]] || return 0
  grep -E "^$1=" "$STATE_FILE" | tail -n 1 | cut -d= -f2- || true
}

# write_state <tag> <empreinte publiée> <sha256 .gz> <sha256 base>
write_state() {
  {
    echo "# Généré par install.sh / update.sh — ne pas modifier"
    echo "DB_RELEASE_TAG=$1"
    echo "DB_REMOTE_SHA256=$2"
    echo "DB_GZ_SHA256=$3"
    echo "DB_SHA256=$4"
    echo "DB_UPDATED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } > "${STATE_FILE}.tmp"
  mv -f "${STATE_FILE}.tmp" "$STATE_FILE"
}

# Release la plus récente contenant l'asset DB (toutes les releases n'en ont pas).
# Positionne DB_TAG et DB_URL. Retourne 1 si l'API est injoignable ou sans asset.
find_db_release() {
  local json
  json=$(curl -fsSL "${GITHUB_API}/repos/${REPO}/releases?per_page=30" 2>/dev/null) || return 1
  DB_URL=$(printf '%s\n' "$json" \
    | grep -oE "\"browser_download_url\": *\"[^\"]*/${DB_ASSET//./\\.}\"" \
    | sed -n '1p' | sed -E 's/.*"(https:[^"]*)"$/\1/' || true)
  [[ -n "$DB_URL" ]] || return 1
  DB_TAG=$(printf '%s\n' "$DB_URL" | sed -E 's#.*/releases/download/([^/]+)/[^/]+$#\1#')
}

# Affiche l'empreinte publiée (64 hex minuscules), ou rien si illisible.
fetch_remote_sha() {
  local sha
  sha=$(curl -fsSL "$1" 2>/dev/null | awk 'NR==1 {print tolower($1)}' || true)
  if [[ "$sha" =~ ^[0-9a-f]{64}$ ]]; then
    printf '%s\n' "$sha"
  fi
}

# Vrai si la base locale correspond déjà à l'empreinte publiée $1.
db_is_current() {
  [[ -f "$DB_FILE" ]] || return 1
  local known local_sha
  known=$(state_get DB_REMOTE_SHA256)
  if [[ -n "$known" ]]; then
    [[ "$known" == "$1" ]]
    return
  fi
  # Pas d'état local (installation antérieure au correctif) : seule la variante
  # historique (empreinte de la base décompressée) est vérifiable sans retélécharger.
  info "Aucun état local : calcul de l'empreinte de la base installée..."
  local_sha=$(sha256_of "$DB_FILE")
  if [[ "$local_sha" == "$1" ]]; then
    write_state "$DB_TAG" "$1" "" "$local_sha"
    return 0
  fi
  return 1
}

cleanup_download() {
  if [[ -n "$DL_DIR" && -d "$DL_DIR" ]]; then
    rm -rf "$DL_DIR"
  fi
  DL_DIR=""
}

# Télécharge et vérifie la base dans un dossier temporaire (même disque que
# DATA_DIR, pour un remplacement atomique). La base en place n'est pas touchée.
# download_and_verify <url .gz> <empreinte publiée>
download_and_verify() {
  cleanup_download
  DL_DIR=$(mktemp -d "${COMPOSE_DIR}/.telechargement.XXXXXX") || return 1
  curl -fSL --progress-bar "$1" -o "${DL_DIR}/${DB_ASSET}" || {
    warn "Échec du téléchargement."
    return 1
  }
  NEW_GZ_SHA=$(sha256_of "${DL_DIR}/${DB_ASSET}")
  gzip -t "${DL_DIR}/${DB_ASSET}" 2>/dev/null || {
    warn "Archive corrompue (gzip -t)."
    return 1
  }
  info "Décompression de la base de données..."
  gunzip -c "${DL_DIR}/${DB_ASSET}" > "${DL_DIR}/ministere.duckdb" || return 1
  rm -f "${DL_DIR:?}/${DB_ASSET}"
  NEW_DB_SHA=$(sha256_of "${DL_DIR}/ministere.duckdb")
  if [[ "$2" == "$NEW_GZ_SHA" ]]; then
    ok "Empreinte SHA256 vérifiée (archive)"
  elif [[ "$2" == "$NEW_DB_SHA" ]]; then
    ok "Empreinte SHA256 vérifiée (base décompressée, format historique)"
  else
    warn "Empreinte SHA256 invalide : publiée $2, archive $NEW_GZ_SHA, base $NEW_DB_SHA"
    return 1
  fi
}

# Remplace la base en place par celle téléchargée et enregistre l'état.
# install_downloaded_db <empreinte publiée>
install_downloaded_db() {
  mkdir -p "$DATA_DIR"
  mv -f "${DL_DIR}/ministere.duckdb" "$DB_FILE"
  write_state "$DB_TAG" "$1" "$NEW_GZ_SHA" "$NEW_DB_SHA"
  cleanup_download
}

trap cleanup_download EXIT
# ── Fin du bloc synchronisé ──────────────────────────────────────────────

echo -e "\n${BOLD}🔄 Mise à jour de Ministère de l'Info${NC}\n"

# Vérifier que l'installation existe
if [[ ! -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
  fail "Installation non trouvée. Lancez d'abord le script d'installation : bash <(curl -fsSL https://raw.githubusercontent.com/${REPO}/main/deploy/install.sh)"
fi

# Vérifier qu'OrbStack/Docker tourne
if ! docker info &>/dev/null; then
  info "Démarrage d'OrbStack..."
  open -a OrbStack
  info "Attente du démarrage (jusqu'à 30 secondes)..."
  for i in $(seq 1 15); do
    sleep 2
    docker info &>/dev/null && break
    if [[ "$i" -eq 15 ]]; then
      fail "OrbStack ne répond pas. Ouvrez OrbStack manuellement puis relancez."
    fi
    echo -n "."
  done
  echo ""
fi

cd "$COMPOSE_DIR"
APP_PORT=$(grep 'APP_PORT' "${COMPOSE_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "8501")
APP_PORT="${APP_PORT:-8501}"

# ── Mise à jour du code ──────────────────────────────────────────────────
info "Vérification des mises à jour de l'application..."
docker compose pull
ok "Vérification terminée"

# ── Mise à jour de la DB ─────────────────────────────────────────────────
info "Vérification des mises à jour de la base de données..."

if ! find_db_release; then
  warn "Impossible de trouver une base de données dans les releases GitHub. Vérification ignorée."
else
  REMOTE_SHA=$(fetch_remote_sha "${DB_URL}.sha256")
  if [[ -z "$REMOTE_SHA" ]]; then
    info "Pas de checksum lisible pour la release ${DB_TAG} — vérification ignorée."
  elif db_is_current "$REMOTE_SHA"; then
    ok "Base de données déjà à jour (release ${DB_TAG})"
  else
    info "Nouvelle base de données disponible (release ${DB_TAG}). Téléchargement en cours..."
    info "(Ceci peut prendre quelques minutes)"
    download_and_verify "$DB_URL" "$REMOTE_SHA" || \
      fail "Mise à jour de la base abandonnée. La base actuelle est conservée."
    info "Arrêt temporaire de l'application pour la mise à jour des données..."
    docker compose stop
    install_downloaded_db "$REMOTE_SHA"
    ok "Base de données mise à jour (release ${DB_TAG})"
  fi
fi

# ── Redémarrage ──────────────────────────────────────────────────────────
info "Redémarrage de l'application..."
docker compose up -d

info "Attente du redémarrage (jusqu'à 60 secondes)..."
ELAPSED=0
while ! curl -sf "http://localhost:${APP_PORT}/_stcore/health" >/dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  if [[ "$ELAPSED" -ge 60 ]]; then
    fail "L'application n'a pas redémarré. Consultez : docker logs ministere-info"
  fi
  echo -n "."
done
echo ""
ok "Application redémarrée"

open "http://localhost:${APP_PORT}"

echo ""
echo -e "${GREEN}${BOLD}🎉 Mise à jour terminée !${NC}"
