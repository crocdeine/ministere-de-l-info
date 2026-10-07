# Audit ponytail — 2026-10-07

Périmètre : `src/`, `scripts/`, `pages/`, `deploy/` (hors `web/`, `data/`, worktrees, fixtures). Lecture seule ; rien n'est appliqué.
Méthode : AST + `git grep` sur tout le dépôt (tests compris) ; graphify pour l'orientation.

Résumé :
- Code mort avéré : `_http_retry.py` entier (aucun import), `_melt_to_rows`, deux constantes, un `.bak` suivi par git.
- 5 dépendances jamais importées (feedparser, jinja2, python-dotenv, requests-cache en prod ; anthropic, geopandas en groupes). Les paquets Streamlit/duckdb n'en dépendent pas.
- Doublons : 5 copies de `_download_cache`, 3 `_open_ro`, 3 `_opt_int`, 2 `_parse_date`, 3 `is_data_loaded` au squelette identique.
- Legacy : `scripts/etl_regions.py` + `fetch_regions_geojson` + `POPULATION_2024` (remplacés par `etl/loaders/regions.py`).
- Gain total estimé : environ 520 lignes (dont ~330 sûres) et 6 dépendances. Aucune suppression ne touche aux classements politiques.
- « À vérifier par le directeur » : tout ce qui est dans `etl/loaders/` et la stack imposée par CLAUDE.md (Jinja2, GeoPandas).

