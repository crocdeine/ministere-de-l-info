# Mission : contrôle d'espace disque avant toute écriture lourde

**Agent** : ingenieur-infra · **Branche** : chore/garde-espace-disque · **Base** : origin/main
**Décision d'origine** : directeur, 2026-10-09 (maintenance) — le disque externe s'est rempli deux fois
(téléchargements personnels), provoquant un export de tuiles tronqué et des compilations en échec.
**Complexité** : S

## Objectif
Aucune opération du projet qui écrit de gros fichiers ne démarre si le disque cible a moins de
10 Go libres ; message clair indiquant l'espace libre et le seuil.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Contrôle existant | `src/ministere_de_l_info/export_web/export.py:290` (`_verifier_espace`) | `shutil.disk_usage`, erreur explicite |
| Scripts shell | `deploy/native/commun.sh` | fonctions partagées |

## Tâches
### 1. Fonction commune Python
- **Action** : déplacer/généraliser `_verifier_espace` dans un module commun (ex. `ministere_de_l_info/espace_disque.py`),
  seuil par défaut 10 Go, surchargeable par variable d'environnement `MINISTERE_ESPACE_MIN_GO` ; l'appeler
  en tête de : chargements électoraux (`scripts/load_elections_*.py`, `load_communes_passage.py`),
  migrations, `load_economie.py`, `load_legislatif.py`, export web (garder son seuil spécifique s'il est
  plus élevé), `scripts/publish_db.sh` (via une petite fonction shell).
- **Valider** : test unitaire avec `disk_usage` simulé (sous le seuil → erreur ; au-dessus → rien).
### 2. Compilation de l'application Mac
- **Action** : script npm `tauri:build` précédé d'une vérification (Node, `fs.statfs`) du disque de
  `CARGO_TARGET_DIR` / `web/` ; même seuil.
- **Valider** : test manuel avec `MINISTERE_ESPACE_MIN_GO` très élevé → refus clair.
### 3. Documentation
- `docs/deployment.md` (section dépannage), `docs/lessons-learned.md` (disque plein deux fois).

## Hors périmètre
Aucun nettoyage automatique de fichiers ; aucune modification des données.

## Contraintes
Disque externe et `UV_CACHE_DIR` habituels ; ne pousse pas ; commits atomiques.

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uvx pyright@1.1.408
uv run pytest -m "not slow and not network"
```

## Acceptation
- [ ] Contrôle actif sur toutes les écritures lourdes listées, testé
- [ ] Documentation à jour
