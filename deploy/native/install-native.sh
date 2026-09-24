#!/usr/bin/env bash
#
# Installe (ou réinstalle) l'exécution native de ministere-de-l-info sur macOS
# Apple Silicon : environnement uv, extension DuckDB spatial, LaunchAgent de
# l'application et LaunchAgent de sauvegarde quotidienne.
#
# Idempotent : peut être relancé autant de fois que nécessaire (après un
# `git pull`, pour changer de port, de base ou de destination de sauvegarde).
# Ne touche ni à Docker, ni à la base, ni aux sauvegardes existantes.
#
# Usage :
#   ./deploy/native/install-native.sh [options]
#
# Options :
#   --projet DOSSIER          dossier du projet (défaut : le dépôt qui contient ce script)
#   --base FICHIER            base DuckDB lue par l'app (défaut : <projet>/data/ministere.duckdb)
#   --port N                  port local (défaut : valeur enregistrée, sinon 8502)
#   --sauvegarde-vers DOSSIER destination des sauvegardes (défaut : <projet>/data/backups)
#   --retention JOURS         durée de conservation des sauvegardes (défaut : 7)
#   --sans-sauvegarde         ne pas installer la sauvegarde quotidienne
#   --sans-navigateur         ne pas ouvrir le navigateur à la fin
#   --aide                    affiche cette aide
#
# Les valeurs retenues sont enregistrées dans ~/.config/ministere-info/native.conf
# et réutilisées aux lancements suivants.

set -euo pipefail

# shellcheck source=deploy/native/commun.sh
source "$(cd "$(dirname "$0")" && pwd)/commun.sh"

VERSION_UV_RECOMMANDEE="0.11.16"

afficher_aide() {
  sed -n '2,/^$/p' "$0" | sed -e 's/^# \{0,1\}//'
}

# ── Options ──────────────────────────────────────────────────────────────
OPT_PROJET=""
OPT_BASE=""
OPT_PORT=""
OPT_DEST=""
OPT_RETENTION=""
AVEC_SAUVEGARDE=1
OUVRIR_NAVIGATEUR=1

valeur_option() {
  # valeur_option <option> <nombre d'arguments restants>
  [ "$2" -ge 2 ] || fatal "L'option $1 attend une valeur (voir --aide)"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --projet)
      valeur_option "$1" "$#"
      OPT_PROJET="$2"
      shift 2
      ;;
    --base)
      valeur_option "$1" "$#"
      OPT_BASE="$2"
      shift 2
      ;;
    --port)
      valeur_option "$1" "$#"
      OPT_PORT="$2"
      shift 2
      ;;
    --sauvegarde-vers)
      valeur_option "$1" "$#"
      OPT_DEST="$2"
      shift 2
      ;;
    --retention)
      valeur_option "$1" "$#"
      OPT_RETENTION="$2"
      shift 2
      ;;
    --sans-sauvegarde)
      AVEC_SAUVEGARDE=0
      shift
      ;;
    --sans-navigateur)
      OUVRIR_NAVIGATEUR=0
      shift
      ;;
    --aide | -h | --help)
      afficher_aide
      exit 0
      ;;
    *) fatal "Option inconnue : $1 (voir --aide)" ;;
  esac
done

echo ""
echo "=== ministere-de-l-info — installation native ==="
echo ""

# ── 1. macOS Apple Silicon ───────────────────────────────────────────────
info "1/9 Vérification du système..."
[ "$(uname -s)" = "Darwin" ] || fatal "Ce script est prévu pour macOS (système détecté : $(uname -s))."
ARCH="$(uname -m)"
if [ "$ARCH" != "arm64" ]; then
  if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
    fatal "Le Terminal tourne en mode Rosetta (x86_64). Ouvrir un Terminal natif (sans « Ouvrir avec Rosetta ») et relancer."
  fi
  fatal "Mac Apple Silicon (arm64) requis ; architecture détectée : ${ARCH}."
fi
ok "macOS arm64"

# ── 2. Paramètres ────────────────────────────────────────────────────────
info "2/9 Paramètres..."
# Priorité : option > variable d'environnement > native.conf > défaut
if [ -n "$OPT_PROJET" ]; then
  [ -d "$OPT_PROJET" ] || fatal "Dossier du projet introuvable : $OPT_PROJET"
  MINISTERE_PROJECT_DIR="$(cd "$OPT_PROJET" && pwd)"
