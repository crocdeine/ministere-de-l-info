# shellcheck shell=bash
# Les variables définies ici sont utilisées par les scripts qui chargent ce fichier.
# shellcheck disable=SC2034
#
# Fonctions communes aux scripts d'exécution native (deploy/native/*.sh).
# Ce fichier est chargé par `source` ; il ne s'exécute pas seul.
# Compatible bash 3.2 (macOS) et bash 5 (Linux, tests simulés).

# ── Identifiants et emplacements ─────────────────────────────────────────
LABEL_APP="com.crocdeine.ministere-info.native"
LABEL_SAUVEGARDE="com.crocdeine.ministere-info.backup"
LABEL_DOCKER="com.ministere-info" # LaunchAgent créé par deploy/install.sh (Docker)

DOSSIER_AGENTS="${HOME}/Library/LaunchAgents"
DOSSIER_AGENTS_DESACTIVES="${DOSSIER_AGENTS}/desactives"
PLIST_APP="${DOSSIER_AGENTS}/${LABEL_APP}.plist"
PLIST_SAUVEGARDE="${DOSSIER_AGENTS}/${LABEL_SAUVEGARDE}.plist"
DOSSIER_LOGS="${HOME}/Library/Logs/ministere-info"
FICHIER_CONF="${MINISTERE_NATIVE_CONF:-${HOME}/.config/ministere-info/native.conf}"
# Script réellement lancé par le LaunchAgent de l'application (voir
# deploy/native/lancer-app.sh) : toujours sur le disque interne (~), jamais
# dans le dossier du projet, pour rester exécutable même si celui-ci est sur
# un disque externe débranché à l'ouverture de session.
LANCEUR_APP="${HOME}/.config/ministere-info/lancer-app.sh"

PORT_PAR_DEFAUT="8501" # Constat du 25/09 : aucun conteneur Docker sur le Mac, installation directe sur 8501
RETENTION_PAR_DEFAUT="7"

# Dossier du dépôt qui contient ces scripts (deploy/native/../..)
DOSSIER_DEPOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Messages ─────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  _V=$'\033[0;32m'
  _J=$'\033[1;33m'
  _R=$'\033[0;31m'
  _B=$'\033[0;34m'
  _N=$'\033[0m'
else
  _V=""
  _J=""
  _R=""
  _B=""
  _N=""
fi
info() { printf '%s[..]%s %s\n' "$_B" "$_N" "$*"; }
ok() { printf '%s[OK]%s %s\n' "$_V" "$_N" "$*"; }
attention() { printf '%s[!!]%s %s\n' "$_J" "$_N" "$*"; }
erreur() { printf '%s[ERREUR]%s %s\n' "$_R" "$_N" "$*" >&2; }
fatal() {
  erreur "$*"
  exit 1
}

# ── Configuration persistante ────────────────────────────────────────────
# Format : une ligne CLE=valeur par paramètre, sans guillemets. Le fichier
# est lu ligne à ligne (jamais exécuté par `source`).
CONF_PROJECT_DIR=""
CONF_MINISTERE_DB_PATH=""
CONF_PORT=""
CONF_BACKUP_DEST=""
CONF_BACKUP_RETENTION_DAYS=""

charger_conf() {
  [ -f "$FICHIER_CONF" ] || return 0
  local ligne cle valeur
  while IFS= read -r ligne || [ -n "$ligne" ]; do
    case "$ligne" in
      '' | '#'*) continue ;;
    esac
    cle="${ligne%%=*}"
    valeur="${ligne#*=}"
    case "$cle" in
      PROJECT_DIR) CONF_PROJECT_DIR="$valeur" ;;
      MINISTERE_DB_PATH) CONF_MINISTERE_DB_PATH="$valeur" ;;
      PORT) CONF_PORT="$valeur" ;;
      BACKUP_DEST) CONF_BACKUP_DEST="$valeur" ;;
      BACKUP_RETENTION_DAYS) CONF_BACKUP_RETENTION_DAYS="$valeur" ;;
      *) ;; # clé inconnue : ignorée
    esac
  done <"$FICHIER_CONF"
}

