"""Migration 0007 — Création des 3 vues d'agrégation municipales.

Vues créées (CREATE OR REPLACE, idempotent) :
- v_scores_commune_muni  : voix par (annee, tour, commune, bloc)
- v_evolution_blocs_hdf_muni : agrégation HdF par scrutin × bloc
- v_listes_commune_muni  : détail liste par liste (clé drill-down D3.3),
  1 ligne par (annee, tour, commune, no_panneau) ; 2008 : descripteurs de liste

Toutes les vues utilisent LEFT JOIN sur nuances_harmonisees : les nuances sans
mapping (NC, LNC) produisent bloc = NULL, agrégées sous "Non classé" dans
l'UI. pct_exprimes calculé sur le total exprimés de la commune ou du HdF selon
la vue, via jointure sur resultats_participation.

Définition des vues : schema_elections.create_municipales_views (déplacée le
2026-10-07, vague B) ; ce script reste le point d'entrée CLI.

Usage :
    uv run python scripts/migrations/0007_add_municipales_views.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info._sql import ligne_unique  # noqa: E402
from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    _ANNEES_NO_PANNEAU_SYNTHETIQUE,  # noqa: F401  (réexport pour les tests)
    _create_v_evolution_blocs_hdf_muni,
    _create_v_listes_commune_muni,
    _create_v_scores_commune_muni,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = get_settings().db_path


def main() -> None:
    from ministere_de_l_info.espace_disque import verifier_espace

    verifier_espace(_DB_PATH.parent)
    if not _DB_PATH.exists():
        logger.error("Base introuvable : %s", _DB_PATH)
        sys.exit(1)

    logger.info("Migration 0007 → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        _create_v_scores_commune_muni(con)
        _create_v_evolution_blocs_hdf_muni(con)
        _create_v_listes_commune_muni(con)

        # Vérification rapide : les 3 vues retournent des lignes
        checks = [
            ("v_scores_commune_muni", "SELECT COUNT(*) FROM v_scores_commune_muni"),
            ("v_evolution_blocs_hdf_muni", "SELECT COUNT(*) FROM v_evolution_blocs_hdf_muni"),
            ("v_listes_commune_muni", "SELECT COUNT(*) FROM v_listes_commune_muni"),
        ]
        print("\n── Migration 0007 — vérification vues ────────────────────────────────────")
        for name, sql in checks:
            n = ligne_unique(con.execute(sql))[0]
            status = "✓" if n > 0 else "✗ VIDE"
            print(f"  {name:<35s} {n:>8,} lignes  {status}")
        print("──────────────────────────────────────────────────────────────────────────\n")
        print("Migration 0007 appliquée.")

    finally:
        con.close()


if __name__ == "__main__":
    main()
