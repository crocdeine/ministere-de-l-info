"""Loader API CLAIR — députés HdF (17e législature).

Source   : https://api.clair.vote/api/v1/deputes?legislature=17
Format   : JSON paginé, limite=20/page (ne PAS augmenter — API instable)
Stabilité: INSTABLE — erreurs 500 fréquentes sous charge ou pagination soutenue.
           Utilise fetch_page_cached() pour reprise partielle sur interruption.

Stratégie :
- Récupération page par page avec cache disque JSON (data/raw/legislatif/)
- Filtre HdF côté client (l'API n'a pas de filtre département)
- Si une page échoue après tous les retries : logger + continuer
- NE PAS lancer en boucle automatique — tester manuellement d'abord

Mapping groupes AN → blocs officiels (ADR-0005) :
  LFI→EXG, GDR→GAU, SOC→GAU, LIOT→DIV, REN→CENT, HOR→CENT, LR→DTE, RN→EXD
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import duckdb

from ministere_de_l_info.etl._common import upsert_metadata
from ministere_de_l_info.etl.loaders._http_retry import fetch_page_cached, fetch_with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.clair.vote/api/v1"
_PAGE_LIMIT = 20
_BETWEEN_PAGES = 1.5

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


def _detect_dept(depute: dict) -> str | None:
    """Extrait le code département depuis les champs CLAIR disponibles."""
    circo = depute.get("circo") or depute.get("circonscription") or {}
    if isinstance(circo, dict):
        code = circo.get("departement") or circo.get("codeDepartement") or circo.get("numDept")
        if code:
            return str(code).zfill(2)[:3]
    dept_raw = depute.get("departement") or depute.get("numDept")
    if dept_raw:
        return str(dept_raw).zfill(2)[:3]
    return None


def _parse_clair_depute(d: dict, legislature: int) -> tuple | None:
    """Convertit un dict CLAIR en tuple pour INSERT leg_elus.

    Retourne None si hors HdF ou champs critiques manquants.
    """
    slug = d.get("slug") or d.get("id")
    if not slug:
        return None

    code_dep = _detect_dept(d)
    if not code_dep or code_dep not in _DEPTS_HDF:
        return None

    nom = (d.get("nom") or d.get("nomDeFamille") or "").strip()
    prenom = (d.get("prenom") or "").strip()
    if not nom or not prenom:
        return None

    groupe_sigle = (d.get("groupeSigle") or d.get("groupe", {}).get("sigle") or "").strip()
    groupe_nom = (d.get("groupeNom") or d.get("groupe", {}).get("nom") or groupe_sigle).strip()
    bloc = _GROUPE_BLOCS.get(groupe_sigle, "DIV")

    sexe_raw = (d.get("sexe") or "").upper()
    sexe = sexe_raw[0] if sexe_raw else None

    date_naissance = None
    ddn = d.get("dateNaissance") or d.get("date_naissance")
    if ddn:
        date_naissance = str(ddn).strip()[:10]

    num_circo_raw = (
        d.get("numCirco")
        or d.get("num_circo")
        or (d.get("circo", {}).get("numero") if isinstance(d.get("circo"), dict) else None)
    )
    num_circo = int(num_circo_raw) if num_circo_raw else None

    date_debut = d.get("mandatDebut") or d.get("mandat_debut")
    if date_debut:
        date_debut = str(date_debut).strip()[:10]

    date_fin = d.get("mandatFin") or d.get("mandat_fin")
    if date_fin:
        date_fin = str(date_fin).strip()[:10]
    est_actif = date_fin is None

    profession = (d.get("profession") or "").strip() or None

    return (
        str(slug),
        "AN",
        legislature,
        nom,
        prenom,
        sexe,
        date_naissance,
        code_dep,
        _NOM_DEPT.get(code_dep, ""),
        num_circo,
        groupe_sigle,
        groupe_nom,
        bloc,
        False,
        date_debut,
        date_fin,
        est_actif,
        profession,
        "clair",
    )


def load_legislatif_deputes_clair(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    legislature: int = 17,
    force: bool = False,
) -> None:
    """Charge les députés HdF depuis l'API CLAIR (17e législature par défaut).

    API connue pour son instabilité (erreurs 500 fréquentes) — voir
    reports/verification-sources-legislatif.md. Utilise un cache page par page
    pour permettre une reprise partielle. Ne PAS augmenter PAGE_LIMIT > 20.

    Idempotent : DELETE + INSERT pour la combinaison source='clair' + legislature.
    """
    cache_dir = raw_dir / "legislatif"
    url = f"{_BASE_URL}/deputes"
    cache_prefix = f"clair-deputes-l{legislature}"

    first = fetch_with_retry(
        url,
        params={"legislature": legislature, "limit": _PAGE_LIMIT, "page": 1},
        max_retries=5,
        base_delay=2.0,
    )
    if first is None:
        logger.error("API CLAIR inaccessible — abandon du chargement 17e législature")
        return

    meta = first.get("meta") or {}
    total = meta.get("total") or 0
    if not total:
        logger.warning("API CLAIR : total inconnu dans meta — parcours jusqu'à page vide")
        total = 10000

    import math

    nb_pages = math.ceil(total / _PAGE_LIMIT)
    logger.info("API CLAIR : %d députés, %d pages (législature %d)", total, nb_pages, legislature)

    all_rows: list[tuple] = []

    first_items = (
        first.get("items") or first.get("data") or (first if isinstance(first, list) else [])
    )
    for d in first_items:
        row = _parse_clair_depute(d, legislature)
        if row:
            all_rows.append(row)

    cache_dir.mkdir(parents=True, exist_ok=True)
    import json

    p1_cache = cache_dir / f"{cache_prefix}-page-{1:04d}.json"
    if not p1_cache.exists() or force:
        with p1_cache.open("w", encoding="utf-8") as f:
            json.dump(first, f, ensure_ascii=False)

    for page in range(2, nb_pages + 1):
        data = fetch_page_cached(
            url=url,
            cache_dir=cache_dir,
            cache_prefix=cache_prefix,
            page=page,
            params={"legislature": legislature, "limit": _PAGE_LIMIT, "page": page},
            max_retries=5,
            base_delay=2.0,
            between_calls=_BETWEEN_PAGES,
        )
        if data is None:
            logger.warning("Page %d manquante — ignorée (reprise possible)", page)
            continue

        items = data.get("items") or data.get("data") or (data if isinstance(data, list) else [])
        if not items:
            logger.info("Page %d vide — fin de pagination", page)
            break
        for d in items:
            row = _parse_clair_depute(d, legislature)
            if row:
                all_rows.append(row)

        time.sleep(_BETWEEN_PAGES)

    if not all_rows:
        logger.warning("Aucun député HdF trouvé via API CLAIR (législature %d)", legislature)
        return

    con.execute("DELETE FROM leg_elus WHERE source = 'clair' AND legislature = ?", [legislature])

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
        all_rows,
    )

    count = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'clair' AND legislature = ?", [legislature]
    ).fetchone()[0]
    logger.info("leg_elus (CLAIR, législature %d) : %d députés HdF chargés", legislature, count)

    upsert_metadata(con, f"leg_elus_clair_l{legislature}", count, f"clair/deputes/l{legislature}")