ecrire_conf() {
  # ecrire_conf <projet> <base> <port> <dest_sauvegarde> <retention>
  local dossier tmp
  dossier="$(dirname "$FICHIER_CONF")"
  mkdir -p "$dossier"
  tmp="${FICHIER_CONF}.tmp"
  {
    echo "# Configuration de l'exécution native de ministere-de-l-info."
    echo "# Écrit par deploy/native/install-native.sh — relancer ce script pour modifier."
    echo "PROJECT_DIR=$1"
    echo "MINISTERE_DB_PATH=$2"
    echo "PORT=$3"
    echo "BACKUP_DEST=$4"
    echo "BACKUP_RETENTION_DAYS=$5"
  } >"$tmp"
  mv "$tmp" "$FICHIER_CONF"
}

# Résout les paramètres effectifs : variable d'environnement > fichier de conf > défaut.
# (install-native.sh applique en plus ses options de ligne de commande, prioritaires.)
resoudre_parametres() {
  charger_conf
  PROJECT_DIR="${MINISTERE_PROJECT_DIR:-${CONF_PROJECT_DIR:-$DOSSIER_DEPOT}}"
  DB_PATH="${MINISTERE_DB_PATH:-${CONF_MINISTERE_DB_PATH:-${PROJECT_DIR}/data/ministere.duckdb}}"
  PORT="${MINISTERE_PORT:-${CONF_PORT:-$PORT_PAR_DEFAUT}}"
  BACKUP_DEST="${BACKUP_DEST:-${CONF_BACKUP_DEST:-${PROJECT_DIR}/data/backups}}"
  BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-${CONF_BACKUP_RETENTION_DAYS:-$RETENTION_PAR_DEFAUT}}"
}

# ── launchd ──────────────────────────────────────────────────────────────
domaine_gui() { echo "gui/$(id -u)"; }

agent_charge() {
  # agent_charge <label> : vrai si le LaunchAgent est chargé dans la session
  launchctl print "$(domaine_gui)/$1" >/dev/null 2>&1
}

pid_agent() {
  # Affiche le PID du processus de l'agent (vide si arrêté)
  launchctl print "$(domaine_gui)/$1" 2>/dev/null |
    awk -F'= ' '/^[[:space:]]*pid = /{print $2; exit}'
}

decharger_agent() {
  # decharger_agent <label> : arrête et décharge l'agent s'il est chargé (idempotent)
  if agent_charge "$1"; then
    launchctl bootout "$(domaine_gui)/$1" 2>/dev/null || true
    local i=0
    while agent_charge "$1" && [ "$i" -lt 10 ]; do
      sleep 1
      i=$((i + 1))
    done
  fi
}

charger_agent() {
  # charger_agent <label> <plist> : charge l'agent (RunAtLoad le démarre)
  launchctl enable "$(domaine_gui)/$1" 2>/dev/null || true
  launchctl bootstrap "$(domaine_gui)" "$2"
}

retirer_ancienne_sauvegarde() {
  # retirer_ancienne_sauvegarde <plist> : si un LaunchAgent de sauvegarde
  # existe déjà (même label, historiquement `com.crocdeine.ministere-info.backup`)
  # et référence un script `backup_db.sh` qui n'existe plus (projet déplacé,
  # par exemple vers un disque externe), le décharge et range le plist dans
  # desactives/ au lieu de l'écraser silencieusement — trace conservée pour
  # diagnostic. Idempotent : ne fait rien si le script référencé existe
  # toujours (y compris après un premier passage, qui aura remplacé le plist).
  local plist="$1" script_ancien
  [ -f "$plist" ] || return 0
  script_ancien="$(awk '
    /<key>ProgramArguments<\/key>/ { dans = 1; next }
    dans && /backup_db\.sh<\/string>/ {
      gsub(/.*<string>|<\/string>.*/, "")
      print
      exit
    }
  ' "$plist" 2>/dev/null || true)"
  [ -n "$script_ancien" ] || return 0
  [ -f "$script_ancien" ] && return 0
  attention "Ancien agent de sauvegarde détecté (script disparu : $script_ancien) — désactivé"
  decharger_agent "$LABEL_SAUVEGARDE"
  mkdir -p "$DOSSIER_AGENTS_DESACTIVES"
  mv "$plist" "${DOSSIER_AGENTS_DESACTIVES}/$(basename "$plist").$(date +%Y%m%d%H%M%S)"
}

