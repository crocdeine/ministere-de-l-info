"""Tests hermétiques du loader RP (economie_rp) — correctif secret 2015/2016 (2026-09-25).

Petit Parquet OLAP écrit dans ``tmp_path`` : aucun accès réseau, aucune base réelle.
Vérifie qu'un millésime où la clef des chômeurs est absente n'est pas marqué « secret »
(auparavant : 100 % des communes RP 2015 et 2016 en secret), que le secret communal reste
détecté, que le filtre HdF s'applique et que le manque de clef est signalé.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pytest

from ministere_de_l_info.etl.loaders.economie_rp import load_economie_rp
from ministere_de_l_info.etl.schema_economie import create_economie_schema

# (code_com, annee, source, clef_json, valeur) — valeurs réalistes, arrondies
_COMMUNES = ("80021", "80001", "59350", "75056")  # Amiens, Abbeville, Lille, Paris (hors HdF)


def _lignes() -> list[tuple[str, int, str, str, float | None]]:
    lignes: list[tuple[str, int, str, str, float | None]] = []
    for annee in (2016, 2017):
        for i, code in enumerate(_COMMUNES):
            base = 1000.0 * (i + 1)
            emploi = [
                ("actifs_15_64_ans_c", base),
                ("actifs_15_64_ans_p", base),
                ("actifs_ouvriers_15_64_ans_c", base * 0.2),
                ("actifs_employes_15_64_ans_c", base * 0.3),
                ("emplois_au_lieu_travail_c", base * 1.5),
                ("emplois_au_lieu_travail_industrie_c", base * 0.15),
            ]
            if annee == 2017:
                # Abbeville : secret communal (valeur NULL, clef diffusée ailleurs)
                emploi.append(("chomeurs_15_64_ans_p", None if code == "80001" else base * 0.12))
            lignes += [(code, annee, "rp_actifs_emploi", k, v) for k, v in emploi]
            lignes += [
                (code, annee, "rp_logements", "residences_principales_p", base * 2),
                (code, annee, "rp_logements", "nb_rp_hlm_p", base * 0.4),
            ]
    return lignes


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    chemin = tmp_path / "economie" / "donnees-insee-olap-hdf.parquet"
    chemin.parent.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE olap (code_com VARCHAR, annee INTEGER, source VARCHAR, "
        "clef_json VARCHAR, valeur DOUBLE)"
    )
    con.executemany("INSERT INTO olap VALUES (?, ?, ?, ?, ?)", _lignes())
    con.execute(f"COPY olap TO '{chemin}' (FORMAT PARQUET)")
    con.close()
    return tmp_path


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    c.execute(
        "CREATE TABLE _etl_metadata (table_name VARCHAR, loaded_at TIMESTAMP, "
        "source_version VARCHAR, row_count INTEGER)"
    )
    create_economie_schema(c)
    yield c
    c.close()


def test_millesime_sans_clef_chomage_non_secret(
    con: duckdb.DuckDBPyConnection, raw_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        load_economie_rp(con, raw_dir)
    rows = con.execute(
        "SELECT code_commune, tx_chomage_dec, part_ouvriers_employes, secret "
        "FROM economie_rp WHERE annee_millesime = 2016 ORDER BY 1"
    ).fetchall()
    assert [r[0] for r in rows] == ["59350", "80001", "80021"]  # Paris filtré (hors HdF)
    assert all(r[1] is None for r in rows)
    assert all(r[2] == pytest.approx(50.0) for r in rows)
    assert not any(r[3] for r in rows)
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("RP 2016" in m and "chomeurs_15_64_ans_p" in m for m in messages)
    assert not any("RP 2017" in m for m in messages)


def test_secret_communal_conserve(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    load_economie_rp(con, raw_dir)
    rows = dict(
        con.execute(
            "SELECT code_commune, secret FROM economie_rp WHERE annee_millesime = 2017"
        ).fetchall()
    )
    assert rows == {"59350": False, "80001": True, "80021": False}
    tx = con.execute(
        "SELECT tx_chomage_dec FROM economie_rp "
        "WHERE annee_millesime = 2017 AND code_commune = '80021'"
    ).fetchone()[0]
    assert tx == pytest.approx(12.0)


def test_rechargement_millesime_idempotent(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    load_economie_rp(con, raw_dir)
    load_economie_rp(con, raw_dir, millesimes=[2016])
    n = con.execute("SELECT annee_millesime, COUNT(*) FROM economie_rp GROUP BY 1 ORDER BY 1")
    assert n.fetchall() == [(2016, 3), (2017, 3)]


def test_annees_proposees_ont_des_valeurs(
    echantillon_db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UI : un millésime n'est proposé que si l'indicateur y a au moins une valeur.

    Sur l'échantillon exporté avant correctif, le chômage RP 2015-2016 est NULL partout :
    ces millésimes ne doivent pas être proposés pour ``tx_chomage_dec``.
    """
    from ministere_de_l_info.viz import economie_queries as q

    monkeypatch.setattr(
        q, "_open_ro", lambda: duckdb.connect(str(echantillon_db_path), read_only=True)
    )
    q.get_annees_par_indicateur.clear()
    try:
        annees = q.get_annees_par_indicateur()
    finally:
        q.get_annees_par_indicateur.clear()

    con = duckdb.connect(str(echantillon_db_path), read_only=True)
    try:
        for indicateur, (table, col) in q._SOURCES_ANNEES.items():
            attendues = [
                int(r[0])
                for r in con.execute(
                    f"SELECT {col} FROM {table} GROUP BY 1 "
                    f"HAVING COUNT({indicateur}) > 0 ORDER BY 1"
                ).fetchall()
            ]
            assert annees[indicateur] == attendues, indicateur
        chargees = {
            int(r[0])
            for r in con.execute("SELECT DISTINCT annee_millesime FROM economie_rp").fetchall()
        }
    finally:
        con.close()
    assert set(annees["tx_chomage_dec"]) <= chargees
