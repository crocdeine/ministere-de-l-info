"""Tests d'intégration — module Économie (Phase E3).

Vérifient la cohérence des données Filosofi + RP chargées,
le secret statistique INSEE, et les 3 vues du module Économie.

Prérequis :
    uv run python scripts/load_economie.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

DB_PATH = _ROOT / "data" / "ministere.duckdb"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer : uv run python scripts/load_economie.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    n = c.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0]
    if n == 0:
        pytest.skip(
            "Données économiques non chargées. Lancer : uv run python scripts/load_economie.py"
        )
    yield c
    c.close()


def test_economie_data_loaded(con):
    """Les 2 tables économiques contiennent des données."""
    n_f = con.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0]
    n_r = con.execute("SELECT COUNT(*) FROM economie_rp").fetchone()[0]
    assert n_f > 0, "economie_filosofi est vide"
    assert n_r > 0, "economie_rp est vide"


def test_economie_filosofi_count(con):
    """Au moins 3 000 communes HdF avec données Filosofi pour 2021."""
    n = con.execute("SELECT COUNT(*) FROM economie_filosofi WHERE annee = 2021").fetchone()[0]
    assert n > 3000, f"Attendu >3000 communes pour Filosofi 2021, trouvé {n}"


def test_economie_rp_count(con):
    """Au moins 3 000 communes HdF avec données RP pour 2020."""
    n = con.execute("SELECT COUNT(*) FROM economie_rp WHERE annee_millesime = 2020").fetchone()[0]
    assert n > 3000, f"Attendu >3000 communes pour RP 2020, trouvé {n}"


def test_economie_filosofi_lille(con):
    """Lille (59350) 2021 : taux de pauvreté voisin de 27 %."""
    row = con.execute(
        "SELECT taux_pauvrete FROM economie_filosofi WHERE code_commune = '59350' AND annee = 2021"
    ).fetchone()
    assert row is not None, "Lille 59350 absente de economie_filosofi 2021"
    tp = row[0]
    assert tp is not None, "taux_pauvrete NULL pour Lille 2021"
    assert 22.0 < tp < 32.0, f"taux_pauvrete Lille 2021 hors plage attendue : {tp:.1f}%"


def test_economie_rp_lille(con):
    """Lille (59350) 2020 : taux de chômage déclaratif dans la plage 14-22 %."""
    row = con.execute(
        "SELECT tx_chomage_dec FROM economie_rp WHERE code_commune = '59350' AND annee_millesime = 2020"
    ).fetchone()
    assert row is not None, "Lille 59350 absente de economie_rp 2020"
    tc = row[0]
    assert tc is not None, "tx_chomage_dec NULL pour Lille 2020"
    assert 14.0 < tc < 22.0, f"tx_chomage_dec Lille 2020 hors plage attendue : {tc:.1f}%"


def test_economie_logements_sociaux(con):
    """Lille (59350) 2020 : part de logements sociaux dans la plage 19-26 %."""
    row = con.execute(
        "SELECT part_logements_sociaux, nb_logements_sociaux "
        "FROM economie_rp WHERE code_commune = '59350' AND annee_millesime = 2020"
    ).fetchone()
    assert row is not None, "Lille 59350 absente de economie_rp 2020"
    pls, nls = row
    assert pls is not None, "part_logements_sociaux NULL pour Lille 2020"
    assert nls is not None, "nb_logements_sociaux NULL pour Lille 2020"
    assert 19.0 < pls < 26.0, f"part_logements_sociaux Lille 2020 hors plage : {pls:.1f}%"
    assert nls > 20_000, f"nb_logements_sociaux Lille 2020 anormalement bas : {nls}"


def test_economie_secret_statistique(con):
    """Des communes ont le secret statistique INSEE (secret = TRUE)."""
    n_secret_f = con.execute(
        "SELECT COUNT(*) FROM economie_filosofi WHERE secret = TRUE"
    ).fetchone()[0]
    n_secret_r = con.execute("SELECT COUNT(*) FROM economie_rp WHERE secret = TRUE").fetchone()[0]
    assert n_secret_f > 0 or n_secret_r > 0, (
        "Aucune ligne avec secret=TRUE — vérifier la logique de détection du secret INSEE"
    )


def test_vue_economie_commune(con):
    """v_economie_commune retourne des lignes et expose les colonnes attendues."""
    rows = con.execute(
        "SELECT code_commune, annee, taux_pauvrete, tx_chomage_dec, "
        "part_logements_sociaux, pop_active "
        "FROM v_economie_commune LIMIT 10"
    ).fetchall()
    assert len(rows) > 0, "v_economie_commune est vide"
    # Au moins une ligne avec des données non NULL
    has_data = any(r[2] is not None or r[3] is not None for r in rows)
    assert has_data, "Toutes les lignes de v_economie_commune ont des indicateurs NULL"


def test_vue_evolution_hdf(con):
    """v_evolution_economie_hdf retourne exactement 5 lignes (2017-2021)."""
    rows = con.execute(
        "SELECT annee, taux_pauvrete_moyen, niveau_vie_median_hdf, tx_chomage_moyen "
        "FROM v_evolution_economie_hdf ORDER BY annee"
    ).fetchall()
    assert len(rows) == 5, f"Attendu 5 lignes (2017-2021), trouvé {len(rows)}"
    annees = [r[0] for r in rows]
    assert annees == [2017, 2018, 2019, 2020, 2021], f"Années inattendues : {annees}"
    # Valeurs agrégées non NULL pour au moins 2021
    r2021 = next(r for r in rows if r[0] == 2021)
    assert r2021[1] is not None, "taux_pauvrete_moyen NULL pour 2021"


def test_code_commune_varchar(con):
    """code_commune est stocké en VARCHAR — la comparaison string fonctionne sans cast."""
    # Si code_commune était INTEGER, '59350' ne correspondrait pas sans CAST
    row = con.execute(
        "SELECT code_commune FROM economie_filosofi WHERE code_commune = '59350' LIMIT 1"
    ).fetchone()
    assert row is not None, "code_commune '59350' introuvable — peut-être stocké en INTEGER ?"
    assert row[0] == "59350", f"Valeur inattendue : {row[0]!r}"
    # Vérifier aussi le format 5 caractères pour un département à zéro préfixant
    row_aisne = con.execute(
        "SELECT code_commune FROM economie_filosofi WHERE LEFT(code_commune, 2) = '02' LIMIT 1"
    ).fetchone()
    if row_aisne:
        assert len(row_aisne[0]) == 5, f"code_commune pas en 5 chars : {row_aisne[0]!r}"


# ── Tests Phase E+ (CNAF, URSSAF, DREES) ──────────────────────────────────────
# Ces tests nécessitent que les loaders cnaf/urssaf/drees aient été exécutés
# via scripts/load_economie.py --source social ou --source all.


@pytest.fixture(scope="module")
def con_social(con) -> duckdb.DuckDBPyConnection:
    """Fixture : passe si economie_social contient des données RSA (CNAF chargé)."""
    n = con.execute(
        "SELECT COUNT(*) FROM economie_social WHERE nb_foyers_rsa IS NOT NULL"
    ).fetchone()[0]
    if n == 0:
        pytest.skip(
            "Données CNAF non chargées. Lancer : uv run python scripts/load_economie.py --source cnaf"
        )
    return con


@pytest.fixture(scope="module")
def con_urssaf(con) -> duckdb.DuckDBPyConnection:
    """Fixture : passe si economie_emploi_urssaf contient des données."""
    n = con.execute("SELECT COUNT(*) FROM economie_emploi_urssaf").fetchone()[0]
    if n == 0:
        pytest.skip(
            "Données URSSAF non chargées. Lancer : uv run python scripts/load_economie.py --source urssaf"
        )
    return con


def test_cnaf_data_loaded(con_social):
    """economie_social contient des données RSA."""
    n = con_social.execute(
        "SELECT COUNT(*) FROM economie_social WHERE nb_foyers_rsa IS NOT NULL"
    ).fetchone()[0]
    assert n > 1000, f"Trop peu de communes avec données RSA : {n}"


def test_cnaf_lille(con_social):
    """Lille (59350) 2024 : nb_foyers_rsa ~11 000 (±1 000)."""
    row = con_social.execute(
        "SELECT nb_foyers_rsa FROM economie_social WHERE code_commune = '59350' AND annee = 2024"
    ).fetchone()
    assert row is not None, "Lille 59350 absente de economie_social 2024 — CNAF chargé ?"
    nfr = row[0]
    assert nfr is not None, "nb_foyers_rsa NULL pour Lille 2024"
    assert 10_000 < nfr < 12_000, f"nb_foyers_rsa Lille 2024 hors plage attendue : {nfr:,}"


def test_urssaf_data_loaded(con_urssaf):
    """economie_emploi_urssaf contient des données."""
    n = con_urssaf.execute("SELECT COUNT(*) FROM economie_emploi_urssaf").fetchone()[0]
    assert n > 100_000, f"Trop peu de lignes URSSAF HdF : {n:,}"


def test_urssaf_industrie_hdf(con_urssaf):
    """Des lignes GS1 Industrie existent pour HdF avec des effectifs > 0."""
    n = con_urssaf.execute(
        "SELECT COUNT(*) FROM economie_emploi_urssaf "
        "WHERE secteur_gs LIKE '%Industrie%' AND nb_salaries > 0"
    ).fetchone()[0]
    assert n > 0, "Aucune ligne secteur Industrie avec salariés > 0 — vérifier secteur_gs"


def test_drees_apl_loaded(con_social):
    """economie_social contient des données APL (DREES chargé)."""
    n = con_social.execute(
        "SELECT COUNT(*) FROM economie_social WHERE apl_medecins IS NOT NULL"
    ).fetchone()[0]
    if n == 0:
        pytest.skip(
            "Données DREES non chargées. Lancer : uv run python scripts/load_economie.py --source drees"
        )
    assert n > 1000, f"Trop peu de communes avec données APL : {n}"


def test_drees_desert_medical(con_social):
    """Des communes HdF ont desert_medical = TRUE (APL < 2.5)."""
    n = con_social.execute(
        "SELECT COUNT(*) FROM economie_social WHERE desert_medical = TRUE"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Données DREES non chargées — test ignoré.")
    assert n > 50, f"Trop peu de déserts médicaux HdF : {n} (attendu >50)"


def test_vue_desindustrialisation(con_urssaf):
    """v_desindustrialisation_commune retourne des lignes avec variation calculée."""
    rows = con_urssaf.execute(
        "SELECT code_commune, variation_pct FROM v_desindustrialisation_commune LIMIT 5"
    ).fetchall()
    assert len(rows) > 0, "v_desindustrialisation_commune est vide — URSSAF chargé ?"
    # Au moins une commune avec variation calculée (secteur Industrie présent au début ET à la fin)
    has_variation = any(r[1] is not None for r in rows)
    assert has_variation, (
        "Toutes les communes ont variation_pct NULL dans v_desindustrialisation_commune"
    )


# ── Tests Phase E++ (Eurostat contexte macro) ─────────────────────────────────
# Nécessitent : uv run python scripts/load_economie.py --source eurostat


@pytest.fixture(scope="module")
def con_contexte(con) -> duckdb.DuckDBPyConnection:
    """Fixture : passe si economie_contexte existe et contient des données Eurostat."""
    table_exists = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'economie_contexte'"
    ).fetchone()[0]
    if not table_exists:
        pytest.skip(
            "Table economie_contexte absente — relancer load_economie.py pour créer le schéma."
        )
    n = con.execute("SELECT COUNT(*) FROM economie_contexte").fetchone()[0]
    if n == 0:
        pytest.skip(
            "Données Eurostat non chargées. "
            "Lancer : uv run python scripts/load_economie.py --source eurostat"
        )
    return con


def test_contexte_chomage_loaded(con_contexte):
    """economie_contexte contient tx_chomage_bit pour FRE et FR."""
    rows = con_contexte.execute(
        "SELECT code_geo FROM economie_contexte "
        "WHERE indicateur = 'tx_chomage_bit' GROUP BY code_geo"
    ).fetchall()
    geos = {r[0] for r in rows}
    assert "FRE" in geos, "FRE absent de economie_contexte (tx_chomage_bit)"
    assert "FR" in geos, "FR absent de economie_contexte (tx_chomage_bit)"
    # HdF structurellement plus élevé que la moyenne nationale
    row = con_contexte.execute(
        "SELECT SUM(CASE WHEN code_geo='FRE' THEN valeur END) > "
        "       SUM(CASE WHEN code_geo='FR'  THEN valeur END) "
        "FROM economie_contexte WHERE indicateur = 'tx_chomage_bit'"
    ).fetchone()
    assert row[0], "tx_chomage_bit HdF (FRE) ≤ France sur l'ensemble des années — inattendu"


def test_contexte_pib_loaded(con_contexte):
    """economie_contexte contient pib_eur_hab pour FRE et FR."""
    rows = con_contexte.execute(
        "SELECT code_geo FROM economie_contexte WHERE indicateur = 'pib_eur_hab' GROUP BY code_geo"
    ).fetchall()
    geos = {r[0] for r in rows}
    assert "FRE" in geos, "FRE absent de economie_contexte (pib_eur_hab)"
    assert "FR" in geos, "FR absent de economie_contexte (pib_eur_hab)"
    # HdF structurellement plus faible que la moyenne nationale
    row = con_contexte.execute(
        "SELECT SUM(CASE WHEN code_geo='FRE' THEN valeur END) < "
        "       SUM(CASE WHEN code_geo='FR'  THEN valeur END) "
        "FROM economie_contexte WHERE indicateur = 'pib_eur_hab'"
    ).fetchone()
    assert row[0], "pib_eur_hab HdF (FRE) ≥ France sur l'ensemble des années — inattendu"


def test_vue_contexte_hdf_france(con_contexte):
    """v_contexte_hdf_vs_france retourne des lignes avec écart HdF > 0 pour le chômage."""
    rows = con_contexte.execute(
        "SELECT annee, valeur_hdf, valeur_france, ecart_hdf_france "
        "FROM v_contexte_hdf_vs_france "
        "WHERE indicateur = 'tx_chomage_bit' AND ecart_hdf_france IS NOT NULL "
        "ORDER BY annee"
    ).fetchall()
    assert len(rows) > 0, "v_contexte_hdf_vs_france vide pour tx_chomage_bit"
    positifs = sum(1 for _, vh, vf, ecart in rows if ecart > 0)
    assert positifs > 0, (
        "ecart_hdf_france toujours ≤ 0 pour tx_chomage_bit — HdF devrait être > France"
    )
