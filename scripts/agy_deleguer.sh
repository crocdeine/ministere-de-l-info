#!/usr/bin/env bash
# Délègue une mission en lecture seule à Antigravity (agy).
# Usage : scripts/agy_deleguer.sh <modele> <fichier-mission.md>
# Sortie : statut, jetons, conversation_id puis réponse (bornée à 20 000 octets).
# Journal : logs/agy-delegations.csv (date;mission;modèle;jetons;statut), ignoré par git.
# Jamais --dangerously-skip-permissions ; toujours --mode plan --sandbox.
set -euo pipefail

modele="${1:?usage: agy_deleguer.sh <modele> <fichier-mission>}"
mission="${2:?usage: agy_deleguer.sh <modele> <fichier-mission>}"
[ -f "$mission" ] || { echo "mission introuvable : $mission" >&2; exit 2; }
command -v agy >/dev/null || { echo "agy introuvable" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq introuvable" >&2; exit 2; }

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine"
mkdir -p logs
sortie="$(mktemp "${TMPDIR:-/tmp}/agy-XXXXXX")"
trap 'rm -f "$sortie"' EXIT

# Délai maximal 900 s (perl : timeout absent de macOS) ; code non nul si dépassé.
code=0
perl -e 'alarm 900; exec @ARGV' agy -p "$(cat "$mission")" --model "$modele" \
  --mode plan --sandbox --output-format json --print-timeout 600s >"$sortie" || code=$?

statut="$(jq -r '.status // "ERREUR"' "$sortie" 2>/dev/null || echo ERREUR)"
jetons="$(jq -r '.usage.total_tokens // 0' "$sortie" 2>/dev/null || echo 0)"
[ "$code" -eq 0 ] || statut="${statut}(code ${code})"

journal=logs/agy-delegations.csv
[ -f "$journal" ] || echo "date;mission;modele;jetons;statut" >"$journal"
echo "$(date +%Y-%m-%dT%H:%M:%S);$(basename "$mission");${modele};${jetons};${statut}" >>"$journal"

jq -r '"status=\(.status) jetons=\(.usage.total_tokens) conversation=\(.conversation_id)\n\(.response)"' \
  "$sortie" 2>/dev/null | head -c 20000 || cat "$sortie" | head -c 2000
[ "$code" -eq 0 ] && [ "$statut" = SUCCESS ]
