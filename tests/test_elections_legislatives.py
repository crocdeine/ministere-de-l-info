"""Tests d'intégration — législatives HdF 2002-2024 (Phase D1.2).

Vérifient la cohérence des données législatives chargées et la reconstruction
de code_circo (direct ou jointure spatiale selon le scrutin).

Prérequis :
    uv run python scripts/init_elections_schema.py
    uv run python scripts/load_elections_legislatives.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

# Scrutins législatifs attendus (12 = 6 années × 2 tours)
_LEGI_SCRUTINS = [f"{a}_legi_t{t}" for a in (2002, 2007, 2012, 2017, 2022, 2024) for t in (1, 2)]
# Scrutins à code_circonscription natif (couverture attendue 100 %)
_NATIFS = ("2012_legi_t1", "2017_legi_t1", "2022_legi_t1")
# Scrutins reconstruits par jointure spatiale (couverture attendue > 95 %)
_SPATIAUX = ("2002_legi_t1", "2007_legi_t1", "2024_legi_t1")


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer init_elections_schema.py + load_elections_legislatives.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_legi_%'"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Législatives non chargées. Lancer load_elections_legislatives.py")
    yield c
    c.close()


class TestVolumes:
    """Chacun des 12 scrutins doit avoir des bureaux et des candidats."""

    def test_douze_scrutins_avec_donnees(self, con):
        rows = con.execute("""
            SELECT
                e.id_election,
                (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_part,
                (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_cand
            FROM elections e
            WHERE e.type_scrutin = 'legi'
            ORDER BY e.id_election
        """).fetchall()
        assert len(rows) == 12, f"Attendu 12 scrutins legi, trouvé {len(rows)}"
        for idel, n_part, n_cand in rows:
            assert n_part > 0, f"{idel} : aucun bureau"
            assert n_cand > 0, f"{idel} : aucun candidat"

    def test_volume_global_plausible(self, con):
        """Ordre de grandeur conforme au chargement (HdF, BV-level)."""
        n_part = con.execute(
            "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_legi_%'"
        ).fetchone()[0]
        n_cand = con.execute(
            "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_legi_%'"
        ).fetchone()[0]
        assert 50_000 < n_part < 120_000, f"participation hors plage : {n_part}"
        assert 400_000 < n_cand < 600_000, f"candidats hors plage : {n_cand}"


class TestBlocs:
    """Test critique : aucun candidat législatif orphelin de bloc."""

    def test_aucun_candidat_orphelin_de_bloc(self, con):
        """Toute (nuance, annee) législative doit exister dans nuances_harmonisees."""
        orphelins = con.execute("""
            SELECT DISTINCT rc.nuance, e.annee
            FROM resultats_candidats rc
            JOIN elections e ON e.id_election = rc.id_election
            LEFT JOIN nuances_harmonisees nh ON nh.nuance = rc.nuance AND nh.annee = e.annee
            WHERE e.type_scrutin = 'legi' AND nh.bloc IS NULL
        """).fetchall()
        assert orphelins == [], f"Nuances orphelines de bloc : {orphelins}"

    def test_pas_de_nuance_null(self, con):
        n = con.execute("""
            SELECT COUNT(*) FROM resultats_candidats rc
            JOIN elections e ON e.id_election = rc.id_election
            WHERE e.type_scrutin = 'legi' AND rc.nuance IS NULL
        """).fetchone()[0]
        assert n == 0, f"{n} candidats legi sans nuance"

    def test_111_nuances_legislatives_dans_le_referentiel(self, con):
        """Les 111 entrées législatives validées sont chargées dans nuances_harmonisees."""
        from ministere_de_l_info.etl.schema_elections import _NUANCES_LEGI

        assert len(_NUANCES_LEGI) == 111, (
            f"_NUANCES_LEGI : {len(_NUANCES_LEGI)} entrées (attendu 111)"
        )
        manquantes = [
            (nuance, annee, bloc)
            for (nuance, annee, bloc, _src) in _NUANCES_LEGI
            if con.execute(
                "SELECT bloc FROM nuances_harmonisees WHERE nuance = ? AND annee = ?",
                [nuance, annee],
            ).fetchone()
            != (bloc,)
        ]
        assert manquantes == [], f"Entrées absentes/divergentes : {manquantes[:10]}"
        # source_bloc renseigné sur 100 % des entrées (modèle candidats_presidentielle)
        n_null = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE source_bloc IS NULL OR source_bloc = ''"
        ).fetchone()[0]
        assert n_null == 0, f"{n_null} entrées sans source_bloc"


class TestCodeCirco:
    """Reconstruction de code_circo : couverture et format."""

    def test_couverture_100pct_scrutins_natifs(self, con):
        for idel in _NATIFS:
            total, ok = con.execute(
                "SELECT COUNT(*), COUNT(code_circo) FROM resultats_participation WHERE id_election = ?",
                [idel],
            ).fetchone()
            assert total > 0 and ok == total, f"{idel} : code_circo {ok}/{total} (attendu 100 %)"

    def test_couverture_sup_95pct_scrutins_spatiaux(self, con):
        for idel in _SPATIAUX:
            total, ok = con.execute(
                "SELECT COUNT(*), COUNT(code_circo) FROM resultats_participation WHERE id_election = ?",
                [idel],
            ).fetchone()
            pct = 100.0 * ok / total if total else 0.0
            assert pct > 95.0, f"{idel} : couverture code_circo {pct:.1f} % (attendu > 95 %)"

    def test_format_code_circo(self, con):
        """Format 'DPT-NN' : 2-3 chiffres, tiret, 2 chiffres."""
        codes = [
            r[0]
            for r in con.execute("""
                SELECT DISTINCT code_circo FROM resultats_participation rp
                JOIN elections e ON e.id_election = rp.id_election
                WHERE e.type_scrutin = 'legi' AND rp.code_circo IS NOT NULL
            """).fetchall()
        ]
        pat = re.compile(r"^\d{2,3}-\d{2}$")
        invalides = [c for c in codes if not pat.match(c)]
        assert invalides == [], f"Codes circo invalides : {invalides[:10]}"

    def test_cinquante_circos_hdf(self, con):
        """HdF = 50 circonscriptions (02:5, 59:21, 60:7, 62:12, 80:5)."""
        n = con.execute("""
            SELECT COUNT(DISTINCT code_circo) FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'legi' AND e.tour = 1 AND rp.code_circo IS NOT NULL
        """).fetchone()[0]
        assert n == 50, f"Attendu 50 circos HdF, trouvé {n}"


class TestParticipation:
    """Cohérence participation au niveau circonscription."""

    def test_votants_inferieur_inscrits(self, con):
        n = con.execute(
            "SELECT COUNT(*) FROM v_participation_circo_legi WHERE votants > inscrits"
        ).fetchone()[0]
        assert n == 0, f"{n} circos avec votants > inscrits"

    def test_taux_dans_intervalle(self, con):
        mn, mx = con.execute("""
            SELECT MIN(taux_participation_pct), MAX(taux_participation_pct)
            FROM v_participation_circo_legi WHERE inscrits > 0
        """).fetchone()
        assert 0 <= mn <= 100, f"taux min hors bornes : {mn}"
        assert 0 <= mx <= 100, f"taux max hors bornes : {mx}"


class TestCircoVingtEtUnLegi:
    """Test concret : circo 21 Nord (Valenciennes, 59-21) en 2022 t1."""

    def test_valenciennes_2022_t1_blocs_majeurs(self, con):
        rows = con.execute("""
            SELECT bloc, voix FROM v_scores_circo_legi
            WHERE code_circo = '59-21' AND annee = 2022 AND tour = 1
        """).fetchall()
        blocs = {b for b, _ in rows}
        # Blocs majeurs réellement présents dans cette circo en 2022 (pas d'Ensemble/CENT)
        assert {"GAU", "DTE", "EXD"}.issubset(blocs), f"Blocs majeurs manquants : {blocs}"
        assert len(rows) >= 4, f"Attendu >= 4 blocs, trouvé {len(rows)}"
        for bloc, voix in rows:
            assert voix > 0, f"Bloc {bloc} : voix = {voix}"
