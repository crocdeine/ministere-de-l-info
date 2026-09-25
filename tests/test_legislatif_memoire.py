"""Tests hermétiques du module Législatif — ADR-0011 (groupes par législature).

Base DuckDB temporaire construite à partir de petits échantillons Datan et ODSEN_GENERAL
écrits dans ``tmp_path`` : aucun accès réseau, aucune base réelle. Couvre :
- le référentiel (groupe, législature) → bloc (FI XVe = GAU, LFI-NFP XVIIe = GAU…) ;
- l'absence de groupe non classé dans les données de test (échec sinon) ;
- le WARNING et le bloc NULL pour un groupe inconnu (plus de repli DIV) ;
- les loaders (leg_mandats, dates de fin, filtre Sénat antérieur à 2002) ;
- les vues et les requêtes UI modifiées ; la migration 0008 (idempotence).
"""

from __future__ import annotations

import csv
import importlib.util
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import duckdb
import pytest
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl import legislatif_groupes as lg  # noqa: E402
from ministere_de_l_info.etl.legislatif_groupes import (  # noqa: E402
    CORRESPONDANCES_GROUPES,
    LEGISLATURE_MAX_COUVERTE,
    CorrespondanceGroupe,
    populate_groupes_blocs,
    resoudre_bloc,
    valider_correspondances,
)
from ministere_de_l_info.etl.loaders.legislatif_datan import load_legislatif_datan  # noqa: E402
from ministere_de_l_info.etl.loaders.legislatif_overrides import load_overrides  # noqa: E402
from ministere_de_l_info.etl.loaders.legislatif_senat import load_legislatif_senat  # noqa: E402
from ministere_de_l_info.etl.schema_legislatif import (  # noqa: E402
    create_legislatif_schema,
    create_legislatif_views,
)
from ministere_de_l_info.viz import legislatif_queries as q  # noqa: E402

# ---------------------------------------------------------------------------
# Échantillons
# ---------------------------------------------------------------------------

# (sigle Datan, legislatureLast, departementCode, actif) — sigles observés par législature
_DEPUTES: list[tuple[str, int, str, bool]] = [
    ("UMP", 12, "59", False),
    ("SOC", 12, "62", False),
    ("UDF", 12, "80", False),
    ("CR", 12, "59", False),
    ("NI", 12, "75", False),
    ("SRC", 13, "59", False),
    ("S.R.C.", 13, "02", False),
    ("GDR", 13, "59", False),
    ("NC", 13, "60", False),
    ("UMP", 13, "60", False),
    ("UMP", 14, "13", False),
    ("R-UMP", 14, "06", False),
    ("LES-REP", 14, "69", False),
    ("SER", 14, "31", False),
    ("RRDP", 14, "11", False),
    ("ECOLO", 14, "35", False),
    ("UDI", 14, "33", False),
    ("LAREM", 15, "59", False),
    ("MODEM", 15, "64", False),
    ("FI", 15, "59", False),
    ("FI", 15, "93", False),
    ("NG", 15, "62", False),
    ("LT", 15, "2A", False),
    ("UDI-AGIR", 15, "51", False),
    ("UDI_I", 15, "51", False),
    ("AGIR-E", 15, "92", False),
    ("LC", 15, "78", False),
    ("LR", 15, "80", False),
    ("DEM", 15, "64", False),
    ("RE", 16, "59", False),
    ("LFI-NUPES", 16, "59", False),
    ("GDR-NUPES", 16, "62", False),
    ("HOR", 16, "76", False),
    ("RN", 16, "62", False),
    ("LIOT", 16, "971", False),
    ("LR", 16, "43", False),
    ("ECOLO", 16, "69", False),
    ("SOC", 16, "40", False),
    ("EPR", 17, "59", True),
    ("LFI-NFP", 17, "59", True),
    ("LFI-NFP", 17, "93", True),
    ("DR", 17, "80", True),
    ("UDR", 17, "06", True),
    ("UDDPLR", 17, "06", True),
    ("ECOS", 17, "59", True),
    ("SOC", 17, "62", True),
    ("RN", 17, "62", True),
    ("RN", 17, "02", True),
    ("DEM", 17, "64", True),
    ("HOR", 17, "76", True),
    ("LIOT", 17, "2B", True),
    ("GDR", 17, "972", True),
    ("NI", 17, "60", True),
]

