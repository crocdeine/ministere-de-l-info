# Architecture Decision Records

Les ADR documentent les décisions d'architecture structurantes : pourquoi ce choix,
quelles alternatives ont été considérées, quelles sont les conséquences.

Un ADR est écrit une fois et ne doit pas être modifié après acceptation. Si une
décision est révisée, un nouvel ADR est créé avec le statut "Remplace 000X".

## Index

| ADR | Titre | Statut |
|-----|-------|--------|
| [0001](0001-duckdb-vs-postgres.md) | DuckDB plutôt que PostgreSQL | Accepté |
| [0002](0002-streamlit-vs-fastapi.md) | Streamlit plutôt que FastAPI + frontend JS | Accepté |
| [0003](0003-uv-vs-pip-poetry.md) | uv plutôt que pip / poetry | Accepté |
| [0004](0004-polars-vs-pandas.md) | Polars prioritaire, Pandas en fallback | Accepté |
| [0005](0005-nuances-et-blocs-officiels.md) | Nomenclature officielle Ministère — 6 blocs | Accepté — partiellement révisé par 0010 |
| [0006](0006-module-economie-sources-et-schema.md) | Module Économie — sources, indicateurs et schéma DuckDB | Accepté (note d'exécution 2026-09-24) |
| [0007](0007-module-legislatif-perimetre-et-sources.md) | Module Législatif — périmètre national, sources Datan + data.senat.fr | Accepté (rédigé a posteriori le 2026-09-24) |
| [0008](0008-economie-sources-complementaires.md) | Module Économie — sources complémentaires CNAF, DREES, URSSAF, Eurostat | Accepté (rédigé a posteriori le 2026-09-24) |
| [0009](0009-design-system-et-navigation.md) | Design system et navigation `st.navigation()` / `st.Page()` | Accepté (rédigé a posteriori le 2026-09-24) |
| [0010](0010-revision-nuances-et-blocs.md) | Révision des classements nuances → blocs : grilles 2020/2023/2026, doctrine, reclassements | Accepté — révise 0005 |

## Format

Chaque ADR suit la structure :

- **Contexte** — la question posée et les contraintes
- **Décision** — le choix retenu en une ou deux phrases
- **Alternatives considérées** — les options écartées et pourquoi
- **Conséquences** — positives, négatives, réversibilité

Les ADR rétroactifs (0007 à 0009) ajoutent une section **Points ouverts** : incohérences
constatées à la rédaction, signalées sans être tranchées.

Un ADR accepté n'est pas réécrit ; un constat d'écart entre décision et réalisation est
ajouté en fin de fichier sous forme de « Note d'exécution » datée (cas de l'ADR-0006).
Constat (non corrigé) : l'ADR-0005 a été étendu deux fois en Phase D par des sections
d'application (législatives, municipales), ce qui s'écarte de la règle de non-modification.
