---
name: streamlit-duckdb-patterns
description: Patterns d'architecture Streamlit + DuckDB pour ministere-de-l-info. À charger pour toute tâche UI Streamlit du projet : nouvelle page, optimisation de cache, performance, visualisation Folium dans Streamlit, requêtes DuckDB depuis pages Streamlit, split screen économie/élections, gestion valeurs manquantes dans l'UI, carte choroplèthe communale HdF.
---

# Streamlit + DuckDB : patterns du projet

## 1. Connexion DuckDB depuis Streamlit

**Règle** : toujours ouvrir en read-only depuis les pages. Écriture uniquement dans les scripts ETL.

```python
import duckdb
import streamlit as st
from pathlib import Path

@st.cache_resource
def _get_con() -> duckdb.DuckDBPyConnection:
    db_path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"
    return duckdb.connect(str(db_path), read_only=True)
```

`parents[3]` : depuis `src/ministere_de_l_info/pages/`, remonter à la racine du projet.

## 2. Cache des requêtes

| Cas | Décorateur | Raison |
|---|---|---|
| Connexion DuckDB | `@st.cache_resource` | Singleton, une seule instance |
| Requête → DataFrame | `@st.cache_data` | Sérialisable, par arguments |
| GeoDataFrame Folium | `@st.cache_data` + `hash_funcs` | GeoPandas non sérialisable nativement |

```python
import polars as pl

@st.cache_data(ttl=3600)
def get_economie_commune(code_commune: str) -> pl.DataFrame:
    con = _get_con()
    return con.execute(
        "SELECT * FROM v_economie_commune WHERE code_commune = ?",
        [code_commune],
    ).pl()


@st.cache_data
def get_filosofi_hdf(annee: int) -> pl.DataFrame:
    con = _get_con()
    return con.execute(
        "SELECT code_commune, taux_pauvrete, niveau_vie_median "
        "FROM economie_filosofi WHERE annee = ?",
        [annee],
    ).pl()
```

## 3. DuckDB → DataFrame dans les pages

```python
# Polars (prioritaire)
df: pl.DataFrame = con.execute("SELECT ...").pl()

# Pandas (fallback si Plotly Express l'exige, ou st.dataframe avec filtre)
df_pd = con.execute("SELECT ...").df()

# ÉVITER sur gros volumes
rows = con.execute("SELECT ...").fetchall()  # liste de tuples → pas de vectorisation
```

## 4. Folium dans Streamlit

```python
import geopandas as gpd
import folium
from streamlit_folium import st_folium

@st.cache_data
def get_geo_hdf() -> gpd.GeoDataFrame:
    con = _get_con()
    gdf = gpd.GeoDataFrame(
        con.execute(
            "SELECT code_commune, nom, geom FROM communes "
            "WHERE LEFT(code_commune, 2) IN ('02','59','60','62','80')"
        ).df(),
        geometry="geom",
        crs="EPSG:4326",
    )
    # Simplifier pour la performance — niveau communal HdF
    gdf["geometry"] = gdf["geometry"].simplify(0.0005)
    return gdf


def render_carte_choropleth(gdf: gpd.GeoDataFrame, colonne: str) -> None:
    # Toujours convertir en EPSG:4326 avant Folium
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    m = folium.Map(location=[50.3, 2.9], zoom_start=8)
    folium.Choropleth(
        geo_data=gdf.__geo_interface__,
        data=gdf,
        columns=["code_commune", colonne],
        key_on="feature.properties.code_commune",
        fill_color="YlOrRd",
        nan_fill_color="#CCCCCC",  # gris pour secret statistique
        legend_name=colonne,
    ).add_to(m)

    st_folium(m, use_container_width=True, height=500)
```

**Règles Folium** :
- `use_container_width=True` obligatoire
- `gdf.simplify(0.0005)` pour HdF niveau communal (0.001 si national)
- Convertir en EPSG:4326 **avant** tout appel Folium
- `nan_fill_color="#CCCCCC"` pour les valeurs manquantes (secret statistique)

## 5. Pattern de page Streamlit — module Économie

Structure standard à suivre pour [pages/4_💶_Économie.py](../pages/4_💶_Économie.py) :

```python
import streamlit as st
from src.ministere_de_l_info.pages.economie import render

st.set_page_config(page_title="Économie — Hauts-de-France", layout="wide")
render()
```

Et dans [src/ministere_de_l_info/pages/economie.py](../src/ministere_de_l_info/pages/economie.py) :

