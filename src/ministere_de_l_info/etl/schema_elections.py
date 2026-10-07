"""Schéma DuckDB — tables électorales et référentiels politiques.

Séparé de schema.py pour la clarté.

Fonctions exportées
-------------------
- create_elections_schema(con)        : CREATE TABLE IF NOT EXISTS × 6, idempotent
- populate_elections_referentiels(con): remplit blocs_politiques, elections,
  nuances_harmonisees (pres + legi + muni) et candidats_presidentielle ;
  idempotent (DELETE + INSERT)
- populate_nuances_municipales(con)   : remplace les seules nuances municipales
  (DELETE ciblé par année + INSERT), utilisé par load_elections_municipales.py

Les tables de résultats (resultats_participation, resultats_candidats) sont créées
vides ici ; le chargement des Parquet est fait en C2b (scripts/load_elections.py).

Filtrage géographique
---------------------
Le chargement C2b filtrera sur CODE_REGION_HDF = "32" (Hauts-de-France) via
jointure sur geographies_communes.code_region.

Blocs politiques
----------------
Nomenclature officielle du Ministère de l'Intérieur : 6 blocs (EXG, GAU, DIV, CENT,
DTE, EXD). Première grille officielle de blocs : INTA1931378J (municipales 2020,
annexe 3, bloc « divers » nommé AUT), puis IOMA2322276J (sénatoriales 2023) et
INTP2602966C (municipales 2026). Doctrine (ADR-0010) : grille du scrutin si elle
existe ; sinon grille la plus proche dans le temps (antérieure de préférence) si le
code y désigne la même famille politique ; sinon classement reconstruit justifié.
Chaque entrée porte une colonne source_bloc indiquant la source de référence.
Voir docs/adr/0005-nuances-et-blocs-officiels.md, docs/adr/0010-revision-nuances-et-blocs.md
et docs/sources-officielles/nuances/index.md.
"""

from __future__ import annotations

import logging

import duckdb

from ministere_de_l_info._sql import ligne_unique
from ministere_de_l_info.perimetre import DEPTS_HDF_SQL

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
# Première grille officielle : INTA1931378J (municipales 2020, annexe 3 ; « AUT » = DIV).
# Grilles suivantes : IOMA2322276J (2023), INTP2602966C (2026). Voir ADR-0010.
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
# Aucune grille officielle ne couvre ces scrutins : doctrine ADR-0010 (grille la plus
# proche, INTA1931378J 2020, si même famille politique ; sinon reconstruction justifiée).
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
        "DIV",
        "Lepage – Cap21, écologiste autonome → DIV : grille la plus proche INTA1931378J "
        "(2020) range « Rassemblement citoyen-CAP 21 » dans ECO → AUT (= DIV), même "
        "formation (ADR-0010 ; avant : CENT)",
    ),
    ("LEPE", 2002, "EXD", "Le Pen J.-M. – FN → EXD"),
    ("MADE", 2002, "DTE", "Madelin – DL (libéral-conservateur) → DTE"),
    ("MAME", 2002, "GAU", "Mamère – Verts (DVGV) → GAU"),
    ("MEGR", 2002, "EXD", "Mégret – MNR (scission FN) → EXD"),
    (
        "SAIN",
        2002,
        "DIV",
        "Saint-Josse – CPNT autonome (candidat contre la droite parlementaire) → DIV "
        "maintenu : INTA1931378J (2020) range CPNT dans DVD du fait de son association "
        "à l'UMP/LR après 2010, famille différente à l'époque (ADR-0010)",
    ),
    ("TAUB", 2002, "GAU", "Taubira – PRG (allié PS) → GAU"),
    # ── 2007 (12 candidats) ────────────────────────────────────────────────
    ("BAYR", 2007, "CENT", "Bayrou – MoDem → CENT"),
    ("BESA", 2007, "EXG", "Besancenot – LCR → EXG"),
    ("BOVE", 2007, "GAU", "Bové – altermondialiste/soutien Verts (DVGV) → GAU"),
    ("BUFF", 2007, "GAU", "Buffet – PCF → GAU"),
    ("LAGU", 2007, "EXG", "Laguiller – LO → EXG"),
    ("LEPE", 2007, "EXD", "Le Pen J.-M. – FN → EXD"),
    (
        "NIHO",
        2007,
        "DIV",
        "Nihous – CPNT autonome (candidat contre l'UMP) → DIV maintenu : rattachement "
        "de CPNT à DVD (INTA1931378J, 2020) postérieur à 2010 (ADR-0010)",
    ),
    ("ROYA", 2007, "GAU", "Royal – PS → GAU"),
    ("SARK", 2007, "DTE", "Sarkozy – UMP → DTE"),
    ("SCHI", 2007, "EXG", "Schivardi – PT trotskiste → EXG"),
    (
        "VILL",
        2007,
        "DTE",
        "de Villiers – MPF (DVDR) → DTE (INTA1931378J p. 8 : MPF ∈ DVD ; p. 10 : DVD → DTE)",
    ),
    ("VOYN", 2007, "GAU", "Voynet – Verts (DVGV) → GAU"),
    # ── 2012 (10 candidats) ────────────────────────────────────────────────
    ("ARTH", 2012, "EXG", "Arthaud – LO → EXG"),
    ("BAYR", 2012, "CENT", "Bayrou – MoDem → CENT"),
    ("CHEM", 2012, "DIV", "Cheminade – Solidarité et Progrès → DIV"),
    (
        "DUPO",
        2012,
        "DTE",
        "Dupont-Aignan – DLR (devenu DLF) → DTE (INTA1931378J p. 10 : DLF → DTE)",
    ),
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
# 2024 = IOMA2415630C. Aucune de ces circulaires ne contient de grille de blocs :
# doctrine ADR-0010 (grille la plus proche : INTA1931378J 2020 pour 2002-2022,
# IOMA2322276J 2023 pour 2024). Reclassements ADR-0010 : ECO 2002/2007/2012/2024 → DIV,
# PRV 2012 → CENT, UDI 2024 → DTE.
# Détail et justification : reports/mapping-nuances-legislatives-validated.md, ADR-0010
# Format : (nuance, annee, bloc, source_bloc)
_NUANCES_LEGI: list[tuple[str, int, str, str]] = [
    # ── 2002 (22 nuances) ──────────────────────────────────────────────────
    ("COM", 2002, "GAU", "PCF → GAU (logique officielle Ministère, pas EXG)"),
    (
        "CPNT",
        2002,
        "DIV",
        "CPNT, nuance propre et autonome en 2002 → DIV maintenu : son rangement dans DVD "
        "(INTA1931378J, 2020) reflète l'association à l'UMP/LR après 2010 (ADR-0010)",
    ),
    ("DIV", 2002, "DIV", "Divers → mapping direct"),
    ("DL", 2002, "DTE", "Démocratie Libérale (Madelin) libéral-conservateur → DTE"),
    ("DVD", 2002, "DTE", "Divers Droite → mapping direct"),
    ("DVG", 2002, "GAU", "Divers Gauche → mapping direct"),
    (
        "ECO",
        2002,
        "DIV",
        "Écologistes hors Verts (VEC distinct) → DIV : INTA1931378J (2020) ECO hors EELV "
        "→ AUT (= DIV), même sens (ADR-0010 ; avant : GAU)",
    ),
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
        "MPF (Villiers) → DTE (INTA1931378J p. 8 : MPF ∈ DVD ; p. 10 : DVD → DTE)",
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
    ("VEC", 2002, "GAU", "Les Verts → GAU (VEC = GAU dans les grilles 2020, 2023, 2026)"),
    # ── 2007 (17 nuances) ──────────────────────────────────────────────────
    ("COM", 2007, "GAU", "PCF → GAU"),
    (
        "CPNT",
        2007,
        "DIV",
        "CPNT, nuance propre et autonome en 2007 → DIV maintenu : son rangement dans DVD "
        "(INTA1931378J, 2020) reflète l'association à l'UMP/LR après 2010 (ADR-0010)",
    ),
    ("DIV", 2007, "DIV", "Divers → mapping direct"),
    ("DVD", 2007, "DTE", "Divers Droite → DTE"),
    ("DVG", 2007, "GAU", "Divers Gauche → GAU"),
    (
        "ECO",
        2007,
        "DIV",
        "Écologistes hors Verts (VEC distinct) → DIV : INTA1931378J (2020) ECO hors EELV "
        "→ AUT (= DIV), même sens (ADR-0010 ; avant : GAU)",
    ),
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
    (
        "ECO",
        2012,
        "DIV",
        "Écologistes hors EELV (VEC distinct) → DIV : INTA1931378J (2020) ECO hors EELV "
        "→ AUT (= DIV), même sens (ADR-0010 ; avant : GAU)",
    ),
    ("EXD", 2012, "EXD", "Extrême droite → code = bloc"),
    ("EXG", 2012, "EXG", "Extrême gauche → code = bloc"),
    ("FG", 2012, "GAU", "Front de Gauche (PCF+PG) → GAU ; LFI bascule EXG en 2026 (INTP2602966C)"),
    ("FN", 2012, "EXD", "Front National → EXD"),
    ("NCE", 2012, "CENT", "Nouveau Centre (Borloo, allié UMP) → CENT"),
    (
        "PRV",
        2012,
        "CENT",
        "Parti radical valoisien (sorti de l'UMP en 2011, ARES puis UDI) → CENT : "
        "INTA1931378J (2020) Mouvement radical (MR, successeur du PRV) → CENT ; "
        "INTP2602966C (2026) PR → CENT (ADR-0010 ; avant : DTE)",
    ),
    ("RDG", 2012, "GAU", "Radical de Gauche (allié PS) → GAU"),
    ("REG", 2012, "DIV", "Régionalistes → DIV"),
    ("SOC", 2012, "GAU", "Parti Socialiste → GAU"),
    ("UMP", 2012, "DTE", "UMP (Sarkozy → Fillon) → DTE"),
    ("VEC", 2012, "GAU", "Les Verts/EELV → GAU"),
    # ── 2017 (17 nuances) ──────────────────────────────────────────────────
    ("COM", 2017, "GAU", "PCF → GAU"),
    ("DIV", 2017, "DIV", "Divers → mapping direct"),
    (
        "DLF",
        2017,
        "DTE",
        "Debout la France → DTE (INTA1931378J p. 10 ; CE n° 437675 a suspendu DLF → EXD)",
    ),
    ("DVD", 2017, "DTE", "Divers Droite → DTE"),
    ("DVG", 2017, "GAU", "Divers Gauche → GAU"),
    (
        "ECO",
        2017,
        "GAU",
        "Écologistes incluant EELV (pas de code VEC en 2017) → GAU maintenu : ECO de "
        "la grille INTA1931378J (2020) exclut EELV, sens différent (ADR-0010)",
    ),
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
    (
        "UDI",
        2017,
        "CENT",
        "Union des démocrates et indépendants → CENT : grille la plus proche "
        "INTA1931378J (2020) UDI → CENT (ADR-0010)",
    ),
    # ── 2022 (16 nuances) — source INTA2212053C ────────────────────────────
    ("DIV", 2022, "DIV", "Divers → mapping direct"),
    ("DSV", 2022, "DTE", "Divers Souverainiste → DTE (souverainistes non-EXD, logique CE DLF)"),
    ("DVC", 2022, "CENT", "Divers Centre → mapping direct"),
    ("DVD", 2022, "DTE", "Divers Droite → DTE"),
    ("DVG", 2022, "GAU", "Divers Gauche → GAU"),
    ("DXD", 2022, "EXD", "Divers Extrême Droite → code explicite"),
    ("DXG", 2022, "EXG", "Divers Extrême Gauche → code explicite"),
    (
        "ECO",
        2022,
        "GAU",
        "Écologistes incluant EELV (INTA2212053C annexe 1, pas de code VEC) → GAU "
        "maintenu : ECO de la grille antérieure INTA1931378J (2020) exclut EELV, sens "
        "différent (ADR-0010)",
    ),
    ("ENS", 2022, "CENT", "Ensemble! (LREM+MoDem+Horizons) → CENT"),
    ("LR", 2022, "DTE", "Les Républicains → DTE"),
    ("NUP", 2022, "GAU", "NUPES (LFI+PS+PCF+EELV) → GAU ; LFI bascule EXG en 2026 (INTP2602966C)"),
    ("RDG", 2022, "GAU", "Radical de Gauche → GAU"),
    ("REC", 2022, "EXD", "Reconquête (Zemmour, INTA2212053C) → EXD"),
    ("REG", 2022, "DIV", "Régionalistes → DIV"),
    ("RN", 2022, "EXD", "Rassemblement National → EXD (CE 21/09/2023 n°488379)"),
    (
        "UDI",
        2022,
        "CENT",
        "UDI → CENT : grille antérieure la plus proche INTA1931378J (2020) UDI → CENT (ADR-0010)",
    ),
    # ── 2024 (22 nuances) — source IOMA2415630C ────────────────────────────
    ("COM", 2024, "GAU", "PCF standalone (hors NFP) → GAU"),
    ("DIV", 2024, "DIV", "Divers → mapping direct"),
    (
        "DSV",
        2024,
        "DTE",
        "Droite souverainiste (Debout la France…) → DTE : IOMA2322276J (2023) DLF → "
        "Droite ; INTP2602966C (2026) DSV → DTE (IOMA2415630C sans grille de blocs)",
    ),
    ("DVC", 2024, "CENT", "Divers Centre → CENT"),
    ("DVD", 2024, "DTE", "Divers Droite → DTE"),
    ("DVG", 2024, "GAU", "Divers Gauche → GAU"),
    (
        "ECO",
        2024,
        "DIV",
        "Autres candidats de sensibilité écologiste (VEC distinct, IOMA2415630C) → DIV : "
        "IOMA2322276J (2023) ECO → Autres (= DIV), même sens ; INTP2602966C (2026) "
        "concorde (ADR-0010 ; avant : GAU)",
    ),
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
    (
        "UDI",
        2024,
        "DTE",
        "UDI → DTE : grille antérieure la plus proche IOMA2322276J (2023) UDI → Droite, "
        "même formation ; INTP2602966C (2026) la replace en CENT, postérieure au scrutin "
        "(ADR-0010 ; avant : CENT)",
    ),
    (
        "UG",
        2024,
        "GAU",
        "NFP/Union de la Gauche (PS+PCF+EELV+LFI) → GAU (IOMA2415630C définit UG = Union de la gauche)",
    ),
    ("UXD", 2024, "EXD", "Union d'extrême droite (RN+alliés 2024) → EXD"),
    ("VEC", 2024, "GAU", "Verts standalone (hors NFP) → GAU"),
]