| # | Tag | Fichier:ligne | Constat | Gain (lignes) | Risque |
|---|-----|---------------|---------|---------------|--------|
| 1 | delete | `src/ministere_de_l_info/etl/loaders/_http_retry.py:1-115` | Module jamais importé (`fetch_with_retry` n'est appelé que par `fetch_page_cached`, lui-même sans appelant ; `url_cache_key` idem). `data_sources/geo.py:66` a son propre `_http_retry_get`. | -115 | Faible. À vérifier par le directeur (dossier loaders) |
| 2 | delete | `src/ministere_de_l_info/etl/loaders/economie_eurostat.py.bak` | Copie identique (`diff` vide) de `economie_eurostat.py`, suivie par git. | -246 | Nul |
| 3 | delete | `pyproject.toml:12,15,22,23` | `feedparser`, `jinja2`, `python-dotenv`, `requests-cache` : aucun import dans src/scripts/pages/tests/deploy. `pydantic-settings` lit `.env` seul. `jinja2` reste installé via Streamlit/Folium (transitif). Retirer aussi du `uv.lock` (`uv lock`). | -4 deps | Faible. Jinja2 figure dans la stack « non négociable » de CLAUDE.md : décision du directeur |
| 4 | delete | `pyproject.toml:44` (`ai`), `.env.example:8-10` | `anthropic` : aucun import, groupe `ai` jamais installé par la CI ni le Dockerfile. `ANTHROPIC_API_KEY` sans lecteur dans `config.py`. | -1 dep, -3 | Faible. À réintroduire si les rapports assistés reviennent |
| 5 | delete | `pyproject.toml:47` (`etl`) ; `deploy/Dockerfile:12,43` | `geopandas` : aucun import (l'ETL passe par DuckDB spatial). Le groupe `etl` ne garde alors que `openpyxl` (lu par `pandas.read_excel` dans `economie_drees.py`). Les paquets GDAL du Dockerfile ne servent plus qu'à lui (à confirmer au build). | -1 dep (+ image plus légère) | Moyen (build Docker, CLAUDE.md cite GeoPandas). À vérifier par le directeur |
| 6 | yagni | `scripts/etl_regions.py:1-76`, `data_sources/geo.py:18-35,289-323` | Chargeur de régions legacy (`fetch_regions_geojson`, `POPULATION_2024`, « alias pour les tests ») doublonné par `etl/loaders/regions.py`. Seuls `tests/test_etl_regions.py` et le script les utilisent. `_CODES_METRO` ne sert qu'à cet alias. Supprimer script, alias, constante et test. | -76 -50 | Moyen. À vérifier par le directeur (ETL) |
| 7 | shrink | `etl/loaders/economie_cnaf.py:46`, `economie_drees.py:46`, `economie_eurostat.py:51`, `economie_urssaf.py:49`, `legislatif_senat.py:206` | 5 copies de `_download_cache` (4 quasi identiques : stream httpx → fichier). Un helper `telecharger(url, dest, force, timeout)` dans `etl/_common.py` (existe déjà, 1 Ko). Le Sénat garde sa validation en plus. | -45 | Moyen. À vérifier par le directeur (loaders) |
| 8 | delete | `etl/loaders/economie_eurostat.py:92-119` | `_melt_to_rows` : définie, jamais appelée (le loader doit passer par DuckDB/polars). Après suppression, vérifier si `pd` ne sert plus qu'à `_parse_eurostat_tsv`. | -28 | Faible. À vérifier par le directeur |
| 9 | shrink | `viz/economie_queries.py:62`, `viz/elections_queries.py:47`, `viz/legislatif_queries.py:52` ; `is_data_loaded` en `economie_queries.py:72`, `elections_queries.py:57`, `legislatif_queries.py:75` | `_open_ro()` copié 3 fois (`open_ro(DB_PATH)`), 3 `is_data_loaded` au même squelette (ouvrir, `COUNT(*)`, fermer). Une `tables_non_vides(con, [(table, where)])` dans `viz/_queries.py`. | -35 | Faible |
| 10 | shrink | `viz/elections_queries.py:51`, `elections_muni_queries.py:29`, `elections_legi_queries.py:46` | `_opt_int` copié 3 fois. Le mettre dans `viz/_display.py` ou `_sql.py`. | -8 | Nul |
| 11 | shrink | `etl/loaders/legislatif_datan.py:102`, `legislatif_senat.py:239` | `_parse_date` en double (corps identique). Partager via `etl/_common.py`. | -8 | Faible. À vérifier par le directeur (loaders législatifs) |
| 12 | delete | `viz/maps_elections.py:311-319` | `_HATCH_PATTERN_SVG` : constante jamais référencée (la légende dessine déjà ses hachures). | -9 | Nul |
| 13 | delete | `etl/loaders/legislatif_senat.py:57-58` | `_CIRCOS_HDF` : constante sans lecteur. | -2 | Nul |
| 14 | delete | `src/ministere_de_l_info/__init__.py:6-7`, `pyproject.toml:27-28` | `main()` vide et entrée `[project.scripts]` qui l'expose. Garder `__version__`. | -5 | Nul |
| 15 | yagni | `scripts/load_elections_{presidentielles,legislatives,municipales}.py` (`_load_participation`, `_load_candidats`, `_print_summary`) | Trois scripts de même forme : 3 × `_load_participation` (~30 l.), 3 × `_load_candidats`, 4 × `_print_summary`. Factorisation possible mais touche les chargeurs électoraux. À ne pas faire sans le directeur. | -80 à -120 | Élevé. À vérifier par le directeur (ETL + nuances) |
| 16 | shrink | `pages/economie.py:497`, `pages/legislatif.py:376` | Deux `_render_evolution_tab` de même nom mais de contenu différent : pas un doublon réel, rien à faire (écarté). | 0 | — |
| 17 | delete | `scripts/com.crocdeine.ministere-info.backup.plist` (66 l.), `deploy/native/commun.sh`, `install-native.sh` (références) | CLAUDE.md : « tâche launchd supprimée le 2026-10-06 ». Le plist modèle et ses références vivent encore. Si la sauvegarde n'est plus planifiée, les retirer ; sinon corriger CLAUDE.md. | -66 + références | Moyen. À vérifier par le directeur (décision de sauvegarde) |
| 18 | shrink | `tests/test_streamlit_smoke.py:16,63` (dev dep `pyproject.toml:39`) | `requests` utilisé une seule fois dans les tests : `httpx.get` fait pareil (déjà en dépendance). | -1 dep dev | Nul |

Total estimé : sûr (1, 2, 8, 9, 10, 12, 13, 14, 18) environ 450 lignes ; avec 4-7, 11, 17 environ 600 ; avec 15 jusqu'à 720.

Écartés après vérification : migrations `scripts/migrations/0006-0008` (chargées par `tests/fixtures/sample_db.py` ; à garder), `scripts/veille_groupes_senat.py` (testé, cité dans le plan de reprise), `scripts/export_sample_db.py` (pre-commit), `etl_territoires.py`, wrappers `pages/N_*.py` (requis par `st.navigation`).
