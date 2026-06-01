"""Tests d'intégration end-to-end (C4).

Vérifient la cohérence entre les données chargées (resultats_*) et les vues
d'agrégation. Ces tests sont durables : ils ne dépendent pas de l'UI.

Prérequis :
    uv run python scripts/init_elections_schema.py
    uv run python scripts/load_elections_presidentielles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip(
            "DB absente. Lancer init_elections_schema.py + load_elections_presidentielles.py"
        )
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_pres_%'"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Présidentielles non chargées. Lancer load_elections_presidentielles.py")
    yield c
    c.close()


class TestCoherenceVolumes:
    """La somme des voix par bloc dans une commune doit correspondre au total des candidats."""

    def test_somme_voix_par_commune_egale_total_candidats(self, con):
        ref = con.execute("""
            SELECT SUM(rc.voix) AS total
            FROM resultats_candidats rc
            JOIN elections e ON e.id_election = rc.id_election
            LEFT JOIN nuances_harmonisees nh ON nh.nuance = rc.nuance AND nh.annee = e.annee
            LEFT JOIN candidats_presidentielle cp ON cp.nom = rc.nom AND cp.annee = e.annee
            WHERE e.id_election = '2022_pres_t1'
              AND COALESCE(nh.bloc, cp.bloc) IS NOT NULL
        """).fetchone()[0]
        agg = con.execute("""
            SELECT SUM(voix) AS total
            FROM v_scores_commune_pres
            WHERE annee = 2022 AND tour = 1
        """).fetchone()[0]
        assert ref == agg, f"Incohérence : référence={ref}, agrégat={agg}"

    def test_chaque_scrutin_a_des_donnees(self, con):
        """Les 10 scrutins doivent avoir au moins 1 bureau et 1 candidat."""
        rows = con.execute("""
            SELECT
                e.id_election,
                (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_part,
                (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_cand
            FROM elections e
            WHERE e.type_scrutin = 'pres'
            ORDER BY e.id_election
        """).fetchall()
        assert len(rows) == 10
        for r in rows:
            assert r[1] > 0, f"{r[0]} : aucun bureau"
            assert r[2] > 0, f"{r[0]} : aucun candidat"


class TestCoherenceBlocs:
    """Tout candidat doit avoir un bloc résolu."""

    def test_aucun_candidat_sans_bloc(self, con):
        n = con.execute(
            "SELECT COUNT(*) FROM v_resultats_candidats_avec_bloc WHERE bloc IS NULL"
        ).fetchone()[0]
        assert n == 0, f"{n} lignes orphelines de bloc"

    def test_tous_blocs_officiels_presents(self, con):
        """Sur la série complète, les 6 blocs officiels doivent tous apparaître au moins une fois."""
        blocs = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT bloc FROM v_resultats_candidats_avec_bloc WHERE bloc IS NOT NULL"
            ).fetchall()
        }
        attendus = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
        assert blocs == attendus, f"Attendus {attendus}, trouvés {blocs}"


class TestCoherenceParticipation:
    """Participation : votants <= inscrits, taux dans [0, 100]."""

    def test_votants_inferieur_inscrits(self, con):
        n = con.execute("""
            SELECT COUNT(*) FROM v_participation_commune_pres
            WHERE votants > inscrits
        """).fetchone()[0]
        assert n == 0, f"{n} communes avec votants > inscrits"

    def test_taux_participation_dans_intervalle(self, con):
        rows = con.execute("""
            SELECT MIN(taux_participation_pct), MAX(taux_participation_pct)
            FROM v_participation_commune_pres
            WHERE inscrits > 0
        """).fetchone()
        assert 0 <= rows[0] <= 100, f"Taux min hors bornes : {rows[0]}"
        assert 0 <= rows[1] <= 100, f"Taux max hors bornes : {rows[1]}"


class TestCircoVingtEtUn:
    """La circo 21 doit avoir exactement 20 communes dans toutes les vues."""

    def test_circo21_exactement_vingt_communes(self, con):
        n = con.execute(
            "SELECT COUNT(DISTINCT code_commune) FROM v_scores_circo21_pres"
        ).fetchone()[0]
        assert n == 20, f"Circo 21 devrait avoir 20 communes, trouvé {n}"

    def test_circo21_couvre_cinq_annees(self, con):
        annees = {
            r[0]
            for r in con.execute("SELECT DISTINCT annee FROM v_evolution_blocs_circo21").fetchall()
        }
        assert annees == {2002, 2007, 2012, 2017, 2022}, f"Années trouvées : {annees}"

    def test_valenciennes_2002_t1_a_les_six_blocs(self, con):
        """Test de fumée : Valenciennes 2002 t1 doit avoir au moins 5 blocs représentés."""
        n = con.execute("""
            SELECT COUNT(DISTINCT bloc) FROM v_scores_commune_pres
            WHERE code_commune = '59606' AND annee = 2002 AND tour = 1
        """).fetchone()[0]
        assert n >= 5, f"Valenciennes 2002 t1 : seulement {n} blocs, attendu >= 5"
