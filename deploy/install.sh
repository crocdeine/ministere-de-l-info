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
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
LAUNCH_AGENT_PLIST="${LAUNCH_AGENT_DIR}/com.ministere-info.plist"
STATE_FILE="${COMPOSE_DIR}/db-release.state"
APP_PORT=8501

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
    # shellcheck disable=SC2016  # ligne écrite telle quelle dans .zprofile
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

if ! find_db_release; then
  warn "Impossible de trouver une base de données dans les releases GitHub."
  warn "L'app démarrera sans données. Contactez Mathias pour obtenir la base de données."
else
  REMOTE_SHA=$(fetch_remote_sha "${DB_URL}.sha256")
  [[ -n "$REMOTE_SHA" ]] || \
    fail "Checksum de la base absent ou illisible (release ${DB_TAG}). Installation interrompue."
  info "Base de données trouvée (release ${DB_TAG}). Téléchargement en cours..."
  info "(Ceci peut prendre quelques minutes selon votre connexion — la base fait environ 1 Go)"
  download_and_verify "$DB_URL" "$REMOTE_SHA" || \
    fail "Échec du téléchargement ou de la vérification de la base de données."
  install_downloaded_db "$REMOTE_SHA"
  ok "Base de données installée (${DB_FILE})"
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
