"""Smoke tests Streamlit — démarrage headless (C4) + onglet législatives (D1.3).

Tests minimaux mais durables : détectent les crashes au démarrage.
Marqué @pytest.mark.slow — exclu du run pytest par défaut.
Lancer explicitement avec : uv run pytest -m slow
"""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "app.py"
ELECTIONS_PAGE = ROOT / "pages" / "2_🗳️_Élections.py"
DB_PATH = ROOT / "data" / "ministere.duckdb"

pytestmark = pytest.mark.slow


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def streamlit_server():
    if not DB_PATH.exists():
        pytest.skip("DB absente")
    if not APP_PY.exists():
        pytest.skip("app.py absent")
    port = _find_free_port()
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            str(APP_PY),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.runOnSave",
            "false",
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://localhost:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/_stcore/health", timeout=2)
            if r.status_code == 200 and r.text.strip() == "ok":
                break
        except (requests.RequestException, ConnectionError):
            pass
        time.sleep(1)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        pytest.fail("Streamlit n'a pas démarré en 30s")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_streamlit_health(streamlit_server):
    r = requests.get(f"{streamlit_server}/_stcore/health", timeout=5)
    assert r.status_code == 200
    assert r.text.strip() == "ok"


def test_streamlit_root_repond(streamlit_server):
    """La racine doit répondre 200 (page principale)."""
    r = requests.get(f"{streamlit_server}/", timeout=10)
    assert r.status_code == 200


# ── Tests AppTest — page Élections onglets ────────────────────────────────────


def test_legi_tab_renders():
    """La page Élections se charge sans exception avec les deux onglets."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception, f"Exception inattendue : {at.exception}"


def test_legi_default_view():
    """Vue par défaut (2022 t1, toutes circos) : pas d'exception, widgets présents."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception
    # Au moins 3 selectbox (année, tour, circo dans l'onglet legi + ceux des pres)
    assert len(at.selectbox) >= 3, f"Selectbox attendus >= 3, trouvé {len(at.selectbox)}"


def test_legi_ancien_decoupage_warning():
    """Sélectionner 2002 dans l'onglet législatives affiche le st.warning."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    # Sélectionner 2002 dans le selectbox année legi (key='legi_annee')
    legi_annee = next((s for s in at.selectbox if s.key == "legi_annee"), None)
    if legi_annee is None:
        pytest.skip("Selectbox legi_annee non trouvé (onglet inactif au démarrage)")
    legi_annee.set_value(2002).run()
    assert not at.exception
    warnings = at.warning
    textes = " ".join(w.value for w in warnings)
    assert "ancien" in textes.lower() or "Ancien" in textes, (
        f"Avertissement ancien découpage absent. Warnings : {textes[:200]}"
    )


def test_pres_drilldown_renders():
    """Sélectionner Lille dans le dropdown BV présidentielles → section drill-down présente."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=60)
    at.run()
    assert not at.exception

    drilldown_sb = next((s for s in at.selectbox if s.key == "pres_drilldown_commune"), None)
    if drilldown_sb is None:
        pytest.skip("Selectbox pres_drilldown_commune non trouvé")

    drilldown_sb.set_value("Lille (59350)").run()
    assert not at.exception, f"Exception : {at.exception}"

    # La section doit avoir rendu au moins un dataframe
    assert len(at.dataframe) >= 1, "Aucun dataframe rendu après sélection de Lille"

    # Au moins une métrique avec "Inscrits"
    metric_labels = [m.label for m in at.metric]
    assert any("Inscrits" in lbl for lbl in metric_labels), (
        f"Métrique 'Inscrits' absente. Labels : {metric_labels}"
    )


def test_legi_drilldown_appears_with_circo():
    """Sélectionner 59-21 + Valenciennes → section drill-down BV présente."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=60)
    at.run()
    assert not at.exception

    # Sélectionner la circo 59-21
    legi_circo = next((s for s in at.selectbox if s.key == "legi_circo"), None)
    if legi_circo is None:
        pytest.skip("Selectbox legi_circo non trouvé")

    circo_option = next((o for o in legi_circo.options if "59-21" in str(o)), None)
    if circo_option is None:
        pytest.skip("Option 59-21 non trouvée dans legi_circo")

    legi_circo.set_value(circo_option).run()
    assert not at.exception

    # Sélectionner Valenciennes dans le drill-down
    drilldown_sb = next(
        (s for s in at.selectbox if s.key and "legi_drilldown_commune" in s.key), None
    )
    if drilldown_sb is None:
        pytest.skip("Selectbox legi_drilldown_commune non trouvé après sélection circo")

    val_option = next((o for o in drilldown_sb.options if "59606" in str(o)), None)
    if val_option is None:
        pytest.skip("Valenciennes (59606) absente du dropdown commune")

    drilldown_sb.set_value(val_option).run()
    assert not at.exception, f"Exception : {at.exception}"
    assert len(at.dataframe) >= 1, "Aucun dataframe rendu après sélection Valenciennes"


def test_legi_drilldown_hidden_when_no_circo():
    """Vue 'toutes les circos HdF' → pas de section drill-down BV."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception

    # Vérifier que le selectbox de drill-down legi n'est pas présent en vue HdF
    drilldown_sb = next(
        (s for s in at.selectbox if s.key and "legi_drilldown_commune" in s.key), None
    )
    assert drilldown_sb is None, (
        "Selectbox legi_drilldown_commune présent en vue HdF alors qu'il ne devrait pas l'être"
    )


