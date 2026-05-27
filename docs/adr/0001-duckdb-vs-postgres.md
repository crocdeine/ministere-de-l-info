# 0001 — DuckDB plutôt que PostgreSQL

Date : 2026-05-27
Statut : Accepté

## Contexte

Le projet nécessite une base de données capable de stocker des géométries (GeoJSON
simplifiées à plusieurs résolutions), des tables analytiques volumineuses (34 877
communes × N millésimes de population), et d'exécuter des requêtes SQL avec jointures
et agrégations complexes.

L'application tourne sur une seule machine (Mac mini + OrbStack), sans accès
concurrent multi-utilisateur. L'ETL est un processus batch ponctuel ; l'application
Streamlit lit la base en lecture seule via une connexion unique par session.

Le projet est piloté par un développeur solo avec une contrainte de complexité opéra-
tionnelle minimale (pas de serveur à administrer, pas de service à démarrer).

## Décision

Utiliser DuckDB avec l'extension spatial comme base analytique principale, stockée
dans un fichier unique `data/ministere.duckdb`.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **PostgreSQL + PostGIS** | Nécessite un serveur persistant (Docker ou natif), une gestion des utilisateurs/rôles, des sauvegardes manuelles. Surcharge opérationnelle injustifiée pour un usage mono-utilisateur. |
| **SQLite + SpatiaLite** | Pas de support natif des requêtes analytiques (window functions, agrégations complexes). Performances nettement inférieures sur les tables 30 000+ lignes. |
| **Fichiers Parquet + Polars** | Pas de SQL spatial natif, pas de jointures multi-tables déclaratives, pas de vues persistantes. Adapté pour du traitement pur, pas pour une base de référence requêtable. |
| **Fichiers GeoJSON bruts** | Pas de requêtes SQL, rechargement complet à chaque accès, pas d'indexation. |

## Conséquences

### Positives

- **Zéro administration** : base = un fichier, copiable, supprimable, versionnable (hors git pour la taille)
- **SQL analytique complet** : window functions, CTEs, agrégations, NULLIF, CASE — même syntaxe que PostgreSQL
- **Extension spatial native** : `ST_AsGeoJSON`, `ST_YMin/XMin/YMax/XMax`, `ST_GeomFromText` sans installation externe
- **Performances excellentes** sur les charges analytiques (colonnaire en mémoire)
- **Connexion in-process** via `duckdb.connect()` : pas de réseau, pas de latence, pas de pool de connexions
- **`@st.cache_resource`** sur la connexion Streamlit suffit pour éviter les reconnexions

### Négatives

- **Pas de concurrence en écriture** : un seul writer à la fois — bloquant si l'ETL tourne pendant que Streamlit lit. Acceptable en usage solo (ETL lancé manuellement avant de démarrer l'app)
- **Pas de triggers, pas de foreign keys enforced** : l'intégrité référentielle est vérifiée en tests, pas par la base
- **Pas de replication / backup automatique** : la base peut être reconstruite depuis l'ETL (source of truth = les API), mais un crash pendant l'ETL laisse la base dans un état partiel

### Réversibilité

Difficile à inverser sans réécriture des loaders ETL et de la couche `viz/`. DuckDB
peut exporter en Parquet ou CSV via `COPY TO`, ce qui faciliterait une migration vers
PostgreSQL si le besoin de concurrence ou de partage réseau apparaît. La décision de
révision serait motivée par un usage multi-utilisateur ou une API REST serveur.
