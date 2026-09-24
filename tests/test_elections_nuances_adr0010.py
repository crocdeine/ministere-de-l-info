"""Tests hermétiques — révision des classements nuances → blocs (ADR-0010).

Base DuckDB en mémoire, sans base réelle ni extension spatial : exécutables en CI.

Vérifie :
- lot 1 : application stricte des grilles officielles 2020 (INTA1931378J, annexe 3)
  et 2026 (INTP2602966C, annexe 3), y compris les codes officiels ajoutés (Q9) ;
- lot 2 : LCMD, LGC, LMC 2008 inchangés (bloc et source_bloc), LMAJ 2008 toujours exclu ;
- lot 3 : doctrine « grille la plus proche » pour les législatives et présidentielles.

Les grilles officielles sont recopiées ici indépendamment du code de production
(lecture des PDF de docs/sources-officielles/nuances/, vérifiée sur rendu image) :
elles servent d'oracle. « AUT » (2020) et « Autres » (2023) correspondent à DIV.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    _NUANCES_LEGI,
    _NUANCES_MUNI,
    _NUANCES_PRES,
    create_elections_schema,
    create_elections_views,
    populate_elections_referentiels,
    populate_nuances_municipales,
)

# INTA1931378J (3 février 2020), annexe 3 p. 10, « Nuances de listes »
_GRILLE_LISTES_2020: dict[str, str] = {
    "LEXG": "EXG",
    **dict.fromkeys(("LCOM", "LFI", "LSOC", "LRDG", "LDVG", "LUG", "LVEC"), "GAU"),
    **dict.fromkeys(("LECO", "LDIV", "LREG", "LGJ"), "DIV"),
    **dict.fromkeys(("LREM", "LMDM", "LUDI", "LUC", "LDVC"), "CENT"),
    **dict.fromkeys(("LLR", "LUD", "LDVD", "LDLF"), "DTE"),
    **dict.fromkeys(("LRN", "LEXD"), "EXD"),
}

# INTP2602966C (2 février 2026), annexe 3 p. 12, « Nuances de listes »
_GRILLE_LISTES_2026: dict[str, str] = {
    **dict.fromkeys(("LEXG", "LFI"), "EXG"),
    **dict.fromkeys(("LCOM", "LSOC", "LVEC", "LUG", "LDVG"), "GAU"),
    **dict.fromkeys(("LECO", "LREG", "LDIV"), "DIV"),
    **dict.fromkeys(("LREN", "LMDM", "LHOR", "LUDI", "LUC", "LDVC"), "CENT"),
    **dict.fromkeys(("LLR", "LUD", "LDVD", "LDSV"), "DTE"),
    **dict.fromkeys(("LUDR", "LRN", "LREC", "LUXD", "LEXD"), "EXD"),
}

# Lot 2 : classements D3.2 conservés à l'identique, en attente de vérification manuelle
_LOT2_INCHANGES: dict[tuple[str, int], tuple[str, str]] = {
    ("LCMD", 2008): (
        "GAU",
        "Communiste et Divers — analyse contextuelle, libellés Parquet NULL, "
        "bassin minier HdF ; cohérence avec LDVG/LSOC (D3.2, LCMD→GAU validé)",
    ),
    ("LGC", 2008): (
        "DIV",
        "Gauche-Centre local — 5 occurrences, trop peu pour classifier (D3.2)",
    ),
    ("LMC", 2008): ("CENT", "Majorité-Centre — UDF sphère 2008 (D3.2)"),
}

# Tous les reclassements appliqués : (nuance, annee) → (avant, après)
_RECLASSEMENTS: dict[tuple[str, int], tuple[str, str]] = {
    # Lot 1 — municipales
    ("LCOM", 2008): ("EXG", "GAU"),
    ("LCOM", 2014): ("EXG", "GAU"),
    ("LCOM", 2020): ("EXG", "GAU"),
    ("LCOM", 2026): ("EXG", "GAU"),
    ("LUDI", 2014): ("DIV", "CENT"),
    ("LUDI", 2020): ("DIV", "CENT"),
    ("LUDI", 2026): ("DIV", "CENT"),
    ("LUD", 2014): ("CENT", "DTE"),
    ("LUD", 2020): ("CENT", "DTE"),
    ("LECO", 2020): ("GAU", "DIV"),
    ("LECO", 2026): ("GAU", "DIV"),
    # Lot 3 — législatives
    ("ECO", 2002): ("GAU", "DIV"),
    ("ECO", 2007): ("GAU", "DIV"),
    ("ECO", 2012): ("GAU", "DIV"),
    ("ECO", 2024): ("GAU", "DIV"),
    ("PRV", 2012): ("DTE", "CENT"),
    ("UDI", 2024): ("CENT", "DTE"),
    # Lot 3 — présidentielle
    ("LEPA", 2002): ("CENT", "DIV"),
}

# Lot 3 — classements examinés et maintenus
_MAINTENUS: dict[tuple[str, int], str] = {
    ("ECO", 2017): "GAU",
    ("ECO", 2022): "GAU",
    ("UDI", 2017): "CENT",
    ("UDI", 2022): "CENT",
    ("CPNT", 2002): "DIV",
    ("CPNT", 2007): "DIV",
    ("SAIN", 2002): "DIV",
    ("NIHO", 2007): "DIV",
}


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Base mémoire : schéma électoral + référentiels."""
    c = duckdb.connect()
    create_elections_schema(c)
    populate_elections_referentiels(c)
    yield c
    c.close()


