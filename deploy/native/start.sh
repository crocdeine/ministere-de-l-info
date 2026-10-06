#!/usr/bin/env bash
#
# Démarre l'application native, ou la redémarre si elle tourne déjà
# (à utiliser après un `git pull` ou après un ETL).
#
# Usage : ./deploy/native/start.sh

set -euo pipefail

# shellcheck source=deploy/native/commun.sh
source "$(cd "$(dirname "$0")" && pwd)/commun.sh"

resoudre_parametres

[ -f "$PLIST_APP" ] || fatal "Application native non installée ($PLIST_APP absent). Lancer d'abord ./deploy/native/install-native.sh"

# Archive les journaux trop gros (> 10 Mo) avant le démarrage : launchd les
# garde ouverts ensuite, on ne peut pas les tourner pendant l'exécution.
archiver_journal() {
  local f="$1" taille
  [ -f "$f" ] || return 0
  taille="$(wc -c <"$f" | tr -d ' ')"
  if [ "$taille" -gt 10485760 ]; then
    mv "$f" "${f}.1"
  fi
}

if agent_charge "$LABEL_APP"; then
  info "L'application tourne déjà : redémarrage..."
  launchctl kickstart -k "$(domaine_gui)/${LABEL_APP}"
else
  info "Démarrage de l'application..."
  mkdir -p "$DOSSIER_LOGS"
  archiver_journal "${DOSSIER_LOGS}/app.out.log"
  archiver_journal "${DOSSIER_LOGS}/app.err.log"
  OCCUPANT="$(port_occupe_par "$PORT")"
  [ -z "$OCCUPANT" ] || fatal "Le port $PORT est déjà utilisé par : $OCCUPANT"
  charger_agent "$LABEL_APP" "$PLIST_APP" || fatal "launchctl bootstrap a échoué"
fi

if attendre_app "$PORT" 60; then
  ok "Application disponible : http://localhost:${PORT}"
else
  erreur "L'application ne répond pas après 60 s."
  tail -n 20 "${DOSSIER_LOGS}/app.err.log" >&2 2>/dev/null || true
  echo "      Journal complet : ${DOSSIER_LOGS}/app.err.log" >&2
  exit 1
fi
