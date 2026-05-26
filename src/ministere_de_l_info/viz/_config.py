"""Constantes de configuration cartographique — tables, colonnes, géométries, filtres."""

from __future__ import annotations

_CENTRE_FRANCE: list[float] = [46.5, 2.5]
_ZOOM_DEPART: int = 5
_SOURCE: str = "Source : data.geopf.fr (IGN ADMIN-EXPRESS COG) — Population INSEE"

_NIVEAUX_SUPPORTES: frozenset[str] = frozenset(
    {
        "region",
        "departement",
        "epci",
        "arrondissement_municipal",
        "circonscription",
        "commune",
    }
)
_NIVEAUX_POPULATION: frozenset[str] = frozenset({"region", "departement", "epci", "commune"})
_NIVEAUX_CONTOURS: frozenset[str] = frozenset({"arrondissement_municipal", "circonscription"})

_TABLE_PAR_NIVEAU: dict[str, str] = {
    "region": "geographies_regions",
    "departement": "geographies_departements",
    "epci": "geographies_epci",
    "arrondissement_municipal": "geographies_arrondissements_municipaux",
    "circonscription": "geographies_circonscriptions",
    "commune": "geographies_communes",
}

_COLONNE_CODE: dict[str, str] = {
    "region": "code_insee",
    "departement": "code_insee",
    "epci": "code_siren",
    "arrondissement_municipal": "code_insee",
    "circonscription": "code",
    "commune": "code_insee",
}

_GEOMETRIE_NATIONALE: dict[str, str] = {
    "region": "geometry_simplified_national",
    "departement": "geometry_simplified_national",
    "epci": "geometry_simplified_epci",
    "arrondissement_municipal": "geometry_simplified_communal",
    "circonscription": "geometry_simplified_circo",
    "commune": "geometry_simplified_communal",
}

_GEOMETRIE_ZOOM: dict[str, str] = {
    "region": "geometry_simplified_regional",
    "departement": "geometry_simplified_departemental",
    "epci": "geometry_simplified_epci",
    "arrondissement_municipal": "geometry_simplified_communal",
    "circonscription": "geometry_simplified_circo",
    "commune": "geometry_simplified_communal",
}

_VUE_PAR_NIVEAU: dict[str, str] = {
    "region": "v_population_region",
    "departement": "v_population_departement",
    "epci": "v_population_epci",
    "commune": "v_population_commune",
}

# (colonne clé dans table géo, colonne correspondante dans la vue population)
_CLE_JOIN: dict[str, tuple[str, str]] = {
    "region": ("code_insee", "code_region"),
    "departement": ("code_insee", "code_departement"),
    "epci": ("code_siren", "code_epci"),
    "commune": ("code_insee", "code_commune"),
}

# Colonne filtre département dans chaque table géo (None = filtre non applicable)
_FILTRE_DEPARTEMENT_COL: dict[str, str | None] = {
    "region": None,
    "departement": None,
    "epci": "code_departement_principal",
    "arrondissement_municipal": None,  # ARM : code_commune_mere seulement, pas de col. dpt
    "circonscription": "code_departement",
    "commune": "code_departement",
}

# Colonne filtre région dans chaque table géo
_FILTRE_REGION_COL: dict[str, str | None] = {
    "region": None,
    "departement": "code_region",
    "epci": None,
    "arrondissement_municipal": None,
    "circonscription": None,
    "commune": "code_region",
}

_LIBELLES_NIVEAUX: dict[str, str] = {
    "region": "Région",
    "departement": "Département",
    "epci": "EPCI",
    "arrondissement_municipal": "Arrondissement municipal",
    "circonscription": "Circonscription",
    "commune": "Commune",
}
