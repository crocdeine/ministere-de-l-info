"""Vague B (2026-10-06) : périmètre France, européennes/régionales/départementales.

Tests hermétiques : base DuckDB en mémoire, Parquet minuscules écrits dans tmp_path,
sans base réelle ni extension spatial.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl import schema_elections as se  # noqa: E402
from ministere_de_l_info.etl.loaders.elections_agregees import (  # noqa: E402
    filtre_perimetre,
    load_scrutins_listes,
)

_BLOCS = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
_GRILLES = ("INTA1931378J", "IOMA2322276J", "INTP2602966C")

# Participation (candidats-results.parquet, nommage inversé) : 1 BV HdF, 1 BV Paris,
# 1 BV Guadeloupe codé « ZA », 1 BV de commune hors référentiel.
_PARTICIPATION = """
SELECT * FROM (VALUES
  ('2024_euro_t1', '59', '59350', '0001', 1000, 400, 600, 10, 5, 585, NULL, NULL),
  ('2024_euro_t1', '75', '75056', '0001', 800, 300, 500, 5, 5, 490, NULL, NULL),
  ('2024_euro_t1', 'ZA', '97101', '0001', 500, 300, 200, 2, 3, 195, NULL, NULL),
  ('2024_euro_t1', '59', '59999', '0001', 10, 5, 5, 0, 0, 5, NULL, NULL),
  ('2021_dpmt_t1', '59', '59350', '0001', 1000, 700, 300, 5, 5, 290, NULL, NULL),
  ('2019_euro_t1', '59', '59350', '0001', 1000, 500, 500, 5, 5, 490, NULL, NULL)
) t(id_election, code_departement, code_commune, code_bv, inscrits, abstentions, votants,
    blancs, nuls, exprimes, code_circonscription, code_canton)
