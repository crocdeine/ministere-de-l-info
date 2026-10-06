#!/usr/bin/env bash
# Hook SessionStart — prépare l'environnement Python dans les sessions Claude Code on the web.
#
# - Ne fait RIEN hors environnement distant (CLAUDE_CODE_REMOTE != "true") :
#   aucun effet sur le Mac de Mathias.
# - Idempotent : `uv sync --frozen` ne fait rien si .venv est déjà à jour.
# - Silencieux en cas de succès ; en cas d'échec, affiche la sortie d'uv sur stderr
#   mais ne bloque pas la session (exit 0).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

project_dir="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$project_dir" || exit 0

if ! command -v uv >/dev/null 2>&1; then
  echo "[session-start] uv introuvable : dépendances non installées." >&2
  exit 0
fi

log="$(mktemp)"
trap 'rm -f "$log"' EXIT

# Groupes : dev (par défaut : pytest, ruff, pre-commit) + etl (geopandas, openpyxl), comme la CI.
if ! uv sync --frozen --group etl >"$log" 2>&1; then
  echo "[session-start] échec de 'uv sync --frozen --group etl' :" >&2
  cat "$log" >&2
  exit 0
fi

exit 0
