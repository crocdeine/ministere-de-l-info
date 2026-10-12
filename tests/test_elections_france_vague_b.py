"""Vague B (2026-10-06) : périmètre France, européennes/régionales/départementales.

Tests hermétiques : base DuckDB en mémoire, Parquet minuscules écrits dans tmp_path,
sans base réelle ni extension spatial.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl import schema_elections as se  # noqa: E402
from ministere_de_l_info.etl.loaders.elections_agregees import (  # noqa: E402
    controler_chargement,
    filtre_perimetre,
    load_scrutins_listes,
    verifier_unicite_resultats,
)

_BLOCS = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
_GRILLES = ("INTA1931378J", "IOMA2322276J", "INTP2602966C")

# Participation (candidats-results.parquet, nommage inversé) : 1 BV HdF, 1 BV Paris,
# 1 BV Guadeloupe codé « ZA », 1 BV de commune hors référentiel.
_PARTICIPATION = """
SELECT * FROM (VALUES
  ('2024_euro_t1', '59', '59350', '0001', 1000, 400, 600, 10, 5, 585, NULL, NULL),
  ('2024_euro_t1', '75', '75056', '0001', 800, 300, 500, 5, 5, 490, NULL, NULL),
  ('2024_euro_t1', 'ZA', '97101', '0001', 500, 300, 200, 2, 3, 195, NULL, NULL),
  ('2024_euro_t1', '59', '59999', '0001', 10, 5, 5, 0, 0, 5, NULL, NULL),
  ('2021_dpmt_t1', '59', '59350', '0001', 1000, 700, 300, 5, 5, 290, NULL, NULL),
  ('2019_euro_t1', '59', '59350', '0001', 1000, 500, 500, 5, 5, 490, NULL, NULL)
) t(id_election, code_departement, code_commune, code_bv, inscrits, abstentions, votants,
    blancs, nuls, exprimes, code_circonscription, code_canton)
