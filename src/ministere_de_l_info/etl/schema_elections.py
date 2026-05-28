"""Schéma DuckDB — tables électorales et référentiels politiques.

Séparé de schema.py pour la clarté.

Fonctions exportées
-------------------
- create_elections_schema(con)        : CREATE TABLE IF NOT EXISTS × 6, idempotent
- populate_elections_referentiels(con): remplit blocs_politiques, elections,
  nuances_harmonisees et candidats_presidentielle ; idempotent (DELETE + INSERT)

Les tables de résultats (resultats_participation, resultats_candidats) sont créées
vides ici ; le chargement des Parquet est fait en C2b (scripts/load_elections.py).

Filtrage géographique
---------------------
Le chargement C2b filtrera sur CODE_REGION_HDF = "32" (Hauts-de-France) via
jointure sur geographies_communes.code_region.

Blocs politiques
----------------
Nomenclature officielle du Ministère de l'Intérieur : 6 blocs (EXG, GAU, DIV, CENT,
DTE, EXD), introduits par la circulaire IOMA2322276J (sénatoriales 2023).
Le classement "officiel de l'époque" s'applique : un parti est classé selon le bloc
qui lui était attribué à la date du scrutin. Chaque entrée porte une colonne
source_bloc indiquant la circulaire ou décision CE de référence.
Voir docs/adr/0005-nuances-et-blocs-officiels.md et
docs/sources-officielles/nuances/index.md.
"""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)

# Code INSEE de la région Hauts-de-France (filtrage géographique C2b)
CODE_REGION_HDF: str = "32"

# ── Types de scrutin → libellé ────────────────────────────────────────────────

_TYPE_LIBELLE: dict[str, str] = {
    "pres": "Présidentielle",
    "legi": "Législatives",
    "euro": "Européennes",
    "regi": "Régionales",
    "muni": "Municipales",
    "dpmt": "Départementales",
    "cant": "Cantonales",
}


def _build_elections() -> list[tuple[str, str, int, int, str]]:
    """Construit la liste des 56 scrutins connus (1999–2026)."""
    # (type_scrutin, annee, tour)
    raw: list[tuple[str, int, int]] = [
        ("euro", 1999, 1),
        ("cant", 2001, 1),
        ("cant", 2001, 2),
        ("legi", 2002, 1),
        ("legi", 2002, 2),
        ("pres", 2002, 1),
        ("pres", 2002, 2),
        ("cant", 2004, 1),
        ("cant", 2004, 2),
        ("euro", 2004, 1),
        ("regi", 2004, 1),
        ("regi", 2004, 2),
        ("legi", 2007, 1),
        ("legi", 2007, 2),
        ("pres", 2007, 1),
        ("pres", 2007, 2),
        ("cant", 2008, 1),
        ("cant", 2008, 2),
        ("muni", 2008, 1),
        ("muni", 2008, 2),
        ("euro", 2009, 1),
        ("regi", 2010, 1),
        ("regi", 2010, 2),
        ("cant", 2011, 1),
        ("cant", 2011, 2),
        ("legi", 2012, 1),
        ("legi", 2012, 2),
        ("pres", 2012, 1),
        ("pres", 2012, 2),
        ("euro", 2014, 1),
        ("muni", 2014, 1),
        ("muni", 2014, 2),
        ("dpmt", 2015, 1),
        ("dpmt", 2015, 2),
        ("regi", 2015, 1),
        ("regi", 2015, 2),
        ("legi", 2017, 1),
        ("legi", 2017, 2),
        ("pres", 2017, 1),
        ("pres", 2017, 2),
        ("euro", 2019, 1),
        ("muni", 2020, 1),
        ("muni", 2020, 2),
        ("dpmt", 2021, 1),
        ("dpmt", 2021, 2),
        ("regi", 2021, 1),
        ("regi", 2021, 2),
        ("legi", 2022, 1),
        ("legi", 2022, 2),
        ("pres", 2022, 1),
        ("pres", 2022, 2),
        ("euro", 2024, 1),
        ("legi", 2024, 1),
        ("legi", 2024, 2),
        ("muni", 2026, 1),
        ("muni", 2026, 2),
    ]
    result: list[tuple[str, str, int, int, str]] = []
    for typ, annee, tour in raw:
        id_el = f"{annee}_{typ}_t{tour}"
        tour_str = "1er tour" if tour == 1 else "2e tour"
        libelle = f"{_TYPE_LIBELLE[typ]} {annee} — {tour_str}"
        result.append((id_el, typ, annee, tour, libelle))
    return result


