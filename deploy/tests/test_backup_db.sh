#!/usr/bin/env bash
#
# Tests de scripts/backup_db.sh avec un vrai DuckDB (version de uv.lock) :
# copie cohérente sous verrou, refus pendant une écriture (ETL), sauvegarde
# pendant une lecture (application), rotation, destination indisponible,
# fichier .wal, chemins avec espace et apostrophe.
#
# Python avec duckdb : <dépôt>/.venv/bin/python s'il convient, sinon un
# environnement jetable `uvx --with duckdb==<version de uv.lock>`.
# Sans l'un ni l'autre, les tests sont ignorés (code 0, message explicite).
#
# Usage : bash deploy/tests/test_backup_db.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="${BACKUP_SCRIPT:-$ROOT/scripts/backup_db.sh}" # surcharge : contrôle de sensibilité
PASS=0
FAIL=0

WORK="$(mktemp -d)"
PIDS=""
nettoyage() {
  local p
  for p in $PIDS; do kill "$p" 2>/dev/null || true; done
  rm -rf "$WORK"
}
trap nettoyage EXIT

check() {
  local desc="$1"
  shift
  if "$@"; then
    PASS=$((PASS + 1))
    echo "  ok   - $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  ÉCHEC - $desc"
  fi
}
not() { ! "$@"; }
contient() { grep -qF -- "$2" "$1"; }
rc_egal() { [ "$RC" -eq "$1" ]; }
egal() { [ "$1" = "$2" ]; }

# ── Python avec duckdb ───────────────────────────────────────────────────
VERSION_DUCKDB="$(awk '/^name = "duckdb"$/{getline; gsub(/version = |"/, ""); print; exit}' "$ROOT/uv.lock")"
PY=""
if [ -x "$ROOT/.venv/bin/python" ] && "$ROOT/.venv/bin/python" -c "import duckdb" 2>/dev/null; then
  PY="$ROOT/.venv/bin/python"
elif command -v uvx >/dev/null 2>&1; then
  PY="$(uvx --with "duckdb==${VERSION_DUCKDB}" python -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
fi
if [ -z "$PY" ] || ! "$PY" -c "import duckdb" 2>/dev/null; then
  echo "IGNORÉ : aucun Python avec duckdb disponible (lancer « uv sync --frozen »)."
  exit 0
fi
echo "Python : $PY (duckdb $("$PY" -c 'import duckdb; print(duckdb.__version__)'))"

# ── Aides ────────────────────────────────────────────────────────────────
creer_base() {
  # creer_base <fichier> : 2 tables (1000 et 50 lignes) + 1 vue
  "$PY" - "$1" <<'PY'
import sys
import duckdb
c = duckdb.connect(sys.argv[1])
c.execute("CREATE TABLE communes AS SELECT range AS id, 'c' || range AS nom FROM range(1000)")
c.execute("CREATE TABLE scrutins AS SELECT range AS id FROM range(50)")
c.execute("CREATE VIEW v_communes AS SELECT * FROM communes WHERE id < 10")
c.close()
PY
}

compter() {
  # compter <fichier base> <table> : nombre de lignes (lecture seule)
  "$PY" -c "import duckdb,sys; print(duckdb.connect(sys.argv[1], read_only=True).execute('SELECT count(*) FROM ' + sys.argv[2]).fetchone()[0])" "$1" "$2"
}

tenir_connexion() {
  # tenir_connexion <fichier> <lecture|ecriture> : ouvre la base dans un
  # processus en arrière-plan et attend qu'elle soit ouverte.
  local drapeau="$WORK/ouvert.$RANDOM"
  local ro="False"
  [ "$2" = "lecture" ] && ro="True"
  "$PY" -c "import duckdb,sys,time; c=duckdb.connect(sys.argv[1], read_only=$ro); open(sys.argv[2],'w').close(); time.sleep(60)" "$1" "$drapeau" &
  DERNIER_PID=$!
  PIDS="$PIDS $DERNIER_PID"
  local i=0
  while [ ! -f "$drapeau" ] && [ "$i" -lt 100 ]; do
    sleep 0.1
    i=$((i + 1))
  done
}

liberer() {
  kill "$DERNIER_PID" 2>/dev/null || true
  wait "$DERNIER_PID" 2>/dev/null || true
}