```python
INDICATEURS = {
    "taux_pauvrete": "Taux de pauvreté (%)",
    "niveau_vie_median": "Niveau de vie médian (€/an)",
    "taux_chomage_rp": "Taux de chômage déclaratif (%)",
    "part_ouvriers": "Part d'ouvriers (%)",
}
ANNEES = list(range(2012, 2024))


def render() -> None:
    st.header("Économie — Hauts-de-France")

    col1, col2 = st.columns([1, 3])
    with col1:
        indicateur = st.selectbox("Indicateur", list(INDICATEURS.keys()),
                                  format_func=lambda k: INDICATEURS[k])
        annee = st.selectbox("Année", ANNEES, index=len(ANNEES) - 1)

    with col2:
        # Carte choroplèthe ici
        ...
```

## 6. Split screen économie × élections

Pattern pour la comparaison croisée (fonctionnalité différenciante du projet) :

```python
def render_split_screen(annee: int, scrutin_id: str) -> None:
    col_eco, col_elect = st.columns(2)

    with col_eco:
        st.subheader("Économie")
        st.caption(f"Taux de pauvreté — Filosofi {annee}")
        # carte économique

    with col_elect:
        st.subheader("Résultats électoraux")
        st.caption(f"Scrutin : {scrutin_id}")
        # carte électorale (réutiliser maps_elections.py)
```

Synchronisation du survol : non implémentée nativement dans Folium/Streamlit. Alternative : utiliser un `st.selectbox` de commune et afficher les deux cartes + métriques côte à côte.

## 7. Gestion des valeurs manquantes dans l'UI

**Secret statistique INSEE** : communes < 50 ménages (fréquent en Picardie, Thiérache)

```python
# Afficher NULL comme donnée indisponible, jamais comme 0
def format_valeur(val: float | None, suffixe: str = "%") -> str:
    if val is None or (isinstance(val, float) and pl.Series([val]).is_nan().all()):
        return "Données non disponibles"
    return f"{val:.1f} {suffixe}".replace(".", ",")  # virgule décimale française


# Dans un tooltip Folium
tooltip_html = """
<b>{nom}</b><br>
Taux de pauvreté : {taux}<br>
<small style="color:#888">
  {note}
</small>
"""
note = "Secret statistique (commune < 50 ménages)" if pd.isna(taux) else f"Source : Filosofi {annee}"
```

```python
# Dans st.metric
st.metric(
    label="Taux de pauvreté",
    value=format_valeur(taux_pauvrete),
    help="Source : INSEE Filosofi. Seuil : 60% du revenu médian national.",
)
```

**Règle** : ne jamais afficher `None`, `nan`, ou `NULL` brut à l'utilisateur.

## 8. Performance et mémoire

```python
# Chargement géographique une seule fois (singleton via cache_resource)
# Données économiques : cache_data avec ttl=3600 (données stables)
# Jamais de jointure Python — toujours faire les jointures en SQL DuckDB

# Jointure eco + geo dans DuckDB (pattern recommandé)
@st.cache_data
def get_filosofi_geo(annee: int) -> dict:
    con = _get_con()
    return con.execute("""
        SELECT c.code_commune, c.nom, c.geom,
               f.taux_pauvrete, f.niveau_vie_median
        FROM communes c
        LEFT JOIN economie_filosofi f
            ON c.code_commune = f.code_commune AND f.annee = ?
        WHERE LEFT(c.code_commune, 2) IN ('02','59','60','62','80')
    """, [annee]).fetchdf()
```

## 9. Citation des sources dans l'UI

Toujours ajouter un footer ou un `st.caption` :

```python
st.caption(
    f"Source : INSEE — Filosofi {annee} | "
    "Licence Ouverte v2.0 | "
    "Niveau géographique : commune"
)
```

Pour la superposition économie/élections :
```python
st.caption(
    "Sources : INSEE Filosofi (revenus) + "
    "Ministère de l'Intérieur via data.gouv.fr (élections)"
)
```

## 10. Pièges Streamlit spécifiques au projet

- **Rerun** : Streamlit ré-exécute tout le script à chaque interaction — tout chargement non caché sera re-déclenché
- **GeoDataFrame** : non sérialisable directement par `@st.cache_data` → wrapper via `hash_funcs` ou retourner un dict GeoJSON
- **Connexion DuckDB** : une seule instance via `@st.cache_resource` — ne jamais ouvrir/fermer dans une fonction appelée souvent
- **st_folium** : retourne un dict avec la dernière interaction (clic, zoom) — utiliser `returned_objects=[]` si non nécessaire pour éviter les reruns parasites

```python
# Éviter les reruns parasites
result = st_folium(m, use_container_width=True, returned_objects=[])
```
