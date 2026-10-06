"""Helpers d'affichage — palettes, formatters et légende HTML."""

from __future__ import annotations

from collections.abc import Callable

import folium

# Fond Plan IGN (Géoplateforme, Licence Ouverte, sans clé), atténué pour ne pas
# interférer avec les couleurs des données. CARTO exige une clé depuis 2026.
_URL_PLAN_IGN: str = (
    "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
    "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&TILEMATRIXSET=PM"
    "&FORMAT=image/png&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
)


def nouvelle_carte(location: list[float], zoom_start: int) -> folium.Map:
    """Carte Folium sur fond Plan IGN atténué."""
    m = folium.Map(location=location, zoom_start=zoom_start, tiles=None)
    folium.TileLayer(
        _URL_PLAN_IGN, attr="Fond : © IGN — Plan IGN", name="Plan IGN", opacity=0.35
    ).add_to(m)
    return m


COULEUR_ND: str = "#5F6368"  # gris foncé : donnée non disponible (n.d.)
_COULEURS_YLORD5: list[str] = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
_COULEUR_CONTOURS: str = "#4292c6"
_COULEUR_FOND_CONTOURS: str = "#f7f7f7"

# Palette et seuils pour le mode évolution démographique (PuOr divergente, sans rouge-vert : daltonisme, pas de connotation « baisse = mal »)
# 6 break points → 5 classes : <-3% | -3→-1% | -1→+1% | +1→+3% | >+3%
_SEUILS_EVOLUTION: list[float] = [-100.0, -3.0, -1.0, 1.0, 3.0, 100.0]
_COULEURS_EVOLUTION5: list[str] = ["#e66101", "#fdb863", "#f7f7f7", "#b2abd2", "#5e3c99"]


def _fmt_fr(n: float) -> str:
    """Formate un nombre en notation française (espace insécable comme séparateur de milliers)."""
    return f"{int(n):,}".replace(",", " ")


def fmt_nd(n: float | None, fmt: str = ",.0f", suffixe: str = "") -> str:
    """Formate un nombre en français ; valeur absente (None/NaN) -> « n.d. », jamais 0."""
    if n is None or n != n:
        return "n.d."
    return f"{n:{fmt}}".replace(",", "\u202f").replace(".", ",") + suffixe


def _fmt_pct(n: float) -> str:
    """Formate un pourcentage avec signe (ex : +4.2% ou -1.3%)."""
    return f"{n:+.1f}%"


def _build_legend_html(
    titre: str,
    breaks: list[float],
    colors: list[str],
    fmt_fn: Callable[[float], str] | None = None,
    note: str | None = None,
    avec_nd: bool = False,
    avec_zero: bool = False,
) -> str:
    """Construit le HTML d'une légende discrète à fond blanc (contraste WCAG AA).

    ``avec_nd`` ajoute la case grise « n.d. » (donnée non disponible ou secret statistique) ;
    ``avec_zero`` ajoute la classe « 0 » et la première classe devient « > 0 et < … ».
    """
    _fmt = fmt_fn if fmt_fn is not None else _fmt_fr
    rows = []
    for i, color in enumerate(colors):
        lo, hi = breaks[i], breaks[i + 1]
        if i == 0:
            label = f"&gt; 0 et &lt; {_fmt(hi)}" if avec_zero else f"&lt; {_fmt(hi)}"
        elif i == len(colors) - 1:
            label = f"&ge; {_fmt(lo)}"
        else:
            label = f"{_fmt(lo)}&nbsp;&ndash; {_fmt(hi)}"
        rows.append(
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px;">'
            f'<div style="width:20px;height:14px;background:{color};'
            f'border:1px solid #bbb;flex-shrink:0;"></div>'
            f'<span style="white-space:nowrap;">{label}</span>'
            f"</div>"
        )
    if avec_zero:
        rows.insert(
            0,
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px;">'
            f'<div style="width:20px;height:14px;background:{COULEUR_ZERO};'
            f'border:1px solid #bbb;flex-shrink:0;"></div>'
            f'<span style="white-space:nowrap;">0 (aucun)</span>'
            f"</div>",
        )
    if avec_nd:
        rows.append(
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px;">'
            f'<div style="width:20px;height:14px;background:{COULEUR_ND};'
            f'border:1px solid #bbb;flex-shrink:0;"></div>'
            f'<span style="white-space:nowrap;">n.d. (donnée non disponible)</span>'
            f"</div>"
        )
    rows_html = "\n".join(rows)
    if note:
        rows_html += f'<div style="margin-top:5px;font-size:11px;color:#555;">{note}</div>'
    return (
        '<div style="position:fixed;bottom:40px;left:12px;z-index:1000;'
        "background:white;color:#222;padding:10px 14px;border-radius:6px;"
        'border:1px solid #ccc;font-size:12px;font-family:sans-serif;pointer-events:none;">'
        f'<div style="font-weight:600;margin-bottom:7px;">{titre}</div>'
        f"{rows_html}"
        "</div>"
    )


