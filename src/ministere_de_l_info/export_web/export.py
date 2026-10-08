"""Export des données de l'application web : élections, France entière (ADR-0015).

Lit la base DuckDB en LECTURE SEULE (vues ``v_resultats_candidats_avec_bloc``,
``resultats_participation``, ``geographies_communes`` ; aucun classement modifié) et écrit :

- ``manifest.json`` : contrat de données (version de schéma, date, empreinte SHA256 et taille de
  chaque fichier, sources et licences, scrutins, blocs, codage des états de la carte) ;
- ``communes.pmtiles`` : contours des communes (tippecanoe), propriétés ``code`` et ``s`` ;
  ``s`` = un caractère par scrutin, dans l'ordre de ``manifest.scrutins`` ;
- ``communes.json.gz`` : codes et noms des communes (ordre de référence des colonnes) ;
- ``scrutins/<id>.json.gz`` : résultats d'un scrutin par commune, colonnes alignées sur
  ``communes.json.gz`` (carte nationale, infobulle) ;
- ``departements/<dep>/communes.json.gz`` et ``bureaux.json.gz`` : tous scrutins, par commune et
  par bureau de vote (fiche territoire, lot A3).

Toutes les agrégations sont faites en SQL. Absence = ``null`` (affichée « n.d. »), jamais 0.
Participation = Σ votants / Σ inscrits (même formule que ``v_participation_commune_pres``).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import shutil
import struct
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from ministere_de_l_info._blocs_politiques import (
    BLOCS_ORDERED,
    COULEURS_BLOCS,
    LIBELLES_BLOCS,
    legende_classement_blocs,
    methode_classement,
)
from ministere_de_l_info.sources import SOURCES, mention
from ministere_de_l_info.viz._display import COULEUR_ND

logger = logging.getLogger(__name__)

VERSION_SCHEMA: int = 2  # 2 : état « aucun scrutin », colonnes etat et total
# Caractères de la propriété `s` des tuiles : a-f = blocs (ordre de BLOCS_ORDERED).
CARACTERES: dict[str, str] = {b: "abcdef"[i] for i, b in enumerate(BLOCS_ORDERED)}
# `.` n.d. : lignes de résultat sans voix exploitables (dont 0 voix dans la source) ;
# `x` aucun scrutin : aucune ligne pour la commune à ce tour (pas de second tour, commune
# hors du champ publié, comme les municipales 2008 sous 3 500 habitants).
EGALITE, NON_CLASSE, ABSENT, AUCUN_SCRUTIN = "=", "n", ".", "x"
# Voix par bloc, puis voix des candidats ou listes sans bloc (nuance non classée).
COLONNES_VOIX: list[str] = [*BLOCS_ORDERED, "NC"]
COLONNES_SCRUTIN: list[str] = [
    "inscrits",
    "votants",
    "exprimes",
    "participation",
    "part_tete",
    "etat",  # caractère d'état, comme dans les tuiles (sélection au clavier)
    "total",  # somme des voix de la source (0 voix : n.d. signalé dans l'infobulle)
    *COLONNES_VOIX,
]
TYPES_SCRUTIN: dict[str, str] = {
    "pres": "Présidentielle",
    "legi": "Législatives",
    "euro": "Européennes",
    "regi": "Régionales",
    "dpmt": "Départementales",
    "cant": "Cantonales",
    "muni": "Municipales",
}
TAILLE_MAX_BRUTE: int = 8_000_000  # octets, avant compression (ADR-0015)
LICENCE_BASE: dict[str, str] = {
    "nom": "ODbL 1.0",
    "url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "mention": (
        "Données dérivées de la base ministere-de-l-info, mises à disposition sous licence "
        "ODbL 1.0 ; les contenus restent soumis à la licence de leur producteur."
    ),
}


def _filtre_dep(departements: list[str] | None, colonne: str = "code_departement") -> str:
    if not departements:
        return ""
    if not all(d.isalnum() and len(d) <= 3 for d in departements):
        raise ValueError(f"Codes département invalides : {departements}")
    return f"AND {colonne} IN ({', '.join(repr(d) for d in departements)})"


def _sql_agregat(departements: list[str] | None, *, bureau: bool) -> str:
    """Participation et voix par bloc, par commune (ou par bureau de vote) et par scrutin."""
    cle = "code_departement, code_commune" + (", code_bv" if bureau else "")
    voix = ", ".join(
        f"SUM(voix) FILTER (WHERE bloc = '{b}')::BIGINT AS \"{b}\"" for b in BLOCS_ORDERED
    )
    # Une ligne de voix existe : les blocs sans candidat valent 0 voix (vrai zéro) ;
    # aucune ligne de voix : null (n.d.).
    sel = ", ".join(
        f'CASE WHEN v.a_voix THEN COALESCE(v."{c}", 0) END AS "{c}"' for c in COLONNES_VOIX
    )
    f = _filtre_dep(departements)
    return f"""
        WITH p AS (
            SELECT id_election, {cle}, SUM(inscrits)::BIGINT AS inscrits, SUM(votants)::BIGINT AS votants,
                   SUM(exprimes)::BIGINT AS exprimes
            FROM resultats_participation
            WHERE id_election IN (SELECT id_election FROM _scrutins) {f}
            GROUP BY ALL
        ),
        v AS (
            SELECT id_election, {cle}, {voix}, SUM(voix) FILTER (WHERE bloc IS NULL)::BIGINT AS "NC",
                   SUM(voix)::BIGINT AS total, TRUE AS a_voix
            FROM v_resultats_candidats_avec_bloc
            WHERE id_election IN (SELECT id_election FROM _scrutins) {f}
            GROUP BY ALL
        )
        SELECT id_election, {cle}, p.inscrits, p.votants, p.exprimes, v.total, {sel}
        FROM p FULL JOIN v USING (id_election, {cle})
    """  # noqa: S608 — codes département validés, noms de blocs issus du code


def _sql_etat() -> str:
    """Caractère d'état d'une commune pour un scrutin (table ``_c`` jointe, ``m`` = max)."""
    cols = [f'c."{c}"' for c in COLONNES_VOIX]
    tete = " + ".join(f"({c} = m)::INT" for c in cols)
    quel = " ".join(
        f"WHEN {c} = m THEN '{CARACTERES.get(n, NON_CLASSE)}'"
        for c, n in zip(cols, COLONNES_VOIX, strict=True)
    )
    return f"""
        CASE
            WHEN c.code_commune IS NULL THEN '{AUCUN_SCRUTIN}'
            WHEN m IS NULL OR m <= 0 THEN '{ABSENT}'
            WHEN {tete} > 1 THEN '{EGALITE}'
            ELSE CASE {quel} END
        END
    """


def _preparer(con: duckdb.DuckDBPyConnection, departements: list[str] | None) -> None:
    """Tables temporaires : ``_scrutins``, ``_communes``, ``_c`` (agrégat), ``_e`` (états)."""
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _scrutins AS
        SELECT e.* FROM elections e
        WHERE EXISTS (SELECT 1 FROM resultats_candidats r WHERE r.id_election = e.id_election)
        """
    )
    # Département pris dans les résultats quand ils existent : `geographies_communes` porte
    # `NR` pour Saint-Pierre-et-Miquelon (97501, 97502), les résultats `975`.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _communes AS
        SELECT * FROM (
            SELECT g.code_insee, g.nom, COALESCE(r.dep, g.code_departement) AS code_departement
            FROM geographies_communes g
            LEFT JOIN (
                SELECT code_commune, ANY_VALUE(code_departement) AS dep
                FROM resultats_participation GROUP BY ALL
            ) r ON r.code_commune = g.code_insee
            WHERE g.geometry_simplified_communal IS NOT NULL
        ) WHERE TRUE {_filtre_dep(departements)}
        """  # noqa: S608
    )
    con.execute(f"CREATE OR REPLACE TEMP TABLE _c AS {_sql_agregat(departements, bureau=False)}")
    greatest = ", ".join(f'c."{c}"' for c in COLONNES_VOIX)
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _e AS
        SELECT s.id_election, g.code_insee, g.code_departement, c.inscrits, c.votants,
               c.exprimes, c.total, {", ".join(f'c."{x}"' for x in COLONNES_VOIX)},
               GREATEST({greatest}) AS m,
               {_sql_etat()} AS etat
        FROM _communes g
        CROSS JOIN _scrutins s
        LEFT JOIN _c c ON c.code_commune = g.code_insee AND c.id_election = s.id_election
        """  # noqa: S608
    )


