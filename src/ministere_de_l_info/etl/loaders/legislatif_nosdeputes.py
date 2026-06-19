"""Loader NosDéputés.fr — profils + métriques 16e législature HdF.

Source   : https://www.nosdeputes.fr/deputes/json (liste)
           https://www.nosdeputes.fr/<slug>/json (profil)
           https://www.nosdeputes.fr/<slug>/synthese/data/json (métriques)
Format   : JSON REST, stable, sans authentification
Couverture: 16e législature (2022-2024), figée depuis dissolution juin 2024
           Tous les députés apparaissent avec mandat_fin renseigné → est_actif=FALSE

Stratégie :
- Télécharger la liste /deputes/json (cache fichier unique)
- Filtrer HdF sur num_deptmt IN ('02','59','60','62','80')
- Pour chaque député HdF, télécharger profil + synthèse (délai 0.5-1s entre appels)
- Insérer profils dans leg_elus (source='nosdeputes')
- Insérer métriques dans leg_activite (source='nosdeputes')
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path

import duckdb

from ministere_de_l_info.etl._common import upsert_metadata
from ministere_de_l_info.etl.loaders._http_retry import fetch_with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.nosdeputes.fr"
_BETWEEN_CALLS = 0.7

_DEPTS_HDF = {"02", "59", "60", "62", "80"}

_GROUPE_BLOCS: dict[str, str] = {
    "LFI": "EXG",
    "GDR": "GAU",
    "SOC": "GAU",
    "LIOT": "DIV",
    "REN": "CENT",
    "HOR": "CENT",
    "LR": "DTE",
    "RN": "EXD",
}

_NOM_DEPT: dict[str, str] = {
    "02": "Aisne",
    "59": "Nord",
    "60": "Oise",
    "62": "Pas-de-Calais",
    "80": "Somme",
}


def _fetch_cached_json(url: str, cache_path: Path, force: bool = False) -> dict | list | None:
    """GET JSON avec cache fichier unique."""
    if cache_path.exists() and not force:
        try:
            with cache_path.open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Cache corrompu, re-téléchargement : %s", cache_path.name)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_with_retry(url, max_retries=4, base_delay=1.5)
    if data is not None:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass
    return data


def _parse_date(val: str | None) -> str | None:
    if not val or str(val).strip() in ("", "None", "0000-00-00"):
        return None
    try:
        return str(val).strip()[:10]
    except Exception:
        return None


def load_legislatif_nosdeputes(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les profils et métriques des 52 députés HdF (16e législature) depuis NosDéputés.fr.

    Idempotent : DELETE + INSERT pour source='nosdeputes'.
    """
    cache_dir = raw_dir / "legislatif" / "nosdeputes"
    cache_dir.mkdir(parents=True, exist_ok=True)

    liste_cache = cache_dir / "deputes-liste.json"
    data_liste = _fetch_cached_json(f"{_BASE_URL}/deputes/json", liste_cache, force=force)
    if not data_liste:
        logger.error("Impossible de récupérer la liste NosDéputés — abandon")
        return

    deputes_raw = data_liste if isinstance(data_liste, list) else data_liste.get("deputes", [])
    deputes_all = []
    for item in deputes_raw:
        d = item.get("depute", item) if isinstance(item, dict) else {}
        deputes_all.append(d)

    deputes_hdf = [d for d in deputes_all if str(d.get("num_deptmt", "")).zfill(2) in _DEPTS_HDF]
    logger.info(
        "NosDéputés : %d députés HdF trouvés sur %d total", len(deputes_hdf), len(deputes_all)
    )

    today = date.today()
    elu_rows: list[tuple] = []
    activite_rows: list[tuple] = []

    for d in deputes_hdf:
        slug = d.get("slug", "")
        if not slug:
            continue

        code_dep = str(d.get("num_deptmt", "")).zfill(2)

        groupe_sigle = (d.get("groupe_sigle") or "").strip()
        bloc = _GROUPE_BLOCS.get(groupe_sigle, "DIV")

        sexe_raw = (d.get("sexe") or "").upper()
        sexe = "H" if sexe_raw == "H" else ("F" if sexe_raw == "F" else None)

        date_fin = _parse_date(d.get("mandat_fin"))
        est_actif = date_fin is None

        elu_rows.append(
            (
                slug,
                "AN",
                16,
                (d.get("nom_de_famille") or "").strip(),
                (d.get("prenom") or "").strip(),
                sexe,
                _parse_date(d.get("date_naissance")),
                code_dep,
                _NOM_DEPT.get(code_dep, ""),
                d.get("num_circo"),
                groupe_sigle,
                d.get("groupe", ""),
                bloc,
                False,
                _parse_date(d.get("mandat_debut")),
                date_fin,
                est_actif,
                (d.get("profession") or "").strip() or None,
                "nosdeputes",
            )
        )

        time.sleep(_BETWEEN_CALLS)
        synthese_cache = cache_dir / f"synthese-{slug}.json"
        synthese = _fetch_cached_json(
            f"{_BASE_URL}/{slug}/synthese/data/json",
            synthese_cache,
            force=force,
        )

        if synthese:
            s = synthese.get("synthese", synthese)
            activite_rows.append(
                (
                    slug,
                    "AN",
                    today,
                    s.get("semaines_presence"),
                    s.get("commission_presences"),
                    s.get("commission_interventions"),
                    s.get("hemicycle_interventions"),
                    s.get("amendements_proposes"),
                    s.get("amendements_signes"),
                    s.get("amendements_adoptes"),
                    s.get("rapports"),
                    s.get("propositions_ecrites"),
                    s.get("propositions_signees"),
                    s.get("questions_ecrites"),
                    s.get("questions_orales"),
                    "nosdeputes",
                )
            )
        else:
            logger.warning("Synthèse introuvable pour %s", slug)

    con.execute("DELETE FROM leg_elus WHERE source = 'nosdeputes'")
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
            legislature      = excluded.legislature,
            groupe_sigle     = excluded.groupe_sigle,
            groupe_nom       = excluded.groupe_nom,
            bloc_politique   = excluded.bloc_politique,
            date_debut_mandat= excluded.date_debut_mandat,
            date_fin_mandat  = excluded.date_fin_mandat,
            est_actif        = excluded.est_actif,
            source           = excluded.source
        """,
        elu_rows,
    )

    if activite_rows:
        con.execute("DELETE FROM leg_activite WHERE source = 'nosdeputes' AND chambre = 'AN'")
        con.executemany(
            """
            INSERT INTO leg_activite (
                elu_id, chambre, date_extraction,
                semaines_presence, commission_presences, commission_interventions,
                hemicycle_interventions, amendements_proposes, amendements_signes,
                amendements_adoptes, rapports, propositions_ecrites, propositions_signees,
                questions_ecrites, questions_orales, source
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (elu_id, chambre, date_extraction) DO UPDATE SET
                semaines_presence        = excluded.semaines_presence,
                commission_presences     = excluded.commission_presences,
                commission_interventions = excluded.commission_interventions,
                hemicycle_interventions  = excluded.hemicycle_interventions,
                amendements_proposes     = excluded.amendements_proposes,
                amendements_signes       = excluded.amendements_signes,
                amendements_adoptes      = excluded.amendements_adoptes,
                source                   = excluded.source
            """,
            activite_rows,
        )

    nb_elus = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'nosdeputes'").fetchone()[0]
    nb_activite = con.execute(
        "SELECT COUNT(*) FROM leg_activite WHERE source = 'nosdeputes'"
    ).fetchone()[0]
    logger.info("NosDéputés : %d élus, %d métriques activité chargés", nb_elus, nb_activite)

    upsert_metadata(con, "leg_elus_nosdeputes", nb_elus, "nosdeputes/deputes/16")