def _bloc(con: duckdb.DuckDBPyConnection, nuance: str, annee: int) -> tuple[str, str] | None:
    return con.execute(
        "SELECT bloc, source_bloc FROM nuances_harmonisees WHERE nuance = ? AND annee = ?",
        [nuance, annee],
    ).fetchone()


def _codes_muni(con: duckdb.DuckDBPyConnection, annee: int) -> dict[str, str]:
    rows = con.execute(
        "SELECT nuance, bloc FROM nuances_harmonisees WHERE annee = ?", [annee]
    ).fetchall()
    return dict(rows)


# ── Lot 1 — grilles officielles 2020 et 2026 ─────────────────────────────────


class TestLot1GrillesOfficielles:
    @pytest.mark.parametrize(
        ("annee", "grille"), [(2020, _GRILLE_LISTES_2020), (2026, _GRILLE_LISTES_2026)]
    )
    def test_referentiel_identique_a_la_grille(
        self, con: duckdb.DuckDBPyConnection, annee: int, grille: dict[str, str]
    ) -> None:
        """Les codes de liste de l'année sont exactement ceux de la grille, même bloc."""
        assert _codes_muni(con, annee) == grille

    def test_volumes_par_annee(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = con.execute(
            "SELECT annee, COUNT(*) FROM nuances_harmonisees "
            "WHERE annee IN (2008, 2014, 2020, 2026) GROUP BY annee ORDER BY annee"
        ).fetchall()
        assert rows == [(2008, 12), (2014, 17), (2020, 23), (2026, 25)]
        assert len(_NUANCES_MUNI) == 77

    @pytest.mark.parametrize(
        ("nuance", "annee", "bloc"),
        [
            ("LREG", 2020, "DIV"),
            ("LGJ", 2020, "DIV"),
            ("LMDM", 2020, "CENT"),
            ("LDLF", 2020, "DTE"),
            ("LUD", 2026, "DTE"),
            ("LREN", 2026, "CENT"),
            ("LMDM", 2026, "CENT"),
            ("LDSV", 2026, "DTE"),
            ("LREC", 2026, "EXD"),
            ("LREG", 2026, "DIV"),
        ],
    )
    def test_codes_officiels_ajoutes(
        self, con: duckdb.DuckDBPyConnection, nuance: str, annee: int, bloc: str
    ) -> None:
        row = _bloc(con, nuance, annee)
        assert row is not None, f"{nuance} {annee} absent"
        assert row[0] == bloc
        assert "ADR-0010" in row[1]

    def test_lcom_gau_toutes_annees_municipales(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = con.execute(
            "SELECT annee, bloc FROM nuances_harmonisees WHERE nuance = 'LCOM' ORDER BY annee"
        ).fetchall()
        assert rows == [(2008, "GAU"), (2014, "GAU"), (2020, "GAU"), (2026, "GAU")]

    def test_ldvc_2020_source_grille_officielle(self, con: duckdb.DuckDBPyConnection) -> None:
        row = _bloc(con, "LDVC", 2020)
        assert row is not None and row[0] == "CENT"
        assert "INTA1931378J" in row[1]

    def test_relance_loader_municipal_applique_les_reclassements(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        """Base existante avec les anciens blocs : populate_nuances_municipales corrige."""
        con.execute(
            "UPDATE nuances_harmonisees SET bloc = 'EXG' WHERE nuance = 'LCOM' AND annee = 2026"
        )
        con.execute("DELETE FROM nuances_harmonisees WHERE nuance = 'LUD' AND annee = 2026")
        populate_nuances_municipales(con)
        assert _bloc(con, "LCOM", 2026)[0] == "GAU"
        assert _bloc(con, "LUD", 2026)[0] == "DTE"


# ── Lot 2 — codes 2008 en attente de vérification ────────────────────────────


class TestLot2Inchanges:
    @pytest.mark.parametrize(("cle", "attendu"), list(_LOT2_INCHANGES.items()))
    def test_bloc_et_source_inchanges(
        self,
        con: duckdb.DuckDBPyConnection,
        cle: tuple[str, int],
        attendu: tuple[str, str],
    ) -> None:
        assert _bloc(con, *cle) == attendu

    def test_lmaj_2008_toujours_exclu(self, con: duckdb.DuckDBPyConnection) -> None:
        assert _bloc(con, "LMAJ", 2008) is None
        assert all(n != "LMAJ" for n, _, _, _ in _NUANCES_MUNI)


# ── Tous lots — reclassements appliqués et justifiés ─────────────────────────


class TestReclassementsTraces:
    @pytest.mark.parametrize(("cle", "avant_apres"), list(_RECLASSEMENTS.items()))
    def test_nouveau_bloc_et_trace_de_l_ancien(
        self,
        con: duckdb.DuckDBPyConnection,
        cle: tuple[str, int],
        avant_apres: tuple[str, str],
    ) -> None:
        avant, apres = avant_apres
        row = _bloc(con, *cle)
        assert row is not None, f"{cle} absent"
        assert row[0] == apres, f"{cle} → {row[0]} (attendu {apres})"
        assert "ADR-0010" in row[1], f"{cle} : source_bloc sans référence ADR-0010"
        assert f"avant : {avant}" in row[1], f"{cle} : ancien bloc non tracé"

    @pytest.mark.parametrize(("cle", "bloc"), list(_MAINTENUS.items()))
    def test_maintiens_justifies(
        self, con: duckdb.DuckDBPyConnection, cle: tuple[str, int], bloc: str
    ) -> None:
        row = _bloc(con, *cle)
        assert row is not None, f"{cle} absent"
        assert row[0] == bloc
        assert "ADR-0010" in row[1]

    def test_vec_toujours_gau(self) -> None:
        """Règle écologistes corrigée : VEC/LVEC = GAU sur tous les scrutins."""
        blocs = {b for n, _, b, _ in _NUANCES_LEGI + _NUANCES_MUNI if n in ("VEC", "LVEC")}
        assert blocs == {"GAU"}

    def test_eco_selon_la_grille(self) -> None:
        """ECO/LECO : DIV sauf 2017 et 2022 (ECO englobe alors EELV)."""
        eco = {(n, a): b for n, a, b, _ in _NUANCES_LEGI + _NUANCES_MUNI if n in ("ECO", "LECO")}
        gau = {cle for cle, b in eco.items() if b == "GAU"}
        assert gau == {("ECO", 2017), ("ECO", 2022)}
        assert {b for cle, b in eco.items() if cle not in gau} == {"DIV"}

    def test_volumes_pres_legi_inchanges(self) -> None:
        assert len(_NUANCES_PRES) == 38
        assert len(_NUANCES_LEGI) == 111


# ── Effet dans les vues : le bloc résolu suit le référentiel ─────────────────


class TestEffetDansLesVues:
    def test_vue_resultats_avec_bloc(self, con: duckdb.DuckDBPyConnection) -> None:
        create_elections_views(con)
        lignes = [
            ("2020_muni_t1", "LUDI", 1),
            ("2020_muni_t1", "LECO", 2),
            ("2026_muni_t1", "LCOM", 1),
            ("2024_legi_t1", "UDI", 1),
            ("2024_legi_t1", "ECO", 2),
            ("2008_muni_t1", "LMAJ", 1),
        ]
        for id_el, nuance, panneau in lignes:
            con.execute(
                "INSERT INTO resultats_candidats "
                "(id_election, code_departement, code_commune, code_bv, no_panneau, nuance, voix) "
                "VALUES (?, '59', '59350', '0001', ?, ?, 10)",
                [id_el, panneau, nuance],
            )
        rows = con.execute(
            "SELECT id_election, nuance, bloc FROM v_resultats_candidats_avec_bloc "
            "ORDER BY id_election, no_panneau"
        ).fetchall()
        assert rows == [
            ("2008_muni_t1", "LMAJ", None),
            ("2020_muni_t1", "LUDI", "CENT"),
            ("2020_muni_t1", "LECO", "DIV"),
            ("2024_legi_t1", "UDI", "DTE"),
            ("2024_legi_t1", "ECO", "DIV"),
            ("2026_muni_t1", "LCOM", "GAU"),
        ]
