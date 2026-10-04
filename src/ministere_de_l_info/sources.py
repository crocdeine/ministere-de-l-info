"""Registre des sources de données : producteur, licence, tables chargées.

Source unique des mentions de réutilisation affichées dans l'interface.
Le détail et l'état de vérification de chaque licence sont dans ``docs/sources.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

LO2 = "Licence Ouverte 2.0"
LO1 = "Licence Ouverte 1.0"
ODBL = "ODbL 1.0"


@dataclass(frozen=True)
class Source:
    """Une source de données et ses conditions de réutilisation."""

    donnees: str
    producteur: str
    licence: str
    url: str
    tables: tuple[str, ...]  # clés de _etl_metadata (vide si non tracé)


SOURCES: dict[str, Source] = {
    "ign": Source(
        "Contours administratifs (ADMIN-EXPRESS-COG)",
        "IGN",
        LO2,
        "https://geoservices.ign.fr/adminexpress",
        (
            "geographies_regions",
            "geographies_departements",
            "geographies_epci",
            "geographies_communes",
            "geographies_arrondissements_municipaux",
        ),
    ),
    "circos": Source(
        "Circonscriptions législatives (contours non officiels)",
        "J. Desboeufs, via data.gouv.fr",
        LO2,
        "https://www.data.gouv.fr/datasets/contours-geographiques-des-circonscriptions-legislatives/",
        ("geographies_circonscriptions",),
    ),
    "insee_pop": Source(
        "Populations légales",
        "INSEE",
        LO2,
        "https://www.insee.fr/fr/information/2381863",
        ("populations_2013", "populations_2018", "populations_2023"),
    ),
    "insee_filosofi_rp": Source(
        "Filosofi et recensement (fichier republié)",
        "INSEE, republié par T. Szczurek-Gayant",
        LO2,
        "https://www.data.gouv.fr/datasets/67289477639527408ae687da/",
        ("economie_filosofi", "economie_rp"),
    ),
    "cnaf": Source(
        "Foyers allocataires du RSA",
        "CNAF (data.caf.fr)",
        LO2,
        "https://data.caf.fr/",
        ("economie_social",),
    ),
    "drees": Source(
        "Accessibilité aux médecins (APL)",
        "DREES",
        LO2,
        "https://data.drees.solidarites-sante.gouv.fr/",
        ("economie_social",),
    ),
    "urssaf": Source(
        "Effectifs salariés du secteur privé",
        "URSSAF (open.urssaf.fr)",
        ODBL,
        "https://open.urssaf.fr/",
        ("economie_emploi_urssaf",),
    ),
    "eurostat": Source(
        "Chômage BIT régional, PIB par habitant",
        "Eurostat",
        "CC BY 4.0",
        "https://ec.europa.eu/eurostat/web/main/help/copyright-notice",
        ("economie_contexte",),
    ),
    "elections": Source(
        "Résultats électoraux agrégés",
        "Ministère de l'Intérieur (data.gouv.fr)",
        LO2,
        "https://www.data.gouv.fr/datasets/donnees-des-elections-agregees/",
        (),
    ),
    "datan": Source(
        "Députés et scores d'activité (d'après l'AN)",
        "Datan",
        LO1,
        "https://www.data.gouv.fr/datasets/historique-des-deputes/",
        ("leg_elus_datan", "leg_mandats_datan"),
    ),
    "senat": Source(
        "Sénateurs (ODSEN_GENERAL)",
        "Sénat (data.senat.fr)",
        "Licence Ouverte (Sénat)",
        "https://data.senat.fr/licence/",
        ("leg_elus_senat",),
    ),
}


def mention(cle: str) -> str:
    """Mention courte pour une légende : « producteur — licence »."""
    s = SOURCES[cle]
    return f"{s.producteur} — {s.licence}"


def tableau_sources(chargements: dict[str, datetime]) -> list[dict[str, str]]:
    """Lignes du tableau des sources ; date = chargement le plus récent des tables."""
    lignes = []
    for s in SOURCES.values():
        dates = [chargements[t] for t in s.tables if t in chargements]
        lignes.append(
            {
                "Données": s.donnees,
                "Producteur": s.producteur,
                "Licence": s.licence,
                "Chargées le": max(dates).strftime("%d/%m/%Y") if dates else "non tracé",
                "Lien": s.url,
            }
        )
    return lignes