_ELECTIONS: list[tuple[str, str, int, int, str]] = _build_elections()

# ── Blocs politiques ──────────────────────────────────────────────────────────
# Nomenclature officielle Ministère de l'Intérieur — 6 blocs, codes en majuscules.
# Source : circulaire IOMA2322276J (sénatoriales 2023, 1re occurrence du regroupement).
# (bloc, libelle, couleur_hex, ordre_gauche_droite)

_BLOCS: list[tuple[str, str, str, int]] = [
    ("EXG", "Extrême gauche", "#8B0000", 1),
    ("GAU", "Gauche", "#E84C61", 2),
    ("DIV", "Divers", "#9E9E9E", 3),
    ("CENT", "Centre", "#F5B800", 4),
    ("DTE", "Droite", "#3B7DD8", 5),
    ("EXD", "Extrême droite", "#1F3864", 6),
]

# ── Nuances → blocs, présidentielles 2002 / 2007 / 2012 ──────────────────────
# Pour ces scrutins, la colonne 'nuance' du Parquet est un code-candidat
# (CHIR = Chirac, JOSP = Jospin, etc.), contrairement aux scrutins de liste
# qui utilisent des codes partisans (RN, SOC, LDVG, …).
# Blocs officiels Ministère (reconstruction ante-2023 selon ADR-0005).
# (nuance, annee, bloc)
#
_NUANCES_PRES: list[tuple[str, int, str]] = [
    # ── 2002 (16 candidats) ────────────────────────────────────────────────
    ("BAYR", 2002, "CENT"),  # Bayrou – UDF → CENT
    ("BESA", 2002, "EXG"),  # Besancenot – LCR trotskiste → EXG
    (
        "BOUT",
        2002,
        "DTE",
    ),  # Boutin – FRS conservateur chrétien, floue DTE/EXD ; retenu DTE par cohérence nomenclature Ministère
    ("CHEV", 2002, "GAU"),  # Chevènement – MDC (socialiste dissident ex-PS) → GAU
    ("CHIR", 2002, "DTE"),  # Chirac – RPR gaulliste → DTE
    ("GLUC", 2002, "EXG"),  # Gluckstein – PT trotskiste → EXG
    ("HUE", 2002, "GAU"),  # Hue – PCF → GAU (logique officielle Ministère, pas EXG)
    ("JOSP", 2002, "GAU"),  # Jospin – PS → GAU
    ("LAGU", 2002, "EXG"),  # Laguiller – LO → EXG
    (
        "LEPA",
        2002,
        "CENT",
    ),  # Lepage – Cap21 (écologie libérale centriste) → CENT ; pas de bloc écolo officiel
    ("LEPE", 2002, "EXD"),  # Le Pen J.-M. – FN → EXD
    ("MADE", 2002, "DTE"),  # Madelin – DL (libéral-conservateur) → DTE
    ("MAME", 2002, "GAU"),  # Mamère – Verts (nuance DVGV) → GAU
    ("MEGR", 2002, "EXD"),  # Mégret – MNR (scissionniste FN) → EXD
    ("SAIN", 2002, "DIV"),  # Saint-Josse – CPNT → DIV
    ("TAUB", 2002, "GAU"),  # Taubira – PRG (allié PS) → GAU
    # ── 2007 (12 candidats) ────────────────────────────────────────────────
    ("BAYR", 2007, "CENT"),  # Bayrou – MoDem → CENT
    ("BESA", 2007, "EXG"),  # Besancenot – LCR → EXG
    ("BOVE", 2007, "GAU"),  # Bové – altermondialiste/soutien Verts (DVGV) → GAU
    ("BUFF", 2007, "GAU"),  # Buffet – PCF → GAU
    ("LAGU", 2007, "EXG"),  # Laguiller – LO → EXG
    ("LEPE", 2007, "EXD"),  # Le Pen J.-M. – FN → EXD
    ("NIHO", 2007, "DIV"),  # Nihous – CPNT → DIV
    ("ROYA", 2007, "GAU"),  # Royal – PS → GAU
    ("SARK", 2007, "DTE"),  # Sarkozy – UMP → DTE
    ("SCHI", 2007, "EXG"),  # Schivardi – PT trotskiste → EXG
    (
        "VILL",
        2007,
        "DTE",
    ),  # de Villiers – MPF (nuance DVDR) → DTE ; CE 31/01/2020 n°437675 conforte DTE
    ("VOYN", 2007, "GAU"),  # Voynet – Verts (nuance DVGV) → GAU
    # ── 2012 (10 candidats) ────────────────────────────────────────────────
    ("ARTH", 2012, "EXG"),  # Arthaud – LO → EXG
    ("BAYR", 2012, "CENT"),  # Bayrou – MoDem → CENT
    ("CHEM", 2012, "DIV"),  # Cheminade – Solidarité et Progrès → DIV
    ("DUPO", 2012, "DTE"),  # Dupont-Aignan – DLR (nuance DVDR) → DTE ; CE 31/01/2020 n°437675
    ("HOLL", 2012, "GAU"),  # Hollande – PS → GAU
    ("JOLY", 2012, "GAU"),  # Joly – EELV (nuance DVGV) → GAU ; pas de bloc écolo officiel
    ("LEPE", 2012, "EXD"),  # Le Pen Marine – FN → EXD
    (
        "MELE",
        2012,
        "GAU",
    ),  # Mélenchon – Front de Gauche → GAU ; LFI bascule EXG en 2026 (INTP2602966C) seulement
    ("POUT", 2012, "EXG"),  # Poutou – NPA (héritage LCR) → EXG
    ("SARK", 2012, "DTE"),  # Sarkozy – UMP → DTE
]

