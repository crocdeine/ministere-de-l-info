#!/usr/bin/env bash
#
# Tests simulés (sans réseau, sans Docker) de la chaîne d'empreinte de la base :
#   scripts/publish_db.sh → release GitHub → deploy/install.sh / deploy/update.sh
#   et scripts/download_db.sh.
#
# Les commandes externes (curl, docker, open, sw_vers, brew, orbctl, lsof,
# launchctl, df, sleep) sont remplacées par des stubs placés en tête du PATH.
# Le stub curl sert des fichiers depuis un « faux web » ($FAKE_WEB/<hôte>/<chemin>)
# et journalise chaque URL demandée.
#
# Usage : bash deploy/tests/test_db_checksum.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO="crocdeine/ministere-de-l-info"
PASS=0
FAIL=0

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

sha() { sha256sum "$1" | awk '{print $1}'; }
not() { ! "$@"; }

check() {
  # check <description> <commande...>
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

# ── Stubs ────────────────────────────────────────────────────────────────
BIN="$WORK/bin"
mkdir -p "$BIN"

cat > "$BIN/curl" <<'STUB'
#!/usr/bin/env bash
out=""; url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -H) shift 2 ;;
    http://*|https://*) url="$1"; shift ;;
    *) shift ;;
  esac
done
echo "$url" >> "$FAKE_WEB/.requetes"
case "$url" in http://localhost*) exit 0 ;; esac
[[ "${FAKE_OFFLINE:-0}" == "1" ]] && exit 6
path="$FAKE_WEB/${url#https://}"
[[ -f "$path" ]] || exit 22
if [[ -n "$out" ]]; then cp "$path" "$out"; else cat "$path"; fi
STUB

cat > "$BIN/docker" <<'STUB'
#!/usr/bin/env bash
echo "docker $*" >> "$FAKE_WEB/.docker"
exit 0
STUB

for cmd in open brew orbctl launchctl sleep; do
  printf '#!/usr/bin/env bash\nexit 0\n' > "$BIN/$cmd"