def _json_gz(chemin: Path, contenu: Any, fichiers: dict[str, dict[str, Any]], racine: Path) -> None:
    """JSON compact compressé (gzip reproductible) ; contrôle la taille brute."""
    brut = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(brut) > TAILLE_MAX_BRUTE:
        logger.warning("%s : %d octets bruts (> %d)", chemin.name, len(brut), TAILLE_MAX_BRUTE)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(gzip.compress(brut, compresslevel=9, mtime=0))
    fichiers[chemin.relative_to(racine).as_posix()] = {"brut": len(brut)}


def _colonnes(df: pl.DataFrame) -> dict[str, list[Any]]:
    return df.to_dict(as_series=False)


def _ecrire_scrutins(
    con: duckdb.DuckDBPyConnection, sortie: Path, fichiers: dict[str, dict[str, Any]]
) -> None:
    """Un fichier par scrutin, colonnes alignées sur l'ordre des codes de ``communes.json.gz``."""
    lettres = ", ".join(f"'{c}'" for c in CARACTERES.values())
    df = con.execute(
        f"""
        SELECT id_election, inscrits, votants, exprimes,
               ROUND(100.0 * votants / NULLIF(inscrits, 0), 2)::DOUBLE AS participation,
               -- Part du bloc en tête : seulement si un bloc est seul en tête et si la somme
               -- des voix ne dépasse pas les exprimés (scrutin plurinominal : non comparable).
               CASE WHEN etat IN ({lettres}) AND exprimes > 0 AND total <= exprimes
                    THEN ROUND(100.0 * m / exprimes, 2)::DOUBLE END AS part_tete,
               etat, total, {", ".join(f'"{c}"' for c in COLONNES_VOIX)}
        FROM _e ORDER BY id_election, code_insee
        """  # noqa: S608
    ).pl()
    for (id_election,), part in df.group_by("id_election", maintain_order=True):
        _json_gz(
            sortie / "scrutins" / f"{id_election}.json.gz",
            _colonnes(part.select(COLONNES_SCRUTIN)),
            fichiers,
            sortie,
        )


