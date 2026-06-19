"""Overrides manuels — sénateurs RN classés NI (Non Inscrits) au Sénat HdF.

Justification : le groupe 'NI' (Non Inscrits) au Sénat masque l'appartenance
politique réelle de certains sénateurs RN qui n'ont pas constitué de groupe
officiel. Ces cas nécessitent un classement manuel basé sur leur étiquette
électorale connue (candidats sous étiquette RN aux sénatoriales 2023).

Vérification : chaque entrée ci-dessous a été confirmée par son matricule
exact dans ODSEN_GENERAL.csv (chargé par legislatif_senat.py).
"""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)

OVERRIDES_BLOCS: list[dict] = [
    {
        "elu_id": "21085M",
        "chambre": "SENAT",
        "bloc_force": "EXD",
        "justification": "Sénateur RN siégeant en NI — Joshua Hochart (Nord, élu 2023)",
    },
    {
        "elu_id": "21069M",
        "chambre": "SENAT",
        "bloc_force": "EXD",
        "justification": "Sénateur RN siégeant en NI — Christopher Szczurek (Pas-de-Calais, élu 2023)",
    },
]


def load_overrides(con: duckdb.DuckDBPyConnection) -> None:
    """Insère ou remplace les overrides dans leg_blocs_override.

    Idempotent : ON CONFLICT DO UPDATE.
    """
    if not OVERRIDES_BLOCS:
        logger.info("Aucun override défini.")
        return

    rows = [
        (o["elu_id"], o["chambre"], o["bloc_force"], o["justification"]) for o in OVERRIDES_BLOCS
    ]

    con.executemany(
        """
        INSERT INTO leg_blocs_override (elu_id, chambre, bloc_force, justification)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (elu_id, chambre) DO UPDATE SET
            bloc_force    = excluded.bloc_force,
            justification = excluded.justification
        """,
        rows,
    )

    count = con.execute("SELECT COUNT(*) FROM leg_blocs_override").fetchone()[0]
    logger.info("leg_blocs_override : %d override(s) chargé(s)", count)
