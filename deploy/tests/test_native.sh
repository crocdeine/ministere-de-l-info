#!/usr/bin/env bash
#
# Tests simulés (sans macOS, sans réseau) des scripts d'exécution native :
#   deploy/native/install-native.sh, start.sh, stop.sh, status.sh,
#   uninstall-native.sh
#
# Les commandes système (uname, sysctl, launchctl, curl, lsof, uv, open,
# sleep) sont remplacées par des stubs placés en tête du PATH. Le stub
# launchctl tient un registre des agents chargés ; le stub curl répond
# « ok » au contrôle de santé tant que l'agent de l'application est chargé.
# HOME est isolé pour chaque scénario.
#
# Usage : bash deploy/tests/test_native.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NATIVE="$ROOT/deploy/native"
LABEL_APP="com.crocdeine.ministere-info.native"
LABEL_SAUV="com.crocdeine.ministere-info.backup"
PASS=0
FAIL=0

WORK="$(mktemp -d)"
# TEST_GARDER=1 : conserve le dossier de travail pour diagnostic
if [ "${TEST_GARDER:-0}" = "1" ]; then
  echo "Dossier de travail conservé : $WORK"
else
  trap 'rm -rf "$WORK"' EXIT
fi

check() {
  local desc="$1"
  shift
  if "$@"; then
    PASS=$((PASS + 1))
    echo "  ok   - $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  ÉCHEC - $desc"
  fi
}
not() { ! "$@"; }
contient() { grep -qF -- "$2" "$1"; }

# ── Stubs ────────────────────────────────────────────────────────────────
BIN="$WORK/bin"
mkdir -p "$BIN"

cat >"$BIN/uname" <<'STUB'
#!/usr/bin/env bash
case "${1:-}" in
  -s) echo "${FAKE_OS:-Darwin}" ;;
  -m) echo "${FAKE_ARCH:-arm64}" ;;
  *) echo "${FAKE_OS:-Darwin}" ;;
esac
STUB

cat >"$BIN/sysctl" <<'STUB'
#!/usr/bin/env bash
echo "${FAKE_ARM64_HW:-0}"
STUB

cat >"$BIN/launchctl" <<'STUB'
#!/usr/bin/env bash
# Registre des agents chargés : $STATE/agents/<label>
echo "launchctl $*" >>"$STATE/journal"
mkdir -p "$STATE/agents"
label_de() { awk '/<key>Label<\/key>/{getline; gsub(/.*<string>|<\/string>.*/,""); print; exit}' "$1"; }
case "$1" in
  print)
    l="${2##*/}"
    [ -f "$STATE/agents/$l" ] || exit 113
    echo "$l = {"
    echo "	state = running"
    echo "	pid = 4242"
    echo "}"
    ;;
  bootstrap)
    [ "${FAKE_BOOTSTRAP_FAIL:-0}" = "1" ] && exit 5
    l="$(label_de "$3")"
    [ -f "$STATE/agents/$l" ] && exit 17 # déjà chargé : erreur comme launchd
    cp "$3" "$STATE/agents/$l"
    ;;
  bootout)
    l="${2##*/}"
    [ -f "$STATE/agents/$l" ] || exit 3
    rm -f "$STATE/agents/$l"
    ;;
  enable | kickstart) ;;
  *) ;;
esac
exit 0
STUB

cat >"$BIN/curl" <<'STUB'
#!/usr/bin/env bash
url=""
for a in "$@"; do case "$a" in http://*) url="$a" ;; esac; done
echo "curl $url" >>"$STATE/journal"
case "$url" in
  http://127.0.0.1:*/_stcore/health)
    if [ "${FAKE_HEALTH:-ok}" = "ok" ] && [ -f "$STATE/agents/com.crocdeine.ministere-info.native" ]; then
      echo "ok"
      exit 0
    fi
    exit 7
    ;;
esac
exit 22
STUB

cat >"$BIN/lsof" <<'STUB'
#!/usr/bin/env bash
if [ -f "$STATE/port_occupe" ]; then
  echo "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME"
  echo "com.docke 999 mathias 10u IPv4 0x0 0t0 TCP *:8501 (LISTEN)"
  exit 0
fi
exit 1
STUB

