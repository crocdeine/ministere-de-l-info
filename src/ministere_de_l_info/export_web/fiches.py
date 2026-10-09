"""Fiches territoire « commune » (lot A3) : un fichier ``departements/<dep>/fiches.json.gz``.

Complète ``communes.json.gz`` et ``bureaux.json.gz`` (résultats par scrutin, écrits par
``export.py``) avec ce qui ne dépend pas du scrutin : identité (département, région, EPCI,
circonscriptions), population légale, économie (Hauts-de-France seulement : ``null`` ailleurs),
élus en cours de mandat et communes anciennes rattachées (fusions, table de passage COG).

Lecture seule ; agrégations en SQL. Absence = ``null`` (« n.d. »), jamais 0.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# Indicateurs économiques de la fiche (vues des pages Streamlit, aucune valeur recalculée).
INDICATEURS_ECONOMIE: tuple[str, ...] = (
    "taux_pauvrete",
    "niveau_vie_median",
    "tx_chomage_dec",
    "part_ouvriers_employes",
    "part_emploi_industriel",
    "part_logements_sociaux",
    "nb_foyers_rsa",
    "apl_medecins",
)
# Part minimale de la surface communale dans une circonscription (exclut les contacts de bord ;
# à défaut, la circonscription de plus grande part est retenue).
PART_MIN_CIRCO: float = 0.01
# Départements des résultats absents de `geographies_departements` (Saint-Pierre-et-Miquelon :
# `NR` dans les contours IGN, `975` dans les résultats).
LIBELLES_OUTRE_MER: dict[str, tuple[str, str]] = {
    "975": ("Saint-Pierre-et-Miquelon", "Collectivités d'outre-mer"),
}


def _preparer_fiches(con: duckdb.DuckDBPyConnection) -> None:
    """Tables temporaires ``_circos``, ``_fusions``, ``_eco`` (``_communes``, ``_scrutins`` existent)."""
    # Circonscriptions : intersection des contours (gotcha 10 : jamais de liste trouvée sur le
    # web) ; une commune partagée (Paris, Amiens) en compte plusieurs. Sans contour commun
    # (îles, 975) : circonscription de ses derniers résultats législatifs, sinon aucune (n.d.).
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _circos AS
        WITH x AS (
            SELECT g.code_insee, c.code,
                   ST_Area(ST_Intersection(ST_MakeValid(g.geometry), ST_MakeValid(c.geometry)))
                   / NULLIF(ST_Area(g.geometry), 0) AS part
            FROM geographies_communes g
            JOIN geographies_circonscriptions c
              ON c.code_departement = g.code_departement AND ST_Intersects(g.geometry, c.geometry)
            WHERE g.code_insee IN (SELECT code_insee FROM _communes)
        ),
        spatial AS (
            SELECT code_insee, list(code ORDER BY code) AS circos, 'contours' AS origine
            FROM (SELECT *, MAX(part) OVER (PARTITION BY code_insee) AS m FROM x)
            WHERE part >= {PART_MIN_CIRCO} OR part = m
            GROUP BY code_insee
        ),
        resultats AS (
            SELECT r.code_commune AS code_insee, list(DISTINCT r.code_circo ORDER BY r.code_circo)
                   AS circos, 'resultats' AS origine
            FROM resultats_participation r
            JOIN (SELECT id_election FROM _scrutins WHERE type_scrutin = 'legi'
                  ORDER BY id_election DESC LIMIT 1) d USING (id_election)
            WHERE r.code_circo IS NOT NULL
              AND r.code_commune NOT IN (SELECT code_insee FROM spatial)
            GROUP BY r.code_commune
        )
        SELECT * FROM spatial UNION ALL SELECT * FROM resultats
        """  # noqa: S608 — constante numérique du module
    )
    # Communes disparues dont les résultats sont rattachés à la commune actuelle, par scrutin.
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _fusions AS
        SELECT i.scrutin, r.code_commune, list(DISTINCT r.code_commune_origine
                                               ORDER BY r.code_commune_origine) AS anciennes
        FROM resultats_participation r
        JOIN (SELECT id_election, (ROW_NUMBER() OVER (ORDER BY id_election) - 1)::INT AS scrutin
              FROM _scrutins) i USING (id_election)
        WHERE r.code_commune_origine IS NOT NULL
          AND r.code_commune IN (SELECT code_insee FROM _communes)
        GROUP BY ALL
        """
    )
    cols = ", ".join(INDICATEURS_ECONOMIE)
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _eco_tout AS
        SELECT code_commune, annee, {cols}
        FROM v_economie_commune e
        FULL JOIN (SELECT code_commune, annee, nb_foyers_rsa, apl_medecins
                   FROM v_economie_sociale_commune) s USING (code_commune, annee)
        """  # noqa: S608 — noms de colonnes issus du module
    )


def _noms_anciennes(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """Noms des communes disparues (``communes_passage.libelle_ancien``, COG INSEE).

    Colonne absente (base antérieure au lot A3) : aucun nom, la fiche affiche le code.
    """
    existe = con.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = 'communes_passage' AND column_name = 'libelle_ancien'"
    ).fetchone()
    if not existe or not existe[0]:
        logger.warning("communes_passage.libelle_ancien absente : noms des anciennes communes n.d.")
        return {}
    return dict(
        con.execute(
            "SELECT code_ancien, libelle_ancien FROM communes_passage "
            "WHERE libelle_ancien IS NOT NULL AND code_ancien IN (SELECT DISTINCT unnest(anciennes) "
            "FROM _fusions)"
        ).fetchall()
    )


