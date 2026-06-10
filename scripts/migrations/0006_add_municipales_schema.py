"""Migration 0006 — Ajout colonnes municipales dans resultats_candidats.

Idempotent : vérifie l'existence de chaque colonne avant ALTER TABLE.
Vérifie également que nuances_harmonisees et elections ont les colonnes attendues.

Usage :
    uv run python scripts/migrations/0006_add_municipales_schema.py [--dry-run]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"

# Colonnes à ajouter dans resultats_candidats (toutes nullable)
_NEW_COLUMNS: list[tuple[str, str]] = [
    ("liste", "VARCHAR"),
    ("libelle_abrege_liste", "VARCHAR"),
    ("libelle_etendu_liste", "VARCHAR"),
    ("nom_tete_liste", "VARCHAR"),
    ("prenom_tete_liste", "VARCHAR"),
]


def _existing_columns(con, table: str) -> set[str]:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _migrate_resultats_candidats(con, dry_run: bool) -> list[str]:
    existing = _existing_columns(con, "resultats_candidats")
    added: list[str] = []
    for col_name, col_type in _NEW_COLUMNS:
        if col_name in existing:
            logger.info("resultats_candidats.%s : déjà présente — ignoré", col_name)
        else:
            sql = f"ALTER TABLE resultats_candidats ADD COLUMN {col_name} {col_type}"
            if dry_run:
                logger.info("[DRY-RUN] %s", sql)
            else:
                con.execute(sql)
                logger.info("Ajout colonne : resultats_candidats.%s %s", col_name, col_type)
            added.append(col_name)
    return added


def _verify_nuances_harmonisees(con) -> None:
    cols = _existing_columns(con, "nuances_harmonisees")
    required = {"nuance", "annee", "bloc", "source_bloc"}
    missing = required - cols
    if missing:
        raise RuntimeError(
            f"nuances_harmonisees manque ces colonnes : {missing}. "
            "Vérifier init_elections_schema.py."
        )
    # Vérifier que (nuance, annee) est la clé primaire
    pk_cols = {
        r[1] for r in con.execute("PRAGMA table_info(nuances_harmonisees)").fetchall() if r[5]
    }
    if pk_cols != {"nuance", "annee"}:
        raise RuntimeError(
            f"Clé primaire nuances_harmonisees inattendue : {pk_cols}. "
            "Attendu : {{nuance, annee}}."
        )
    logger.info("nuances_harmonisees : structure OK (nuance+annee PK, source_bloc présente)")


def _verify_elections_type_scrutin(con) -> None:
    """Vérifie que la table elections accepte type_scrutin='muni'."""
    # La colonne est VARCHAR, aucune contrainte CHECK n'est imposée — vérifier juste le type
    rows = con.execute("PRAGMA table_info(elections)").fetchall()
    col_types = {r[1]: r[2] for r in rows}
    if col_types.get("type_scrutin") != "VARCHAR":
        raise RuntimeError(
            f"elections.type_scrutin type inattendu : {col_types.get('type_scrutin')}. "
            "VARCHAR attendu."
        )
    logger.info("elections.type_scrutin : VARCHAR — type 'muni' accepté")


def main(dry_run: bool = False) -> None:
    if not _DB_PATH.exists():
        logger.error("Base introuvable : %s", _DB_PATH)
        sys.exit(1)

    logger.info("Migration 0006%s → %s", " [DRY-RUN]" if dry_run else "", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        # État avant
        cols_avant = _existing_columns(con, "resultats_candidats")
        logger.info("resultats_candidats avant migration : %d colonnes", len(cols_avant))

        # Migration
        added = _migrate_resultats_candidats(con, dry_run)

        # Vérifications structure
        _verify_nuances_harmonisees(con)
        _verify_elections_type_scrutin(con)

        # État après
        cols_apres = _existing_columns(con, "resultats_candidats")
        logger.info("resultats_candidats après migration : %d colonnes", len(cols_apres))

        print("\n── Migration 0006 — résumé ────────────────────────────────────────────────")
        if not dry_run:
            if added:
                print(f"  Colonnes ajoutées dans resultats_candidats : {', '.join(added)}")
            else:
                print("  Aucune colonne ajoutée (toutes déjà présentes — migration idempotente)")
        else:
            print(f"  [DRY-RUN] Colonnes qui seraient ajoutées : {', '.join(added) or 'aucune'}")
        print("  nuances_harmonisees : OK (nuance+annee PK, source_bloc présente)")
        print("  elections.type_scrutin : VARCHAR — 'muni' accepté")
        print("──────────────────────────────────────────────────────────────────────────\n")

        if not dry_run and not added:
            print("Migration déjà appliquée — rien à faire.")
        elif not dry_run:
            print("Migration 0006 appliquée.")

    finally:
        con.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
