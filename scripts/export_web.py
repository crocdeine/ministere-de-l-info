"""Export des données de la maquette web (présidentielles, Hauts-de-France).

Usage :
    uv run python scripts/export_web.py [--db CHEMIN] [--out DOSSIER]

Lit la base en LECTURE SEULE via les vues existantes (``v_scores_commune_pres``,
``v_participation_commune_pres``) et ``geographies_communes`` ; écrit dans
``web/public/data/`` (non commité) :

- ``communes.geojson`` : contours simplifiés des communes HdF (propriétés ``code``, ``nom``) ;
- ``resultats.json``   : par scrutin, colonnes alignées sur ``codes`` (inscrits, votants,
  exprimés, voix par bloc) et chiffres-clés de la région ;
- ``evolution.json``   : part des exprimés de chaque bloc, région entière, par année et tour ;
- ``meta.json``        : date d'export, sources et licences, légende de classement par
  scrutin, blocs (ordre, libellés, couleurs), fond de carte.

Absence de donnée = ``null`` (affichée « n.d. »), jamais 0. Toutes les agrégations sont en SQL.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info._blocs_politiques import (  # noqa: E402
    BLOCS_ORDERED,
    COULEURS_BLOCS,
    LIBELLES_BLOCS,
    couleurs_traits,
    legende_classement_blocs,
)
from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.sources import SOURCES, mention  # noqa: E402
from ministere_de_l_info.viz._display import _URL_PLAN_IGN, COULEUR_ND  # noqa: E402
from ministere_de_l_info.viz._queries import open_ro  # noqa: E402
from ministere_de_l_info.viz.maps_elections import ECHELLE_SCORE_MAX  # noqa: E402

logger = logging.getLogger(__name__)

SORTIE_DEFAUT: Path = ROOT / "web" / "public" / "data"
_HDF_DEPTS_SQL: str = "'02', '59', '60', '62', '80'"
# Arrondi des coordonnées (~1 m) : réduit le GeoJSON d'environ 20 % sans effet visible.
_PRECISION_DEG: float = 0.00001


def _ecrire_json(chemin: Path, contenu: Any) -> int:
    """Écrit un JSON compact UTF-8 ; renvoie la taille en octets."""
    texte = json.dumps(contenu, ensure_ascii=False, separators=(",", ":"))
    chemin.write_text(texte, encoding="utf-8")
    return len(texte.encode("utf-8"))


def _geometries(con: duckdb.DuckDBPyConnection) -> tuple[dict[str, Any], list[str]]:
    """FeatureCollection des communes HdF (ordre des codes INSEE) et liste des codes."""
    rows = con.execute(
        f"""
        SELECT code_insee, nom,
               ST_AsGeoJSON(ST_ReducePrecision(geometry_simplified_communal, {_PRECISION_DEG}))
        FROM geographies_communes
        WHERE code_region = '32' AND geometry_simplified_communal IS NOT NULL
        ORDER BY code_insee
        """
    ).fetchall()
    features = [
        {
            "type": "Feature",
            "properties": {"code": code, "nom": nom},
            "geometry": json.loads(geojson),
        }
        for code, nom, geojson in rows
        if geojson
    ]
    codes = [f["properties"]["code"] for f in features]
    return {"type": "FeatureCollection", "features": features}, codes


def _bornes(con: duckdb.DuckDBPyConnection) -> list[list[float]] | None:
    """Emprise [[lon_min, lat_min], [lon_max, lat_max]] des communes HdF."""
    row = con.execute(
        """
        SELECT MIN(ST_XMin(geometry_simplified_communal)), MIN(ST_YMin(geometry_simplified_communal)),
               MAX(ST_XMax(geometry_simplified_communal)), MAX(ST_YMax(geometry_simplified_communal))
        FROM geographies_communes WHERE code_region = '32'
        """
    ).fetchone()
    if not row or row[0] is None:
        return None
    return [[float(row[0]), float(row[1])], [float(row[2]), float(row[3])]]


def _scrutins(con: duckdb.DuckDBPyConnection) -> list[tuple[int, int]]:
    """Scrutins présidentiels présents en base, (année, tour) triés."""
    return [
        (int(a), int(t))
        for a, t in con.execute(
            "SELECT DISTINCT annee, tour FROM v_participation_commune_pres ORDER BY annee, tour"
        ).fetchall()
    ]


def _resultats(
    con: duckdb.DuckDBPyConnection, codes: list[str], scrutins: list[tuple[int, int]]
) -> dict[str, Any]:
    """Colonnes par scrutin alignées sur ``codes`` + chiffres-clés régionaux."""
    voix_cols = ",\n".join(f"SUM(voix) FILTER (WHERE bloc = '{b}') AS v_{b}" for b in BLOCS_ORDERED)
    # Bloc présent en base pour la commune mais sans voix pour ce bloc = 0 voix réel ;
    # commune absente des résultats = NULL (n.d.).
    voix_select = ", ".join(
        f"CASE WHEN s.code_commune IS NULL THEN NULL ELSE COALESCE(s.v_{b}, 0) END"
        for b in BLOCS_ORDERED
    )
    con.execute("CREATE OR REPLACE TEMP TABLE _codes (code VARCHAR, rang INTEGER)")
    con.executemany("INSERT INTO _codes VALUES (?, ?)", [(c, i) for i, c in enumerate(codes)])
    rows = con.execute(
        f"""
        WITH s AS (
            SELECT annee, tour, code_commune, {voix_cols}
            FROM v_scores_commune_pres
            WHERE code_departement IN ({_HDF_DEPTS_SQL})
            GROUP BY annee, tour, code_commune
        ),
        sc AS (SELECT DISTINCT annee, tour FROM v_participation_commune_pres)
        SELECT sc.annee, sc.tour, p.inscrits, p.votants, p.exprimes, {voix_select}
        FROM sc CROSS JOIN _codes c
        LEFT JOIN v_participation_commune_pres p
            ON p.annee = sc.annee AND p.tour = sc.tour AND p.code_commune = c.code
        LEFT JOIN s
            ON s.annee = sc.annee AND s.tour = sc.tour AND s.code_commune = c.code
        ORDER BY sc.annee, sc.tour, c.rang
        """  # noqa: S608
    ).fetchall()
    chiffres = {
        (int(r[0]), int(r[1])): r[2:]
        for r in con.execute(
            f"""
            WITH p AS (
                SELECT annee, tour, SUM(inscrits) AS inscrits,
                       100.0 * SUM(votants) FILTER (WHERE inscrits IS NOT NULL)
                         / NULLIF(SUM(inscrits) FILTER (WHERE votants IS NOT NULL), 0) AS participation
                FROM v_participation_commune_pres
                WHERE code_departement IN ({_HDF_DEPTS_SQL})
                GROUP BY annee, tour
            ),
            b AS (
                SELECT annee, tour, bloc, SUM(voix) AS voix
                FROM v_scores_commune_pres
                WHERE code_departement IN ({_HDF_DEPTS_SQL})
                GROUP BY annee, tour, bloc
            ),
            s AS (
                SELECT annee, tour, COUNT(DISTINCT code_commune) AS communes
                FROM v_scores_commune_pres
                WHERE code_departement IN ({_HDF_DEPTS_SQL})
                GROUP BY annee, tour
            )
            SELECT p.annee, p.tour, s.communes, p.inscrits, p.participation,
                   (SELECT arg_max(bloc, voix) FROM b WHERE b.annee = p.annee AND b.tour = p.tour)
            FROM p LEFT JOIN s USING (annee, tour)
            """  # noqa: S608
        ).fetchall()
    }

    def _int(v: Any) -> int | None:
        return None if v is None else int(v)

    sortie: dict[str, Any] = {"codes": codes, "scrutins": {}}
    n = len(codes)
    for i, (annee, tour) in enumerate(scrutins):
        bloc_rows = rows[i * n : (i + 1) * n]
        communes, inscrits, participation, bloc_maj = chiffres.get((annee, tour), (None,) * 4)
        sortie["scrutins"][f"{annee}_{tour}"] = {
            "annee": annee,
            "tour": tour,
            "inscrits": [_int(r[2]) for r in bloc_rows],
            "votants": [_int(r[3]) for r in bloc_rows],
            "exprimes": [_int(r[4]) for r in bloc_rows],
            "voix": {b: [_int(r[5 + j]) for r in bloc_rows] for j, b in enumerate(BLOCS_ORDERED)},
            "chiffres": {
                "communes": _int(communes),
                "inscrits": _int(inscrits),
                "participation": None if participation is None else round(float(participation), 2),
                "bloc_majoritaire": bloc_maj,
            },
        }
    return sortie


def _evolution(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Part des exprimés (%) de chaque bloc, région entière ; bloc sans candidat = absent."""
    rows = con.execute(
        f"""
        WITH e AS (
            SELECT annee, tour, SUM(exprimes) AS exprimes
            FROM v_participation_commune_pres
            WHERE code_departement IN ({_HDF_DEPTS_SQL})
            GROUP BY annee, tour
        )
        SELECT s.annee, s.tour, s.bloc, 100.0 * SUM(s.voix) / NULLIF(ANY_VALUE(e.exprimes), 0)
        FROM v_scores_commune_pres s JOIN e USING (annee, tour)
        WHERE s.code_departement IN ({_HDF_DEPTS_SQL})
        GROUP BY s.annee, s.tour, s.bloc
        ORDER BY s.annee, s.tour, s.bloc
        """  # noqa: S608
    ).fetchall()
    return [
        {
            "annee": int(a),
            "tour": int(t),
            "bloc": b,
            "pct": None if p is None else round(float(p), 2),
        }
        for a, t, b, p in rows
    ]


