"""Nuance préfectorale d'élection des députés non inscrits (orientation Mathias 2026-10-04).

Un député non inscrit (groupe ``NI``) est classé selon la nuance attribuée par la
préfecture lors de son élection, convertie en bloc par ``nuances_harmonisees`` (ADR-0010).
Ce module renseigne, pour chaque mandat NI de ``leg_mandats``, la nuance retrouvée
(``nuance_election``, ``nuance_annee``, ``nuance_source``) ; la conversion en bloc est
faite par les vues (``schema_legislatif._bloc_et_source``).

Source : « Données des élections agrégées » (data.gouv.fr), fichier national
``general-results.parquet`` (résultats **par candidat** malgré son nom, gotcha n° 8),
déposé manuellement dans ``data/exploration/``. Il ne contient que les élections
générales (2002-2024), ni les partielles ni les remplaçants.

Règle d'appariement (aucune nuance devinée) :
1. élection générale de la législature du mandat (XIIe → 2002 … XVIIe → 2024) ;
2. candidat du même département, prénom identique et nom identique ou préfixe l'un de
   l'autre après normalisation (casse, accents, ponctuation ; un ``?`` de la source, accent
   perdu, vaut un caractère) — ex. « Djebbari » candidat sous « DJEBBARI-BONNET » ; le nom
   de candidature est alors cité dans la source ;
3. candidat **élu** : en tête au second tour sur ses bureaux de vote, ou plus de 50 %
   des voix au premier tour s'il n'a pas de second tour ;
4. une seule nuance parmi les candidatures élues retenues, sinon ambiguïté.
Le département suffit (pas de circonscription) : le redécoupage de 2010 (appliqué en 2012)
et l'absence de code de circonscription dans la source pour 2002, 2007 et 2024 sont sans
effet. Échec → ``nuance_election`` NULL et motif explicite dans ``nuance_source`` ; le
mandat garde le bloc du groupe NI (DIV).

Mandats non retrouvés (orientation Mathias 2026-10-06), selon la cause du mandat dans
l'AMO30 de l'Assemblée nationale (historique des mandats, Licence Ouverte) :
- remplaçant(e) (« remplacement d'un député … ») : nuance de l'élection générale de son
  titulaire (mandat de la même législature dont il ou elle est suppléant(e)), retrouvée
  par la même règle d'appariement ;
- élu(e) d'une partielle : résultats des partielles absents de l'open data (data.gouv ne
  publie que quelques partielles de 2016) → DIV, motif explicite.
Seuls l'identifiant, le nom, la législature, la cause, la date de prise de fonction, la
circonscription et les suppléants sont lus, en table temporaire.
"""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path

import duckdb
import httpx

from ministere_de_l_info._sql import ligne_unique
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

# Année de l'élection générale de chaque législature
ANNEE_ELECTION: dict[int, int] = {12: 2002, 13: 2007, 14: 2012, 15: 2017, 16: 2022, 17: 2024}

# Codes départements de la source (outre-mer, étranger) → codes Datan / leg_mandats
_DEPT_SOURCE = {
    "ZA": "971",
    "ZB": "972",
    "ZC": "973",
    "ZD": "974",
    "ZS": "975",
    "ZM": "976",
    "ZX": "977",
    "ZW": "986",
    "ZP": "987",
    "ZN": "988",
    "ZZ": "099",
}

NON_RETROUVEE = "nuance d'élection non retrouvée"
_NR_SQL = NON_RETROUVEE.replace("'", "''")
_WHERE_NI = "m.chambre = 'AN' AND m.groupe_sigle = 'NI'"

AMO_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/amo/"
    "tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
)


