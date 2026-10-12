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
MIN_COUPLES = 35000  # 35 511 le 2026-10-12
DDL = "CREATE OR REPLACE TABLE codes_postaux (code_insee VARCHAR NOT NULL, code_postal VARCHAR NOT NULL)"


def _verifier_entete(csv: Path) -> None:
    if not csv.read_bytes()[:200].startswith(_ENTETE):
        raise RuntimeError(f"{csv} n'est pas le fichier hexasmal attendu (entête) ; --force.")


def telecharger(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge hexasmal.csv ; l'entête est contrôlée aussi sur un cache existant."""
    dest = raw_dir / "laposte" / "hexasmal.csv"
    if dest.exists() and not force:
        _verifier_entete(dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with httpx.stream("GET", URL_HEXASMAL, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        tmp.write_bytes(b"".join(r.iter_bytes()))
    try:
        _verifier_entete(tmp)
    except RuntimeError:
        tmp.unlink()
        raise RuntimeError(
            "data.laposte.fr n'a pas renvoyé hexasmal.csv ; cache conservé."
        ) from None
    tmp.replace(dest)
    return dest


def charger(con: duckdb.DuckDBPyConnection, csv: Path) -> int:
    """(Re)construit `codes_postaux` ; renvoie le nombre de couples distincts.

    Erreur si une ligne est rejetée (code mal formé) ou si moins de ``MIN_COUPLES`` couples.
    Les couples dont la commune n'est pas dans `geographies_communes` (COM : 98x, 97x hors
    départements d'outre-mer du référentiel) sont conservés et journalisés par préfixe.
    """
    cas = " ".join(f"WHEN c BETWEEN '{a}' AND '{b}' THEN '{r}'" for a, b, r in _PLM)
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _hexa AS
        SELECT "#Code_commune_INSEE" AS c, Code_postal AS cp
        FROM read_csv(?, delim = ';', header = true, all_varchar = true, encoding = 'latin-1')
        """,
        [str(csv)],
    )
    total, rejetees = con.execute(
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE NOT (regexp_matches(cp, '^[0-9]{5}$') "
        "AND regexp_matches(c, '^([0-9]{5}|2[AB][0-9]{3})$'))) FROM _hexa"
    ).fetchone()  # type: ignore[misc]
    if rejetees:
        raise RuntimeError(
            f"codes_postaux : {rejetees} lignes sur {total} rejetées (codes mal formés)"
        )
    con.execute(DDL)
    con.execute(
        f"""
        INSERT INTO codes_postaux
        SELECT DISTINCT CASE {cas} ELSE c END, cp FROM _hexa
        """  # noqa: S608
    )
    n = int(con.execute("SELECT COUNT(*) FROM codes_postaux").fetchone()[0])  # type: ignore[index]
    if n < MIN_COUPLES:
        raise RuntimeError(f"codes_postaux : {n} couples seulement (minimum {MIN_COUPLES})")
    if con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'geographies_communes'"
    ).fetchone()[0]:  # type: ignore[index]
        hors = con.execute(
            "SELECT left(code_insee, 3), COUNT(*) FROM codes_postaux "
            "WHERE code_insee NOT IN (SELECT code_insee FROM geographies_communes) GROUP BY 1 ORDER BY 1"
        ).fetchall()
        if hors:
            logger.warning(
                "codes_postaux : %d couples hors référentiel des communes (COM), conservés : %s",
                sum(k for _, k in hors),
                ", ".join(f"{p}={k}" for p, k in hors),
            )
    logger.info("codes_postaux : %d couples (commune, code postal), %d lignes lues", n, total)
    return n
