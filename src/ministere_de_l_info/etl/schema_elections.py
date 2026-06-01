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


def _build_elections() -> list[tuple[str, str, int, int, str, bool]]:
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
    result: list[tuple[str, str, int, int, str, bool]] = []
    for typ, annee, tour in raw:
        id_el = f"{annee}_{typ}_t{tour}"
        tour_str = "1er tour" if tour == 1 else "2e tour"
        libelle = f"{_TYPE_LIBELLE[typ]} {annee} — {tour_str}"
        # Scrutins législatifs antérieurs au redécoupage Marleix (applicable dès 2012)
        ancien_decoupage = typ == "legi" and annee in (2002, 2007)
        result.append((id_el, typ, annee, tour, libelle, ancien_decoupage))
    return result


_ELECTIONS: list[tuple[str, str, int, int, str, bool]] = _build_elections()

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

# ── Circo 21 Nord (Valenciennes) — 20 communes ───────────────────────────────
# Codes INSEE validés par jointure spatiale ST_Within sur geographies_circonscriptions
# (code = '59-21'). Source : IGN ADMIN-EXPRESS-COG, millésime 2025.

_CIRCO21_CODES: tuple[str, ...] = (
    "59027",  # Aubry-du-Hainaut
    "59064",  # Bellaing
    "59153",  # Condé-sur-l'Escaut
    "59160",  # Crespin
    "59166",  # Curgies
    "59215",  # Estreux
    "59383",  # Marly
    "59447",  # Onnaing
    "59459",  # Petite-Forêt
    "59471",  # Préseau
    "59479",  # Quarouble
    "59484",  # Quiévrechain
    "59505",  # Rombies-et-Marchipont
    "59530",  # Saint-Aybert
    "59544",  # Saint-Saulve
    "59557",  # Saultain
    "59559",  # Sebourg
    "59591",  # Thivencelle
    "59606",  # Valenciennes
    "59632",  # Wallers
)

# ── Nuances → blocs, présidentielles 2002 / 2007 / 2012 ──────────────────────
# Pour ces scrutins, la colonne 'nuance' du Parquet est un code-candidat
# (CHIR = Chirac, JOSP = Jospin, etc.), contrairement aux scrutins de liste
# qui utilisent des codes partisans (RN, SOC, LDVG, …).
# Blocs officiels Ministère (reconstruction ante-2023 selon ADR-0005).
# (nuance, annee, bloc, source_bloc) — source_bloc = justification courte (1 ligne).
#
_NUANCES_PRES: list[tuple[str, int, str, str]] = [
    # ── 2002 (16 candidats) ────────────────────────────────────────────────
    ("BAYR", 2002, "CENT", "Bayrou – UDF → CENT"),
    ("BESA", 2002, "EXG", "Besancenot – LCR trotskiste → EXG"),
    (
        "BOUT",
        2002,
        "DTE",
        "Boutin – FRS conservateur chrétien → DTE (cohérence nomenclature Ministère)",
    ),
    ("CHEV", 2002, "GAU", "Chevènement – MDC (ex-PS) → GAU"),
    ("CHIR", 2002, "DTE", "Chirac – RPR gaulliste → DTE"),
    ("GLUC", 2002, "EXG", "Gluckstein – PT trotskiste → EXG"),
    ("HUE", 2002, "GAU", "Hue – PCF → GAU (logique officielle Ministère, pas EXG)"),
    ("JOSP", 2002, "GAU", "Jospin – PS → GAU"),
    ("LAGU", 2002, "EXG", "Laguiller – LO → EXG"),
    (
        "LEPA",
        2002,
        "CENT",
        "Lepage – Cap21 (écologie libérale) → CENT ; pas de bloc écolo officiel",
    ),
    ("LEPE", 2002, "EXD", "Le Pen J.-M. – FN → EXD"),
    ("MADE", 2002, "DTE", "Madelin – DL (libéral-conservateur) → DTE"),
    ("MAME", 2002, "GAU", "Mamère – Verts (DVGV) → GAU"),
    ("MEGR", 2002, "EXD", "Mégret – MNR (scission FN) → EXD"),
    ("SAIN", 2002, "DIV", "Saint-Josse – CPNT → DIV"),
    ("TAUB", 2002, "GAU", "Taubira – PRG (allié PS) → GAU"),
    # ── 2007 (12 candidats) ────────────────────────────────────────────────
    ("BAYR", 2007, "CENT", "Bayrou – MoDem → CENT"),
    ("BESA", 2007, "EXG", "Besancenot – LCR → EXG"),
    ("BOVE", 2007, "GAU", "Bové – altermondialiste/soutien Verts (DVGV) → GAU"),
    ("BUFF", 2007, "GAU", "Buffet – PCF → GAU"),
    ("LAGU", 2007, "EXG", "Laguiller – LO → EXG"),
    ("LEPE", 2007, "EXD", "Le Pen J.-M. – FN → EXD"),
    ("NIHO", 2007, "DIV", "Nihous – CPNT → DIV"),
    ("ROYA", 2007, "GAU", "Royal – PS → GAU"),
    ("SARK", 2007, "DTE", "Sarkozy – UMP → DTE"),
    ("SCHI", 2007, "EXG", "Schivardi – PT trotskiste → EXG"),
    ("VILL", 2007, "DTE", "de Villiers – MPF (DVDR) → DTE (CE 31/01/2020 n°437675)"),
    ("VOYN", 2007, "GAU", "Voynet – Verts (DVGV) → GAU"),
    # ── 2012 (10 candidats) ────────────────────────────────────────────────
    ("ARTH", 2012, "EXG", "Arthaud – LO → EXG"),
    ("BAYR", 2012, "CENT", "Bayrou – MoDem → CENT"),
    ("CHEM", 2012, "DIV", "Cheminade – Solidarité et Progrès → DIV"),
    ("DUPO", 2012, "DTE", "Dupont-Aignan – DLR (DVDR) → DTE (CE 31/01/2020 n°437675)"),
    ("HOLL", 2012, "GAU", "Hollande – PS → GAU"),
    ("JOLY", 2012, "GAU", "Joly – EELV (DVGV) → GAU ; pas de bloc écolo officiel"),
    ("LEPE", 2012, "EXD", "Le Pen Marine – FN → EXD"),
    (
        "MELE",
        2012,
        "GAU",
        "Mélenchon – Front de Gauche → GAU ; LFI bascule EXG en 2026 (INTP2602966C)",
    ),
    ("POUT", 2012, "EXG", "Poutou – NPA (héritage LCR) → EXG"),
    ("SARK", 2012, "DTE", "Sarkozy – UMP → DTE"),
]

