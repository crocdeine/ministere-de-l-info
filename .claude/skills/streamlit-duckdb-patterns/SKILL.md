---
name: streamlit-duckdb-patterns
description: Patterns d'architecture Streamlit + DuckDB pour ministere-de-l-info. À charger pour toute tâche UI Streamlit du projet : nouvelle page, optimisation de cache, performance, visualisation Folium dans Streamlit, requêtes DuckDB depuis pages Streamlit, croisement économie/élections, gestion valeurs manquantes dans l'UI, carte choroplèthe communale HdF.
---

# Streamlit + DuckDB : patterns du projet

> Vérifié contre le code au 2026-09-24 (`app.py`, `pages/`, `src/ministere_de_l_info/pages/`,
> `viz/*_queries.py`). Modèles de référence : `viz/economie_queries.py`, `pages/economie.py`.

## 1. Connexion DuckDB depuis Streamlit

**Règle** : lecture seule depuis l'UI. Écriture uniquement dans les scripts ETL.

Pattern standard des modules `viz/*_queries.py` : connexion courte, ouverte **dans** une fonction
`@st.cache_data`, fermée dans `finally`. Le cache porte sur le résultat, pas sur la connexion.

```python
from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

DB_PATH: Path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"


def _open_ro() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")  # nécessaire pour ST_AsGeoJSON
    return con


@st.cache_data(ttl=60)
def is_data_loaded() -> bool:
    con = _open_ro()
    try:
        return con.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0] > 0
    finally:
        con.close()
```

`parents[3]` : depuis `src/ministere_de_l_info/viz/<fichier>.py`, remonte à la racine.
Exception historique : `pages/1_📍_Géographie.py` garde une connexion partagée `@st.cache_resource`.
Chaque page vérifie la présence des données (`is_data_loaded()`) et affiche un message clair sinon.

## 2. Cache des requêtes

| Cas | Décorateur | Usage dans le projet |
|---|---|---|
| Test de présence des données | `@st.cache_data(ttl=60)` | `is_data_loaded()` |
| Requête → DataFrame Polars | `@st.cache_data(ttl=3600)` | toutes les `get_*()` ; `show_spinner="…"` pour les longues |
| Connexion partagée | `@st.cache_resource` | Géographie uniquement |
| CSS | aucun | `_theme._load_css()` relu à chaque rerun (volontaire) |

Arguments des fonctions cachées : types hashables (`int`, `str`, `tuple`), pas de DataFrame.

## 3. DuckDB → DataFrame

```python
df: pl.DataFrame = con.execute("SELECT ... WHERE annee = ?", [annee]).pl()  # prioritaire
df_pd = con.execute("SELECT ...").df()  # seulement si l'API aval l'exige (folium.Choropleth)
```

SQL paramétré (`?`). Si un nom de colonne doit être injecté (indicateur choisi), le valider contre
une liste blanche (`_INDICATEURS_VALIDES`) avant la f-string.

## 4. Cartes Folium

Les géométries sont **pré-simplifiées en base** (`geometry_simplified_communal`, `_circo`,
`_epci`, `_national`...) et sérialisées en SQL — pas de GeoPandas ni de `simplify()` à l'affichage.
La clé commune des tables géo est `code_insee` (pas `code_commune`) ; filtre HdF = `code_region = '32'`.

```python
@st.cache_data(ttl=3600, show_spinner="Chargement des données communales…")
def get_scores_commune(annee: int, indicateur: str) -> pl.DataFrame:
    if indicateur not in _INDICATEURS_VALIDES:
        raise ValueError(f"Indicateur inconnu : {indicateur}")
    con = _open_ro()
    try:
        return con.execute(f"""
            SELECT gc.code_insee AS code_commune, gc.nom AS nom_commune,
                   v.{indicateur} AS valeur, COALESCE(v.secret_partiel, FALSE) AS secret,
                   ST_AsGeoJSON(gc.geometry_simplified_communal) AS geojson
            FROM geographies_communes gc
            LEFT JOIN v_economie_commune v
                ON gc.code_insee = v.code_commune AND v.annee = ?
            WHERE gc.code_region = '32'
        """, [annee]).pl()
    finally:
        con.close()
```

Construction de la carte : voir `pages/economie.py::_make_choropleth` (FeatureCollection bâtie
depuis la colonne `geojson`, `folium.Choropleth` + `GeoJsonTooltip`) et `viz/maps_elections.py`
(bloc dominant, couleurs issues de `_blocs_politiques.COULEURS_BLOCS`).

