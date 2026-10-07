#!/usr/bin/env bash
#
# Installateur de « Ministère de l'Info » (macOS), en une commande :
#
#   curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/v1.0.0/install.sh | bash
#
# Installe (ou met à jour) l'application dans
#   ~/Library/Application Support/Ministere-de-l-Info/   (code, base, Python, environnement)
# crée l'icône ~/Applications/Ministère de l'Info.app et écrit son journal dans
#   ~/Library/Logs/Ministere-de-l-Info/
# Aucun sudo, aucun jeton GitHub. Relancer la même commande = mise à jour.
# Désinstallation : uninstall.sh (voir docs/guide-utilisateur.md).
#
# Mode test local (fichiers locaux au lieu de GitHub, dossiers de test) :
#   MI_SOURCE_ARCHIVE  archive .tar.gz du code (un dossier racine, comme celle de GitHub)
#   MI_DB_ARCHIVE      ministere.duckdb.gz local (+ MI_DB_ARCHIVE.sha256 à côté)
#   MI_INSTALL_DIR     dossier d'installation
#   MI_APPS_DIR        dossier où créer l'icône
#   MI_LOG_DIR         dossier des journaux
#
# Tout le script est dans `main`, appelée en dernière ligne : un téléchargement
# coupé de ce script par `curl | bash` n'exécute rien.
# Compatible bash 3.2 (macOS).

set -euo pipefail

VERSION="1.0.0"
DB_TAG="db-2026-10-04"      # release GitHub de la base (asset ministere.duckdb.gz + .sha256)
VERSION_UV="0.11.16"        # même version que deploy/native/install-native.sh
DEPOT="crocdeine/ministere-de-l-info"
NOM_APP="Ministère de l'Info"
# Espace libre exigé (Mo) : base décompressée ≈ 1 300 + archive ≈ 700 + Python et
# environnement ≈ 1 000 ; sans téléchargement de base : 1 000.
ESPACE_AVEC_BASE_MO=3000
ESPACE_SANS_BASE_MO=1000

