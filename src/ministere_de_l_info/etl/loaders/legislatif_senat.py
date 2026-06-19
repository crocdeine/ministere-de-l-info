"""Loader Sénat — sénateurs HdF actifs et anciens depuis ODSEN_GENERAL.csv.

Source   : https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv
Format   : CSV encodé cp1252, séparateur virgule, 18 lignes de commentaires (%) à sauter
Colonnes : Matricule, Qualité, Nom usuel, Prénom usuel, État, Date naissance,
           Groupe politique, Circonscription, Description de la profession, …

Filtrage HdF : Circonscription IN ('Aisne', 'Nord', 'Oise', 'Pas-de-Calais', 'Somme')
Inclut les anciens sénateurs (État='ANCIEN') pour couverture historique.

Mapping département : nom → code INSEE 2 caractères
Mapping groupe politique → bloc officiel (6 blocs, ADR-0005)
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import duckdb
import httpx
import polars as pl

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_SENAT_CSV_URL = "https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv"
_CACHE_FILENAME = "senat-odsen-general.csv"
_COMMENT_LINES = 18

_CIRCOS_HDF: dict[str, tuple[str, str]] = {
    "Aisne": ("02", "Aisne"),
    "Nord": ("59", "Nord"),
    "Oise": ("60", "Oise"),
    "Pas-de-Calais": ("62", "Pas-de-Calais"),
    "Somme": ("80", "Somme"),
}

_GROUPE_BLOCS: dict[str, str] = {
    "CRCE-K": "EXG",
    "SER": "GAU",
    "UC": "CENT",
    "Les Indépendants": "DTE",
    "Les Républicains": "DTE",
    "NI": "DIV",
}


def _download_cache(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge ODSEN_GENERAL.csv en cache local."""
    dest = raw_dir / "legislatif" / _CACHE_FILENAME
    if dest.exists() and not force:
        logger.info("Cache existant : %s (--force pour re-télécharger)", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement ODSEN_GENERAL → %s", dest)
    with httpx.stream("GET", _SENAT_CSV_URL, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    logger.info("Téléchargé : %.1f Ko", dest.stat().st_size / 1024)
    return dest


def _parse_date(val: str | None) -> date | None:
    """Parse une date Sénat (YYYY-MM-DD HH:MM:SS.F) en date Python."""
    if not val or str(val).strip() in ("", "nan", "None"):
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except (ValueError, TypeError):
        return None


def load_legislatif_senat(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les sénateurs HdF (actifs + anciens) depuis ODSEN_GENERAL.csv dans leg_elus.

    Idempotent : DELETE leg_elus WHERE source='senat_csv' puis INSERT.
    """
    csv_path = _download_cache(raw_dir, force=force)

    df = pl.read_csv(
        csv_path,
        encoding="cp1252",
        separator=",",
        skip_rows=_COMMENT_LINES,
        has_header=True,
        null_values=["", "nan"],
        infer_schema_length=0,
    )

    circos_hdf = list(_CIRCOS_HDF.keys())
    df = df.filter(pl.col("Circonscription").is_in(circos_hdf))

    if df.is_empty():
        logger.error("Aucun sénateur HdF trouvé dans %s — vérifier colonnes CSV", csv_path)
        return

    today = date.today()

    rows: list[tuple] = []
    for row in df.iter_rows(named=True):
        matricule = str(row["Matricule"]).strip() if row["Matricule"] else None
        if not matricule:
            continue

        etat = str(row["État"]).strip() if row["État"] else ""
        est_actif = etat == "ACTIF"

        circo_nom = str(row["Circonscription"]).strip()
        code_dep, nom_dep = _CIRCOS_HDF.get(circo_nom, ("??", circo_nom))

        groupe = str(row["Groupe politique"]).strip() if row["Groupe politique"] else None
        bloc = _GROUPE_BLOCS.get(groupe, "DIV") if groupe else None

        date_naissance = _parse_date(row.get("Date naissance"))
        date_debut = None
        date_fin = None if est_actif else today

        profession = str(row.get("Description de la profession", "") or "").strip() or None

        rows.append(
            (
                matricule,
                "SENAT",
                None,
                str(row["Nom usuel"]).strip(),
                str(row["Prénom usuel"]).strip(),
                None,
                date_naissance,
                code_dep,
                nom_dep,
                None,
                groupe,
                groupe,
                bloc,
                False,
                date_debut,
                date_fin,
                est_actif,
                profession,
                "senat_csv",
            )
        )

    con.execute("DELETE FROM leg_elus WHERE source = 'senat_csv'")

    con.executemany(
        """
        INSERT INTO leg_elus (
            id, chambre, legislature,
            nom, prenom, sexe, date_naissance,
            code_departement, nom_departement, num_circo,
            groupe_sigle, groupe_nom, bloc_politique, bloc_override,
            date_debut_mandat, date_fin_mandat,
            est_actif, profession, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (id, chambre) DO UPDATE SET
            nom              = excluded.nom,
            prenom           = excluded.prenom,
            code_departement = excluded.code_departement,
            groupe_sigle     = excluded.groupe_sigle,
            groupe_nom       = excluded.groupe_nom,
            bloc_politique   = excluded.bloc_politique,
            est_actif        = excluded.est_actif,
            profession       = excluded.profession,
            source           = excluded.source
        """,
        rows,
    )

    total = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv'").fetchone()[0]
    actifs = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND est_actif = TRUE"
    ).fetchone()[0]
    logger.info(
        "leg_elus (Sénat) : %d total (%d actifs, %d anciens)", total, actifs, total - actifs
    )

    upsert_metadata(con, "leg_elus_senat", total, "senat/ODSEN_GENERAL")