def _meta(scrutins: list[tuple[int, int]], bornes: list[list[float]] | None) -> dict[str, Any]:
    annees = sorted({a for a, _ in scrutins})
    traits = couleurs_traits(COULEURS_BLOCS)
    return {
        "date_export": datetime.now(UTC).isoformat(timespec="seconds"),
        "sources": {
            cle: {
                "donnees": SOURCES[cle].donnees,
                "producteur": SOURCES[cle].producteur,
                "licence": SOURCES[cle].licence,
                "url": SOURCES[cle].url,
                "mention": mention(cle),
            }
            for cle in ("elections", "ign")
        },
        "legendes_classement": {str(a): legende_classement_blocs("pres", a) for a in annees},
        "annees": annees,
        "tours": sorted({t for _, t in scrutins}),
        "blocs": [
            {
                "code": b,
                "libelle": LIBELLES_BLOCS[b],
                "couleur": COULEURS_BLOCS[b],
                "couleur_trait": traits[b],
            }
            for b in BLOCS_ORDERED
        ],
        "couleur_nd": COULEUR_ND,
        "echelle_score_max": ECHELLE_SCORE_MAX,
        "bornes": bornes,
        "fond_carte": {
            "url": _URL_PLAN_IGN,
            "attribution": "Fond : © IGN — Plan IGN",
            "opacite": 0.35,
        },
    }


def exporter(db_path: Path, sortie: Path) -> dict[str, int]:
    """Exporte les 4 fichiers ; renvoie leur taille en octets par nom de fichier."""
    sortie.mkdir(parents=True, exist_ok=True)
    con = open_ro(db_path)
    try:
        geo, codes = _geometries(con)
        scrutins = _scrutins(con)
        tailles = {
            "communes.geojson": _ecrire_json(sortie / "communes.geojson", geo),
            "resultats.json": _ecrire_json(
                sortie / "resultats.json", _resultats(con, codes, scrutins)
            ),
            "evolution.json": _ecrire_json(sortie / "evolution.json", _evolution(con)),
            "meta.json": _ecrire_json(sortie / "meta.json", _meta(scrutins, _bornes(con))),
        }
    finally:
        con.close()
    return tailles


def main() -> None:
    parser = argparse.ArgumentParser(description="Export des données de la maquette web.")
    parser.add_argument("--db", type=Path, default=get_settings().db_path)
    parser.add_argument("--out", type=Path, default=SORTIE_DEFAUT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for nom, taille in exporter(args.db, args.out).items():
        logger.info("%-18s %8.2f Mo", nom, taille / 1e6)


if __name__ == "__main__":
    main()