main() {
  local install_dir apps_dir log_dir journal
  install_dir="${MI_INSTALL_DIR:-${HOME}/Library/Application Support/Ministere-de-l-Info}"
  apps_dir="${MI_APPS_DIR:-${HOME}/Applications}"
  log_dir="${MI_LOG_DIR:-${HOME}/Library/Logs/Ministere-de-l-Info}"
  journal="${log_dir}/installation.log"

  mkdir -p "$install_dir" "$apps_dir" "$log_dir"
  JOURNAL="$journal"
  {
    echo
    echo "=== Installation $VERSION — $(date '+%Y-%m-%d %H:%M:%S') ==="
  } >>"$JOURNAL"

  dire "Installation de « $NOM_APP » (version $VERSION)"

  # ── 1. Vérifications ────────────────────────────────────────────────────
  etape "1/7 Vérification du Mac..."
  [ "$(uname -s)" = "Darwin" ] || echec "Cet installateur ne fonctionne que sur Mac."
  if [ "$(uname -m)" != "arm64" ]; then
    attention "Mac Intel : installation non testée (seuls les Mac Apple Silicon l'ont été)."
  fi
  command -v curl >/dev/null 2>&1 || echec "La commande curl est introuvable."

  local base="$install_dir/ministere.duckdb"
  local empreinte_installee="$install_dir/ministere.duckdb.gz.sha256"
  local besoin=$ESPACE_SANS_BASE_MO
  [ -s "$base" ] || besoin=$ESPACE_AVEC_BASE_MO
  local libre
  libre="$(df -Pk "$install_dir" | awk 'NR==2 {print int($4 / 1024)}')"
  if [ "$libre" -lt "$besoin" ]; then
    echec "Espace disque insuffisant : ${libre} Mo libres, ${besoin} Mo nécessaires. Libérez de la place puis relancez la commande."
  fi
  ok "Mac compatible, ${libre} Mo libres"

  # ── 2. uv (gestionnaire Python) ─────────────────────────────────────────
  etape "2/7 Préparation de l'outil d'installation (uv $VERSION_UV)..."
  local uv="$install_dir/bin/uv"
  if [ ! -x "$uv" ] || [ "$("$uv" --version 2>/dev/null | awk '{print $2}')" != "$VERSION_UV" ]; then
    lancer "Téléchargement de uv impossible (connexion Internet ?)." \
      env UV_INSTALL_DIR="$install_dir/bin" UV_NO_MODIFY_PATH=1 INSTALLER_NO_MODIFY_PATH=1 \
      sh -c "curl -fsSL https://astral.sh/uv/${VERSION_UV}/install.sh | sh"
  fi
  [ -x "$uv" ] || echec "uv introuvable après installation ($uv)."
  ok "uv prêt"
  # Python, cache et environnement restent dans le dossier d'installation.
  export UV_PYTHON_INSTALL_DIR="$install_dir/python"
  export UV_CACHE_DIR="$install_dir/cache"
  export UV_PROJECT_ENVIRONMENT="$install_dir/venv"
  export UV_PYTHON_PREFERENCE="only-managed"
  export UV_NO_PROGRESS=1

  # ── 3. Code de l'application ────────────────────────────────────────────
  etape "3/7 Téléchargement de l'application..."
  local archive_code="$install_dir/code-$VERSION.tar.gz"
  if [ -n "${MI_SOURCE_ARCHIVE:-}" ]; then
    cp "$MI_SOURCE_ARCHIVE" "$archive_code"
  else
    telecharger "https://github.com/${DEPOT}/archive/refs/tags/v${VERSION}.tar.gz" "$archive_code"
  fi
  rm -rf "$install_dir/code.nouveau"
  mkdir -p "$install_dir/code.nouveau"
  lancer "Archive de l'application illisible." \
    tar -xzf "$archive_code" -C "$install_dir/code.nouveau" --strip-components 1
  [ -f "$install_dir/code.nouveau/app.py" ] || echec "Archive de l'application incomplète (app.py absent)."
  arreter_serveur "$install_dir"
  rm -rf "$install_dir/code.ancien"
  [ -d "$install_dir/code" ] && mv "$install_dir/code" "$install_dir/code.ancien"
  mv "$install_dir/code.nouveau" "$install_dir/code"
  rm -rf "$install_dir/code.ancien" "$archive_code"
  ok "Application $VERSION"

  # ── 4. Python et dépendances ────────────────────────────────────────────
  etape "4/7 Installation de Python et des bibliothèques (quelques minutes la première fois)..."
  lancer "Installation des bibliothèques impossible (connexion Internet ?)." \
    "$uv" sync --frozen --no-dev --python 3.12 --project "$install_dir/code"
  lancer "Extension cartographique de DuckDB impossible à installer (connexion Internet ?)." \
    "$install_dir/venv/bin/python" -c \
    "import duckdb; c = duckdb.connect(); c.execute('INSTALL spatial'); c.execute('LOAD spatial')"
  "$uv" cache clean >>"$JOURNAL" 2>&1 || true
  ok "Python et bibliothèques prêts"

  # ── 5. Base de données ──────────────────────────────────────────────────
  etape "5/7 Base de données ($DB_TAG)..."
  installer_base "$install_dir" "$base" "$empreinte_installee"

  # ── 6. Icône ────────────────────────────────────────────────────────────
  etape "6/7 Création de l'icône dans $apps_dir..."
  creer_app "$install_dir" "$apps_dir/$NOM_APP.app" "$log_dir"
  ok "Icône « $NOM_APP » créée"

  # ── 7. Fin ──────────────────────────────────────────────────────────────
  etape "7/7 Vérification..."
  "$install_dir/venv/bin/python" -c "import streamlit, duckdb, ministere_de_l_info" >>"$JOURNAL" 2>&1 ||
    echec "L'application installée ne démarre pas."
  ok "Installation terminée ($(du -sh "$install_dir" | awk '{print $1}') utilisés)"
  dire ""
  dire "Pour ouvrir l'application : dossier Applications de votre dossier personnel,"
  dire "icône « $NOM_APP » (double-clic). Elle s'ouvre dans votre navigateur."
  dire "Pour mettre à jour : relancer la même commande."
}

