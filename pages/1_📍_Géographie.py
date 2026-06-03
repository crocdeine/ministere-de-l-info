"""Page Géographie — carte choroplèthe multi-niveaux."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info.viz.maps import make_choropleth

st.set_page_config(page_title="Géographie", page_icon="📍", layout="wide")
st.title("📍 Géographie territoriale")

_DB_PATH = Path(__file__).parent.parent / "data" / "ministere.duckdb"

_NIVEAU_LABELS: dict[str, str] = {
    "region": "Régions (18)",
    "departement": "Départements (101)",
    "epci": "Intercommunalités EPCI (~1 265)",
    "arrondissement_municipal": "Arrondissements municipaux (45)",
    "circonscription": "Circonscriptions législatives (559)",
    "commune": "Communes (~35 000) ⚠️",
}

_TABLE_META: dict[str, str] = {
    "region": "geographies_regions",
    "departement": "geographies_departements",
    "epci": "geographies_epci",
    "arrondissement_municipal": "geographies_arrondissements_municipaux",
    "circonscription": "geographies_circonscriptions",
    "commune": "geographies_communes",
}

# Vues population disponibles et clé de jointure
_VUE_POP: dict[str, tuple[str, str]] = {
    "region": ("v_population_region", "code_region"),
    "departement": ("v_population_departement", "code_departement"),
    "epci": ("v_population_epci", "code_epci"),
    "commune": ("v_population_commune", "code_commune"),
}

_TABLE_CODE: dict[str, tuple[str, str]] = {
    "region": ("geographies_regions", "code_insee"),
    "departement": ("geographies_departements", "code_insee"),
    "epci": ("geographies_epci", "code_siren"),
    "arrondissement_municipal": (
        "geographies_arrondissements_municipaux",
        "code_insee",
    ),
    "circonscription": ("geographies_circonscriptions", "code"),
    "commune": ("geographies_communes", "code_insee"),
}

_FILTRE_DEPT_COL: dict[str, str] = {
    "epci": "code_departement_principal",
    "circonscription": "code_departement",
    "commune": "code_departement",
}

_FILTRE_REGION_COL: dict[str, str] = {
    "departement": "code_region",
    "commune": "code_region",
}


def _format_evolution(delta_abs: float | None, delta_pct: float | None) -> str:
    """Formate l'évolution démographique : '↗ +4.2% (+503 260 hab)'."""
    if delta_abs is None or delta_pct is None:
        return "—"
    icon = "↗" if delta_pct > 1.0 else ("↘" if delta_pct < -1.0 else "→")
    abs_val = int(delta_abs)
    abs_str = (f"+{abs_val:,}" if abs_val >= 0 else f"{abs_val:,}").replace(",", " ")
    return f"{icon} {delta_pct:+.1f}% ({abs_str} hab)"


