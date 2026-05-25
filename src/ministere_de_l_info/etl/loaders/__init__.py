"""Loaders ETL — insertion des données dans DuckDB."""

from ministere_de_l_info.etl.loaders.arrondissements_municipaux import (
    load_arrondissements_municipaux,
)
from ministere_de_l_info.etl.loaders.communes import load_communes
from ministere_de_l_info.etl.loaders.departements import load_departements
from ministere_de_l_info.etl.loaders.epci import load_epci, update_epci_departement_principal
from ministere_de_l_info.etl.loaders.regions import load_regions

__all__ = [
    "load_arrondissements_municipaux",
    "load_communes",
    "load_departements",
    "load_epci",
    "load_regions",
    "update_epci_departement_principal",
]