# ── Candidats présidentiels 2017 / 2022 ──────────────────────────────────────
# La colonne 'nuance' est NULL pour ces scrutins dans le Parquet.
# Le classement se fait via le nom de famille EXACT tel qu'il apparaît dans le
# Parquet (vérifié par requête DISTINCT sur general-results.parquet).
# Blocs officiels Ministère et "classement de l'époque" (ADR-0005).
# (annee, nom_parquet, prenom, parti, bloc, libelle, source_bloc)
#
_CANDIDATS_PRES_2017: list[tuple[int, str, str, str, str, str, str]] = [
    # (annee, nom_parquet, prenom, parti, bloc, libelle, source_bloc)
    (
        2017,
        "ARTHAUD",
        "Nathalie",
        "Lutte Ouvrière",
        "EXG",
        "Nathalie Arthaud",
        "Logique officielle EXG — LO",
    ),
    (
        2017,
        "ASSELINEAU",
        "François",
        "Union Populaire Républicaine",
        "DIV",
        "François Asselineau",
        "Logique officielle DIV — souverainiste inclassable",
    ),
    (
        2017,
        "CHEMINADE",
        "Jacques",
        "Solidarité et Progrès",
        "DIV",
        "Jacques Cheminade",
        "Logique officielle DIV",
    ),
    (
        2017,
        "DUPONT-AIGNAN",
        "Nicolas",
        "Debout la France",
        "DTE",
        "Nicolas Dupont-Aignan",
        "Nuance DVDR — CE 31/01/2020 n°437675 conforte DTE",
    ),
    (
        2017,
        "FILLON",
        "François",
        "Les Républicains",
        "DTE",
        "François Fillon",
        "LR — nuance LR → DTE",
    ),
    (2017, "HAMON", "Benoît", "Parti Socialiste", "GAU", "Benoît Hamon", "PS — nuance PS → GAU"),
    (
        2017,
        "LASSALLE",
        "Jean",
        "Résistons!",
        "DIV",
        "Jean Lassalle",
        "Logique officielle DIV — mouvement régionaliste",
    ),
    (
        2017,
        "LE PEN",
        "Marine",
        "FN",
        "EXD",
        "Marine Le Pen",
        "FN → EXD — CE 21/09/2023 n°488379, CE 11/03/2024 n°488378 (rebranding RN en juin 2018, après le scrutin)",
    ),
    (2017, "MACRON", "Emmanuel", "En Marche", "CENT", "Emmanuel Macron", "LREM → CENT"),
    (
        2017,
        "MÉLENCHON",
        "Jean-Luc",
        "La France Insoumise",
        "GAU",
        "Jean-Luc Mélenchon",
        "LFI → GAU en 2017 (IOMA2322276J 2023 confirme) — bascule EXG en 2026 seulement (INTP2602966C)",
    ),
    (
        2017,
        "POUTOU",
        "Philippe",
        "Nouveau Parti Anticapitaliste",
        "EXG",
        "Philippe Poutou",
        "NPA → EXG — logique officielle",
    ),
]

