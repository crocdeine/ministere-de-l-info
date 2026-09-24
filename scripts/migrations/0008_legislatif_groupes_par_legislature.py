"""Migration 0008 — Législatif : mandats par législature et classement (groupe, législature).

ADR-0011. Applicable à une base déjà chargée, sans téléchargement ni rechargement :

1. crée ``leg_mandats`` et ``leg_groupes_blocs`` (IF NOT EXISTS) ;
2. recharge le référentiel ``leg_groupes_blocs`` depuis ``etl/legislatif_groupes.py`` ;
3. initialise ``leg_mandats`` depuis ``leg_elus`` pour chaque source absente de la table
   (un mandat par élu : Datan = dernière législature ; Sénat = groupe actuel ou dernier) ;
4. met ``date_fin_mandat`` à NULL (valeurs erronées : date du chargement pour le Sénat,
   date de mise à jour Datan pour l'AN) ;
5. recalcule ``leg_elus.bloc_politique`` depuis le référentiel (NULL si non classé) ;
6. recrée les vues (``v_elus_actuels`` + alias ``v_elus_hdf_actuels``, etc.).

Idempotente : relancer la migration ne change rien. Aucune table n'est supprimée.
Le filtre des sénateurs antérieurs à 2002 n'est appliqué qu'au rechargement du Sénat
(``scripts/load_legislatif.py --source senat``), car il exige le CSV source.

Usage :
    uv run python scripts/migrations/0008_legislatif_groupes_par_legislature.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.legislatif_groupes import populate_groupes_blocs  # noqa: E402
from ministere_de_l_info.etl.schema_legislatif import (  # noqa: E402
    _jointure_groupe,
    create_legislatif_schema,
    create_legislatif_views,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"

_GRANULARITE_PAR_SOURCE: dict[str, str] = {
    "datan": "derniere_legislature",
    "senat_csv": "groupe_actuel_ou_dernier",
}


def appliquer_migration(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Applique la migration 0008 sur une connexion ouverte ; renvoie des compteurs."""
    create_legislatif_schema(con)
    populate_groupes_blocs(con)

    inseres = 0
    for source, granularite in _GRANULARITE_PAR_SOURCE.items():
        deja = con.execute("SELECT COUNT(*) FROM leg_mandats WHERE source = ?", [source])
        if deja.fetchone()[0]:
            continue
        con.execute(
            """
            INSERT INTO leg_mandats (
                elu_id, chambre, legislature, groupe_sigle, groupe_nom,
                code_departement, num_circo, date_debut, date_fin, granularite, source
            )
            SELECT id, chambre,
                   CASE WHEN chambre = 'SENAT' THEN NULL ELSE legislature END,
                   NULLIF(groupe_sigle, ''), NULLIF(groupe_nom, ''),
                   code_departement, num_circo, date_debut_mandat, NULL, ?, source
            FROM leg_elus
            WHERE source = ?
            """,
            [granularite, source],
        )
        inseres += con.execute(
            "SELECT COUNT(*) FROM leg_mandats WHERE source = ?", [source]
        ).fetchone()[0]

    con.execute(
        "UPDATE leg_elus SET date_fin_mandat = NULL "
        "WHERE source IN ('datan', 'senat_csv') AND date_fin_mandat IS NOT NULL"
    )

    con.execute(f"""
        UPDATE leg_elus SET bloc_politique = (
            SELECT g.bloc FROM leg_groupes_blocs g
            WHERE {_jointure_groupe("g", "leg_elus")}
        )
    """)

    create_legislatif_views(con)

    non_classes = con.execute(
        "SELECT chambre, groupe_sigle, legislature, COUNT(*) FROM v_mandats_legislatif "
        "WHERE bloc_final IS NULL GROUP BY ALL ORDER BY 4 DESC"
    ).fetchall()
    for chambre, groupe, legislature, n in non_classes:
        logger.warning(
            "%s : groupe non classé %r (lég. %s) — %d mandat(s), bloc NULL",
            chambre,
            groupe,
            legislature,
            n,
        )
    n_mandats = con.execute("SELECT COUNT(*) FROM leg_mandats").fetchone()[0]
    logger.info(
        "Migration 0008 : %d mandats (%d insérés), %d groupe(s) non classé(s)",
        n_mandats,
        inseres,
        len(non_classes),
    )
    return {"mandats": n_mandats, "inseres": inseres, "non_classes": len(non_classes)}


def main() -> None:
    configure_logging()
    con = open_connection(_DB_PATH)
    try:
        appliquer_migration(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