# ── Nuances municipales (2008 / 2014 / 2020 / 2026) ──────────────────────────
# Source unique du référentiel municipal (correctif C2, audit 2026-09-24).
# 67 entrées validées en phase D3.2 (ADR-0005), révisées par l'ADR-0010 (2026-09-24,
# addendum 2026-09-25) :
# - 2020 et 2026 : application stricte des grilles officielles de blocs
#   (INTA1931378J annexe 3 p. 10 ; INTP2602966C annexe 3 p. 12) ; « AUT » (2020) = DIV ;
#   ajout des codes de liste officiels jusque-là non mappés (2020 : LREG, LGJ, LMDM,
#   LDLF ; 2026 : LUD, LREN, LMDM, LDSV, LREC, LREG) ;
# - 2008 et 2014 (aucune grille) : grille la plus proche (INTA1931378J) pour LCOM,
#   LUD, LUDI (même famille politique) ;
# - lot 2 (addendum ADR-0010 du 2026-09-25) : libellés officiels 2008 et 2014 vérifiés sur
#   les archives du ministère (docs/sources-officielles/nuances/2008-* et 2014-*) :
#   LCMD GAU → CENT, LMAJ exclu → DTE, LGC (DIV) et LMC (CENT) maintenus par la règle 3,
#   ajout de LREG → DIV et LEXD → EXD (2008).
# Total : 80 entrées (2008 : 15, 2014 : 17, 2020 : 23, 2026 : 25).
# Codes SANS mapping (non insérés, bloc NULL en vue) : NC (2014/2020), LNC (2020)
# Format : (nuance, annee, bloc, source_bloc)
_SRC_2020 = "INTA1931378J annexe 3 p. 10"
_SRC_2026 = "INTP2602966C annexe 3 p. 12"
_ARCH_2008 = "libellé officiel archives ministère MN2008 (vérif. 2026-09-25)"
_ARCH_2014 = "libellé officiel archives ministère MN2014 (vérif. 2026-09-25)"