nouvel_env() {
  S="$WORK/$1"
  mkdir -p "$S/projet/data" "$S/dest"
  BASE="$S/projet/data/ministere.duckdb"
  DEST="$S/dest"
  LOG="$S/backup.log"
  export MINISTERE_PROJECT_DIR="$S/projet"
  export MINISTERE_DB_PATH="$BASE"
  export BACKUP_DEST="$DEST"
  export BACKUP_LOG="$LOG"
  export MINISTERE_PYTHON="$PY"
  export MINISTERE_NATIVE_CONF="$S/inexistant.conf"
  unset BACKUP_RETENTION_DAYS REPO_DIR
}

lancer() {
  OUT="$S/sortie.txt"
  bash "$SCRIPT" >"$OUT" 2>&1
  RC=$?
}

vieillir() {
  # vieillir <fichier> <jours> : recule la date de modification (portable GNU/BSD)
  "$PY" -c "import os,sys,time; t=time.time()-int(sys.argv[2])*86400; os.utime(sys.argv[1],(t,t))" "$1" "$2"
}

nb_sauvegardes() { find "$1" -maxdepth 1 -type f -name 'ministere-*.duckdb' | wc -l | tr -d ' '; }
une_sauvegarde() { find "$1" -maxdepth 1 -type f -name 'ministere-*.duckdb' | sort | tail -n 1; }
pas_de_temporaire() { [ -z "$(find "$1" -maxdepth 1 -name '.ministere-en-cours-*' 2>/dev/null)" ]; }

# ─────────────────────────────────────────────────────────────────────────
echo "== B1 sauvegarde nominale et restauration"
nouvel_env b1
creer_base "$BASE"
lancer
check "code 0" rc_egal 0
check "une sauvegarde créée" egal "$(nb_sauvegardes "$DEST")" "1"
SAUV="$(une_sauvegarde "$DEST")"
check "nom horodaté ministere-AAAA-MM-JJ_HHMM.duckdb" egal "$(basename "$SAUV" | grep -cE '^ministere-[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}\.duckdb$')" "1"
check "pas de fichier temporaire" pas_de_temporaire "$DEST"
check "journal : OK avec 2 tables et 1 vue" contient "$LOG" "tables=2 vues=1"
RESTAUREE="$S/restauree.duckdb"
cp "$SAUV" "$RESTAUREE"
check "restauration : 1000 lignes" egal "$(compter "$RESTAUREE" communes)" "1000"
check "restauration : vue présente" egal "$(compter "$RESTAUREE" v_communes)" "10"
check "base source intacte" egal "$(compter "$BASE" communes)" "1000"
check "avertissement « même disque »" contient "$LOG" "même disque"

echo "== B2 application en cours de lecture : sauvegarde possible"
nouvel_env b2
creer_base "$BASE"
tenir_connexion "$BASE" lecture
lancer
check "code 0 pendant une lecture" rc_egal 0
check "sauvegarde créée" egal "$(nb_sauvegardes "$DEST")" "1"
liberer

echo "== B3 ETL en cours d'écriture : sauvegarde refusée proprement"
nouvel_env b3
creer_base "$BASE"
tenir_connexion "$BASE" ecriture
lancer
check "code 4" rc_egal 4
check "message « en cours d'écriture »" contient "$LOG" "en cours d'écriture"
check "aucune sauvegarde" egal "$(nb_sauvegardes "$DEST")" "0"
check "pas de fichier temporaire" pas_de_temporaire "$DEST"
liberer
lancer
check "après l'ETL : code 0" rc_egal 0

echo "== B4 rotation"
nouvel_env b4
creer_base "$BASE"
for f in ministere-2026-01-01_0300.duckdb ministere-2026-01-02_0300.duckdb; do
  echo vieux >"$DEST/$f"
  vieillir "$DEST/$f" 10
done
echo wal >"$DEST/ministere-2026-01-01_0300.duckdb.wal"
echo recent >"$DEST/ministere-2026-09-22_0300.duckdb"
vieillir "$DEST/ministere-2026-09-22_0300.duckdb" 2
echo autre >"$DEST/autre-fichier.duckdb"
vieillir "$DEST/autre-fichier.duckdb" 30
lancer
check "code 0" rc_egal 0
check "sauvegardes > 7 jours supprimées" not test -e "$DEST/ministere-2026-01-01_0300.duckdb"
check "leur .wal aussi" not test -e "$DEST/ministere-2026-01-01_0300.duckdb.wal"
check "sauvegarde récente conservée" test -e "$DEST/ministere-2026-09-22_0300.duckdb"
check "fichier étranger conservé" test -e "$DEST/autre-fichier.duckdb"
check "journal : 2 supprimées" contient "$LOG" "Rotation : 2 sauvegarde(s)"
check "2 sauvegardes restantes" egal "$(nb_sauvegardes "$DEST")" "2"
export BACKUP_RETENTION_DAYS=1
lancer
check "rétention 1 jour : la récente (2 j) supprimée" not test -e "$DEST/ministere-2026-09-22_0300.duckdb"
export BACKUP_RETENTION_DAYS=abc
lancer
check "rétention invalide : 7 utilisé" contient "$LOG" "BACKUP_RETENTION_DAYS invalide"
check "rétention invalide : code 0" rc_egal 0

