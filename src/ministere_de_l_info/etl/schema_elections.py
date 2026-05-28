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
Le classement de chaque candidat/nuance dans un bloc est un CHOIX ÉDITORIAL.
Les cas ambigus sont marqués « [ambigu] » en commentaire et documentés dans
docs/schema-elections.md. Ne pas modifier sans mettre à jour l'ADR correspondant.
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
# (bloc, libelle, couleur_hex, ordre_gauche_droite)
# Couleurs indicatives ; à affiner lors de la conception de la viz.

_BLOCS: list[tuple[str, str, str, int]] = [
    ("extreme_gauche", "Extrême gauche", "#8B0000", 1),
    ("gauche", "Gauche", "#E63946", 2),
    ("ecologistes", "Écologistes", "#4CAF50", 3),
    ("centre", "Centre", "#FFD700", 4),
    ("droite", "Droite", "#2196F3", 5),
    ("extreme_droite", "Extrême droite", "#1A237E", 6),
    ("divers", "Divers / Autres", "#9E9E9E", 99),
]

# ── Nuances → blocs, présidentielles 2002 / 2007 / 2012 ──────────────────────
# Pour ces scrutins, la colonne 'nuance' du Parquet est un code-candidat
# (CHIR = Chirac, JOSP = Jospin, etc.), contrairement aux scrutins de liste
# qui utilisent des codes partisans (RN, SOC, LDVG, …).
# (nuance, annee, bloc)

_NUANCES_PRES: list[tuple[str, int, str]] = [
    # ── 2002 (16 candidats) ────────────────────────────────────────────────
    ("BAYR", 2002, "centre"),  # Bayrou – UDF
    ("BESA", 2002, "extreme_gauche"),  # Besancenot – LCR
    ("BOUT", 2002, "droite"),  # Boutin – FRS (conservatisme chrétien)
    ("CHEV", 2002, "gauche"),  # Chevènement – MDC
    ("CHIR", 2002, "droite"),  # Chirac – RPR
    ("GLUC", 2002, "extreme_gauche"),  # Gluckstein – PT (trotskiste)
    ("HUE", 2002, "gauche"),  # Hue – PCF
    ("JOSP", 2002, "gauche"),  # Jospin – PS
    ("LAGU", 2002, "extreme_gauche"),  # Laguiller – LO
    ("LEPA", 2002, "ecologistes"),  # Lepage – Cap21 [ambigu : centre ou écolo]
    ("LEPE", 2002, "extreme_droite"),  # Le Pen – FN
    ("MADE", 2002, "droite"),  # Madelin – DL (libéral)
    ("MAME", 2002, "ecologistes"),  # Mamère – Verts
    ("MEGR", 2002, "extreme_droite"),  # Mégret – MNR (scissionniste FN)
    ("SAIN", 2002, "divers"),  # Saint-Josse – CPNT
    ("TAUB", 2002, "gauche"),  # Taubira – PRG
    # ── 2007 (12 candidats) ────────────────────────────────────────────────
    ("BAYR", 2007, "centre"),  # Bayrou – MoDem
    ("BESA", 2007, "extreme_gauche"),  # Besancenot – LCR
    ("BOVE", 2007, "gauche"),  # Bové – altermondialiste [ambigu : extrême gauche]
    ("BUFF", 2007, "gauche"),  # Buffet – PCF
    ("LAGU", 2007, "extreme_gauche"),  # Laguiller – LO
    ("LEPE", 2007, "extreme_droite"),  # Le Pen – FN
    ("NIHO", 2007, "divers"),  # Nihous – CPNT
    ("ROYA", 2007, "gauche"),  # Royal – PS
    ("SARK", 2007, "droite"),  # Sarkozy – UMP
    ("SCHI", 2007, "extreme_gauche"),  # Schivardi – PT (trotskiste, successeur Gluckstein)
    ("VILL", 2007, "droite"),  # Villiers – MPF [ambigu : extrême droite]
    ("VOYN", 2007, "ecologistes"),  # Voynet – Verts
    # ── 2012 (10 candidats) ────────────────────────────────────────────────
    ("ARTH", 2012, "extreme_gauche"),  # Arthaud – LO
    ("BAYR", 2012, "centre"),  # Bayrou – MoDem
    ("CHEM", 2012, "divers"),  # Cheminade – Solidarité et Progrès
    ("DUPO", 2012, "droite"),  # Dupont-Aignan – DLR [ambigu : extrême droite]
    ("HOLL", 2012, "gauche"),  # Hollande – PS
    ("JOLY", 2012, "ecologistes"),  # Joly – EELV
    ("LEPE", 2012, "extreme_droite"),  # Le Pen Marine – FN
    ("MELE", 2012, "gauche"),  # Mélenchon – Front de Gauche [ambigu : extrême gauche]
    ("POUT", 2012, "extreme_gauche"),  # Poutou – NPA
    ("SARK", 2012, "droite"),  # Sarkozy – UMP
]