**Règles Folium** :
- géométries en EPSG:4326 (stockage) ; si un GeoDataFrame intervient : `gdf.to_crs(epsg=4326)` avant Folium ;
- `folium.Map(location=[50.3, 2.9], zoom_start=8)` pour les Hauts-de-France ;
- `nan_fill_color="#CCCCCC"` pour secret statistique / valeur manquante ;
- `st_folium(m, use_container_width=True, height=540, returned_objects=[])` sauf besoin d'interaction.

## 5. Structure d'une page

`app.py` appelle **une seule fois** `st.set_page_config`, `inject_css()` et `st.navigation()`.
Les fichiers de `pages/` ne doivent pas rappeler `st.set_page_config`.

```python
# pages/4_📊_Économie.py
"""Page Économie — ministere-de-l-info."""

from ministere_de_l_info.pages.economie import render

render()
```

```python
# src/ministere_de_l_info/pages/economie.py (extrait)
from ministere_de_l_info._theme import render_page_header

def render() -> None:
    if not is_data_loaded():
        st.warning("Données économiques non chargées. Lancez :")
        st.code("uv run python scripts/load_economie.py")
        return
    render_page_header(icon="bar_chart", title="Économie", subtitle="Hauts-de-France")
    tab_carte, tab_evolution, tab_croisement, tab_industrie = st.tabs([...])
    with tab_carte:
        _render_carte_tab()
    ...
```

Ajouter une page = créer `src/.../pages/<module>.py::render()`, un fichier mince dans `pages/`,
et une entrée `st.Page(..., icon=":material/<nom>:", url_path="<slug>")` dans `app.py`
(changement de navigation → validation Mathias).

Indicateurs économiques réels (`viz/economie_queries.py`) : `taux_pauvrete`, `niveau_vie_median`,
`tx_chomage_dec`, `part_ouvriers_employes`, `part_emploi_industriel`, `part_logements_sociaux`,
`nb_foyers_rsa`, `apl_medecins` ; contexte Eurostat : `tx_chomage_bit`, `pib_eur_hab`.
Années : lire `get_annees_par_indicateur()`, ne pas coder de plage en dur.

## 6. Croisement économie × élections

Implémenté dans l'onglet « Économie × Élections » (`_render_croisement_tab`) : `px.scatter`
commune par commune, indicateur économique (année n-1) × score d'un bloc à la présidentielle,
via `get_croisement_eco_elections()` (jointure SQL `v_scores_commune_pres` +
`v_participation_commune_pres` + `v_economie_commune` ; la vue `v_croisement_eco_elections`
existe mais n'est pas utilisée par l'UI). Deux cartes côte à côte (`st.columns(2)`) restent
possibles ; la synchronisation du survol entre cartes Folium n'est pas faisable nativement.

## 7. Valeurs manquantes dans l'UI

Secret statistique INSEE (petites communes) et données absentes : afficher « n.d. » ou
« Données non disponibles », **jamais** `None`, `nan`, `NULL` ni 0.

```python
def format_valeur(val: float | None, suffixe: str = "%") -> str:
    if val is None or val != val:  # None ou NaN
        return "Données non disponibles"
    return f"{val:.1f} {suffixe}".replace(".", ",")  # virgule décimale
```

## 8. Performance

- Jointures en SQL DuckDB, jamais en Python.
- Ne sélectionner que les colonnes utiles ; GeoJSON uniquement quand une carte est affichée.
- Données stables : `ttl=3600` ; tests de présence : `ttl=60`.

## 9. Citation des sources

Toujours un `st.caption` : producteur, dataset, millésime, licence, niveau géographique.

```python
st.caption(f"Source : INSEE — Filosofi {annee} | Licence Ouverte v2.0 | Niveau : commune")
st.caption("Sources : INSEE (économie) + Ministère de l'Intérieur via data.gouv.fr (élections)")
```

## 10. Pièges spécifiques

- **Rerun** : tout le script est ré-exécuté à chaque interaction → tout chargement lourd en cache.
- **Couleurs de blocs** : uniquement `_blocs_politiques.py` (alignée sur `--nuance-*` de `custom.css`).
- **Couleurs d'interface** : tokens CSS de `custom.css`, pas de valeurs en dur.
- **`st_folium`** : `returned_objects=[]` pour éviter les reruns parasites.
- **Session cloud** : pas de base → les pages affichent leur message d'absence ; les tests
  d'interface (`tests/test_pages_*.py`, `test_streamlit_smoke.py`) sont majoritairement ignorés.
