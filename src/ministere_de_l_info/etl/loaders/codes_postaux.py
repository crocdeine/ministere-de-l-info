"""Codes postaux des communes (La Poste, « Base officielle des codes postaux », hexasmal).

Source : data.laposte.fr, jeu `laposte-hexasmal` (Licence Ouverte 2.0 d'après data.gouv.fr,
vérifiée le 2026-10-12). CSV latin-1, séparateur `;`. Une commune peut avoir plusieurs codes
postaux et un code postal couvre plusieurs communes : table `codes_postaux(code_insee,
code_postal)`, sans interprétation. Paris, Lyon et Marseille sont publiés par arrondissement
(75101…) : rattachés à la commune (75056, 69123, 13055), comme dans `geographies_communes`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import httpx

logger = logging.getLogger(__name__)

URL_HEXASMAL = "https://data.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/raw"
_ENTETE = b"#Code_commune_INSEE;Nom_de_la_commune;Code_postal"
_PLM = (("75101", "75120", "75056"), ("69381", "69389", "69123"), ("13201", "13216", "13055"))
DDL = "CREATE OR REPLACE TABLE codes_postaux (code_insee VARCHAR NOT NULL, code_postal VARCHAR NOT NULL)"


def telecharger(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge hexasmal.csv (entête contrôlée avant de remplacer le cache)."""
    dest = raw_dir / "laposte" / "hexasmal.csv"
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with httpx.stream("GET", URL_HEXASMAL, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        tmp.write_bytes(b"".join(r.iter_bytes()))
    if not tmp.read_bytes()[:200].startswith(_ENTETE):
        tmp.unlink()
        raise RuntimeError("data.laposte.fr n'a pas renvoyé hexasmal.csv ; cache conservé.")
    tmp.replace(dest)
    return dest


def charger(con: duckdb.DuckDBPyConnection, csv: Path) -> int:
    """(Re)construit `codes_postaux` ; renvoie le nombre de couples distincts."""
    cas = " ".join(f"WHEN c BETWEEN '{a}' AND '{b}' THEN '{r}'" for a, b, r in _PLM)
    con.execute(DDL)
    con.execute(
        f"""
        INSERT INTO codes_postaux
        SELECT DISTINCT code_insee, cp FROM (
            SELECT CASE {cas} ELSE c END AS code_insee, cp
            FROM (SELECT "#Code_commune_INSEE" AS c, Code_postal AS cp
                  FROM read_csv(?, delim = ';', header = true, all_varchar = true,
                                encoding = 'latin-1'))
        ) WHERE regexp_matches(cp, '^[0-9]{{5}}$') AND regexp_matches(code_insee, '^([0-9]{{5}}|2[AB][0-9]{{3}})$')
        """,  # noqa: S608 — constantes du module
        [str(csv)],
    )
    n = int(con.execute("SELECT COUNT(*) FROM codes_postaux").fetchone()[0])  # type: ignore[index]
    if n < 30000:
        raise RuntimeError(f"codes_postaux : {n} lignes seulement (attendu ≈ 39 000)")
    logger.info("codes_postaux : %d couples (commune, code postal)", n)
    return n