_NUANCES_MUNI: list[tuple[str, int, str, str]] = [
    # ── 2008 — seuil 3 500 hab — 164 communes HdF nuancées ───────────────────
    # 15 codes = référentiel officiel complet des listes 2008 (archives du ministère).
    ("LAUT", 2008, "DIV", f"« Liste inclassable » ({_ARCH_2008}) → DIV (D3.2)"),
    (
        "LCMD",
        2008,
        "CENT",
        f"« Liste centre-MoDem » ({_ARCH_2008}) → CENT : grille la plus proche "
        f"{_SRC_2020} LMDM → CENT, même formation (ADR-0010 lot 2 ; avant : GAU, "
        "code lu à tort « Communiste et Divers »)",
    ),
    (
        "LCOM",
        2008,
        "GAU",
        f"« Liste du Parti Communiste » ({_ARCH_2008}) → GAU : aucune grille 2008, grille "
        f"la plus proche {_SRC_2020} LCOM → GAU, même famille (ADR-0010 ; avant : EXG)",
    ),
    ("LDVD", 2008, "DTE", f"« Liste divers droite » ({_ARCH_2008}) → DTE (D3.2)"),
    ("LDVG", 2008, "GAU", f"« Liste divers gauche » ({_ARCH_2008}) → GAU (D3.2)"),
    (
        "LEXD",
        2008,
        "EXD",
        f"« Liste d'extrême droite » ({_ARCH_2008}) → EXD : grille la plus proche "
        f"{_SRC_2020} LEXD → EXD (ADR-0010 lot 2 ; ajout)",
    ),
    ("LEXG", 2008, "EXG", f"« Liste d'extrême gauche » ({_ARCH_2008}) → EXG (D3.2)"),
    ("LFN", 2008, "EXD", f"« Liste du Front National » ({_ARCH_2008}) → EXD (D3.2)"),
    (
        "LGC",
        2008,
        "DIV",
        f"« Liste gauche-centristes » ({_ARCH_2008}) : entente gauche + centristes sans "
        "équivalent dans les grilles officielles (règle 2 inapplicable) → classement "
        "D3.2 maintenu, règle 3 (ADR-0010 lot 2)",
    ),
    (
        "LMAJ",
        2008,
        "DTE",
        f"« Liste de la majorité » ({_ARCH_2008}) : majorité présidentielle UMP/NC → DTE, "
        f"grille la plus proche {_SRC_2020} LLR/LUD → DTE, même famille ; cohérent avec "
        "MAJ 2007 → DTE (ADR-0010 lot 2 ; avant : exclu, lu « liste sortante »)",
    ),
    (
        "LMC",
        2008,
        "CENT",
        f"« Liste majorité-centristes » ({_ARCH_2008}) : entente majorité + centristes "
        "sans équivalent dans les grilles officielles → classement D3.2 maintenu, "
        "règle 3 (ADR-0010 lot 2)",
    ),
    (
        "LREG",
        2008,
        "DIV",
        f"« Liste régionaliste » ({_ARCH_2008}) → DIV : grille la plus proche "
        f"{_SRC_2020} LREG → AUT = DIV (ADR-0010 lot 2 ; ajout)",
    ),
    ("LSOC", 2008, "GAU", f"« Liste du Parti Socialiste » ({_ARCH_2008}) → GAU (D3.2)"),
    ("LUG", 2008, "GAU", f"« Liste d'union de la gauche » ({_ARCH_2008}) → GAU (D3.2)"),
    ("LVEC", 2008, "GAU", f"« Liste des Verts » ({_ARCH_2008}) → GAU (D3.2 ; ADR-0010 (c))"),
    # ── 2014 — seuil 1 000 hab — ~3 778 communes HdF nuancées ────────────────
    # 17 codes = référentiel officiel des listes 2014 (archives du ministère), sans NC.
    (
        "LCOM",
        2014,
        "GAU",
        f"« Liste du Parti communiste français » ({_ARCH_2014}) → GAU : aucune grille 2014, "
        f"grille la plus proche {_SRC_2020} LCOM → GAU, même famille (ADR-0010 ; avant : EXG)",
    ),
    ("LDIV", 2014, "DIV", f"« Liste Divers » ({_ARCH_2014}) → DIV (D3.2)"),
    ("LDVD", 2014, "DTE", f"« Liste Divers droite » ({_ARCH_2014}) → DTE (D3.2)"),
    ("LDVG", 2014, "GAU", f"« Liste Divers gauche » ({_ARCH_2014}) → GAU (D3.2)"),
    ("LEXD", 2014, "EXD", f"« Liste Extrême droite » ({_ARCH_2014}) → EXD (D3.2)"),
    ("LEXG", 2014, "EXG", f"« Liste Extrême gauche » ({_ARCH_2014}) → EXG (D3.2)"),
    (
        "LFG",
        2014,
        "GAU",
        f"« Liste Front de Gauche » ({_ARCH_2014}) : PCF + Parti de Gauche, 2012-2016 — "
        "GAU per ADR-0005 ; bascule EXG concerne LFI/Mélenchon en 2026 seulement (D3.2)",
    ),
    ("LFN", 2014, "EXD", f"« Liste Front National » ({_ARCH_2014}) → EXD (D3.2)"),
    ("LMDM", 2014, "CENT", f"« Liste Modem » ({_ARCH_2014}) → CENT (D3.2)"),
    (
        "LPG",
        2014,
        "GAU",
        f"« Liste du Parti de Gauche » ({_ARCH_2014}) : Mélenchon, 2008-2016, dans le "
        "Front de Gauche en 2014 ; GAU par cohérence avec LFG (D3.2)",
    ),
    ("LSOC", 2014, "GAU", f"« Liste Socialiste » ({_ARCH_2014}) → GAU (D3.2)"),
    ("LUC", 2014, "CENT", f"« Liste Union du Centre » ({_ARCH_2014}) → CENT (D3.2)"),
    (
        "LUD",
        2014,
        "DTE",
        f"« Liste Union de la Droite » ({_ARCH_2014}) → DTE : grille la plus proche "
        f"{_SRC_2020} LUD → DTE, même sens (ADR-0010 ; avant : CENT)",
    ),
    (
        "LUDI",
        2014,
        "CENT",
        f"« Liste Union Démocrates et Indépendants » ({_ARCH_2014}) → CENT : grille la plus "
        f"proche {_SRC_2020} LUDI → CENT, même formation (ADR-0010 ; avant : DIV)",
    ),
    ("LUG", 2014, "GAU", f"« Liste Union de la Gauche » ({_ARCH_2014}) → GAU (D3.2)"),
    (
        "LUMP",
        2014,
        "DTE",
        f"« Liste Union pour un Mouvement Populaire » ({_ARCH_2014}) → DTE (D3.2)",
    ),
    (
        "LVEC",
        2014,
        "GAU",
        f"« Liste Europe-Ecologie-Les Verts » ({_ARCH_2014}) → GAU (D3.2 ; ADR-0010 (c))",
    ),
    # NC (~45 281 occurrences HdF t1) : non inséré — absent du référentiel officiel 2014
    # (communes de moins de 1 000 hab.), pas un bloc idéologique (D3.2 ; vérif. 2026-09-25)
    # ── 2020 — seuil 3 500 hab — ~3 779 communes HdF nuancées ────────────────
    # Grille officielle INTA1931378J annexe 3 : les 23 codes de liste y figurent.
    (
        "LCOM",
        2020,
        "GAU",
        f"Liste du Parti communiste français → GAU ({_SRC_2020} ; ADR-0010 ; avant : EXG)",
    ),
    ("LDIV", 2020, "DIV", f"Divers — grille officielle ({_SRC_2020})"),
    (
        "LDVC",
        2020,
        "CENT",
        f"Divers centre → CENT ({_SRC_2020}) ; CE 31/01/2020 n°437675 a seulement "
        "suspendu l'attribution de LDVC aux listes simplement soutenues par LREM/MoDem/UDI",
    ),
    ("LDVD", 2020, "DTE", f"Divers Droite — grille officielle ({_SRC_2020})"),
    ("LDVG", 2020, "GAU", f"Divers Gauche — grille officielle ({_SRC_2020})"),
    (
        "LECO",
        2020,
        "DIV",
        f"Autre liste écologiste, hors EELV (LVEC distinct) → AUT = DIV ({_SRC_2020} ; "
        "ADR-0010 ; avant : GAU)",
    ),
    ("LEXD", 2020, "EXD", f"Extrême droite — grille officielle ({_SRC_2020})"),
    ("LEXG", 2020, "EXG", f"Extrême gauche — grille officielle ({_SRC_2020})"),
    (
        "LFI",
        2020,
        "GAU",
        "La France Insoumise 2020 — GAU per circulaire INTA1931378J ; "
        "bascule EXG uniquement à partir de 2026 (INTP2602966C + CE 27/02/2026 n°512694) (D3.2)",
    ),
    ("LLR", 2020, "DTE", f"Les Républicains — grille officielle ({_SRC_2020})"),
    # LNC (~1 787 occurrences) : non inséré — parallèle structurel avec NC ;
    # identité LNC ambiguë (Nouveau Centre ou Liste Non Classée) → NULL (D3.2, Q9 validé)
    ("LRDG", 2020, "GAU", f"Radicaux de Gauche — allié PS — grille officielle ({_SRC_2020})"),
    ("LREM", 2020, "CENT", f"La République En Marche — grille officielle ({_SRC_2020})"),
    ("LRN", 2020, "EXD", f"Rassemblement National — grille officielle ({_SRC_2020})"),
    ("LSOC", 2020, "GAU", f"Socialiste — grille officielle ({_SRC_2020})"),
    ("LUC", 2020, "CENT", f"Union Centre — grille officielle ({_SRC_2020})"),
    (
        "LUD",
        2020,
        "DTE",
        f"Liste union de la droite (dont LR) → DTE ({_SRC_2020} ; ADR-0010 ; avant : CENT)",
    ),
    ("LUDI", 2020, "CENT", f"Liste UDI → CENT ({_SRC_2020} ; ADR-0010 ; avant : DIV)"),
    ("LUG", 2020, "GAU", f"Union de la Gauche — grille officielle ({_SRC_2020})"),
    ("LVEC", 2020, "GAU", f"Verts / EELV — grille officielle ({_SRC_2020})"),
    # Codes officiels ajoutés par l'ADR-0010 (sans effet s'ils sont absents des données HdF)
    ("LREG", 2020, "DIV", f"Liste régionaliste → AUT = DIV ({_SRC_2020} ; ajout ADR-0010)"),
    ("LGJ", 2020, "DIV", f"Liste Gilets jaunes → AUT = DIV ({_SRC_2020} ; ajout ADR-0010)"),
    ("LMDM", 2020, "CENT", f"Liste Modem → CENT ({_SRC_2020} ; ajout ADR-0010)"),
    ("LDLF", 2020, "DTE", f"Liste Debout la France → DTE ({_SRC_2020} ; ajout ADR-0010)"),
    # NC (~43 074 occurrences HdF t1) : non inséré — voir 2014 NC (D3.2)
    # ── 2026 — seuil 3 500 hab — ~318 communes HdF nuancées ──────────────────
    # Grille officielle INTP2602966C annexe 3 : les 25 codes de liste y figurent.
    (
        "LCOM",
        2026,
        "GAU",
        f"Liste investie par le Parti communiste français → GAU ({_SRC_2026} ; "
        "ADR-0010 ; avant : EXG)",
    ),
    ("LDIV", 2026, "DIV", f"Divers — grille officielle ({_SRC_2026})"),
    ("LDVC", 2026, "CENT", f"Divers Centre — grille officielle ({_SRC_2026})"),
    ("LDVD", 2026, "DTE", f"Divers Droite — grille officielle ({_SRC_2026})"),
    ("LDVG", 2026, "GAU", f"Divers Gauche — grille officielle ({_SRC_2026})"),
    (
        "LECO",
        2026,
        "DIV",
        f"Liste écologiste hors Les Écologistes (LVEC distinct) → DIV ({_SRC_2026} ; "
        "ADR-0010 ; avant : GAU)",
    ),
    ("LEXD", 2026, "EXD", f"Extrême droite — grille officielle ({_SRC_2026})"),
    ("LEXG", 2026, "EXG", f"Extrême gauche — grille officielle ({_SRC_2026})"),
    (
        "LFI",
        2026,
        "EXG",
        "La France Insoumise 2026 — EXG per circulaire INTP2602966C (2 fév. 2026) "
        "+ CE 27/02/2026 n°512694 (rejet recours LFI) (D3.2)",
    ),
    (
        "LHOR",
        2026,
        "CENT",
        f"Horizons — parti centriste Édouard Philippe — grille officielle ({_SRC_2026})",
    ),
    ("LLR", 2026, "DTE", f"Les Républicains — grille officielle ({_SRC_2026})"),
    ("LRN", 2026, "EXD", f"Rassemblement National — grille officielle ({_SRC_2026})"),
    ("LSOC", 2026, "GAU", f"Socialiste — grille officielle ({_SRC_2026})"),
    ("LUC", 2026, "CENT", f"Union Centre — grille officielle ({_SRC_2026})"),
    (
        "LUDI",
        2026,
        "CENT",
        f"Liste investie par l'UDI → CENT ({_SRC_2026} ; ADR-0010 ; avant : DIV)",
    ),
    (
        "LUDR",
        2026,
        "EXD",
        f"Union des droites pour la République (parti Ciotti, allié RN) → EXD "
        f"({_SRC_2026} ; CE 27/02/2026 n°512694)",
    ),
    (
        "LUG",
        2026,
        "GAU",
        f"Union de la gauche (au moins deux partis parmi PCF, PS, Les Écologistes) → GAU "
        f"({_SRC_2026})",
    ),
    (
        "LUXD",
        2026,
        "EXD",
        f"Union de l'extrême droite (au moins deux partis parmi RN, REC, UDR) → EXD ({_SRC_2026})",
    ),
    ("LVEC", 2026, "GAU", f"Les Écologistes → GAU ({_SRC_2026})"),
    # Codes officiels ajoutés par l'ADR-0010 (sans effet s'ils sont absents des données HdF)
    (
        "LUD",
        2026,
        "DTE",
        f"Union de la droite (partis du bloc de droite, dont LR) → DTE ({_SRC_2026} ; "
        "ajout ADR-0010)",
    ),
    ("LREN", 2026, "CENT", f"Liste investie par Renaissance → CENT ({_SRC_2026} ; ajout ADR-0010)"),
    ("LMDM", 2026, "CENT", f"Liste investie par le Modem → CENT ({_SRC_2026} ; ajout ADR-0010)"),
    ("LDSV", 2026, "DTE", f"Droite souverainiste → DTE ({_SRC_2026} ; ajout ADR-0010)"),
    ("LREC", 2026, "EXD", f"Liste Reconquête → EXD ({_SRC_2026} ; ajout ADR-0010)"),
    ("LREG", 2026, "DIV", f"Liste régionaliste → DIV ({_SRC_2026} ; ajout ADR-0010)"),
]


