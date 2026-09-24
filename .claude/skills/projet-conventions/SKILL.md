---
name: projet-conventions
description: Conventions du projet ministere-de-l-info : schéma DuckDB réel (tables et vues par module), arborescence, nommage, commandes courantes. À charger avant de créer ou modifier un loader, une table, une vue SQL, une page, un test, ou de refactoriser.
---

# Conventions projet — ministere-de-l-info

> Source de vérité : le code. Ce skill a été vérifié contre `src/ministere_de_l_info/etl/schema*.py`,
> `views.py`, `scripts/migrations/` et l'arborescence au 2026-09-24. En cas de doute, relire le code.

## 1. Stack et outils (NON NÉGOCIABLES)

| Outil | Règle |
|---|---|
| Python | 3.12 strict, type hints partout |
| Paquets | `uv` **uniquement** — jamais pip, poetry, conda |
| Environnement | `uv sync --all-groups` (groupes : `dev`, `etl` = geopandas + openpyxl, `ai`) |
| Exécution | `uv run <commande>` — jamais `python` direct |
| Lint/format | `ruff` (line-length 100) via pre-commit ; `.claude/` est exclu des hooks |
| Tests | `pytest` ; `addopts` exclut `slow` (tests qui lancent un process Streamlit) ; les tests qui exigent la base font `pytest.skip` si `data/ministere.duckdb` est absente |
| Commits | Conventional Commits : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`, `perf:` |
| Branches | CLAUDE.md : branche par feature + PR squash-merge. En pratique l'historique est sur `main` sans PR ; le workflow Git est une décision ouverte (état des lieux 2026-09-24). CI déclenchée seulement sur `main` et PR vers `main`. |
| DataFrame | Polars en priorité ; pandas toléré pour XLSX/TSV (DREES, Eurostat) et l'interface Folium |

## 2. Structure des fichiers

```
ministere-de-l-info/
├── app.py                         # Routeur st.navigation() : page config + inject_css() une fois
├── pages/                         # Déclarées dans app.py via st.Page (icônes Material)
│   ├── 0_🏠_Accueil.py            # Hub de navigation (4 tuiles)
│   ├── 1_📍_Géographie.py         # Logique inline (historique), @st.cache_resource
│   ├── 2_🗳️_Élections.py          # Onglets pres / legi / muni → pages/elections_*.render()
│   ├── 3_🏛️_Législatif.py         # → pages/legislatif.render()
│   └── 4_📊_Économie.py           # → pages/economie.render()
├── src/ministere_de_l_info/
│   ├── _theme.py                  # inject_css(), render_page_header()
│   ├── _blocs_politiques.py       # BLOCS_ORDERED, COULEURS_BLOCS, LIBELLES_BLOCS (source unique)
│   ├── custom.css                 # Tokens du design system
│   ├── logging_config.py
│   ├── data_sources/              # geo.py, circonscriptions.py, insee_populations.py
│   ├── etl/
│   │   ├── _common.py             # open_connection(), upsert_metadata()
│   │   ├── schema.py              # Géo + populations + méta
│   │   ├── schema_elections.py    # Tables, référentiels (nuances, candidats), vues électorales
│   │   ├── schema_economie.py     # Tables + vues économie
│   │   ├── schema_legislatif.py   # Tables + vues législatif
│   │   ├── views.py               # Vues population
│   │   └── loaders/               # regions, departements, epci, communes, arrondissements_municipaux,
│   │                              # circonscriptions, populations, economie_{filosofi,rp,cnaf,drees,
│   │                              # urssaf,eurostat}, legislatif_{datan,senat,overrides},
│   │                              # legislatif_{nosdeputes,clair} (inutilisés), _http_retry
│   ├── pages/                     # render() : economie, elections_{presidentielles,legislatives,
│   │                              # municipales}, legislatif
│   └── viz/                       # _config, _display, _queries, maps, maps_elections,
│                                  # elections_{,legi_,muni_}queries, economie_queries, legislatif_queries
├── scripts/                       # etl_territoires.py, init_elections_schema.py, load_elections_*.py,
│   │                              # load_economie.py, load_legislatif.py, *_db.sh, etl_regions.py (obsolète)
│   └── migrations/                # 0006 (colonnes listes municipales), 0007 (vues municipales)
├── tests/                         # ~350 fonctions de test
├── deploy/                        # Dockerfile (image GHCR), install.sh, update.sh
├── docs/                          # architecture, schema-elections, data-sources, deployment,
│                                  # lessons-learned, guide-utilisateur, adr/ (0001→0006), sources-officielles/
├── reports/                       # Rapports de session (templates/ pour les modèles)
└── data/ministere.duckdb          # gitignored
```

**Règle de placement** : jamais de fichier de travail ou de test à la racine.

## 3. Schéma DuckDB réel

### Géographie + méta (`etl/schema.py`, `etl/views.py`)

| Objet | Clé / colonnes notables |
|---|---|
| `geographies_regions` | `code_insee VARCHAR(3)`, `nom`, `geometry`, `geometry_simplified_{national,regional}` |
| `geographies_departements` | `code_insee VARCHAR(3)`, `code_region`, `geometry_simplified_{national,departemental}` |
| `geographies_epci` | `code_siren VARCHAR(9)`, `type_epci`, `code_departement_principal`, `geometry_simplified_epci` |
| `geographies_communes` | `code_insee VARCHAR(5)`, `nom`, `code_departement`, `code_region`, `code_epci`, `geometry_simplified_communal` |
| `geographies_arrondissements_municipaux` | `code_insee`, `code_commune_mere` |
| `geographies_circonscriptions` | `code VARCHAR(6)`, `code_departement`, `geometry_simplified_circo` |
| `populations` | `code_insee_commune`, `annee`, `municipale`, `comptee_a_part`, `totale`, `source` |
| `_etl_metadata`, `_schema_version` | Traçabilité des chargements |
| Vues | `v_population_{commune,departement,region,epci}` |

⚠️ Dans les tables géo, la clé commune s'appelle `code_insee` ; dans les tables métier, `code_commune`.

### Élections (`etl/schema_elections.py` + `scripts/migrations/0006-0007`)

| Objet | Contenu |
|---|---|
| `elections` | `id_election` (`2022_pres_t1`), `type_scrutin`, `annee`, `tour`, `libelle`, `ancien_decoupage` |
| `resultats_participation` | par BV : inscrits, abstentions, votants, blancs, nuls, exprimes, `code_circo` |
| `resultats_candidats` | par BV × `no_panneau` : nuance, nom, prénom, voix (+ colonnes listes municipales) |
| `blocs_politiques` | `bloc`, `libelle`, `couleur`, `ordre` (6 blocs) |
| `nuances_harmonisees` | `(nuance, annee) → bloc` + `source_bloc` (justification) |
| `candidats_presidentielle` | `(annee, nom) → bloc` pour 2017/2022 (nuance NULL dans la source) |
| Vues | `v_resultats_candidats_avec_bloc`, `v_scores_commune_pres`, `v_participation_commune_pres`, `v_scores_circo21_pres`, `v_evolution_blocs_circo21`, `v_scores_circo_legi`, `v_participation_circo_legi`, `v_evolution_blocs_hdf_legi`, et (migration 0007) `v_scores_commune_muni`, `v_evolution_blocs_hdf_muni`, `v_listes_commune_muni` |

Fonctions : `create_elections_schema()`, `populate_elections_referentiels()`, `create_elections_views()`.

### Économie (`etl/schema_economie.py`) — Hauts-de-France

| Objet | Contenu |
|---|---|
| `economie_filosofi` | `(code_commune, annee)` : taux_pauvrete, niveau_vie_median, d1/d9_niveau_vie, secret |
| `economie_rp` | `(code_commune, annee_millesime)` : tx_chomage_dec, part_ouvriers_employes, part_emploi_industriel, part/nb_logements_sociaux, pop_active, secret |
| `economie_social` | `(code_commune, annee)` : nb/taux_foyers_rsa (CNAF), apl_medecins, desert_medical (DREES) |
| `economie_emploi_urssaf` | `(code_commune, annee, code_ape)` : secteur_gs, nb_salaries, nb_etablissements |
| `economie_contexte` | `(code_geo, annee, indicateur)` : Eurostat chômage BIT, PIB/hab (HdF vs France) |
| Vues | `v_economie_commune`, `v_croisement_eco_elections`, `v_evolution_economie_hdf`, `v_economie_sociale_commune`, `v_desindustrialisation_commune`, `v_contexte_hdf_vs_france` |

### Législatif (`etl/schema_legislatif.py`) — national

| Objet | Contenu |
|---|---|
| `leg_elus` | `(id, chambre)` : legislature, identité, `code_departement`, groupe_sigle, `bloc_politique`, mandat, `est_actif` |
| `leg_activite` | `(elu_id, chambre, date_extraction)` : présences, amendements, scores Datan (AN seulement) |
| `leg_blocs_override` | `(elu_id, chambre) → bloc_force` + justification |
| Vues | `v_elus_hdf_actuels` (⚠️ malgré son nom : élus actifs **toutes régions**, bloc final avec override), `v_activite_par_bloc` |

## 4. Conventions de nommage DuckDB

- Tables : `snake_case`, préfixe de module (`geographies_`, `economie_`, `leg_`) ; tables électorales sans préfixe.
- Vues : `v_` + thème + grain (+ scrutin) — `v_scores_commune_pres`, `v_evolution_blocs_hdf_muni`.
- `code_commune` / `code_insee` commune : `VARCHAR(5)`, JAMAIS INTEGER ; département `VARCHAR(3)`.
- `annee` : `INTEGER` (RP : `annee_millesime`).
- Idempotence : `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE VIEW`.

## 5. Conventions Python

- Line-length 100, docstrings courtes en français, `logging` (jamais `print()` en prod).
- Départements HdF : `("02", "59", "60", "62", "80")` — actuellement dupliqué (`_DEPTS_HDF` dans chaque loader économie, `_HDF_DEPTS_SQL` dans `viz/elections_queries.py`).
- Requêtes UI : fonctions `@st.cache_data` dans `viz/*_queries.py`, connexion `_open_ro()` (read-only + `LOAD spatial`), fermée dans `finally`.
- SQL en f-string : uniquement avec liste blanche (ex. `_INDICATEURS_VALIDES`), sinon paramètres `?`.

## 6. Blocs politiques officiels (ADR-0005)

6 blocs : `EXG` Extrême gauche, `GAU` Gauche, `DIV` Divers, `CENT` Centre, `DTE` Droite, `EXD` Extrême droite.
Classement « de l'époque » (grille en vigueur à la date du scrutin), justification `source_bloc`.
Ne jamais inventer `centre-gauche`, `centre-droit`, etc. Détails et couleurs : skill `data-viz-politique`,
code : `_blocs_politiques.py`. Toute modification de classement = décision de Mathias.

## 7. Points d'arrêt (CLAUDE.md)

1. Décision structurante (architecture, schéma, source, classement, workflow) : proposer → attendre Mathias → ADR si validé.
2. « POINT D'ARRÊT », « STOP », « ATTENDRE VALIDATION » dans un prompt : s'arrêter.
3. Validation UI demandée : AppTest ne la remplace pas.
4. Après `git push` : vérifier le run dont `headSha` = `git rev-parse HEAD` (Mac : `gh run list --limit 3 --json databaseId,headSha,conclusion,displayTitle` ; cloud : outils GitHub MCP, `gh` absent).
5. Fin de tâche significative : rapport dans `reports/`, proposition de mise à jour de CLAUDE.md.

## 8. Gotchas techniques

- Pre-commit ruff reformate → `git add` puis **nouveau** commit (pas `--amend`).
- Streamlit rerun complet à chaque clic → chargement lourd en `@st.cache_data`.
- EPSG:4326 pour Folium (`to_crs` avant), EPSG:2154 pour les calculs métriques.
- Parquet élections : `general-results.parquet` = candidats ; `candidats-results.parquet` = participation.
- Nuances NULL pour les présidentielles 2017/2022 → `candidats_presidentielle`.
- Session cloud : pas de `data/`, réseau restreint (INSEE/IGN/data.gouv, extension `spatial`) → la plupart des tests sont ignorés.

## 9. Commandes courantes

```bash
uv sync --all-groups                  # Environnement complet
uv run pytest -q                      # Tests (hors slow)
uv run pytest -m slow                 # Tests Streamlit (process externe)
uv run ruff check . && uv run ruff format --check .
uv run streamlit run app.py           # Lancer l'app (base requise)
uv run python scripts/load_economie.py --help
git log --oneline -10                 # Début de session
```