@st.cache_resource
def _get_con() -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB partagée en lecture seule."""
    con = duckdb.connect(str(_DB_PATH), read_only=True)
    con.execute("LOAD spatial;")
    return con


if not _DB_PATH.exists():
    st.error(
        "Base de données absente. Lancez d'abord :\n\n"
        "```bash\nuv run python scripts/etl_regions.py\n```"
    )
    st.stop()

con = _get_con()

# ── Sidebar : paramètres ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Paramètres")

    niveau = st.selectbox(
        "Niveau territorial",
        options=list(_NIVEAU_LABELS),
        format_func=lambda x: _NIVEAU_LABELS[x],
    )

    annees_dispo = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT annee FROM populations ORDER BY annee DESC"
        ).fetchall()
    ]
    if not annees_dispo:
        st.warning("Aucune donnée population — carte en mode contours.")
        annee = 2023
    else:
        annee = st.selectbox(
            "Année de recensement (INSEE)",
            annees_dispo,
            help="Population municipale (PMUN) issue de DS_POPULATIONS_HISTORIQUES",
        )
        st.caption(
            f"📊 {len(annees_dispo)} millésime(s) disponible(s) : "
            f"{', '.join(str(a) for a in sorted(annees_dispo))}"
        )

    # Comparaison inter-millésimes (contextuelle)
    annee_ref: int | None = None
    indicateur_carte = "Population absolue"
    if len(annees_dispo) > 1 and niveau in _VUE_POP:
        annees_compare = sorted(a for a in annees_dispo if a != annee)
        annee_ref = st.selectbox(
            "Comparer avec",
            [None, *annees_compare],
            format_func=lambda x: "Aucune comparaison" if x is None else str(x),
            help="Affiche l'évolution démographique par rapport à l'année choisie",
        )
        if annee_ref is not None:
            indicateur_carte = st.radio(
                "Indicateur cartographique",
                ["Population absolue", "Évolution démographique"],
                horizontal=True,
            )

    # Filtre département (contextuel)
    filtre_departement: str | None = None
    if niveau in _FILTRE_DEPT_COL:
        depts = con.execute(
            "SELECT code_insee, nom FROM geographies_departements ORDER BY code_insee"
        ).fetchall()
        dept_labels = {d[0]: f"{d[0]} — {d[1]}" for d in depts}

        if niveau == "commune":
            st.warning("⚠️ Un département doit être sélectionné pour les communes.")
            filtre_departement = st.selectbox(
                "Département",
                options=[d[0] for d in depts],
                format_func=lambda x: dept_labels.get(x, x),
            )
        else:
            choix = st.selectbox(
                "Département (optionnel)",
                options=[None] + [d[0] for d in depts],
                format_func=lambda x: "Tous" if x is None else dept_labels.get(x, x),
            )
            filtre_departement = choix

    # Filtre région (contextuel)
    filtre_region: str | None = None
    if niveau in _FILTRE_REGION_COL:
        regions = con.execute(
            "SELECT code_insee, nom FROM geographies_regions ORDER BY nom"
        ).fetchall()
        region_labels = {r[0]: r[1] for r in regions}
        choix = st.selectbox(
            "Région (optionnelle)",
            options=[None] + [r[0] for r in regions],
            format_func=lambda x: "Toutes" if x is None else region_labels.get(x, x),
        )
        filtre_region = choix

    with st.expander("Options avancées"):
        mode = st.radio("Mode de rendu", ["auto", "choropleth", "contours"], index=0)

# ── Carte ────────────────────────────────────────────────────────────────────

_a_population = niveau in _VUE_POP and mode != "contours"
_mode_evolution = indicateur_carte == "Évolution démographique" and annee_ref is not None

if _mode_evolution:
    titre_carte = f"Évolution démographique {annee_ref} → {annee}"
elif _a_population:
    titre_carte = f"Population municipale {annee}"
else:
    titre_carte = "Contours territoriaux"

try:
    carte = make_choropleth(
        con,
        niveau=niveau,
        annee=annee,
        annee_ref=annee_ref if _mode_evolution else None,
        filtre_departement=filtre_departement,
        filtre_region=filtre_region,
        titre=titre_carte,
        mode=mode,
    )
    st_folium(carte, width="100%", height=600, returned_objects=[])
except ValueError as e:
    st.error(f"Paramètres invalides : {e}")
    st.stop()
except RuntimeError as e:
    st.warning(str(e))
    st.stop()
except Exception as e:
    st.error(f"Erreur inattendue : {e}")
    raise

# ── Métadonnée ───────────────────────────────────────────────────────────────

meta = con.execute(
    "SELECT loaded_at, source_version, row_count FROM _etl_metadata WHERE table_name = ?",
    [_TABLE_META[niveau]],
).fetchone()

if meta:
    loaded_at, source, row_count = meta
    if _mode_evolution:
        pop_info = f"Évolution {annee_ref}→{annee} (INSEE) · "
    elif _a_population:
        pop_info = f"Population municipale {annee} (INSEE) · "
    else:
        pop_info = ""
    st.caption(f"📊 {row_count:,} entités · {pop_info}Géométries : data.geopf.fr")
else:
    st.caption("⚠️ Aucune métadonnée ETL pour ce niveau.")

# ── Tableau de données ────────────────────────────────────────────────────────

st.divider()

if niveau in _VUE_POP:
    vue, vue_code = _VUE_POP[niveau]
    table, code_col = _TABLE_CODE[niveau]

    # Filtres géographiques communs
    where: list[str] = []
    geo_params: list = []
    dept_col = _FILTRE_DEPT_COL.get(niveau)
    if filtre_departement and dept_col:
        where.append(f"g.{dept_col} = ?")
        geo_params.append(filtre_departement)
    region_col = _FILTRE_REGION_COL.get(niveau)
    if filtre_region and region_col:
        where.append(f"g.{region_col} = ?")
        geo_params.append(filtre_region)
    where_sql = f"AND {' AND '.join(where)}" if where else ""

    if annee_ref is not None:
        # Double JOIN millesime — ajoute une colonne evolution
        rows = con.execute(  # noqa: S608
            f"SELECT g.{code_col} AS code, g.nom,"
            f" COALESCE(p_main.population_municipale, 0) AS pop_main,"
            f" (p_main.population_municipale - p_ref.population_municipale) AS delta_abs,"
            f" 100.0 * (p_main.population_municipale - p_ref.population_municipale)"
            f" / NULLIF(p_ref.population_municipale, 0) AS delta_pct"
            f" FROM {table} g"
            f" LEFT JOIN {vue} p_main"
            f"   ON g.{code_col} = p_main.{vue_code} AND p_main.annee = ?"
            f" LEFT JOIN {vue} p_ref"
            f"   ON g.{code_col} = p_ref.{vue_code} AND p_ref.annee = ?"
            f" {where_sql}"
            f" ORDER BY pop_main DESC NULLS LAST LIMIT 200",
            [annee, annee_ref, *geo_params],
        ).fetchall()
        df = pl.DataFrame(
            {
                "Code": [r[0] for r in rows],
                "Nom": [r[1] for r in rows],
                f"Population municipale {annee}": [
                    f"{r[2]:,}".replace(",", " ") if r[2] else "—" for r in rows
                ],
                f"Évolution {annee_ref}→{annee}": [_format_evolution(r[3], r[4]) for r in rows],
            }
        )
    else:
        rows = con.execute(  # noqa: S608
            f"SELECT g.{code_col} AS code, g.nom,"
            f" COALESCE(p.population_municipale, 0) AS pop"
            f" FROM {table} g"
            f" LEFT JOIN {vue} p ON g.{code_col} = p.{vue_code} AND p.annee = ?"
            f" {where_sql}"
            f" ORDER BY pop DESC NULLS LAST LIMIT 200",
            [annee, *geo_params],
        ).fetchall()
        df = pl.DataFrame(
            {
                "Code": [r[0] for r in rows],
                "Nom": [r[1] for r in rows],
                f"Population municipale {annee}": [
                    f"{r[2]:,}".replace(",", " ") if r[2] else "—" for r in rows
                ],
            }
        )
else:
    # ARM ou circonscriptions : pas de population
    table, code_col = _TABLE_CODE[niveau]
    extra_col = "code_commune_mere" if niveau == "arrondissement_municipal" else "code_departement"
    rows = con.execute(  # noqa: S608
        f"SELECT {code_col}, nom, {extra_col} FROM {table} ORDER BY {code_col} LIMIT 200"
    ).fetchall()

    extra_label = "Commune mère" if niveau == "arrondissement_municipal" else "Département"
    df = pl.DataFrame(
        {
            "Code": [r[0] for r in rows],
            "Nom": [r[1] for r in rows],
            extra_label: [r[2] for r in rows],
        }
    )

st.dataframe(df, width="stretch", hide_index=True)
