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

echo -e "\n${BOLD}🔄 Mise à jour de Ministère de l'Info${NC}\n"

# Vérifier que l'installation existe
if [[ ! -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
  fail "Installation non trouvée. Lancez d'abord le script d'installation : bash <(curl -fsSL https://raw.githubusercontent.com/${REPO}/main/deploy/install.sh)"
fi

# Vérifier qu'OrbStack/Docker tourne
if ! docker info &>/dev/null 2>&1; then
  info "Démarrage d'OrbStack..."
  open -a OrbStack
  info "Attente du démarrage (jusqu'à 30 secondes)..."
  for i in $(seq 1 15); do
    sleep 2
    docker info &>/dev/null 2>&1 && break
    if [[ "$i" -eq 15 ]]; then
      fail "OrbStack ne répond pas. Ouvrez OrbStack manuellement puis relancez."
    fi
    echo -n "."
  done
  echo ""
fi

cd "$COMPOSE_DIR"
APP_PORT=$(grep 'APP_PORT' "${COMPOSE_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "8501")

# ── Mise à jour du code ──────────────────────────────────────────────────
info "Vérification des mises à jour de l'application..."
docker compose pull
ok "Vérification terminée"

# ── Mise à jour de la DB ─────────────────────────────────────────────────
info "Vérification des mises à jour de la base de données..."

LATEST_RELEASE=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | \
  grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/' || echo "")

if [[ -z "$LATEST_RELEASE" ]]; then
  warn "Impossible de contacter l'API GitHub. La vérification de la base de données est ignorée."
else
  CHECKSUM_URL="https://github.com/${REPO}/releases/download/${LATEST_RELEASE}/ministere.duckdb.gz.sha256"
  DB_URL="https://github.com/${REPO}/releases/download/${LATEST_RELEASE}/ministere.duckdb.gz"

  if curl --head --silent --fail "$CHECKSUM_URL" >/dev/null 2>&1; then
    REMOTE_CHECKSUM=$(curl -fsSL "$CHECKSUM_URL" | awk '{print $1}')
    LOCAL_CHECKSUM=$(shasum -a 256 "${DATA_DIR}/ministere.duckdb" 2>/dev/null | awk '{print $1}' || echo "absent")

    if [[ "$REMOTE_CHECKSUM" != "$LOCAL_CHECKSUM" ]]; then
      info "Nouvelle base de données disponible. Téléchargement en cours..."
      info "(Ceci peut prendre quelques minutes)"
      curl -fsSL --progress-bar "$DB_URL" -o "/tmp/ministere.duckdb.gz" || \
        fail "Échec du téléchargement."
      info "Arrêt temporaire de l'application pour la mise à jour des données..."
      docker compose stop
      gunzip -f "/tmp/ministere.duckdb.gz"
      mv "/tmp/ministere.duckdb" "${DATA_DIR}/ministere.duckdb"
      ok "Base de données mise à jour"
    else
      ok "Base de données déjà à jour"
    fi
  else
    info "Pas de checksum disponible pour cette release — vérification ignorée."
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
