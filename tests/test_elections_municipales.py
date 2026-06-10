"""Tests d'intégration — municipales HdF 2008-2026 (Phase D3.2).

Vérifient la cohérence des données municipales chargées, le mapping nuances,
et les 3 vues d'agrégation créées en D3.2.

Prérequis :
    uv run python scripts/migrations/0006_add_municipales_schema.py
    uv run python scripts/load_elections_municipales.py
    uv run python scripts/migrations/0007_add_municipales_views.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))  # pour importer scripts.*

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_MUNI_SCRUTINS = [f"{a}_muni_t{t}" for a in (2008, 2014, 2020, 2026) for t in (1, 2)]

# Volumes BV attendus (source : rapport D3.1)
_VOLUMES_BV = {
    "2008_muni_t1": 1_240,
    "2008_muni_t2": 500,
    "2014_muni_t1": 6_434,
    "2014_muni_t2": 2_051,
    "2020_muni_t1": 6_514,
    "2020_muni_t2": 1_383,
    "2026_muni_t1": 6_546,
    "2026_muni_t2": 1_193,
}

# Volumes communes attendus
_VOLUMES_COMMUNES = {
    "2008_muni_t1": 164,
    "2008_muni_t2": 50,
    "2014_muni_t1": 3_778,
    "2014_muni_t2": 778,
    "2020_muni_t1": 3_779,
    "2020_muni_t2": 560,
    "2026_muni_t1": 3_779,
    "2026_muni_t2": 182,
}


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer load_elections_municipales.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_muni_%'"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Municipales non chargées. Lancer load_elections_municipales.py")
    yield c
    c.close()


class TestVolumesParScrutin:
    """8 scrutins avec les volumes BV et communes conformes au rapport D3.1."""

    def test_huit_scrutins_avec_donnees(self, con):
        rows = con.execute("""
            SELECT e.id_election,
                (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_bv,
                (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_listes
            FROM elections e
            WHERE e.type_scrutin = 'muni'
            ORDER BY e.id_election
        """).fetchall()
        assert len(rows) == 8, f"Attendu 8 scrutins muni, trouvé {len(rows)}"
        for idel, n_bv, n_listes in rows:
            assert n_bv > 0, f"{idel} : aucun BV"
            assert n_listes > 0, f"{idel} : aucune liste"

    def test_volumes_bv_conformes_rapport_d31(self, con):
        for idel, attendu in _VOLUMES_BV.items():
            n = con.execute(
                "SELECT COUNT(*) FROM resultats_participation WHERE id_election = ?", [idel]
            ).fetchone()[0]
            assert n == attendu, f"{idel} BV : {n} (attendu {attendu})"

    def test_volumes_communes_conformes_rapport_d31(self, con):
        for idel, attendu in _VOLUMES_COMMUNES.items():
            n = con.execute(
                "SELECT COUNT(DISTINCT code_commune) FROM resultats_participation WHERE id_election = ?",
                [idel],
            ).fetchone()[0]
            assert n == attendu, f"{idel} communes : {n} (attendu {attendu})"

    def test_volume_global_plausible(self, con):
        n_part = con.execute(
            "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_muni_%'"
        ).fetchone()[0]
        n_cand = con.execute(
            "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_muni_%'"
        ).fetchone()[0]
        assert 20_000 < n_part < 35_000, f"participation hors plage : {n_part}"
        assert 100_000 < n_cand < 200_000, f"candidats hors plage : {n_cand}"


class TestNuancesHarmonisees:
    """67 entrées municipales dans nuances_harmonisees, ventilation par année."""

    def test_67_entrees_municipales(self, con):
        from scripts.load_elections_municipales import _NUANCES_MUNI

        assert len(_NUANCES_MUNI) == 67, (
            f"_NUANCES_MUNI : {len(_NUANCES_MUNI)} entrées (attendu 67)"
        )
        n_db = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee IN (2008,2014,2020,2026)"
        ).fetchone()[0]
        assert n_db == 67, f"nuances_harmonisees muni : {n_db} (attendu 67)"

    def test_ventilation_par_annee(self, con):
        attendus = {2008: 12, 2014: 17, 2020: 19, 2026: 19}
        for annee, n_att in attendus.items():
            n = con.execute(
                "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee = ?", [annee]
            ).fetchone()[0]
            assert n == n_att, f"nuances_harmonisees {annee} : {n} (attendu {n_att})"

    def test_pres_legi_preservees(self, con):
        """Les 149 entrées pres/legi ne doivent pas avoir été écrasées."""
        n = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee NOT IN (2008,2014,2020,2026)"
        ).fetchone()[0]
        assert n == 149, f"Entrées pres/legi : {n} (attendu 149)"

    def test_toutes_les_entrees_ont_source_bloc(self, con):
        n_null = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees "
            "WHERE annee IN (2008,2014,2020,2026) AND (source_bloc IS NULL OR source_bloc = '')"
        ).fetchone()[0]
        assert n_null == 0, f"{n_null} entrées muni sans source_bloc"


class TestLFIBascule:
    """Test critique : LFI classé GAU en 2020, EXG en 2026 (bascule INTP2602966C)."""

    def test_lfi_2020_est_gau(self, con):
        bloc = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance='LFI' AND annee=2020"
        ).fetchone()
        assert bloc is not None, "LFI 2020 absent de nuances_harmonisees"
        assert bloc[0] == "GAU", f"LFI 2020 → {bloc[0]} (attendu GAU)"

    def test_lfi_2026_est_exg(self, con):
        bloc = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance='LFI' AND annee=2026"
        ).fetchone()
        assert bloc is not None, "LFI 2026 absent de nuances_harmonisees"
        assert bloc[0] == "EXG", f"LFI 2026 → {bloc[0]} (attendu EXG)"

    def test_exactement_deux_entrees_lfi(self, con):
        n = con.execute("SELECT COUNT(*) FROM nuances_harmonisees WHERE nuance='LFI'").fetchone()[0]
        assert n == 2, f"LFI : {n} entrées (attendu exactement 2 : 2020+2026)"


class TestCodesSansMapping:
    """NC, LMAJ, LNC doivent être absents de nuances_harmonisees."""

    @pytest.mark.parametrize("code", ["NC", "LMAJ", "LNC"])
    def test_code_absent_de_nuances_harmonisees(self, con, code):
        n = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees "
            "WHERE nuance = ? AND annee IN (2008,2014,2020,2026)",
            [code],
        ).fetchone()[0]
        assert n == 0, f"{code} trouvé dans nuances_harmonisees ({n} entrées) — doit être absent"


class TestDecisionsStructurantes:
    """Vérifications des décisions validées en D3.1.2."""

    def test_lcmd_2008_est_gau(self, con):
        """LCMD 2008 → GAU (analyse contextuelle, libellés Parquet NULL, bassin minier HdF)."""
        row = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance='LCMD' AND annee=2008"
        ).fetchone()
        assert row is not None, "LCMD 2008 absent"
        assert row[0] == "GAU", f"LCMD 2008 → {row[0]} (attendu GAU)"

    def test_ldvc_2020_est_cent_avec_source_ce_437675(self, con):
        """LDVC 2020 → CENT per CE 31/01/2020 n°437675."""
        row = con.execute(
            "SELECT bloc, source_bloc FROM nuances_harmonisees WHERE nuance='LDVC' AND annee=2020"
        ).fetchone()
        assert row is not None, "LDVC 2020 absent"
        assert row[0] == "CENT", f"LDVC 2020 → {row[0]} (attendu CENT)"
        assert "437675" in row[1], f"source_bloc ne cite pas CE 437675 : {row[1]}"

    def test_ludr_2026_est_exd(self, con):
        """LUDR 2026 → EXD, nouveau code per INTP2602966C + CE 512694."""
        row = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance='LUDR' AND annee=2026"
        ).fetchone()
        assert row is not None, "LUDR 2026 absent"
        assert row[0] == "EXD", f"LUDR 2026 → {row[0]} (attendu EXD)"

    def test_lfg_2014_est_gau(self, con):
        """LFG 2014 → GAU (Front de Gauche, bascule EXG concerne LFI/2026 seulement)."""
        row = con.execute(
            "SELECT bloc FROM nuances_harmonisees WHERE nuance='LFG' AND annee=2014"
        ).fetchone()
        assert row is not None, "LFG 2014 absent"
        assert row[0] == "GAU", f"LFG 2014 → {row[0]} (attendu GAU)"


class TestVueScoresCommune:
    """v_scores_commune_muni : agrégation par bloc et commune."""

    def test_vue_existe_et_non_vide(self, con):
        n = con.execute("SELECT COUNT(*) FROM v_scores_commune_muni").fetchone()[0]
        assert n > 10_000, f"v_scores_commune_muni : {n} lignes (attendu > 10 000)"

    def test_lille_2020_t1_blocs_cohérents(self, con):
        """Lille 2020 t1 : tous les blocs couverts, voix positives, somme = exprimes."""
        rows = con.execute("""
            SELECT bloc, voix, pct_exprimes
            FROM v_scores_commune_muni
            WHERE code_commune='59350' AND annee=2020 AND tour=1
        """).fetchall()
        blocs = {r[0] for r in rows}
        assert {"GAU", "CENT", "DTE", "EXD", "EXG", "DIV"}.issubset(blocs), (
            f"Blocs manquants à Lille 2020 t1 : {blocs}"
        )
        for bloc, voix, pct in rows:
            assert voix > 0, f"Lille 2020 t1 {bloc} : voix = {voix}"
            assert 0 < pct <= 100, f"Lille 2020 t1 {bloc} : pct_exprimes = {pct} hors bornes"
        total_pct = sum(r[2] for r in rows)
        assert 99.0 <= total_pct <= 101.0, f"Somme pct_exprimes Lille 2020 t1 = {total_pct}"

    def test_pas_de_pct_hors_bornes(self, con):
        n = con.execute("""
            SELECT COUNT(*) FROM v_scores_commune_muni
            WHERE pct_exprimes < 0 OR pct_exprimes > 100
        """).fetchone()[0]
        assert n == 0, f"{n} lignes avec pct_exprimes hors [0,100]"


class TestVueEvolutionBlocs:
    """v_evolution_blocs_hdf_muni : cohérence HdF × scrutin."""

    def test_vue_existe_et_8_scrutins(self, con):
        n_scrutins = con.execute(
            "SELECT COUNT(DISTINCT annee || '_' || tour) FROM v_evolution_blocs_hdf_muni"
        ).fetchone()[0]
        assert n_scrutins == 8, f"Attendu 8 scrutins, trouvé {n_scrutins}"

    def test_pct_exprimes_nul_pour_bloc_null(self, con):
        """pct_exprimes = NULL pour bloc=NULL : communes plurinominales (< 1000 hab).

        La sémantique voix est candidat (plurinominal) et non liste pour ces communes,
        rendant le % non comparable aux blocs politiques des communes ≥ seuil.
        """
        n_non_null = con.execute("""
            SELECT COUNT(*) FROM v_evolution_blocs_hdf_muni
            WHERE bloc IS NULL AND pct_exprimes IS NOT NULL
        """).fetchone()[0]
        assert n_non_null == 0, f"{n_non_null} lignes bloc=NULL avec pct_exprimes non-NULL"

    def test_pct_exprimes_blocs_nommes_dans_intervalle(self, con):
        """Pour les blocs nommés, pct_exprimes ∈ ]0, 100]."""
        rows = con.execute("""
            SELECT bloc, pct_exprimes FROM v_evolution_blocs_hdf_muni
            WHERE bloc IS NOT NULL AND (pct_exprimes IS NULL OR pct_exprimes <= 0 OR pct_exprimes > 100)
        """).fetchall()
        assert rows == [], f"Lignes blocs nommés avec pct hors ]0,100] : {rows[:5]}"

    def test_voix_positifs_tous_scrutins(self, con):
        n = con.execute(
            "SELECT COUNT(*) FROM v_evolution_blocs_hdf_muni WHERE voix <= 0"
        ).fetchone()[0]
        assert n == 0, f"{n} lignes avec voix <= 0"


class TestVueListes:
    """v_listes_commune_muni : détail liste par liste pour le drill-down."""

    def test_vue_existe_et_non_vide(self, con):
        n = con.execute("SELECT COUNT(*) FROM v_listes_commune_muni").fetchone()[0]
        assert n > 10_000, f"v_listes_commune_muni : {n} lignes (attendu > 10 000)"

    def test_valenciennes_2026_t1_libelles_renseignes(self, con):
        """Valenciennes 2026 t1 : les libellés de liste doivent être non-NULL (données 2026)."""
        rows = con.execute("""
            SELECT nuance, libelle_abrege_liste, voix
            FROM v_listes_commune_muni
            WHERE code_commune='59606' AND annee=2026 AND tour=1
            ORDER BY voix DESC
        """).fetchall()
        assert len(rows) >= 2, f"Valenciennes 2026 t1 : {len(rows)} liste(s) (attendu >= 2)"
        for nuance, libelle, voix in rows:
            assert libelle is not None, f"Valenciennes 2026 t1 {nuance} : libelle NULL"
            assert voix > 0, f"Valenciennes 2026 t1 {nuance} : voix = {voix}"

    def test_lille_2020_t1_lfi_est_gau(self, con):
        """À Lille 2020 t1, LFI doit être classé GAU (pas EXG)."""
        row = con.execute("""
            SELECT nuance, bloc, voix
            FROM v_listes_commune_muni
            WHERE code_commune='59350' AND annee=2020 AND tour=1 AND nuance='LFI'
        """).fetchone()
        assert row is not None, "LFI absent à Lille 2020 t1"
        assert row[1] == "GAU", f"LFI à Lille 2020 t1 → {row[1]} (attendu GAU)"


class TestCommunesSansNuance2026:
    """2026 : ~3 459 communes HdF avec nuance NULL (seuil 3 500 hab)."""

    def test_communes_sans_nuance_2026_t1(self, con):
        n_sans = con.execute("""
            SELECT COUNT(DISTINCT code_commune)
            FROM resultats_candidats
            WHERE id_election = '2026_muni_t1' AND nuance IS NULL
        """).fetchone()[0]
        assert 3_400 <= n_sans <= 3_520, f"Communes sans nuance 2026 t1 : {n_sans} (attendu ~3 459)"

    def test_communes_avec_nuance_2026_t1(self, con):
        n_avec = con.execute("""
            SELECT COUNT(DISTINCT code_commune)
            FROM resultats_candidats
            WHERE id_election = '2026_muni_t1' AND nuance IS NOT NULL
        """).fetchone()[0]
        assert 310 <= n_avec <= 330, f"Communes avec nuance 2026 t1 : {n_avec} (attendu ~320)"

    def test_null_bloc_dans_vue_scores_2026(self, con):
        """v_scores_commune_muni : bloc NULL présent en 2026 (communes sans nuance)."""
        n_null = con.execute("""
            SELECT COUNT(*)
            FROM v_scores_commune_muni
            WHERE annee=2026 AND tour=1 AND bloc IS NULL
        """).fetchone()[0]
        assert n_null > 3_000, f"Lignes bloc=NULL en 2026 t1 : {n_null} (attendu > 3 000)"
