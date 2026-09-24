---
name: insee-duckdb-loader
description: "Chargement dans DuckDB des sources économiques (INSEE Filosofi et RP, CNAF, DREES, URSSAF, Eurostat) : encodage, secret statistique, codes INSEE, idempotence. À charger pour tout ETL économie ou donnée INSEE (revenus, pauvreté, chômage, CSP, logements sociaux)."
---

# INSEE → DuckDB : conventions de chargement

> Vérifié contre `scripts/load_economie.py`, `src/ministere_de_l_info/etl/loaders/economie_*.py`
> et `etl/schema_economie.py` au 2026-09-24.

## 1. Sources réellement chargées

| Table | Source | Loader | Format / accès | Millésimes |
|---|---|---|---|---|
| `economie_filosofi` | INSEE Filosofi, dataset data.gouv `67289477639527408ae687da` (« RP communal et Filosofi depuis 2015 ») | `economie_filosofi.py` | Parquet **long/OLAP** (`code_com, annee, source, clef_json, valeur`), `source='filosofi_disponible'` | 2017-2021 |
| `economie_rp` | INSEE RP, même Parquet | `economie_rp.py` | `source IN ('rp_actifs_emploi','rp_logements')` | 2015-2021 |
| `economie_social` | CNAF (RSA, data.caf.fr) + DREES (APL médecins, XLSX) | `economie_cnaf.py`, `economie_drees.py` | CSV `;` / XLSX (pandas + openpyxl, groupe `etl`) | CNAF 2020-2024 |
| `economie_emploi_urssaf` | URSSAF open data (salariés × APE) | `economie_urssaf.py` | CSV `;`, colonnes par année | 2006-2025 |
| `economie_contexte` | Eurostat SDMX (chômage BIT, PIB/hab, HdF vs France) | `economie_eurostat.py` | TSV (pandas) | 1999-2025 |

Non utilisés à ce jour : **Sirene** (prévu par ADR-0006, remplacé par le RP pour
`part_emploi_industriel`) et **BPE**. Les introduire = nouvelle source → validation Mathias + ADR.

Le Parquet national (~1,7 Go) n'est jamais chargé entier : `scripts/load_economie.py` le lit à
distance (httpfs, pushdown) et écrit un cache HdF `data/raw/economie/donnees-insee-olap-hdf.parquet`
(~40-50 Mo), que les loaders lisent ensuite.

## 2. Règle absolue : filtre HdF AVANT matérialisation

Départements Hauts-de-France : `02`, `59`, `60`, `62`, `80` (~3 800 communes, `code_region = '32'`).

```sql
WHERE LEFT(code_com, 2) IN ('02', '59', '60', '62', '80')   -- nom de colonne selon la source
```

```python
lf = pl.scan_parquet(path).filter(pl.col("code_commune").str.slice(0, 2).is_in(["02", "59", "60", "62", "80"]))
```

## 3. Conventions de chargement DuckDB

### 3.1 Codes commune : toujours VARCHAR(5)

Lire en texte (`all_varchar=true` en DuckDB, `infer_schema_length=0` en Polars, `dtype=str` en
pandas), puis `::VARCHAR(5)`. `'02001'` casté en entier perd son zéro et la jointure avec
`geographies_communes.code_insee` échoue silencieusement.

### 3.2 Secret statistique et valeurs manquantes

- Parquet OLAP INSEE : le secret est déjà une valeur **NULL** ; le loader pose `secret = TRUE`
  quand les indicateurs principaux sont tous NULL.
- CSV INSEE « classiques » : marqueurs `s`, `nd`, chaîne vide → NULL, jamais 0.

```python
df = pl.read_csv(path, separator=";", encoding="latin1", null_values=["s", "nd", ""],
                 infer_schema_length=0)
```

```sql
SELECT code::VARCHAR(5) AS code_commune, TRY_CAST(valeur AS DOUBLE) AS valeur
FROM read_csv('fichier.csv', delim=';', all_varchar=true, nullstr=['s', 'nd', ''])
```

`nullstr` est une option de `read_csv` uniquement (pas de `read_parquet`).

### 3.3 Séparateur et encodage

