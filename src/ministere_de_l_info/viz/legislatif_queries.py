"""Requêtes DuckDB cachées pour la page Législatif (Phase F3).

Fonctions exportées
-------------------
- is_data_loaded()               : True si leg_elus contient des données AN et SENAT
- get_chambres()                 : ['AN', 'SENAT']
- get_departements_disponibles() : départements avec nombre d'élus actifs
- get_elus_actuels()             : élus actifs avec bloc_final (override ou dérivé)
- get_composition_politique()    : répartition par bloc_final
- get_activite_elu()             : scores d'activité d'un élu
- get_classement_activite()      : top N par indicateur d'activité
- get_activite_par_bloc()        : moyennes d'activité par bloc
- get_historique_legislatures_an() : législatures AN avec comptages
- get_evolution_composition_an() : composition AN par législature et bloc
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

logger = logging.getLogger(__name__)

DB_PATH: Path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"

_INDICATEURS_ACTIVITE_VALIDES = frozenset(
    {
        "score_participation",
        "score_participation_specialite",
        "score_loyaute",
        "score_majorite",
    }
)


def _open_ro() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def _dept_clause(
    codes: tuple[str, ...] | None,
    params: list,
    alias: str = "e",
) -> str:
    """Construit la clause SQL de filtre département (paramétré)."""
    if codes is None:
        return ""
    placeholders = ", ".join("?" * len(codes))
    params.extend(codes)
    return f" AND {alias}.code_departement IN ({placeholders})"


# ---------------------------------------------------------------------------
# 1. is_data_loaded
# ---------------------------------------------------------------------------


@st.cache_data(ttl=60)
def is_data_loaded() -> bool:
    """Vérifie que leg_elus contient des données pour AN et SENAT."""
    con = _open_ro()
    try:
        n_an = con.execute("SELECT COUNT(*) FROM leg_elus WHERE chambre = 'AN'").fetchone()[0]
        n_senat = con.execute("SELECT COUNT(*) FROM leg_elus WHERE chambre = 'SENAT'").fetchone()[0]
        return int(n_an) > 0 and int(n_senat) > 0
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 2. get_chambres
# ---------------------------------------------------------------------------


def get_chambres() -> list[str]:
    """Retourne la liste des chambres."""
    return ["AN", "SENAT"]


# ---------------------------------------------------------------------------
# 3. get_departements_disponibles
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_departements_disponibles() -> pl.DataFrame:
    """Départements avec nombre d'élus actifs, triés par nom."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT code_departement, nom_departement, COUNT(*) AS nb_elus "
            "FROM leg_elus WHERE est_actif = TRUE "
            "GROUP BY code_departement, nom_departement "
            "ORDER BY nom_departement"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_departement": pl.Utf8,
                "nom_departement": pl.Utf8,
                "nb_elus": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "code_departement": [r[0] for r in rows],
            "nom_departement": [r[1] for r in rows],
            "nb_elus": [int(r[2]) for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 4. get_elus_actuels
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner="Chargement des élus…")
def get_elus_actuels(
    chambre: str | None = None,
    codes_departement: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """Élus actifs avec bloc_final (COALESCE override)."""
    con = _open_ro()
    try:
        sql = (
            "SELECT e.id, e.chambre, e.nom, e.prenom, "
            "e.code_departement, e.nom_departement, e.num_circo, "
            "e.groupe_sigle, "
            "COALESCE(o.bloc_force, e.bloc_politique, 'DIV') AS bloc_final, "
            "e.profession "
            "FROM leg_elus e "
            "LEFT JOIN leg_blocs_override o "
            "ON e.id = o.elu_id AND e.chambre = o.chambre "
            "WHERE e.est_actif = TRUE"
        )
        params: list = []
        if chambre is not None:
            sql += " AND e.chambre = ?"
            params.append(chambre)
        sql += _dept_clause(codes_departement, params)
        sql += " ORDER BY e.nom, e.prenom"
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "id": pl.Utf8,
                "chambre": pl.Utf8,
                "nom": pl.Utf8,
                "prenom": pl.Utf8,
                "code_departement": pl.Utf8,
                "nom_departement": pl.Utf8,
                "num_circo": pl.Int64,
                "groupe_sigle": pl.Utf8,
                "bloc_final": pl.Utf8,
                "profession": pl.Utf8,
            }
        )
    return pl.DataFrame(
        {
            "id": [r[0] for r in rows],
            "chambre": [r[1] for r in rows],
            "nom": [r[2] for r in rows],
            "prenom": [r[3] for r in rows],
            "code_departement": [r[4] for r in rows],
            "nom_departement": [r[5] for r in rows],
            "num_circo": [int(r[6]) if r[6] is not None else None for r in rows],
            "groupe_sigle": [r[7] for r in rows],
            "bloc_final": [r[8] for r in rows],
            "profession": [r[9] for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 5. get_composition_politique
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_composition_politique(
    chambre: str | None = None,
    codes_departement: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """Répartition par bloc_final des élus actifs."""
    con = _open_ro()
    try:
        sql = (
            "SELECT COALESCE(o.bloc_force, e.bloc_politique, 'DIV') AS bloc_final, "
            "COUNT(*) AS nb_elus "
            "FROM leg_elus e "
            "LEFT JOIN leg_blocs_override o "
            "ON e.id = o.elu_id AND e.chambre = o.chambre "
            "WHERE e.est_actif = TRUE"
        )
        params: list = []
        if chambre is not None:
            sql += " AND e.chambre = ?"
            params.append(chambre)
        sql += _dept_clause(codes_departement, params)
        sql += " GROUP BY bloc_final ORDER BY nb_elus DESC"
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(schema={"bloc_final": pl.Utf8, "nb_elus": pl.Int64})
    return pl.DataFrame(
        {
            "bloc_final": [r[0] for r in rows],
            "nb_elus": [int(r[1]) for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 6. get_activite_elu
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_activite_elu(elu_id: str, chambre: str) -> pl.DataFrame:
    """Scores d'activité d'un élu (toutes dates d'extraction)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT date_extraction, score_participation, "
            "score_participation_specialite, score_loyaute, score_majorite "
            "FROM leg_activite WHERE elu_id = ? AND chambre = ? "
            "ORDER BY date_extraction",
            [elu_id, chambre],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "date_extraction": pl.Date,
                "score_participation": pl.Float64,
                "score_participation_specialite": pl.Float64,
                "score_loyaute": pl.Float64,
                "score_majorite": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "date_extraction": [r[0] for r in rows],
            "score_participation": [float(r[1]) if r[1] is not None else None for r in rows],
            "score_participation_specialite": [
                float(r[2]) if r[2] is not None else None for r in rows
            ],
            "score_loyaute": [float(r[3]) if r[3] is not None else None for r in rows],
            "score_majorite": [float(r[4]) if r[4] is not None else None for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 7. get_classement_activite
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner="Chargement classement activité…")
def get_classement_activite(
    chambre: str,
    indicateur: str,
    codes_departement: tuple[str, ...] | None = None,
    n: int = 20,
) -> pl.DataFrame:
    """Top N élus par indicateur d'activité (AN uniquement — Datan)."""
    if indicateur not in _INDICATEURS_ACTIVITE_VALIDES:
        raise ValueError(f"Indicateur activité inconnu : {indicateur}")
    if chambre == "SENAT":
        logger.warning("Scores d'activité non disponibles pour le Sénat (source Datan = AN)")
        return pl.DataFrame(
            schema={
                "nom": pl.Utf8,
                "prenom": pl.Utf8,
                "groupe_sigle": pl.Utf8,
                "bloc_final": pl.Utf8,
                "code_departement": pl.Utf8,
                indicateur: pl.Float64,
            }
        )

    con = _open_ro()
    try:
        sql = (  # noqa: S608
            f"SELECT e.nom, e.prenom, e.groupe_sigle, "
            f"COALESCE(o.bloc_force, e.bloc_politique, 'DIV') AS bloc_final, "
            f"e.code_departement, a.{indicateur} "
            f"FROM leg_elus e "
            f"JOIN leg_activite a ON e.id = a.elu_id AND e.chambre = a.chambre "
            f"LEFT JOIN leg_blocs_override o "
            f"ON e.id = o.elu_id AND e.chambre = o.chambre "
            f"WHERE e.est_actif = TRUE AND e.chambre = ? "
            f"AND a.{indicateur} IS NOT NULL"
        )
        params: list = [chambre]
        sql += _dept_clause(codes_departement, params)
        sql += f" ORDER BY a.{indicateur} DESC LIMIT ?"
        params.append(n)
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "nom": pl.Utf8,
                "prenom": pl.Utf8,
                "groupe_sigle": pl.Utf8,
                "bloc_final": pl.Utf8,
                "code_departement": pl.Utf8,
                indicateur: pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "nom": [r[0] for r in rows],
            "prenom": [r[1] for r in rows],
            "groupe_sigle": [r[2] for r in rows],
            "bloc_final": [r[3] for r in rows],
            "code_departement": [r[4] for r in rows],
            indicateur: [float(r[5]) if r[5] is not None else None for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 8. get_activite_par_bloc
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_activite_par_bloc(
    codes_departement: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """Moyennes d'activité par bloc politique (AN actifs uniquement)."""
    con = _open_ro()
    try:
        sql = (
            "SELECT COALESCE(o.bloc_force, e.bloc_politique, 'DIV') AS bloc, "
            "AVG(a.score_participation) AS moy_participation, "
            "AVG(a.score_loyaute) AS moy_loyaute, "
            "AVG(a.score_majorite) AS moy_majorite, "
            "COUNT(*) AS nb_elus "
            "FROM leg_elus e "
            "JOIN leg_activite a ON e.id = a.elu_id AND e.chambre = a.chambre "
            "LEFT JOIN leg_blocs_override o "
            "ON e.id = o.elu_id AND e.chambre = o.chambre "
            "WHERE e.est_actif = TRUE AND e.chambre = 'AN'"
        )
        params: list = []
        sql += _dept_clause(codes_departement, params)
        sql += " GROUP BY bloc ORDER BY moy_participation DESC"
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "bloc": pl.Utf8,
                "moy_participation": pl.Float64,
                "moy_loyaute": pl.Float64,
                "moy_majorite": pl.Float64,
                "nb_elus": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "bloc": [r[0] for r in rows],
            "moy_participation": [float(r[1]) if r[1] is not None else None for r in rows],
            "moy_loyaute": [float(r[2]) if r[2] is not None else None for r in rows],
            "moy_majorite": [float(r[3]) if r[3] is not None else None for r in rows],
            "nb_elus": [int(r[4]) for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 9. get_historique_legislatures_an
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_historique_legislatures_an() -> pl.DataFrame:
    """Législatures AN distinctes avec nombre de députés."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT legislature, COUNT(*) AS nb_deputes "
            "FROM leg_elus WHERE chambre = 'AN' AND legislature IS NOT NULL "
            "GROUP BY legislature ORDER BY legislature"
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(schema={"legislature": pl.Int64, "nb_deputes": pl.Int64})
    return pl.DataFrame(
        {
            "legislature": [int(r[0]) for r in rows],
            "nb_deputes": [int(r[1]) for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# 10. get_evolution_composition_an
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def get_evolution_composition_an() -> pl.DataFrame:
    """Composition AN par législature et bloc_final (tous les élus, pas seulement actifs)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT e.legislature, "
            "COALESCE(o.bloc_force, e.bloc_politique, 'DIV') AS bloc_final, "
            "COUNT(*) AS nb_elus "
            "FROM leg_elus e "
            "LEFT JOIN leg_blocs_override o "
            "ON e.id = o.elu_id AND e.chambre = o.chambre "
            "WHERE e.chambre = 'AN' AND e.legislature IS NOT NULL "
            "GROUP BY e.legislature, bloc_final "
            "ORDER BY e.legislature, bloc_final"
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "legislature": pl.Int64,
                "bloc_final": pl.Utf8,
                "nb_elus": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "legislature": [int(r[0]) for r in rows],
            "bloc_final": [r[1] for r in rows],
            "nb_elus": [int(r[2]) for r in rows],
        }
    )
