#!/usr/bin/env bash
#
# Désinstalle le démarrage automatique de l'application native.
#
# Ne supprime JAMAIS : la base, les sauvegardes, l'environnement .venv, le
# code, les journaux, ni l'installation Docker.
#
# Par défaut, la sauvegarde quotidienne reste active (elle protège la base,
# quel que soit le mode d'exécution). Pour la retirer aussi :
#   ./deploy/native/uninstall-native.sh --sauvegarde-aussi
#
# Usage : ./deploy/native/uninstall-native.sh [--sauvegarde-aussi]

set -euo pipefail

# shellcheck source=deploy/native/commun.sh
source "$(cd "$(dirname "$0")" && pwd)/commun.sh"

AUSSI_SAUVEGARDE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --sauvegarde-aussi)
      AUSSI_SAUVEGARDE=1
      shift
      ;;
    --aide | -h | --help)
      sed -n '2,/^$/p' "$0" | sed -e 's/^# \{0,1\}//'
      exit 0
      ;;
    *) fatal "Option inconnue : $1" ;;
  esac
done

info "Arrêt et retrait de l'application native..."
decharger_agent "$LABEL_APP"
rm -f "$PLIST_APP"
ok "Application native désinstallée (plus de démarrage automatique)."

if [ "$AUSSI_SAUVEGARDE" -eq 1 ]; then
  decharger_agent "$LABEL_SAUVEGARDE"
  rm -f "$PLIST_SAUVEGARDE"
  rm -f "$FICHIER_CONF"
  ok "Sauvegarde quotidienne retirée, configuration supprimée."
else
  if [ -f "$PLIST_SAUVEGARDE" ]; then
    info "Sauvegarde quotidienne conservée (retrait : --sauvegarde-aussi)."
  fi
fi

echo ""
echo "Conservés : base de données, sauvegardes, .venv, journaux (${DOSSIER_LOGS})."
echo "Réinstaller : ./deploy/native/install-native.sh"