def telecharger_amo(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge l'AMO30 (≈ 14 Mo) en cache dans ``raw_dir/legislatif``."""
    dest = raw_dir / "legislatif" / AMO_URL.rsplit("/", 1)[1]
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement AMO30 → %s", dest)
    with httpx.stream("GET", AMO_URL, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    return dest


def _liste(x: object) -> list:
    """Le JSON AMO (converti du XML) donne un objet seul ou une liste."""
    return [] if x is None else x if isinstance(x, list) else [x]


def lire_mandats_amo(zip_path: Path) -> list[tuple]:
    """Mandats de député de l'AMO : (acteur, nom, prénom, législature, cause, prise de
    fonction, département, circonscription, suppléants)."""
    lignes = []
    with zipfile.ZipFile(zip_path) as z:
        for fichier in z.namelist():
            if not fichier.startswith("json/acteur/"):
                continue
            a = json.loads(z.read(fichier))["acteur"]
            uid = a["uid"]["#text"] if isinstance(a["uid"], dict) else a["uid"]
            ident = a["etatCivil"]["ident"]
            for m in _liste((a.get("mandats") or {}).get("mandat")):
                if m.get("typeOrgane") != "ASSEMBLEE":
                    continue
                election = m.get("election") or {}
                lieu = election.get("lieu") or {}
                suppleants = _liste((m.get("suppleants") or {}).get("suppleant"))
                lignes.append(
                    (
                        uid,
                        ident["nom"],
                        ident["prenom"],
                        int(m["legislature"]),
                        election.get("causeMandat"),
                        (m.get("mandature") or {}).get("datePriseFonction"),
                        lieu.get("numDepartement"),
                        lieu.get("numCirco"),
                        [s["suppleantRef"] for s in suppleants],
                    )
                )
    return lignes


def _charger_amo(con: duckdb.DuckDBPyConnection, lignes: list[tuple]) -> None:
    con.execute(
        "CREATE OR REPLACE TEMP TABLE _amo (acteur VARCHAR, nom VARCHAR, prenom VARCHAR, "
        "legislature INTEGER, cause VARCHAR, prise_fonction DATE, dept VARCHAR, "
        "circo VARCHAR, suppleants VARCHAR[])"
    )
    if lignes:
        con.executemany("INSERT INTO _amo VALUES (?,?,?,?,?,?,?,?,?)", lignes)


def _norm(col: str, joker: bool = False) -> str:
    """Expression SQL : majuscules sans accents ni ponctuation (``?`` → ``_`` si joker)."""
    garde = "A-Z_" if joker else "A-Z"
    expr = f"upper(strip_accents({col}))"
    if joker:
        expr = f"replace({expr}, '?', '_')"
    return f"regexp_replace({expr}, '[^{garde}]', '', 'g')"


def _resoudre(con: duckdb.DuckDBPyConnection, parquet_candidats: Path) -> None:
    """``_cibles`` (elu_id, legislature, dept, num_circo, nom, prenom) → ``_ni_resolution``."""
    annees = ", ".join(f"({leg}, {an})" for leg, an in ANNEE_ELECTION.items())
    ids = ", ".join(f"'{an}_legi_t{t}'" for an in ANNEE_ELECTION.values() for t in (1, 2))
    dept_case = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in _DEPT_SOURCE.items())
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _ni_resolution AS
        WITH ni AS (
            SELECT t.elu_id, t.legislature, a.annee, upper(t.dept) AS dept, t.num_circo,
                   {_norm("t.nom")} AS nom_n, {_norm("t.prenom")} AS prenom_n
            FROM _cibles t
            JOIN (VALUES {annees}) a(legislature, annee) ON a.legislature = t.legislature
        ),
        c AS (
            SELECT id_election, CAST(left(id_election, 4) AS INTEGER) AS annee,
                   CAST(right(id_election, 1) AS INTEGER) AS tour,
                   CASE code_departement {dept_case} ELSE code_departement END AS dept,
                   code_commune, code_bv, nom, prenom, nuance, voix
            FROM read_parquet(?)
            WHERE id_election IN ({ids})
        ),
        cand AS (  -- candidatures appariées (un candidat = nom, prénom, nuance, département)
            SELECT DISTINCT ni.elu_id, c.id_election, c.tour, c.dept, c.nom, c.prenom, c.nuance
            FROM ni JOIN c ON c.annee = ni.annee AND c.dept = ni.dept
            WHERE (ni.nom_n LIKE {_norm("c.nom", joker=True)} || '%'
                   OR {_norm("c.nom")} LIKE ni.nom_n || '%')
              AND ni.prenom_n LIKE {_norm("c.prenom", joker=True)}
        ),
        bv AS (
            SELECT DISTINCT cand.*, c.code_commune, c.code_bv
            FROM cand JOIN c USING (id_election, dept, nom, prenom, nuance)
        ),
        scores AS (  -- voix de chaque concurrent sur les bureaux du candidat apparié
            SELECT bv.elu_id, bv.id_election, bv.tour, bv.nom, bv.prenom, bv.nuance,
                   r.nom IS NOT DISTINCT FROM bv.nom AND r.prenom IS NOT DISTINCT FROM bv.prenom
                   AND r.nuance IS NOT DISTINCT FROM bv.nuance AS lui,
                   SUM(r.voix) AS voix
            FROM bv JOIN c r USING (id_election, code_commune, code_bv)
            GROUP BY bv.elu_id, bv.id_election, bv.tour, bv.nom, bv.prenom, bv.nuance,
                     r.nom, r.prenom, r.nuance
        ),
        tours AS (
            SELECT elu_id, id_election, tour, nom, prenom, nuance,
                   MAX(voix) FILTER (WHERE lui) AS voix_lui,
                   MAX(voix) FILTER (WHERE NOT lui) AS voix_max_autres,
                   SUM(voix) AS voix_total
            FROM scores GROUP BY ALL
        ),
        dernier AS (  -- dernier tour disputé par chaque candidature
            SELECT *, tour = MAX(tour) OVER (PARTITION BY elu_id, nom, prenom, nuance) AS est_dernier
            FROM tours
        ),
        elus AS (
            SELECT elu_id, nom, prenom, nuance FROM dernier
            WHERE est_dernier AND (
                (tour = 2 AND voix_lui > COALESCE(voix_max_autres, 0))
                OR (tour = 1 AND 2 * voix_lui > voix_total)
            )
        )
        SELECT ni.elu_id, ni.legislature, ni.annee, ni.dept, ni.num_circo,
               (SELECT list(DISTINCT nuance ORDER BY nuance) FROM elus
                WHERE elus.elu_id = ni.elu_id) AS nuances_elu,
               (SELECT string_agg(DISTINCT elus.nom || ' ' || elus.prenom, ', ') FROM elus
                WHERE elus.elu_id = ni.elu_id
                  AND NOT ni.nom_n LIKE {_norm("elus.nom", joker=True)}) AS nom_candidature,
               (SELECT COUNT(*) FROM cand WHERE cand.elu_id = ni.elu_id) AS nb_candidatures
        FROM ni
        """,
        [str(parquet_candidats)],
    )


def attribuer_nuances_non_inscrits(
    con: duckdb.DuckDBPyConnection, parquet_candidats: Path, amo_zip: Path | None = None
) -> int:
    """Renseigne la nuance d'élection des mandats NI de l'AN ; renvoie le nombre retrouvé.

    ``amo_zip`` (AMO30) : traite les remplaçants et élus de partielles non retrouvés.
    """
    con.execute(
        "UPDATE leg_mandats SET nuance_election = NULL, nuance_annee = NULL, "
        "nuance_source = NULL WHERE nuance_source IS NOT NULL"
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cibles AS
        SELECT m.elu_id, m.legislature, m.code_departement AS dept, m.num_circo,
               e.nom, e.prenom
        FROM leg_mandats m JOIN leg_elus e ON e.id = m.elu_id AND e.chambre = m.chambre
        WHERE {_WHERE_NI}
        """
    )
    _resoudre(con, parquet_candidats)
    con.execute(
        f"""
        UPDATE leg_mandats m SET
            nuance_election = CASE WHEN len(r.nuances_elu) = 1 THEN r.nuances_elu[1] END,
            nuance_annee = CASE WHEN len(r.nuances_elu) = 1 THEN r.annee END,
            nuance_source = CASE
                WHEN len(r.nuances_elu) = 1 THEN
                    'législatives ' || r.annee || ', ' || r.dept || '-' || r.num_circo
                    || COALESCE(', candidature « ' || r.nom_candidature || ' »', '')
                WHEN len(r.nuances_elu) > 1 THEN
                    '{_NR_SQL} : plusieurs candidatures élues homonymes (législatives '
                    || r.annee || ', ' || r.dept || ')'
                WHEN r.nb_candidatures > 0 THEN
                    '{_NR_SQL} : candidat(e) non élu(e) aux législatives générales '
                    || r.annee || ' (' || r.dept || ') — élection partielle ou remplacement'
                ELSE
                    '{_NR_SQL} : absent(e) des candidats des législatives générales '
                    || r.annee || ' (' || r.dept || ') — remplaçant(e) ou élection partielle'
            END
        FROM _ni_resolution r
        WHERE m.elu_id = r.elu_id AND m.legislature = r.legislature AND {_WHERE_NI}
        """
    )
    if amo_zip is not None:
        _charger_amo(con, lire_mandats_amo(amo_zip))
        _remplacants_et_partielles(con, parquet_candidats)
        con.execute("DROP TABLE _amo")
    n_total, n_ok = ligne_unique(
        con.execute(
            "SELECT COUNT(*), COUNT(nuance_election) FROM leg_mandats WHERE nuance_source IS NOT NULL"
        )
    )
    con.execute("DROP TABLE _ni_resolution")
    con.execute("DROP TABLE _cibles")
    logger.info(
        "Non-inscrits AN : %d mandat(s), nuance d'élection retrouvée pour %d", n_total, n_ok
    )
    if n_total > n_ok:
        logger.warning(
            "%d mandat(s) NI sans nuance d'élection : bloc du groupe (DIV)", n_total - n_ok
        )
    source = f"data.gouv élections agrégées ({parquet_candidats.name})"
    if amo_zip is not None:
        source += f" + Assemblée nationale ({amo_zip.name})"
    upsert_metadata(con, "leg_mandats_nuances_ni", n_ok, source)
    return n_ok