def _ecrire_departements(
    con: duckdb.DuckDBPyConnection,
    sortie: Path,
    fichiers: dict[str, dict[str, Any]],
    departements: list[str] | None,
) -> None:
    """Par département : communes et bureaux de vote, tous scrutins (lignes présentes seulement)."""
    for nom, sql, ordre in (
        ("communes", "SELECT * FROM _c", ""),
        ("bureaux", _sql_agregat(departements, bureau=True), "a.code_bv,"),
    ):
        # `scrutin` = rang dans manifest.scrutins ; communes sans contour exclues (comme la carte).
        df = con.execute(
            f"""
            SELECT i.scrutin, a.* EXCLUDE (id_election, total)
            FROM ({sql}) a
            JOIN (SELECT id_election, (ROW_NUMBER() OVER (ORDER BY id_election) - 1)::INT
                  AS scrutin FROM _scrutins) i USING (id_election)
            WHERE a.code_commune IN (SELECT code_insee FROM _communes)
            ORDER BY a.code_departement, a.code_commune, {ordre} i.scrutin
            """  # noqa: S608
        ).pl()
        for (dep,), part in df.group_by("code_departement", maintain_order=True):
            _json_gz(
                sortie / "departements" / str(dep) / f"{nom}.json.gz",
                _colonnes(part.drop("code_departement")),
                fichiers,
                sortie,
            )


def _ecrire_tuiles(
    con: duckdb.DuckDBPyConnection, sortie: Path, tippecanoe: str, detail_bas: int
) -> None:
    """GeoJSONSeq → PMTiles. Aucune commune abandonnée ni fusionnée à aucun zoom."""
    seq = sortie / "communes.geojsonl"
    rows = con.execute(
        """
        SELECT g.code_insee, string_agg(e.etat, '' ORDER BY e.id_election) AS s,
               ST_AsGeoJSON(ANY_VALUE(g.geometry_simplified_communal))
        FROM geographies_communes g JOIN _e e USING (code_insee)
        GROUP BY g.code_insee ORDER BY g.code_insee
        """
    ).fetchall()
    try:
        with seq.open("w", encoding="utf-8") as f:
            for code, s, geojson in rows:
                props = json.dumps({"code": code, "s": s}, separators=(",", ":"))
                f.write(f'{{"type":"Feature","properties":{props},"geometry":{geojson}}}\n')
        _tippecanoe(tippecanoe, seq, sortie / "communes.pmtiles", detail_bas)
    finally:
        seq.unlink(missing_ok=True)


