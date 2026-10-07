"""Migration 0009 — tables de résultats électoraux sans clé primaire.

Décision Mathias 2026-10-07 (vague B, Q2) : l'index de clé primaire de
resultats_participation et resultats_candidats pesait ~1,1 Go en France entière.
Les deux tables sont reconstruites sans clé primaire (NOT NULL conservé sur les colonnes
de la clé) ; l'unicité est contrôlée par les loaders (verifier_unicite_resultats).

Idempotente : sans effet si les tables n'ont plus de clé primaire. Nombre de lignes
contrôlé avant et après (RuntimeError, rollback). Les vues électorales, municipales et
économiques sont recréées en fin de migration. À lancer AVANT les rechargements --perimetre france.

Usage :
    uv run python scripts/migrations/0009_resultats_sans_cle_primaire.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.schema_economie import create_economie_views  # noqa: E402
from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    create_elections_views,
    create_municipales_views,
    retirer_cles_primaires_resultats,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


def appliquer(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Retire les clés primaires puis recrée les vues dépendantes. Idempotent."""
    tables = retirer_cles_primaires_resultats(con)
    create_elections_views(con)
    create_municipales_views(con)
    create_economie_views(con)
    return tables


def main() -> None:
    db_path = get_settings().db_path
    if not db_path.exists():
        logger.error("Base introuvable : %s", db_path)
        sys.exit(1)
    con = open_connection(db_path)
    try:
        tables = appliquer(con)
        con.execute("CHECKPOINT")
        logger.info("Migration 0009 : %s", ", ".join(tables) or "rien à faire (déjà appliquée)")
    finally:
        con.close()


if __name__ == "__main__":
    main()
