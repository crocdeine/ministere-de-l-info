"""Export de l'application web (``ministere_de_l_info.export_web``) sur l'échantillon (Somme)."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from ministere_de_l_info.export_web import VERSION_SCHEMA, exporter
from ministere_de_l_info.export_web.export import (
    CARACTERES,
    COLONNES_SCRUTIN,
    COLONNES_VOIX,
    TAILLE_MAX_BRUTE,
    _preparer,
)

pytestmark = pytest.mark.spatial


def _lire(chemin: Path) -> Any:
    return json.loads(gzip.decompress(chemin.read_bytes()))


@pytest.fixture(scope="module")
def export(echantillon_db_path: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    sortie = tmp_path_factory.mktemp("export_web")
    exporter(echantillon_db_path, sortie, tippecanoe=None)
    return sortie


def test_manifeste(export: Path) -> None:
    m = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    assert m["schema"] == VERSION_SCHEMA
    assert m["licence_base"]["nom"] == "ODbL 1.0"
    assert m["sources"]["elections"]["licence"] == "Licence Ouverte 2.0"
    assert m["sources"]["ign"]["producteur"] == "IGN"
    assert [b["code"] for b in m["blocs"]] == ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]
    assert m["couleur_nd"] == "#5F6368"
    ids = [s["id"] for s in m["scrutins"]]
    assert ids == sorted(ids) and "2022_pres_t1" in ids
    methodes = {s["id"]: s["methode"] for s in m["scrutins"]}
    assert methodes["2026_muni_t1"] == "officielle" and methodes["2022_pres_t1"] == "reconstruit"
    assert all(s["legende"].startswith("Classement des blocs") for s in m["scrutins"])
    # Chaque fichier écrit est décrit (taille, SHA256) ; aucun ne dépasse la taille brute maximale.
    ecrits = {p.relative_to(export).as_posix() for p in export.rglob("*") if p.is_file()}
    assert ecrits - {"manifest.json"} == set(m["fichiers"])
    for rel, info in m["fichiers"].items():
        octets = (export / rel).read_bytes()
        assert info["octets"] == len(octets)
        assert info["sha256"] == hashlib.sha256(octets).hexdigest()
        assert info["brut"] <= TAILLE_MAX_BRUTE
        brut = gzip.decompress(octets)
        assert info["sha256_brut"] == hashlib.sha256(brut).hexdigest()


def test_scrutins_alignes_et_nd(export: Path) -> None:
    m = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    codes = _lire(export / "communes.json.gz")["codes"]
    assert codes == sorted(codes) and all(isinstance(c, str) and len(c) == 5 for c in codes)
    for s in m["scrutins"]:
        col = _lire(export / "scrutins" / f"{s['id']}.json.gz")
        assert list(col) == COLONNES_SCRUTIN == m["colonnes_scrutin"]
        assert all(len(v) == len(codes) for v in col.values())
        for i in range(len(codes)):
            voix = [col[c][i] for c in COLONNES_VOIX]
            # Absence de voix : toutes nulles (n.d.), jamais 0 ; sinon toutes renseignées.
            assert all(v is None for v in voix) or None not in voix
            if s["type"] == "pres" and None not in voix and col["exprimes"][i] is not None:
                assert sum(voix) == col["exprimes"][i]
            p = col["part_tete"][i]
            assert p is None or 0 < p <= 100


def _totaux_export(export: Path, id_election: str) -> dict[str, int]:
    col = _lire(export / "scrutins" / f"{id_election}.json.gz")
    return {
        c: sum(v for v in col[c] if v is not None) for c in ["inscrits", "votants", *COLONNES_VOIX]
    }


@pytest.mark.parametrize(
    ("id_election", "sql_participation", "sql_voix"),
    [
        # Même source que les pages Streamlit : vues des présidentielles et des municipales.
        (
            "2022_pres_t1",
            "SELECT SUM(inscrits), SUM(votants) FROM v_participation_commune_pres "
            "WHERE id_election = '2022_pres_t1'",
            "SELECT COALESCE(bloc, 'NC'), SUM(voix) FROM v_scores_commune_pres "
            "WHERE id_election = '2022_pres_t1' GROUP BY 1",
        ),
        (
            "2024_legi_t1",
            "SELECT SUM(inscrits), SUM(votants) FROM resultats_participation "
            "WHERE id_election = '2024_legi_t1'",
            "SELECT COALESCE(bloc, 'NC'), SUM(voix) FROM v_resultats_candidats_avec_bloc "
            "WHERE id_election = '2024_legi_t1' GROUP BY 1",
        ),
        (
            "2026_muni_t1",
            "SELECT SUM(inscrits), SUM(votants) FROM resultats_participation "
            "WHERE id_election = '2026_muni_t1'",
            "SELECT COALESCE(bloc, 'NC'), SUM(voix) FROM v_scores_commune_muni "
            "WHERE annee = 2026 AND tour = 1 GROUP BY 1",
        ),
    ],
)
def test_parite_totaux(
    export: Path,
    echantillon_con: duckdb.DuckDBPyConnection,
    id_election: str,
    sql_participation: str,
    sql_voix: str,
) -> None:
    """Totaux du département = requêtes des pages Streamlit (aucune commune perdue)."""
    attendu: dict[str, int] = dict.fromkeys(COLONNES_VOIX, 0)
    row = echantillon_con.execute(sql_participation).fetchone()
    assert row is not None
    attendu["inscrits"], attendu["votants"] = row
    attendu |= dict(echantillon_con.execute(sql_voix).fetchall())
    assert _totaux_export(export, id_election) == attendu


def test_departements(export: Path) -> None:
    m = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    for nom, cles in (("communes", ["code_commune"]), ("bureaux", ["code_commune", "code_bv"])):
        d = _lire(export / "departements" / "80" / f"{nom}.json.gz")
        assert list(d)[: 1 + len(cles)] == ["scrutin", *cles]
        n = len(d["scrutin"])
        assert n and all(0 <= i < len(m["scrutins"]) for i in d["scrutin"])
        assert all(isinstance(c, str) for c in d["code_commune"])
    # Communes du département = somme des bureaux, pour chaque scrutin.
    com = _lire(export / "departements" / "80" / "communes.json.gz")
    bur = _lire(export / "departements" / "80" / "bureaux.json.gz")
    assert sum(v or 0 for v in com["inscrits"]) == sum(v or 0 for v in bur["inscrits"])
    assert sum(v or 0 for v in com["GAU"]) == sum(v or 0 for v in bur["GAU"])


def test_etats_carte(echantillon_con: duckdb.DuckDBPyConnection) -> None:
    """Caractère d'état : bloc seul en tête, égalité, non classé, n.d., aucun scrutin."""
    cur = echantillon_con.cursor()
    _preparer(cur, None)
    lignes = cur.execute(
        f"SELECT etat, m, {', '.join(f'"{c}"' for c in COLONNES_VOIX)}, inscrits FROM _e"
    ).fetchall()
    vus = set()
    for etat, m, *reste in lignes:
        voix, inscrits = reste[:-1], reste[-1]
        vus.add(etat)
        if etat == "x":  # aucune ligne de résultat pour la commune
            assert inscrits is None and m is None
        elif etat == ".":
            assert m is None or m <= 0
        elif etat == "=":
            assert voix.count(m) > 1
        else:
            assert voix.count(m) == 1
            tete = COLONNES_VOIX[voix.index(m)]
            assert etat == CARACTERES.get(tete, "n")
    assert {"a", "b", "c", "d", "e", "f"} & vus and "n" in vus and "x" in vus


