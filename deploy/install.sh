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
IMAGE="ghcr.io/${REPO}:latest"
DATA_DIR="${HOME}/.ministere-info/data"
COMPOSE_DIR="${HOME}/.ministere-info"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
LAUNCH_AGENT_PLIST="${LAUNCH_AGENT_DIR}/com.ministere-info.plist"
APP_PORT=8501

# ── Étape 1 : Vérifications préalables ──────────────────────────────────
echo -e "\n${BOLD}🗳️  Installation de Ministère de l'Info${NC}\n"

info "Vérification de la version macOS..."
OS_VERSION=$(sw_vers -productVersion)
OS_MAJOR=$(echo "$OS_VERSION" | cut -d. -f1)
if [[ "$OS_MAJOR" -lt 13 ]]; then
  fail "macOS $OS_VERSION détecté. macOS 13 (Ventura) ou plus récent requis."
fi
ok "macOS $OS_VERSION compatible"

info "Vérification de l'espace disque..."
AVAILABLE_KB=$(df -k "$HOME" | awk 'NR==2 {print $4}')
AVAILABLE_GB=$(( AVAILABLE_KB / 1024 / 1024 ))
if [[ "$AVAILABLE_GB" -lt 4 ]]; then
  fail "Espace disque insuffisant : ${AVAILABLE_GB} Go disponibles, 4 Go requis."
fi
ok "${AVAILABLE_GB} Go disponibles"

info "Vérification du port $APP_PORT..."
if lsof -Pi ":$APP_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  warn "Le port $APP_PORT est déjà utilisé. L'app utilisera le port 8502."
  APP_PORT=8502
fi
ok "Port $APP_PORT disponible"

