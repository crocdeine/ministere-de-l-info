# Exécution native (macOS Apple Silicon)

Mode principal d'exécution sur le Mac mini ([ADR-0012](../../docs/adr/0012-execution-native-mac.md)).
Procédure complète, bascule depuis Docker et dépannage : [`docs/deployment.md`](../../docs/deployment.md).

| Fichier | Rôle |
|---|---|
| `install-native.sh` | Installe ou réinstalle (idempotent) : uv sync, extension spatial, LaunchAgents application et sauvegarde. `--aide` pour les options. |
| `start.sh` | Démarre l'application, ou la redémarre si elle tourne. |
| `stop.sh` | Arrête l'application (avant un ETL). |
| `status.sh` | État de l'application, de la base et des sauvegardes. |
| `uninstall-native.sh` | Retire le démarrage automatique (ne supprime ni base, ni sauvegardes, ni `.venv`). |
| `ministere-info.plist` | Modèle du LaunchAgent (marqueurs `@...@` remplacés par `install-native.sh`). |
| `commun.sh` | Fonctions partagées (chargé par les autres scripts). |

Tests simulés (Linux ou macOS, sans launchd ni réseau) :

```bash
bash deploy/tests/test_native.sh
bash deploy/tests/test_backup_db.sh
```