_DATAN_COLONNES = [
    "id", "legislatureLast", "civ", "nom", "prenom", "villeNaissance", "naissance", "age",
    "groupe", "groupeAbrev", "departementNom", "departementCode", "circo",
    "datePriseFonction", "job", "mail", "twitter", "facebook", "website", "nombreMandats",
    "experienceDepute", "scoreParticipation", "scoreParticipationSpecialite", "scoreLoyaute",
    "scoreMajorite", "active", "dateMaj",
]  # fmt: skip

_SENAT_COLONNES = [
    "Matricule", "Qualité", "Nom usuel", "Prénom usuel", "État", "Date naissance",
    "Date de décès", "Groupe politique", "Type d'app au grp politique",
    "Commission permanente", "Circonscription", "Fonction au Bureau du Sénat",
    "Courrier électronique", "PCS INSEE", "Catégorie professionnelle",
    "Description de la profession",
]  # fmt: skip

# (matricule, état, groupe, circonscription, date de décès)
_SENATEURS: list[tuple[str, str, str, str, str]] = [
    ("S001", "ACTIF", "CRCE-K", "Nord", ""),
    ("S002", "ACTIF", "SER", "Pas-de-Calais", ""),
    ("S003", "ACTIF", "GEST", "Paris", ""),
    ("S004", "ACTIF", "RDPI", "Guadeloupe", ""),
    ("S005", "ACTIF", "UC", "Somme", ""),
    ("S006", "ACTIF", "Les Indépendants", "Allier", ""),
    ("S007", "ACTIF", "RDSE", "Corse-du-Sud", ""),
    ("S008", "ACTIF", "Les Républicains", "Oise", ""),
    ("21085M", "ACTIF", "NI", "Nord", ""),
    ("21069M", "ACTIF", "NI", "Pas-de-Calais", ""),
    ("A001", "ANCIEN", "UMP", "Aisne", ""),
    ("A002", "ANCIEN", "CRC", "Nord", ""),
    ("A003", "ANCIEN", "SOC", "Somme", "2019-03-01 00:00:00.0"),
    ("A004", "ANCIEN", "UC-UDF", "Oise", ""),
    ("A005", "ANCIEN", "CRCE", "Val-de-Marne", ""),
    # Hors périmètre 2002-présent : circonscription disparue, décès avant 2002
    ("H001", "ANCIEN", "RPR", "Seine-et-Oise", ""),
    ("H002", "ANCIEN", "RI", "Nord", "1998-05-12 00:00:00.0"),
    # Hors périmètre : dernier groupe disparu avant 2002 (addendum ADR-0011, sigles réels)
    ("H003", "ANCIEN", "G.D.", "Aisne", ""),
    ("H004", "ANCIEN", "U.C.D.P.", "Somme", ""),
]


def _ecrire_datan(raw_dir: Path, deputes: list[tuple[str, int, str, bool]]) -> None:
    chemin = raw_dir / "legislatif" / "datan-deputes-historique.csv"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_DATAN_COLONNES)
        writer.writeheader()
        for i, (sigle, leg, dep, actif) in enumerate(deputes, start=1):
            writer.writerow(
                {
                    "id": f"PA{i:04d}",
                    "legislatureLast": str(leg),
                    "civ": "Mme" if i % 2 else "M.",
                    "nom": f"Nom{i:03d}",
                    "prenom": f"Prenom{i:03d}",
                    "naissance": "1970-01-01",
                    "groupe": f"Groupe {sigle}",
                    "groupeAbrev": sigle,
                    "departementNom": f"Dept {dep}",
                    "departementCode": dep,
                    "circo": str(1 + i % 5),
                    "datePriseFonction": "2024-07-07" if actif else "2017-06-21",
                    "job": "Profession",
                    "scoreParticipation": str(40 + i % 50),
                    "scoreParticipationSpecialite": "55.5",
                    "scoreLoyaute": "90",
                    "scoreMajorite": "50",
                    "active": "1" if actif else "0",
                    "dateMaj": "2026-06-17",
                }
            )