# Bornes de classes FIXES par indicateur : identiques quelle que soit l'année ou la zone
# affichée, pour que deux cartes soient comparables (audit I7). Seuils arrondis, fixés a priori
# (ordres de grandeur observés), pas recalculés sur les données affichées. 5 classes = 6 bornes ;
# les bornes extrêmes ne servent qu'à encadrer la première et la dernière classe.
_INF: float = 1e12
BORNES_FIXES: dict[str, list[float]] = {
    # Géographie : population municipale, selon le niveau territorial
    "population_municipale:region": [0, 1e6, 2e6, 4e6, 6e6, _INF],
    "population_municipale:departement": [0, 250e3, 500e3, 750e3, 1e6, _INF],
    "population_municipale:epci": [0, 20e3, 50e3, 100e3, 250e3, _INF],
    "population_municipale:arrondissement_municipal": [0, 20e3, 40e3, 60e3, 80e3, _INF],
    "population_municipale:circonscription": [0, 80e3, 100e3, 120e3, 140e3, _INF],
    "population_municipale:commune": [0, 500, 2e3, 10e3, 50e3, _INF],
    # Économie (communes HdF)
    "taux_pauvrete": [0, 10, 15, 20, 25, 100],  # décision Mathias 2026-10-06
    "niveau_vie_median": [0, 16e3, 19e3, 22e3, 25e3, _INF],
    "tx_chomage_dec": [0, 6, 9, 12, 15, 100],
    "part_ouvriers_employes": [0, 30, 40, 50, 60, 100],
    "part_emploi_industriel": [0, 5, 10, 15, 25, 100],
    "part_logements_sociaux": [0, 5, 10, 20, 30, 100],
    "nb_foyers_rsa": [0, 10, 50, 200, 1e3, _INF],
    "apl_medecins": [0, 2.5, 3.5, 4.5, 5.5, _INF],
}
NOTE_CLASSES_FIXES: str = "Classes fixes, identiques pour toutes les années"

# Indicateurs où « 0 » (aucun logement social, aucun emploi industriel, aucun foyer RSA) est
# fréquent : classe « 0 » distincte de « peu » (décision Mathias 2026-10-06).
INDICATEURS_CLASSE_ZERO: frozenset[str] = frozenset(
    {"part_emploi_industriel", "part_logements_sociaux", "nb_foyers_rsa"}
)
COULEUR_ZERO: str = "#F0EDE6"  # beige très clair, distinct de la 1re classe et du gris n.d.


def bornes_fixes(cle: str) -> list[float]:
    """Bornes de classes fixes d'un indicateur (ValueError si inconnu : pas de repli auto)."""
    try:
        return list(BORNES_FIXES[cle])
    except KeyError:
        raise ValueError(f"Pas de bornes fixes définies pour « {cle} »") from None
