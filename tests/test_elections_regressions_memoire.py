"""Tests de régression hermétiques — bugs C1, C2, C3 (audit 2026-09-24).

Base DuckDB en mémoire, sans extension spatial ni base réelle : exécutables en CI.
Chaque test reproduit un scénario de l'audit (reports/audit-code-2026-09-24.md) avec
les fonctions réelles du projet (schéma, référentiels, migrations 0006/0007).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    _NUANCES_LEGI,
    _NUANCES_MUNI,
    _NUANCES_PRES,
    create_elections_schema,
    populate_elections_referentiels,
)

_ANNEES_MUNI = (2008, 2014, 2020, 2026)


def _charger_script(chemin: Path) -> ModuleType:
    """Importe un script (scripts/, migrations/) par son chemin de fichier."""
    spec = importlib.util.spec_from_file_location(f"_test_{chemin.stem}", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Base mémoire : schéma électoral + référentiels."""
    c = duckdb.connect()
    create_elections_schema(c)
    populate_elections_referentiels(c)
    yield c
    c.close()


def _n_muni(con: duckdb.DuckDBPyConnection) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee IN (2008, 2014, 2020, 2026)"
    ).fetchone()[0]


# ── C2 — populate_elections_referentiels ne doit pas perdre les nuances municipales ──


class TestC2ReferentielsConserventMunicipales:
    def test_referentiel_contient_les_trois_jeux(self, con: duckdb.DuckDBPyConnection) -> None:
        n_total = con.execute("SELECT COUNT(*) FROM nuances_harmonisees").fetchone()[0]
        assert n_total == len(_NUANCES_PRES) + len(_NUANCES_LEGI) + len(_NUANCES_MUNI)
        assert _n_muni(con) == 67

    def test_relance_referentiels_conserve_les_67_nuances_muni(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        """Scénario audit : relancer init_elections_schema après le chargement municipal."""
        assert _n_muni(con) == 67
        populate_elections_referentiels(con)
        assert _n_muni(con) == 67, "Nuances municipales perdues après relance des référentiels"

    def test_relance_referentiels_bloc_muni_resolu(self, con: duckdb.DuckDBPyConnection) -> None:
        populate_elections_referentiels(con)
        bloc = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance = 'LFI' AND annee = 2026"
        ).fetchone()
        assert bloc is not None and bloc[0] == "EXG"

    def test_cles_nuance_annee_uniques_entre_les_trois_jeux(self) -> None:
        cles = [(n, a) for n, a, _, _ in _NUANCES_PRES + _NUANCES_LEGI + _NUANCES_MUNI]
        assert len(cles) == len(set(cles)), "Collision (nuance, annee) entre pres/legi/muni"

    def test_annees_municipales_disjointes_des_autres_jeux(self) -> None:
        annees_pres_legi = {a for _, a, _, _ in _NUANCES_PRES + _NUANCES_LEGI}
        annees_muni = {a for _, a, _, _ in _NUANCES_MUNI}
        assert annees_muni == set(_ANNEES_MUNI)
        assert not annees_muni & annees_pres_legi

    def test_codes_sans_mapping_absents(self, con: duckdb.DuckDBPyConnection) -> None:
        n = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE nuance IN ('NC', 'LMAJ', 'LNC')"
        ).fetchone()[0]
        assert n == 0

    def test_script_loader_reutilise_la_liste_centrale(self) -> None:
        loader = _charger_script(ROOT / "scripts" / "load_elections_municipales.py")
        assert loader._NUANCES_MUNI is _NUANCES_MUNI