# ── Étape 2 : Homebrew ──────────────────────────────────────────────────
info "Vérification de Homebrew..."
if ! command -v brew &>/dev/null; then
  info "Installation de Homebrew (gestionnaire de logiciels pour Mac)..."
  info "Votre mot de passe macOS sera demandé."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || \
    fail "Échec de l'installation de Homebrew."
  if [[ -f "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "${HOME}/.zprofile"
  fi
  ok "Homebrew installé"
else
  ok "Homebrew déjà installé ($(brew --version | head -1))"
fi

# ── Étape 3 : OrbStack ──────────────────────────────────────────────────
info "Vérification d'OrbStack..."
if ! orbctl version &>/dev/null 2>&1; then
  info "Installation d'OrbStack (gestionnaire de containers léger et natif pour Mac)..."
  brew install --cask orbstack || fail "Échec de l'installation d'OrbStack."
  info "Démarrage d'OrbStack..."
  open -a OrbStack
  info "Attente du démarrage d'OrbStack (jusqu'à 60 secondes)..."
  TIMEOUT=60
  ELAPSED=0
  while ! docker info &>/dev/null 2>&1; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
      fail "OrbStack n'a pas démarré dans les temps. Relancez le script après avoir ouvert OrbStack manuellement."
    fi
    echo -n "."
  done
  echo ""
  ok "OrbStack opérationnel"
else
  ok "OrbStack déjà installé"
  if ! docker info &>/dev/null 2>&1; then
    info "Démarrage d'OrbStack..."
    open -a OrbStack
    sleep 5
    docker info &>/dev/null 2>&1 || fail "OrbStack ne répond pas. Ouvrez OrbStack manuellement et relancez."
  fi
fi


# ── Étape 4 : Dossiers et configuration ─────────────────────────────────
info "Création des dossiers de données..."
mkdir -p "$DATA_DIR"
mkdir -p "$COMPOSE_DIR"
ok "Dossiers créés dans ~/.ministere-info/"

info "Téléchargement de la configuration..."
curl -fsSL "https://raw.githubusercontent.com/${REPO}/main/deploy/docker-compose.yml" \
  -o "${COMPOSE_DIR}/docker-compose.yml" || \
  fail "Impossible de télécharger la configuration. Vérifiez votre connexion internet."

cat > "${COMPOSE_DIR}/.env" <<EOF
APP_PORT=${APP_PORT}
DB_PATH=${DATA_DIR}
EOF
ok "Configuration créée"

# ── Étape 5 : Base de données initiale ──────────────────────────────────
info "Recherche de la base de données dans les releases GitHub..."

LATEST_RELEASE=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | \
  grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/' || echo "")

if [[ -z "$LATEST_RELEASE" ]]; then
  warn "Impossible de contacter l'API GitHub. La base de données ne sera pas téléchargée automatiquement."
else
  DB_URL="https://github.com/${REPO}/releases/download/${LATEST_RELEASE}/ministere.duckdb.gz"
  if curl --head --silent --fail "$DB_URL" >/dev/null 2>&1; then
    info "Base de données trouvée (release ${LATEST_RELEASE}). Téléchargement en cours..."
    info "(Ceci peut prendre quelques minutes selon votre connexion — la base fait environ 1 Go)"
    curl -fsSL --progress-bar "$DB_URL" -o "/tmp/ministere.duckdb.gz" || \
      fail "Échec du téléchargement de la base de données."
    info "Décompression de la base de données..."
    gunzip -f "/tmp/ministere.duckdb.gz"
    mv "/tmp/ministere.duckdb" "${DATA_DIR}/ministere.duckdb"
    ok "Base de données installée (${DATA_DIR}/ministere.duckdb)"
  else
    warn "Base de données non trouvée dans la release ${LATEST_RELEASE}."
    warn "L'app démarrera sans données. Contactez Mathias pour obtenir la base de données."
  fi
fi

# ── Étape 6 : Téléchargement et démarrage ───────────────────────────────
info "Téléchargement de l'application (première fois : quelques minutes)..."
cd "$COMPOSE_DIR"
docker compose pull || fail "Impossible de télécharger l'application. Vérifiez votre connexion internet."
ok "Application téléchargée"

info "Démarrage de l'application..."
docker compose up -d || fail "Impossible de démarrer l'application."

info "Attente du démarrage (jusqu'à 60 secondes)..."
TIMEOUT=60
ELAPSED=0
while ! curl -sf "http://localhost:${APP_PORT}/_stcore/health" >/dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
    fail "L'application n'a pas démarré dans les temps. Consultez les logs : docker logs ministere-info"
  fi
  echo -n "."
done
echo ""
ok "Application démarrée"

# ── Étape 7 : Script de démarrage robuste ───────────────────────────────
info "Création du script de démarrage automatique..."
cat > "${COMPOSE_DIR}/start.sh" <<'STARTSCRIPT'
#!/usr/bin/env bash
# Attend que Docker soit disponible puis démarre l'application
for i in $(seq 1 30); do
  docker info &>/dev/null 2>&1 && break
  sleep 2
done
cd "$(dirname "$0")" && docker compose up -d
STARTSCRIPT
chmod +x "${COMPOSE_DIR}/start.sh"

# ── Étape 8 : LaunchAgent (démarrage automatique au login) ───────────────
info "Configuration du démarrage automatique..."
mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ministere-info</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${COMPOSE_DIR}/start.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${COMPOSE_DIR}/launch.log</string>
  <key>StandardErrorPath</key>
  <string>${COMPOSE_DIR}/launch-error.log</string>
</dict>
</plist>
EOF

launchctl load "$LAUNCH_AGENT_PLIST" 2>/dev/null || true
ok "Démarrage automatique configuré"

# ── Étape 9 : Ouverture du navigateur ───────────────────────────────────
info "Ouverture de l'application dans le navigateur..."
open "http://localhost:${APP_PORT}"

# ── Succès ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}🎉 Installation terminée !${NC}"
echo ""
echo -e "L'application est accessible à : ${BOLD}http://localhost:${APP_PORT}${NC}"
echo ""
echo -e "L'app démarrera ${BOLD}automatiquement${NC} à chaque allumage de votre Mac."
echo ""
echo -e "Pour mettre à jour l'application :"
echo -e "  ${BLUE}bash <(curl -fsSL https://raw.githubusercontent.com/${REPO}/main/deploy/update.sh)${NC}"
echo ""
echo -e "En cas de problème, contactez Mathias."