fi
[ -z "$OPT_BASE" ] || MINISTERE_DB_PATH="$OPT_BASE"
[ -z "$OPT_PORT" ] || MINISTERE_PORT="$OPT_PORT"
[ -z "$OPT_DEST" ] || BACKUP_DEST="$OPT_DEST"
[ -z "$OPT_RETENTION" ] || BACKUP_RETENTION_DAYS="$OPT_RETENTION"
resoudre_parametres
[ -d "$PROJECT_DIR" ] || fatal "Dossier du projet introuvable : $PROJECT_DIR"

for f in app.py pyproject.toml uv.lock; do
  [ -f "${PROJECT_DIR}/$f" ] || fatal "$f absent de $PROJECT_DIR : ce n'est pas le dossier du projet."
done
valider_chemin "$PROJECT_DIR"
valider_chemin "$DB_PATH"
valider_chemin "$BACKUP_DEST"
valider_chemin "$DOSSIER_LOGS"

case "$PORT" in
  '' | *[!0-9]*) fatal "Port invalide : '$PORT' (nombre attendu, ex. 8502)" ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  fatal "Port hors plage 1024-65535 : $PORT"
fi
case "$BACKUP_RETENTION_DAYS" in
  '' | *[!0-9]* | 0) fatal "Rétention invalide : '$BACKUP_RETENTION_DAYS' (nombre de jours ≥ 1)" ;;
esac

echo "      Projet     : $PROJECT_DIR"
echo "      Base       : $DB_PATH"
echo "      Adresse    : http://localhost:${PORT} (écoute 127.0.0.1 uniquement)"
if [ "$AVEC_SAUVEGARDE" -eq 1 ]; then
  echo "      Sauvegarde : $BACKUP_DEST (${BACKUP_RETENTION_DAYS} jours, chaque jour à 3 h)"
else
  echo "      Sauvegarde : non installée (--sans-sauvegarde)"
fi

# ── 3. Base de données ───────────────────────────────────────────────────
info "3/9 Base de données..."
if [ ! -s "$DB_PATH" ]; then
  erreur "Base introuvable ou vide : $DB_PATH"
  echo "      Voir docs/deployment.md, « Bascule », étape 2 (obtenir la base)." >&2
  exit 1
fi
ok "Base présente ($(taille_lisible "$DB_PATH"), modifiée le $(date_fichier "$DB_PATH"))"

# ── 4. uv ────────────────────────────────────────────────────────────────
info "4/9 Recherche de uv..."
UV_BIN="$(command -v uv 2>/dev/null || true)"
if [ -z "$UV_BIN" ]; then
  for candidat in "${HOME}/.local/bin/uv" "/opt/homebrew/bin/uv" "${HOME}/.cargo/bin/uv"; do
    if [ -x "$candidat" ]; then
      UV_BIN="$candidat"
      break
    fi
  done
fi
if [ -z "$UV_BIN" ]; then
  erreur "uv n'est pas installé."
  echo "" >&2
  echo "      Installer uv (version figée du projet) avec cette commande, puis" >&2
  echo "      fermer et rouvrir le Terminal et relancer ce script :" >&2
  echo "" >&2
  echo "      curl -LsSf https://astral.sh/uv/${VERSION_UV_RECOMMANDEE}/install.sh | sh" >&2
  echo "" >&2
  exit 1
fi
VERSION_UV="$("$UV_BIN" --version 2>/dev/null | awk '{print $2}')"
ok "uv ${VERSION_UV:-?} ($UV_BIN)"
if [ -n "$VERSION_UV" ] && [ "$VERSION_UV" != "$VERSION_UV_RECOMMANDEE" ]; then
  attention "Version recommandée : ${VERSION_UV_RECOMMANDEE} (sans gravité si l'installation aboutit)."
fi

# ── 5. Environnement Python ──────────────────────────────────────────────
info "5/9 Installation des dépendances (uv sync --frozen)..."
# --group etl : même environnement que la CI, l'ETL reste utilisable.
# --inexact  : ne retire aucun paquet déjà installé (ex. groupe « ai ») ;
#              le dossier .venv est partagé avec le développement.
(cd "$PROJECT_DIR" && "$UV_BIN" sync --frozen --group etl --inexact) ||
  fatal "uv sync a échoué (voir les messages ci-dessus ; connexion Internet requise la première fois)."
PYTHON_VENV="${PROJECT_DIR}/.venv/bin/python"
[ -x "$PYTHON_VENV" ] || fatal "Python de l'environnement introuvable : $PYTHON_VENV"
ok "Environnement prêt (${PROJECT_DIR}/.venv)"

