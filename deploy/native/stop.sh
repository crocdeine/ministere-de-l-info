#!/usr/bin/env bash
#
# Arrête l'application native (par exemple avant de lancer un ETL, qui doit
# écrire dans la base : DuckDB n'accepte pas d'écrivain tant que l'app la lit).
#
# L'arrêt dure jusqu'à `./deploy/native/start.sh` ou jusqu'à la prochaine
# ouverture de session macOS. Pour un arrêt définitif : uninstall-native.sh.
# La sauvegarde quotidienne n'est pas concernée.
#
# Usage : ./deploy/native/stop.sh

set -euo pipefail

# shellcheck source=deploy/native/commun.sh
source "$(cd "$(dirname "$0")" && pwd)/commun.sh"

resoudre_parametres

if ! agent_charge "$LABEL_APP"; then
  ok "L'application native est déjà arrêtée."
  exit 0
fi

info "Arrêt de l'application native..."
decharger_agent "$LABEL_APP"

if agent_charge "$LABEL_APP"; then
  fatal "L'application ne s'est pas arrêtée (voir ./deploy/native/status.sh)."
fi
ok "Application arrêtée. Relancer avec : ./deploy/native/start.sh"
