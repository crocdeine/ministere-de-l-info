"""Helpers d'affichage — palettes, formatters et légende HTML."""

from __future__ import annotations

from collections.abc import Callable

_COULEURS_YLORD5: list[str] = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
_COULEUR_CONTOURS: str = "#4292c6"
_COULEUR_FOND_CONTOURS: str = "#f7f7f7"

# Palette et seuils pour le mode évolution démographique (RdYlGn divergente)
# 6 break points → 5 classes : <-3% | -3→-1% | -1→+1% | +1→+3% | >+3%
_SEUILS_EVOLUTION: list[float] = [-100.0, -3.0, -1.0, 1.0, 3.0, 100.0]
_COULEURS_RDYLGN5: list[str] = ["#d73027", "#fc8d59", "#ffffbf", "#91cf60", "#1a9850"]


def _fmt_fr(n: float) -> str:
    """Formate un nombre en notation française (espace insécable comme séparateur de milliers)."""
    return f"{int(n):,}".replace(",", " ")


def _fmt_pct(n: float) -> str:
    """Formate un pourcentage avec signe (ex : +4.2% ou -1.3%)."""
    return f"{n:+.1f}%"


def _build_legend_html(
    titre: str,
    breaks: list[float],
    colors: list[str],
    fmt_fn: Callable[[float], str] | None = None,
) -> str:
    """Construit le HTML d'une légende discrète à fond blanc (contraste WCAG AA)."""
    _fmt = fmt_fn if fmt_fn is not None else _fmt_fr
    rows = []
    for i, color in enumerate(colors):
        lo, hi = breaks[i], breaks[i + 1]
        if i == 0:
            label = f"&lt; {_fmt(hi)}"
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
    rows_html = "\n".join(rows)
    return (
        '<div style="position:fixed;bottom:40px;left:12px;z-index:1000;'
        "background:white;color:#222;padding:10px 14px;border-radius:6px;"
        'border:1px solid #ccc;font-size:12px;font-family:sans-serif;pointer-events:none;">'
        f'<div style="font-weight:600;margin-bottom:7px;">{titre}</div>'
        f"{rows_html}"
        "</div>"
    )


def _compute_breaks(values: list[float], n_classes: int = 5) -> list[float]:
    """Calcule n_classes+1 bornes équidistantes depuis les valeurs observées."""
    if not values:
        return [0.0] * (n_classes + 1)
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        spread = max(abs(vmin) * 0.1, 1.0)
        vmin, vmax = vmin - spread, vmax + spread * n_classes
    step = (vmax - vmin) / n_classes
    return [vmin + i * step for i in range(n_classes + 1)]