_CANDIDATS_PRES_2022: list[tuple[int, str, str, str, str, str, str]] = [
    # (annee, nom_parquet, prenom, parti, bloc, libelle, source_bloc)
    (
        2022,
        "ARTHAUD",
        "Nathalie",
        "Lutte Ouvrière",
        "EXG",
        "Nathalie Arthaud",
        "Logique officielle EXG — LO",
    ),
    (
        2022,
        "DUPONT-AIGNAN",
        "Nicolas",
        "Debout la France",
        "DTE",
        "Nicolas Dupont-Aignan",
        "Nuance DVDR — CE 31/01/2020 n°437675 conforte DTE",
    ),
    (2022, "HIDALGO", "Anne", "Parti Socialiste", "GAU", "Anne Hidalgo", "PS — nuance PS → GAU"),
    (
        2022,
        "JADOT",
        "Yannick",
        "EELV",
        "GAU",
        "Yannick Jadot",
        "EELV, nuance ECO (INTA2212053C 2022) ; classement GAU selon logique officielle Ministère post-2023 (blocs inexistants en 2022)",
    ),
    (2022, "LASSALLE", "Jean", "Résistons!", "DIV", "Jean Lassalle", "Logique officielle DIV"),
    (
        2022,
        "LE PEN",
        "Marine",
        "Rassemblement National",
        "EXD",
        "Marine Le Pen",
        "RN → EXD — CE 21/09/2023 n°488379, CE 11/03/2024 n°488378",
    ),
    (
        2022,
        "MACRON",
        "Emmanuel",
        "La République En Marche / Renaissance",
        "CENT",
        "Emmanuel Macron",
        "LREM → CENT",
    ),
    (
        2022,
        "MÉLENCHON",
        "Jean-Luc",
        "La France Insoumise / NUPES",
        "GAU",
        "Jean-Luc Mélenchon",
        "LFI → GAU en 2022 (IOMA2322276J 2023 confirme) — bascule EXG en 2026 seulement (INTP2602966C)",
    ),
    (
        2022,
        "POUTOU",
        "Philippe",
        "Nouveau Parti Anticapitaliste",
        "EXG",
        "Philippe Poutou",
        "NPA → EXG — logique officielle",
    ),
    (2022, "PÉCRESSE", "Valérie", "Les Républicains", "DTE", "Valérie Pécresse", "LR → DTE"),
    (
        2022,
        "ROUSSEL",
        "Fabien",
        "Parti Communiste Français",
        "GAU",
        "Fabien Roussel",
        "PCF → GAU dans logique officielle Ministère",
    ),
    (
        2022,
        "ZEMMOUR",
        "Éric",
        "Reconquête",
        "EXD",
        "Éric Zemmour",
        "Reconquête, nuance REC (INTA2212053C 2022) ; bloc EXD selon logique officielle IOMA2322276J (2023)",
    ),
]


# ── Création du schéma ────────────────────────────────────────────────────────


