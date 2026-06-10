"""Chargement filtré des résultats municipaux (HdF, 2008-2026).

Usage :
    uv run python scripts/load_elections_municipales.py

Filtre :
- Région Hauts-de-France (code_region = '32'), 5 départements : 02, 59, 60, 62, 80
- Municipales uniquement : type_scrutin = 'muni' dans la table elections
- 8 scrutins : 2008, 2014, 2020, 2026 (t1 + t2)

Granularité : bureau de vote (granularité fine de la source).
Idempotent : DELETE + INSERT sur les municipales uniquement, sans toucher
aux présidentielles, législatives ni autres scrutins.

Mapping Parquet (ATTENTION nommage inversé dans la source) :
- 'general-results.parquet'   → résultats par liste → resultats_candidats
- 'candidats-results.parquet' → participation       → resultats_participation

Spécificités municipales :
- Pas de code_circo (NULL pour tous les BV)
- nom/prenom = NULL (scrutin de liste, pas de candidat individuel)
- prenom_tete_liste absent du Parquet → NULL
- Colonnes liste/libelle_abrege_liste/libelle_etendu_liste/nom_tete_liste : lecture directe
- 2020_muni_t2 : date 28 juin 2020 (reporté COVID, pas 22 mars)
- 2008 : 164 communes HdF nuancées (seuil ≥ 3 500 hab — normal, pas un bug)
- 2026 : ~320 communes HdF nuancées (seuil ≥ 3 500 hab), ~3 459 avec nuance NULL

Nuances harmonisées :
- 67 entrées insérées (2008 : 12, 2014 : 17, 2020 : 19, 2026 : 19)
- SANS mapping (bloc NULL, UI : Non classé / Liste sortante) : NC, LMAJ, LNC
- LFI 2020 = GAU ; LFI 2026 = EXG (bascule structurante INTP2602966C + CE 512694)
- LCMD 2008 = GAU (analyse contextuelle — libellés Parquet NULL, bassin minier HdF)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"
_PARQUET_CANDIDATS = ROOT / "data" / "exploration" / "general-results.parquet"
_PARQUET_PARTICIPATION = ROOT / "data" / "exploration" / "candidats-results.parquet"

_MUNI_FILTER = "type_scrutin = 'muni'"
_MUNI_IDS = f"(SELECT id_election FROM elections WHERE {_MUNI_FILTER})"

# 67 entrées nuances municipales (nuance, annee, bloc, source_bloc)
# Codes SANS mapping (non insérés) : NC (2014/2020), LMAJ (2008), LNC (2020)
_NUANCES_MUNI: list[tuple[str, int, str, str]] = [
    # ── 2008 — seuil 3 500 hab — 164 communes HdF nuancées ───────────────────
    ("LAUT", 2008, "DIV", "Autre — liste inclassable (D3.2)"),
    (
        "LCMD",
        2008,
        "GAU",
        "Communiste et Divers — analyse contextuelle, libellés Parquet NULL, "
        "bassin minier HdF ; cohérence avec LDVG/LSOC (D3.2, LCMD→GAU validé)",
    ),
    ("LCOM", 2008, "EXG", "Communiste — PCF (D3.2)"),
    ("LDVD", 2008, "DTE", "Divers Droite (D3.2)"),
    ("LDVG", 2008, "GAU", "Divers Gauche (D3.2)"),
    ("LEXG", 2008, "EXG", "Extrême gauche (D3.2)"),
    ("LFN", 2008, "EXD", "Front National (D3.2)"),
    ("LGC", 2008, "DIV", "Gauche-Centre local — 5 occurrences, trop peu pour classifier (D3.2)"),
    ("LMC", 2008, "CENT", "Majorité-Centre — UDF sphère 2008 (D3.2)"),
    ("LSOC", 2008, "GAU", "Socialiste (D3.2)"),
    ("LUG", 2008, "GAU", "Union de la Gauche (D3.2)"),
    ("LVEC", 2008, "GAU", "Verts / Écologistes (D3.2)"),
    # LMAJ (543 occurrences) : non inséré — liste de la majorité sortante,
    # indique le statut et non l'orientation idéologique (D3.2, Q1 validé)
    # ── 2014 — seuil 1 000 hab — ~3 778 communes HdF nuancées ────────────────
    ("LCOM", 2014, "EXG", "Communiste — PCF (D3.2)"),
    ("LDIV", 2014, "DIV", "Divers (D3.2)"),
    ("LDVD", 2014, "DTE", "Divers Droite (D3.2)"),
    ("LDVG", 2014, "GAU", "Divers Gauche (D3.2)"),
    ("LEXD", 2014, "EXD", "Extrême droite (D3.2)"),
    ("LEXG", 2014, "EXG", "Extrême gauche (D3.2)"),
    (
        "LFG",
        2014,
        "GAU",
        "Front de Gauche (PCF + Parti de Gauche, 2012-2016) — "
        "GAU per ADR-0005 ; bascule EXG concerne LFI/Mélenchon en 2026 seulement (D3.2)",
    ),
    ("LFN", 2014, "EXD", "Front National (D3.2)"),
    ("LMDM", 2014, "CENT", "Mouvement Démocrate — MoDem (D3.2)"),
    (
        "LPG",
        2014,
        "GAU",
        "Parti de Gauche (Mélenchon, 2008-2016) — dans le Front de Gauche en 2014 ; "
        "GAU par cohérence avec LFG (D3.2)",
    ),
    ("LSOC", 2014, "GAU", "Socialiste (D3.2)"),
    ("LUC", 2014, "CENT", "Union Centre (D3.2)"),
    ("LUD", 2014, "CENT", "Union Démocratique / UDI (D3.2)"),
    ("LUDI", 2014, "DIV", "Union Divers (D3.2)"),
    ("LUG", 2014, "GAU", "Union de la Gauche (D3.2)"),
    ("LUMP", 2014, "DTE", "UMP (devenu LR en 2015) (D3.2)"),
    ("LVEC", 2014, "GAU", "Verts / EELV (D3.2)"),
    # NC (~45 281 occurrences HdF t1) : non inséré — Non Classé, indication
    # administrative pour listes sans investiture, pas un bloc idéologique (D3.2)
    # ── 2020 — seuil 3 500 hab — ~3 779 communes HdF nuancées ────────────────
    ("LCOM", 2020, "EXG", "Communiste — PCF (D3.2)"),
    ("LDIV", 2020, "DIV", "Divers (D3.2)"),
    (
        "LDVC",
        2020,
        "CENT",
        "Divers Centre — investiture officielle LREM/MoDem/UDI post-CE 31/01/2020 "
        "n°437675 (D3.2, LDVC→CENT validé par CE 437675)",
    ),
    ("LDVD", 2020, "DTE", "Divers Droite (D3.2)"),
    ("LDVG", 2020, "GAU", "Divers Gauche (D3.2)"),
    ("LECO", 2020, "GAU", "Écologiste — EELV principalement (D3.2)"),
    ("LEXD", 2020, "EXD", "Extrême droite (D3.2)"),
    ("LEXG", 2020, "EXG", "Extrême gauche (D3.2)"),
    (
        "LFI",
        2020,
        "GAU",
        "La France Insoumise 2020 — GAU per circulaire INTA1931378J ; "
        "bascule EXG uniquement à partir de 2026 (INTP2602966C + CE 27/02/2026 n°512694) (D3.2)",
    ),
    ("LLR", 2020, "DTE", "Les Républicains (D3.2)"),
    # LNC (~1 787 occurrences) : non inséré — parallèle structurel avec NC ;
    # identité LNC ambiguë (Nouveau Centre ou Liste Non Classée) → NULL (D3.2, Q9 validé)
    ("LRDG", 2020, "GAU", "Radicaux de Gauche — allié PS (D3.2)"),
    ("LREM", 2020, "CENT", "La République En Marche (D3.2)"),
    ("LRN", 2020, "EXD", "Rassemblement National (D3.2)"),
    ("LSOC", 2020, "GAU", "Socialiste (D3.2)"),
    ("LUC", 2020, "CENT", "Union Centre (D3.2)"),
    ("LUD", 2020, "CENT", "Union Démocratique / UDI (D3.2)"),
    ("LUDI", 2020, "DIV", "Union Divers (D3.2)"),
    ("LUG", 2020, "GAU", "Union de la Gauche (D3.2)"),
    ("LVEC", 2020, "GAU", "Verts / EELV (D3.2)"),
    # NC (~43 074 occurrences HdF t1) : non inséré — voir 2014 NC (D3.2)
    # ── 2026 — seuil 3 500 hab — ~318 communes HdF nuancées ──────────────────
    ("LCOM", 2026, "EXG", "Communiste — PCF (D3.2)"),
    ("LDIV", 2026, "DIV", "Divers (D3.2)"),
    ("LDVC", 2026, "CENT", "Divers Centre — per circulaire INTP2602966C (2 fév. 2026) (D3.2)"),
    ("LDVD", 2026, "DTE", "Divers Droite (D3.2)"),
    ("LDVG", 2026, "GAU", "Divers Gauche (D3.2)"),
    ("LECO", 2026, "GAU", "Écologiste (D3.2)"),
    ("LEXD", 2026, "EXD", "Extrême droite (D3.2)"),
    ("LEXG", 2026, "EXG", "Extrême gauche (D3.2)"),
    (
        "LFI",
        2026,
        "EXG",
        "La France Insoumise 2026 — EXG per circulaire INTP2602966C (2 fév. 2026) "
        "+ CE 27/02/2026 n°512694 (rejet recours LFI) (D3.2)",
    ),
    ("LHOR", 2026, "CENT", "Horizons — parti centriste Édouard Philippe (D3.2)"),
    ("LLR", 2026, "DTE", "Les Républicains (D3.2)"),
    ("LRN", 2026, "EXD", "Rassemblement National (D3.2)"),
    ("LSOC", 2026, "GAU", "Socialiste (D3.2)"),
    ("LUC", 2026, "CENT", "Union Centre (D3.2)"),
    ("LUDI", 2026, "DIV", "Union Divers (D3.2)"),
    (
        "LUDR",
        2026,
        "EXD",
        "Union Droite Républicaine (parti Ciotti, allié RN) — "
        "per INTP2602966C + CE 27/02/2026 n°512694 (D3.2)",
    ),
    ("LUG", 2026, "GAU", "Union de la Gauche / NFP (D3.2)"),
    ("LUXD", 2026, "EXD", "Union Extrême Droite (D3.2)"),
    ("LVEC", 2026, "GAU", "Verts / EELV (D3.2)"),
]

assert len(_NUANCES_MUNI) == 67, f"_NUANCES_MUNI : {len(_NUANCES_MUNI)} entrées (attendu 67)"


def _delete_municipales(con) -> None:
    """Supprime les lignes municipales existantes (idempotence)."""
    con.execute(f"DELETE FROM resultats_participation WHERE id_election IN {_MUNI_IDS}")
    con.execute(f"DELETE FROM resultats_candidats WHERE id_election IN {_MUNI_IDS}")
    logger.info("Nettoyage idempotent : municipales supprimées avant rechargement")


def _insert_nuances_harmonisees(con) -> int:
    """Insère les 67 nuances municipales. INSERT OR IGNORE pour ne pas écraser pres/legi."""
    # Vérification préalable : NC, LMAJ, LNC ne doivent PAS être insérés
    codes_sans_mapping = {"NC", "LMAJ", "LNC"}
    codes_a_inserer = {nuance for nuance, _, _, _ in _NUANCES_MUNI}
    intersection = codes_sans_mapping & codes_a_inserer
    if intersection:
        raise RuntimeError(
            f"Codes sans mapping détectés dans _NUANCES_MUNI : {intersection}. "
            "Ces codes doivent rester absents de nuances_harmonisees."
        )

    n_avant = con.execute("SELECT COUNT(*) FROM nuances_harmonisees").fetchone()[0]

    for nuance, annee, bloc, source_bloc in _NUANCES_MUNI:
        con.execute(
            "INSERT OR IGNORE INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) "
            "VALUES (?, ?, ?, ?)",
            [nuance, annee, bloc, source_bloc],
        )

    n_apres = con.execute("SELECT COUNT(*) FROM nuances_harmonisees").fetchone()[0]
    n_inserted = n_apres - n_avant
    logger.info(
        "nuances_harmonisees : %d entrées insérées (%d → %d total)", n_inserted, n_avant, n_apres
    )
    return n_inserted


def _load_participation(con) -> int:
    """Charge resultats_participation depuis candidats-results.parquet (HdF, muni).

    code_circo = NULL pour toutes les municipales (pas de circonscription).
    """
    parquet = str(_PARQUET_PARTICIPATION)
    con.execute(f"""
        INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv,
             inscrits, abstentions, votants, blancs, nuls, exprimes, code_circo)
        SELECT
            p.id_election,
            p.code_departement,
            p.code_commune,
            p.code_bv,
            p.inscrits,
            p.abstentions,
            p.votants,
            p.blancs,
            p.nuls,
            p.exprimes,
            NULL AS code_circo
        FROM '{parquet}' p
        INNER JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE gc.code_region = '32'
          AND p.id_election IN {_MUNI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_participation WHERE id_election IN {_MUNI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_participation : %d lignes chargées (muni HdF)", n)
    return n


def _load_candidats(con) -> int:
    """Charge resultats_candidats depuis general-results.parquet (HdF, muni).

    Colonnes spécifiques muni :
    - liste, libelle_abrege_liste, libelle_etendu_liste, nom_tete_liste : lecture directe Parquet
    - prenom_tete_liste : absent du Parquet → NULL
    - nom, prenom : NULL (scrutin de liste, pas de candidat individuel)

    Cas 2008 : no_panneau = NULL pour toutes les lignes dans le Parquet source.
    Résolution : ROW_NUMBER() OVER (PARTITION BY id_election, dpt, commune, bv
    ORDER BY nuance, voix DESC) comme numéro synthétique.
    Ces numéros sont arbitraires mais stables au sein d'un rechargement donné.
    """
    parquet = str(_PARQUET_CANDIDATS)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix,
             liste, libelle_abrege_liste, libelle_etendu_liste,
             nom_tete_liste, prenom_tete_liste)
        SELECT
            c.id_election,
            c.code_departement,
            c.code_commune,
            c.code_bv,
            COALESCE(
                c.no_panneau,
                CAST(ROW_NUMBER() OVER (
                    PARTITION BY c.id_election, c.code_departement, c.code_commune, c.code_bv
                    ORDER BY c.nuance, c.voix DESC
                ) AS INTEGER)
            ) AS no_panneau,
            c.nuance,
            c.sexe,
            NULL AS nom,
            NULL AS prenom,
            c.voix,
            c.liste,
            c.libelle_abrege_liste,
            c.libelle_etendu_liste,
            c.nom_tete_liste,
            NULL AS prenom_tete_liste
        FROM '{parquet}' c
        INNER JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE gc.code_region = '32'
          AND c.id_election IN {_MUNI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN {_MUNI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_candidats : %d lignes chargées (muni HdF)", n)
    return n


def _print_summary(con) -> None:
    """Affiche volumes par scrutin + vérifications clés."""
    rows = con.execute("""
        SELECT
            e.id_election,
            (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_bv,
            (SELECT COUNT(DISTINCT rp.code_commune) FROM resultats_participation rp
              WHERE rp.id_election = e.id_election) AS n_communes,
            (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_listes
        FROM elections e
        WHERE e.type_scrutin = 'muni'
        ORDER BY e.id_election
    """).fetchall()

    print("\n── Résumé par scrutin (municipales HdF) ──────────────────────────────────")
    print(f"  {'id_election':<17s} {'BV':>7s} {'communes':>9s} {'listes':>8s}")
    for idel, n_bv, n_com, n_list in rows:
        print(f"  {idel:<17s} {n_bv:>7,} {n_com:>9,} {n_list:>8,}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Vérification LFI bascule
    lfi_rows = con.execute(
        "SELECT nuance, annee, bloc FROM nuances_harmonisees WHERE nuance='LFI' ORDER BY annee"
    ).fetchall()
    print("\n── Vérification LFI bascule ──────────────────────────────────────────────")
    for r in lfi_rows:
        print(f"  LFI {r[1]} → {r[2]}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Vérification codes sans mapping
    absent_ok = []
    for code in ("NC", "LMAJ", "LNC"):
        n = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE nuance = ? AND annee IN (2008,2014,2020,2026)",
            [code],
        ).fetchone()[0]
        absent_ok.append((code, n))
    print("\n── Codes sans mapping (attendu 0 entrée) ─────────────────────────────────")
    for code, n in absent_ok:
        status = "✓ absent" if n == 0 else f"✗ ERREUR {n} entrées"
        print(f"  {code:<6s} : {status}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Total nuances_harmonisees
    n_total = con.execute("SELECT COUNT(*) FROM nuances_harmonisees").fetchone()[0]
    n_muni = con.execute(
        "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee IN (2008,2014,2020,2026)"
    ).fetchone()[0]
    print(f"\n  nuances_harmonisees total : {n_total} (dont {n_muni} municipales)")


def main() -> None:
    for p in (_PARQUET_PARTICIPATION, _PARQUET_CANDIDATS):
        if not p.exists():
            logger.error("Parquet manquant : %s", p)
            sys.exit(1)

    logger.info("Chargement municipales HdF → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        _delete_municipales(con)
        _insert_nuances_harmonisees(con)
        _load_participation(con)
        _load_candidats(con)
        _print_summary(con)
        print("\nChargement municipales terminé.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