echo "== B5 base absente"
nouvel_env b5
lancer
check "code 2" rc_egal 2
check "message base absente" contient "$LOG" "base absente"

echo "== B6 disque externe débranché : secours local"
nouvel_env b6
creer_base "$BASE"
export BACKUP_DEST="/Volumes/DisqueAbsentPourTest/ministere-info"
lancer
check "code 5" rc_egal 5
check "message destination indisponible" contient "$LOG" "destination indisponible"
check "sauvegarde faite dans <projet>/data/backups" egal "$(nb_sauvegardes "$S/projet/data/backups")" "1"
check "rien créé sous /Volumes" not test -e "/Volumes/DisqueAbsentPourTest"

echo "== B7 Python sans duckdb"
nouvel_env b7
creer_base "$BASE"
export MINISTERE_PYTHON="/bin/false"
lancer
check "code 3" rc_egal 3
check "message uv sync" contient "$LOG" "uv sync --frozen"

echo "== B8 base avec journal .wal non intégré"
nouvel_env b8
"$PY" - "$BASE" <<'PY'
import sys
import duckdb
c = duckdb.connect(sys.argv[1])
c.execute("CREATE TABLE t AS SELECT range AS id FROM range(10)")
c.execute("CHECKPOINT")
c.execute("PRAGMA disable_checkpoint_on_shutdown")
c.execute("INSERT INTO t SELECT range + 10 FROM range(5)")
c.close()
PY
if [ -s "${BASE}.wal" ]; then
  lancer
  check "code 0" rc_egal 0
  SAUV="$(une_sauvegarde "$DEST")"
  check ".wal copié avec la sauvegarde" test -s "${SAUV}.wal"
  RESTAUREE="$S/restauree.duckdb"
  cp "$SAUV" "$RESTAUREE"
  cp "${SAUV}.wal" "${RESTAUREE}.wal"
  check "restauration : 15 lignes (écritures du .wal incluses)" egal "$(compter "$RESTAUREE" t)" "15"
else
  echo "  (DuckDB n'a pas laissé de .wal : scénario non applicable)"
fi

echo "== B9 deux sauvegardes dans la même minute"
nouvel_env b9
creer_base "$BASE"
lancer
lancer
check "code 0" rc_egal 0
check "deux fichiers distincts" egal "$(nb_sauvegardes "$DEST")" "2"

echo "== B10 paramètres lus dans native.conf"
nouvel_env b10
creer_base "$BASE"
mkdir -p "$S/dest-conf"
{
  echo "# conf de test"
  echo "MINISTERE_DB_PATH=$BASE"
  echo "BACKUP_DEST=$S/dest-conf"
  echo "BACKUP_RETENTION_DAYS=3"
} >"$S/native.conf"
export MINISTERE_NATIVE_CONF="$S/native.conf"
unset BACKUP_DEST MINISTERE_DB_PATH
lancer
check "code 0" rc_egal 0
check "destination de la conf utilisée" egal "$(nb_sauvegardes "$S/dest-conf")" "1"

echo "== B11 chemins avec espace et apostrophe"
nouvel_env b11
BASE="$S/l'info du Mac/ministere.duckdb"
mkdir -p "$(dirname "$BASE")"
creer_base "$BASE"
export MINISTERE_DB_PATH="$BASE"
export BACKUP_DEST="$S/Mobile Documents/com~apple~CloudDocs/sauvegardes"
lancer
check "code 0" rc_egal 0
check "sauvegarde dans un dossier à espaces" egal "$(nb_sauvegardes "$BACKUP_DEST")" "1"

echo "== B12 fichier qui n'est pas une base DuckDB"
nouvel_env b12
echo "pas une base" >"$BASE"
lancer
check "code 4" rc_egal 4
check "aucune sauvegarde" egal "$(nb_sauvegardes "$DEST")" "0"
check "pas de fichier temporaire" pas_de_temporaire "$DEST"

echo ""
echo "Résultat : $PASS réussis, $FAIL échoués"
[ "$FAIL" -eq 0 ]
