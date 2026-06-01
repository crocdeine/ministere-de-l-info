"""Smoke test Streamlit : démarrer l'app headless et vérifier qu'elle répond (C4).

Test minimal mais durable : détecte les crashes au démarrage, indépendant de
la structure UI précise des pages.

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