# ── Candidats présidentiels 2017 / 2022 ──────────────────────────────────────
# La colonne 'nuance' est NULL pour ces scrutins dans le Parquet.
# Le classement se fait via le nom de famille EXACT tel qu'il apparaît dans le
# Parquet (vérifié par requête DISTINCT sur general-results.parquet).
# (annee, nom_parquet, prenom, bloc, libelle)

_CANDIDATS_PRES_2017: list[tuple[int, str, str, str, str]] = [
    (2017, "ARTHAUD", "Nathalie", "extreme_gauche", "Nathalie Arthaud"),
    (
        2017,
        "ASSELINEAU",
        "François",
        "divers",
        "François Asselineau",
    ),  # UPR, souverainiste inclassable
    (2017, "CHEMINADE", "Jacques", "divers", "Jacques Cheminade"),
    (
        2017,
        "DUPONT-AIGNAN",
        "Nicolas",
        "droite",
        "Nicolas Dupont-Aignan",
    ),  # [ambigu : extrême droite]
    (2017, "FILLON", "François", "droite", "François Fillon"),
    (2017, "HAMON", "Benoît", "gauche", "Benoît Hamon"),
    (2017, "LASSALLE", "Jean", "divers", "Jean Lassalle"),
    (2017, "LE PEN", "Marine", "extreme_droite", "Marine Le Pen"),
    (2017, "MACRON", "Emmanuel", "centre", "Emmanuel Macron"),
    (2017, "MÉLENCHON", "Jean-Luc", "gauche", "Jean-Luc Mélenchon"),  # [ambigu : extrême gauche]
    (2017, "POUTOU", "Philippe", "extreme_gauche", "Philippe Poutou"),
]

_CANDIDATS_PRES_2022: list[tuple[int, str, str, str, str]] = [
    (2022, "ARTHAUD", "Nathalie", "extreme_gauche", "Nathalie Arthaud"),
    (
        2022,
        "DUPONT-AIGNAN",
        "Nicolas",
        "droite",
        "Nicolas Dupont-Aignan",
    ),  # [ambigu : extrême droite]
    (2022, "HIDALGO", "Anne", "gauche", "Anne Hidalgo"),
    (2022, "JADOT", "Yannick", "ecologistes", "Yannick Jadot"),
    (2022, "LASSALLE", "Jean", "divers", "Jean Lassalle"),
    (2022, "LE PEN", "Marine", "extreme_droite", "Marine Le Pen"),
    (2022, "MACRON", "Emmanuel", "centre", "Emmanuel Macron"),
    (2022, "MÉLENCHON", "Jean-Luc", "gauche", "Jean-Luc Mélenchon"),  # [ambigu : extrême gauche]
    (2022, "POUTOU", "Philippe", "extreme_gauche", "Philippe Poutou"),
    (2022, "PÉCRESSE", "Valérie", "droite", "Valérie Pécresse"),
    (2022, "ROUSSEL", "Fabien", "gauche", "Fabien Roussel"),  # PCF [ambigu : extrême gauche]
    (2022, "ZEMMOUR", "Éric", "extreme_droite", "Éric Zemmour"),
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
            annee   INTEGER NOT NULL,
            nom     VARCHAR NOT NULL,
            prenom  VARCHAR,
            bloc    VARCHAR NOT NULL,
            libelle VARCHAR,
            PRIMARY KEY (annee, nom)
        )
    """)

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
    con.executemany("INSERT INTO nuances_harmonisees VALUES (?, ?, ?)", _NUANCES_PRES)
    logger.info("nuances_harmonisees : %d entrées (pres 2002/2007/2012)", len(_NUANCES_PRES))

    # candidats_presidentielle (présidentielles sans nuances : 2017, 2022)
    candidats = _CANDIDATS_PRES_2017 + _CANDIDATS_PRES_2022
    con.executemany("INSERT INTO candidats_presidentielle VALUES (?, ?, ?, ?, ?)", candidats)
    logger.info("candidats_presidentielle : %d candidats (2017 + 2022)", len(candidats))