def _tippecanoe(tippecanoe: str, seq: Path, pmtiles: Path, detail_bas: int) -> None:
    subprocess.run(  # noqa: S603
        [
            tippecanoe,
            *("-o", str(pmtiles), "--force", "--quiet", "-l", "communes"),
            *("-Z3", "-z10", "--detect-shared-borders", "--no-feature-limit"),
            "--no-tile-size-limit",
            # Précision des zooms < 10 : 2**detail_bas unités par tuile (décision A0 : 10).
            f"--low-detail={detail_bas}",
            *("-P", str(seq)),
        ],
        check=True,
    )


def nombre_communes_tuiles(pmtiles: Path) -> int:
    """Nombre d'entités de la couche ``communes`` (métadonnées tippecanoe de l'archive)."""
    with pmtiles.open("rb") as f:
        entete = f.read(127)
        if entete[:7] != b"PMTiles":
            raise ValueError(f"{pmtiles} : archive PMTiles invalide")
        debut, longueur = struct.unpack("<QQ", entete[24:40])
        f.seek(debut)
        brut = f.read(longueur)
    meta = json.loads(gzip.decompress(brut) if entete[97] == 2 else brut)  # 2 = gzip
    couches = {c["layer"]: c["count"] for c in meta["tilestats"]["layers"]}
    return int(couches["communes"])


def _manifeste(
    con: duckdb.DuckDBPyConnection, departements: list[str] | None, n_communes: int
) -> dict[str, Any]:
    scrutins = con.execute(
        "SELECT id_election, type_scrutin, annee, tour, libelle FROM _scrutins ORDER BY 1"
    ).fetchall()
    sans = con.execute(
        "SELECT id_election, libelle FROM elections "
        "WHERE id_election NOT IN (SELECT id_election FROM _scrutins) ORDER BY 1"
    ).fetchall()
    sans_contour = con.execute(
        "SELECT COUNT(DISTINCT code_commune) FROM _c "
        "WHERE code_commune NOT IN (SELECT code_insee FROM _communes)"
    ).fetchone()
    return {
        "schema": VERSION_SCHEMA,
        "date_export": datetime.now(UTC).isoformat(timespec="seconds"),
        "licence_base": LICENCE_BASE,
        "sources": {
            cle: {
                "mention": mention(cle),
                "producteur": SOURCES[cle].producteur,
                "licence": SOURCES[cle].licence,
                "url": SOURCES[cle].url,
            }
            for cle in ("elections", "ign")
        },
        "perimetre": {
            "departements": departements,
            "communes": n_communes,
            # Codes de résultats absents des contours actuels (non affichés) : écart de chargement.
            "communes_sans_contour": sans_contour[0] if sans_contour else 0,
        },
        "types": {t: TYPES_SCRUTIN.get(t, t) for t in dict.fromkeys(s[1] for s in scrutins)},
        "scrutins": [
            {
                "id": i,
                "type": t,
                "annee": a,
                "tour": tour,
                "libelle": lib,
                "methode": methode_classement(t, a),
                "legende": legende_classement_blocs(t, a),
            }
            for i, t, a, tour, lib in scrutins
        ],
        # Écart de chargement : tours déclarés dans `elections` sans aucun résultat.
        "scrutins_sans_resultats": [{"id": i, "libelle": lib} for i, lib in sans],
        "blocs": [
            {
                "code": b,
                "car": CARACTERES[b],
                "libelle": LIBELLES_BLOCS[b],
                "couleur": COULEURS_BLOCS[b],
            }
            for b in BLOCS_ORDERED
        ],
        "codage": {
            "egalite": EGALITE,
            "non_classe": NON_CLASSE,
            "absent": ABSENT,
            "aucun_scrutin": AUCUN_SCRUTIN,
        },
        "couleur_nd": COULEUR_ND,
        "colonnes_scrutin": COLONNES_SCRUTIN,
    }