# Années gérées par _NUANCES_MUNI (périmètre du DELETE ciblé de populate_nuances_municipales)
_ANNEES_MUNI: tuple[int, ...] = tuple(sorted({annee for _, annee, _, _ in _NUANCES_MUNI}))
# Codes municipaux volontairement SANS mapping (ADR-0005) : ne doivent jamais être insérés.
# LMAJ (2008) en est sorti : mappé DTE depuis l'addendum ADR-0010 du 2026-09-25 (lot 2).
_CODES_MUNI_SANS_MAPPING: frozenset[str] = frozenset({"NC", "LNC"})

# ── Nuances européennes, régionales, départementales (vague B, 2026-10-06) ───
# Classement validé par Mathias le 2026-10-07 (addendum ADR-0010 « vague B » ;
# reports/etl-elections-france-2026-10-06.md), reconstruit selon la doctrine ADR-0010 (b).
# Aucune grille ne couvre ces scrutins :
# - 1999 à 2021 : INTA1931378J (2020), seule grille antérieure ou la plus proche ;
# - européennes 2024 : IOMA2322276J (2023), grille antérieure la plus proche.
# Les codes de liste 2004 sont communs aux européennes et aux régionales ; les européennes
# 2014 utilisent les codes des municipales 2014 (déjà dans _NUANCES_MUNI, même sens).
# Cas tranchés par Mathias (2026-10-07) : LDR 2004 → DTE, LUCD/BC-UCD 2021 → DTE,
# BC-UCG 2021 → DIV, LECO/BC-ECO 2021 → GAU. Seuls codes restant sans bloc : résidus
# LPC/LDD/LDV des européennes 2009 (11 voix au total).
# « Composition » : code d'union absent des grilles dont toutes les composantes sont de
# gauche → GAU (décision Mathias 2026-10-07, Q3).
_SRC_2023 = "IOMA2322276J annexes 1-2 p. 6-7"
_R2 = "ADR-0010 règle 2"


def _n(
    nuance: str, annee: int, bloc: str, motif: str, grille: str = _SRC_2020
) -> tuple[str, int, str, str]:
    """Entrée (nuance, annee, bloc, source_bloc) avec grille et règle citées."""
    return (nuance, annee, bloc, f"{motif} ({grille} ; {_R2} ; décision Mathias 2026-10-07)")