def create_elections_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 6 tables électorales. Idempotent (CREATE TABLE IF NOT EXISTS)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS elections (
            id_election  VARCHAR PRIMARY KEY,
            type_scrutin VARCHAR NOT NULL,
            annee        INTEGER NOT NULL,
            tour         INTEGER NOT NULL,
            libelle      VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS resultats_participation (
            id_election      VARCHAR NOT NULL,
            code_departement VARCHAR NOT NULL,
            code_commune     VARCHAR NOT NULL,
            code_bv          VARCHAR NOT NULL,
            inscrits         INTEGER,
            abstentions      INTEGER,
            votants          INTEGER,
            blancs           INTEGER,
            nuls             INTEGER,
            exprimes         INTEGER,
            PRIMARY KEY (id_election, code_departement, code_commune, code_bv)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS resultats_candidats (
            id_election      VARCHAR NOT NULL,
            code_departement VARCHAR NOT NULL,
            code_commune     VARCHAR NOT NULL,
            code_bv          VARCHAR NOT NULL,
            no_panneau       INTEGER NOT NULL,
            nuance           VARCHAR,
            sexe             VARCHAR,
            nom              VARCHAR,
            prenom           VARCHAR,
            voix             INTEGER,
            PRIMARY KEY (id_election, code_departement, code_commune, code_bv, no_panneau)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS blocs_politiques (
            bloc    VARCHAR PRIMARY KEY,
            libelle VARCHAR NOT NULL,
            couleur VARCHAR NOT NULL,
            ordre   INTEGER NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS nuances_harmonisees (
            nuance VARCHAR NOT NULL,
            annee  INTEGER NOT NULL,
            bloc   VARCHAR NOT NULL,
            PRIMARY KEY (nuance, annee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS candidats_presidentielle (
            annee        INTEGER NOT NULL,
            nom          VARCHAR NOT NULL,
            prenom       VARCHAR,
            parti        VARCHAR,
            bloc         VARCHAR NOT NULL,
            libelle      VARCHAR,
            source_bloc  VARCHAR,
            PRIMARY KEY (annee, nom)
        )
    """)
    # Migration C2a-bis : ajout des colonnes parti et source_bloc si absentes
    # (nécessaire si la table existait déjà avec l'ancien schéma à 5 colonnes)
    con.execute("ALTER TABLE candidats_presidentielle ADD COLUMN IF NOT EXISTS parti VARCHAR")
    con.execute("ALTER TABLE candidats_presidentielle ADD COLUMN IF NOT EXISTS source_bloc VARCHAR")

    logger.info("Schéma électoral créé/vérifié : 6 tables")


# ── Population des référentiels ───────────────────────────────────────────────


def populate_elections_referentiels(con: duckdb.DuckDBPyConnection) -> None:
    """Remplit les 4 tables de référence. Idempotent (DELETE + INSERT).

    Ne touche pas resultats_participation ni resultats_candidats.
    Ordre de suppression respecté pour les FK déclaratives (blocs en dernier).
    """
    # Supprimer dans l'ordre FK (enfants avant parents)
    con.execute("DELETE FROM candidats_presidentielle")
    con.execute("DELETE FROM nuances_harmonisees")
    con.execute("DELETE FROM elections")
    con.execute("DELETE FROM blocs_politiques")

    # blocs_politiques (parent des FK nuances et candidats)
    con.executemany("INSERT INTO blocs_politiques VALUES (?, ?, ?, ?)", _BLOCS)
    logger.info("blocs_politiques : %d blocs", len(_BLOCS))

    # elections (56 scrutins 1999-2026)
    con.executemany("INSERT INTO elections VALUES (?, ?, ?, ?, ?)", _ELECTIONS)
    logger.info("elections : %d scrutins", len(_ELECTIONS))

    # nuances_harmonisees (présidentielles avec nuances : 2002, 2007, 2012)
    if _NUANCES_PRES:
        con.executemany("INSERT INTO nuances_harmonisees VALUES (?, ?, ?)", _NUANCES_PRES)
    logger.info("nuances_harmonisees : %d entrées (pres 2002/2007/2012)", len(_NUANCES_PRES))

    # candidats_presidentielle (présidentielles sans nuances : 2017, 2022)
    candidats = _CANDIDATS_PRES_2017 + _CANDIDATS_PRES_2022
    if candidats:
        con.executemany(
            """INSERT INTO candidats_presidentielle
               (annee, nom, prenom, parti, bloc, libelle, source_bloc)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            candidats,
        )
    logger.info("candidats_presidentielle : %d candidats (2017 + 2022)", len(candidats))
