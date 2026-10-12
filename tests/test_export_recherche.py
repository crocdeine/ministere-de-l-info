"""Index de la recherche globale (lot A4) et chargement des codes postaux."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from ministere_de_l_info.etl.loaders.codes_postaux import charger
from ministere_de_l_info.export_web import exporter
from ministere_de_l_info.export_web.recherche import COLONNES, normaliser


def test_normaliser() -> None:
    assert normaliser("Saint-Étienne") == "saint etienne"
    assert normaliser("St-Étienne") == "saint etienne"
    assert normaliser("Ste Marie") == "sainte marie"
    assert normaliser("Cœur-de-Lion") == "coeur de lion"
    assert normaliser("L'Abergement") == "l abergement"


def test_charger_codes_postaux_plm(tmp_path: Path) -> None:
    csv = tmp_path / "h.csv"
    lignes = ["#Code_commune_INSEE;Nom_de_la_commune;Code_postal;Libellé;Ligne_5"]
    lignes += [f"{c};X;{cp};X;" for c, cp in [("01001", "01400"), ("75101", "75001")]]
    lignes += [f"{c};X;{cp};X;" for c, cp in [("75116", "75116"), ("2A004", "20000")]]
    lignes += [f"99999;X;{i:05d};X;" for i in range(30000)]  # volume minimal du contrôle
    csv.write_text("\n".join(lignes), encoding="latin-1")
    con = duckdb.connect()
    charger(con, csv)
    got = set(con.execute("SELECT * FROM codes_postaux").fetchall())
    assert ("75056", "75001") in got and ("75056", "75116") in got
    assert ("01001", "01400") in got and ("2A004", "20000") in got
    con.close()


def test_charger_refuse_fichier_vide(tmp_path: Path) -> None:
    csv = tmp_path / "h.csv"
    csv.write_text("#Code_commune_INSEE;Nom_de_la_commune;Code_postal\n01001;X;01400\n")
    with pytest.raises(RuntimeError):
        charger(duckdb.connect(), csv)


@pytest.mark.spatial
def test_index_echantillon(echantillon_db_path: Path, tmp_path: Path) -> None:
    exporter(echantillon_db_path, tmp_path, tippecanoe=None, departements=["80"])
    idx: dict[str, Any] = json.loads(gzip.decompress((tmp_path / "recherche.json.gz").read_bytes()))
    assert idx["colonnes"] == COLONNES
    lignes = [dict(zip(COLONNES, r, strict=True)) for r in idx["lignes"]]
    cles = [(r["type"], r["code"]) for r in lignes]
    assert len(cles) == len(set(cles))  # clés uniques
    assert {r["type"] for r in lignes} >= {"c", "d"}
    amiens = next(r for r in lignes if r["type"] == "c" and r["code"] == "80021")
    assert amiens["norm"] == "amiens" and amiens["dep"] == "80"
    # Chaque renvoi (département, circonscription, élu) vise une commune de l'index.
    communes = {r["code"] for r in lignes if r["type"] == "c"}
    assert all(r["ref"] in communes for r in lignes if r["type"] != "c")
    # Aucune donnée personnelle ou politique dans l'index.
    assert all(r["type"] != "u" or r["extra"] in ("Député", "Sénateur") for r in lignes)