_NUANCES_EURO_REGI_DPMT: list[tuple[str, int, str, str]] = [
    # ── Européennes 1999 (13 codes) ─────────────────────────────────────────
    _n("GAU", 1999, "GAU", "Liste PS-PRG-MDC (Hollande) ; SOC/RDG → GAU"),
    _n("DTE", 1999, "DTE", "Liste RPR-DL (Sarkozy) ; LR (successeur du RPR) → DTE"),
    _n("DVD", 1999, "DTE", "Liste RPF-MPF (Pasqua-Villiers) ; MPF ∈ DVD (p. 8) → DTE"),
    _n("VEC", 1999, "GAU", "Les Verts (Cohn-Bendit) ; VEC → GAU, ADR-0010 (c)"),
    _n("UDF", 1999, "CENT", "UDF (Bayrou) → CENT, cohérent UDF législatives 2002"),
    _n(
        "CPNT",
        1999,
        "DIV",
        "CPNT autonome (Saint-Josse) → DIV, cohérent CPNT 2002/2007 (règle 3, Q9)",
    ),
    _n("COM", 1999, "GAU", "PCF (Hue) ; LCOM → GAU"),
    _n("FRN", 1999, "EXD", "Front national (Le Pen) ; LRN (successeur) → EXD"),
    _n("EXG", 1999, "EXG", "Liste LO-LCR (Laguiller) ; code = bloc"),
    _n("DIV", 1999, "DIV", "Divers ; LDIV → AUT = DIV"),
    _n("MNA", 1999, "EXD", "MN-MNR (Mégret, scission FN) ; LEXD → EXD, cohérent MNR 2002"),
    _n("ECO", 1999, "DIV", "Écologistes hors Verts (MEI, Waechter), VEC distinct ; LECO → AUT"),
    _n("REG", 1999, "DIV", "Régionalistes ; LREG → AUT = DIV"),
    # ── 2004 : européennes + régionales (codes communs, 16 codes) ──────────────
    _n("LPS", 2004, "GAU", "Liste du Parti socialiste ; LSOC → GAU"),
    _n("LUMP", 2004, "DTE", "Liste UMP ; LLR (successeur) → DTE"),
    _n("LUDF", 2004, "CENT", "Liste UDF ; LMDM / LUDI (héritiers) → CENT"),
    _n("LFN", 2004, "EXD", "Liste du Front national ; LRN → EXD"),
    _n("LDD", 2004, "DTE", "Liste divers droite (dont MPF) ; LDVD → DTE"),
    _n("LVE", 2004, "GAU", "Liste des Verts ; LVEC → GAU, ADR-0010 (c)"),
    _n("LPC", 2004, "GAU", "Liste du Parti communiste ; LCOM → GAU"),
    _n("LDV", 2004, "DIV", "Liste divers ; LDIV → AUT = DIV"),
    _n("LXG", 2004, "EXG", "Liste d'extrême gauche ; LEXG → EXG"),
    _n("LCP", 2004, "DIV", "Liste CPNT autonome → DIV, cohérent CPNT 2002/2007 (règle 3, Q9)"),
    _n("LDG", 2004, "GAU", "Liste divers gauche ; LDVG → GAU"),
    _n("LEC", 2004, "DIV", "Liste écologiste hors Verts (LVE distinct, dont Cap 21) ; LECO → AUT"),
    _n("LXD", 2004, "EXD", "Liste d'extrême droite ; LEXD → EXD"),
    _n("LRG", 2004, "DIV", "Liste régionaliste ; LREG → AUT = DIV"),
    _n(
        "LGA",
        2004,
        "GAU",
        "Composition : liste de gauche (union PS-PCF-Verts : Huchon, Queyranne) ; LUG → GAU "
        "(union 100 % gauche, Q3)",
    ),
    _n(
        "LDR",
        2004,
        "DTE",
        "Liste divers droite des régionales (unions UMP-UDF, majoritairement UMP ; inclut "
        "des listes UDF autonomes : Santini, Bayrou, Arthuis) ; LUD → DTE (Q4)",
    ),
    # ── Européennes 2009 (12 codes) ─────────────────────────────────────────
    _n(
        "LMAJ",
        2009,
        "DTE",
        "Liste de la majorité présidentielle (UMP-NC) ; LUD → DTE, cohérent LMAJ 2008",
    ),
    _n("LSOC", 2009, "GAU", "Liste du Parti socialiste ; LSOC → GAU"),
    _n("LVEC", 2009, "GAU", "Europe Écologie ; LVEC → GAU, ADR-0010 (c)"),
    _n("LCMD", 2009, "CENT", "Liste MoDem ; LMDM → CENT, cohérent LCMD 2008"),
    _n("LDVD", 2009, "DTE", "Liste divers droite (Libertas MPF-CPNT, DLR) ; LDVD → DTE"),
    _n("LFN", 2009, "EXD", "Liste du Front national ; LRN → EXD"),
    _n("LEXG", 2009, "EXG", "Liste d'extrême gauche (NPA, LO) ; LEXG → EXG"),
    _n("LCOP", 2009, "GAU", "Front de gauche (PCF-PG, Mélenchon) ; LCOM / LFI → GAU"),
    _n("LAUT", 2009, "DIV", "Autres listes ; LDIV → AUT = DIV"),
    _n("LEXD", 2009, "EXD", "Liste d'extrême droite ; LEXD → EXD"),
    _n("LDVG", 2009, "GAU", "Liste divers gauche ; LDVG → GAU"),
    _n("LREG", 2009, "DIV", "Liste régionaliste ; LREG → AUT = DIV"),
    # ── Régionales 2010 (13 codes) ──────────────────────────────────────────
    _n("LMAJ", 2010, "DTE", "Liste de la majorité présidentielle (UMP-NC) ; LUD → DTE"),
    _n("LUG", 2010, "GAU", "Liste d'union de la gauche ; LUG → GAU"),
    _n("LSOC", 2010, "GAU", "Liste du Parti socialiste ; LSOC → GAU"),
    _n("LFN", 2010, "EXD", "Liste du Front national ; LRN → EXD"),
    _n("LVEC", 2010, "GAU", "Europe Écologie ; LVEC → GAU, ADR-0010 (c)"),
    _n("LDVG", 2010, "GAU", "Liste divers gauche (dont Frêche) ; LDVG → GAU"),
    _n("LCOP", 2010, "GAU", "Front de gauche (PCF-PG) ; LCOM / LFI → GAU"),
    _n("LCMD", 2010, "CENT", "Liste MoDem ; LMDM → CENT"),
    _n("LEXG", 2010, "EXG", "Liste d'extrême gauche ; LEXG → EXG"),
    _n("LAUT", 2010, "DIV", "Autres listes ; LDIV → AUT = DIV"),
    _n("LREG", 2010, "DIV", "Liste régionaliste ; LREG → AUT = DIV"),
    _n("LDVD", 2010, "DTE", "Liste divers droite ; LDVD → DTE"),
    _n("LEXD", 2010, "EXD", "Liste d'extrême droite ; LEXD → EXD"),
    # ── Régionales 2015 (20 codes) ──────────────────────────────────────────
    _n("LUD", 2015, "DTE", "Liste d'union de la droite (LR-UDI-MoDem) ; LUD → DTE"),
    _n("LFN", 2015, "EXD", "Liste du Front national ; LRN → EXD"),
    _n("LUG", 2015, "GAU", "Liste d'union de la gauche ; LUG → GAU"),
    _n("LDVG", 2015, "GAU", "Liste divers gauche ; LDVG → GAU"),
    _n("LVEC", 2015, "GAU", "EELV ; LVEC → GAU, ADR-0010 (c)"),
    _n("LDLF", 2015, "DTE", "Debout la France ; LDLF → DTE"),
    _n(
        "LVEG",
        2015,
        "GAU",
        "Composition : liste EELV-Front de gauche, LVEC et LFG/LCOM → GAU (union 100 % gauche, Q3)",
    ),
    _n("LFG", 2015, "GAU", "Front de gauche ; LCOM / LFI → GAU, cohérent LFG 2014"),
    _n("LREG", 2015, "DIV", "Liste régionaliste ; LREG → AUT = DIV"),
    _n("LCOM", 2015, "GAU", "Liste du Parti communiste ; LCOM → GAU"),
    _n("LEXG", 2015, "EXG", "Liste d'extrême gauche ; LEXG → EXG"),
    _n("LDIV", 2015, "DIV", "Liste divers ; LDIV → AUT = DIV"),
    _n("LDVD", 2015, "DTE", "Liste divers droite ; LDVD → DTE"),
    _n("LSOC", 2015, "GAU", "Liste du Parti socialiste ; LSOC → GAU"),
    _n("LECO", 2015, "DIV", "Liste écologiste hors EELV (LVEC distinct) ; LECO → AUT"),
    _n("LMDM", 2015, "CENT", "Liste MoDem ; LMDM → CENT"),
    _n("LLR", 2015, "DTE", "Liste Les Républicains ; LLR → DTE"),
    _n("LEXD", 2015, "EXD", "Liste d'extrême droite ; LEXD → EXD"),
    _n("LRDG", 2015, "GAU", "Liste du Parti radical de gauche ; LRDG → GAU"),
    _n("LUDI", 2015, "CENT", "Liste UDI ; LUDI → CENT"),
    # ── Régionales 2021 (22 codes) ──────────────────────────────────────────
    _n("LRN", 2021, "EXD", "Liste du Rassemblement national ; LRN → EXD"),
    _n("LUD", 2021, "DTE", "Liste d'union de la droite ; LUD → DTE"),
    _n(
        "LUGE",
        2021,
        "GAU",
        "Composition : union de la gauche et des écologistes, LUG et LVEC → GAU (union 100 % gauche, Q3)",
    ),
    _n("LUG", 2021, "GAU", "Liste d'union de la gauche ; LUG → GAU"),
    _n("LLR", 2021, "DTE", "Liste Les Républicains ; LLR → DTE"),
    _n("LUC", 2021, "CENT", "Liste d'union du centre ; LUC → CENT"),
    _n("LDVG", 2021, "GAU", "Liste divers gauche ; LDVG → GAU"),
    _n("LEXG", 2021, "EXG", "Liste d'extrême gauche ; LEXG → EXG"),
    _n("LDVC", 2021, "CENT", "Liste divers centre ; LDVC → CENT"),
    _n("LREG", 2021, "DIV", "Liste régionaliste ; LREG → AUT = DIV"),
    _n("LDVD", 2021, "DTE", "Liste divers droite ; LDVD → DTE"),
    _n("LDSV", 2021, "DTE", "Liste droite souverainiste ; LDLF → DTE (2020), LDSV → DTE (2026)"),
    _n("LREM", 2021, "CENT", "Liste La République en marche ; LREM → CENT"),
    _n("LFI", 2021, "GAU", "Liste La France insoumise ; LFI → GAU (2020, antérieure)"),
    _n("LDIV", 2021, "DIV", "Liste divers ; LDIV → AUT = DIV"),
    _n("LSOC", 2021, "GAU", "Liste du Parti socialiste ; LSOC → GAU"),
    _n("LCOM", 2021, "GAU", "Liste du Parti communiste ; LCOM → GAU"),
    _n("LMDM", 2021, "CENT", "Liste MoDem ; LMDM → CENT"),
    _n("LEXD", 2021, "EXD", "Liste d'extrême droite ; LEXD → EXD"),
    _n("LUDI", 2021, "CENT", "Liste UDI ; LUDI → CENT"),
    _n("LUCD", 2021, "DTE", "Liste d'union du centre et de la droite ; LUD → DTE (Q5)"),
    _n(
        "LECO",
        2021,
        "GAU",
        "Liste écologiste incluant EELV (aucun code LVEC en 2021 : Bayou, Grebert, Thierry) "
        "→ GAU, sens de l'époque comme ECO législatives 2017/2022 (Q7)",
    ),
    # ── Départementales 2015 (binômes, 19 codes) ────────────────────────────
    _n("BC-UD", 2015, "DTE", "Binôme d'union de la droite ; LUD → DTE"),
    _n("BC-FN", 2015, "EXD", "Binôme Front national ; RN → EXD"),
    _n("BC-SOC", 2015, "GAU", "Binôme Parti socialiste ; SOC → GAU"),
    _n("BC-UG", 2015, "GAU", "Binôme d'union de la gauche ; LUG → GAU"),
    _n("BC-UMP", 2015, "DTE", "Binôme UMP ; LR (successeur) → DTE"),
    _n("BC-DVD", 2015, "DTE", "Binôme divers droite ; DVD → DTE"),
    _n("BC-DVG", 2015, "GAU", "Binôme divers gauche ; DVG → GAU"),
    _n("BC-FG", 2015, "GAU", "Binôme Front de gauche ; COM / FI → GAU"),
    _n("BC-UDI", 2015, "CENT", "Binôme UDI ; UDI → CENT"),
    _n("BC-VEC", 2015, "GAU", "Binôme EELV ; VEC → GAU, ADR-0010 (c)"),
    _n("BC-DIV", 2015, "DIV", "Binôme divers ; DIV → AUT = DIV"),
    _n("BC-COM", 2015, "GAU", "Binôme Parti communiste ; COM → GAU"),
    _n("BC-RDG", 2015, "GAU", "Binôme Parti radical de gauche ; RDG → GAU"),
    _n("BC-MDM", 2015, "CENT", "Binôme MoDem ; MDM → CENT"),
    _n("BC-UC", 2015, "CENT", "Binôme d'union du centre ; LUC → CENT"),
    _n("BC-DLF", 2015, "DTE", "Binôme Debout la France ; DLF → DTE"),
    _n("BC-EXD", 2015, "EXD", "Binôme d'extrême droite ; EXD → EXD"),
    _n("BC-EXG", 2015, "EXG", "Binôme d'extrême gauche ; EXG → EXG"),
    _n("BC-PG", 2015, "GAU", "Binôme Parti de gauche ; FI (successeur) → GAU, cohérent LPG 2014"),
    # ── Départementales 2021 (binômes, 26 codes) ────────────────────────────
    _n("BC-DVD", 2021, "DTE", "Binôme divers droite ; DVD → DTE"),
    _n("BC-RN", 2021, "EXD", "Binôme Rassemblement national ; RN → EXD"),
    _n(
        "BC-UGE",
        2021,
        "GAU",
        "Composition : union de la gauche et des écologistes, UG et VEC → GAU (union 100 % gauche, Q3)",
    ),
    _n("BC-DVG", 2021, "GAU", "Binôme divers gauche ; DVG → GAU"),
    _n("BC-UG", 2021, "GAU", "Binôme d'union de la gauche ; LUG → GAU"),
    _n("BC-UD", 2021, "DTE", "Binôme d'union de la droite ; LUD → DTE"),
    _n("BC-LR", 2021, "DTE", "Binôme Les Républicains ; LR → DTE"),
    _n("BC-SOC", 2021, "GAU", "Binôme Parti socialiste ; SOC → GAU"),
    _n("BC-DVC", 2021, "CENT", "Binôme divers centre ; DVC → CENT"),
    _n("BC-DIV", 2021, "DIV", "Binôme divers ; DIV → AUT = DIV"),
    _n("BC-COM", 2021, "GAU", "Binôme Parti communiste ; COM → GAU"),
    _n("BC-UC", 2021, "CENT", "Binôme d'union du centre ; LUC → CENT"),
    _n("BC-REM", 2021, "CENT", "Binôme La République en marche ; REM → CENT"),
    _n("BC-UDI", 2021, "CENT", "Binôme UDI ; UDI → CENT (2020, antérieure)"),
    _n("BC-FI", 2021, "GAU", "Binôme La France insoumise ; FI → GAU (2020, antérieure)"),
    _n("BC-REG", 2021, "DIV", "Binôme régionaliste ; REG → AUT = DIV"),
    _n("BC-RDG", 2021, "GAU", "Binôme Parti radical de gauche ; RDG → GAU"),
    _n("BC-EXG", 2021, "EXG", "Binôme d'extrême gauche ; EXG → EXG"),
    _n("BC-EXD", 2021, "EXD", "Binôme d'extrême droite ; EXD → EXD"),
    _n("BC-MDM", 2021, "CENT", "Binôme MoDem ; MDM → CENT"),
    _n("BC-DSV", 2021, "DTE", "Binôme droite souverainiste ; DLF → DTE (2020), DSV → DTE (2026)"),
    _n("BC-GJ", 2021, "DIV", "Binôme Gilets jaunes ; LGJ → AUT = DIV"),
    _n("BC-UCD", 2021, "DTE", "Binôme d'union du centre et de la droite ; LUD → DTE (Q5)"),
    _n(
        "BC-UCG",
        2021,
        "DIV",
        "Binôme d'union du centre et de la gauche, entente sans équivalent dans les grilles ; "
        "DIV comme LGC 2008 (Q6)",
    ),
    _n(
        "BC-ECO",
        2021,
        "GAU",
        "Binôme écologiste incluant EELV (aucun code BC-VEC en 2021) → GAU, sens de l'époque "
        "comme ECO législatives 2017/2022 (Q7)",
    ),
    _n(
        "BC-UXD",
        2021,
        "EXD",
        "Binôme d'union de l'extrême droite ; absent de la grille 2020, grille suivante LUXD → EXD",
        _SRC_2023,
    ),
    # ── Européennes 2024 (14 codes, grille antérieure la plus proche : 2023) ──
    _n("LRN", 2024, "EXD", "Liste du Rassemblement national ; LRN → EXD", _SRC_2023),
    _n("LENS", 2024, "CENT", "Liste Ensemble (Besoin d'Europe) ; LENS → Centre", _SRC_2023),
    _n(
        "LUG",
        2024,
        "GAU",
        "Liste d'union de la gauche (PS-Place publique) ; LUG → Gauche",
        _SRC_2023,
    ),
    _n(
        "LFI",
        2024,
        "GAU",
        "Liste La France insoumise ; FI → Gauche (2023) ; EXG seulement en 2026 (INTP2602966C), "
        "cohérent FI législatives 2024",
        _SRC_2023,
    ),
    _n("LLR", 2024, "DTE", "Liste Les Républicains ; LR → Droite", _SRC_2023),
    _n("LVEC", 2024, "GAU", "Liste Les Écologistes ; VEC → Gauche", _SRC_2023),
    _n("LREC", 2024, "EXD", "Liste Reconquête ; REC → EXD", _SRC_2023),
    _n("LDIV", 2024, "DIV", "Liste divers ; DIV → Autres = DIV", _SRC_2023),
    _n("LCOM", 2024, "GAU", "Liste du Parti communiste ; COM → Gauche", _SRC_2023),
    _n("LDVD", 2024, "DTE", "Liste divers droite (Alliance rurale) ; DVD → Droite", _SRC_2023),
    _n(
        "LECO", 2024, "DIV", "Liste écologiste hors Les Écologistes ; ECO → Autres = DIV", _SRC_2023
    ),
    _n("LEXD", 2024, "EXD", "Liste d'extrême droite ; EXD → EXD", _SRC_2023),
    _n("LEXG", 2024, "EXG", "Liste d'extrême gauche ; EXG → EXG", _SRC_2023),
    _n("LDVG", 2024, "GAU", "Liste divers gauche ; DVG → Gauche", _SRC_2023),
]

