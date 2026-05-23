"""Tests smoke — fetch_populations (DS_POPULATIONS_HISTORIQUES INSEE Mélodi)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.data_sources.insee_populations import (
    _ANNEES_DISPONIBLES,
    _MILLESIMES_RECOMMANDES,
    fetch_populations,
)


def test_annee_inconnue() -> None:
    """Un millésime non disponible lève une ValueError explicite."""
    with pytest.raises(ValueError, match="non disponible"):
        fetch_populations(1900)


def test_millesimes_recommandes_sont_disponibles() -> None:
    """Les 3 millésimes recommandés sont bien dans _ANNEES_DISPONIBLES."""
    for m in _MILLESIMES_RECOMMANDES:
        assert m in _ANNEES_DISPONIBLES, f"{m} manquant dans _ANNEES_DISPONIBLES"


def test_schema_colonnes() -> None:
    """Le DataFrame retourné respecte le schéma garanti."""
    df = fetch_populations(2022)
    assert set(df.columns) == {
        "code_insee_commune",
        "annee",
        "municipale",
        "comptee_a_part",
        "totale",
    }
    assert df.schema["code_insee_commune"] == pl.Utf8
    assert df.schema["annee"] == pl.Int32
    assert df.schema["municipale"] == pl.Int64
    assert df.schema["comptee_a_part"] == pl.Int64
    assert df.schema["totale"] == pl.Int64


def test_comptee_a_part_et_totale_sont_null() -> None:
    """comptee_a_part et totale sont intentionnellement NULL (PCAP non disponible)."""
    df = fetch_populations(2022)
    assert df["comptee_a_part"].is_null().all(), "comptee_a_part doit être entièrement NULL"
    assert df["totale"].is_null().all(), "totale doit être entièrement NULL"


def test_count_2022() -> None:
    """Le millésime 2022 doit contenir entre 34 000 et 36 000 lignes."""
    df = fetch_populations(2022)
    assert 34_000 <= len(df) <= 36_000, (
        f"Nombre de communes hors fourchette [34000-36000] : {len(df)}"
    )


def test_code_format() -> None:
    """Tous les codes commune sont des str de 5 chars."""
    df = fetch_populations(2022)
    longueurs = df["code_insee_commune"].str.len_chars()
    invalides = df.filter(longueurs != 5)["code_insee_commune"]
    assert len(invalides) == 0, f"Codes de longueur ≠ 5 : {invalides[:10].to_list()}"


def test_no_duplicates() -> None:
    """Pas de doublon sur code_insee_commune pour un millésime donné."""
    df = fetch_populations(2022)
    assert df["code_insee_commune"].n_unique() == len(df), (
        "Doublons détectés sur code_insee_commune"
    )


def test_plm_present() -> None:
    """Communes-mères PLM présentes pour 2022 (arrondissements absents de la source)."""
    df = fetch_populations(2022)
    codes = set(df["code_insee_commune"].to_list())
    for code in ("75056", "69123", "13055"):
        assert code in codes, f"Commune-mère PLM manquante : {code}"


def test_annee_dans_dataframe() -> None:
    """La colonne annee correspond au millésime demandé."""
    df = fetch_populations(2013)
    assert (df["annee"] == 2013).all(), "La colonne annee doit valoir 2013 partout"


def test_reprise_disque() -> None:
    """Un second appel force=False ne retélécharge pas le ZIP."""
    fetch_populations(2022, force=False)  # s'assure que le fichier existe
    with patch("ministere_de_l_info.data_sources.insee_populations._http_retry_get") as mock_http:
        fetch_populations(2022, force=False)
        mock_http.assert_not_called()
