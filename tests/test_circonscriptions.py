"""Tests smoke — fetch_circonscriptions_legislatives."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.data_sources.circonscriptions import (
    _normalize_code,
    fetch_circonscriptions_legislatives,
)

_CODE_RE = re.compile(r"^(\d{2,3}|2[AB])-\d{2}$")


def test_normalize_code_metro() -> None:
    """Normalisation metro : '0104' / '01' → '01-04'."""
    assert _normalize_code("0104", "01") == "01-04"
    assert _normalize_code("7518", "75") == "75-18"
    assert _normalize_code("2A01", "2A") == "2A-01"


def test_normalize_code_drom() -> None:
    """Normalisation DROM : 'ZA01' / 'ZA' → '971-01'."""
    assert _normalize_code("ZA01", "ZA") == "971-01"
    assert _normalize_code("ZD07", "ZD") == "974-07"
    assert _normalize_code("ZM02", "ZM") == "976-02"
    assert _normalize_code("ZS01", "ZS") == "975-01"


def test_count() -> None:
    """Le dataset doit contenir entre 550 et 580 features (fourchette tolérante)."""
    data = fetch_circonscriptions_legislatives()
    count = len(data["features"])
    assert 550 <= count <= 580, (
        f"Nombre de features hors fourchette [550-580] : {count}"
    )


def test_code_format() -> None:
    """Tous les codes normalisés respectent le format {dept}-{num:02d}."""
    data = fetch_circonscriptions_legislatives()
    codes = [f["properties"]["code"] for f in data["features"]]
    invalides = [c for c in codes if not _CODE_RE.match(c)]
    assert not invalides, f"Codes invalides : {invalides[:10]}"


def test_drom_present() -> None:
    """Au moins une feature avec code_departement commençant par '97'."""
    data = fetch_circonscriptions_legislatives()
    drom = [
        f
        for f in data["features"]
        if f["properties"]["code_departement"].startswith("97")
    ]
    assert len(drom) >= 19, f"Attendu ≥19 features DROM, obtenu {len(drom)}"


def test_reprise_disque() -> None:
    """Un second appel force=False ne déclenche aucune requête HTTP."""
    # Premier appel pour s'assurer que le fichier existe
    fetch_circonscriptions_legislatives(force=False)

    # Second appel : httpx ne doit pas être appelé
    with patch(
        "ministere_de_l_info.data_sources.circonscriptions._http_retry_get"
    ) as mock_http:
        fetch_circonscriptions_legislatives(force=False)
        mock_http.assert_not_called()
