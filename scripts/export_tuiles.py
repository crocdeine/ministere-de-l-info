"""Prototype A0 : tuiles vectorielles des communes (France entière) + bloc dominant par scrutin.

Usage :
    uv run python scripts/export_tuiles.py --db COPIE.duckdb [--out web/public/data]
        [--tippecanoe CHEMIN] [--codage chaine|colonnes]

Lit la base en LECTURE SEULE (vue ``v_resultats_candidats_avec_bloc``, aucun classement
modifié) et écrit dans ``--out`` (non commité) :

- ``communes.pmtiles`` : couche ``communes`` (propriétés ``code`` et ``s`` ;
  les noms vont dans ``detail/codes.json``, chargé après la 1re carte)
  ``s`` = 1 caractère par scrutin, dans l'ordre de ``meta.scrutins`` ;
- ``meta.json`` : scrutins, codage des caractères, blocs (couleurs), sources ;
- ``detail/<id>.json`` et ``detail/<id>.bin`` (+ ``codes.json``) : résultats d'un scrutin
  France entière, pour comparer JSON et colonnes d'entiers binaires (tâche 4).

Codage : ``a``-``f`` = blocs dans l'ordre de ``BLOCS_ORDERED`` ; ``=`` = égalité de voix en
tête (couleur neutre, décision du 2026-10-06) ; ``n`` = listes non classées en tête
(municipales) ; ``.`` = pas de résultat (n.d., jamais 0).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info._blocs_politiques import (  # noqa: E402
    BLOCS_ORDERED,
    COULEURS_BLOCS,
    LIBELLES_BLOCS,
    legende_classement_blocs,
)
from ministere_de_l_info.sources import SOURCES, mention  # noqa: E402
from ministere_de_l_info.viz._display import COULEUR_ND  # noqa: E402
from ministere_de_l_info.viz._queries import open_ro  # noqa: E402

logger = logging.getLogger(__name__)

SORTIE_DEFAUT: Path = ROOT / "web" / "public" / "data"
CARACTERES: dict[str, str] = {b: "abcdef"[i] for i, b in enumerate(BLOCS_ORDERED)}
EGALITE, NON_CLASSE, ABSENT = "=", "n", "."
SCRUTIN_DETAIL = "2022_pres_t1"
NUL = -1  # entier « absent » dans le format binaire (jamais confondu avec 0 voix)


def _scrutins(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str, int, str]]:
    """Scrutins ayant des résultats par commune : (id, type, année, libellé), ordre des id."""
    return con.execute(
        """
        SELECT e.id_election, e.type_scrutin, e.annee, e.libelle
        FROM elections e
        WHERE EXISTS (SELECT 1 FROM resultats_candidats r WHERE r.id_election = e.id_election)
        ORDER BY e.id_election
        """
    ).fetchall()


def _dominants_sql() -> str:
    """Table temporaire ``_dom`` (code_insee, s) : chaîne des blocs dominants, en SQL."""
    cas = " ".join(f"WHEN '{b}' THEN '{c}'" for b, c in CARACTERES.items())
    return f"""
        CREATE OR REPLACE TEMP TABLE _dom AS
        WITH v AS (
            SELECT id_election, code_commune, COALESCE(bloc, '?') AS bloc, SUM(voix) AS voix
            FROM v_resultats_candidats_avec_bloc
            GROUP BY ALL
        ),
        m AS (SELECT id_election, code_commune, MAX(voix) AS m FROM v GROUP BY ALL),
        t AS (
            SELECT v.id_election, v.code_commune, COUNT(*) AS n, ANY_VALUE(v.bloc) AS bloc,
                   ANY_VALUE(m.m) AS m
            FROM v JOIN m USING (id_election, code_commune)
            WHERE v.voix = m.m
            GROUP BY ALL
        ),
        c AS (
            SELECT id_election, code_commune,
                   CASE WHEN m IS NULL OR m <= 0 THEN '{ABSENT}'
                        WHEN n > 1 THEN '{EGALITE}'
                        ELSE CASE bloc {cas} ELSE '{NON_CLASSE}' END END AS c
            FROM t
        )
        SELECT g.code_insee,
               string_agg(COALESCE(c.c, '{ABSENT}'), '' ORDER BY e.id_election) AS s
        FROM geographies_communes g
        CROSS JOIN _scrutins e
        LEFT JOIN c ON c.code_commune = g.code_insee AND c.id_election = e.id_election
        WHERE g.geometry_simplified_communal IS NOT NULL
        GROUP BY g.code_insee
    """  # noqa: S608


def _ecrire_geojsonseq(con: duckdb.DuckDBPyConnection, chemin: Path, codage: str, n: int) -> int:
    """Une Feature GeoJSON par ligne (entrée de tippecanoe) ; renvoie le nombre d'entités."""
    rows = con.execute(
        """
        SELECT g.code_insee, d.s, ST_AsGeoJSON(g.geometry_simplified_communal)
        FROM geographies_communes g JOIN _dom d USING (code_insee)
        ORDER BY g.code_insee
        """
    ).fetchall()
    with chemin.open("w", encoding="utf-8") as f:
        for code, s, geojson in rows:
            props: dict[str, Any] = {"code": code}
            if codage == "chaine":
                props["s"] = s
            else:  # une propriété par scrutin : valeurs dédupliquées dans chaque tuile
                props |= {f"s{i}": s[i] for i in range(n)}
            f.write(
                '{"type":"Feature","properties":'
                + json.dumps(props, ensure_ascii=False, separators=(",", ":"))
                + ',"geometry":'
                + geojson
                + "}\n"
            )
    return len(rows)