CSV INSEE : souvent **latin-1 + `;`** (CLAUDE.md) → le préciser à l'import, convertir en UTF-8.
Vérifier empiriquement avant d'affirmer : `file -bi fichier.csv` ou `head -c 2000 | iconv -f utf-8`
(pas de `chardet`, non déclaré dans `pyproject.toml`). Parquet : pas de problème d'encodage.

### 3.4 Format long (OLAP) → large

Pivot par agrégat conditionnel, cf. `economie_filosofi.py` :

```sql
INSERT INTO economie_filosofi
    (code_commune, annee, taux_pauvrete, niveau_vie_median, d1_niveau_vie, d9_niveau_vie, secret)
SELECT code_com::VARCHAR(5), annee,
       MAX(CASE WHEN clef_json = 'taux_de_pauvrete' THEN valeur END)::DOUBLE,
       MAX(CASE WHEN clef_json = 'revenu_median'    THEN valeur END)::DOUBLE,
       MAX(CASE WHEN clef_json = '1er_decile'       THEN valeur END)::DOUBLE,
       MAX(CASE WHEN clef_json = '9eme_decile'      THEN valeur END)::DOUBLE,
       ( ... IS NULL AND ... IS NULL ) AS secret
FROM read_parquet('data/raw/economie/donnees-insee-olap-hdf.parquet')
WHERE source = 'filosofi_disponible' AND LEFT(code_com, 2) IN ('02','59','60','62','80')
GROUP BY code_com, annee
```

RP : suffixes `_c` et `_p` sont **deux effectifs** (pas des pourcentages) ; les taux sont calculés
dans le loader (voir la docstring de `economie_rp.py`).

## 4. Pattern ETL du projet

1. Tables créées par `create_economie_schema()` (`CREATE TABLE IF NOT EXISTS` + `ALTER ... ADD COLUMN IF NOT EXISTS`).
   Pas de `CREATE OR REPLACE TABLE` dans les loaders.
2. Loader `load_economie_*(con, raw_dir, force=False, ...)` (ex. `load_economie_filosofi`, `load_economie_chomage_eurostat`) :
   téléchargement en cache (`httpx.stream`, `_download_cache`) → `DELETE` des millésimes visés →
   `INSERT ... SELECT` filtré HdF → log des volumes par année.
3. `upsert_metadata(con, "<table>", count, "<source> <millésimes>")` (`etl/_common.py`).
4. Vues recréées par `create_economie_views()` (`CREATE OR REPLACE VIEW`).
5. Orchestration CLI : `uv run python scripts/load_economie.py` (voir `--help`).

## 5. Pièges spécifiques

### Taux de chômage : définitions incompatibles
| Définition | Source | Granularité | Dans le projet |
|---|---|---|---|
| BIT | INSEE / Eurostat | région (NUTS 2) au mieux | `economie_contexte.tx_chomage_bit` |
| Inscrits France Travail | France Travail | communes > 5 000 hab. | non chargé |
| Déclaratif | RP | toutes communes | `economie_rp.tx_chomage_dec` |

Toujours indiquer dans l'UI laquelle est affichée.

### Sirene (si un jour introduit)
Jamais `pl.read_parquet` du stock national (> 2 Go) : `pl.scan_parquet(...).filter(...)` avant `collect()`.

### Communes nouvelles (COG)
Les fusions changent les codes INSEE. `geographies_communes` suit le COG de l'ADMIN-EXPRESS
chargé ; pour une série longue, passer par la table de passage COG INSEE et documenter l'année.

### PLM
Paris/Lyon/Marseille : arrondissements (`75101`…`75120`) vs commune-mère (`75056`). HdF non concerné,
mais vérifier l'échelle avant toute comparaison nationale.

## 6. Nommage

Tables `economie_<thème>` (clé `code_commune VARCHAR(5)` + `annee INTEGER`, RP : `annee_millesime`),
vues `v_<thème>_<grain>`. Existant : `economie_filosofi`, `economie_rp`, `economie_social`,
`economie_emploi_urssaf`, `economie_contexte` ; vues `v_economie_commune`,
`v_croisement_eco_elections`, `v_evolution_economie_hdf`, `v_economie_sociale_commune`,
`v_desindustrialisation_commune`, `v_contexte_hdf_vs_france`.