def _ecrire_senat(raw_dir: Path, senateurs: list[tuple[str, str, str, str, str]]) -> None:
    chemin = raw_dir / "legislatif" / "senat-odsen-general.csv"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    lignes = [f"% commentaire {i}" for i in range(18)]
    lignes.append(",".join(f'"{c}"' for c in _SENAT_COLONNES))
    for mat, etat, groupe, circo, deces in senateurs:
        valeurs = dict.fromkeys(_SENAT_COLONNES, "")
        valeurs.update(
            {
                "Matricule": mat,
                "Qualité": "M.",
                "Nom usuel": f"NOM {mat}",
                "Prénom usuel": "Prénom",
                "État": etat,
                "Date naissance": "1960-01-01 00:00:00.0",
                "Date de décès": deces,
                "Groupe politique": groupe,
                "Circonscription": circo,
                "Description de la profession": "Élu local",
            }
        )
        lignes.append(",".join(f'"{valeurs[c]}"' for c in _SENAT_COLONNES))
    chemin.write_bytes(("\n".join(lignes) + "\n").encode("cp1252"))


def _creer_meta(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS _etl_metadata (table_name VARCHAR NOT NULL, "
        "loaded_at TIMESTAMP NOT NULL, source_version VARCHAR, row_count INTEGER NOT NULL, "
        "UNIQUE (table_name))"
    )


def _charger(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    _creer_meta(con)
    create_legislatif_schema(con)
    populate_groupes_blocs(con)
    load_legislatif_senat(con, raw_dir)
    load_legislatif_datan(con, raw_dir)
    load_overrides(con)
    create_legislatif_views(con)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    d = tmp_path / "raw"
    _ecrire_datan(d, _DEPUTES)
    _ecrire_senat(d, _SENATEURS)
    return d


@pytest.fixture
def con(raw_dir: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    c = duckdb.connect()
    _charger(c, raw_dir)
    yield c
    c.close()


@pytest.fixture
def base_ro(raw_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Base fichier chargée, requêtes UI redirigées dessus en lecture seule."""
    chemin = tmp_path / "leg.duckdb"
    c = duckdb.connect(str(chemin))
    _charger(c, raw_dir)
    c.close()
    monkeypatch.setattr(q, "_open_ro", lambda: duckdb.connect(str(chemin), read_only=True))
    st.cache_data.clear()
    yield chemin
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Référentiel (groupe, législature) → bloc
# ---------------------------------------------------------------------------


class TestReferentiel:
    def test_referentiel_valide(self) -> None:
        valider_correspondances()

    @pytest.mark.parametrize(
        ("chambre", "groupe", "legislature", "attendu"),
        [
            ("AN", "FI", 15, "GAU"),
            ("AN", "LFI-NUPES", 16, "GAU"),
            ("AN", "LFI-NFP", 17, "GAU"),
            ("AN", "RRDP", 14, "GAU"),
            ("AN", "GDR", 13, "GAU"),
            ("AN", "UMP", 12, "DTE"),
            ("AN", "LAREM", 15, "CENT"),
            ("AN", "RN", 17, "EXD"),
            ("AN", "UDR", 17, "EXD"),
            ("AN", "LIOT", 17, "DIV"),
            ("AN", "NI", 12, "DIV"),
            ("SENAT", "GEST", None, "GAU"),
            ("SENAT", "RDPI", None, "CENT"),
            ("SENAT", "Les Indépendants", None, "CENT"),
            ("SENAT", "CRCE-K", None, "GAU"),
            ("SENAT", "NI", None, "DIV"),
        ],
    )
    def test_bloc_par_legislature(
        self, chambre: str, groupe: str, legislature: int | None, attendu: str
    ) -> None:
        assert resoudre_bloc(chambre, groupe, legislature) == attendu

    @pytest.mark.parametrize(
        ("chambre", "groupe", "legislature"),
        [
            ("AN", "FI", 18),  # législature non couverte : revue obligatoire
            ("AN", "LFI-NFP", 18),
            ("AN", "LFI-NFP", 16),  # sigle hors de sa législature
            ("AN", "RN", 15),
            ("AN", "EDS", 15),  # groupe non tranché
            ("AN", "SOC", None),  # législature inconnue
            ("SENAT", "RPR", None),
            ("SENAT", None, None),
        ],
    )
    def test_non_classe(self, chambre: str, groupe: str | None, legislature: int | None) -> None:
        assert resoudre_bloc(chambre, groupe, legislature) is None

    @pytest.mark.parametrize(
        ("groupe", "attendu"),
        [
            ("RPR", True),
            ("R.P.R.", True),
            ("RI", True),
            ("UNR", True),
            ("G.D.", True),
            ("U.C.D.P.", True),
            ("R.D.E.", True),
            ("C.R.A.R.S.", True),
            ("UREI", True),
            # Groupes existant après 2002 : dans le périmètre
            ("RDSE", False),
            ("UC", False),
            ("UMP", False),
            ("CRC", False),
            ("UC-UDF", False),
            # Inconnu : jamais écarté, reste signalé « non classé »
            ("Groupe inventé", False),
            (None, False),
            ("", False),
        ],
    )
    def test_groupes_senat_anterieurs_2002(self, groupe: str | None, attendu: bool) -> None:
        assert lg.est_groupe_senat_anterieur_2002(groupe) is attendu

    def test_groupes_anterieurs_2002_sans_bloc_ni_recouvrement(self) -> None:
        """Aucun groupe hors périmètre n'est classé ; chaque entrée est justifiée."""
        for g in lg.GROUPES_SENAT_ANTERIEURS_2002:
            assert g.sigle == lg.normaliser_sigle(g.sigle)
            assert g.justification.strip() and g.periode.strip()
            assert resoudre_bloc("SENAT", g.sigle, None) is None
        sigles = [g.sigle for g in lg.GROUPES_SENAT_ANTERIEURS_2002]
        assert len(sigles) == len(set(sigles))

    def test_validation_detecte_groupe_historique_classe(self) -> None:
        conflit = CorrespondanceGroupe("SENAT", "R.P.R.", None, None, "DTE", "RPR", "test")
        with pytest.raises(ValueError, match="antérieurs à 2002"):
            valider_correspondances((*CORRESPONDANCES_GROUPES, conflit))

    def test_aucun_groupe_lfi_en_exg_avant_2026(self) -> None:
        """ADR-0005 n° 3 : aucune législature 15-17 ne place LFI en EXG."""
        for c in CORRESPONDANCES_GROUPES:
            if c.groupe in {"FI", "LFI-NUPES", "LFI-NFP"}:
                assert c.bloc == "GAU", c

    def test_lfi_nfp_documente_la_grille_2026(self) -> None:
        (c,) = [c for c in CORRESPONDANCES_GROUPES if c.groupe == "LFI-NFP"]
        assert "IOMA2322276J" in c.source_bloc
        assert "INTP2602966C" in c.source_bloc and "EXG" in c.source_bloc

    def test_intervalles_an_bornes(self) -> None:
        for c in CORRESPONDANCES_GROUPES:
            if c.chambre == "AN":
                assert c.legislature_debut is not None and c.legislature_fin is not None
                assert 12 <= c.legislature_debut <= c.legislature_fin <= LEGISLATURE_MAX_COUVERTE

    def test_validation_detecte_recouvrement(self) -> None:
        doublon = (
            CorrespondanceGroupe("AN", "X", 12, 15, "GAU", "x", "s"),
            CorrespondanceGroupe("AN", "X", 15, 17, "EXG", "x", "s"),
        )
        with pytest.raises(ValueError, match="recouvrent"):
            valider_correspondances(doublon)

    def test_validation_detecte_bloc_invalide(self) -> None:
        with pytest.raises(ValueError, match="ADR-0005"):
            valider_correspondances((CorrespondanceGroupe("AN", "X", 12, 12, "EG", "x", "s"),))

    def test_table_leg_groupes_blocs(self) -> None:
        c = duckdb.connect()
        create_legislatif_schema(c)
        n1 = populate_groupes_blocs(c)
        n2 = populate_groupes_blocs(c)  # idempotent
        assert n1 == n2 == c.execute("SELECT COUNT(*) FROM leg_groupes_blocs").fetchone()[0]
        vides = c.execute(
            "SELECT COUNT(*) FROM leg_groupes_blocs WHERE TRIM(source_bloc) = ''"
        ).fetchone()[0]
        assert vides == 0
        c.close()


# ---------------------------------------------------------------------------
# Loaders et vues
# ---------------------------------------------------------------------------


class TestChargement:
    def test_aucun_groupe_non_classe_dans_les_donnees_de_test(
        self, raw_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Échoue si un groupe présent dans les échantillons n'est pas dans le référentiel."""
        c = duckdb.connect()
        with caplog.at_level(logging.WARNING, logger=lg.__name__):
            _charger(c, raw_dir)
        non_classes = c.execute(
            "SELECT chambre, groupe_sigle, legislature FROM v_mandats_legislatif "
            "WHERE bloc_groupe IS NULL"
        ).fetchall()
        c.close()
        assert non_classes == []
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_groupe_inconnu_null_et_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        raw = tmp_path / "raw_inconnu"
        _ecrire_datan(raw, [("EDS", 15, "59", False), ("SOC", 18, "62", True)])
        _ecrire_senat(raw, [("S1", "ACTIF", "Groupe inventé", "Nord", "")])
        c = duckdb.connect()
        with caplog.at_level(logging.WARNING, logger=lg.__name__):
            _charger(c, raw)
        blocs = c.execute(
            "SELECT groupe_sigle, bloc_politique FROM leg_elus ORDER BY groupe_sigle"
        ).fetchall()
        c.close()
        assert blocs == [("EDS", None), ("Groupe inventé", None), ("SOC", None)]
        messages = " ".join(r.getMessage() for r in caplog.records)
        assert "EDS (lég. 15)" in messages and "SOC (lég. 18)" in messages
        assert "Groupe inventé" in messages

    def test_un_mandat_par_depute_datan(self, con: duckdb.DuckDBPyConnection) -> None:
        n_elus, n_mandats = con.execute(
            "SELECT (SELECT COUNT(*) FROM leg_elus WHERE chambre = 'AN'), "
            "(SELECT COUNT(*) FROM leg_mandats WHERE chambre = 'AN')"
        ).fetchone()
        assert n_elus == n_mandats == len(_DEPUTES)
        granularites = con.execute(
            "SELECT DISTINCT granularite FROM leg_mandats WHERE chambre = 'AN'"
        ).fetchall()
        assert granularites == [("derniere_legislature",)]

    def test_bloc_du_mandat_selon_legislature(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = con.execute(
            "SELECT DISTINCT groupe_sigle, legislature, bloc_final FROM v_mandats_legislatif "
            "WHERE groupe_sigle IN ('FI', 'LFI-NUPES', 'LFI-NFP', 'RRDP') ORDER BY 2"
        ).fetchall()
        assert rows == [
            ("RRDP", 14, "GAU"),
            ("FI", 15, "GAU"),
            ("LFI-NUPES", 16, "GAU"),
            ("LFI-NFP", 17, "GAU"),
        ]

    def test_dates_de_fin_non_inventees(self, con: duckdb.DuckDBPyConnection) -> None:
        n = con.execute(
            "SELECT COUNT(*) FROM leg_elus WHERE date_fin_mandat IS NOT NULL"
        ).fetchone()[0]
        assert n == 0
        n = con.execute("SELECT COUNT(*) FROM leg_mandats WHERE date_fin IS NOT NULL").fetchone()[0]
        assert n == 0

    def test_senat_filtre_anterieurs_2002(self, con: duckdb.DuckDBPyConnection) -> None:
        ids = {
            r[0] for r in con.execute("SELECT id FROM leg_elus WHERE chambre = 'SENAT'").fetchall()
        }
        assert not {"H001", "H002", "H003", "H004"} & ids
        assert {"A001", "A002", "A003", "A004", "A005"} <= ids
        assert len(ids) == len(_SENATEURS) - 4
        n_mandats = con.execute(
            "SELECT COUNT(*) FROM leg_mandats WHERE chambre = 'SENAT'"
        ).fetchone()[0]
        assert n_mandats == len(ids)

    def test_senat_groupes_anterieurs_2002_logges_en_info(
        self, raw_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        c = duckdb.connect()
        with caplog.at_level(logging.INFO):
            _charger(c, raw_dir)
        c.close()
        infos = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        message = next(m for m in infos if "disparu avant le renouvellement de 2002" in m)
        assert "2 ancien(s)" in message
        assert "G.D. × 1" in message and "U.C.D.P. × 1" in message
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_senateur_actif_groupe_historique_reste_signale(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Un sénateur ACTIF n'est jamais écarté : sigle historique = anomalie signalée."""
        raw = tmp_path / "raw_actif"
        _ecrire_senat(raw, [("S1", "ACTIF", "RPR", "Nord", "")])
        c = duckdb.connect()
        _creer_meta(c)
        create_legislatif_schema(c)
        with caplog.at_level(logging.WARNING):
            load_legislatif_senat(c, raw)
        rows = c.execute("SELECT id, bloc_politique FROM leg_elus").fetchall()
        c.close()
        assert rows == [("S1", None)]
        assert any("RPR" in r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)

    def test_depute_sans_groupe(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """groupeAbrev vide : statut « sans groupe » (NULL, INFO), pas « non classé »."""
        raw = tmp_path / "raw_sans_groupe"
        _ecrire_datan(raw, [("", 15, "59", False), ("SOC", 15, "62", False)])
        _ecrire_senat(raw, [("S1", "ACTIF", "SER", "Nord", "")])
        c = duckdb.connect()
        with caplog.at_level(logging.INFO):
            _charger(c, raw)
        rows = c.execute(
            "SELECT groupe_sigle, groupe_nom, bloc_groupe FROM v_mandats_legislatif "
            "WHERE chambre = 'AN' ORDER BY groupe_sigle NULLS FIRST"
        ).fetchall()
        elus = c.execute(
            "SELECT groupe_sigle, bloc_politique FROM leg_elus WHERE chambre = 'AN' "
            "ORDER BY groupe_sigle NULLS FIRST"
        ).fetchall()
        c.close()
        assert rows[0][0] is None and rows[0][2] is None
        assert rows[1] == ("SOC", "Groupe SOC", "GAU")
        assert elus == [(None, None), ("SOC", "GAU")]
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any(
            "sans groupe" in r.getMessage() and "lég. 15 × 1" in r.getMessage()
            for r in caplog.records
        )

    def test_senat_filtre_desactivable(self, raw_dir: Path) -> None:
        c = duckdb.connect()
        _creer_meta(c)
        create_legislatif_schema(c)
        load_legislatif_senat(c, raw_dir, inclure_anterieurs_2002=True)
        n = c.execute("SELECT COUNT(*) FROM leg_elus WHERE chambre = 'SENAT'").fetchone()[0]
        c.close()
        assert n == len(_SENATEURS)

    def test_rechargement_idempotent(self, con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
        avant = con.execute("SELECT COUNT(*) FROM leg_mandats").fetchone()[0]
        _charger(con, raw_dir)
        assert con.execute("SELECT COUNT(*) FROM leg_mandats").fetchone()[0] == avant

    def test_vue_elus_actuels_et_alias(self, con: duckdb.DuckDBPyConnection) -> None:
        n = con.execute("SELECT COUNT(*) FROM v_elus_actuels").fetchone()[0]
        n_alias = con.execute("SELECT COUNT(*) FROM v_elus_hdf_actuels").fetchone()[0]
        n_actifs = con.execute("SELECT COUNT(*) FROM leg_elus WHERE est_actif").fetchone()[0]
        assert n == n_alias == n_actifs
        # Nationale : des élus hors HdF sont présents (nom exact de la vue)
        hors_hdf = con.execute(
            "SELECT COUNT(*) FROM v_elus_actuels "
            "WHERE code_departement NOT IN ('02', '59', '60', '62', '80')"
        ).fetchone()[0]
        assert hors_hdf > 0

    def test_override_prime_sur_groupe(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = con.execute(
            "SELECT id, bloc_groupe, bloc_final FROM v_elus_actuels "
            "WHERE id IN ('21085M', '21069M') ORDER BY id"
        ).fetchall()
        assert rows == [("21069M", "DIV", "EXD"), ("21085M", "DIV", "EXD")]

    def test_vue_sans_doublon(self, con: duckdb.DuckDBPyConnection) -> None:
        n_vue = con.execute("SELECT COUNT(*) FROM v_mandats_legislatif").fetchone()[0]
        n_table = con.execute("SELECT COUNT(*) FROM leg_mandats").fetchone()[0]
        assert n_vue == n_table

    def test_composition_legislature(self, con: duckdb.DuckDBPyConnection) -> None:
        rows = con.execute(
            "SELECT bloc_final, nb_elus FROM v_composition_legislature "
            "WHERE chambre = 'AN' AND legislature = 15 AND bloc_final = 'GAU'"
        ).fetchall()
        assert rows == [("GAU", 3)]  # FI × 2 + NG

    def test_activite_par_bloc(self, con: duckdb.DuckDBPyConnection) -> None:
        blocs = {
            r[0]
            for r in con.execute(
                "SELECT bloc FROM v_activite_par_bloc WHERE chambre='AN'"
            ).fetchall()
        }
        assert "EXG" not in blocs and None not in blocs


# ---------------------------------------------------------------------------
# Requêtes UI (viz/legislatif_queries.py)
# ---------------------------------------------------------------------------


class TestRequetes:
    def test_evolution_bloc_par_legislature(self, base_ro: Path) -> None:
        df = q.get_evolution_composition_an()
        assert set(df["granularite"].to_list()) == {"derniere_legislature"}
        assert set(df["legislature"].to_list()) == {12, 13, 14, 15, 16, 17}
        assert "EXG" not in df["bloc_final"].to_list()
        assert q.BLOC_NON_CLASSE not in df["bloc_final"].to_list()
        gau_15 = df.filter((df["legislature"] == 15) & (df["bloc_final"] == "GAU"))
        assert gau_15["nb_elus"].to_list() == [3]

    def test_evolution_filtre_departement(self, base_ro: Path) -> None:
        df = q.get_evolution_composition_an(codes_departement=("93",))
        assert df.select("legislature", "bloc_final", "nb_elus").rows() == [
            (15, "GAU", 1),
            (17, "GAU", 1),
        ]

    def test_historique_legislatures(self, base_ro: Path) -> None:
        df = q.get_historique_legislatures_an()
        assert df["nb_deputes"].sum() == len(_DEPUTES)

    def test_composition_senat(self, base_ro: Path) -> None:
        df = q.get_composition_politique(chambre="SENAT")
        compo = dict(df.select("bloc_final", "nb_elus").rows())
        assert compo == {"GAU": 3, "CENT": 3, "DIV": 1, "DTE": 1, "EXD": 2}

    def test_elus_actuels_non_classe_affiche_nc(
        self, base_ro: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c = duckdb.connect(str(base_ro))
        c.execute("UPDATE leg_elus SET groupe_sigle = 'INCONNU' WHERE id = 'S007'")
        c.close()
        st.cache_data.clear()
        df = q.get_elus_actuels(chambre="SENAT")
        assert df.filter(df["id"] == "S007")["bloc_final"].to_list() == [q.BLOC_NON_CLASSE]

    def test_classement_complet_et_top(self, base_ro: Path) -> None:
        complet = q.get_classement_activite("AN", "score_participation", n=None)
        n_actifs = sum(1 for d in _DEPUTES if d[3])
        assert complet.height == n_actifs
        assert complet["rang"].to_list() == sorted(complet["rang"].to_list())
        top = q.get_classement_activite("AN", "score_participation", n=3)
        assert top.height == 3
        assert top["id"].to_list() == complet["id"].head(3).to_list()

    def test_classement_senat_vide(self, base_ro: Path) -> None:
        df = q.get_classement_activite("SENAT", "score_loyaute")
        assert df.is_empty() and "rang" in df.columns

    def test_classement_indicateur_invalide(self, base_ro: Path) -> None:
        with pytest.raises(ValueError):
            q.get_classement_activite("AN", "nom; DROP TABLE leg_elus")

    def test_fiche_elu(self, base_ro: Path) -> None:
        elu_id = q.get_elus_actuels(chambre="AN").filter(
            q.get_elus_actuels(chambre="AN")["groupe_sigle"] == "ECOS"
        )["id"][0]
        fiche = q.get_fiche_elu(elu_id, "AN")
        assert fiche.height == 1
        assert fiche.row(0, named=True)["bloc_final"] == "GAU"
        assert "IOMA2322276J" in fiche.row(0, named=True)["source_bloc"]
        scores = q.get_activite_elu(elu_id, "AN")
        assert scores.height == 1 and scores["score_loyaute"][0] == 90.0


# ---------------------------------------------------------------------------
# Migration 0008
# ---------------------------------------------------------------------------


def _charger_migration() -> ModuleType:
    chemin = ROOT / "scripts" / "migrations" / "0008_legislatif_groupes_par_legislature.py"
    spec = importlib.util.spec_from_file_location("_test_migration_0008", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigration0008:
    def _base_ancienne(self) -> duckdb.DuckDBPyConnection:
        """Base au format Phase F : leg_elus seul, FI en EXG, date_fin = date du chargement."""
        c = duckdb.connect()
        create_legislatif_schema(c)
        c.execute("DROP TABLE leg_mandats")
        c.execute("DROP TABLE leg_groupes_blocs")
        c.execute("""
            INSERT INTO leg_elus (id, chambre, legislature, nom, prenom, code_departement,
                groupe_sigle, groupe_nom, bloc_politique, date_fin_mandat, est_actif, source)
            VALUES
              ('PA1', 'AN', 15, 'A', 'a', '59', 'FI', 'FI', 'EXG', '2026-06-17', FALSE, 'datan'),
              ('PA2', 'AN', 17, 'B', 'b', '93', 'LFI-NFP', 'LFI', 'EXG', NULL, TRUE, 'datan'),
              ('S1', 'SENAT', NULL, 'C', 'c', '75', 'GEST', 'GEST', 'DIV', NULL, TRUE,
               'senat_csv'),
              ('S2', 'SENAT', NULL, 'D', 'd', '59', 'UMP', 'UMP', 'DIV', '2026-06-22', FALSE,
               'senat_csv')
        """)
        return c

    def test_migration_idempotente(self) -> None:
        migration = _charger_migration()
        c = self._base_ancienne()
        r1 = migration.appliquer_migration(c)
        r2 = migration.appliquer_migration(c)
        assert r1["mandats"] == r2["mandats"] == 4
        assert r1["inseres"] == 4 and r2["inseres"] == 0
        assert r1["non_classes"] == 0
        blocs = dict(c.execute("SELECT id, bloc_politique FROM leg_elus").fetchall())
        assert blocs == {"PA1": "GAU", "PA2": "GAU", "S1": "GAU", "S2": "DTE"}
        assert (
            c.execute("SELECT COUNT(*) FROM leg_elus WHERE date_fin_mandat IS NOT NULL").fetchone()[
                0
            ]
            == 0
        )
        assert c.execute("SELECT COUNT(*) FROM v_elus_hdf_actuels").fetchone()[0] == 2
        c.close()


# ---------------------------------------------------------------------------
# Page Streamlit (AppTest, même processus : _open_ro redirigé sur la base temporaire)
# ---------------------------------------------------------------------------


def _page_legislatif() -> None:
    from ministere_de_l_info.pages.legislatif import render

    render()


class TestPage:
    def test_rendu_par_defaut(self, base_ro: Path) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_function(_page_legislatif, default_timeout=60).run()
        assert not at.exception, at.exception
        # Onglet Activité utilisable avec Chambre = « Toutes » (plus de blocage)
        textes = " ".join(c.value for c in at.caption)
        assert "affichage des députés" in textes
        assert any(s.value.startswith("Top 20") for s in at.subheader)
        assert any(s.value == "Fiche d'un député" for s in at.subheader)
        # Évolution : graphique partiel signalé explicitement
        assert any("dernière" in w.value for w in at.warning)

    def test_fiche_depute(self, base_ro: Path) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_function(_page_legislatif, default_timeout=60).run()
        fiche = at.selectbox(key="leg_fiche_depute")
        fiche.select_index(0).run()
        assert not at.exception, at.exception
        assert any("Rang" in c.value for c in at.caption)
        assert len(at.metric) >= 4
