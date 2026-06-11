---
name: insee-duckdb-loader
description: Conventions de chargement des données INSEE (Filosofi, Recensement de la population, Sirene, BPE) dans DuckDB pour le projet ministere-de-l-info. À charger pour toute tâche impliquant charger données INSEE, ETL économie, Filosofi, données revenus/pauvreté, chômage communal, tissu entreprises, Recensement de la population, Sirene, BPE, données économiques INSEE, taux de pauvreté, niveau de vie, CSP, catégories socioprofessionnelles.
---

# INSEE → DuckDB : conventions de chargement

## 1. Sources prioritaires et leurs caractéristiques

| Source | Indicateurs clés | Granularité | Temporalité | Format préféré |
|---|---|---|---|---|
| **Filosofi** | Revenu médian, taux de pauvreté, déciles | Commune, IRIS, EPCI | Annuelle depuis 2012 | Parquet (data.gouv.fr) |
| **RP (Recensement)** | Taux d'activité, chômage déclaratif, CSP, diplôme | Commune, IRIS, EPCI | Annuelle (millésimes 5 ans) | CSV/Parquet |
| **Sirene** | Tissu d'entreprises, code APE, effectifs, date création | Commune, adresse | Quotidien/Mensuel (stock) | Parquet (data.gouv.fr) |
| **BPE** | Équipements (commerces, santé, écoles) | Commune, localisation | Annuelle | CSV/Parquet |

**Source d'accès** : `https://www.insee.fr/fr/statistiques/` et `https://www.data.gouv.fr/`

## 2. Règle absolue : filtre HdF AVANT chargement mémoire

Les bases nationales (Sirene >2 Go, RP plusieurs centaines de Mo) ne doivent **jamais** être chargées intégralement.

**Codes département Hauts-de-France** : `02` (Aisne), `59` (Nord), `60` (Oise), `62` (Pas-de-Calais), `80` (Somme)
**Communes cibles** : ~3 782 communes

```sql
-- Filtre pushdown DuckDB (sur Parquet distant ou local)
WHERE LEFT(code_commune, 2) IN ('02', '59', '60', '62', '80')
```

```python
# Filtre Polars LazyFrame (équivalent)
.filter(
    pl.col("code_commune").str.starts_with("02")
    | pl.col("code_commune").str.starts_with("59")
    | pl.col("code_commune").str.starts_with("60")
    | pl.col("code_commune").str.starts_with("62")
    | pl.col("code_commune").str.starts_with("80")
)
```

## 3. Conventions de chargement DuckDB

### 3.1 Code commune : toujours VARCHAR(5)

```sql
-- TOUJOURS caster en VARCHAR, JAMAIS laisser inférer en INTEGER
code_commune::VARCHAR AS code_commune

-- Raison : '02001' (Aisne) perd son zéro initial si casté en INT
-- La jointure avec la table communes (code_commune VARCHAR(5)) échoue silencieusement
```

### 3.2 Secret statistique et valeurs manquantes

INSEE utilise `'s'` (secret statistique) et `'nd'` (non disponible) dans les colonnes numériques.

```python
# Polars : remplacer avant cast
df = pl.read_csv(
    "filosofi.csv",
    separator=";",
    null_values=["s", "nd", ""],
    infer_schema_length=0,  # tout en String d'abord
)
# Puis cast les colonnes numériques
df = df.with_columns([
    pl.col("taux_pauvrete").cast(pl.Float64, strict=False),
    pl.col("niveau_vie_median").cast(pl.Float64, strict=False),
])
```

```sql
-- DuckDB read_csv avec nullstr
CREATE TABLE economie_filosofi AS
SELECT
    code_commune::VARCHAR AS code_commune,
    TRY_CAST(taux_pauvrete AS DOUBLE) AS taux_pauvrete,
    TRY_CAST(niveau_vie_median AS DOUBLE) AS niveau_vie_median
FROM read_csv(
    'filosofi_*.csv',
    delim=';',
    nullstr=['s', 'nd'],
    all_varchar=true
)
WHERE LEFT(code_commune, 2) IN ('02', '59', '60', '62', '80');
```

### 3.3 Séparateur et encodage

| Source | Séparateur | Encodage | Remarque |
|---|---|---|---|
| Filosofi CSV | `;` | UTF-8 (vérifier) | Vérifier empiriquement avant d'affirmer UTF-8 |
| RP CSV | `;` | UTF-8 (vérifier) | Certains millésimes anciens en latin-1 |
| Sirene CSV | `;` | UTF-8 | Stable |
| BPE CSV | `;` | UTF-8 | Stable |

**Règle** : ne jamais supposer UTF-8 sans vérification sur les fichiers de l'année en cours.