# ── Tests AppTest — onglet Municipales (D3.3) ─────────────────────────────────


def test_muni_tab_renders():
    """La page Élections se charge avec le 3e onglet Municipales sans exception."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception, f"Exception inattendue : {at.exception}"


def test_muni_selectbox_scrutin_present():
    """Le selectbox 'muni_scrutin' est présent dans la page après chargement."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception

    muni_sb = next((s for s in at.selectbox if s.key == "muni_scrutin"), None)
    if muni_sb is None:
        pytest.skip("Selectbox muni_scrutin non trouvé (onglet inactif ou données absentes)")
    assert len(muni_sb.options) >= 8, (
        f"muni_scrutin : seulement {len(muni_sb.options)} options (attendu 8)"
    )


def test_muni_warning_seuil_2026():
    """Sélectionner Municipales 2026 — 1er tour → warning circulaire INTP2602966C."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=30)
    at.run()
    assert not at.exception

    muni_sb = next((s for s in at.selectbox if s.key == "muni_scrutin"), None)
    if muni_sb is None:
        pytest.skip("Selectbox muni_scrutin non trouvé")

    opt_2026 = next((o for o in muni_sb.options if "2026" in str(o) and "1er" in str(o)), None)
    if opt_2026 is None:
        pytest.skip("Option 2026 1er tour non trouvée")

    muni_sb.set_value(opt_2026).run()
    assert not at.exception

    infos = at.info
    texte_infos = " ".join(i.value for i in infos)
    assert "INTP2602966C" in texte_infos or "512694" in texte_infos, (
        f"Warning circulaire 2026 absent. Infos : {texte_infos[:300]}"
    )


def test_muni_drilldown_lille_renders():
    """Sélectionner Lille dans le drill-down muni → métriques et dataframe présents."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=60)
    at.run()
    assert not at.exception

    muni_sb = next((s for s in at.selectbox if s.key == "muni_scrutin"), None)
    if muni_sb is None:
        pytest.skip("Selectbox muni_scrutin non trouvé")

    opt_2026 = next((o for o in muni_sb.options if "2026" in str(o) and "1er" in str(o)), None)
    if opt_2026 is None:
        pytest.skip("Option 2026 1er tour non trouvée")
    muni_sb.set_value(opt_2026).run()
    assert not at.exception

    drilldown_sb = next((s for s in at.selectbox if s.key and "muni_drilldown" in s.key), None)
    if drilldown_sb is None:
        pytest.skip("Selectbox muni_drilldown non trouvé")

    lille_opt = next((o for o in drilldown_sb.options if "59350" in str(o)), None)
    if lille_opt is None:
        pytest.skip("Lille (59350) absente du dropdown commune")

    drilldown_sb.set_value(lille_opt).run()
    assert not at.exception, f"Exception : {at.exception}"

    metric_labels = [m.label for m in at.metric]
    assert any("Inscrits" in lbl for lbl in metric_labels), (
        f"Métrique 'Inscrits' absente. Labels : {metric_labels}"
    )
    assert len(at.dataframe) >= 1, "Aucun dataframe après sélection de Lille"


def test_muni_drilldown_petite_commune_non_nuancee():
    """Petite commune en 2026 → warning 'non nuancée' affiché, vue bloc indisponible."""
    from streamlit.testing.v1 import AppTest

    if not DB_PATH.exists():
        pytest.skip("DB absente")
    at = AppTest.from_file(str(ELECTIONS_PAGE), default_timeout=60)
    at.run()
    assert not at.exception

    muni_sb = next((s for s in at.selectbox if s.key == "muni_scrutin"), None)
    if muni_sb is None:
        pytest.skip("Selectbox muni_scrutin non trouvé")

    opt_2026 = next((o for o in muni_sb.options if "2026" in str(o) and "1er" in str(o)), None)
    if opt_2026 is None:
        pytest.skip("Option 2026 1er tour non trouvée")
    muni_sb.set_value(opt_2026).run()
    assert not at.exception

    drilldown_sb = next((s for s in at.selectbox if s.key and "muni_drilldown" in s.key), None)
    if drilldown_sb is None:
        pytest.skip("Selectbox muni_drilldown non trouvé")

    # Chercher une commune avec un code connu comme petite (< 3500 hab)
    # On prend la première commune avec code INSEE < 59200 autre que Lille
    petite_opt = next(
        (
            o
            for o in drilldown_sb.options
            if o != "(aucune sélection)" and "59350" not in str(o) and "59001" in str(o)
        ),
        None,
    )
    if petite_opt is None:
        pytest.skip("Commune petite connue (59001) absente du dropdown — absente du Parquet 2026")

    drilldown_sb.set_value(petite_opt).run()
    assert not at.exception, f"Exception : {at.exception}"

    warnings = at.warning
    textes = " ".join(w.value for w in warnings)
    assert "non nuancée" in textes.lower() or "Non nuancée" in textes, (
        f"Warning 'non nuancée' absent. Warnings : {textes[:300]}"
    )