# ── 6. Extension DuckDB spatial ──────────────────────────────────────────
info "6/9 Extension DuckDB spatial..."
# INSTALL ne télécharge que si l'extension manque pour cette version de DuckDB
# (dossier ~/.duckdb/extensions/<version>/osx_arm64/).
if ! "$PYTHON_VENV" -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL spatial'); c.execute('LOAD spatial'); print(duckdb.__version__)" >/dev/null; then
  fatal "Impossible d'installer l'extension spatial (connexion Internet requise la première fois)."
fi
ok "Extension spatial disponible"

# ── 7. Configuration et journaux ─────────────────────────────────────────
info "7/9 Enregistrement de la configuration..."
mkdir -p "$DOSSIER_LOGS" "$DOSSIER_AGENTS"
ecrire_conf "$PROJECT_DIR" "$DB_PATH" "$PORT" "$BACKUP_DEST" "$BACKUP_RETENTION_DAYS"
ok "Configuration : $FICHIER_CONF"

# ── 8. LaunchAgents ──────────────────────────────────────────────────────
info "8/9 Démarrage automatique (LaunchAgent)..."
decharger_agent "$LABEL_APP"

OCCUPANT="$(port_occupe_par "$PORT")"
if [ -n "$OCCUPANT" ]; then
  erreur "Le port $PORT est déjà utilisé par : $OCCUPANT"
  echo "      Choisir un autre port (--port 8502) ou arrêter ce programme." >&2
  echo "      Si c'est Docker : voir docs/deployment.md, étape 8 de la bascule." >&2
  exit 1
fi

R_LABEL="$LABEL_APP"
R_PROJECT_DIR="$PROJECT_DIR"
R_PYTHON="$PYTHON_VENV"
R_DB_PATH="$DB_PATH"
R_PORT="$PORT"
R_LOG_DIR="$DOSSIER_LOGS"
R_PATH="${PROJECT_DIR}/.venv/bin:$(dirname "$UV_BIN"):/usr/bin:/bin:/usr/sbin:/sbin"
R_BACKUP_DEST="$BACKUP_DEST"
R_RETENTION="$BACKUP_RETENTION_DAYS"

rendre_modele "${DOSSIER_DEPOT}/deploy/native/ministere-info.plist" "$PLIST_APP"
charger_agent "$LABEL_APP" "$PLIST_APP" || fatal "launchctl bootstrap a échoué pour $PLIST_APP"
ok "Application : $PLIST_APP"

if [ "$AVEC_SAUVEGARDE" -eq 1 ]; then
  if [ ! -d "$BACKUP_DEST" ]; then
    case "$BACKUP_DEST" in
      /Volumes/*) attention "Destination non accessible pour l'instant : $BACKUP_DEST (disque débranché ?)" ;;
      *) mkdir -p "$BACKUP_DEST" ;;
    esac
  fi
  decharger_agent "$LABEL_SAUVEGARDE"
  R_LABEL="$LABEL_SAUVEGARDE"
  rendre_modele "${DOSSIER_DEPOT}/scripts/com.crocdeine.ministere-info.backup.plist" "$PLIST_SAUVEGARDE"
  charger_agent "$LABEL_SAUVEGARDE" "$PLIST_SAUVEGARDE" ||
    fatal "launchctl bootstrap a échoué pour $PLIST_SAUVEGARDE"
  ok "Sauvegarde quotidienne : $PLIST_SAUVEGARDE"
fi

# ── 9. Vérification ──────────────────────────────────────────────────────
info "9/9 Attente du démarrage de l'application (jusqu'à 90 s)..."
if ! attendre_app "$PORT" 90; then
  erreur "L'application ne répond pas sur http://localhost:${PORT}/_stcore/health"
  echo "      Dernières lignes du journal d'erreurs :" >&2
  tail -n 20 "${DOSSIER_LOGS}/app.err.log" >&2 2>/dev/null || true
  echo "      Journal complet : ${DOSSIER_LOGS}/app.err.log" >&2
  exit 1
fi
ok "L'application répond (santé : ok)"

echo ""
echo "=== Installation native terminée ==="
echo ""
echo "  Adresse     : http://localhost:${PORT}"
echo "  État        : ./deploy/native/status.sh"
echo "  Arrêter     : ./deploy/native/stop.sh"
echo "  (Re)démarrer: ./deploy/native/start.sh"
echo "  Journaux    : ${DOSSIER_LOGS}/"
echo ""

if [ "$OUVRIR_NAVIGATEUR" -eq 1 ] && command -v open >/dev/null 2>&1; then
  open "http://localhost:${PORT}" || true
fi
