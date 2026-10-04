"""Tests hermétiques — classement des non-inscrits AN par nuance préfectorale d'élection."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from ministere_de_l_info.etl.legislatif_groupes import populate_groupes_blocs
from ministere_de_l_info.etl.loaders.legislatif_nuances_ni import (
    NON_RETROUVEE,
    attribuer_nuances_non_inscrits,
)
from ministere_de_l_info.etl.schema_legislatif import (
    create_legislatif_schema,
    create_legislatif_views,
)

# (elu_id, nom, prénom, dept, circo, actif, [(législature, groupe)])
_DEPUTES = [
    ("PA1", "Maréchal-Le Pen", "Marion", "84", 3, False, [(14, "NI")]),
    # NI en XVe, membre d'un groupe en XIVe (source complète simulée)
    ("PA2", "Durand", "Paul", "52", 1, False, [(14, "SOC"), (15, "NI")]),
    ("PA3", "Suppléante", "Anne", "62", 10, False, [(15, "NI")]),  # absente des candidats
    ("PA4", "Battu", "Jean", "08", 1, True, [(17, "NI")]),  # candidat non élu (partielle)
    ("PA5", "Aliot", "Thérèse", "971", 2, False, [(14, "NI")]),  # accents perdus, code ZA
    ("PA6", "Membre", "Luc", "75", 1, True, [(17, "DR")]),  # non concerné
]

# (id_election, dept, commune, bv, nom, prénom, nuance, voix)
_CANDIDATS = [
    # 2012, 84-3 : FN élue au second tour
    ("2012_legi_t1", "84", "84001", "0001", "MARECHAL-LE PEN", "Marion", "FN", 400),
    ("2012_legi_t1", "84", "84001", "0001", "DUPUIS", "Marc", "UMP", 350),
    ("2012_legi_t1", "84", "84001", "0001", "MARTIN", "Lea", "SOC", 300),
    ("2012_legi_t2", "84", "84001", "0001", "MARECHAL-LE PEN", "Marion", "FN", 520),
    ("2012_legi_t2", "84", "84001", "0001", "DUPUIS", "Marc", "UMP", 480),
    # 2017, 52-1 : REM élu au premier tour (> 50 %)
    ("2017_legi_t1", "52", "52001", "0001", "DURAND", "Paul", "REM", 600),
    ("2017_legi_t1", "52", "52001", "0001", "PETIT", "Ana", "LR", 400),
    # 2024, 08-1 : candidat battu au second tour
    ("2024_legi_t1", "08", "08001", "0001", "BATTU", "Jean", "ENS", 300),
    ("2024_legi_t1", "08", "08001", "0001", "GAGNANT", "Max", "RN", 450),
    ("2024_legi_t2", "08", "08001", "0001", "BATTU", "Jean", "ENS", 480),
    ("2024_legi_t2", "08", "08001", "0001", "GAGNANT", "Max", "RN", 520),
    # 2012, 971-2 (code source ZA) : accents remplacés par « ? »
    ("2012_legi_t1", "ZA", "97101", "0001", "ALIOT", "Th?r?se", "DVG", 700),
    ("2012_legi_t1", "ZA", "97101", "0001", "AUTRE", "Paul", "SOC", 300),
]

_NUANCES = [
    ("FN", 2012, "EXD"),
    ("UMP", 2012, "DTE"),
    ("SOC", 2012, "GAU"),
    ("DVG", 2012, "GAU"),
    ("REM", 2017, "CENT"),
    ("ENS", 2024, "CENT"),
    ("RN", 2024, "EXD"),
]


@pytest.fixture
def parquet(tmp_path: Path) -> Path:
    chemin = tmp_path / "general-results.parquet"
    c = duckdb.connect()
    c.execute(
        "CREATE TABLE t (id_election VARCHAR, code_departement VARCHAR, code_commune VARCHAR, "
        "code_bv VARCHAR, nom VARCHAR, prenom VARCHAR, nuance VARCHAR, voix INTEGER)"
    )
    c.executemany("INSERT INTO t VALUES (?,?,?,?,?,?,?,?)", _CANDIDATS)
    c.execute(f"COPY t TO '{chemin}' (FORMAT parquet)")
    c.close()
    return chemin


@pytest.fixture
def con(parquet: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    c = duckdb.connect()
    c.execute(
        "CREATE TABLE _etl_metadata (table_name VARCHAR NOT NULL, loaded_at TIMESTAMP NOT NULL, "
        "source_version VARCHAR, row_count INTEGER NOT NULL, UNIQUE (table_name))"
    )
    create_legislatif_schema(c)
    populate_groupes_blocs(c)
    c.executemany(
        "INSERT INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) VALUES (?,?,?,'test')",
        _NUANCES,
    )
    for elu_id, nom, prenom, dept, circo, actif, mandats in _DEPUTES:
        leg_last, groupe_last = mandats[-1]
        c.execute(
            "INSERT INTO leg_elus (id, chambre, legislature, nom, prenom, code_departement, "
            "num_circo, groupe_sigle, est_actif, source) VALUES (?,'AN',?,?,?,?,?,?,?,'datan')",
            [elu_id, leg_last, nom, prenom, dept, circo, groupe_last, actif],
        )
        for leg, groupe in mandats:
            c.execute(
                "INSERT INTO leg_mandats (elu_id, chambre, legislature, groupe_sigle, "
                "code_departement, num_circo, granularite, source) "
                "VALUES (?,'AN',?,?,?,?,'complete','datan')",
                [elu_id, leg, groupe, dept, circo],
            )
    create_legislatif_views(c)
    attribuer_nuances_non_inscrits(c, parquet)
    yield c
    c.close()


def _mandat(con: duckdb.DuckDBPyConnection, elu_id: str, leg: int) -> tuple[str, str, str]:
    return con.execute(
        "SELECT bloc_groupe, bloc_final, source_bloc FROM v_mandats_legislatif "
        "WHERE elu_id = ? AND legislature = ?",
        [elu_id, leg],
    ).fetchone()


def test_ni_elue_sous_nuance_fn_classee_exd(con: duckdb.DuckDBPyConnection) -> None:
    bloc_groupe, bloc_final, source = _mandat(con, "PA1", 14)
    assert (bloc_groupe, bloc_final) == ("DIV", "EXD")
    assert source == (
        "nuance préfectorale FN (législatives 2012, 84-3) → EXD (nuances_harmonisees)"
    )


def test_classement_par_mandat(con: duckdb.DuckDBPyConnection) -> None:
    """NI en XVe (nuance REM élu au 1er tour), groupe SOC en XIVe : chaque mandat garde le sien."""
    assert _mandat(con, "PA2", 15)[1] == "CENT"
    bloc_groupe, bloc_final, source = _mandat(con, "PA2", 14)
    assert bloc_groupe == bloc_final == "GAU"
    assert "nuance préfectorale" not in source


@pytest.mark.parametrize(
    ("elu_id", "leg", "motif"),
    [("PA3", 15, "absent(e) des candidats"), ("PA4", 17, "non élu(e)")],
)
def test_nuance_non_retrouvee_reste_div(
    con: duckdb.DuckDBPyConnection, elu_id: str, leg: int, motif: str
) -> None:
    bloc_groupe, bloc_final, source = _mandat(con, elu_id, leg)
    assert bloc_groupe == bloc_final == "DIV"
    assert source.startswith(NON_RETROUVEE)
    assert motif in source


def test_accents_perdus_et_code_outre_mer(con: duckdb.DuckDBPyConnection) -> None:
    assert _mandat(con, "PA5", 14)[1:] == (
        "GAU",
        "nuance préfectorale DVG (législatives 2012, 971-2) → GAU (nuances_harmonisees)",
    )


def test_elus_actuels_et_override(con: duckdb.DuckDBPyConnection) -> None:
    def actuel(elu_id: str) -> str:
        return con.execute(
            "SELECT bloc_final FROM v_elus_actuels WHERE id = ?", [elu_id]
        ).fetchone()[0]

    assert actuel("PA4") == "DIV"
    assert actuel("PA6") == "DTE"
    con.execute("INSERT INTO leg_blocs_override VALUES ('PA4', 'AN', 'CENT', 'test')")
    assert actuel("PA4") == "CENT"


def test_idempotent(con: duckdb.DuckDBPyConnection, parquet: Path) -> None:
    avant = con.execute("SELECT * FROM v_mandats_legislatif ORDER BY ALL").fetchall()
    assert attribuer_nuances_non_inscrits(con, parquet) == 3
    assert con.execute("SELECT * FROM v_mandats_legislatif ORDER BY ALL").fetchall() == avant
    assert (
        con.execute("SELECT COUNT(*) FROM leg_mandats WHERE nuance_source IS NOT NULL").fetchone()[
            0
        ]
        == 5
    )