# ── Messages ──────────────────────────────────────────────────────────────
JOURNAL="/dev/null"
dire() { printf '%s\n' "$*" | tee -a "$JOURNAL"; }
etape() { dire "$*"; }
ok() { dire "   OK : $*"; }
attention() { dire "   Attention : $*"; }
echec() {
  printf '\nÉCHEC : %s\n' "$*" | tee -a "$JOURNAL" >&2
  printf 'Détails dans le journal : %s\n' "$JOURNAL" >&2
  exit 1
}
lancer() {
  # lancer <message d'échec> <commande...> : sortie de la commande dans le journal
  local message="$1"
  shift
  "$@" </dev/null >>"$JOURNAL" 2>&1 || echec "$message"
}
arreter_serveur() {
  # Arrête le serveur lancé par l'icône (avant de remplacer son code).
  local pid_fichier="$1/serveur.pid" pid
  [ -f "$pid_fichier" ] || return 0
  pid="$(cat "$pid_fichier")"
  if kill -0 "$pid" 2>/dev/null; then
    dire "   Arrêt de l'application en cours d'exécution..."
    kill "$pid" 2>/dev/null || true
    sleep 2
  fi
  rm -f "$pid_fichier"
}
sha256_de() { shasum -a 256 "$1" | awk '{print $1}'; }

telecharger() {
  # telecharger <url> <destination> : reprend un téléchargement interrompu.
  local url="$1" dest="$2" code=0
  curl -fL --retry 3 --progress-bar -C - -o "$dest" "$url" </dev/null || code=$?
  if { [ "$code" -eq 33 ] || [ "$code" -eq 22 ]; } && [ -f "$dest" ]; then
    # 33 = reprise refusée par le serveur, 22 = 416 (fichier déjà complet ou changé) :
    # on repart de zéro une fois.
    rm -f "$dest"
    code=0
    curl -fL --retry 3 --progress-bar -o "$dest" "$url" </dev/null || code=$?
  fi
  [ "$code" -eq 0 ] || echec "Téléchargement interrompu ($url). Relancez la commande : il reprendra où il s'est arrêté."
}

installer_base() {
  local install_dir="$1" base="$2" empreinte_installee="$3"
  local archive="$install_dir/ministere.duckdb.gz" attendue
  if [ -n "${MI_DB_ARCHIVE:-}" ]; then
    attendue="$(awk 'NR==1 {print tolower($1)}' "${MI_DB_ARCHIVE}.sha256")"
  else
    attendue="$(curl -fsSL --retry 3 \
      "https://github.com/${DEPOT}/releases/download/${DB_TAG}/ministere.duckdb.gz.sha256" </dev/null |
      awk 'NR==1 {print tolower($1)}')" || attendue=""
  fi
  [ -n "$attendue" ] || echec "Empreinte de la base introuvable (release $DB_TAG)."

  if [ -s "$base" ] && [ -f "$empreinte_installee" ] && [ "$(cat "$empreinte_installee")" = "$attendue" ]; then
    ok "Base déjà à jour, conservée"
    return 0
  fi

  # Archive partielle d'un essai précédent : reprise ; archive complète : réutilisée.
  if [ ! -f "$archive" ] || [ "$(sha256_de "$archive")" != "$attendue" ]; then
    if [ -n "${MI_DB_ARCHIVE:-}" ]; then
      cp "$MI_DB_ARCHIVE" "$archive"
    else
      dire "   Téléchargement (environ 700 Mo)..."
      telecharger "https://github.com/${DEPOT}/releases/download/${DB_TAG}/ministere.duckdb.gz" "$archive"
    fi
  fi

  dire "   Vérification de l'empreinte et décompression..."
  local recue
  recue="$(sha256_de "$archive")"
  lancer "Archive de la base corrompue." gzip -t "$archive"
  rm -f "$base.nouvelle"
  gunzip -c "$archive" >"$base.nouvelle" || echec "Décompression de la base impossible."
  if [ "$recue" != "$attendue" ] && [ "$(sha256_de "$base.nouvelle")" != "$attendue" ]; then
    # Ni l'archive ni la base décompressée (format historique) ne correspondent.
    rm -f "$archive" "$base.nouvelle"
    echec "Empreinte SHA-256 de la base invalide (attendue $attendue, reçue $recue). Relancez la commande."
  fi
  mv -f "$base.nouvelle" "$base"
  printf '%s\n' "$attendue" >"$empreinte_installee"
  rm -f "$archive"
  ok "Base installée ($(du -h "$base" | awk '{print $1}'))"
}

