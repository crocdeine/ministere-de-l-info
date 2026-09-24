# Échantillon de la base pour tests hermétiques

Contenu attendu (généré, puis commité) :

- un fichier `<table>.parquet` par table ;
- `manifest.json` : date de génération, version DuckDB, département, scrutins retenus,
  filtre SQL appliqué à chaque table, colonnes, nombres de lignes, vues de la base source.

## Provenance

Extrait **réel** de `data/ministere.duckdb`, limité au département de la Somme (80).
Aucune donnée n'est inventée. Les transformations sont les suivantes :

- les géométries sont simplifiées (tolérance 0,002° par défaut, EPSG:4326) et stockées en WKB ;
  la colonne `geometry` de l'échantillon n'est donc **pas** en pleine résolution ;
- les résultats électoraux sont limités à 12 scrutins (liste dans `manifest.json`) ;
- l'emploi URSSAF est limité aux secteurs industriels, les seuls utilisés par le code ;
- les tables techniques `_etl_metadata` et `_schema_version` ne sont pas exportées.

Sources et licences : voir `docs/data-sources.md`.

## Générer ou régénérer (sur le Mac, base complète présente)

```bash
uv run python scripts/export_sample_db.py
git add tests/fixtures/sample/
```

Options : `--departement`, `--scrutins` (liste d'identifiants ou `tous`), `--tolerance`,
`--max-mo` (5 Mo par défaut ; le script échoue sans rien écrire au-delà), `--source`.
La base source est lue en lecture seule (chemin : `MINISTERE_DB_PATH` ou `data/ministere.duckdb`).

Régénérer après toute évolution de schéma ou de classement des nuances : l'échantillon est un
instantané de la base, pas du code. Un écart (colonne, table ou vue présente dans l'échantillon
mais pas créée par le code) déclenche l'avertissement `EcartSchemaEchantillon` à la reconstruction.

## Utilisation dans les tests

Voir `tests/fixtures/sample_db.py` et les fixtures `echantillon_con` / `echantillon_db_path`
de `tests/conftest.py`. Sans échantillon, les tests concernés sont ignorés avec un message
explicite.
