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

## Format

Chaque ADR suit la structure :

- **Contexte** — la question posée et les contraintes
- **Décision** — le choix retenu en une ou deux phrases
- **Alternatives considérées** — les options écartées et pourquoi
- **Conséquences** — positives, négatives, réversibilité
