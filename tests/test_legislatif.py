"""Tests d'intégration — module Législatif (Phase F2.2).

Vérifient le schéma, les données Sénat nationale, Datan AN, et les overrides de blocs.

Prérequis :
    uv run python scripts/load_legislatif.py --source senat
    uv run python scripts/load_legislatif.py --source datan
    uv run python scripts/load_legislatif.py --source overrides
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

DB_PATH = _ROOT / "data" / "ministere.duckdb"

_DEPTS_HDF = ("02", "59", "60", "62", "80")


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer : uv run python scripts/load_legislatif.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    tables = [r[0] for r in c.execute("SHOW TABLES").fetchall()]
    if "leg_elus" not in tables:
        pytest.skip("Table leg_elus absente.")
    n = c.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv'").fetchone()[0]
    if n == 0:
        pytest.skip(
            "Sénat non chargé. Lancer : uv run python scripts/load_legislatif.py --source senat"
        )
    return c


# ---------------------------------------------------------------------------
# Sénat — portée nationale
# ---------------------------------------------------------------------------


def test_senat_data_loaded(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv'").fetchone()[0]
    assert n > 0, "Aucun sénateur chargé"


def test_senat_national_total(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv'").fetchone()[0]
    assert n > 500, f"Attendu >500 sénateurs (actifs + anciens), trouvé {n}"


def test_senat_actifs_national(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND est_actif = TRUE"
    ).fetchone()[0]
    assert n >= 300, f"Attendu ≥300 sénateurs actifs (France entière), trouvé {n}"


def test_senat_28_actifs_hdf(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND est_actif = TRUE "
        f"AND code_departement IN {_DEPTS_HDF!r}"
    ).fetchone()[0]
    assert n == 28, f"Attendu 28 sénateurs actifs HdF, trouvé {n}"


def test_senat_anciens_inclus(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND est_actif = FALSE"
    ).fetchone()[0]
    assert n >= 100, f"Attendu ≥100 anciens sénateurs, trouvé {n}"


def test_senat_repartition_hdf(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        "SELECT code_departement, COUNT(*) FROM leg_elus "
        "WHERE source = 'senat_csv' AND est_actif = TRUE "
        f"AND code_departement IN {_DEPTS_HDF!r} "
        "GROUP BY code_departement ORDER BY code_departement"
    ).fetchall()
    repartition = {r[0]: r[1] for r in rows}
    assert repartition.get("02") == 3, f"Aisne : attendu 3, trouvé {repartition.get('02')}"
    assert repartition.get("59") == 11, f"Nord : attendu 11, trouvé {repartition.get('59')}"
    assert repartition.get("60") == 4, f"Oise : attendu 4, trouvé {repartition.get('60')}"
    assert repartition.get("62") == 7, f"PdC : attendu 7, trouvé {repartition.get('62')}"
    assert repartition.get("80") == 3, f"Somme : attendu 3, trouvé {repartition.get('80')}"


def test_mapping_blocs_senat(con: duckdb.DuckDBPyConnection) -> None:
    blocs_valides = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
    blocs_trouves = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT bloc_politique FROM leg_elus "
            "WHERE source = 'senat_csv' AND bloc_politique IS NOT NULL"
        ).fetchall()
    }
    hors_referentiel = blocs_trouves - blocs_valides
    assert not hors_referentiel, f"Blocs hors référentiel : {hors_referentiel}"


def test_senat_chambre_value(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND chambre != 'SENAT'"
    ).fetchone()[0]
    assert n == 0, f"{n} lignes Sénat avec chambre != 'SENAT'"


def test_senat_no_num_circo(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND num_circo IS NOT NULL"
    ).fetchone()[0]
    assert n == 0, f"Sénat ne doit pas avoir num_circo, trouvé {n} lignes"


# ---------------------------------------------------------------------------
# Datan — AN national
# ---------------------------------------------------------------------------


def test_datan_data_loaded(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'datan'").fetchone()[0]
    if n == 0:
        pytest.skip(
            "Datan non chargé. Lancer : uv run python scripts/load_legislatif.py --source datan"
        )
    assert n > 1000, f"Attendu >1000 députés (12e-17e), trouvé {n}"


def test_datan_577_actifs(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'datan' AND est_actif = TRUE"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Datan non chargé")
    assert n == 577, f"Attendu 577 actifs (17e), trouvé {n}"


def test_datan_couverture_legislatures(con: duckdb.DuckDBPyConnection) -> None:
    legislatures = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT legislature FROM leg_elus WHERE source = 'datan'"
        ).fetchall()
    }
    if not legislatures:
        pytest.skip("Datan non chargé")
    for leg in (12, 13, 14, 15, 16, 17):
        assert leg in legislatures, f"Législature {leg} absente des données Datan"


def test_datan_blocs_valides(con: duckdb.DuckDBPyConnection) -> None:
    blocs_valides = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
    blocs = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT bloc_politique FROM leg_elus "
            "WHERE source = 'datan' AND bloc_politique IS NOT NULL"
        ).fetchall()
    }
    if not blocs:
        pytest.skip("Datan non chargé")
    hors = blocs - blocs_valides
    assert not hors, f"Blocs hors référentiel (Datan) : {hors}"


def test_datan_chambre_value(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'datan' AND chambre != 'AN'"
    ).fetchone()[0]
    assert n == 0, f"{n} lignes Datan avec chambre != 'AN'"


def test_datan_scores_presents(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_activite WHERE source = 'datan' "
        "AND score_participation IS NOT NULL"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Datan non chargé ou scores absents")
    assert n > 500, f"Attendu >500 scores participation, trouvé {n}"


def test_datan_filtre_hdf_applicable(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'datan' AND est_actif = TRUE "
        f"AND code_departement IN {_DEPTS_HDF!r}"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Datan non chargé")
    # HdF = 5 dpts × 10-12 circonscriptions chacun = ~57 actifs attendus
    assert n >= 50, f"Attendu ≥50 députés actifs HdF (Datan), trouvé {n}"


# ---------------------------------------------------------------------------
# Overrides et vues
# ---------------------------------------------------------------------------


def test_overrides_appliques(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute("SELECT COUNT(*) FROM leg_blocs_override").fetchone()[0]
    assert n >= 2, f"Attendu ≥2 overrides (Hochart + Szczurek), trouvé {n}"


def test_overrides_hochart_szczurek(con: duckdb.DuckDBPyConnection) -> None:
    matricules = {
        r[0]
        for r in con.execute(
            "SELECT elu_id FROM leg_blocs_override WHERE bloc_force = 'EXD' AND chambre = 'SENAT'"
        ).fetchall()
    }
    assert "21085M" in matricules, "Override Hochart (21085M) manquant"
    assert "21069M" in matricules, "Override Szczurek (21069M) manquant"


def test_vue_elus_hdf_actuels(con: duckdb.DuckDBPyConnection) -> None:
    n = con.execute("SELECT COUNT(*) FROM v_elus_hdf_actuels").fetchone()[0]
    assert n >= 28, f"Vue v_elus_hdf_actuels : attendu ≥28, trouvé {n}"


def test_vue_bloc_final_override(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        "SELECT id, bloc_politique, bloc_final FROM v_elus_hdf_actuels "
        "WHERE id IN ('21085M', '21069M')"
    ).fetchall()
    if not rows:
        pytest.skip("Hochart/Szczurek absents de v_elus_hdf_actuels (peut-être non actifs)")
    for elu_id, bloc_politique, bloc_final in rows:
        assert bloc_final == "EXD", f"{elu_id} : bloc_final attendu EXD, trouvé {bloc_final}"
        assert bloc_politique == "DIV", (
            f"{elu_id} : bloc_politique attendu DIV (NI), trouvé {bloc_politique}"
        )


def test_pk_unicite(con: duckdb.DuckDBPyConnection) -> None:
    n_doublons = con.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT id, chambre, COUNT(*) AS c FROM leg_elus GROUP BY id, chambre HAVING c > 1)"
    ).fetchone()[0]
    assert n_doublons == 0, f"{n_doublons} doublons (id, chambre) dans leg_elus"


def test_schema_region_nom_exists(con: duckdb.DuckDBPyConnection) -> None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(leg_elus)").fetchall()]
    assert "region_nom" in cols, "Colonne region_nom absente de leg_elus"


def test_schema_score_columns_exist(con: duckdb.DuckDBPyConnection) -> None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(leg_activite)").fetchall()]
    for col in ("score_participation", "score_loyaute", "score_majorite"):
        assert col in cols, f"Colonne {col} absente de leg_activite"
