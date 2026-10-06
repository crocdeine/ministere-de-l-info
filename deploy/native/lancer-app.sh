#!/usr/bin/env bash
#
# MODÈLE exécuté par le LaunchAgent com.crocdeine.ministere-info.native
# (référencé dans ProgramArguments de ministere-info.plist).
#
# Généré par deploy/native/install-native.sh (marqueurs @...@ remplacés) et
# installé sur le DISQUE INTERNE, dans ~/.config/ministere-info/lancer-app.sh
# — jamais dans le dossier du projet. Raison : si le projet est sur un disque
# externe qui n'est pas encore monté à l'ouverture de session, ce script doit
# pouvoir démarrer quand même pour attendre le montage et journaliser un
# message clair, au lieu que launchd échoue instantanément à trouver un
# exécutable absent (ce qui provoquerait une boucle de relance rapide malgré
# ThrottleInterval).
#
# Limite connue : si le disque externe reste débranché plus de
# MINISTERE_LANCER_ATTENTE_MAX secondes, l'application reste indisponible
# jusqu'au prochain déclenchement de KeepAlive (au rythme de ThrottleInterval)
# ou jusqu'à ./deploy/native/start.sh une fois le disque rebranché.

set -euo pipefail

PROJECT_DIR="@PROJECT_DIR@"
PYTHON="@PYTHON@"
PORT="@PORT@"

# Surchargeables pour les tests (deploy/tests/test_native.sh) ; en usage réel,
# 60 s par pas de 2 s.
ATTENTE_MAX="${MINISTERE_LANCER_ATTENTE_MAX:-60}"
INTERVALLE="${MINISTERE_LANCER_INTERVALLE:-2}"

horodatage() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(horodatage)] Démarrage : vérification de la disponibilité de $PROJECT_DIR..."

ECOULE=0
while [ ! -x "$PYTHON" ] || [ ! -f "$PROJECT_DIR/app.py" ]; do
  if [ "$ECOULE" -eq 0 ]; then
    echo "[$(horodatage)] $PROJECT_DIR indisponible (disque externe pas encore monté ?) — attente jusqu'à ${ATTENTE_MAX}s."
  fi
  if [ "$ECOULE" -ge "$ATTENTE_MAX" ]; then
    echo "[$(horodatage)] ERREUR : $PROJECT_DIR toujours indisponible après ${ATTENTE_MAX}s. Abandon de cette tentative (relance au prochain cycle KeepAlive, ou rebrancher le disque puis ./deploy/native/start.sh)." >&2
    exit 1
  fi
  sleep "$INTERVALLE"
  ECOULE=$((ECOULE + INTERVALLE))
done

echo "[$(horodatage)] $PROJECT_DIR disponible — démarrage de Streamlit sur le port $PORT."

cd "$PROJECT_DIR"
exec "$PYTHON" -m streamlit run app.py \
  --server.address 127.0.0.1 \
  --server.port "$PORT"