# ── Nuances → blocs, législatives 2002/2007/2012/2017/2022/2024 ──────────────
# 111 entrées (nuance, annee) validées par Mathias le 2026-06-01.
# Classement "officiel de l'époque" (ADR-0005) ; circulaires 2002-2017 non publiées
# au JO (documents internes) → reconstruction sourcée ; 2022 = INTA2212053C ;
# 2024 = IOMA2415630C. Détail et justification : reports/mapping-nuances-legislatives-validated.md
# Format : (nuance, annee, bloc, source_bloc)
_NUANCES_LEGI: list[tuple[str, int, str, str]] = [
    # ── 2002 (22 nuances) ──────────────────────────────────────────────────
    ("COM", 2002, "GAU", "PCF → GAU (logique officielle Ministère, pas EXG)"),
    ("CPNT", 2002, "DIV", "Chasse Pêche Nature Tradition → DIV"),
    ("DIV", 2002, "DIV", "Divers → mapping direct"),
    ("DL", 2002, "DTE", "Démocratie Libérale (Madelin) libéral-conservateur → DTE"),
    ("DVD", 2002, "DTE", "Divers Droite → mapping direct"),
    ("DVG", 2002, "GAU", "Divers Gauche → mapping direct"),
    ("ECO", 2002, "GAU", "Écologistes/Verts → GAU (pas de bloc écolo officiel, ADR-0005)"),
    ("EXD", 2002, "EXD", "Extrême droite → code = bloc"),
    ("EXG", 2002, "EXG", "Extrême gauche → code = bloc"),
    ("FN", 2002, "EXD", "Front National → EXD"),
    ("LCR", 2002, "EXG", "Ligue Communiste Révolutionnaire (trotskiste) → EXG"),
    ("LO", 2002, "EXG", "Lutte Ouvrière → EXG"),
    ("MNR", 2002, "EXD", "MNR (Mégret, scission FN) → EXD"),
    (
        "MPF",
        2002,
        "DTE",
        "MPF (Villiers) souverainiste conservateur → DTE (CE 31/01/2020 n°437675)",
    ),
    (
        "PREP",
        2002,
        "GAU",
        "Pôle Républicain (Chevènement, souverainiste de gauche) → GAU par cohérence DVG/MDC",
    ),
    ("PRG", 2002, "GAU", "Parti Radical de Gauche (allié PS) → GAU"),
    ("REG", 2002, "DIV", "Régionalistes → DIV"),
    ("RPF", 2002, "DTE", "RPF (Pasqua) souverainiste conservateur → DTE (même logique que MPF)"),
    ("SOC", 2002, "GAU", "Parti Socialiste → GAU"),
    ("UDF", 2002, "CENT", "UDF (Bayrou-Giscard) → CENT"),
    ("UMP", 2002, "DTE", "UMP (Chirac) → DTE"),
    ("VEC", 2002, "GAU", "Les Verts → GAU (idem ECO)"),
    # ── 2007 (17 nuances) ──────────────────────────────────────────────────
    ("COM", 2007, "GAU", "PCF → GAU"),
    ("CPNT", 2007, "DIV", "Chasse Pêche Nature Tradition → DIV"),
    ("DIV", 2007, "DIV", "Divers → mapping direct"),
    ("DVD", 2007, "DTE", "Divers Droite → DTE"),
    ("DVG", 2007, "GAU", "Divers Gauche → GAU"),
    ("ECO", 2007, "GAU", "Écologistes → GAU (ADR-0005)"),
    ("EXD", 2007, "EXD", "Extrême droite → code = bloc"),
    ("EXG", 2007, "EXG", "Extrême gauche → code = bloc"),
    ("FN", 2007, "EXD", "Front National → EXD"),
    ("MAJ", 2007, "DTE", "Majorité présidentielle (UMP-alliés Sarkozy 2007) → DTE"),
    ("MPF", 2007, "DTE", "MPF (Villiers) → DTE"),
    ("RDG", 2007, "GAU", "Radical de Gauche (allié PS) → GAU"),
    ("REG", 2007, "DIV", "Régionalistes → DIV"),
    ("SOC", 2007, "GAU", "Parti Socialiste → GAU"),
    ("UDFD", 2007, "CENT", "UDF Démocrate (rump post-MoDem 2007) tradition centriste → CENT"),
    ("UMP", 2007, "DTE", "UMP (Sarkozy) → DTE"),
    ("VEC", 2007, "GAU", "Les Verts → GAU"),
    # ── 2012 (17 nuances) ──────────────────────────────────────────────────
    ("ALLI", 2012, "CENT", "Alliance Centriste (Arthuis), précurseur UDI → CENT"),
    ("AUT", 2012, "DIV", "Autres → divers inclassables, DIV"),
    ("CEN", 2012, "CENT", "Centre → code centriste, CENT"),
    ("DVD", 2012, "DTE", "Divers Droite → DTE"),
    ("DVG", 2012, "GAU", "Divers Gauche → GAU"),
    ("ECO", 2012, "GAU", "Écologistes (EELV) → GAU"),
    ("EXD", 2012, "EXD", "Extrême droite → code = bloc"),
    ("EXG", 2012, "EXG", "Extrême gauche → code = bloc"),
    ("FG", 2012, "GAU", "Front de Gauche (PCF+PG) → GAU ; LFI bascule EXG en 2026 (INTP2602966C)"),
    ("FN", 2012, "EXD", "Front National → EXD"),
    ("NCE", 2012, "CENT", "Nouveau Centre (Borloo, allié UMP) → CENT"),
    ("PRV", 2012, "DTE", "Parti Radical Valoisien (allié UMP) → DTE"),
    ("RDG", 2012, "GAU", "Radical de Gauche (allié PS) → GAU"),
    ("REG", 2012, "DIV", "Régionalistes → DIV"),
    ("SOC", 2012, "GAU", "Parti Socialiste → GAU"),
    ("UMP", 2012, "DTE", "UMP (Sarkozy → Fillon) → DTE"),
    ("VEC", 2012, "GAU", "Les Verts/EELV → GAU"),
    # ── 2017 (17 nuances) ──────────────────────────────────────────────────
    ("COM", 2017, "GAU", "PCF → GAU"),
    ("DIV", 2017, "DIV", "Divers → mapping direct"),
    ("DLF", 2017, "DTE", "Debout la France (Dupont-Aignan) → DTE (CE 31/01/2020 n°437675)"),
    ("DVD", 2017, "DTE", "Divers Droite → DTE"),
    ("DVG", 2017, "GAU", "Divers Gauche → GAU"),
    ("ECO", 2017, "GAU", "Écologistes (EELV) → GAU"),
    ("EXD", 2017, "EXD", "Extrême droite → code = bloc"),
    ("EXG", 2017, "EXG", "Extrême gauche → code = bloc"),
    (
        "FI",
        2017,
        "GAU",
        "La France Insoumise → GAU en 2017 (IOMA2322276J 2023 confirme) ; EXG en 2026 (INTP2602966C)",
    ),
    ("FN", 2017, "EXD", "Front National → EXD (RN en 2018, après le scrutin)"),
    ("LR", 2017, "DTE", "Les Républicains → DTE"),
    ("MDM", 2017, "CENT", "MoDem (Bayrou) → CENT"),
    ("RDG", 2017, "GAU", "Radical de Gauche → GAU"),
    ("REG", 2017, "DIV", "Régionalistes → DIV"),
    ("REM", 2017, "CENT", "La République En Marche (Macron) → CENT"),
    ("SOC", 2017, "GAU", "Parti Socialiste → GAU"),
    ("UDI", 2017, "CENT", "Union des Démocrates Indépendants → CENT"),
    # ── 2022 (16 nuances) — source INTA2212053C ────────────────────────────
    ("DIV", 2022, "DIV", "Divers → mapping direct"),
    ("DSV", 2022, "DTE", "Divers Souverainiste → DTE (souverainistes non-EXD, logique CE DLF)"),
    ("DVC", 2022, "CENT", "Divers Centre → mapping direct"),
    ("DVD", 2022, "DTE", "Divers Droite → DTE"),
    ("DVG", 2022, "GAU", "Divers Gauche → GAU"),
    ("DXD", 2022, "EXD", "Divers Extrême Droite → code explicite"),
    ("DXG", 2022, "EXG", "Divers Extrême Gauche → code explicite"),
    ("ECO", 2022, "GAU", "Écologistes (EELV, INTA2212053C) → GAU"),
    ("ENS", 2022, "CENT", "Ensemble! (LREM+MoDem+Horizons) → CENT"),
    ("LR", 2022, "DTE", "Les Républicains → DTE"),
    ("NUP", 2022, "GAU", "NUPES (LFI+PS+PCF+EELV) → GAU ; LFI bascule EXG en 2026 (INTP2602966C)"),
    ("RDG", 2022, "GAU", "Radical de Gauche → GAU"),
    ("REC", 2022, "EXD", "Reconquête (Zemmour, INTA2212053C) → EXD"),
    ("REG", 2022, "DIV", "Régionalistes → DIV"),
    ("RN", 2022, "EXD", "Rassemblement National → EXD (CE 21/09/2023 n°488379)"),
    ("UDI", 2022, "CENT", "UDI → CENT"),
    # ── 2024 (22 nuances) — source IOMA2415630C ────────────────────────────
    ("COM", 2024, "GAU", "PCF standalone (hors NFP) → GAU"),
    ("DIV", 2024, "DIV", "Divers → mapping direct"),
    ("DSV", 2024, "DTE", "Divers Souverainiste → DTE (IOMA2415630C : souverainistes ≠ EXD)"),
    ("DVC", 2024, "CENT", "Divers Centre → CENT"),
    ("DVD", 2024, "DTE", "Divers Droite → DTE"),
    ("DVG", 2024, "GAU", "Divers Gauche → GAU"),
    ("ECO", 2024, "GAU", "Écologistes → GAU"),
    ("ENS", 2024, "CENT", "Ensemble (Macron) → CENT"),
    ("EXD", 2024, "EXD", "Extrême droite → code = bloc"),
    (
        "EXG",
        2024,
        "EXG",
        "Extrême gauche (LO+NPA+POI, sans LFI) → IOMA2415630C confirme, code = bloc",
    ),
    (
        "FI",
        2024,
        "GAU",
        "LFI standalone hors NFP → GAU (IOMA2415630C : FI distincte d'EXG) ; EXG en 2026",
    ),
    ("HOR", 2024, "CENT", "Horizons (Philippe, allié Ensemble) → CENT"),
    ("LR", 2024, "DTE", "Les Républicains (hors accord Macron) → DTE"),
    ("RDG", 2024, "GAU", "Radical de Gauche → GAU"),
    ("REC", 2024, "EXD", "Reconquête → EXD"),
    ("REG", 2024, "DIV", "Régionalistes → DIV"),
    ("RN", 2024, "EXD", "Rassemblement National → EXD"),
    ("SOC", 2024, "GAU", "PS standalone (hors NFP) → GAU"),
    ("UDI", 2024, "CENT", "UDI → CENT"),
    (
        "UG",
        2024,
        "GAU",
        "NFP/Union de la Gauche (PS+PCF+EELV+LFI) → GAU (IOMA2415630C définit UG = Union de la gauche)",
    ),
    ("UXD", 2024, "EXD", "Union d'extrême droite (RN+alliés 2024) → EXD"),
    ("VEC", 2024, "GAU", "Verts standalone (hors NFP) → GAU"),
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
            id_election      VARCHAR PRIMARY KEY,
            type_scrutin     VARCHAR NOT NULL,
            annee            INTEGER NOT NULL,
            tour             INTEGER NOT NULL,
            libelle          VARCHAR NOT NULL,
            ancien_decoupage BOOLEAN DEFAULT FALSE
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

    # Migration D1.2 : nouvelles colonnes pour les scrutins législatifs
    con.execute(
        "ALTER TABLE elections ADD COLUMN IF NOT EXISTS ancien_decoupage BOOLEAN DEFAULT FALSE"
    )
    con.execute("ALTER TABLE resultats_participation ADD COLUMN IF NOT EXISTS code_circo VARCHAR")
    # Migration D1.2 : justification courte du bloc, sur le modèle de candidats_presidentielle
    con.execute("ALTER TABLE nuances_harmonisees ADD COLUMN IF NOT EXISTS source_bloc VARCHAR")

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
    con.executemany("INSERT INTO elections VALUES (?, ?, ?, ?, ?, ?)", _ELECTIONS)
    logger.info("elections : %d scrutins", len(_ELECTIONS))

    # nuances_harmonisees : présidentielles (2002/2007/2012) + législatives
    # (2002/2007/2012/2017/2022/2024). Chaque entrée porte sa justification (source_bloc).
    nuances = _NUANCES_PRES + _NUANCES_LEGI
    if nuances:
        con.executemany(
            "INSERT INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) VALUES (?, ?, ?, ?)",
            nuances,
        )
    logger.info(
        "nuances_harmonisees : %d entrées (%d pres + %d legi)",
        len(nuances),
        len(_NUANCES_PRES),
        len(_NUANCES_LEGI),
    )

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


# ── Vues d'agrégation ─────────────────────────────────────────────────────────


def create_elections_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 5 vues d'agrégation électorales. Idempotent (CREATE OR REPLACE).

    Résolution du bloc politique :
    - 2002/2007/2012 : nuance (code-candidat) → nuances_harmonisees
    - 2017/2022      : nom (nuance NULL)       → candidats_presidentielle
    COALESCE(nh.bloc, cp.bloc) couvre les deux cas en un seul SELECT.
    """
    # ── Vue 1 — résultats par BV avec bloc résolu ─────────────────────────
    con.execute("""
        CREATE OR REPLACE VIEW v_resultats_candidats_avec_bloc AS
        SELECT
            rc.id_election,
            e.type_scrutin,
            e.annee,
            e.tour,
            rc.code_departement,
            rc.code_commune,
            rc.code_bv,
            rc.no_panneau,
            rc.nom,
            rc.prenom,
            rc.nuance,
            rc.voix,
            COALESCE(nh.bloc, cp.bloc) AS bloc
        FROM resultats_candidats rc
        JOIN elections e ON e.id_election = rc.id_election
        LEFT JOIN nuances_harmonisees nh
            ON nh.nuance = rc.nuance AND nh.annee = e.annee
        LEFT JOIN candidats_presidentielle cp
            ON cp.nom = rc.nom AND cp.annee = e.annee
    """)

    # ── Vue 2 — scores par commune, présidentielles ───────────────────────
    con.execute("""
        CREATE OR REPLACE VIEW v_scores_commune_pres AS
        SELECT
            r.id_election,
            r.annee,
            r.tour,
            r.code_departement,
            r.code_commune,
            r.bloc,
            SUM(r.voix) AS voix
        FROM v_resultats_candidats_avec_bloc r
        WHERE r.type_scrutin = 'pres'
        GROUP BY r.id_election, r.annee, r.tour, r.code_departement, r.code_commune, r.bloc
    """)

    # ── Vue 3 — participation par commune, présidentielles ────────────────
    con.execute("""
        CREATE OR REPLACE VIEW v_participation_commune_pres AS
        SELECT
            rp.id_election,
            e.annee,
            e.tour,
            rp.code_departement,
            rp.code_commune,
            SUM(rp.inscrits)                                                        AS inscrits,
            SUM(rp.votants)                                                         AS votants,
            SUM(rp.exprimes)                                                        AS exprimes,
            SUM(rp.blancs)                                                          AS blancs,
            SUM(rp.nuls)                                                            AS nuls,
            SUM(rp.abstentions)                                                     AS abstentions,
            ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2)        AS taux_participation_pct
        FROM resultats_participation rp
        JOIN elections e ON e.id_election = rp.id_election
        WHERE e.type_scrutin = 'pres'
        GROUP BY rp.id_election, e.annee, e.tour, rp.code_departement, rp.code_commune
    """)

    # ── Vue 4 — focus circo 21 Nord (Valenciennes, 20 communes) ──────────
    circo21_sql = ", ".join(f"'{c}'" for c in _CIRCO21_CODES)
    con.execute(f"""
        CREATE OR REPLACE VIEW v_scores_circo21_pres AS
        SELECT *
        FROM v_scores_commune_pres
        WHERE code_commune IN ({circo21_sql})
    """)

    # ── Vue 5 — évolution blocs dans le temps, circo 21 ──────────────────
    con.execute("""
        CREATE OR REPLACE VIEW v_evolution_blocs_circo21 AS
        SELECT
            annee,
            tour,
            bloc,
            SUM(voix) AS voix_total
        FROM v_scores_circo21_pres
        GROUP BY annee, tour, bloc
        ORDER BY annee, tour, bloc
    """)

    # ── Vue 6 — scores par circonscription, législatives ─────────────────
    con.execute("""
        CREATE OR REPLACE VIEW v_scores_circo_legi AS
        SELECT
            rc.id_election,
            e.annee,
            e.tour,
            e.ancien_decoupage,
            rp.code_circo,
            COALESCE(nh.bloc, 'DIV') AS bloc,
            SUM(rc.voix)             AS voix
        FROM resultats_candidats rc
        JOIN elections e ON e.id_election = rc.id_election
        JOIN resultats_participation rp
            ON rp.id_election      = rc.id_election
            AND rp.code_departement = rc.code_departement
            AND rp.code_commune     = rc.code_commune
            AND rp.code_bv          = rc.code_bv
        LEFT JOIN nuances_harmonisees nh ON nh.nuance = rc.nuance AND nh.annee = e.annee
        WHERE e.type_scrutin = 'legi'
          AND rp.code_circo IS NOT NULL
        GROUP BY
            rc.id_election, e.annee, e.tour, e.ancien_decoupage,
            rp.code_circo, COALESCE(nh.bloc, 'DIV')
    """)

    # ── Vue 7 — participation par circonscription, législatives ──────────
    con.execute("""
        CREATE OR REPLACE VIEW v_participation_circo_legi AS
        SELECT
            rp.id_election,
            e.annee,
            e.tour,
            e.ancien_decoupage,
            rp.code_circo,
            SUM(rp.inscrits)                                                  AS inscrits,
            SUM(rp.votants)                                                   AS votants,
            SUM(rp.exprimes)                                                  AS exprimes,
            ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2)  AS taux_participation_pct
        FROM resultats_participation rp
        JOIN elections e ON e.id_election = rp.id_election
        WHERE e.type_scrutin = 'legi'
          AND rp.code_circo IS NOT NULL
        GROUP BY rp.id_election, e.annee, e.tour, e.ancien_decoupage, rp.code_circo
    """)

    # ── Vue 8 — évolution temporelle des blocs HdF, législatives ─────────
    con.execute("""
        CREATE OR REPLACE VIEW v_evolution_blocs_hdf_legi AS
        SELECT
            annee,
            tour,
            ancien_decoupage,
            bloc,
            SUM(voix) AS voix_total
        FROM v_scores_circo_legi
        GROUP BY annee, tour, ancien_decoupage, bloc
        ORDER BY annee, tour, bloc
    """)

    logger.info("Vues d'agrégation créées/mises à jour : 8 vues")