done
printf '#!/usr/bin/env bash\necho 15.0\n' > "$BIN/sw_vers"
printf '#!/usr/bin/env bash\nexit 1\n' > "$BIN/lsof"
printf '#!/usr/bin/env bash\necho "Filesystem 1K-blocks Used Available"\necho "fake 999999999 1 999999999"\n' > "$BIN/df"
chmod +x "$BIN"/*
export PATH="$BIN:$PATH"

# ── Faux web ─────────────────────────────────────────────────────────────
# new_web : réinitialise le faux web et le HOME simulé
new_web() {
  export FAKE_WEB="$WORK/web.$RANDOM$RANDOM"
  export HOME="$WORK/home.$RANDOM$RANDOM"
  mkdir -p "$FAKE_WEB/raw.githubusercontent.com/$REPO/main/deploy" "$HOME"
  cp "$ROOT/deploy/docker-compose.yml" "$FAKE_WEB/raw.githubusercontent.com/$REPO/main/deploy/"
  : > "$FAKE_WEB/.requetes"
  RELEASES_JSON_ENTRIES=()
}

# add_release <tag> <fichier .gz ou ""> <contenu .sha256 ou "">
# Les releases sont ajoutées de la plus récente à la plus ancienne.
add_release() {
  local tag="$1" gz="$2" shacontent="$3"
  local dl="github.com/$REPO/releases/download/$tag"
  mkdir -p "$FAKE_WEB/$dl"
  local assets=""
  if [[ -n "$gz" ]]; then
    cp "$gz" "$FAKE_WEB/$dl/ministere.duckdb.gz"
    assets="{\"name\": \"ministere.duckdb.gz\", \"browser_download_url\": \"https://$dl/ministere.duckdb.gz\"}"
    if [[ -n "$shacontent" ]]; then
      printf '%s\n' "$shacontent" > "$FAKE_WEB/$dl/ministere.duckdb.gz.sha256"
      assets="$assets, {\"name\": \"ministere.duckdb.gz.sha256\", \"browser_download_url\": \"https://$dl/ministere.duckdb.gz.sha256\"}"
    fi
  fi
  RELEASES_JSON_ENTRIES+=("{\"tag_name\": \"$tag\", \"assets\": [$assets]}")
  write_releases_json
}

write_releases_json() {
  local api="$FAKE_WEB/api.github.com/repos/$REPO"
  mkdir -p "$api"
  local IFS=,
  # Même mise en forme que l'API GitHub (une clé par ligne, indentée)
  printf '[%s]\n' "${RELEASES_JSON_ENTRIES[*]}" | python3 -m json.tool > "$api/releases?per_page=30"
}

downloads_of() { grep -c "/ministere.duckdb.gz$" "$FAKE_WEB/.requetes" || true; }

state_val() { grep -E "^$1=" "$HOME/.ministere-info/db-release.state" | cut -d= -f2-; }

# fake_db <fichier> <graine> : base factice de ~200 Ko
fake_db() { python3 -c "import random,sys; random.seed(sys.argv[2]); open(sys.argv[1],'wb').write(random.randbytes(200000))" "$1" "$2"; }

# make_gz <db> <gz>
make_gz() { gzip -n -c "$1" > "$2"; }

run_install() { bash "$ROOT/deploy/install.sh" > "$WORK/install.log" 2>&1; }
run_update() { bash "$ROOT/deploy/update.sh" > "$WORK/update.log" 2>&1; }

DBV1="$WORK/v1.duckdb"; DBV2="$WORK/v2.duckdb"
fake_db "$DBV1" 1; fake_db "$DBV2" 2
make_gz "$DBV1" "$WORK/v1.gz"; make_gz "$DBV2" "$WORK/v2.gz"
GZ1=$(sha "$WORK/v1.gz"); DB1=$(sha "$DBV1")
GZ2=$(sha "$WORK/v2.gz"); DB2=$(sha "$DBV2")

# ── publish_db.sh ────────────────────────────────────────────────────────
echo "publish_db.sh"
PUB="$WORK/pubrepo"
mkdir -p "$PUB/scripts" "$PUB/data"
cp "$ROOT/scripts/publish_db.sh" "$PUB/scripts/"
cp "$DBV1" "$PUB/data/ministere.duckdb"
run_publish() { bash "$PUB/scripts/publish_db.sh" v0.9-test > "$WORK/publish.log" 2>&1; }
check "s'exécute sans erreur" run_publish
check ".sha256 = empreinte de l'archive, nom sans chemin" \
  test "$(cat "$PUB/data/ministere.duckdb.gz.sha256")" = "$(sha "$PUB/data/ministere.duckdb.gz")  ministere.duckdb.gz"
check "sha256sum -c valide dans le dossier de l'archive" \
  bash -c "cd '$PUB/data' && sha256sum -c --quiet ministere.duckdb.gz.sha256"
check "archive restituant la base à l'identique" \
  test "$(gunzip -c "$PUB/data/ministere.duckdb.gz" | sha256sum | awk '{print $1}')" = "$DB1"
check "archive reproductible (gzip -n)" test "$(sha "$PUB/data/ministere.duckdb.gz")" = "$GZ1"
check "commande gh affichée avec le tag" grep -q "gh release upload v0.9-test" "$WORK/publish.log"
PUB_SHA_LINE=$(cat "$PUB/data/ministere.duckdb.gz.sha256")

# ── install.sh ───────────────────────────────────────────────────────────
echo "install.sh"
new_web
add_release v1 "$PUB/data/ministere.duckdb.gz" "$PUB_SHA_LINE"
check "installation (convention archive) réussie" run_install
check "base installée identique" test "$(sha "$HOME/.ministere-info/data/ministere.duckdb")" = "$DB1"
check "état : tag" test "$(state_val DB_RELEASE_TAG)" = v1
check "état : empreinte publiée" test "$(state_val DB_REMOTE_SHA256)" = "$GZ1"
check "état : sha256 archive + base" \
  test "$(state_val DB_GZ_SHA256):$(state_val DB_SHA256)" = "$GZ1:$DB1"
check "pas de dossier temporaire résiduel" \
  test -z "$(find "$HOME/.ministere-info" -name '.telechargement.*')"

new_web
add_release v1 "$WORK/v1.gz" "$DB1  data/ministere.duckdb"
check "installation (format historique : hash base) réussie" run_install
check "état : empreinte publiée historique conservée" test "$(state_val DB_REMOTE_SHA256)" = "$DB1"

new_web
add_release v1 "$WORK/v1.gz" "$(printf '%064d' 0)  ministere.duckdb.gz"
check "installation refusée si empreinte invalide" not run_install
check "aucune base installée après refus" test ! -f "$HOME/.ministere-info/data/ministere.duckdb"

new_web
add_release v2-sans-db "" ""
add_release v1 "$WORK/v1.gz" "$GZ1  data/ministere.duckdb.gz"
check "installation : release récente sans DB → release antérieure" run_install
check "état : tag de la release contenant la DB" test "$(state_val DB_RELEASE_TAG)" = v1

# ── update.sh ────────────────────────────────────────────────────────────
echo "update.sh"
# U1 — Cas réel v0.5 : .sha256 = hash de l'archive (« data/ministere.duckdb.gz »),
#      installation antérieure au correctif (pas d'état local).
new_web
add_release v0.5 "$WORK/v1.gz" "$GZ1  data/ministere.duckdb.gz"
mkdir -p "$HOME/.ministere-info/data"
cp "$ROOT/deploy/docker-compose.yml" "$HOME/.ministere-info/"
printf 'APP_PORT=8501\nDB_PATH=%s\n' "$HOME/.ministere-info/data" > "$HOME/.ministere-info/.env"
cp "$DBV1" "$HOME/.ministere-info/data/ministere.duckdb"
check "U1 sans état : mise à jour réussie" run_update
check "U1 sans état : un seul téléchargement (inévitable, archive non reconstructible)" \
  test "$(downloads_of)" = 1
check "U1 état écrit (empreinte archive)" test "$(state_val DB_REMOTE_SHA256)" = "$GZ1"
: > "$FAKE_WEB/.requetes"
check "U1 2e passage réussi" run_update
check "U1 2e passage : aucun retéléchargement" test "$(downloads_of)" = 0
check "U1 2e passage : message « déjà à jour »" grep -q "déjà à jour" "$WORK/update.log"

# U2 — Format historique (hash de la base), sans état : aucun téléchargement.
new_web
add_release v0.4 "$WORK/v1.gz" "$DB1  data/ministere.duckdb.gz"
mkdir -p "$HOME/.ministere-info/data"
cp "$ROOT/deploy/docker-compose.yml" "$HOME/.ministere-info/"
cp "$DBV1" "$HOME/.ministere-info/data/ministere.duckdb"
check "U2 historique sans état : réussi" run_update
check "U2 aucun téléchargement" test "$(downloads_of)" = 0
check "U2 état écrit" test "$(state_val DB_REMOTE_SHA256):$(state_val DB_SHA256)" = "$DB1:$DB1"

# U3 — Nouvelle release : téléchargement, remplacement, état mis à jour.
new_web
add_release v1 "$WORK/v1.gz" "$GZ1  ministere.duckdb.gz"
run_install
RELEASES_JSON_ENTRIES=()
add_release v2 "$WORK/v2.gz" "$GZ2  ministere.duckdb.gz"
add_release v1 "$WORK/v1.gz" "$GZ1  ministere.duckdb.gz"
: > "$FAKE_WEB/.requetes"; : > "$FAKE_WEB/.docker"
check "U3 nouvelle release : réussi" run_update
check "U3 un téléchargement" test "$(downloads_of)" = 1
check "U3 base remplacée par v2" test "$(sha "$HOME/.ministere-info/data/ministere.duckdb")" = "$DB2"
check "U3 état v2" test "$(state_val DB_RELEASE_TAG):$(state_val DB_REMOTE_SHA256)" = "v2:$GZ2"
check "U3 application arrêtée avant remplacement" grep -q "docker compose stop" "$FAKE_WEB/.docker"

# U4 — Téléchargement corrompu : échec, base et état conservés.
RELEASES_JSON_ENTRIES=()
add_release v3 "$WORK/v1.gz" "$(printf '%064d' 1)  ministere.duckdb.gz"
: > "$FAKE_WEB/.docker"
check "U4 empreinte invalide : échec signalé" not run_update
check "U4 base v2 conservée" test "$(sha "$HOME/.ministere-info/data/ministere.duckdb")" = "$DB2"
check "U4 état inchangé" test "$(state_val DB_RELEASE_TAG)" = v2
check "U4 application non arrêtée" not grep -q "compose stop" "$FAKE_WEB/.docker"
check "U4 pas de dossier temporaire résiduel" \
  test -z "$(find "$HOME/.ministere-info" -name '.telechargement.*')"

# U5 — Archive tronquée (gzip -t).
RELEASES_JSON_ENTRIES=()
head -c 1000 "$WORK/v1.gz" > "$WORK/tronque.gz"
add_release v4 "$WORK/tronque.gz" "$(sha "$WORK/tronque.gz")  ministere.duckdb.gz"
check "U5 archive tronquée : échec signalé" not run_update
check "U5 base v2 conservée" test "$(sha "$HOME/.ministere-info/data/ministere.duckdb")" = "$DB2"

# U6 — Base locale absente : téléchargement même si l'état correspond.
RELEASES_JSON_ENTRIES=()
add_release v2 "$WORK/v2.gz" "$GZ2  ministere.duckdb.gz"
rm -f "$HOME/.ministere-info/data/ministere.duckdb"
: > "$FAKE_WEB/.requetes"
check "U6 base absente : réussi" run_update
check "U6 base retéléchargée" test "$(sha "$HOME/.ministere-info/data/ministere.duckdb")" = "$DB2"

# U7 — API injoignable : avertissement, pas d'échec, base conservée.
export FAKE_OFFLINE=1
check "U7 hors ligne : pas d'échec" run_update
check "U7 avertissement affiché" grep -q "Vérification ignorée" "$WORK/update.log"
unset FAKE_OFFLINE

# ── download_db.sh ───────────────────────────────────────────────────────
echo "download_db.sh"
DL="$WORK/dlrepo"
mkdir -p "$DL/scripts"
cp "$ROOT/scripts/download_db.sh" "$DL/scripts/"
export GITHUB_TOKEN=factice
new_web
api="$FAKE_WEB/api.github.com/repos/$REPO"
mkdir -p "$api/releases/tags" "$api/releases/assets"
cp "$WORK/v2.gz" "$api/releases/assets/21"
printf '%s  data/ministere.duckdb.gz\n' "$GZ2" > "$api/releases/assets/22"
cp "$WORK/v1.gz" "$api/releases/assets/11"
printf '%s  data/ministere.duckdb\n' "$DB1" > "$api/releases/assets/12"
printf '%s\n' "$(printf '%064d' 7)" > "$api/releases/assets/32"
A="https://api.github.com/repos/$REPO/releases/assets"
python3 - "$api" "$A" <<'PY'
import json, sys
api, a = sys.argv[1], sys.argv[2]
def rel(tag, gz, sha):
    assets = [] if gz is None else [
        {"name": "ministere.duckdb.gz", "url": f"{a}/{gz}"},
        {"name": "ministere.duckdb.gz.sha256", "url": f"{a}/{sha}"},
    ]
    return {"tag_name": tag, "draft": False, "assets": assets}
releases = [rel("v0.6-sans-db", None, None), rel("v0.5", 21, 22), rel("db-2026-05", 11, 12)]
json.dump(releases, open(f"{api}/releases?per_page=30", "w"))
for r in releases:
    json.dump(r, open(f"{api}/releases/tags/{r['tag_name']}", "w"))
json.dump(rel("v-corrompue", 21, 32), open(f"{api}/releases/tags/v-corrompue", "w"))
PY
run_dl() { bash "$DL/scripts/download_db.sh" "$@" > "$WORK/dl.log" 2>&1; }
check "D1 sans argument : réussi" run_dl
check "D1 release la plus récente avec DB (v0.5, pas db-*)" grep -q "Release retenue : v0.5" "$WORK/dl.log"
check "D1 base = v2 (empreinte archive)" test "$(sha "$DL/data/ministere.duckdb")" = "$DB2"
check "D2 tag explicite, format historique : réussi" run_dl db-2026-05
check "D2 base = v1" test "$(sha "$DL/data/ministere.duckdb")" = "$DB1"
bash "$DL/scripts/download_db.sh" v-corrompue > "$WORK/dl.log" 2>&1
check "D3 empreinte invalide : code 4" test $? -eq 4
check "D3 base existante conservée" test "$(sha "$DL/data/ministere.duckdb")" = "$DB1"
check "D3 pas de dossier temporaire résiduel" test -z "$(find "$DL/data" -name '.telechargement.*')"

echo ""
echo "Résultat : $PASS réussis, $FAIL échoués"
[[ "$FAIL" -eq 0 ]]
