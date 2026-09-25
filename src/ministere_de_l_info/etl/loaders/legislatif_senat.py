"""Loader Sénat — sénateurs actifs et anciens depuis ODSEN_GENERAL.csv (portée nationale).

Source   : https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv
Format   : CSV encodé cp1252, séparateur virgule, 18 lignes de commentaires (%) à sauter
Colonnes : Matricule, Qualité, Nom usuel, Prénom usuel, État, Date naissance,
           Groupe politique, Circonscription, Description de la profession, …

Portée   : France entière par défaut (departements=None).
           Passer departements=['Aisne','Nord',...] pour filtrer par circonscription.
Inclut les anciens sénateurs (État='ANCIEN') pour couverture historique.

Mapping département : nom circonscription → code INSEE 2-3 caractères
Groupe politique → bloc : référentiel ``etl/legislatif_groupes.py`` (ADR-0011) ;
groupe non classé → bloc NULL + WARNING (plus de repli DIV).

Dates (ADR-0011) : le fichier ne contient aucune date de mandat. ``date_debut_mandat``
et ``date_fin_mandat`` restent NULL (auparavant, la fin valait la date du chargement).

Périmètre temporel (ADR-0011) : le projet couvre 2002-présent. Faute de dates de mandat,
seuls les anciens sénateurs **certainement** antérieurs au renouvellement du
29 septembre 2002 sont écartés : circonscriptions disparues (code ``XX`` : Seine,
Seine-et-Oise, Algérie, anciens territoires, toutes antérieures à 1968) et sénateurs
décédés avant cette date (colonne « Date de décès », si présente). Addendum ADR-0011
(2026-09-25) : sont aussi écartés les anciens sénateurs dont le dernier groupe a disparu
avant ce renouvellement (RPR, RI, UNR, G.D., …, liste ``GROUPES_SENAT_ANTERIEURS_2002``
de ``etl/legislatif_groupes.py``) ; aucun bloc ne leur est attribué. Les autres anciens
sénateurs sont conservés ; un filtre exact exige une source datée des mandats.
Groupe vide : statut « sans groupe » (bloc NULL, INFO), distinct de « non classé ».
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date
from pathlib import Path

import duckdb
import httpx
import polars as pl

from ministere_de_l_info.etl._common import upsert_metadata
from ministere_de_l_info.etl.legislatif_groupes import (
    est_groupe_senat_anterieur_2002,
    journaliser_non_classes,
    journaliser_sans_groupe,
    resoudre_bloc,
)

logger = logging.getLogger(__name__)

_SENAT_CSV_URL = "https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv"
_CACHE_FILENAME = "senat-odsen-general.csv"
_COMMENT_LINES = 18

# Subset HdF pour usage UI (filtre optionnel côté appelant)
_CIRCOS_HDF: frozenset[str] = frozenset({"Aisne", "Nord", "Oise", "Pas-de-Calais", "Somme"})

# Début du périmètre temporel du projet pour le Sénat : renouvellement de 2002.
DEBUT_PERIMETRE_SENAT = date(2002, 9, 29)
GRANULARITE_SENAT = "groupe_actuel_ou_dernier"

# Mapping complet circonscription Sénat → code département INSEE
# Inclut les dpts historiques (Algérie, Seine-et-Oise...) → "XX"
_ALL_CIRCOS: dict[str, str] = {
    # Métropole 01-19
    "Ain": "01",
    "Aisne": "02",
    "Allier": "03",
    "Alpes de Haute-Provence": "04",
    "Basses-Alpes": "04",  # ancien nom
    "Hautes-Alpes": "05",
    "Alpes-Maritimes": "06",
    "Ardèche": "07",
    "Ardennes": "08",
    "Ariège": "09",
    "Aube": "10",
    "Aude": "11",
    "Aveyron": "12",
    "Bouches-du-Rhône": "13",
    "Calvados": "14",
    "Cantal": "15",
    "Charente": "16",
    "Charente-Maritime": "17",
    "Cher": "18",
    "Corrèze": "19",
    # Corse
    "Corse": "20",  # avant division 1976
    "Corse-du-Sud": "2A",
    "Haute-Corse": "2B",
    # Métropole 21-69
    "Côte-d'Or": "21",
    "Côtes-d'Armor": "22",
    "Côtes-du-Nord": "22",  # ancien nom
    "Creuse": "23",
    "Dordogne": "24",
    "Doubs": "25",
    "Drôme": "26",
    "Eure": "27",
    "Eure-et-Loir": "28",
    "Finistère": "29",
    "Gard": "30",
    "Haute-Garonne": "31",
    "Gers": "32",
    "Gironde": "33",
    "Hérault": "34",
    "Ille-et-Vilaine": "35",
    "Indre": "36",
    "Indre-et-Loire": "37",
    "Isère": "38",
    "Jura": "39",
    "Landes": "40",
    "Loir-et-Cher": "41",
    "Loire": "42",
    "Haute-Loire": "43",
    "Loire-Atlantique": "44",
    "Loiret": "45",
    "Lot": "46",
    "Lot-et-Garonne": "47",
    "Lozère": "48",
    "Maine-et-Loire": "49",
    "Manche": "50",
    "Marne": "51",
    "Haute-Marne": "52",
    "Mayenne": "53",
    "Meurthe-et-Moselle": "54",
    "Meuse": "55",
    "Morbihan": "56",
    "Moselle": "57",
    "Nièvre": "58",
    "Nord": "59",
    "Oise": "60",
    "Orne": "61",
    "Pas-de-Calais": "62",
    "Puy-de-Dôme": "63",
    "Pyrénées-Atlantiques": "64",
    "Basses-Pyrénées": "64",  # ancien nom
    "Hautes-Pyrénées": "65",
    "Pyrénées-Orientales": "66",
    "Bas-Rhin": "67",
    "Haut-Rhin": "68",
    "Rhône": "69",
    # Métropole 70-95
    "Haute-Saône": "70",
    "Saône-et-Loire": "71",
    "Sarthe": "72",
    "Savoie": "73",
    "Haute-Savoie": "74",
    "Paris": "75",
    "Seine-Maritime": "76",
    "Seine-et-Marne": "77",
    "Yvelines": "78",
    "Deux-Sèvres": "79",
    "Somme": "80",
    "Tarn": "81",
    "Tarn-et-Garonne": "82",
    "Var": "83",
    "Vaucluse": "84",
    "Vendée": "85",
    "Vienne": "86",
    "Haute-Vienne": "87",
    "Vosges": "88",
    "Yonne": "89",
    "Territoire de Belfort": "90",
    "Essonne": "91",
    "Hauts-de-Seine": "92",
    "Seine-Saint-Denis": "93",
    "Val-de-Marne": "94",
    "Val-d'Oise": "95",
    # DOM
    "Guadeloupe": "971",
    "Martinique": "972",
    "Guyane": "973",
    "La Réunion": "974",
    "Saint-Pierre-et-Miquelon": "975",
    "Mayotte": "976",
    # Collectivités d'outre-mer
    "Saint-Barthélemy": "977",
    "Saint-Martin": "978",
    "Iles Wallis et Futuna": "986",
    "Polynésie française": "987",
    "Nouvelle-Calédonie": "988",
    # Français de l'étranger
    "Français établis hors de France": "999",
    # Départements historiques dissous (Seine-et-Oise → 91/92/95/78 en 1968)
    "Seine": "XX",
    "Seine-et-Oise": "XX",
    # Départements algériens (indépendance 1962)
    "Alger": "XX",
    "Bône": "XX",
    "Constantine": "XX",
    "Mostaganem-Tiaret": "XX",
    "Oasis": "XX",
    "Oran-Tlemcen": "XX",
    "Orléansville-Médéa": "XX",
    "Saoura": "XX",
    "Setif-Batna": "XX",
    "Tizi-Ouzou": "XX",
    # Anciens territoires
    "Comores": "XX",
    "Côte française des Somalis": "XX",
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


def _hors_perimetre(est_actif: bool, code_dep: str, date_deces: date | None) -> bool:
    """Vrai si un ancien sénateur est certainement antérieur au renouvellement de 2002."""
    if est_actif:
        return False
    if code_dep == "XX":
        return True
    return date_deces is not None and date_deces < DEBUT_PERIMETRE_SENAT


def _groupe_anterieur_2002(est_actif: bool, groupe: str | None) -> bool:
    """Vrai si un ancien sénateur a pour dernier groupe un groupe disparu avant 2002.

    Un sénateur actif n'est jamais écarté : s'il portait un tel sigle, il resterait
    chargé et signalé « non classé » (anomalie de source à examiner).
    """
    return not est_actif and est_groupe_senat_anterieur_2002(groupe)


def load_legislatif_senat(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    departements: list[str] | None = None,
    force: bool = False,
    inclure_anterieurs_2002: bool = False,
) -> None:
    """Charge les sénateurs depuis ODSEN_GENERAL.csv dans leg_elus et leg_mandats.

    departements : liste de noms de circonscription (ex. ['Nord', 'Oise']).
                   None = France entière (défaut).
    inclure_anterieurs_2002 : conserver les anciens sénateurs certainement antérieurs
                   au renouvellement de 2002 (défaut : écartés, voir docstring du module).
    Idempotent : DELETE leg_elus/leg_mandats WHERE source='senat_csv' puis INSERT.
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

    if departements is not None:
        df = df.filter(pl.col("Circonscription").is_in(departements))

    if df.is_empty():
        logger.error("Aucun sénateur trouvé dans %s — vérifier colonnes CSV", csv_path)
        return

    rows: list[tuple] = []
    mandat_rows: list[tuple] = []
    non_classes: Counter[tuple[str, int | None]] = Counter()
    sans_groupe: Counter[int | None] = Counter()
    groupes_anterieurs: Counter[str] = Counter()
    n_hors_perimetre = 0
    for row in df.iter_rows(named=True):
        matricule = str(row["Matricule"]).strip() if row["Matricule"] else None
        if not matricule:
            continue

        etat = str(row["État"]).strip() if row["État"] else ""
        est_actif = etat == "ACTIF"

        circo_nom = str(row["Circonscription"]).strip() if row["Circonscription"] else ""
        code_dep = _ALL_CIRCOS.get(circo_nom, "XX")

        date_deces = _parse_date(row.get("Date de décès"))
        if not inclure_anterieurs_2002 and _hors_perimetre(est_actif, code_dep, date_deces):
            n_hors_perimetre += 1
            continue

        groupe = str(row["Groupe politique"]).strip() if row["Groupe politique"] else None
        groupe = groupe or None
        if not inclure_anterieurs_2002 and _groupe_anterieur_2002(est_actif, groupe):
            groupes_anterieurs[groupe or ""] += 1
            continue

        bloc = resoudre_bloc("SENAT", groupe, None)
        if groupe is None:
            sans_groupe[None] += 1
        elif bloc is None:
            non_classes[(groupe, None)] += 1

        date_naissance = _parse_date(row.get("Date naissance"))
        # Aucune date de mandat dans ODSEN_GENERAL : NULL plutôt que la date du jour.
        date_debut = None
        date_fin = None

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
                circo_nom,
                None,  # region_nom — non disponible dans le CSV Sénat
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
        mandat_rows.append(
            (
                matricule,
                "SENAT",
                None,  # pas de législature au Sénat
                groupe,
                groupe,
                code_dep,
                None,
                date_debut,
                date_fin,
                GRANULARITE_SENAT,
                "senat_csv",
            )
        )

    if n_hors_perimetre:
        logger.info(
            "Sénat : %d ancien(s) sénateur(s) écarté(s), antérieurs au renouvellement de "
            "2002 (circonscription disparue ou décès avant le %s)",
            n_hors_perimetre,
            DEBUT_PERIMETRE_SENAT.isoformat(),
        )
    if groupes_anterieurs:
        logger.info(
            "Sénat : %d ancien(s) sénateur(s) écarté(s), dernier groupe disparu avant le "
            "renouvellement de 2002 (hors périmètre, aucun bloc attribué) : %s",
            sum(groupes_anterieurs.values()),
            ", ".join(
                f"{g} × {n}"
                for g, n in sorted(groupes_anterieurs.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
        )

    con.execute("DELETE FROM leg_elus WHERE source = 'senat_csv'")

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
            nom              = excluded.nom,
            prenom           = excluded.prenom,
            code_departement = excluded.code_departement,
            nom_departement  = excluded.nom_departement,
            region_nom       = excluded.region_nom,
            groupe_sigle     = excluded.groupe_sigle,
            groupe_nom       = excluded.groupe_nom,
            bloc_politique   = excluded.bloc_politique,
            date_debut_mandat = excluded.date_debut_mandat,
            date_fin_mandat  = excluded.date_fin_mandat,
            est_actif        = excluded.est_actif,
            profession       = excluded.profession,
            source           = excluded.source
        """,
        rows,
    )

    con.execute("DELETE FROM leg_mandats WHERE source = 'senat_csv'")
    con.executemany(
        """
        INSERT INTO leg_mandats (
            elu_id, chambre, legislature, groupe_sigle, groupe_nom,
            code_departement, num_circo, date_debut, date_fin, granularite, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        mandat_rows,
    )
    journaliser_non_classes("SENAT", non_classes)
    journaliser_sans_groupe("SENAT", sans_groupe)

    total = con.execute("SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv'").fetchone()[0]
    actifs = con.execute(
        "SELECT COUNT(*) FROM leg_elus WHERE source = 'senat_csv' AND est_actif = TRUE"
    ).fetchone()[0]
    scope = f"filtre={departements}" if departements else "France entière"
    logger.info(
        "leg_elus (Sénat, %s) : %d total (%d actifs, %d anciens)",
        scope,
        total,
        actifs,
        total - actifs,
    )

    upsert_metadata(con, "leg_elus_senat", total, "senat/ODSEN_GENERAL")
    upsert_metadata(
        con, "leg_mandats_senat", len(mandat_rows), f"senat/ODSEN_GENERAL ({GRANULARITE_SENAT})"
    )
