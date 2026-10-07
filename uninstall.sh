#!/usr/bin/env bash
#
# Désinstalle « Ministère de l'Info » installé par install.sh :
#
#   curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/v1.0.0/uninstall.sh | bash
#
# Supprime le dossier d'installation (code, base, Python), l'icône et les journaux,
# après confirmation (`--oui` pour ne pas la demander). Mêmes variables de test
# que install.sh : MI_INSTALL_DIR, MI_APPS_DIR, MI_LOG_DIR.
# Laisse en place ~/.duckdb (extensions DuckDB, partagées avec d'autres outils).

set -euo pipefail

main() {
  local install_dir apps_dir log_dir app reponse=""
  install_dir="${MI_INSTALL_DIR:-${HOME}/Library/Application Support/Ministere-de-l-Info}"
  apps_dir="${MI_APPS_DIR:-${HOME}/Applications}"
  log_dir="${MI_LOG_DIR:-${HOME}/Library/Logs/Ministere-de-l-Info}"
  app="$apps_dir/Ministère de l'Info.app"

  echo "Désinstallation de « Ministère de l'Info ». Seront supprimés :"
  echo "  $install_dir"
  echo "  $app"
  echo "  $log_dir"
  if [ "${1:-}" != "--oui" ]; then
    # Lecture sur le terminal : l'entrée standard est le script lui-même avec curl | bash.
    printf 'Confirmer ? (o/N) '
    read -r reponse </dev/tty || reponse=""
    case "$reponse" in
      o | O | oui | OUI) ;;
      *)
        echo "Annulé, rien n'a été supprimé."
        exit 0
        ;;
    esac
  fi

  if [ -f "$install_dir/serveur.pid" ]; then
    kill "$(cat "$install_dir/serveur.pid")" 2>/dev/null || true
    sleep 1
  fi
  rm -rf "$install_dir" "$app" "$log_dir"
  echo "Ministère de l'Info a été désinstallé."
}

main "$@"
