"""Tests sanitaires des vues d'agrégation électorales (C2b).

Prérequis :
    uv run python scripts/init_elections_schema.py
    uv run python scripts/load_elections_presidentielles.py

Ces tests ouvrent la DB en read_only. Ils échouent explicitement si les données
ne sont pas chargées plutôt que de retourner des faux positifs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.etl.schema_elections import _CIRCO21_CODES

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_PRES_IDS = [
    "2002_pres_t1",
    "2002_pres_t2",
    "2007_pres_t1",
    "2007_pres_t2",
    "2012_pres_t1",
    "2012_pres_t2",
    "2017_pres_t1",
    "2017_pres_t2",
    "2022_pres_t1",
    "2022_pres_t2",
]


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("ministere.duckdb introuvable — lancer les scripts ETL d'abord")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")

    # Vérifie que les données sont chargées
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_pres_%'"
    ).fetchone()[0]
    if n == 0:
        c.close()
        pytest.skip("resultats_candidats vide — lancer load_elections_presidentielles.py d'abord")

    yield c
    c.close()


class TestVolumes:
    def test_participation_non_vide(self, con):
        n = con.execute(
            "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_pres_%'"
        ).fetchone()[0]
        assert n > 0, "resultats_participation vide pour les présidentielles"

    def test_dix_scrutins_charges(self, con):
        """Vérifie que les 10 scrutins présidentiels ont des données."""
        rows = con.execute("""
            SELECT id_election, COUNT(*) AS n
            FROM resultats_candidats
            WHERE id_election LIKE '%_pres_%'
            GROUP BY id_election
        """).fetchall()
        ids_charges = {r[0] for r in rows}
        manquants = set(_PRES_IDS) - ids_charges
        assert not manquants, f"Scrutins sans données : {manquants}"

    def test_communes_hdf_uniquement(self, con):
        """Aucune commune hors HdF ne doit être présente."""
        n_hors_hdf = con.execute("""
            SELECT COUNT(DISTINCT rc.code_commune)
            FROM resultats_candidats rc
            LEFT JOIN geographies_communes gc ON gc.code_insee = rc.code_commune
            WHERE rc.id_election LIKE '%_pres_%'
              AND (gc.code_region IS NULL OR gc.code_region != '32')
        """).fetchone()[0]
        assert n_hors_hdf == 0, f"{n_hors_hdf} communes hors HdF trouvées"


class TestResolutionBloc:
    def test_aucun_candidat_sans_bloc(self, con):
        """Critique : chaque ligne de v_resultats_candidats_avec_bloc doit avoir un bloc."""
        rows = con.execute("""
            SELECT id_election, COUNT(*) AS n_orphelins
            FROM v_resultats_candidats_avec_bloc
            WHERE bloc IS NULL
            GROUP BY id_election
        """).fetchall()
        assert not rows, (
            f"Candidats sans bloc résolu : {rows}. "
            "Vérifier nuances_harmonisees et candidats_presidentielle."
        )

    def test_blocs_valides_uniquement(self, con):
        """Tous les blocs résolus doivent exister dans blocs_politiques."""
        rows = con.execute("""
            SELECT DISTINCT v.bloc
            FROM v_resultats_candidats_avec_bloc v
            WHERE v.bloc NOT IN (SELECT bloc FROM blocs_politiques)
        """).fetchall()
        assert not rows, f"Blocs inconnus dans les résultats : {[r[0] for r in rows]}"

    def test_tous_blocs_presents_2022_t1(self, con):
        """Le t1 2022 doit couvrir les 6 blocs officiels au minimum."""
        blocs = {
            r[0]
            for r in con.execute("""
                SELECT DISTINCT bloc
                FROM v_resultats_candidats_avec_bloc
                WHERE id_election = '2022_pres_t1'
            """).fetchall()
        }
        attendus = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
        manquants = attendus - blocs
        assert not manquants, f"Blocs absents en 2022 t1 : {manquants}"


class TestVuesCommune:
    def test_valenciennes_2002_t1_a_tous_les_blocs(self, con):
        """Sanity check : Valenciennes 2002 t1 doit avoir des voix dans plusieurs blocs."""
        rows = con.execute("""
            SELECT bloc, voix
            FROM v_scores_commune_pres
            WHERE code_commune = '59606' AND annee = 2002 AND tour = 1
            ORDER BY voix DESC
        """).fetchall()
        assert len(rows) >= 5, f"Valenciennes 2002 t1 : seulement {len(rows)} blocs, attendu ≥5"
        total_voix = sum(r[1] for r in rows)
        assert total_voix > 1000, f"Total voix Valenciennes 2002 t1 trop faible : {total_voix}"

    def test_participation_valenciennes_2022(self, con):
        """Taux de participation calculé et cohérent pour Valenciennes 2022."""
        row = con.execute("""
            SELECT taux_participation_pct, inscrits, votants
            FROM v_participation_commune_pres
            WHERE code_commune = '59606' AND annee = 2022 AND tour = 1
        """).fetchone()
        assert row is not None, "Participation Valenciennes 2022 t1 absente"
        taux, inscrits, votants = row
        assert 0 < taux < 100, f"Taux participation hors plage : {taux}"
        assert votants <= inscrits, "votants > inscrits — incohérence"


class TestCirco21:
    def test_circo21_contient_20_communes(self, con):
        """v_scores_circo21_pres doit couvrir exactement 20 communes distinctes."""
        n = con.execute("""
            SELECT COUNT(DISTINCT code_commune)
            FROM v_scores_circo21_pres
            WHERE annee = 2022 AND tour = 1
        """).fetchone()[0]
        assert n == len(_CIRCO21_CODES), (
            f"Circo 21 : {n} communes trouvées, attendu {len(_CIRCO21_CODES)}"
        )

    def test_evolution_circo21_cinq_annees(self, con):
        """L'évolution doit couvrir les 5 présidentielles (t1)."""
        annees = {
            r[0]
            for r in con.execute("""
                SELECT DISTINCT annee
                FROM v_evolution_blocs_circo21
                WHERE tour = 1
            """).fetchall()
        }
        assert annees == {2002, 2007, 2012, 2017, 2022}, (
            f"Années manquantes dans v_evolution_blocs_circo21 : {annees}"
        )

    def test_valenciennes_dans_circo21(self, con):
        """59606 (Valenciennes) doit être dans v_scores_circo21_pres."""
        n = con.execute("""
            SELECT COUNT(*)
            FROM v_scores_circo21_pres
            WHERE code_commune = '59606' AND annee = 2022 AND tour = 1
        """).fetchone()[0]
        assert n > 0, "Valenciennes absente de v_scores_circo21_pres"