# Codes sans bloc restant dans les scrutins vague B (non classés, volume négligeable) :
# résidus des européennes 2009 (codes 2004 réapparus, 11 voix au total).
_CODES_VAGUE_B_NON_CLASSES: frozenset[tuple[str, int]] = frozenset(
    {("LPC", 2009), ("LDD", 2009), ("LDV", 2009)}
)

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
        "Nuance DVDR — DLF → DTE : INTA1931378J p. 10 (CE n° 437675 a suspendu DLF → EXD)",
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
        "Nuance DVDR — DLF → DTE : INTA1931378J p. 10 (CE n° 437675 a suspendu DLF → EXD)",
    ),
    (2022, "HIDALGO", "Anne", "Parti Socialiste", "GAU", "Anne Hidalgo", "PS — nuance PS → GAU"),
    (
        2022,
        "JADOT",
        "Yannick",
        "EELV",
        "GAU",
        "Yannick Jadot",
        "EELV (nuance ECO en 2022, INTA2212053C) → GAU : EELV = VEC → GAU dans les "
        "grilles INTA1931378J (2020), IOMA2322276J (2023) et INTP2602966C (2026) (ADR-0010)",
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


# ── Listes européennes 2019 (nuance NULL dans la source, gotcha n° 9) ─────────
# Validé par Mathias le 2026-10-07 : résolution comme les présidentielles 2017/2022, par jointure
# sur le nom (resultats_candidats.nom = nom_tete_liste de la source, ex. « BARDELLA Jordan »).
# Grille la plus proche : INTA1931378J (2020, postérieure de 9 mois) ; ADR-0010 règle 2.
# Philippot → EXD et Vauclin → DIV : décision Mathias 2026-10-07 (Q8).
_SRC_EURO_2019 = f"{_SRC_2020} ; ADR-0010 règle 2 ; décision Mathias 2026-10-07"


def _l19(
    nom: str, prenom: str, parti: str, bloc: str, motif: str
) -> tuple[int, str, str, str, str, str, str]:
    """Entrée candidats_presidentielle pour une liste européenne 2019."""
    return (
        2019,
        f"{nom} {prenom}",
        prenom,
        parti,
        bloc,
        f"{prenom} {nom.title()}",
        f"{motif} ({_SRC_EURO_2019})",
    )


_LISTES_EURO_2019: list[tuple[int, str, str, str, str, str, str]] = [
    _l19("BARDELLA", "Jordan", "RN", "EXD", "Rassemblement national ; LRN → EXD"),
    _l19("LOISEAU", "Nathalie", "LREM-MoDem", "CENT", "Renaissance (LREM-MoDem) ; LREM → CENT"),
    _l19("JADOT", "Yannick", "EELV", "GAU", "Europe Écologie ; LVEC → GAU, ADR-0010 (c)"),
    _l19("BELLAMY", "François-Xavier", "LR", "DTE", "Union droite-centre (LR) ; LLR → DTE"),
    _l19("AUBRY", "Manon", "LFI", "GAU", "La France insoumise ; LFI → GAU (2020)"),
    _l19("GLUCKSMANN", "Raphaël", "PS-Place publique", "GAU", "Envie d'Europe (PS) ; LSOC → GAU"),
    _l19("DUPONT-AIGNAN", "Nicolas", "DLF", "DTE", "Debout la France ; LDLF → DTE"),
    _l19("HAMON", "Benoît", "Génération.s", "GAU", "Liste citoyenne (Génération.s) ; LDVG → GAU"),
    _l19("LAGARDE", "Jean-Christophe", "UDI", "CENT", "Les Européens (UDI) ; LUDI → CENT"),
    _l19("BROSSAT", "Ian", "PCF", "GAU", "Parti communiste ; LCOM → GAU"),
    _l19(
        "THOUY",
        "Hélène",
        "Parti animaliste",
        "DIV",
        "Parti animaliste ; LECO → AUT (le parti animaliste relève d'ECO, INTA2212053C ; "
        "LDIV aux européennes 2024)",
    ),
    _l19("BOURG", "Dominique", "Urgence écologie", "DIV", "Écologiste hors EELV ; LECO → AUT"),
    _l19(
        "ASSELINEAU",
        "François",
        "UPR",
        "DIV",
        "UPR (Frexit) ; LDIV → AUT, même formation nuancée LDIV aux européennes 2024 (Q9)",
    ),
    _l19("ARTHAUD", "Nathalie", "LO", "EXG", "Lutte ouvrière ; LEXG → EXG"),
    _l19("LALANNE", "Francis", "Alliance jaune", "DIV", "Gilets jaunes ; LGJ → AUT = DIV"),
    _l19(
        "BIDOU", "Olivier", "Les oubliés de l'Europe", "DIV", "Liste sans rattachement ; LDIV → AUT"
    ),
    _l19("MARIE", "Florie", "Parti pirate", "DIV", "Parti pirate ; LDIV → AUT, LDIV en 2024"),
    _l19("AZERGUI", "Nagib", "UDMF", "DIV", "UDMF ; LDIV → AUT, LDIV en 2024 (Free Palestine)"),
    _l19("DIEUMEGARD", "Pierre", "Espéranto", "DIV", "Espéranto ; LDIV → AUT, LDIV en 2024"),
    _l19(
        "GERNIGON",
        "Yves",
        "Parti fédéraliste européen",
        "DIV",
        "Liste sans rattachement ; LDIV → AUT",
    ),
    _l19("DELFEL", "Thérèse", "Décroissance", "DIV", "Écologiste hors EELV ; LECO → AUT"),
    _l19("CAILLAUD", "Sophie", "Allons enfants", "DIV", "Liste sans rattachement ; LDIV → AUT"),
    _l19("TOMASINI", "Nathalie", "À voix égales", "DIV", "Liste sans rattachement ; LDIV → AUT"),
    _l19("ALEXANDRE", "Audric", "PACE", "DIV", "PACE ; LDIV → AUT, LDIV en 2024"),
    _l19("HELGEN", "Gilles", "Initiative citoyenne", "DIV", "Liste sans rattachement ; LDIV → AUT"),
    _l19("PERSON", "Christian Luc", "UDLEF", "DIV", "Liste sans rattachement ; LDIV → AUT"),
    _l19(
        "DE PREVOISIN",
        "Robert",
        "Une France royale",
        "DTE",
        "Royaliste ; même tête de liste nuancée LDVD aux européennes 2014 ; LDVD → DTE",
    ),
    _l19(
        "TRAORÉ",
        "Hamada",
        "Démocratie représentative",
        "DIV",
        "Liste sans rattachement ; LDIV → AUT, LDIV en 2024",
    ),
    _l19(
        "CHALENÇON", "Christophe", "Évolution citoyenne", "DIV", "Gilets jaunes ; LGJ → AUT = DIV"
    ),
    _l19(
        "CAMUS",
        "Renaud",
        "La ligne claire",
        "EXD",
        "Même tête de liste nuancée LEXD aux européennes 2014 ; LEXD → EXD",
    ),
    _l19(
        "SANCHEZ",
        "Antonio",
        "Parti révolutionnaire Communistes",
        "EXG",
        "Même formation nuancée LEXG aux européennes 2024 ; LEXG → EXG",
    ),
    _l19(
        "CORBET",
        "Cathy Denise Ginette",
        "Neutre et actif",
        "DIV",
        "Liste sans rattachement ; LDIV → AUT",
    ),
    _l19(
        "PHILIPPOT",
        "Florian",
        "Les Patriotes",
        "EXD",
        "Souverainiste nationaliste (ex-FN) ; LEXD → EXD (Q8)",
    ),
    _l19(
        "VAUCLIN",
        "Vincent",
        "Liste de la reconquête",
        "DIV",
        "Liste sans rattachement à une formation de la grille ; LDIV → AUT (Q8)",
    ),
]


# ── Création du schéma ────────────────────────────────────────────────────────


def create_nuances_harmonisees(con: duckdb.DuckDBPyConnection) -> None:
    """Crée la table (nuance, annee) → bloc. Idempotent ; partagée avec le module Législatif."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS nuances_harmonisees (
            nuance VARCHAR NOT NULL,
            annee  INTEGER NOT NULL,
            bloc   VARCHAR NOT NULL,
            PRIMARY KEY (nuance, annee)
        )
    """)
    # Migration D1.2 : justification courte du bloc, sur le modèle de candidats_presidentielle
    con.execute("ALTER TABLE nuances_harmonisees ADD COLUMN IF NOT EXISTS source_bloc VARCHAR")