# uv : `uv sync` crée .venv/bin/python (stub) dans le dossier courant
cat >"$BIN/uv" <<'STUB'
#!/usr/bin/env bash
echo "uv $* (dans $PWD)" >>"$STATE/journal"
case "${1:-}" in
  --version) echo "uv 0.11.16" ;;
  sync)
    [ "${FAKE_UV_SYNC_FAIL:-0}" = "1" ] && exit 2
    mkdir -p .venv/bin
    cat >.venv/bin/python <<'PY'
#!/usr/bin/env bash
echo "python $*" >>"$STATE/journal"
[ "${FAKE_SPATIAL_FAIL:-0}" = "1" ] && exit 1
exit 0
PY
    chmod +x .venv/bin/python
    ;;
esac
exit 0
STUB

for cmd in open sleep; do
  # shellcheck disable=SC2016 # $* et $STATE sont destinés au stub généré
  printf '#!/usr/bin/env bash\necho "%s $*" >>"$STATE/journal"\nexit 0\n' "$cmd" >"$BIN/$cmd"
done
chmod +x "$BIN"/*

# PATH minimal : stubs + outils système, sans le uv réel (~/.local/bin)
BASE_PATH="$BIN:/usr/local/bin:/usr/bin:/bin"
BIN_SANS_UV="$WORK/bin-sans-uv"
mkdir -p "$BIN_SANS_UV"
for f in "$BIN"/*; do
  [ "$(basename "$f")" = "uv" ] || cp "$f" "$BIN_SANS_UV/"
done

# ── Environnement par scénario ───────────────────────────────────────────
# nouvel_env <nom> [dossier projet] : HOME, registre launchd et projet factices
nouvel_env() {
  local nom="$1"
  S="$WORK/$nom"
  export HOME="$S/home"
  export STATE="$S/state"
  PROJ="${2:-$S/projet}"
  mkdir -p "$HOME" "$STATE" "$PROJ/data"
  : >"$STATE/journal"
  touch "$PROJ/app.py" "$PROJ/pyproject.toml" "$PROJ/uv.lock"
  echo "base factice" >"$PROJ/data/ministere.duckdb"
  PLIST_APP="$HOME/Library/LaunchAgents/$LABEL_APP.plist"
  PLIST_SAUV="$HOME/Library/LaunchAgents/$LABEL_SAUV.plist"
  CONF="$HOME/.config/ministere-info/native.conf"
  unset FAKE_OS FAKE_ARCH FAKE_ARM64_HW FAKE_HEALTH FAKE_SPATIAL_FAIL FAKE_UV_SYNC_FAIL FAKE_BOOTSTRAP_FAIL
  unset MINISTERE_DB_PATH MINISTERE_PORT MINISTERE_PROJECT_DIR BACKUP_DEST BACKUP_RETENTION_DAYS MINISTERE_NATIVE_CONF
  export PATH="$BASE_PATH"
}

# lancer <script> [args...] : exécute, garde sortie et code
lancer() {
  local script="$1"
  shift
  OUT="$S/sortie.txt"
  "$NATIVE/$script" "$@" >"$OUT" 2>&1
  RC=$?
}

plist_valeur() {
  # plist_valeur <fichier> <expression python sur d> : affiche la valeur
  python3 -c "import plistlib,sys; d=plistlib.load(open(sys.argv[1],'rb')); print($2)" "$1"
}
plist_valide() { python3 -c "import plistlib,sys; plistlib.load(open(sys.argv[1],'rb'))" "$1" 2>/dev/null; }
agent_charge() { [ -f "$STATE/agents/$1" ]; }
rc_egal() { [ "$RC" -eq "$1" ]; }
rc_non_nul() { [ "$RC" -ne 0 ]; }
egal() { [ "$1" = "$2" ]; }

# ─────────────────────────────────────────────────────────────────────────
echo "== N1 installation nominale"
nouvel_env n1
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code 0" rc_egal 0
check "plist application créé" test -f "$PLIST_APP"
check "plist application valide" plist_valide "$PLIST_APP"
check "aucun marqueur @...@ restant (app)" not grep -q '@[A-Z_]*@' "$PLIST_APP"
check "port par défaut 8502" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['STREAMLIT_SERVER_PORT']")" "8502"
check "écoute 127.0.0.1 (argument)" egal "$(plist_valeur "$PLIST_APP" "d['ProgramArguments'][d['ProgramArguments'].index('--server.address')+1]")" "127.0.0.1"
check "écoute 127.0.0.1 (variable)" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['STREAMLIT_SERVER_ADDRESS']")" "127.0.0.1"
check "MINISTERE_DB_PATH = base du projet" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['MINISTERE_DB_PATH']")" "$PROJ/data/ministere.duckdb"
check "KeepAlive et RunAtLoad" egal "$(plist_valeur "$PLIST_APP" "(d['KeepAlive'], d['RunAtLoad'])")" "(True, True)"
check "runOnSave désactivé" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['STREAMLIT_SERVER_RUN_ON_SAVE']")" "false"
check "WorkingDirectory = projet" egal "$(plist_valeur "$PLIST_APP" "d['WorkingDirectory']")" "$PROJ"
check "Python du .venv" egal "$(plist_valeur "$PLIST_APP" "d['ProgramArguments'][0]")" "$PROJ/.venv/bin/python"
check "journaux dans ~/Library/Logs/ministere-info" egal "$(plist_valeur "$PLIST_APP" "d['StandardErrorPath']")" "$HOME/Library/Logs/ministere-info/app.err.log"
check "dossier de journaux créé" test -d "$HOME/Library/Logs/ministere-info"
check "uv sync --frozen appelé dans le projet" contient "$STATE/journal" "uv sync --frozen --group etl --inexact (dans $PROJ)"
check "extension spatial installée" contient "$STATE/journal" "INSTALL spatial"
check "agent application chargé" agent_charge "$LABEL_APP"
check "plist sauvegarde créé et valide" plist_valide "$PLIST_SAUV"
check "sauvegarde : script du projet" egal "$(plist_valeur "$PLIST_SAUV" "d['ProgramArguments'][1]")" "$PROJ/scripts/backup_db.sh"
check "sauvegarde : MINISTERE_DB_PATH" egal "$(plist_valeur "$PLIST_SAUV" "d['EnvironmentVariables']['MINISTERE_DB_PATH']")" "$PROJ/data/ministere.duckdb"
check "sauvegarde : destination par défaut" egal "$(plist_valeur "$PLIST_SAUV" "d['EnvironmentVariables']['BACKUP_DEST']")" "$PROJ/data/backups"
check "sauvegarde : 3 h, pas au chargement" egal "$(plist_valeur "$PLIST_SAUV" "(d['StartCalendarInterval']['Hour'], d['RunAtLoad'])")" "(3, False)"
check "agent sauvegarde chargé" agent_charge "$LABEL_SAUV"
check "configuration écrite" contient "$CONF" "PORT=8502"
check "navigateur non ouvert (--sans-navigateur)" not contient "$STATE/journal" "open http"
check "Docker non touché" not grep -q "com.ministere-info\$\|docker" "$STATE/journal"
cp "$PLIST_APP" "$S/plist1"
cp "$CONF" "$S/conf1"

echo "== N2 idempotence (relance sans option)"
: >"$STATE/journal"
lancer install-native.sh --sans-navigateur
check "code 0" rc_egal 0
check "plist identique" cmp -s "$PLIST_APP" "$S/plist1"
check "configuration identique" cmp -s "$CONF" "$S/conf1"
check "ancien agent déchargé avant rechargement" contient "$STATE/journal" "launchctl bootout gui/$(id -u)/$LABEL_APP"
check "agent chargé" agent_charge "$LABEL_APP"

echo "== N3 port mémorisé"
lancer install-native.sh --port 8501 --sans-navigateur
check "code 0 (port 8501)" rc_egal 0
lancer install-native.sh --sans-navigateur
check "port 8501 conservé à la relance" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['STREAMLIT_SERVER_PORT']")" "8501"
check "configuration PORT=8501" contient "$CONF" "PORT=8501"

echo "== N4 destination de sauvegarde et rétention"
DEST_ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/ministere-info-sauvegardes"
lancer install-native.sh --sauvegarde-vers "$DEST_ICLOUD" --retention 14 --sans-navigateur
check "code 0" rc_egal 0
check "destination avec espaces et ~" egal "$(plist_valeur "$PLIST_SAUV" "d['EnvironmentVariables']['BACKUP_DEST']")" "$DEST_ICLOUD"
check "rétention 14" egal "$(plist_valeur "$PLIST_SAUV" "d['EnvironmentVariables']['BACKUP_RETENTION_DAYS']")" "14"
check "dossier destination créé" test -d "$DEST_ICLOUD"

echo "== N5 projet dont le chemin contient un espace + base ailleurs"
nouvel_env n5 "$WORK/n5/Mes Projets/ministere"
AUTRE_BASE="$S/Autre Dossier/base.duckdb"
mkdir -p "$(dirname "$AUTRE_BASE")"
echo x >"$AUTRE_BASE"
lancer install-native.sh --projet "$PROJ" --base "$AUTRE_BASE" --sans-navigateur
check "code 0" rc_egal 0
check "WorkingDirectory avec espace" egal "$(plist_valeur "$PLIST_APP" "d['WorkingDirectory']")" "$PROJ"
check "base personnalisée" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['MINISTERE_DB_PATH']")" "$AUTRE_BASE"

echo "== N6 refus hors macOS"
nouvel_env n6
export FAKE_OS=Linux
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code non nul" rc_non_nul
check "message macOS" contient "$OUT" "prévu pour macOS"
check "aucun plist" not test -e "$PLIST_APP"

echo "== N7 refus Intel / Rosetta"
nouvel_env n7
export FAKE_ARCH=x86_64
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "Intel : code non nul" rc_non_nul
check "Intel : message arm64" contient "$OUT" "Apple Silicon (arm64) requis"
export FAKE_ARM64_HW=1
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "Rosetta : message explicite" contient "$OUT" "Rosetta"
check "aucun plist" not test -e "$PLIST_APP"

echo "== N8 uv absent"
nouvel_env n8
export PATH="$BIN_SANS_UV:/usr/local/bin:/usr/bin:/bin"
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code non nul" rc_non_nul
check "commande d'installation figée affichée" contient "$OUT" "https://astral.sh/uv/0.11.16/install.sh"
check "aucun plist" not test -e "$PLIST_APP"

echo "== N9 base absente"
nouvel_env n9
rm -f "$PROJ/data/ministere.duckdb"
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code non nul" rc_non_nul
check "message base introuvable" contient "$OUT" "Base introuvable"
check "uv sync non lancé" not contient "$STATE/journal" "uv sync"

echo "== N10 dossier qui n'est pas le projet"
nouvel_env n10
rm -f "$PROJ/uv.lock"
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code non nul" rc_non_nul
check "message uv.lock absent" contient "$OUT" "uv.lock absent"

echo "== N11 port invalide / occupé"
nouvel_env n11
lancer install-native.sh --projet "$PROJ" --port abc --sans-navigateur
check "port non numérique refusé" contient "$OUT" "Port invalide"
lancer install-native.sh --projet "$PROJ" --port 80 --sans-navigateur
check "port < 1024 refusé" contient "$OUT" "hors plage"
touch "$STATE/port_occupe"
lancer install-native.sh --projet "$PROJ" --port 8501 --sans-navigateur
check "port occupé : code non nul" rc_non_nul
check "port occupé : occupant affiché" contient "$OUT" "com.docke (PID 999)"
check "port occupé : agent non chargé" not agent_charge "$LABEL_APP"

echo "== N12 échec uv sync / spatial / santé"
nouvel_env n12
export FAKE_UV_SYNC_FAIL=1
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "uv sync en échec : code non nul" rc_non_nul
check "uv sync en échec : pas de plist" not test -e "$PLIST_APP"
unset FAKE_UV_SYNC_FAIL
export FAKE_SPATIAL_FAIL=1
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "spatial en échec : code non nul" rc_non_nul
check "spatial en échec : message" contient "$OUT" "extension spatial"
unset FAKE_SPATIAL_FAIL
export FAKE_HEALTH=ko
mkdir -p "$HOME/Library/Logs/ministere-info"
echo "Traceback: erreur simulée" >"$HOME/Library/Logs/ministere-info/app.err.log"
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "santé KO : code non nul" rc_non_nul
check "santé KO : extrait du journal affiché" contient "$OUT" "erreur simulée"

echo "== N13 option --sans-sauvegarde, chemin refusé, option inconnue"
nouvel_env n13
lancer install-native.sh --projet "$PROJ" --sans-sauvegarde --sans-navigateur
check "code 0" rc_egal 0
check "pas de plist sauvegarde" not test -e "$PLIST_SAUV"
lancer install-native.sh --projet "$PROJ" --sauvegarde-vers "/tmp/a&b" --sans-navigateur
check "caractère & refusé" contient "$OUT" "Chemin refusé"
lancer install-native.sh --projet "$PROJ" --sauvegarde-vers "relatif/dossier" --sans-navigateur
check "chemin relatif refusé" contient "$OUT" "absolu"
lancer install-native.sh --inconnue
check "option inconnue refusée" contient "$OUT" "Option inconnue"
lancer install-native.sh --aide
check "--aide : code 0" rc_egal 0
check "--aide : décrit --port" contient "$OUT" "--port N"

echo "== N14 navigateur ouvert par défaut"
nouvel_env n14
lancer install-native.sh --projet "$PROJ"
check "open http://localhost:8502" contient "$STATE/journal" "open http://localhost:8502"

echo "== N15 status / stop / start"
lancer status.sh
check "status : code 0 si l'app répond" rc_egal 0
check "status : santé OK" contient "$OUT" "Santé        : OK"
check "status : PID affiché" contient "$OUT" "PID 4242"
check "status : base affichée" contient "$OUT" "$PROJ/data/ministere.duckdb"
lancer stop.sh
check "stop : code 0" rc_egal 0
check "stop : agent déchargé" not agent_charge "$LABEL_APP"
check "stop : sauvegarde intacte" agent_charge "$LABEL_SAUV"
lancer stop.sh
check "stop répété : code 0" rc_egal 0
check "stop répété : déjà arrêtée" contient "$OUT" "déjà arrêtée"
lancer status.sh
check "status après stop : code 1" rc_egal 1
check "status après stop : arrêté" contient "$OUT" "arrêté"
lancer start.sh
check "start : code 0" rc_egal 0
check "start : agent chargé" agent_charge "$LABEL_APP"
: >"$STATE/journal"
lancer start.sh
check "start sur app active : redémarrage (kickstart -k)" contient "$STATE/journal" "kickstart -k gui/$(id -u)/$LABEL_APP"
check "start sur app active : code 0" rc_egal 0

echo "== N16 start : journal trop gros archivé"
lancer stop.sh
head -c 11000000 /dev/zero >"$HOME/Library/Logs/ministere-info/app.err.log"
lancer start.sh
check "app.err.log archivé en .1" test -f "$HOME/Library/Logs/ministere-info/app.err.log.1"

echo "== N17 start sans installation"
nouvel_env n17
lancer start.sh
check "code non nul" rc_non_nul
check "invite à lancer install-native.sh" contient "$OUT" "install-native.sh"

echo "== N18 uninstall"
nouvel_env n18
lancer install-native.sh --projet "$PROJ" --sans-navigateur
lancer uninstall-native.sh
check "code 0" rc_egal 0
check "plist application supprimé" not test -e "$PLIST_APP"
check "agent application déchargé" not agent_charge "$LABEL_APP"
check "sauvegarde conservée par défaut" agent_charge "$LABEL_SAUV"
check "base intacte" contient "$PROJ/data/ministere.duckdb" "base factice"
lancer uninstall-native.sh
check "uninstall répété : code 0" rc_egal 0
lancer uninstall-native.sh --sauvegarde-aussi
check "--sauvegarde-aussi : plist sauvegarde supprimé" not test -e "$PLIST_SAUV"
check "--sauvegarde-aussi : agent sauvegarde déchargé" not agent_charge "$LABEL_SAUV"
check "--sauvegarde-aussi : conf supprimée" not test -e "$CONF"
check "base toujours intacte" contient "$PROJ/data/ministere.duckdb" "base factice"

echo "== N19 variable d'environnement MINISTERE_DB_PATH prise en compte"
nouvel_env n19
ENV_BASE="$S/base-env.duckdb"
echo x >"$ENV_BASE"
export MINISTERE_DB_PATH="$ENV_BASE"
lancer install-native.sh --projet "$PROJ" --sans-navigateur
check "code 0" rc_egal 0
check "base issue de l'environnement" egal "$(plist_valeur "$PLIST_APP" "d['EnvironmentVariables']['MINISTERE_DB_PATH']")" "$ENV_BASE"
unset MINISTERE_DB_PATH

echo ""
echo "Résultat : $PASS réussis, $FAIL échoués"
[ "$FAIL" -eq 0 ]
