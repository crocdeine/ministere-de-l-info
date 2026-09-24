"""Tests de la base échantillon (tests/fixtures/sample) et de son script d'export.

Deux familles :
- ``TestExportAllerRetour`` : hermétique, toujours exécutée. Base source SYNTHÉTIQUE
  construite en mémoire (quelques lignes inventées, jamais écrites dans
  tests/fixtures/sample) pour vérifier la mécanique export → reconstruction.
- ``TestEchantillonReel`` : porte sur l'échantillon réel exporté du Mac ; ignorée avec
  un message explicite tant que les Parquet n'ont pas été générés.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import duckdb
import pytest
from fixtures.sample_db import (
    MESSAGE_ABSENT,
    SAMPLE_DIR,
    EcartSchemaEchantillon,
    charger_manifest,
    construire_base,
    creer_schema,
    creer_vues,
    echantillon_disponible,
)

ROOT = Path(__file__).resolve().parent.parent


def _charger_script(chemin: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_test_{chemin.stem}", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # requis par @dataclass
    spec.loader.exec_module(module)
    return module


export_sample_db = _charger_script(ROOT / "scripts" / "export_sample_db.py")

# Carré synthétique (pas une vraie géométrie de commune)
_CARRE_WKT = "POLYGON ((2 49, 2.1 49, 2.1 49.1, 2 49.1, 2 49))"


@pytest.fixture
def source_synthetique() -> duckdb.DuckDBPyConnection:
    """Base source synthétique : schéma réel du projet, données inventées (80 et 59)."""
    con = duckdb.connect()
    creer_schema(con)
    con.execute(
        "INSERT INTO geographies_regions (code_insee, nom, geometry) "
        f"VALUES ('32', 'Région test', '{_CARRE_WKT}'::GEOMETRY)"
    )
    con.execute(
        "INSERT INTO geographies_departements (code_insee, nom, code_region, geometry) VALUES "
        f"('80', 'Dept test 80', '32', '{_CARRE_WKT}'::GEOMETRY), "
        f"('59', 'Dept test 59', '32', '{_CARRE_WKT}'::GEOMETRY)"
    )
    con.execute(
        "INSERT INTO geographies_communes "
        "(code_insee, nom, code_departement, code_region, code_epci, geometry) VALUES "
        f"('80001', 'Commune test A', '80', '32', '200000001', '{_CARRE_WKT}'::GEOMETRY), "
        f"('59001', 'Commune test B', '59', '32', '200000002', '{_CARRE_WKT}'::GEOMETRY)"
    )
    con.execute(
        "INSERT INTO geographies_epci (code_siren, nom) VALUES "
        "('200000001', 'EPCI test A'), ('200000002', 'EPCI test B')"
    )
    con.execute(
        "INSERT INTO populations (code_insee_commune, annee, municipale) VALUES "
        "('80001', 2023, 100), ('59001', 2023, 200)"
    )
    con.execute(
        "INSERT INTO elections VALUES ('2022_pres_t1', 'pres', 2022, 1, 'Test', FALSE), "
        "('2017_pres_t1', 'pres', 2017, 1, 'Test', FALSE)"
    )
    con.execute("INSERT INTO blocs_politiques VALUES ('GAU', 'Gauche', '#000000', 2)")
    for id_el in ("2022_pres_t1", "2017_pres_t1"):
        for dept, commune in (("80", "80001"), ("59", "59001")):
            con.execute(
                "INSERT INTO resultats_participation (id_election, code_departement, "
                "code_commune, code_bv, exprimes) VALUES (?, ?, ?, '0001', 50)",
                [id_el, dept, commune],
            )
            con.execute(
                "INSERT INTO resultats_candidats (id_election, code_departement, code_commune, "
                "code_bv, no_panneau, nom, voix) VALUES (?, ?, ?, '0001', 1, 'CANDIDAT', 50)",
                [id_el, dept, commune],
            )
    con.execute(
        "INSERT INTO economie_emploi_urssaf VALUES "
        "('80001', 2020, 'Industrie', '10.11', 5, 1), "
        "('80001', 2020, 'Commerce', '47.11', 3, 1), "
        "('59001', 2020, 'Industrie', '10.11', 7, 1)"
    )
    con.execute(
        "INSERT INTO leg_elus (id, chambre, nom, prenom, code_departement, est_actif) VALUES "
        "('E80', 'AN', 'NOM', 'Prénom', '80', TRUE), ('E59', 'AN', 'NOM', 'Prénom', '59', TRUE)"
    )
    con.execute(
        "INSERT INTO leg_activite (elu_id, chambre, date_extraction) VALUES "
        "('E80', 'AN', DATE '2026-01-01'), ('E59', 'AN', DATE '2026-01-01')"
    )
    creer_vues(con)
    yield con
    con.close()


class TestExportAllerRetour:
    def test_filtre_departement_et_scrutins(
        self, source_synthetique: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        manifest = export_sample_db.exporter(
            source_synthetique, tmp_path, scrutins=("2022_pres_t1",), tolerance=None
        )
        t = manifest["tables"]
        assert t["geographies_communes"]["lignes"] == 1
        assert t["geographies_departements"]["lignes"] == 1
        assert t["geographies_regions"]["lignes"] == 1
        assert t["geographies_epci"]["lignes"] == 1
        assert t["populations"]["lignes"] == 1
        assert t["resultats_candidats"]["lignes"] == 1  # 80 et 2022 seulement
        assert t["resultats_participation"]["lignes"] == 1
        assert t["elections"]["lignes"] == 2  # référentiel complet
        assert t["economie_emploi_urssaf"]["lignes"] == 1  # 80, industrie seulement
        assert t["leg_elus"]["lignes"] == 1
        assert t["leg_activite"]["lignes"] == 1
        assert "_etl_metadata" not in t
        assert manifest["departement"] == "80"
        assert (tmp_path / "manifest.json").is_file()

    def test_reconstruction_tables_vues_geometries(
        self, source_synthetique: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None)
        assert echantillon_disponible(tmp_path)
        con = construire_base(sample_dir=tmp_path)
        try:
            assert con.execute(
                "SELECT DISTINCT code_departement FROM resultats_candidats"
            ).fetchall() == [("80",)]
            wkt = con.execute(
                "SELECT ST_AsText(geometry) FROM geographies_communes WHERE code_insee = '80001'"
            ).fetchone()[0]
            assert wkt == "POLYGON ((2 49, 2.1 49, 2.1 49.1, 2 49.1, 2 49))"
            type_geom = con.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'geographies_communes' AND column_name = 'geometry'"
            ).fetchone()[0]
            assert type_geom.startswith("GEOMETRY")
            for vue in manifest_vues(tmp_path):
                con.execute(f"SELECT * FROM {vue} LIMIT 1").fetchall()
            n = con.execute(
                "SELECT COUNT(*) FROM v_population_commune WHERE code_commune = '80001'"
            ).fetchone()[0]
            assert n == 1
        finally:
            con.close()

    def test_budget_depasse_ne_modifie_pas_la_destination(
        self, source_synthetique: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None)
        avant = (tmp_path / "manifest.json").read_text(encoding="utf-8")
        with pytest.raises(RuntimeError, match="trop volumineux"):
            export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None, max_mo=0.0001)
        assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == avant

    def test_reexport_idempotent_conserve_readme(
        self, source_synthetique: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        (tmp_path / "README.md").write_text("doc", encoding="utf-8")
        (tmp_path / "table_obsolete.parquet").write_bytes(b"x")
        export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None)
        export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None)
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "doc"
        assert not (tmp_path / "table_obsolete.parquet").exists()

    def test_ecart_de_schema_signale(
        self, source_synthetique: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        source_synthetique.execute("ALTER TABLE elections ADD COLUMN colonne_future VARCHAR")
        source_synthetique.execute("CREATE VIEW v_future AS SELECT 1 AS x")
        export_sample_db.exporter(source_synthetique, tmp_path, tolerance=None)
        with pytest.warns(EcartSchemaEchantillon) as avertissements:
            construire_base(sample_dir=tmp_path).close()
        messages = " ".join(str(w.message) for w in avertissements)
        assert "elections.colonne_future" in messages
        assert "v_future" in messages

    @pytest.mark.parametrize("dept", ["8", "80'; DROP TABLE x; --", "ABC"])
    def test_departement_invalide_refuse(self, dept: str) -> None:
        with pytest.raises(ValueError, match="département"):
            export_sample_db.construire_specs(dept, None)

    def test_scrutin_invalide_refuse(self) -> None:
        with pytest.raises(ValueError, match="scrutin"):
            export_sample_db.construire_specs("80", ("2022_pres_t1'--",))

    def test_scrutins_par_defaut(self) -> None:
        assert len(export_sample_db.SCRUTINS_DEFAUT) == 12
        assert "2008_muni_t1" in export_sample_db.SCRUTINS_DEFAUT


def manifest_vues(sample_dir: Path) -> list[str]:
    return json.loads((sample_dir / "manifest.json").read_text(encoding="utf-8"))["vues_source"]


# ── Échantillon réel (généré sur le Mac) ─────────────────────────────────────


@pytest.fixture(scope="module")
def manifest_reel() -> dict:
    if not echantillon_disponible():
        pytest.skip(MESSAGE_ABSENT)
    return charger_manifest()


class TestEchantillonReel:
    def test_taille_sous_5_mo(self, manifest_reel: dict) -> None:
        total = sum(p.stat().st_size for p in SAMPLE_DIR.glob("*.parquet"))
        assert total < 5_000_000

    def test_perimetre_departement(
        self, manifest_reel: dict, echantillon_con: duckdb.DuckDBPyConnection
    ) -> None:
        dept = manifest_reel["departement"]
        for table in ("resultats_candidats", "resultats_participation", "geographies_communes"):
            depts = echantillon_con.execute(
                f"SELECT DISTINCT code_departement FROM {table}"
            ).fetchall()
            assert depts == [(dept,)], table

    def test_tables_principales_non_vides(
        self, manifest_reel: dict, echantillon_con: duckdb.DuckDBPyConnection
    ) -> None:
        for table in (
            "geographies_communes",
            "populations",
            "resultats_candidats",
            "resultats_participation",
            "nuances_harmonisees",
            "leg_elus",
        ):
            n = echantillon_con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert n > 0, table

    def test_toutes_les_vues_executables(
        self, manifest_reel: dict, echantillon_con: duckdb.DuckDBPyConnection
    ) -> None:
        vues = [
            r[0]
            for r in echantillon_con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
            ).fetchall()
        ]
        assert vues
        for vue in vues:
            echantillon_con.execute(f"SELECT * FROM {vue} LIMIT 5").fetchall()

    def test_requetes_legislatif_sur_echantillon(
        self, echantillon_db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ministere_de_l_info.viz import legislatif_queries

        monkeypatch.setattr(legislatif_queries, "DB_PATH", echantillon_db_path)
        legislatif_queries.get_departements_disponibles.clear()
        df = legislatif_queries.get_departements_disponibles()
        assert df.height > 0
        legislatif_queries.get_departements_disponibles.clear()

    @pytest.mark.spatial
    def test_communes_dans_leur_departement(self, manifest_reel: dict) -> None:
        """Contrôle géométrique : centroïdes des communes dans le polygone du département."""
        con = construire_base(charger_spatial=True)
        try:
            n_total, n_dedans = con.execute(
                """
                SELECT COUNT(*),
                       COUNT(*) FILTER (WHERE ST_Within(ST_Centroid(c.geometry), d.geometry))
                FROM geographies_communes c
                JOIN geographies_departements d ON d.code_insee = c.code_departement
                """
            ).fetchone()
        finally:
            con.close()
        assert n_total > 0
        assert n_dedans / n_total >= 0.95


def test_message_absent_explicite() -> None:
    assert "scripts/export_sample_db.py" in MESSAGE_ABSENT