creer_app() {
  # creer_app <dossier d'installation> <chemin .app> <dossier des journaux>
  local install_dir="$1" app="$2" log_dir="$3" tmp
  tmp="${app}.tmp"
  rm -rf "$tmp"
  mkdir -p "$tmp/Contents/MacOS"
  cat >"$tmp/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Ministère de l'Info</string>
  <key>CFBundleDisplayName</key><string>Ministère de l'Info</string>
  <key>CFBundleIdentifier</key><string>com.crocdeine.ministere-info.lanceur</string>
  <key>CFBundleExecutable</key><string>lancer</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
EOF
  {
    echo '#!/bin/bash'
    echo '# Généré par install.sh : démarre le serveur local si besoin, puis ouvre le navigateur.'
    printf 'INSTALL_DIR=%q\n' "$install_dir"
    printf 'LOG_DIR=%q\n' "$log_dir"
    cat <<'EOF'
set -euo pipefail
# shellcheck source=/dev/null
source "$INSTALL_DIR/code/deploy/native/commun.sh"
mkdir -p "$LOG_DIR"
JOURNAL="$LOG_DIR/application.log"
FICHIER_PORT="$INSTALL_DIR/port"
FICHIER_PID="$INSTALL_DIR/serveur.pid"

alerte() {
  osascript -e "display alert \"Ministère de l'Info\" message \"$1\"" >/dev/null 2>&1 || true
  echo "$1" >&2
  exit 1
}
ouvrir() {
  [ -n "${MI_NO_BROWSER:-}" ] && { echo "http://127.0.0.1:$1"; return 0; }
  open "http://127.0.0.1:$1"
}

# Serveur déjà lancé par cette icône et qui répond : on rouvre simplement la page.
if [ -f "$FICHIER_PORT" ] && [ -f "$FICHIER_PID" ] &&
  kill -0 "$(cat "$FICHIER_PID")" 2>/dev/null && app_repond "$(cat "$FICHIER_PORT")"; then
  ouvrir "$(cat "$FICHIER_PORT")"
  exit 0
fi

# Premier port libre à partir de 8501.
PORT=8501
while [ -n "$(port_occupe_par "$PORT")" ]; do
  PORT=$((PORT + 1))
  [ "$PORT" -le 8600 ] || alerte "Aucun port libre entre 8501 et 8600."
done
echo "$PORT" >"$FICHIER_PORT"

cd "$INSTALL_DIR/code"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage sur le port $PORT" >>"$JOURNAL"
MINISTERE_DB_PATH="$INSTALL_DIR/ministere.duckdb" nohup "$INSTALL_DIR/venv/bin/python" \
  -m streamlit run app.py --server.address 127.0.0.1 --server.port "$PORT" \
  --server.headless true --server.runOnSave false --server.fileWatcherType none \
  </dev/null >>"$JOURNAL" 2>&1 &
echo $! >"$FICHIER_PID"

attendre_app "$PORT" 90 ||
  alerte "L'application ne démarre pas. Journal : $JOURNAL"
ouvrir "$PORT"
EOF
  } >"$tmp/Contents/MacOS/lancer"
  chmod +x "$tmp/Contents/MacOS/lancer"
  plutil -lint "$tmp/Contents/Info.plist" >>"$JOURNAL" 2>&1 || echec "Icône invalide (Info.plist)."
  rm -rf "$app"
  mv "$tmp" "$app"
}

main "$@"
