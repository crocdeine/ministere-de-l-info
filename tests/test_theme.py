"""Tests du module _theme (design system v2 « direction éditoriale », ADR-0014)."""

from __future__ import annotations

import plotly.io as pio

from ministere_de_l_info import _theme


def test_css_contient_tokens_v2() -> None:
    css = _theme._load_css()
    for token in ("--ink: #0a0a0a", "--paper: #ffffff", "--bleu-france: #000091"):
        assert token in css


def test_css_conserve_alias_v1() -> None:
    """Les noms de tokens v1 restent définis (compatibilité)."""
    css = _theme._load_css()
    for alias in ("--surface-page:", "--text-strong:", "--radius-lg:", "--nuance-exg:"):
        assert alias in css


def test_css_sans_import() -> None:
    """Les polices passent par une balise <link>, jamais par @import."""
    lignes = _theme._load_css().splitlines()
    assert not any(ligne.lstrip().startswith("@import") for ligne in lignes)


def test_polices_sans_spectral() -> None:
    assert "Spectral" not in _theme._GOOGLE_FONTS_URL
    assert "Hanken+Grotesk" in _theme._GOOGLE_FONTS_URL


def test_template_plotly_enregistre_par_defaut() -> None:
    _theme.register_plotly_template()
    assert pio.templates.default == _theme.PLOTLY_TEMPLATE_NAME
    template = pio.templates[_theme.PLOTLY_TEMPLATE_NAME]
    layout = template.to_plotly_json()["layout"]
    assert layout["paper_bgcolor"] == _theme.PAPER
    assert "Hanken Grotesk" in layout["font"]["family"]


def test_page_header_echappe_html(monkeypatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(_theme.st, "markdown", lambda html, **_: captured.append(html))
    _theme.render_page_header("map", "<b>Titre</b>", "Sous & titre")
    html = captured[0]
    assert "&lt;b&gt;Titre&lt;/b&gt;" in html
    assert "Sous &amp; titre" in html
    assert "mdi-page-title--display" not in html


def test_page_header_display(monkeypatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(_theme.st, "markdown", lambda html, **_: captured.append(html))
    _theme.render_page_header("flag", "Accueil", display=True)
    assert "mdi-page-title--display" in captured[0]
    assert "mdi-page-subtitle" not in captured[0]


def test_css_metrique_jamais_tronquee() -> None:
    """La valeur d'une métrique (« Extrême droite ») revient à la ligne, sans ellipse (J2)."""
    css = _theme._load_css()
    bloc = css.split('[data-testid="stMetricValue"] * {', 1)[1].split("}", 1)[0]
    assert "text-overflow: unset !important" in bloc
    assert "white-space: normal !important" in bloc


def test_tokens_evolution_alignes_sur_palette_accessible() -> None:
    """--choro-evo-* = _COULEURS_EVOLUTION5 (PuOr, décision J3), dans l'app et dans le skill."""
    from pathlib import Path

    from ministere_de_l_info.viz._display import _COULEURS_EVOLUTION5

    skill = Path(__file__).resolve().parents[1] / ".claude/skills/design-system-mi"
    for css in (
        _theme._load_css(),
        (skill / "tokens.css").read_text(encoding="utf-8"),
        (skill / "streamlit/custom.css").read_text(encoding="utf-8"),
    ):
        for i, couleur in enumerate(_COULEURS_EVOLUTION5, start=1):
            assert f"--choro-evo-{i}: {couleur.lower()};" in css