def _remplacants_et_partielles(con: duckdb.DuckDBPyConnection, parquet_candidats: Path) -> None:
    """Mandats NI non retrouvés : nuance du titulaire (remplaçant) ou motif partielle."""
    # Titulaire = mandat issu de l'élection générale de la même législature dont le NI est
    # suppléant. Plusieurs titulaires distincts (aucun cas dans l'AMO au 2026-10-04) :
    # mandat écarté, il garde le motif générique.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cibles AS
        SELECT DISTINCT m.elu_id, m.legislature, t.dept,
               TRY_CAST(t.circo AS INTEGER) AS num_circo, t.nom, t.prenom
        FROM leg_mandats m
        JOIN _amo r ON r.acteur = m.elu_id AND r.legislature = m.legislature
        JOIN _amo t ON t.legislature = r.legislature AND list_contains(t.suppleants, r.acteur)
        WHERE {_WHERE_NI} AND m.nuance_election IS NULL
          AND r.cause ILIKE 'remplacement%' AND t.cause = 'élections générales'
        QUALIFY COUNT(DISTINCT t.acteur) OVER (PARTITION BY m.elu_id, m.legislature) = 1
        """
    )
    _resoudre(con, parquet_candidats)
    con.execute(
        f"""
        UPDATE leg_mandats m SET
            nuance_election = CASE WHEN len(r.nuances_elu) = 1 THEN r.nuances_elu[1] END,
            nuance_annee = CASE WHEN len(r.nuances_elu) = 1 THEN r.annee END,
            nuance_source = CASE
                WHEN len(r.nuances_elu) = 1 THEN
                    'remplaçant(e) de ' || t.prenom || ' ' || t.nom || ', élu(e) aux législatives '
                    || r.annee || ', ' || r.dept || '-' || r.num_circo
                    || COALESCE(', candidature « ' || r.nom_candidature || ' »', '')
                ELSE
                    '{_NR_SQL} : remplaçant(e) de ' || t.prenom || ' ' || t.nom
                    || ', nuance du titulaire non retrouvée (législatives ' || r.annee
                    || ', ' || r.dept || ')'
            END
        FROM _ni_resolution r JOIN _cibles t USING (elu_id, legislature)
        WHERE m.elu_id = r.elu_id AND m.legislature = r.legislature AND {_WHERE_NI}
        """
    )
    con.execute(
        f"""
        UPDATE leg_mandats m SET nuance_source =
            '{_NR_SQL} : élu(e) lors d''une élection partielle (prise de fonction le '
            || strftime(p.prise_fonction, '%d/%m/%Y') || ', ' || p.dept || '-' || p.circo
            || ') — résultats des partielles non publiés en open data'
        FROM (
            SELECT acteur, legislature, arg_max(dept, prise_fonction) AS dept,
                   arg_max(circo, prise_fonction) AS circo, MAX(prise_fonction) AS prise_fonction
            FROM _amo WHERE cause ILIKE 'élection partielle%' GROUP BY ALL
        ) p
        WHERE p.acteur = m.elu_id AND p.legislature = m.legislature AND {_WHERE_NI}
          AND m.nuance_election IS NULL AND m.nuance_source NOT LIKE '%remplaçant(e) de %'
        """
    )
