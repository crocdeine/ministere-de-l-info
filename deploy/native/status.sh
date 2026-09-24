#!/usr/bin/env bash
#
# Affiche l'état de l'exécution native : application, base, sauvegardes,
# et, pour information, l'ancien démarrage Docker.
#
# Code de sortie : 0 si l'application répond, 1 sinon.
#
# Usage : ./deploy/native/status.sh

set -euo pipefail

# shellcheck source=deploy/native/commun.sh
source "$(cd "$(dirname "$0")" && pwd)/commun.sh"

resoudre_parametres

echo ""
echo "=== ministere-de-l-info — état de l'exécution native ==="
echo ""

# ── Application ──────────────────────────────────────────────────────────
echo "Application"
if [ ! -f "$PLIST_APP" ]; then
  echo "  Installation : non installée (lancer ./deploy/native/install-native.sh)"
elif agent_charge "$LABEL_APP"; then
  PID="$(pid_agent "$LABEL_APP")"
  echo "  Démarrage    : actif (PID ${PID:-aucun, relance en cours})"
else
  echo "  Démarrage    : arrêté (relancer avec ./deploy/native/start.sh)"
fi
echo "  Adresse      : http://localhost:${PORT}"
if app_repond "$PORT"; then
  SANTE=0
  echo "  Santé        : OK (répond)"
else
  SANTE=1
  echo "  Santé        : NE RÉPOND PAS"
fi
echo "  Journaux     : ${DOSSIER_LOGS}/app.err.log"

# ── Base ─────────────────────────────────────────────────────────────────
echo ""
echo "Base de données"
echo "  Fichier      : $DB_PATH"
if [ -f "$DB_PATH" ]; then
  echo "  Taille       : $(taille_lisible "$DB_PATH")"
  echo "  Modifiée le  : $(date_fichier "$DB_PATH")"
else
  echo "  ATTENTION    : fichier absent"
fi

# ── Sauvegardes ──────────────────────────────────────────────────────────
echo ""
echo "Sauvegardes"
if [ -f "$PLIST_SAUVEGARDE" ]; then
  if agent_charge "$LABEL_SAUVEGARDE"; then
    echo "  Automatique  : active (chaque jour à 3 h)"
  else
    echo "  Automatique  : installée mais non chargée"
  fi
else
  echo "  Automatique  : non installée"
fi
echo "  Destination  : $BACKUP_DEST (conservation ${BACKUP_RETENTION_DAYS} jours)"
if [ -d "$BACKUP_DEST" ]; then
  DERNIERE="$(find "$BACKUP_DEST" -maxdepth 1 -type f -name 'ministere-*.duckdb' 2>/dev/null | sort | tail -n 1)"
  NOMBRE="$(find "$BACKUP_DEST" -maxdepth 1 -type f -name 'ministere-*.duckdb' 2>/dev/null | wc -l | tr -d ' ')"
  if [ -n "$DERNIERE" ]; then
    echo "  Dernière     : $(basename "$DERNIERE") ($(taille_lisible "$DERNIERE"))"
  else
    echo "  Dernière     : aucune sauvegarde"
  fi
  echo "  Nombre       : $NOMBRE"
else
  echo "  ATTENTION    : destination inaccessible (disque débranché ?)"
fi

# ── Docker (repli) ───────────────────────────────────────────────────────
echo ""
echo "Docker (repli pendant la période de transition)"
if agent_charge "$LABEL_DOCKER"; then
  echo "  Démarrage auto Docker : encore actif ($LABEL_DOCKER)"
else
  echo "  Démarrage auto Docker : inactif"
fi
echo ""

exit "$SANTE"
