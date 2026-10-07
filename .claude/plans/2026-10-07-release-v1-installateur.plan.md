# Mission : version 1.0 — installateur en une commande

**Agent** : ingenieur-infra · **Branche** : release/v1.0 · **Base** : origin/main
**Décision d'origine** : Mathias, 2026-10-07 — première version de prod = application Streamlit
actuelle complète, installée par une seule commande collée dans le Terminal.
**Complexité** : M

## Objectif
Un destinataire non technique, sur un Mac, colle une commande dans le Terminal et obtient une icône
« Ministère de l'Info » dans son dossier Applications, qui ouvre l'application dans son navigateur.
Mise à jour = relancer la même commande ; désinstallation = une commande documentée.

## Hors périmètre
- Publier quoi que ce soit (tag, release, push) : le directeur publie après accord de Mathias.
- Application Tauri, Docker, signature Apple (refusée par Mathias).
- Contenu de la base : la base v1.0 viendra de la vague B (publiée sous un tag `db-AAAA-MM-JJ`).

## Exigences
- `install.sh` à la racine, utilisable par
  `curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/v1.0.0/install.sh | bash`
  (épinglé sur le tag, jamais sur `main`).
- Aucun jeton GitHub (dépôt et releases publics), aucun `sudo`, aucun outil à installer à la main :
  installe uv par l'installateur officiel s'il manque (version épinglée, comme `install-native.sh`).
- Code téléchargé depuis l'archive du tag (pas besoin de git) ; base téléchargée depuis la release
  de base désignée par une variable en tête de script (`DB_TAG`), **empreinte SHA-256 vérifiée**
  (asset `.sha256`, convention de `scripts/download_db.sh`), décompressée ; reprise propre si le
  téléchargement est interrompu ; base conservée lors d'une mise à jour si l'empreinte n'a pas changé.
- Dossier d'installation : `~/Library/Application Support/Ministere-de-l-Info/` (code, base, venv) ;
  journaux dans `~/Library/Logs/Ministere-de-l-Info/`.
- Icône : `~/Applications/Ministère de l'Info.app` construite **localement** par le script (donc
  sans quarantaine Gatekeeper) ; au clic : démarre le serveur sur 127.0.0.1 (port libre à partir de
  8501) s'il ne tourne pas, attend qu'il réponde, ouvre le navigateur. Pas de LaunchAgent permanent
  ni de sauvegarde automatique pour les destinataires (ce sont des lecteurs).
- `uninstall.sh` : supprime dossier, icône, journaux ; demande confirmation.
- Messages en français, simples, une étape par ligne ; échec = message clair + chemin du journal.
- Mac Apple Silicon testé ; Intel : dire honnêtement « non testé » dans la doc.
- Espace disque requis vérifié avant téléchargement (base ≈ 1,3 Go décompressée + 0,7 Go archive).

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Fonctions shell communes | `deploy/native/commun.sh` | réutiliser (port, attente du serveur, journaux) plutôt que dupliquer |
| Lancement | `deploy/native/lancer-app.sh` | démarrage + ouverture du navigateur |
| Téléchargement vérifié | `scripts/download_db.sh` | `sha256_of`, comparaison stricte |
| uv épinglé | `deploy/native/install-native.sh` (`VERSION_UV_RECOMMANDEE`) | même version |

## Tâches
### 1. `install.sh` + `uninstall.sh`
- **Valider** : `shellcheck install.sh uninstall.sh` sans erreur.
### 2. Mode test local
- **Action** : variables d'environnement de surcharge (`MI_SOURCE_ARCHIVE`, `MI_DB_ARCHIVE`,
  `MI_INSTALL_DIR`, `MI_APPS_DIR`) pour installer depuis des fichiers locaux.
- **Valider** : installation complète dans `/Volumes/le gros stockage/outils/tmp/test-install/`
  depuis `git archive` de la branche et une copie compressée de `data/ministere.duckdb`
  (lecture seule) ; l'icône lance l'app ; `curl` de la page répond 200 ; deuxième passage
  (mise à jour) idempotent ; `uninstall.sh` nettoie tout. Rien d'écrit dans le vrai `~/Applications`.
### 3. Version et notes
- **Action** : `pyproject.toml` version `1.0.0` (+ `uv lock` si nécessaire), `CHANGELOG.md`
  (format Keep a Changelog, en français, depuis v0.5 : licences, design v2, France entière, etc.),
  brouillon `docs/release-notes-v1.0.md` (pour qui, ce que fait l'app, installation, limites,
  données et licences, application non signée → aucune conséquence ici car l'icône est créée
  localement).
### 4. Documentation
- **Action** : README (section Installation = la commande), `docs/deployment.md`,
  `docs/guide-utilisateur.md` (premier lancement, mise à jour, désinstallation), `docs/reprise.md`.
- Liste de publication pour le directeur dans le rapport : tag, assets, ordre des opérations.

## Contraintes du projet
- Disque interne presque plein : tests, archives, venv de test sur le disque externe
  (`TMPDIR`, `UV_CACHE_DIR` sous `/Volumes/le gros stockage/outils/`).
- Base réelle en lecture seule ; ne jamais pousser ni publier.
- Commits tôt et souvent. Réflexe documentation.

## Validation finale
```bash
shellcheck install.sh uninstall.sh deploy/native/*.sh
uv run ruff check . && uv run pytest -m "not slow and not network"
```
Plus le scénario de la tâche 2, avec temps d'installation mesuré.

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| `curl | bash` coupé en plein milieu | moyenne | tout le script dans une fonction `main` appelée en dernière ligne |
| Port 8501 déjà pris | moyenne | recherche d'un port libre, mémorisé |
| Disque plein chez le destinataire | faible | contrôle d'espace préalable |
| Python absent | certaine | uv installe Python 3.12 lui-même |

## Acceptation
- [ ] Scénario local complet vert (installation, lancement, mise à jour, désinstallation)
- [ ] shellcheck propre, tests verts
- [ ] Documentation et notes de version
- [ ] Rapport `reports/release-v1-installateur-2026-10-07.md` avec liste de publication
