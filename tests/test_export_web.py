"""Export des données de la maquette web (scripts/export_web.py) sur l'échantillon (Somme)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _charger_script(chemin: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_test_{chemin.stem}", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export_web = _charger_script(ROOT / "scripts" / "export_web.py")


@pytest.mark.spatial
def test_export_echantillon(echantillon_db_path: Path, tmp_path: Path) -> None:
    tailles = export_web.exporter(echantillon_db_path, tmp_path)
    assert set(tailles) == {"communes.geojson", "resultats.json", "evolution.json", "meta.json"}

    geo = json.loads((tmp_path / "communes.geojson").read_text(encoding="utf-8"))
    res = json.loads((tmp_path / "resultats.json").read_text(encoding="utf-8"))
    evo = json.loads((tmp_path / "evolution.json").read_text(encoding="utf-8"))
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))

    # Géométries et colonnes alignées sur les mêmes codes INSEE (str, 5 caractères).
    codes = [f["properties"]["code"] for f in geo["features"]]
    assert codes and codes == res["codes"] == sorted(codes)
    assert all(isinstance(c, str) and len(c) == 5 for c in codes)

    # Présidentielles de l'échantillon : 2012 et 2022, deux tours.
    assert set(res["scrutins"]) == {"2012_1", "2012_2", "2022_1", "2022_2"}
    for s in res["scrutins"].values():
        n = len(codes)
        assert len(s["inscrits"]) == len(s["exprimes"]) == n
        assert set(s["voix"]) == {b["code"] for b in meta["blocs"]}
        assert all(len(v) == n for v in s["voix"].values())
        # Somme des voix des blocs = exprimés (cohérence des vues) pour chaque commune présente.
        for i in range(n):
            voix = [s["voix"][b][i] for b in s["voix"]]
            if s["exprimes"][i] is not None and None not in voix:
                assert sum(voix) == s["exprimes"][i]
        c = s["chiffres"]
        assert c["communes"] and c["inscrits"] and 0 < c["participation"] <= 100
        assert c["bloc_majoritaire"] in s["voix"]

    # Évolution : parts des exprimés ; somme ≈ 100 % par scrutin.
    for cle in res["scrutins"]:
        annee, tour = map(int, cle.split("_"))
        total = sum(p["pct"] for p in evo if p["annee"] == annee and p["tour"] == tour)
        assert total == pytest.approx(100, abs=0.1)

    # Méta : sources et licences issues du registre, légende de classement par année.
    assert meta["sources"]["elections"]["licence"] == "Licence Ouverte 2.0"
    assert meta["sources"]["ign"]["producteur"] == "IGN"
    assert set(meta["legendes_classement"]) == {"2012", "2022"}
    assert "reconstruction par le projet" in meta["legendes_classement"]["2022"]
    assert [b["code"] for b in meta["blocs"]] == ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]
    assert meta["couleur_nd"] == "#5F6368"
    assert meta["echelle_score_max"] == 100.0
    assert meta["fond_carte"]["url"].startswith("https://data.geopf.fr/")