def create_elections_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 6 tables électorales. Idempotent (CREATE TABLE IF NOT EXISTS).

    resultats_participation et resultats_candidats n'ont pas de clé primaire (décision
    Mathias 2026-10-07 : l'index pesait ~1,1 Go en France entière) ; l'unicité est
    contrôlée au chargement (loaders.elections_agregees.verifier_unicite_resultats).
    """
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
            exprimes         INTEGER
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
            voix             INTEGER
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

    create_nuances_harmonisees(con)

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

    # Vague B (2026-10-07) : rattachement des communes fusionnées (code d'origine conservé)
    con.execute(PASSAGE_DDL)
    for table in CLES_RESULTATS:
        con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS code_commune_origine VARCHAR(5)")
    # Vague B (2026-10-07) : lignes de la source non chargées, par scrutin et catégorie
    con.execute(ECARTS_DDL)

    # Migration D1.2 : nouvelles colonnes pour les scrutins législatifs
    con.execute(
        "ALTER TABLE elections ADD COLUMN IF NOT EXISTS ancien_decoupage BOOLEAN DEFAULT FALSE"
    )
    con.execute("ALTER TABLE resultats_participation ADD COLUMN IF NOT EXISTS code_circo VARCHAR")

    logger.info("Schéma électoral créé/vérifié : 6 tables")


# Lignes de la source écartées au chargement (commune absente de geographies_communes)
ECARTS_DDL = """
    CREATE TABLE IF NOT EXISTS elections_ecarts_chargement (
        id_election    VARCHAR NOT NULL,
        perimetre      VARCHAR NOT NULL,
        categorie      VARCHAR NOT NULL,  -- etranger | pacifique | reste
        nb_communes    INTEGER,
        nb_bv          INTEGER,
        exprimes       BIGINT,
        exprimes_total BIGINT,            -- exprimés de la source sur le périmètre
        pct_exprimes   DOUBLE
    )
"""

# Communes fusionnées → commune actuelle (INSEE COG, etl/loaders/communes_passage.py)
PASSAGE_DDL = """
    CREATE TABLE IF NOT EXISTS communes_passage (
        code_ancien    VARCHAR(5) PRIMARY KEY,
        code_actuel    VARCHAR(5) NOT NULL,
        date_effet     DATE,         -- date de la dernière fusion de la chaîne
        type_evenement VARCHAR       -- code MOD INSEE de cette fusion
    )
"""


# Clés logiques des tables de résultats (unicité contrôlée au chargement, sans index)
CLES_RESULTATS: dict[str, tuple[str, ...]] = {
    "resultats_participation": ("id_election", "code_departement", "code_commune", "code_bv"),
    "resultats_candidats": (
        "id_election",
        "code_departement",
        "code_commune",
        "code_bv",
        "no_panneau",
    ),
}


def retirer_cles_primaires_resultats(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Reconstruit sans clé primaire les tables de résultats qui en ont une. Idempotent.

    DuckDB ne sait pas supprimer une contrainte : copie (CREATE TABLE AS), suppression de
    l'ancienne table, renommage, puis NOT NULL rétabli sur les colonnes de la clé, dans
    une transaction. Les vues, liées par nom, restent valides. Retourne les tables
    reconstruites.
    """
    reconstruites: list[str] = []
    for table, cles in CLES_RESULTATS.items():
        n_pk = ligne_unique(
            con.execute(
                "SELECT COUNT(*) FROM duckdb_constraints() "
                "WHERE table_name = ? AND constraint_type = 'PRIMARY KEY'",
                [table],
            )
        )[0]
        if not n_pk:
            continue
        con.execute("BEGIN TRANSACTION")
        try:
            n_avant = ligne_unique(con.execute(f"SELECT COUNT(*) FROM {table}"))[0]  # noqa: S608
            con.execute(f"CREATE TABLE {table}__sans_pk AS SELECT * FROM {table}")  # noqa: S608
            con.execute(f"DROP TABLE {table}")
            con.execute(f"ALTER TABLE {table}__sans_pk RENAME TO {table}")
            for col in cles:
                con.execute(f"ALTER TABLE {table} ALTER COLUMN {col} SET NOT NULL")
            n_apres = ligne_unique(con.execute(f"SELECT COUNT(*) FROM {table}"))[0]  # noqa: S608
            if n_apres != n_avant:
                raise RuntimeError(
                    f"{table} : {n_avant} lignes avant reconstruction, {n_apres} après"
                )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        reconstruites.append(table)
        logger.info("%s reconstruite sans clé primaire", table)
    return reconstruites


# ── Population des référentiels ───────────────────────────────────────────────


def populate_elections_referentiels(con: duckdb.DuckDBPyConnection) -> None:
    """Remplit les 4 tables de référence. Idempotent (DELETE + INSERT).

    nuances_harmonisees est réinitialisée avec ses trois jeux (présidentielles,
    législatives, municipales) : relancer cette fonction ne perd plus les nuances
    municipales (correctif C2, audit 2026-09-24).

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
    # (2002/2007/2012/2017/2022/2024) + municipales (2008/2014/2020/2026).
    # Chaque entrée porte sa justification (source_bloc).
    _verifier_nuances_municipales()
    nuances = _NUANCES_PRES + _NUANCES_LEGI + _NUANCES_MUNI + _NUANCES_EURO_REGI_DPMT
    if nuances:
        con.executemany(
            "INSERT INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) VALUES (?, ?, ?, ?)",
            nuances,
        )
    logger.info(
        "nuances_harmonisees : %d entrées (%d pres + %d legi + %d muni + %d euro/regi/dpmt)",
        len(nuances),
        len(_NUANCES_PRES),
        len(_NUANCES_LEGI),
        len(_NUANCES_MUNI),
        len(_NUANCES_EURO_REGI_DPMT),
    )

    # candidats_presidentielle (présidentielles sans nuances : 2017, 2022)
    # + listes européennes 2019 (nuance NULL aussi, même mécanisme de jointure sur nom)
    candidats = _CANDIDATS_PRES_2017 + _CANDIDATS_PRES_2022 + _LISTES_EURO_2019
    if candidats:
        con.executemany(
            """INSERT INTO candidats_presidentielle
               (annee, nom, prenom, parti, bloc, libelle, source_bloc)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            candidats,
        )
    logger.info(
        "candidats_presidentielle : %d entrées (pres 2017 + 2022, euro 2019)", len(candidats)
    )


def _verifier_nuances_municipales() -> None:
    """Garde-fous sur _NUANCES_MUNI avant écriture en base.

    - NC, LNC doivent rester absents (bloc NULL, décision ADR-0005).
    - Les années municipales doivent être disjointes des années pres/legi, sinon le
      DELETE ciblé de populate_nuances_municipales toucherait d'autres scrutins.
    """
    codes = {nuance for nuance, _, _, _ in _NUANCES_MUNI}
    interdits = codes & _CODES_MUNI_SANS_MAPPING
    if interdits:
        raise RuntimeError(
            f"Codes sans mapping détectés dans _NUANCES_MUNI : {sorted(interdits)}. "
            "Ces codes doivent rester absents de nuances_harmonisees."
        )
    annees_autres = {
        annee for _, annee, _, _ in _NUANCES_PRES + _NUANCES_LEGI + _NUANCES_EURO_REGI_DPMT
    }
    chevauchement = set(_ANNEES_MUNI) & annees_autres
    if chevauchement:
        raise RuntimeError(
            f"Années municipales partagées avec pres/legi/euro/regi/dpmt : {sorted(chevauchement)}. "
            "Le remplacement ciblé par année n'est plus sûr (voir audit M5)."
        )