def test_publication_atomique(
    echantillon_db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un export qui échoue laisse le précédent intact ; un export réussi ne garde rien d'ancien."""
    from ministere_de_l_info.export_web import export as module

    sortie = tmp_path / "data"
    exporter(echantillon_db_path, sortie, tippecanoe=None)
    (sortie / "communes.pmtiles").write_bytes(b"ancien")  # reste d'un export avec tuiles
    avant = (sortie / "manifest.json").read_text(encoding="utf-8")

    def echec(*_: object) -> None:
        raise ValueError("contrôle en échec")

    monkeypatch.setattr(module, "_controler", echec)
    with pytest.raises(ValueError, match="contrôle"):
        exporter(echantillon_db_path, sortie, tippecanoe=None)
    assert (sortie / "manifest.json").read_text(encoding="utf-8") == avant
    assert not list(tmp_path.glob(".data.*"))  # dossier de préparation supprimé

    monkeypatch.undo()
    exporter(echantillon_db_path, sortie, tippecanoe=None)  # --sans-tuiles
    assert not (sortie / "communes.pmtiles").exists()


def test_zero_voix_nd(export: Path) -> None:
    """Commune avec des lignes mais 0 voix : n.d. (`.`), total 0 (signalé dans l'infobulle)."""
    m = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    for s in m["scrutins"]:
        col = _lire(export / "scrutins" / f"{s['id']}.json.gz")
        for etat, total in zip(col["etat"], col["total"], strict=True):
            if total == 0:
                assert etat == "."
            if etat == "x":
                assert total is None
