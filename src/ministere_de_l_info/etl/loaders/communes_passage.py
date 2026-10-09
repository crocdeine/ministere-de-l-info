"""Table de passage des communes fusionnées vers les communes actuelles (INSEE, COG).

Décision de Mathias du 2026-10-07 : les résultats électoraux d'une commune disparue par
fusion sont rattachés à la commune actuelle qui l'a absorbée (géographie actuelle).

Source : INSEE, Code officiel géographique, fichier des mouvements des communes
(`v_mvt_commune_<millésime>.csv`, UTF-8, séparateur virgule), Licence Ouverte 2.0.

Règle : arêtes « commune avant → commune après » des événements où le code change
(fusions 31-34, changements de code 41 et de département 50 : TYPECOM_AV = TYPECOM_AP =
'COM', COM_AV ≠ COM_AP). Les créations et rétablissements (20, 21 : scissions) ne sont
pas des fusions : ils sont comptés, jamais utilisés pour répartir des voix. Pour un code
ancien, l'arête la plus récente est retenue, puis la chaîne est suivie jusqu'à un code
présent dans geographies_communes. Seuls les codes absents de ce référentiel sont
inscrits dans communes_passage.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import httpx

from ministere_de_l_info._sql import ligne_unique
from ministere_de_l_info.etl.schema_elections import PASSAGE_DDL

logger = logging.getLogger(__name__)

MILLESIME_COG = 2026
URL_MVT_COMMUNE = "https://www.insee.fr/fr/statistiques/fichier/8740222/v_mvt_commune_2026.csv"
_ENTETE_ATTENDUE = b'"MOD","DATE_EFF","TYPECOM_AV","COM_AV"'
_MODS_FUSION = ("31", "32", "33", "34", "41", "50")
_MODS_SCISSION = ("20", "21")
_PROFONDEUR_MAX = 10


def telecharger_mvt(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge le fichier des mouvements des communes (fichier temporaire contrôlé)."""
    dest = raw_dir / "cog" / f"v_mvt_commune_{MILLESIME_COG}.csv"
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with httpx.stream("GET", URL_MVT_COMMUNE, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    if not tmp.read_bytes()[:200].lstrip(b"\xef\xbb\xbf").startswith(_ENTETE_ATTENDUE):
        tmp.unlink()
        raise RuntimeError(
            "insee.fr n'a pas renvoyé le fichier v_mvt_commune attendu ; cache conservé."
        )
    tmp.replace(dest)
    logger.info("Mouvements des communes téléchargés : %s", dest)
    return dest


def construire_passage(con: duckdb.DuckDBPyConnection, csv_mvt: Path) -> int:
    """(Re)construit communes_passage depuis le fichier des mouvements. Idempotent.

    Une chaîne qui ne rejoint aucune commune du référentiel en _PROFONDEUR_MAX étapes
    (cycle, code disparu sans successeur) est journalisée et non rattachée : ses résultats
    restent écartés et comptés dans elections_ecarts_chargement. Retourne le nombre de
    codes rattachés.
    """
    con.execute(PASSAGE_DDL)
    fusions = ", ".join(f"'{m}'" for m in _MODS_FUSION)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _aretes AS
        SELECT code_ancien, code_suivant, date_effet, mod, libelle_ancien FROM (
            SELECT COM_AV AS code_ancien, COM_AP AS code_suivant,
                   CAST(DATE_EFF AS DATE) AS date_effet, MOD AS mod,
                   LIBELLE_AV AS libelle_ancien,
                   ROW_NUMBER() OVER (PARTITION BY COM_AV
                                      ORDER BY CAST(DATE_EFF AS DATE) DESC, COM_AP) AS rang
            FROM read_csv('{csv_mvt}', all_varchar = true, header = true)
            WHERE MOD IN ({fusions}) AND TYPECOM_AV = 'COM' AND TYPECOM_AP = 'COM'
              AND COM_AV <> COM_AP
        ) WHERE rang = 1
    """)  # noqa: S608
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _chaines AS
        WITH RECURSIVE ch(code_ancien, code_courant, date_effet, mod, etape, libelle_ancien) AS (
            SELECT a.code_ancien, a.code_suivant, a.date_effet, a.mod, 1, a.libelle_ancien
            FROM _aretes a
            WHERE a.code_ancien NOT IN (SELECT code_insee FROM geographies_communes)
            UNION ALL
            SELECT ch.code_ancien, a.code_suivant, a.date_effet, a.mod, ch.etape + 1,
                   ch.libelle_ancien
            FROM ch JOIN _aretes a ON a.code_ancien = ch.code_courant
            WHERE ch.code_courant NOT IN (SELECT code_insee FROM geographies_communes)
              AND ch.etape < {_PROFONDEUR_MAX}
        )
        SELECT * FROM ch
    """)  # noqa: S608
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM communes_passage")
        con.execute("""
            INSERT INTO communes_passage
                (code_ancien, code_actuel, date_effet, type_evenement, libelle_ancien)
            SELECT code_ancien, code_courant, date_effet, mod, libelle_ancien
            FROM _chaines
            WHERE code_courant IN (SELECT code_insee FROM geographies_communes)
            QUALIFY ROW_NUMBER() OVER (PARTITION BY code_ancien ORDER BY etape) = 1
        """)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    non_resolus = con.execute("""
        SELECT DISTINCT code_ancien FROM _chaines
        WHERE code_ancien NOT IN (SELECT code_ancien FROM communes_passage)
        ORDER BY 1 LIMIT 10
    """).fetchall()
    if non_resolus:
        # Codes dont la chaîne ne rejoint pas le référentiel : signalés, non rattachés
        logger.warning("Chaînes de fusion non résolues (extrait) : %s", non_resolus)
    scissions = ", ".join(f"'{m}'" for m in _MODS_SCISSION)
    n_scissions = ligne_unique(
        con.execute(
            f"SELECT COUNT(*) FROM read_csv('{csv_mvt}', all_varchar = true, header = true) "  # noqa: S608
            f"WHERE MOD IN ({scissions}) AND TYPECOM_AP = 'COM'"
        )
    )[0]
    n = ligne_unique(con.execute("SELECT COUNT(*) FROM communes_passage"))[0]
    logger.info(
        "communes_passage : %d codes anciens rattachés ; %d créations/rétablissements "
        "(scissions) recensés, non répartis",
        n,
        n_scissions,
    )
    return int(n)