"""

_CANDIDATS = """
SELECT * FROM (VALUES
  ('2024_euro_t1', '59', '59350', '0001', 1, 300, 'LRN', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '59', '59350', '0001', 2, 285, 'LFI', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '75', '75056', '0001', 1, 490, 'LENS', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', 'ZA', '97101', '0001', 1, 195, 'LUG', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '59', '59999', '0001', 1, 5, 'LDIV', NULL, NULL, NULL, NULL, NULL),
  ('2021_dpmt_t1', '59', '59350', '0001', NULL, 200, 'BC-UCD', NULL, NULL,
   NULL, NULL, 'M. A et Mme B'),
  ('2021_dpmt_t1', '59', '59350', '0001', NULL, 90, 'BC-RN', NULL, NULL,
   NULL, NULL, 'M. C et Mme D'),
  ('2019_euro_t1', '59', '59350', '0001', 23, 300, NULL, NULL, NULL,
   'PRENEZ LE POUVOIR', 'BARDELLA Jordan', NULL),
  ('2019_euro_t1', '59', '59350', '0001', 7, 190, NULL, NULL, NULL,
   'ENSEMBLE PATRIOTES', 'PHILIPPOT Florian', NULL)
) t(id_election, code_departement, code_commune, code_bv, no_panneau, voix, nuance, nom,
    prenom, libelle_abrege_liste, nom_tete_liste, binome)
"""


def _parquets(tmp_path: Path) -> tuple[Path, Path]:
    """Écrit les deux Parquet de test (colonnes absentes complétées à NULL)."""
    c = duckdb.connect()
    cand = tmp_path / "general-results.parquet"
    part = tmp_path / "candidats-results.parquet"
    c.execute(f"""COPY (SELECT * REPLACE (code_circonscription::VARCHAR AS code_circonscription,
        code_canton::VARCHAR AS code_canton) FROM ({_PARTICIPATION}))
        TO '{part}' (FORMAT parquet)""")
    c.execute(f"""COPY (SELECT * REPLACE (no_panneau::INTEGER AS no_panneau,
            nuance::VARCHAR AS nuance, nom::VARCHAR AS nom, prenom::VARCHAR AS prenom,
            libelle_abrege_liste::VARCHAR AS libelle_abrege_liste,
            nom_tete_liste::VARCHAR AS nom_tete_liste, binome::VARCHAR AS binome),
        NULL::VARCHAR AS sexe, NULL::VARCHAR AS liste, NULL::VARCHAR AS libelle_etendu_liste
        FROM ({_CANDIDATS})) TO '{cand}' (FORMAT parquet)""")
    c.close()
    return cand, part


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Schéma électoral + référentiels + 3 communes du référentiel géographique."""
    c = duckdb.connect()
    se.create_elections_schema(c)
    c.execute("ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS liste VARCHAR")
    for col in ("libelle_abrege_liste", "libelle_etendu_liste", "nom_tete_liste"):
        c.execute(f"ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS {col} VARCHAR")
    c.execute("ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS prenom_tete_liste VARCHAR")
    se.populate_elections_referentiels(c)
    se.create_elections_views(c)
    c.execute("""CREATE TABLE geographies_communes AS SELECT * FROM (VALUES
        ('59350', '59', '32'), ('75056', '75', '11'), ('97101', '971', '01'))
        t(code_insee, code_departement, code_region)""")
    yield c
    c.close()


def _n(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


class TestPerimetre:
    def test_filtre_inconnu_refuse(self) -> None:
        with pytest.raises(ValueError):
            filtre_perimetre("europe")

    def test_hdf_ne_charge_que_les_hauts_de_france(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        n_p, n_c = load_scrutins_listes(con, "euro", cand, part, "hdf")
        assert (n_p, n_c) == (2, 4)  # 2024 + 2019 à Lille ; commune 59999 hors référentiel
        assert (
            _n(con, "SELECT COUNT(*) FROM resultats_participation WHERE code_commune <> '59350'")
            == 0
        )

    def test_france_charge_tout_le_referentiel(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        n_p, _ = load_scrutins_listes(con, "euro", cand, part, "france")
        assert n_p == 4
        # « ZA » normalisé en 971 ; commune hors référentiel écartée
        depts = {
            r[0]
            for r in con.execute("SELECT code_departement FROM resultats_participation").fetchall()
        }
        assert depts == {"59", "75", "971"}

    def test_idempotent_et_cible(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "dpmt", cand, part, "france")
        load_scrutins_listes(con, "euro", cand, part, "france")
        load_scrutins_listes(con, "euro", cand, part, "france")
        assert _n(con, "SELECT COUNT(*) FROM resultats_participation") == 5
        assert (
            _n(con, "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%dpmt%'") == 2
        )

    def test_type_inconnu_refuse(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        with pytest.raises(ValueError):
            load_scrutins_listes(con, "senat", cand, part, "france")


class TestColonnes:
    def test_panneau_null_numerote_et_binome_dans_nom(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "dpmt", cand, part, "hdf")
        rows = con.execute(
            "SELECT no_panneau, nom FROM resultats_candidats ORDER BY no_panneau"
        ).fetchall()
        assert rows == [(1, "M. C et Mme D"), (2, "M. A et Mme B")]  # ORDER BY nuance

    def test_euro_2019_bloc_par_tete_de_liste(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "hdf")
        rows = dict(
            con.execute(
                "SELECT nom, bloc FROM v_resultats_candidats_avec_bloc "
                "WHERE id_election = '2019_euro_t1'"
            ).fetchall()
        )
        assert rows == {"BARDELLA Jordan": "EXD", "PHILIPPOT Florian": None}

    def test_blocs_euro_2024_et_codes_ambigus(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "france")
        load_scrutins_listes(con, "dpmt", cand, part, "france")
        rows = dict(
            con.execute(
                "SELECT nuance, bloc FROM v_resultats_candidats_avec_bloc WHERE nuance IS NOT NULL"
            ).fetchall()
        )
        assert rows == {
            "LRN": "EXD",
            "LFI": "GAU",  # grille 2023 antérieure ; EXG seulement en 2026
            "LENS": "CENT",
            "LUG": "GAU",
            "BC-RN": "EXD",
            "BC-UCD": None,  # ambigu : non classé, question à Mathias
        }


class TestReferentielVagueB:
    def test_cles_uniques_et_blocs_valides(self) -> None:
        cles = [(n, a) for n, a, _, _ in se._NUANCES_EURO_REGI_DPMT]
        assert len(cles) == len(set(cles))
        autres = {(n, a) for n, a, _, _ in se._NUANCES_PRES + se._NUANCES_LEGI + se._NUANCES_MUNI}
        assert not set(cles) & autres
        assert {b for _, _, b, _ in se._NUANCES_EURO_REGI_DPMT} <= _BLOCS
        assert {e[4] for e in se._LISTES_EURO_2019} <= _BLOCS

    def test_chaque_entree_cite_une_grille(self) -> None:
        for n, a, _, src in se._NUANCES_EURO_REGI_DPMT:
            assert any(g in src for g in _GRILLES), (n, a)
            assert "ADR-0010" in src, (n, a)
        for e in se._LISTES_EURO_2019:
            assert "INTA1931378J" in e[6], e[1]

    def test_codes_ambigus_absents(self) -> None:
        cles = {(n, a) for n, a, _, _ in se._NUANCES_EURO_REGI_DPMT}
        assert not cles & se._CODES_VAGUE_B_NON_CLASSES

    def test_annees_disjointes_des_municipales(self) -> None:
        annees = {a for _, a, _, _ in se._NUANCES_EURO_REGI_DPMT}
        assert not annees & set(se._ANNEES_MUNI)

    def test_populate_vague_b_idempotent(self) -> None:
        c = duckdb.connect()
        se.create_elections_schema(c)
        se.populate_elections_referentiels(c)
        n0 = _n(c, "SELECT COUNT(*) FROM nuances_harmonisees")
        se.populate_nuances_vague_b(c)
        se.populate_nuances_vague_b(c)
        assert _n(c, "SELECT COUNT(*) FROM nuances_harmonisees") == n0
        assert _n(c, "SELECT COUNT(*) FROM candidats_presidentielle WHERE annee = 2019") == 32


class TestVuesHdF:
    """Les vues « HdF » excluent les autres départements quand la base est nationale."""

    def test_evolution_legi_et_muni_bornees_hdf(self, con) -> None:
        con.execute("""INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv, inscrits, votants, exprimes,
             code_circo) VALUES
            ('2022_legi_t1', '59', '59350', '0001', 100, 60, 50, '59-01'),
            ('2022_legi_t1', '75', '75056', '0001', 100, 60, 50, '75-01'),
            ('2020_muni_t1', '59', '59350', '0001', 100, 60, 50, NULL),
            ('2020_muni_t1', '75', '75056', '0001', 100, 60, 50, NULL)""")
        con.execute("""INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv, no_panneau, nuance, voix)
            VALUES
            ('2022_legi_t1', '59', '59350', '0001', 1, 'RN', 50),
            ('2022_legi_t1', '75', '75056', '0001', 1, 'ENS', 50),
            ('2020_muni_t1', '59', '59350', '0001', 1, 'LSOC', 50),
            ('2020_muni_t1', '75', '75056', '0001', 1, 'LREM', 50)""")
        assert con.execute("SELECT bloc FROM v_evolution_blocs_hdf_legi").fetchall() == [("EXD",)]
        spec = importlib.util.spec_from_file_location(
            "_m0007", ROOT / "scripts" / "migrations" / "0007_add_municipales_views.py"
        )
        assert spec is not None and spec.loader is not None
        m0007 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m0007)
        m0007._create_v_evolution_blocs_hdf_muni(con)
        rows = con.execute("SELECT bloc, pct_exprimes FROM v_evolution_blocs_hdf_muni").fetchall()
        assert rows == [("GAU", 100.0)]