def _empreintes(sortie: Path, fichiers: dict[str, dict[str, Any]]) -> None:
    for rel, info in fichiers.items():
        octets = (sortie / rel).read_bytes()
        if not octets:
            raise ValueError(f"Export incomplet : {rel} est vide")
        info["octets"] = len(octets)
        info["sha256"] = hashlib.sha256(octets).hexdigest()


def _controler(
    sortie: Path, fichiers: dict[str, dict[str, Any]], n_communes: int, n_scrutins: int
) -> None:
    """Contrôles avant publication : un fichier par tour, toutes les communes dans les tuiles."""
    n = sum(1 for rel in fichiers if rel.startswith("scrutins/"))
    if n != n_scrutins:
        raise ValueError(f"Export incomplet : {n} fichiers de tours pour {n_scrutins} tours")
    if "communes.pmtiles" in fichiers:
        dans_tuiles = nombre_communes_tuiles(sortie / "communes.pmtiles")
        if dans_tuiles != n_communes:
            raise ValueError(f"Tuiles : {dans_tuiles} communes pour {n_communes} attendues")


def _publier(prepa: Path, sortie: Path) -> None:
    """Remplace ``sortie`` par l'export préparé (renommages sur le même disque)."""
    ancien = sortie.with_name(f".{sortie.name}.ancien")
    shutil.rmtree(ancien, ignore_errors=True)
    if sortie.exists():
        sortie.rename(ancien)
    prepa.rename(sortie)
    shutil.rmtree(ancien, ignore_errors=True)


def exporter(
    db_path: Path,
    sortie: Path,
    *,
    tippecanoe: str | None = "tippecanoe",
    departements: list[str] | None = None,
    detail_bas: int = 10,
) -> dict[str, Any]:
    """Écrit l'export complet dans ``sortie`` et renvoie le manifeste.

    Tout est écrit dans un dossier voisin, contrôlé, puis substitué à ``sortie`` (manifeste
    écrit en dernier) : un export interrompu ou invalide laisse l'export précédent intact.
    ``tippecanoe=None`` : pas de tuiles (tests). ``departements`` : échantillon.
    """
    t0 = time.perf_counter()
    sortie = sortie.resolve()
    prepa = sortie.with_name(f".{sortie.name}.prepa")
    shutil.rmtree(prepa, ignore_errors=True)
    prepa.mkdir(parents=True)
    fichiers: dict[str, dict[str, Any]] = {}
    try:
        con = duckdb.connect(str(db_path), read_only=True)  # lecture seule, jamais d'écriture
        try:
            con.execute("LOAD spatial")
            _preparer(con, departements)
            communes = con.execute("SELECT code_insee, nom FROM _communes ORDER BY 1").pl()
            _json_gz(
                prepa / "communes.json.gz",
                {"codes": communes["code_insee"].to_list(), "noms": communes["nom"].to_list()},
                fichiers,
                prepa,
            )
            _ecrire_scrutins(con, prepa, fichiers)
            logger.info("Scrutins écrits (%.1f s)", time.perf_counter() - t0)
            _ecrire_departements(con, prepa, fichiers, departements)
            logger.info("Départements écrits (%.1f s)", time.perf_counter() - t0)
            if tippecanoe:
                _ecrire_tuiles(con, prepa, tippecanoe, detail_bas)
                fichiers["communes.pmtiles"] = {}
                logger.info("Tuiles écrites (%.1f s)", time.perf_counter() - t0)
            manifeste = _manifeste(con, departements, communes.height)
        finally:
            con.close()
        _empreintes(prepa, fichiers)
        _controler(prepa, fichiers, communes.height, len(manifeste["scrutins"]))
        manifeste["fichiers"] = dict(sorted(fichiers.items()))
        (prepa / "manifest.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        _publier(prepa, sortie)
    except BaseException:
        shutil.rmtree(prepa, ignore_errors=True)
        raise
    total = sum(f["octets"] for f in fichiers.values())
    logger.info(
        "Export : %d fichiers, %.1f Mo, %.1f s",
        len(fichiers),
        total / 1e6,
        time.perf_counter() - t0,
    )
    return manifeste
