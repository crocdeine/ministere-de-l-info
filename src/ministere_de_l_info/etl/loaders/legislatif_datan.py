"""Loader Datan — historique des députés AN depuis 2002 (national, législatures 12-17).

Source   : data.gouv.fr — dataset "historique-des-deputes-de-lassemblee-nationale-..."
Format   : CSV UTF-8 séparateur virgule, ~2120 lignes, 27 colonnes
Couverture: Législatures 12 à 17 (2002-présent), France entière
Actifs   : colonne active=1 (~577 actifs en 17e législature)

Données chargées :
- leg_elus     : profil de chaque député (groupe, bloc, département, ...)
- leg_activite : scores Datan (participation, loyauté, majorité, dateMaj)

Règle blocs : PCF/GDR = GAU (pas EXG).
EXG réservé à LFI et l'extrême gauche stricto sensu.

Idempotent : DELETE leg_elus/leg_activite WHERE source='datan' puis INSERT.
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path

import duckdb
import httpx

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_DATAGOUV_SLUG = (
    "historique-des-deputes-de-lassemblee-nationale-depuis-2002-informations-et-statistiques"
)
_CACHE_FILENAME = "datan-deputes-historique.csv"
# URL statique de secours (mise à jour 2026-06-17)
_STATIC_CSV_URL = (
    "https://static.data.gouv.fr/resources/"
    "historique-des-deputes-de-lassemblee-nationale-depuis-2002"
    "-informations-et-statistiques/"
    "20260617-171043/deputes-historique.csv"
)

# Règle : PCF/GDR = GAU (pas EXG) — cohérent avec grille data-viz-politique
# EXG réservé à LFI et l'extrême gauche stricto sensu
_GROUPE_BLOCS: dict[str, str] = {
    # EXG
    "FI": "EXG",
    "LFI-NFP": "EXG",
    "LFI-NUPES": "EXG",
    # GAU — Socialistes, Écologistes, PCF/GDR
    "CR": "GAU",
    "ECOLO": "GAU",
    "ECOS": "GAU",
    "GDR": "GAU",
    "GDR-NUPES": "GAU",
    "NG": "GAU",
    "S.R.C.": "GAU",
    "SER": "GAU",
    "SOC": "GAU",
    "SOC-A": "GAU",
    "SRC": "GAU",
    # DIV
    "LIOT": "DIV",
    "LT": "DIV",
    "NI": "DIV",
    "RRDP": "DIV",
    # CENT
    "AGIR-E": "CENT",
    "DEM": "CENT",
    "EPR": "CENT",
    "HOR": "CENT",
    "LAREM": "CENT",
    "MODEM": "CENT",
    "NC": "CENT",
    "RE": "CENT",
    "UDF": "CENT",
    "UDI": "CENT",
    "UDI-AGIR": "CENT",
    "UDI_I": "CENT",
    # DTE
    "DR": "DTE",
    "LES-REP": "DTE",
    "LR": "DTE",
    "UMP": "DTE",
    # EXD
    "RN": "EXD",
    "UDDPLR": "EXD",
    "UDR": "EXD",
}


def _get_csv_url() -> str | None:
    """Récupère l'URL courante du CSV via l'API data.gouv.fr."""
    api_url = f"https://www.data.gouv.fr/api/1/datasets/{_DATAGOUV_SLUG}/"
    try:
        resp = httpx.get(api_url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        for resource in data.get("resources", []):
            if resource.get("format", "").upper() == "CSV":
                url = resource.get("url")
                if url:
                    logger.info("URL CSV Datan (API) : %s", url)
                    return url
    except Exception as exc:
        logger.warning("Impossible de récupérer URL Datan via API : %s", exc)
    return None


def _download_csv(url: str, dest: Path) -> None:
    """Télécharge le CSV Datan en cache local."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement Datan → %s", dest)
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    logger.info("Téléchargé : %.1f Ko", dest.stat().st_size / 1024)


def _parse_float(val: str | None) -> float | None:
    if not val or str(val).strip() in ("", "None", "nan"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val: str | None) -> date | None:
    if not val or str(val).strip() in ("", "None", "nan"):
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except (ValueError, TypeError):
        return None


def _sexe(civ: str | None) -> str | None:
    if not civ:
        return None
    c = civ.strip()
    if c in ("M.", "M"):
        return "H"
    if c in ("Mme", "Mme."):
        return "F"
    return None