# ── Santé de l'application ───────────────────────────────────────────────
app_repond() {
  # app_repond <port> : vrai si /_stcore/health répond « ok »
  local reponse
  reponse="$(curl -fsS --max-time 3 "http://127.0.0.1:$1/_stcore/health" 2>/dev/null || true)"
  [ "$reponse" = "ok" ]
}

attendre_app() {
  # attendre_app <port> <secondes>
  local port="$1" max="$2" ecoule=0
  while [ "$ecoule" -lt "$max" ]; do
    if app_repond "$port"; then
      return 0
    fi
    sleep 2
    ecoule=$((ecoule + 2))
  done
  return 1
}

port_occupe_par() {
  # Affiche le processus qui écoute sur le port (vide si libre)
  # lsof renvoie 1 quand le port est libre : neutralisé (pipefail)
  { lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true; } | awk 'NR==2{print $1" (PID "$2")"}'
}

# ── Divers ───────────────────────────────────────────────────────────────
taille_lisible() {
  # taille_lisible <fichier>
  du -h "$1" 2>/dev/null | awk '{print $1}'
}

date_fichier() {
  # date de dernière modification, format AAAA-MM-JJ HH:MM (BSD puis GNU)
  local sortie
  if sortie="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$1" 2>/dev/null)"; then
    echo "$sortie"
  elif sortie="$(date -r "$1" '+%Y-%m-%d %H:%M' 2>/dev/null)"; then
    echo "$sortie"
  else
    echo "?"
  fi
}

valider_chemin() {
  # Refuse les caractères qui casseraient le plist XML ou la substitution sed.
  case "$1" in
    *'&'* | *'<'* | *'>'* | *'|'* | *'"'* | *\\*)
      fatal "Chemin refusé (caractère & < > | \" ou \\ interdit) : $1"
      ;;
  esac
  case "$1" in
    /*) ;;
    *) fatal "Le chemin doit être absolu (commencer par /) : $1" ;;
  esac
}

# Les variables R_* sont définies par l'appelant (install-native.sh).
# shellcheck disable=SC2153
rendre_modele() {
  # rendre_modele <modèle> <destination> : remplace les marqueurs @CLE@ par
  # les valeurs des variables R_* (définies par l'appelant), écrit atomiquement.
  local modele="$1" dest="$2" tmp
  tmp="${dest}.tmp"
  sed \
    -e "s|@LABEL@|${R_LABEL}|g" \
    -e "s|@PROJECT_DIR@|${R_PROJECT_DIR}|g" \
    -e "s|@PYTHON@|${R_PYTHON}|g" \
    -e "s|@DB_PATH@|${R_DB_PATH}|g" \
    -e "s|@PORT@|${R_PORT}|g" \
    -e "s|@LOG_DIR@|${R_LOG_DIR}|g" \
    -e "s|@PATH@|${R_PATH}|g" \
    -e "s|@BACKUP_DEST@|${R_BACKUP_DEST}|g" \
    -e "s|@RETENTION@|${R_RETENTION}|g" \
    -e "s|@LANCEUR@|${R_LANCEUR:-}|g" \
    "$modele" >"$tmp"
  if grep -q '@[A-Z_]*@' "$tmp"; then
    rm -f "$tmp"
    fatal "Marqueur non remplacé dans $modele (bug du script)"
  fi
  if command -v plutil >/dev/null 2>&1; then
    plutil -lint "$tmp" >/dev/null || {
      rm -f "$tmp"
      fatal "plist invalide généré depuis $modele"
    }
  fi
  mv "$tmp" "$dest"
}

# Les variables R_* sont définies par l'appelant (install-native.sh).
# shellcheck disable=SC2153
rendre_script() {
  # rendre_script <modèle> <destination> : comme rendre_modele, pour un script
  # shell (pas de vérification plutil ; rend le résultat exécutable).
  local modele="$1" dest="$2" tmp
  tmp="${dest}.tmp"
  sed \
    -e "s|@PROJECT_DIR@|${R_PROJECT_DIR}|g" \
    -e "s|@PYTHON@|${R_PYTHON}|g" \
    -e "s|@PORT@|${R_PORT}|g" \
    "$modele" >"$tmp"
  if grep -q '@[A-Z_]*@' "$tmp"; then
    rm -f "$tmp"
    fatal "Marqueur non remplacé dans $modele (bug du script)"
  fi
  chmod +x "$tmp"
  mv "$tmp" "$dest"
}
