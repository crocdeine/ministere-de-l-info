"""Index de la recherche globale : ``recherche.json.gz`` (lot A4).

Communes (nom, code INSEE, codes postaux La Poste), départements, circonscriptions
législatives, élus en exercice. Libellés normalisés ici (même règle que ``normaliser`` de
``web/src/recherche.ts``). Aucun libellé politique, aucune date de naissance. Les départements,
circonscriptions et élus n'ayant pas de page propre, ils pointent vers la fiche de la commune
la plus peuplée de leur périmètre (règle objective, indiquée à l'écran) : colonne ``ref``.
Sans table ``codes_postaux`` (base non chargée), l'index est produit sans codes postaux.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb

from ministere_de_l_info.export_web.fiches import LIBELLES_OUTRE_MER

logger = logging.getLogger(__name__)

# type : c commune, d département, e circonscription, u élu
COLONNES = ["type", "code", "libelle", "norm", "dep", "extra", "ref"]
_MOTS = {"st": "saint", "ste": "sainte"}


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation ; « St » → « saint » (mot entier)."""
    t = unicodedata.normalize("NFD", texte.replace("œ", "oe").replace("Œ", "oe"))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    mots = re.sub(r"[^a-z0-9]+", " ", t).split()
    return " ".join(_MOTS.get(m, m) for m in mots)


def table_existe(con: duckdb.DuckDBPyConnection, nom: str) -> bool:
    r = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [nom]
    ).fetchone()
    return bool(r and r[0])


def construire_index(con: duckdb.DuckDBPyConnection) -> tuple[dict[str, Any], dict[str, Any]]:
    """Index et écarts, à partir des tables temporaires ``_communes`` et ``_circos`` (export en cours).

    Écarts (comptés, journalisés, publiés dans le manifeste) : élus non indexés (aucune commune
    exportée dans leur département), élus rattachés au département faute de circonscription
    exportée, circonscriptions écartées.
    """
    avec_cp = table_existe(con, "codes_postaux")
    if not avec_cp:
        logger.warning("codes_postaux absente : recherche par code postal indisponible")
    # Commune de référence : la plus peuplée (dernière population connue), à égalité le code.
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _pop AS
        SELECT c.code_insee, c.code_departement,
               COALESCE((SELECT arg_max(population_municipale, annee) FROM v_population_commune p
                         WHERE p.code_commune = c.code_insee), -1) AS pop
        FROM _communes c
        """
    )
    lignes: list[list[Any]] = []
    cps: dict[str, list[str]] = {}
    if avec_cp:
        for code, cp in con.execute(
            "SELECT code_insee, code_postal FROM codes_postaux "
            "WHERE code_insee IN (SELECT code_insee FROM _communes) ORDER BY 1, 2"
        ).fetchall():
            cps.setdefault(code, []).append(cp)
    for code, nom, dep in con.execute(
        "SELECT code_insee, nom, code_departement FROM _communes ORDER BY code_insee"
    ).fetchall():
        lignes.append(["c", code, nom, normaliser(nom), dep, " ".join(cps.get(code, [])), None])

    ref_dep = dict(
        con.execute(
            "SELECT code_departement, arg_max(code_insee, (pop, code_insee)) FROM _pop GROUP BY 1"
        ).fetchall()
    )
    noms_dep = dict(
        con.execute(
            "SELECT code_insee, nom FROM geographies_departements WHERE code_insee IN "
            "(SELECT DISTINCT code_departement FROM _communes)"
        ).fetchall()
    )
    noms_dep |= {k: v[0] for k, v in LIBELLES_OUTRE_MER.items() if k in ref_dep}
    for dep in sorted(ref_dep):
        nom = noms_dep.get(dep, dep)
        lignes.append(["d", dep, nom, normaliser(nom), dep, "", ref_dep[dep]])

    ref_circo = dict(
        con.execute(
            "SELECT circo, arg_max(code_insee, (pop, code_insee)) FROM "
            "(SELECT unnest(ci.circos) AS circo, p.code_insee, p.pop FROM _circos ci "
            "JOIN _pop p USING (code_insee)) GROUP BY 1"
        ).fetchall()
    )
    circos_ecartees: list[str] = []
    for code, nom in con.execute(
        "SELECT code, nom FROM geographies_circonscriptions "
        "WHERE code_departement IN (SELECT DISTINCT code_departement FROM _communes) ORDER BY 1"
    ).fetchall():
        if code not in ref_circo:
            circos_ecartees.append(code)
        else:
            libelle = nom or f"Circonscription {code}"
            norm = normaliser(f"{libelle} {code}")
            lignes.append(["e", code, libelle, norm, code.split("-")[0], "", ref_circo[code]])

    non_indexes: dict[str, int] = {}
    replis = 0
    for chambre, id_, prenom, nom, dep, num in con.execute(
        "SELECT chambre, id, prenom, nom, upper(code_departement), num_circo "
        "FROM v_elus_actuels ORDER BY chambre, nom, prenom, id"
    ).fetchall():
        circo = f"{dep}-{int(num):02d}" if chambre == "AN" and num is not None else None
        ref = ref_circo.get(circo) if circo else None
        if ref is None:
            ref = ref_dep.get(dep)
            if ref is not None and chambre == "AN":
                replis += (
                    1  # député : commune la plus peuplée du département (circonscription inconnue)
                )
        if ref is None:
            non_indexes[dep] = non_indexes.get(dep, 0) + 1
            continue
        titre = "Député" if chambre == "AN" else "Sénateur"
        lignes.append(
            [
                "u",
                f"{chambre}:{id_}",
                f"{prenom} {nom}",
                normaliser(f"{nom} {prenom}"),
                dep,
                titre,
                ref,
            ]
        )
    if non_indexes:
        logger.warning(
            "Recherche : %d élus non indexés (aucune commune exportée dans leur département) : %s",
            sum(non_indexes.values()),
            ", ".join(f"{d}={n}" for d, n in sorted(non_indexes.items())),
        )
    if replis:
        logger.warning(
            "Recherche : %d députés rattachés au département (circonscription inconnue)", replis
        )
    if circos_ecartees:
        logger.warning(
            "Recherche : %d circonscriptions écartées (aucune commune rattachée) : %s",
            len(circos_ecartees),
            ", ".join(circos_ecartees[:20]),
        )
    index = {
        "colonnes": COLONNES,
        "departements": {k: noms_dep.get(k, k) for k in sorted(ref_dep)},
        "codes_postaux": avec_cp,
        "lignes": lignes,
    }
    ecarts = {
        "elus_non_indexes": sum(non_indexes.values()),
        "elus_non_indexes_par_departement": dict(sorted(non_indexes.items())),
        "elus_rattaches_au_departement": replis,
        "circonscriptions_ecartees": len(circos_ecartees),
        "codes_postaux_charges": avec_cp,
    }
    return index, ecarts


def ecrire_recherche(
    con: duckdb.DuckDBPyConnection, sortie: Path, ecrire: Callable[[Path, Any], None]
) -> dict[str, Any]:
    """Écrit ``recherche.json.gz`` ; renvoie les écarts (publiés dans le manifeste)."""
    index, ecarts = construire_index(con)
    cles = [(r[0], r[1]) for r in index["lignes"]]
    if len(cles) != len(set(cles)):
        raise ValueError("Index de recherche : clés (type, code) en double")
    ecrire(sortie / "recherche.json.gz", index)
    return ecarts
