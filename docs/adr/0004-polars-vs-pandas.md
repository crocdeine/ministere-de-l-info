# 0004 — Polars prioritaire, Pandas en fallback

Date : 2026-05-27
Statut : Accepté

## Contexte

Le projet manipule des données tabulaires à plusieurs étapes : parsing des réponses
API (GeoJSON, JSON INSEE), transformations avant insertion DuckDB, et éventuellement
traitement dans les pages Streamlit. Deux bibliothèques coexistent dans l'écosystème
Python data :

- **Pandas** — référence historique, utilisée par GeoPandas, Streamlit, et la plupart
  des bibliothèques tierces
- **Polars** — bibliothèque colonnaire écrite en Rust, API expression-based, parue en
  2020, montée en maturité depuis 2023

La contrainte réelle du projet : **GeoPandas est construit sur Pandas** et ne peut pas
être remplacé pour le traitement des géométries. Pandas reste donc une dépendance
transitive incontournable.

## Décision

Polars est l'outil prioritaire pour tout traitement tabulaire pur (parsing, filtrage,
agrégation). Pandas est accepté uniquement quand une bibliothèque tierce l'impose
explicitement (GeoPandas, ou tout composant Streamlit qui requiert un `pd.DataFrame`).
Ce compromis est inscrit dans `CLAUDE.md` : _"Polars prioritaire, Pandas en fallback
seulement"_.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **Pandas uniquement** | API mutative, inférences de types silencieuses, GIL Python (pas de parallélisme natif), performances inférieures sur les tables 30 000+ lignes |
| **Polars uniquement** | Impossible : GeoPandas dépend de Pandas ; certains composants Streamlit renvoient des `pd.DataFrame` |
| **DuckDB comme seul outil de transformation** | Pertinent pour les transformations SQL, mais pas pour le parsing des réponses API JSON/GeoJSON avant insertion |
| **Arrow (PyArrow) pur** | API bas niveau, peu ergonomique pour des transformations métier |

## Conséquences

### Positives

- **Performances** : Polars est 5–20× plus rapide que Pandas sur les opérations
  colonnaires (parsing, groupby, join) grâce à l'exécution parallèle et au moteur
  Arrow natif
- **Immutabilité par défaut** : les expressions Polars (`pl.col(...)`) ne modifient
  pas en place — moins de bugs silencieux liés aux effets de bord
- **Types stricts** : Polars refuse les cast implicites ; les erreurs de type sont
  détectées tôt
- **Interopérabilité DuckDB** : DuckDB peut consommer directement des `pl.DataFrame`
  via PyArrow — pas de conversion coûteuse

### Négatives

- **Deux bibliothèques en parallèle** : un développeur doit connaître les deux APIs.
  Les conversions `pl.DataFrame.to_pandas()` / `pd.DataFrame` → Polars introduisent
  une friction
- **GeoPandas impose Pandas** : les pipelines géospatiales (lecture WFS, reprojection,
  simplification) restent en Pandas/GeoPandas, ce qui crée une frontière dans le code
- **Moins de ressources francophones** : Polars est moins documenté en français que
  Pandas ; les exemples INSEE / data.gouv.fr utilisent majoritairement Pandas
- **API encore en évolution** : certaines fonctionnalités Polars changent entre
  versions mineures (breaking changes plus fréquents qu'avec Pandas)

### Réversibilité

Facile dans les deux sens : `pl.DataFrame.to_pandas()` et `pd.DataFrame.to_polars()`
existent. La décision de révision (revenir à Pandas only) serait motivée par une
multiplication excessive des conversions ou par l'introduction d'une bibliothèque
centrale qui ne supporte pas Polars.