"""

_CANDIDATS = """
SELECT * FROM (VALUES
  ('2024_euro_t1', '59', '59350', '0001', 1, 300, 'LRN', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '59', '59350', '0001', 2, 285, 'LFI', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '75', '75056', '0001', 1, 490, 'LENS', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', 'ZA', '97101', '0001', 1, 195, 'LUG', NULL, NULL, NULL, NULL, NULL),
  ('2024_euro_t1', '59', '59999', '0001', 1, 5, 'LDIV', NULL, NULL, NULL, NULL, NULL),
  ('2021_dpmt_t1', '59', '59350', '0001', NULL, 200, 'BC-UCD', NULL, NULL,
   NULL, NULL, 'M. A et Mme B'),
  ('2021_dpmt_t1', '59', '59350', '0001', NULL, 90, 'BC-RN', NULL, NULL,
   NULL, NULL, 'M. C et Mme D'),
  ('2019_euro_t1', '59', '59350', '0001', 23, 300, NULL, NULL, NULL,
   'PRENEZ LE POUVOIR', 'BARDELLA Jordan', NULL),
  ('2019_euro_t1', '59', '59350', '0001', 7, 190, NULL, NULL, NULL,
   'ENSEMBLE PATRIOTES', 'PHILIPPOT Florian', NULL)
) t(id_election, code_departement, code_commune, code_bv, no_panneau, voix, nuance, nom,
    prenom, libelle_abrege_liste, nom_tete_liste, binome)
"""


def _parquets(tmp_path: Path) -> tuple[Path, Path]:
    """Écrit les deux Parquet de test (colonnes absentes complétées à NULL)."""
    c = duckdb.connect()
    cand = tmp_path / "general-results.parquet"
    part = tmp_path / "candidats-results.parquet"
    c.execute(f"""COPY (SELECT * REPLACE (code_circonscription::VARCHAR AS code_circonscription,
        code_canton::VARCHAR AS code_canton) FROM ({_PARTICIPATION}))
        TO '{part}' (FORMAT parquet)""")
    c.execute(f"""COPY (SELECT * REPLACE (no_panneau::INTEGER AS no_panneau,
            nuance::VARCHAR AS nuance, nom::VARCHAR AS nom, prenom::VARCHAR AS prenom,
            libelle_abrege_liste::VARCHAR AS libelle_abrege_liste,
            nom_tete_liste::VARCHAR AS nom_tete_liste, binome::VARCHAR AS binome),
        NULL::VARCHAR AS sexe, NULL::VARCHAR AS liste, NULL::VARCHAR AS libelle_etendu_liste
        FROM ({_CANDIDATS})) TO '{cand}' (FORMAT parquet)""")
    c.close()
    return cand, part


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Schéma électoral + référentiels + 3 communes du référentiel géographique."""
    c = duckdb.connect()
    se.create_elections_schema(c)
    c.execute("ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS liste VARCHAR")
    for col in ("libelle_abrege_liste", "libelle_etendu_liste", "nom_tete_liste"):
        c.execute(f"ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS {col} VARCHAR")
    c.execute("ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS prenom_tete_liste VARCHAR")
    se.populate_elections_referentiels(c)
    se.create_elections_views(c)
    c.execute("""CREATE TABLE geographies_communes AS SELECT * FROM (VALUES
        ('59350', '59', '32', 'Lille'), ('75056', '75', '11', 'Paris'),
        ('97101', '971', '01', 'Les Abymes'))
        t(code_insee, code_departement, code_region, nom)""")
    # Table de passage non vide (exigée en périmètre france) ; code fictif sans effet
    c.execute(se.PASSAGE_DDL)
    c.execute("INSERT INTO communes_passage VALUES ('00000', '59350', NULL, '32', NULL)")
    yield c
    c.close()


def _n(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


class TestPerimetre:
    def test_filtre_inconnu_refuse(self) -> None:
        with pytest.raises(ValueError):
            filtre_perimetre("europe")

    def test_hdf_ne_charge_que_les_hauts_de_france(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        n_p, n_c = load_scrutins_listes(con, "euro", cand, part, "hdf")
        assert (n_p, n_c) == (2, 4)  # 2024 + 2019 à Lille ; commune 59999 hors référentiel
        assert (
            _n(con, "SELECT COUNT(*) FROM resultats_participation WHERE code_commune <> '59350'")
            == 0
        )

    def test_france_charge_tout_le_referentiel(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        n_p, _ = load_scrutins_listes(con, "euro", cand, part, "france")
        assert n_p == 4
        # « ZA » normalisé en 971 ; commune hors référentiel écartée
        depts = {
            r[0]
            for r in con.execute("SELECT code_departement FROM resultats_participation").fetchall()
        }
        assert depts == {"59", "75", "971"}

    def test_idempotent_et_cible(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "dpmt", cand, part, "france")
        load_scrutins_listes(con, "euro", cand, part, "france")
        load_scrutins_listes(con, "euro", cand, part, "france")
        assert _n(con, "SELECT COUNT(*) FROM resultats_participation") == 5
        assert (
            _n(con, "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%dpmt%'") == 2
        )

    def test_type_inconnu_refuse(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        with pytest.raises(ValueError):
            load_scrutins_listes(con, "senat", cand, part, "france")


class TestColonnes:
    def test_panneau_null_numerote_et_binome_dans_nom(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "dpmt", cand, part, "hdf")
        rows = con.execute(
            "SELECT no_panneau, nom FROM resultats_candidats ORDER BY no_panneau"
        ).fetchall()
        assert rows == [(1, "M. C et Mme D"), (2, "M. A et Mme B")]  # ORDER BY nuance

    def test_euro_2019_bloc_par_tete_de_liste(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "hdf")
        rows = dict(
            con.execute(
                "SELECT nom, bloc FROM v_resultats_candidats_avec_bloc "
                "WHERE id_election = '2019_euro_t1'"
            ).fetchall()
        )
        assert rows == {"BARDELLA Jordan": "EXD", "PHILIPPOT Florian": "EXD"}

    def test_blocs_euro_2024_et_codes_ambigus(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "france")
        load_scrutins_listes(con, "dpmt", cand, part, "france")
        rows = dict(
            con.execute(
                "SELECT nuance, bloc FROM v_resultats_candidats_avec_bloc WHERE nuance IS NOT NULL"
            ).fetchall()
        )
        assert rows == {
            "LRN": "EXD",
            "LFI": "GAU",  # grille 2023 antérieure ; EXG seulement en 2026
            "LENS": "CENT",
            "LUG": "GAU",
            "BC-RN": "EXD",
            "BC-UCD": "DTE",  # décision Mathias 2026-10-07 (Q5)
        }


class TestReferentielVagueB:
    def test_cles_uniques_et_blocs_valides(self) -> None:
        cles = [(n, a) for n, a, _, _ in se._NUANCES_EURO_REGI_DPMT]
        assert len(cles) == len(set(cles))
        autres = {(n, a) for n, a, _, _ in se._NUANCES_PRES + se._NUANCES_LEGI + se._NUANCES_MUNI}
        assert not set(cles) & autres
        assert {b for _, _, b, _ in se._NUANCES_EURO_REGI_DPMT} <= _BLOCS
        assert {e[4] for e in se._LISTES_EURO_2019} <= _BLOCS

    def test_chaque_entree_cite_une_grille(self) -> None:
        for n, a, _, src in se._NUANCES_EURO_REGI_DPMT:
            assert any(g in src for g in _GRILLES), (n, a)
            assert "ADR-0010" in src, (n, a)
        for e in se._LISTES_EURO_2019:
            assert "INTA1931378J" in e[6], e[1]

    def test_codes_ambigus_absents(self) -> None:
        cles = {(n, a) for n, a, _, _ in se._NUANCES_EURO_REGI_DPMT}
        assert not cles & se._CODES_VAGUE_B_NON_CLASSES

    def test_annees_disjointes_des_municipales(self) -> None:
        annees = {a for _, a, _, _ in se._NUANCES_EURO_REGI_DPMT}
        assert not annees & set(se._ANNEES_MUNI)

    def test_populate_vague_b_idempotent(self) -> None:
        c = duckdb.connect()
        se.create_elections_schema(c)
        se.populate_elections_referentiels(c)
        n0 = _n(c, "SELECT COUNT(*) FROM nuances_harmonisees")
        se.populate_nuances_vague_b(c)
        se.populate_nuances_vague_b(c)
        assert _n(c, "SELECT COUNT(*) FROM nuances_harmonisees") == n0
        assert _n(c, "SELECT COUNT(*) FROM candidats_presidentielle WHERE annee = 2019") == 34


class TestVuesHdF:
    """Les vues « HdF » excluent les autres départements quand la base est nationale."""

    def test_evolution_legi_et_muni_bornees_hdf(self, con) -> None:
        con.execute("""INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv, inscrits, votants, exprimes,
             code_circo) VALUES
            ('2022_legi_t1', '59', '59350', '0001', 100, 60, 50, '59-01'),
            ('2022_legi_t1', '75', '75056', '0001', 100, 60, 50, '75-01'),
            ('2020_muni_t1', '59', '59350', '0001', 100, 60, 50, NULL),
            ('2020_muni_t1', '75', '75056', '0001', 100, 60, 50, NULL)""")
        con.execute("""INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv, no_panneau, nuance, voix)
            VALUES
            ('2022_legi_t1', '59', '59350', '0001', 1, 'RN', 50),
            ('2022_legi_t1', '75', '75056', '0001', 1, 'ENS', 50),
            ('2020_muni_t1', '59', '59350', '0001', 1, 'LSOC', 50),
            ('2020_muni_t1', '75', '75056', '0001', 1, 'LREM', 50)""")
        assert con.execute("SELECT bloc FROM v_evolution_blocs_hdf_legi").fetchall() == [("EXD",)]
        spec = importlib.util.spec_from_file_location(
            "_m0007", ROOT / "scripts" / "migrations" / "0007_add_municipales_views.py"
        )
        assert spec is not None and spec.loader is not None
        m0007 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m0007)
        m0007._create_v_evolution_blocs_hdf_muni(con)
        rows = con.execute("SELECT bloc, pct_exprimes FROM v_evolution_blocs_hdf_muni").fetchall()
        assert rows == [("GAU", 100.0)]


class TestSansClePrimaire:
    """Q2 (décision Mathias 2026-10-07) : pas de PK, unicité contrôlée au chargement."""

    def test_migration_retire_la_pk_et_conserve_donnees_et_vues(self) -> None:
        c = duckdb.connect()
        c.execute("""CREATE TABLE resultats_participation (id_election VARCHAR NOT NULL,
            code_departement VARCHAR NOT NULL, code_commune VARCHAR NOT NULL,
            code_bv VARCHAR NOT NULL, inscrits INTEGER,
            PRIMARY KEY (id_election, code_departement, code_commune, code_bv))""")
        c.execute("""CREATE TABLE resultats_candidats (id_election VARCHAR NOT NULL,
            code_departement VARCHAR NOT NULL, code_commune VARCHAR NOT NULL,
            code_bv VARCHAR NOT NULL, no_panneau INTEGER NOT NULL, voix INTEGER,
            PRIMARY KEY (id_election, code_departement, code_commune, code_bv, no_panneau))""")
        c.execute("INSERT INTO resultats_participation VALUES ('x', '59', '59350', '1', 10)")
        c.execute("CREATE VIEW v AS SELECT SUM(inscrits) AS s FROM resultats_participation")
        assert se.retirer_cles_primaires_resultats(c) == [
            "resultats_participation",
            "resultats_candidats",
        ]
        assert se.retirer_cles_primaires_resultats(c) == []
        assert _n(c, "SELECT s FROM v") == 10
        assert (
            _n(c, "SELECT COUNT(*) FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY'")
            == 0
        )

    def test_schema_neuf_sans_pk_et_doublon_detecte(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "hdf")
        con.execute(
            "INSERT INTO resultats_candidats (id_election, code_departement, code_commune, "
            "code_bv, no_panneau, voix) VALUES ('2024_euro_t1', '59', '59350', '0001', 1, 1)"
        )
        with pytest.raises(RuntimeError, match="Doublons"):
            verifier_unicite_resultats(con, "('2024_euro_t1')")


def _charger_migration(nom: str):
    spec = importlib.util.spec_from_file_location(
        f"_m_{nom}", ROOT / "scripts" / "migrations" / nom
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDurcissement:
    """Fiche « vague B — durcissement » (2026-10-07)."""

    def test_migration_0009_puis_vues_hdf_bornees(self, con) -> None:
        from ministere_de_l_info.etl.schema_economie import create_economie_schema

        create_economie_schema(con)
        con.execute(
            "ALTER TABLE resultats_participation ADD PRIMARY KEY "
            "(id_election, code_departement, code_commune, code_bv)"
        )
        con.execute("""INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv, inscrits, votants, exprimes,
             code_circo) VALUES
            ('2022_legi_t1', '59', '59350', '0001', 100, 60, 50, '59-01'),
            ('2022_legi_t1', '75', '75056', '0001', 100, 60, 50, '75-01'),
            ('2020_muni_t1', '59', '59350', '0001', 100, 60, 50, NULL),
            ('2020_muni_t1', '75', '75056', '0001', 100, 60, 50, NULL)""")
        con.execute("""INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv, no_panneau, nuance, voix)
            VALUES ('2022_legi_t1', '59', '59350', '0001', 1, 'RN', 50),
            ('2022_legi_t1', '75', '75056', '0001', 1, 'ENS', 50),
            ('2020_muni_t1', '59', '59350', '0001', 1, 'LSOC', 50),
            ('2020_muni_t1', '75', '75056', '0001', 1, 'LREM', 50)""")
        m0009 = _charger_migration("0009_resultats_sans_cle_primaire.py")
        assert m0009.appliquer(con) == ["resultats_participation"]
        assert _n(con, "SELECT COUNT(*) FROM resultats_participation") == 4
        assert con.execute(
            "SELECT bloc, voix_total FROM v_evolution_blocs_hdf_legi"
        ).fetchall() == [("EXD", 50)]
        assert con.execute("SELECT bloc, voix FROM v_evolution_blocs_hdf_muni").fetchall() == [
            ("GAU", 50)
        ]

    def test_ecarts_enregistres_et_seuil(self, con, tmp_path) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "hdf")
        rows = con.execute(
            "SELECT id_election, categorie, nb_communes, exprimes, exprimes_total "
            "FROM elections_ecarts_chargement"
        ).fetchall()
        assert rows == [("2024_euro_t1", "reste", 1, 5, 590)]
        with pytest.raises(RuntimeError, match="référentiel"):
            controler_chargement(con, part, "('2024_euro_t1')", "hdf", seuil_reste_pct=0.5)

    def test_categories_etranger_et_pacifique(self, con, tmp_path) -> None:
        c = duckdb.connect()
        part = tmp_path / "p.parquet"
        c.execute(f"""COPY (SELECT * FROM (VALUES
            ('2024_euro_t1', 'ZZ', '99001', '1', 10),
            ('2024_euro_t1', 'ZN', '98801', '1', 20),
            ('2024_euro_t1', '75', '75056', '1', 970)
        ) t(id_election, code_departement, code_commune, code_bv, exprimes))
        TO '{part}' (FORMAT parquet)""")
        c.close()
        controler_chargement(con, part, "('2024_euro_t1')", "france")
        rows = con.execute(
            "SELECT categorie, exprimes, pct_exprimes FROM elections_ecarts_chargement ORDER BY 1"
        ).fetchall()
        assert rows == [("etranger", 10, 1.0), ("outremer_hors_referentiel", 20, 2.0)]

    def test_voix_differentes_des_exprimes_signalees(self, con, tmp_path, caplog) -> None:
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "france")
        con.execute(
            "UPDATE resultats_participation SET exprimes = 999 WHERE code_commune = '75056'"
        )
        with caplog.at_level("WARNING"):
            controler_chargement(con, part, "('2024_euro_t1')", "france")
        assert any(
            "somme des voix" in r.getMessage() and "75056" in r.getMessage() for r in caplog.records
        )


class TestCommunesFusionnees:
    """Rattachement des communes fusionnées (décision Mathias 2026-10-07)."""

    _MVT = (
        '"MOD","DATE_EFF","TYPECOM_AV","COM_AV","TNCC_AV","NCC_AV","NCCENR_AV","LIBELLE_AV",'
        '"TYPECOM_AP","COM_AP","TNCC_AP","NCC_AP","NCCENR_AP","LIBELLE_AP"\n'
        # fusion en deux étapes : 59997 → 59998 (2016), puis 59998 → 59350 (2019)
        '"32","2016-01-01","COM","59997","0","A","A","A","COM","59998","0","B","B","B"\n'
        '"32","2016-01-01","COM","59997","0","A","A","A","COMD","59997","0","A","A","A"\n'
        '"32","2019-01-01","COM","59998","0","B","B","B","COM","59350","0","L","L","L"\n'
        # changement de code : 59999 → 59350
        '"41","2018-01-01","COM","59999","0","C","C","C","COM","59350","0","L","L","L"\n'
        # rétablissement (scission) : jamais utilisé pour rattacher
        '"21","2020-01-01","COMD","75100","0","D","D","D","COM","75100","0","D","D","D"\n'
        '"21","2020-01-01","COM","75056","0","P","P","P","COM","75100","0","D","D","D"\n'
    )

    def _passage(self, con, tmp_path) -> int:
        from ministere_de_l_info.etl.loaders.communes_passage import construire_passage

        csv = tmp_path / "mvt.csv"
        csv.write_text(self._MVT, encoding="utf-8")
        return construire_passage(con, csv)

    def test_chaines_resolues_scissions_ignorees(self, con, tmp_path) -> None:
        assert self._passage(con, tmp_path) == 3
        rows = con.execute(
            "SELECT code_ancien, code_actuel, libelle_ancien FROM communes_passage ORDER BY 1"
        ).fetchall()
        # Nom de la commune disparue : celui de sa première fusion (fiche commune, lot A3).
        assert rows == [
            ("59997", "59350", "A"),
            ("59998", "59350", "B"),
            ("59999", "59350", "C"),
        ]

    def test_colonne_libelle_ajoutee_aux_bases_existantes(self) -> None:
        import duckdb

        from ministere_de_l_info.etl import schema_elections as se

        c = duckdb.connect()
        c.execute(
            "CREATE TABLE communes_passage (code_ancien VARCHAR(5) PRIMARY KEY, "
            "code_actuel VARCHAR(5) NOT NULL, date_effet DATE, type_evenement VARCHAR)"
        )
        c.execute(se.PASSAGE_DDL)
        c.execute(se.PASSAGE_DDL)  # idempotent
        cols = [r[0] for r in c.execute("DESCRIBE communes_passage").fetchall()]
        assert cols[-1] == "libelle_ancien"

    def test_resultats_rattaches_avec_origine_et_bv_prefixe(self, con, tmp_path) -> None:
        self._passage(con, tmp_path)
        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "hdf")
        rows = con.execute(
            "SELECT code_commune, code_bv, code_commune_origine FROM resultats_participation "
            "WHERE id_election = '2024_euro_t1' ORDER BY code_bv"
        ).fetchall()
        assert rows == [("59350", "0001", None), ("59350", "59999-0001", "59999")]
        ecarts = con.execute(
            "SELECT categorie, nb_communes, exprimes FROM elections_ecarts_chargement "
            "WHERE id_election = '2024_euro_t1'"
        ).fetchall()
        assert ecarts == [("rattachee", 1, 5)]
        assert (
            _n(con, "SELECT COUNT(*) FROM resultats_candidats WHERE code_commune_origine = '59999'")
            == 1
        )


class TestCorrectifsRelecture:
    """Fiche « vague B — correctifs issus des relectures » (2026-10-07)."""

    def test_echec_de_controle_laisse_la_base_intacte(self, con, tmp_path, monkeypatch) -> None:
        from ministere_de_l_info.etl.loaders import elections_agregees as ea

        cand, part = _parquets(tmp_path)
        load_scrutins_listes(con, "euro", cand, part, "france")
        avant = con.execute(
            "SELECT COUNT(*), SUM(voix) FROM resultats_candidats WHERE id_election LIKE '%euro%'"
        ).fetchall()

        def doublon(c, ids):
            raise RuntimeError("Doublons de clé simulés")

        monkeypatch.setattr(ea, "verifier_unicite_resultats", doublon)
        with pytest.raises(RuntimeError, match="simulés"):
            load_scrutins_listes(con, "euro", cand, part, "france")
        apres = con.execute(
            "SELECT COUNT(*), SUM(voix) FROM resultats_candidats WHERE id_election LIKE '%euro%'"
        ).fetchall()
        assert apres == avant

    def test_passage_vide_bloque_le_perimetre_france(self, con, tmp_path) -> None:
        con.execute("DELETE FROM communes_passage")
        cand, part = _parquets(tmp_path)
        with pytest.raises(RuntimeError, match="communes_passage vide"):
            load_scrutins_listes(con, "euro", cand, part, "france")
        load_scrutins_listes(con, "euro", cand, part, "hdf")  # HdF : simple avertissement

    def test_hors_referentiel_au_dela_du_seuil(self, con, tmp_path) -> None:
        c = duckdb.connect()
        part = tmp_path / "p.parquet"
        c.execute(f"""COPY (SELECT * FROM (VALUES
            ('2024_euro_t1', 'ZZ', '99001', '1', 100),
            ('2024_euro_t1', '75', '75056', '1', 900)
        ) t(id_election, code_departement, code_commune, code_bv, exprimes))
        TO '{part}' (FORMAT parquet)""")
        c.close()
        with pytest.raises(RuntimeError, match="hors référentiel"):
            controler_chargement(con, part, "('2024_euro_t1')", "france")

    def test_listes_commune_absorbee_pct_sur_ses_exprimes(self, con) -> None:
        con.execute("""INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv, exprimes, code_commune_origine)
            VALUES ('2020_muni_t1', '59', '59350', '0001', 100, NULL),
                   ('2020_muni_t1', '59', '59350', '59999-0001', 50, '59999')""")
        con.execute("""INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv, no_panneau, nuance, voix,
             code_commune_origine)
            VALUES ('2020_muni_t1', '59', '59350', '0001', 1, 'LSOC', 60, NULL),
                   ('2020_muni_t1', '59', '59350', '0001', 2, 'LLR', 40, NULL),
                   ('2020_muni_t1', '59', '59350', '59999-0001', 1, 'LDVD', 50, '59999')""")
        se.create_municipales_views(con)
        rows = con.execute(
            "SELECT code_commune_origine, SUM(pct_exprimes) FROM v_listes_commune_muni "
            "GROUP BY 1 ORDER BY 1 NULLS FIRST"
        ).fetchall()
        assert rows == [(None, 100.0), ("59999", 100.0)]