def load_legislatif_datan(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les députés AN (législatures 12-17, national) depuis le dataset Datan.

    Tente d'abord de récupérer l'URL courante via l'API data.gouv.fr,
    avec fallback sur l'URL statique connue.

    Idempotent : DELETE + INSERT pour source='datan'.
    """
    cache_path = raw_dir / "legislatif" / _CACHE_FILENAME

    if not cache_path.exists() or force:
        url = _get_csv_url() or _STATIC_CSV_URL
        _download_csv(url, cache_path)

    with cache_path.open(encoding="utf-8") as fh:
        rows_csv = list(csv.DictReader(fh))

    logger.info("Datan : %d lignes CSV lues", len(rows_csv))

    today = date.today()
    elu_rows: list[tuple] = []
    activite_rows: list[tuple] = []

    for row in rows_csv:
        elu_id = (row.get("id") or "").strip()
        if not elu_id:
            continue

        nom = (row.get("nom") or "").strip()
        prenom = (row.get("prenom") or "").strip()
        if not nom:
            continue

        legislature_raw = (row.get("legislatureLast") or "").strip()
        legislature = int(legislature_raw) if legislature_raw.isdigit() else None

        groupe_abrev = (row.get("groupeAbrev") or "").strip()
        groupe_nom = (row.get("groupe") or "").strip()
        bloc = _GROUPE_BLOCS.get(groupe_abrev, "DIV")

        code_dep = (row.get("departementCode") or "XX").strip()
        nom_dep = (row.get("departementNom") or "").strip()
        circo_raw = (row.get("circo") or "").strip()
        num_circo = int(circo_raw) if circo_raw.isdigit() else None

        est_actif = str(row.get("active", "0")).strip() == "1"
        date_debut = _parse_date(row.get("datePriseFonction"))
        date_fin = None if est_actif else _parse_date(row.get("dateMaj"))

        elu_rows.append(
            (
                elu_id,
                "AN",
                legislature,
                nom,
                prenom,
                _sexe(row.get("civ")),
                _parse_date(row.get("naissance")),
                code_dep,
                nom_dep,
                None,  # region_nom non disponible dans Datan
                num_circo,
                groupe_abrev,
                groupe_nom,
                bloc,
                False,
                date_debut,
                date_fin,
                est_actif,
                (row.get("job") or "").strip() or None,
                "datan",
            )
        )

        # Scores d'activité (tous actifs et anciens — dateMaj comme date_extraction)
        date_maj = _parse_date(row.get("dateMaj")) or today
        score_part = _parse_float(row.get("scoreParticipation"))
        score_part_spe = _parse_float(row.get("scoreParticipationSpecialite"))
        score_loy = _parse_float(row.get("scoreLoyaute"))
        score_maj = _parse_float(row.get("scoreMajorite"))

        if any(s is not None for s in (score_part, score_part_spe, score_loy, score_maj)):
            activite_rows.append(
                (
                    elu_id,
                    "AN",
                    date_maj,
                    score_part,
                    score_part_spe,
                    score_loy,
                    score_maj,
                    "datan",
                )
            )

    con.execute("DELETE FROM leg_elus WHERE source = 'datan'")
    con.executemany(
        """
        INSERT INTO leg_elus (
            id, chambre, legislature,
            nom, prenom, sexe, date_naissance,
            code_departement, nom_departement, region_nom, num_circo,
            groupe_sigle, groupe_nom, bloc_politique, bloc_override,
            date_debut_mandat, date_fin_mandat,
            est_actif, profession, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (id, chambre) DO UPDATE SET
            legislature       = excluded.legislature,
            groupe_sigle      = excluded.groupe_sigle,
            groupe_nom        = excluded.groupe_nom,
            bloc_politique    = excluded.bloc_politique,
            date_debut_mandat = excluded.date_debut_mandat,
            date_fin_mandat   = excluded.date_fin_mandat,
            est_actif         = excluded.est_actif,
            source            = excluded.source
        """,
        elu_rows,
    )

    if activite_rows:
        con.execute("DELETE FROM leg_activite WHERE source = 'datan'")
        con.executemany(
            """
            INSERT INTO leg_activite (
                elu_id, chambre, date_extraction,
                score_participation, score_participation_specialite,
                score_loyaute, score_majorite, source
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT (elu_id, chambre, date_extraction) DO UPDATE SET
                score_participation            = excluded.score_participation,
                score_participation_specialite = excluded.score_participation_specialite,
                score_loyaute                  = excluded.score_loyaute,
                score_majorite                 = excluded.score_majorite,
                source                         = excluded.source
            """,
            activite_rows,
        )

    nb_elus = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'datan'").fetchone()[0]
    nb_actifs = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'datan' AND est_actif = TRUE"
    ).fetchone()[0]
    nb_act = con.execute("SELECT COUNT(*) FROM leg_activite WHERE source = 'datan'").fetchone()[0]
    logger.info(
        "leg_elus (Datan, AN) : %d total (%d actifs) | leg_activite : %d scores",
        nb_elus,
        nb_actifs,
        nb_act,
    )

    upsert_metadata(con, "leg_elus_datan", nb_elus, "datan/deputes-historique")
