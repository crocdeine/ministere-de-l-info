# Infra : durcissement J4 (audit I13)

Date : 2026-10-06 — Agent : ingénieur infra — Branche `claude/exciting-dirac-8mogwe` (non poussée)

## Résumé exécutif
- Les 3 compose publient désormais `127.0.0.1:8501` (ADR-0012) ; la doc était déjà juste.
- `scripts/download_db.sh` échoue (code 4) sans `.sha256` ou avec `.sha256` vide ; tests D4/D5 ajoutés (55/55 verts).
- Dockerfile : SHA256 de l'archive Tectonic vérifié (x86_64 et aarch64).
- 9 actions GitHub épinglées par SHA de commit (tag en commentaire).
- Images de base épinglées par digest d'index multi-arch ; `deploy/Dockerfile` aligné sur bookworm.
- Non traité : `curl | bash` depuis `main` (décision ci-dessous).
- Vérifié : `bash -n`, YAML, `docker compose config`. Non fait : shellcheck (absent), build.

## Changements
1. Ports : `docker-compose.yml`, `docker-compose.prod.yml`, `deploy/docker-compose.yml` (`127.0.0.1:${APP_PORT:-8501}:8501`). Note à `deploy/README-deploy.md`. Les healthchecks internes (localhost dans le conteneur) sont inchangés.
2. SHA256 : `scripts/download_db.sh` ne continue plus sans empreinte (avant le `mv`, base existante intacte). Tests dans `deploy/tests/test_db_checksum.sh`.
3. Tectonic 0.16.9 : sommes lues dans le champ `digest` des assets de la release GitHub `tectonic@0.16.9` (le projet ne publie pas de fichier de somme). x86_64-musl `60b13a08...a902`, aarch64-musl `f9aa3901...f9c1`. Contrôle par `sha256sum -c`. À remettre à jour à chaque changement de version.
4. Actions (SHA dérefencés via l'API commits) : checkout df4cb1c0, setup-uv fac544c0, cache 55cc8345, upload-artifact 043fb46d, setup-qemu 06116385, setup-buildx d7f5e7f5, login 650006c6, metadata 80c7e94d, build-push f9f3042f. Les lignes de commentaire (docker-publish l.74) sont aussi mises à jour.
5. Images : `python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258` (Docker Hub, relevé le 2026-10-06, index multi-arch) dans `Dockerfile` (2 stages) et `deploy/Dockerfile` (anciennement `python:3.12-slim`, donc base Debian potentiellement différente : à surveiller).
6. `curl | bash` depuis `main` : laissé tel quel. Épingler sur un tag figerait `update.sh` sur une version périmée dès le commit suivant, et exige une étape de release qui réécrit les URLs. Documenté dans le README (possibilité de remplacer `main` par un tag/SHA).

## Test manuel pour Mathias (Mac)
- `docker build .` puis `docker buildx build --platform linux/amd64,linux/arm64 .` : doit passer la vérification Tectonic et `tectonic --version`.
- `docker compose up` ; `curl http://127.0.0.1:8501/_stcore/health` OK ; l'accès par l'IP LAN doit être refusé.
- `bash deploy/tests/test_db_checksum.sh` (déjà exécuté ici : 55 réussis).
- Après push : vérifier que le run CI de `headSha` correspond (actions épinglées résolues).

## Risques
- Le digest de base bloque les correctifs de sécurité Debian jusqu'à mise à jour manuelle (Dependabot/Renovate possible).
- Les releases existantes sans `.sha256` ne sont plus téléchargeables par `download_db.sh` (voulu).
- `docker compose config` sur dev/prod exige un `.env` (préexistant) ; validé avec un `.env` vide temporaire.

## Décisions à soumettre
1. Épingler `install.sh`/`update.sh`/compose sur un tag de release (avec étape de release) plutôt que `main` : oui/non ?
2. Activer Dependabot (github-actions + docker) pour tenir les SHA/digest à jour : oui/non ?
