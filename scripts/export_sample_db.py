"""Exporte un échantillon départemental de la base réelle en Parquet (tests hermétiques).

À lancer sur le Mac, là où la base complète existe :

    uv run python scripts/export_sample_db.py

Produit dans tests/fixtures/sample/ :
- un fichier Parquet par table (données réelles, filtrées sur un département) ;
- manifest.json : provenance, filtres appliqués, colonnes, nombres de lignes, vues
  présentes dans la base source.

Périmètre par défaut : Somme (80).
- Géographies : région et département du 80, communes, EPCI et circonscriptions du 80.
  Toutes les colonnes géométriques sont simplifiées (tolérance en degrés, EPSG:4326)
  et stockées en WKB (BLOB) : la reconstruction ne dépend pas de l'extension spatial.
- Résultats électoraux : bureaux de vote du 80, pour une sélection de scrutins
  (--scrutins). Défaut : 2 années par type, choisies pour couvrir les cas de résolution
  des blocs (nuance vs nom de candidat, ancien découpage, panneaux synthétiques 2008).
- Référentiels complets : elections, blocs_politiques, nuances_harmonisees,
  candidats_presidentielle, leg_blocs_override, leg_groupes_blocs, economie_contexte.
- Économie : communes du 80 ; URSSAF limitée aux secteurs industriels (seuls utilisés
  par les vues et requêtes du projet).
- Législatif : élus rattachés au 80 (toutes chambres, toutes législatures), leurs mandats
  (leg_mandats) et leur activité.

La taille totale est vérifiée (--max-mo, 5 Mo par défaut) : le script échoue sans rien
écrire si le budget est dépassé. Il est idempotent : l'échantillon précédent est remplacé.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

logger = logging.getLogger(__name__)

DEST_DEFAUT = ROOT / "tests" / "fixtures" / "sample"
DEPARTEMENT_DEFAUT = "80"
TOLERANCE_DEFAUT = 0.002  # degrés (~150-200 m en latitude HdF)
MAX_MO_DEFAUT = 5.0
MANIFEST = "manifest.json"
FORMAT_MANIFEST = 1

# Deux années par type : 2012/2022 (pres : bloc par nuance puis par nom de candidat),
# 2007/2024 (legi : ancien puis nouveau découpage), 2008/2026 (muni : panneaux
# synthétiques 2008, dernier scrutin).
SCRUTINS_DEFAUT: tuple[str, ...] = tuple(
    f"{annee}_{typ}_t{tour}"
    for typ, annees in (("pres", (2012, 2022)), ("legi", (2007, 2024)), ("muni", (2008, 2026)))
    for annee in annees
    for tour in (1, 2)
)

_RE_DEPT = re.compile(r"^(\d{2}|2[AB]|\d{3})$")
_RE_ID_ELECTION = re.compile(r"^\d{4}_[a-z]{3,4}_t\d$")


@dataclass(frozen=True)
class TableSpec:
    """Table à exporter et filtre SQL (clause WHERE, vide = table complète)."""

    nom: str
    filtre: str = ""


def construire_specs(dept: str, scrutins: tuple[str, ...] | None) -> list[TableSpec]:
    """Liste ordonnée des tables exportées et de leurs filtres.

    ``dept`` et ``scrutins`` sont validés par expression régulière avant interpolation.
    ``scrutins=None`` : tous les scrutins présents en base.
    """
    if not _RE_DEPT.match(dept):
        raise ValueError(f"Code département invalide : {dept!r}")
    if scrutins is not None:
        invalides = [s for s in scrutins if not _RE_ID_ELECTION.match(s)]
        if invalides:
            raise ValueError(f"Identifiants de scrutin invalides : {invalides}")

    d = f"'{dept}'"
    communes = f"SELECT code_insee FROM geographies_communes WHERE code_departement = {d}"
    filtre_scrutins = ""
    if scrutins is not None:
        filtre_scrutins = " AND id_election IN (" + ", ".join(f"'{s}'" for s in scrutins) + ")"
    elus = f"SELECT id FROM leg_elus WHERE code_departement = {d}"

    return [
        # Géographies
        TableSpec(
            "geographies_regions",
            "code_insee IN (SELECT code_region FROM geographies_departements "
            f"WHERE code_insee = {d})",
        ),
        TableSpec("geographies_departements", f"code_insee = {d}"),
        TableSpec(
            "geographies_epci",
            f"code_siren IN (SELECT code_epci FROM geographies_communes "
            f"WHERE code_departement = {d})",
        ),
        TableSpec("geographies_communes", f"code_departement = {d}"),
        TableSpec("geographies_arrondissements_municipaux", f"code_commune_mere IN ({communes})"),
        TableSpec("geographies_circonscriptions", f"code_departement = {d}"),
        TableSpec("populations", f"code_insee_commune IN ({communes})"),
        # Élections : référentiels complets, résultats filtrés
        TableSpec("elections"),
        TableSpec("blocs_politiques"),
        TableSpec("nuances_harmonisees"),
        TableSpec("candidats_presidentielle"),
        TableSpec("resultats_participation", f"code_departement = {d}{filtre_scrutins}"),
        TableSpec("resultats_candidats", f"code_departement = {d}{filtre_scrutins}"),
        # Économie
        TableSpec("economie_filosofi", f"code_commune IN ({communes})"),
        TableSpec("economie_rp", f"code_commune IN ({communes})"),
        TableSpec("economie_social", f"code_commune IN ({communes})"),
        TableSpec(
            "economie_emploi_urssaf",
            f"code_commune IN ({communes}) AND secteur_gs LIKE '%Industrie%'",
        ),
        TableSpec("economie_contexte"),
        # Législatif
        TableSpec("leg_elus", f"code_departement = {d}"),
        TableSpec(
            "leg_mandats",
            "EXISTS (SELECT 1 FROM leg_elus e WHERE e.id = leg_mandats.elu_id "
            f"AND e.chambre = leg_mandats.chambre AND e.code_departement = {d})",
        ),
        TableSpec("leg_activite", f"elu_id IN ({elus})"),
        TableSpec("leg_blocs_override"),
        TableSpec("leg_groupes_blocs"),
    ]


# Tables techniques recréées par create_schema() : non exportées (leurs compteurs
# décrivent la base complète et seraient faux pour l'échantillon).
TABLES_NON_EXPORTEES = frozenset({"_etl_metadata", "_schema_version"})


def _colonnes(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    rows = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'main' AND table_name = ? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def _objets(con: duckdb.DuckDBPyConnection, type_objet: str) -> set[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = ?",
        [type_objet],
    ).fetchall()
    return {str(r[0]) for r in rows}


def _quote(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _expr_colonne(nom: str, type_sql: str, tolerance: float | None) -> str:
    """Expression SELECT : géométries simplifiées puis converties en WKB."""
    col = _quote(nom)
    if not type_sql.upper().startswith("GEOMETRY"):
        return col
    if tolerance is None:
        return f"ST_AsWKB({col})::BLOB AS {col}"
    return f"ST_AsWKB(ST_SimplifyPreserveTopology({col}, {float(tolerance)!r}))::BLOB AS {col}"


def exporter(
    con: duckdb.DuckDBPyConnection,
    dest: Path,
    *,
    dept: str = DEPARTEMENT_DEFAUT,
    scrutins: tuple[str, ...] | None = SCRUTINS_DEFAUT,
    tolerance: float | None = TOLERANCE_DEFAUT,
    max_mo: float = MAX_MO_DEFAUT,
    source_label: str = "",
) -> dict:
    """Exporte l'échantillon dans ``dest`` et retourne le manifeste.

    ``tolerance=None`` : géométries non simplifiées (ne nécessite pas l'extension
    spatial ; réservé aux tests du script). Lève RuntimeError si le budget de taille
    est dépassé ; ``dest`` n'est alors pas modifié.
    """
    specs = construire_specs(dept, scrutins)
    tables_source = _objets(con, "BASE TABLE")
    vues_source = sorted(_objets(con, "VIEW"))
    noms_specs = {s.nom for s in specs}

    manifest: dict = {
        "format": FORMAT_MANIFEST,
        "genere_le": datetime.now(UTC).isoformat(timespec="seconds"),
        "duckdb_version": duckdb.__version__,
        "source": source_label,
        "departement": dept,
        "scrutins": list(scrutins) if scrutins is not None else "tous",
        "tolerance_simplification_deg": tolerance,
        "encodage_geometries": "WKB (BLOB), EPSG:4326",
        "tables": {},
        "tables_absentes_de_la_source": sorted(noms_specs - tables_source),
        "tables_source_non_exportees": sorted(tables_source - noms_specs - TABLES_NON_EXPORTEES),
        "vues_source": vues_source,
    }

    with tempfile.TemporaryDirectory(prefix="sample_export_") as tmp:
        tmp_dir = Path(tmp)
        total = 0
        for spec in specs:
            if spec.nom not in tables_source:
                logger.warning("Table absente de la base source : %s (ignorée)", spec.nom)
                continue
            cols = _colonnes(con, spec.nom)
            select = ", ".join(_expr_colonne(n, t, tolerance) for n, t in cols)
            where = f" WHERE {spec.filtre}" if spec.filtre else ""
            fichier = tmp_dir / f"{spec.nom}.parquet"
            chemin_sql = str(fichier).replace("'", "''")
            con.execute(
                f"COPY (SELECT {select} FROM {_quote(spec.nom)}{where} ORDER BY ALL) "
                f"TO '{chemin_sql}' (FORMAT parquet, COMPRESSION zstd)"
            )
            ligne = con.execute(f"SELECT COUNT(*) FROM read_parquet('{chemin_sql}')").fetchone()
            n = ligne[0] if ligne else 0
            taille = fichier.stat().st_size
            total += taille
            manifest["tables"][spec.nom] = {
                "fichier": fichier.name,
                "lignes": int(n),
                "octets": taille,
                "filtre": spec.filtre or None,
                "colonnes": [[nom, t] for nom, t in cols],
                "colonnes_geometrie": [nom for nom, t in cols if t.upper().startswith("GEOMETRY")],
            }
            logger.info("%-40s %8d lignes  %8.1f Ko", spec.nom, n, taille / 1024)

        manifest["octets_total"] = total
        logger.info("Total : %.2f Mo (budget %.2f Mo)", total / 1e6, max_mo)
        if total > max_mo * 1e6:
            detail = sorted(
                ((v["octets"], k) for k, v in manifest["tables"].items()), reverse=True
            )[:5]
            raise RuntimeError(
                f"Échantillon trop volumineux : {total / 1e6:.2f} Mo > {max_mo} Mo. "
                f"Plus gros fichiers : {detail}. Réduire --scrutins ou augmenter --tolerance."
            )

        (tmp_dir / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        # Remplacement : on ne touche qu'aux fichiers générés (le README reste en place).
        dest.mkdir(parents=True, exist_ok=True)
        for ancien in [*dest.glob("*.parquet"), dest / MANIFEST]:
            ancien.unlink(missing_ok=True)
        for nouveau in tmp_dir.iterdir():
            shutil.move(str(nouveau), dest / nouveau.name)

    return manifest


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Exporte un échantillon départemental de la base réelle en Parquet."
    )
    p.add_argument("--source", type=Path, default=None, help="Base DuckDB source (défaut : config)")
    p.add_argument("--dest", type=Path, default=DEST_DEFAUT, help="Répertoire de sortie")
    p.add_argument("--departement", default=DEPARTEMENT_DEFAUT, help="Code département (80)")
    p.add_argument(
        "--scrutins",
        default=",".join(SCRUTINS_DEFAUT),
        help="Identifiants séparés par des virgules, ou 'tous'",
    )
    p.add_argument("--tolerance", type=float, default=TOLERANCE_DEFAUT, help="Degrés")
    p.add_argument("--max-mo", type=float, default=MAX_MO_DEFAUT, help="Budget total en Mo")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = _parse_args(argv)
    source: Path = args.source or get_settings().db_path
    if not source.exists():
        logger.error("Base source introuvable : %s", source)
        return 1
    scrutins = (
        None
        if args.scrutins.strip().lower() == "tous"
        else tuple(s.strip() for s in args.scrutins.split(",") if s.strip())
    )

    con = duckdb.connect(str(source), read_only=True)
    try:
        try:
            con.execute("LOAD spatial")
        except duckdb.Error as exc:
            logger.error("Extension spatial requise pour simplifier les géométries : %s", exc)
            return 1
        manifest = exporter(
            con,
            args.dest,
            dept=args.departement,
            scrutins=scrutins,
            tolerance=args.tolerance,
            max_mo=args.max_mo,
            source_label=source.name,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    finally:
        con.close()

    logger.info(
        "Échantillon écrit dans %s : %d tables, %.2f Mo",
        args.dest,
        len(manifest["tables"]),
        manifest["octets_total"] / 1e6,
    )
    if manifest["tables_source_non_exportees"]:
        logger.warning(
            "Tables de la source non couvertes par l'échantillon : %s",
            ", ".join(manifest["tables_source_non_exportees"]),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