def _tuiler(tippecanoe: str, entree: Path, sortie: Path, detail_bas: int) -> None:
    """GeoJSONSeq → PMTiles. Aucune entité abandonnée ni fusionnée : chaque commune garde
    son identifiant à tous les zooms (bordures partagées simplifiées ensemble)."""
    subprocess.run(  # noqa: S603
        [
            tippecanoe,
            "-o",
            str(sortie),
            "--force",
            "--quiet",
            "-l",
            "communes",
            "-Z3",
            "-z10",
            "--detect-shared-borders",
            # Précision des zooms < 10 : 2**detail_bas unités par tuile (512 px affichés).
            f"--low-detail={detail_bas}",
            "--no-feature-limit",
            "--no-tile-size-limit",
            "-P",
            str(entree),
        ],
        check=True,
    )


def _detail(con: duckdb.DuckDBPyConnection, sortie: Path, id_election: str) -> None:
    """Résultats d'un scrutin par commune, alignés sur ``codes.json`` : JSON et binaire."""
    voix = ", ".join(f"SUM(voix) FILTER (WHERE bloc = '{b}') AS v_{b}" for b in BLOCS_ORDERED)
    df = con.execute(
        f"""
        WITH p AS (
            SELECT code_commune, SUM(inscrits) AS inscrits, SUM(votants) AS votants,
                   SUM(exprimes) AS exprimes
            FROM resultats_participation WHERE id_election = ? GROUP BY ALL
        ),
        s AS (
            SELECT code_commune, {voix}
            FROM v_resultats_candidats_avec_bloc WHERE id_election = ? GROUP BY ALL
        )
        SELECT d.code_insee, g.nom, p.inscrits, p.votants, p.exprimes,
               {", ".join(f"CASE WHEN s.code_commune IS NULL THEN NULL ELSE COALESCE(s.v_{b}, 0) END" for b in BLOCS_ORDERED)}
        FROM _dom d
        JOIN geographies_communes g USING (code_insee)
        LEFT JOIN p ON p.code_commune = d.code_insee
        LEFT JOIN s ON s.code_commune = d.code_insee
        ORDER BY d.code_insee
        """,  # noqa: S608
        [id_election, id_election],
    ).fetchnumpy()
    cols = ["inscrits", "votants", "exprimes", *BLOCS_ORDERED]
    valeurs = [df[k] for k in list(df)[2:]]
    (sortie / "detail").mkdir(exist_ok=True)
    (sortie / "detail" / "codes.json").write_text(
        json.dumps({"codes": list(df["code_insee"]), "noms": list(df["nom"])}, ensure_ascii=False),
        encoding="utf-8",
    )
    # JSON : colonnes, null = n.d.
    contenu = {
        c: [None if np.ma.is_masked(x) else int(x) for x in v]
        for c, v in zip(cols, valeurs, strict=True)
    }
    (sortie / "detail" / f"{id_election}.json").write_text(
        json.dumps(contenu, separators=(",", ":"))
    )
    # Binaire : colonnes Int32 petit-boutistes contiguës, -1 = n.d. ; ordre dans meta.
    tableau = np.stack([np.ma.filled(np.ma.asarray(v, dtype="int64"), NUL) for v in valeurs])
    (sortie / "detail" / f"{id_election}.bin").write_bytes(tableau.astype("<i4").tobytes())


def _meta(scrutins: list[tuple[str, str, int, str]]) -> dict[str, Any]:
    return {
        "date_export": datetime.now(UTC).isoformat(timespec="seconds"),
        "scrutins": [
            {
                "id": i,
                "libelle": lib,
                "legende": legende_classement_blocs(t, a),
            }
            for i, t, a, lib in scrutins
        ],
        "blocs": [
            {
                "code": b,
                "car": CARACTERES[b],
                "libelle": LIBELLES_BLOCS[b],
                "couleur": COULEURS_BLOCS[b],
            }
            for b in BLOCS_ORDERED
        ],
        "codage": {"egalite": EGALITE, "non_classe": NON_CLASSE, "absent": ABSENT},
        "couleur_nd": COULEUR_ND,
        "detail": {
            "scrutin": SCRUTIN_DETAIL,
            "colonnes": ["inscrits", "votants", "exprimes", *BLOCS_ORDERED],
            "nul": NUL,
        },
        "sources": {
            cle: {"mention": mention(cle), "licence": SOURCES[cle].licence}
            for cle in ("elections", "ign")
        },
    }


def exporter(db_path: Path, sortie: Path, tippecanoe: str, codage: str, detail_bas: int) -> None:
    sortie.mkdir(parents=True, exist_ok=True)
    con = open_ro(db_path)
    try:
        scrutins = _scrutins(con)
        con.execute("CREATE OR REPLACE TEMP TABLE _scrutins AS SELECT * FROM elections")
        con.execute(
            "DELETE FROM _scrutins WHERE id_election NOT IN (SELECT UNNEST(?))",
            [[s[0] for s in scrutins]],
        )
        con.execute(_dominants_sql())
        seq = sortie / "communes.geojsonl"
        n = _ecrire_geojsonseq(con, seq, codage, len(scrutins))
        logger.info("%d communes, %d scrutins", n, len(scrutins))
        _detail(con, sortie, SCRUTIN_DETAIL)
    finally:
        con.close()
    (sortie / "meta.json").write_text(
        json.dumps(_meta(scrutins), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    _tuiler(tippecanoe, seq, sortie / "communes.pmtiles", detail_bas)
    seq.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=SORTIE_DEFAUT)
    parser.add_argument("--tippecanoe", default="tippecanoe")
    parser.add_argument("--codage", choices=("chaine", "colonnes"), default="chaine")
    parser.add_argument("--detail-bas", type=int, default=10)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    exporter(args.db, args.out, args.tippecanoe, args.codage, args.detail_bas)


if __name__ == "__main__":
    main()