def populate_nuances_municipales(con: duckdb.DuckDBPyConnection) -> int:
    """Remplace les nuances municipales de nuances_harmonisees. Idempotent et correcteur.

    DELETE ciblé sur les années municipales puis INSERT de _NUANCES_MUNI, dans une
    transaction : une correction de bloc ou de source_bloc dans le code est appliquée
    à la relance, et une nuance retirée de la liste disparaît de la base
    (correctif C3, audit 2026-09-24). Les nuances pres/legi ne sont pas touchées.

    Retourne le nombre d'entrées municipales présentes après l'opération.
    """
    _verifier_nuances_municipales()
    placeholders = ", ".join("?" for _ in _ANNEES_MUNI)
    con.execute("BEGIN TRANSACTION")
    try:
        n_supprimees = ligne_unique(
            con.execute(
                f"DELETE FROM nuances_harmonisees WHERE annee IN ({placeholders})",  # noqa: S608
                list(_ANNEES_MUNI),
            )
        )[0]
        con.executemany(
            "INSERT INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) VALUES (?, ?, ?, ?)",
            _NUANCES_MUNI,
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    logger.info(
        "nuances_harmonisees (muni %s) : %d entrées remplacées par %d",
        "/".join(str(a) for a in _ANNEES_MUNI),
        n_supprimees,
        len(_NUANCES_MUNI),
    )
    return len(_NUANCES_MUNI)


def populate_nuances_vague_b(con: duckdb.DuckDBPyConnection) -> int:
    """Insère ou remplace les nuances euro/regi/dpmt et les listes européennes 2019.

    INSERT OR REPLACE ciblé sur les clés de _NUANCES_EURO_REGI_DPMT et _LISTES_EURO_2019 :
    ne touche ni les autres nuances ni les autres candidats. Un code retiré de la liste
    ne disparaît qu'au prochain populate_elections_referentiels (remise à plat complète).
    Retourne le nombre d'entrées nuances écrites.
    """
    _verifier_nuances_municipales()
    con.executemany(
        "INSERT OR REPLACE INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) "
        "VALUES (?, ?, ?, ?)",
        _NUANCES_EURO_REGI_DPMT,
    )
    con.executemany(
        """INSERT OR REPLACE INTO candidats_presidentielle
           (annee, nom, prenom, parti, bloc, libelle, source_bloc)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        _LISTES_EURO_2019,
    )
    logger.info(
        "nuances vague B : %d nuances, %d listes européennes 2019",
        len(_NUANCES_EURO_REGI_DPMT),
        len(_LISTES_EURO_2019),
    )
    return len(_NUANCES_EURO_REGI_DPMT)


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
    con.execute(f"""
        CREATE OR REPLACE VIEW v_evolution_blocs_hdf_legi AS
        SELECT
            annee,
            tour,
            ancien_decoupage,
            bloc,
            SUM(voix) AS voix_total
        FROM v_scores_circo_legi
        -- Filtre explicite (vague B) : la base peut contenir la France entière
        WHERE split_part(code_circo, '-', 1) IN ({DEPTS_HDF_SQL})
        GROUP BY annee, tour, ancien_decoupage, bloc
        ORDER BY annee, tour, bloc
    """)  # noqa: S608

    logger.info("Vues d'agrégation créées/mises à jour : 8 vues")


# ── Vues municipales (ex-migration 0007) ─────────────────────────────────────


def _create_v_scores_commune_muni(con: duckdb.DuckDBPyConnection) -> None:
    """Voix agrégés par bloc et commune — 1 ligne par (annee, tour, commune, bloc).

    bloc = NULL pour les nuances sans mapping (NC, LNC, nuance=NULL).
    pct_exprimes = NULL quand bloc IS NULL : les communes plurinominales (< 1000 hab)
    ont une sémantique voix candidat (non additive), ce qui rendrait le % faux.
    Pour les blocs nommés (scrutin de liste ≥ seuil), pct = voix / exprimes_commune.
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_scores_commune_muni AS
        WITH exprimes_commune AS (
            SELECT rp.id_election, rp.code_commune, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
            GROUP BY rp.id_election, rp.code_commune
        )
        SELECT
            e.annee,
            e.tour,
            rc.code_commune,
            nh.bloc,
            SUM(rc.voix)                                                          AS voix,
            CASE WHEN nh.bloc IS NOT NULL
                 THEN ROUND(100.0 * SUM(rc.voix) / NULLIF(MAX(ex.exprimes), 0), 2)
                 ELSE NULL END                                                    AS pct_exprimes
        FROM resultats_candidats rc
        JOIN elections e
            ON e.id_election = rc.id_election
        LEFT JOIN nuances_harmonisees nh
            ON nh.nuance = rc.nuance AND nh.annee = e.annee
        JOIN exprimes_commune ex
            ON ex.id_election = rc.id_election AND ex.code_commune = rc.code_commune
        WHERE e.type_scrutin = 'muni'
        GROUP BY e.annee, e.tour, rc.code_commune, nh.bloc
    """)
    logger.info("Vue v_scores_commune_muni créée/mise à jour")


def _create_v_evolution_blocs_hdf_muni(con: duckdb.DuckDBPyConnection) -> None:
    """Évolution temporelle des blocs sur l'ensemble HdF.

    Filtre explicite sur les 5 départements (vague B : la base peut contenir la France).

    1 ligne par (annee, tour, bloc). voix = SUM(rc.voix) par bloc.
    pct_exprimes = voix_bloc / exprimes_HdF * 100, SEULEMENT pour les blocs nommés.
    Pour bloc=NULL (NC/plurinominal), pct_exprimes=NULL : les communes < 1000 hab
    ont un scrutin plurinominal (voix candidat ≠ voix liste), ce qui rend le %
    non comparable avec les blocs politiques des communes ≥ seuil.
    """
    con.execute(f"""
        CREATE OR REPLACE VIEW v_evolution_blocs_hdf_muni AS
        WITH exprimes_hdf AS (
            SELECT rp.id_election, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
              AND rp.code_departement IN ({DEPTS_HDF_SQL})
            GROUP BY rp.id_election
        ),
        blocs_hdf AS (
            SELECT
                e.id_election,
                e.annee,
                e.tour,
                nh.bloc,
                SUM(rc.voix) AS voix
            FROM resultats_candidats rc
            JOIN elections e
                ON e.id_election = rc.id_election
            LEFT JOIN nuances_harmonisees nh
                ON nh.nuance = rc.nuance AND nh.annee = e.annee
            WHERE e.type_scrutin = 'muni'
              AND rc.code_departement IN ({DEPTS_HDF_SQL})
            GROUP BY e.id_election, e.annee, e.tour, nh.bloc
        )
        SELECT
            bh.annee,
            bh.tour,
            bh.bloc,
            bh.voix,
            CASE WHEN bh.bloc IS NOT NULL
                 THEN ROUND(100.0 * bh.voix / NULLIF(ex.exprimes, 0), 2)
                 ELSE NULL END AS pct_exprimes
        FROM blocs_hdf bh
        JOIN exprimes_hdf ex ON ex.id_election = bh.id_election
        ORDER BY bh.annee, bh.tour, bh.bloc
    """)  # noqa: S608
    logger.info("Vue v_evolution_blocs_hdf_muni créée/mise à jour")


# Scrutins dont no_panneau est synthétique (NULL dans le Parquet source, ROW_NUMBER par BV
# au chargement, ADR-0005) : il n'identifie pas une liste d'un BV à l'autre.
_ANNEES_NO_PANNEAU_SYNTHETIQUE: tuple[int, ...] = (2008,)


def _create_v_listes_commune_muni(con: duckdb.DuckDBPyConnection) -> None:
    """Détail liste par liste par commune — clé pour le drill-down D3.3.

    1 ligne par liste : (annee, tour, commune, no_panneau). no_panneau est le numéro
    de panneau officiel, identique dans tous les BV d'une commune ; dans les communes
    au scrutin plurinominal, une ligne = un candidat.

    Cas 2008 (no_panneau synthétique, variable d'un BV à l'autre) : no_panneau = NULL
    dans la vue et la liste est identifiée par (nuance, libellés, tête de liste).
    Limite résiduelle : deux listes 2008 de même nuance sans libellé ni tête de liste
    restent fusionnées (information absente de la source).

    Correctif C1 (audit 2026-09-24) : la vue groupait par nuance, fusionnant les listes
    de même nuance (voix additionnées, tête de liste arbitraire).
    bloc = NULL pour nuances sans mapping (NC, LNC).
    pct_exprimes = voix_liste / exprimes_commune * 100 (NULL si bloc NULL).
    """
    annees_synth = ", ".join(str(a) for a in _ANNEES_NO_PANNEAU_SYNTHETIQUE)
    con.execute(f"""
        CREATE OR REPLACE VIEW v_listes_commune_muni AS
        WITH exprimes_commune AS (
            SELECT rp.id_election, rp.code_commune, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
            GROUP BY rp.id_election, rp.code_commune
        ),
        lignes AS (
            SELECT
                rc.id_election,
                e.annee,
                e.tour,
                rc.code_commune,
                CASE WHEN e.annee IN ({annees_synth}) THEN NULL
                     ELSE rc.no_panneau END AS no_panneau,
                rc.nuance,
                nh.bloc,
                rc.libelle_abrege_liste,
                rc.libelle_etendu_liste,
                rc.nom_tete_liste,
                rc.prenom_tete_liste,
                rc.code_commune_origine,
                rc.voix
            FROM resultats_candidats rc
            JOIN elections e
                ON e.id_election = rc.id_election
            LEFT JOIN nuances_harmonisees nh
                ON nh.nuance = rc.nuance AND nh.annee = e.annee
            WHERE e.type_scrutin = 'muni'
        )
        SELECT
            l.annee,
            l.tour,
            l.code_commune,
            l.no_panneau,
            l.nuance,
            l.bloc,
            MAX(l.libelle_abrege_liste) AS libelle_abrege_liste,
            MAX(l.libelle_etendu_liste) AS libelle_etendu_liste,
            MAX(l.nom_tete_liste)       AS nom_tete_liste,
            MAX(l.prenom_tete_liste)    AS prenom_tete_liste,
            SUM(l.voix)                 AS voix,
            CASE WHEN l.bloc IS NOT NULL
                 THEN ROUND(100.0 * SUM(l.voix) / NULLIF(MAX(ex.exprimes), 0), 2)
                 ELSE NULL END          AS pct_exprimes
        FROM lignes l
        JOIN exprimes_commune ex
            ON ex.id_election = l.id_election AND ex.code_commune = l.code_commune
        GROUP BY
            l.annee, l.tour, l.code_commune, l.no_panneau, l.nuance, l.bloc,
            -- commune absorbée depuis (rattachement COG) : ses listes restent distinctes
            l.code_commune_origine,
            -- 2008 (no_panneau NULL) : la liste est identifiée par ses descripteurs
            CASE WHEN l.no_panneau IS NULL THEN l.libelle_abrege_liste END,
            CASE WHEN l.no_panneau IS NULL THEN l.libelle_etendu_liste END,
            CASE WHEN l.no_panneau IS NULL THEN l.nom_tete_liste END,
            CASE WHEN l.no_panneau IS NULL THEN l.prenom_tete_liste END
    """)  # noqa: S608
    logger.info("Vue v_listes_commune_muni créée/mise à jour")


def create_municipales_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 3 vues municipales (anciennement dans la migration 0007). Idempotent."""
    _create_v_scores_commune_muni(con)
    _create_v_evolution_blocs_hdf_muni(con)
    _create_v_listes_commune_muni(con)