```python
# Vérification encodage
import chardet
with open("fichier.csv", "rb") as f:
    result = chardet.detect(f.read(100_000))
print(result["encoding"])  # Doit afficher 'UTF-8' ou 'ISO-8859-1'
```

### 3.4 Préférer Parquet quand disponible

```python
# Parquet = pas de problème d'encodage, pas de séparateur, pushdown natif
con.execute("""
    CREATE TABLE economie_filosofi AS
    SELECT *
    FROM read_parquet('https://..../filosofi_communes.parquet')
    WHERE LEFT(code_commune, 2) IN ('02', '59', '60', '62', '80')
""")
```

## 4. Pattern ETL recommandé (Filosofi HdF complet)

```python
import duckdb
import polars as pl
from pathlib import Path

def load_filosofi_hdf(con: duckdb.DuckDBPyConnection, parquet_path: str) -> None:
    """Charge Filosofi filtré HdF dans DuckDB."""
    DEPTS_HDF = ("02", "59", "60", "62", "80")
    filtre = " OR ".join(f"LEFT(code_commune, 2) = '{d}'" for d in DEPTS_HDF)

    con.execute(f"""
        CREATE OR REPLACE TABLE economie_filosofi AS
        SELECT
            code_commune::VARCHAR(5) AS code_commune,
            annee::INTEGER AS annee,
            TRY_CAST(taux_pauvrete AS DOUBLE) AS taux_pauvrete,
            TRY_CAST(niveau_vie_median AS DOUBLE) AS niveau_vie_median,
            TRY_CAST(niveau_vie_d1 AS DOUBLE) AS niveau_vie_d1,
            TRY_CAST(niveau_vie_d9 AS DOUBLE) AS niveau_vie_d9
        FROM read_parquet('{parquet_path}', nullstr=['s', 'nd'])
        WHERE {filtre}
    """)
```

## 5. Pièges spécifiques

### Sirene : filtre IMPÉRATIF
```python
# JAMAIS :
df = pl.read_parquet("sirene_stock_national.parquet")  # >2 Go RAM

# TOUJOURS :
df = pl.scan_parquet("sirene_stock_national.parquet").filter(
    pl.col("code_commune_etablissement").str.starts_with("02")
    | pl.col("code_commune_etablissement").str.starts_with("59")
    # ... etc.
).collect()
```

### Taux de chômage : 3 définitions incompatibles
| Définition | Source | Granularité communale | Notes |
|---|---|---|---|
| BIT (officiel) | INSEE | ❌ Zone d'emploi minimum | Pour comparaisons internationales |
| Inscrits France Travail | France Travail | ⚠️ Communes >5 000 hab. seulement | Absent pour petites communes HdF |
| Déclaratif | Recensement RP | ✅ Toutes communes | Seule source exhaustive communale |

**Décision éditoriale à documenter dans l'UI** : toujours indiquer laquelle est affichée.

### Communes nouvelles (COG)
- Les fusions de communes changent les codes INSEE chaque année
- Pour séries temporelles : joindre via table de correspondance COG INSEE annuelle
- La table `communes` du projet suit le COG d'une année de référence à préciser

### PLM (Paris, Lyon, Marseille)
- Données parfois par arrondissement (`75101`→`75120`), parfois par commune-mère (`75056`)
- Vérifier l'échelle source avant jointure
- HdF : non concerné directement, mais attention si comparaisons nationales

## 6. Table de compatibilité

| Source | Format prioritaire | Encodage attendu | read_* DuckDB | Nullstr | Filtre HdF |
|---|---|---|---|---|---|
| Filosofi communes | Parquet | n/a | `read_parquet` | `['s', 'nd']` | `LEFT(code_commune, 2)` |
| RP tableaux | CSV/Parquet | UTF-8 (vérifier) | `read_csv` / `read_parquet` | `['s', 'nd']` | `LEFT(code_commune, 2)` |
| Sirene stock | Parquet | n/a | `read_parquet` (via `scan_parquet`) | — | **IMPÉRATIF avant collect** |
| BPE | CSV/Parquet | UTF-8 | `read_csv` / `read_parquet` | — | `LEFT(depcom, 2)` |

## 7. Nommage des tables DuckDB économie

Convention à respecter (cohérence avec les tables électorales existantes) :

```
economie_filosofi         → Revenus et pauvreté par commune/an
economie_rp_csp           → CSP et taux d'activité par commune/an
economie_rp_diplome       → Diplôme par commune/an
economie_sirene           → Tissu entreprises agrégé par commune
v_economie_commune        → Vue agrégée multi-sources par commune (à créer)
```