def _elus(con: duckdb.DuckDBPyConnection, dep: str) -> list[dict[str, Any]]:
    """Députés et sénateurs en cours de mandat du département (bloc du groupe, ADR-0011)."""
    rows = con.execute(
        """
        SELECT chambre,
               CASE WHEN chambre = 'AN'
                    THEN upper(code_departement) || '-' || lpad(num_circo::VARCHAR, 2, '0')
               END AS circo,
               prenom, nom, groupe_sigle, groupe_nom, bloc_final
        -- Bases publiées avant le correctif de la vue : Corse en « 2a »/« 2b » (Datan).
        FROM v_elus_actuels WHERE upper(code_departement) = ?
        ORDER BY chambre, circo, nom, prenom
        """,
        [dep],
    ).fetchall()
    cles = ("chambre", "circo", "prenom", "nom", "groupe", "groupe_nom", "bloc")
    return [dict(zip(cles, r, strict=True)) for r in rows]


def _compter_ecarts(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Données non affichées dans les fiches : comptées et signalées, jamais réparties."""
    hors = con.execute(
        "SELECT COUNT(*) FROM v_elus_actuels "
        "WHERE upper(code_departement) NOT IN (SELECT DISTINCT code_departement FROM _communes)"
    ).fetchone()
    # Économie publiée sous un code de commune disparue : les taux ne s'additionnent pas.
    eco = con.execute(
        "SELECT COUNT(DISTINCT code_commune) FROM _eco_tout e "
        "WHERE code_commune NOT IN (SELECT code_insee FROM geographies_communes)"
    ).fetchone()
    ecarts = {
        "elus_hors_perimetre": int(hors[0]) if hors else 0,
        "economie_communes_anciennes": int(eco[0]) if eco else 0,
    }
    for cle, n in ecarts.items():
        if n:
            logger.warning("Fiches : %s = %d (non affichés)", cle, n)
    return ecarts


def ecrire_fiches(
    con: duckdb.DuckDBPyConnection,
    sortie: Path,
    ecrire: Callable[[Path, Any], None],
) -> dict[str, int]:
    """Un fichier ``fiches.json.gz`` par département de ``_communes`` ; renvoie les écarts."""
    _preparer_fiches(con)
    communes = con.execute(
        """
        SELECT c.code_departement, c.code_insee, c.nom, d.nom, r.nom, ep.nom, ci.circos, ci.origine
        FROM _communes c
        LEFT JOIN geographies_communes g USING (code_insee)
        LEFT JOIN geographies_departements d ON d.code_insee = g.code_departement
        LEFT JOIN geographies_regions r ON r.code_insee = g.code_region
        LEFT JOIN geographies_epci ep ON ep.code_siren = g.code_epci
        LEFT JOIN _circos ci USING (code_insee)
        ORDER BY 1, 2
        """
    ).fetchall()
    population: dict[str, list[list[int]]] = {}
    for code, annee, pop in con.execute(
        "SELECT code_commune, annee, population_municipale::BIGINT FROM v_population_commune "
        "WHERE code_commune IN (SELECT code_insee FROM _communes) ORDER BY 1, 2"
    ).fetchall():
        population.setdefault(code, []).append([annee, pop])
    noms = _noms_anciennes(con)
    fusions: dict[str, dict[str, list[str]]] = {}
    for scrutin, code, anciennes in con.execute("SELECT * FROM _fusions ORDER BY 2, 1").fetchall():
        fusions.setdefault(code, {})[str(scrutin)] = anciennes
    economie: dict[str, dict[str, list[Any]]] = {}
    for row in con.execute(
        "SELECT * FROM _eco_tout WHERE code_commune IN (SELECT code_insee FROM _communes) "
        "ORDER BY code_commune, annee"
    ).fetchall():
        e = economie.setdefault(row[0], {"annee": [], **{k: [] for k in INDICATEURS_ECONOMIE}})
        e["annee"].append(row[1])
        for k, v in zip(INDICATEURS_ECONOMIE, row[2:], strict=True):
            e[k].append(None if v is None else round(float(v), 2))

    par_dep: dict[str, dict[str, Any]] = {}
    for dep, code, nom, nom_dep, region, epci, circos, origine in communes:
        om = LIBELLES_OUTRE_MER.get(dep, (None, None))
        f = par_dep.setdefault(
            dep,
            {
                "departement": {"code": dep, "nom": nom_dep or om[0], "region": region or om[1]},
                "communes": {},
            },
        )
        anciennes = sorted({a for liste in fusions.get(code, {}).values() for a in liste})
        f["communes"][code] = {
            "nom": nom,
            "epci": epci,
            "circos": circos or [],
            # `contours` (intersection) ou `resultats` (repli : derniers résultats législatifs).
            "circos_origine": origine,
            "population": population.get(code, []),
            "fusions": fusions.get(code, {}),
            "noms_anciennes": {a: noms.get(a) for a in anciennes},
            # null : hors périmètre (économie chargée pour les Hauts-de-France seulement).
            "economie": economie.get(code),
        }
    for dep, f in par_dep.items():
        f["elus"] = _elus(con, dep)
        ecrire(sortie / "departements" / dep / "fiches.json.gz", f)
    return _compter_ecarts(con)
