"""
Constantes et configuration pour les visualisations Plotly.

Ce module centralise les configurations Plotly, couleurs et layouts
pour garantir une cohérence visuelle dans tous les graphiques.
"""

PLOTLY_CONFIG: dict = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "survey_statistics",
        "height": 1080,
        "width": 1920,
        "scale": 2,
    },
}
"""Configuration Plotly pour tous les graphiques."""

FONT_FAMILY: str = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
"""Police de caractères cohérente avec le rapport."""

COLOR_PALETTE: dict[str, str] = {
    "distance": "#d8b365",
    "time": "#5ab4ac",
    "points": "#999999",
    "background": "#f0f2f5",
    "grid": "#dee2e6",
    "primary": "#2c3e50",
}
"""Palette de couleurs standardisée."""

LAYOUT_DEFAULTS: dict = {
    "font": {"family": FONT_FAMILY, "size": 13},
    "paper_bgcolor": "white",
    "plot_bgcolor": "white",
    "margin": {"l": 60, "r": 60, "t": 40, "b": 60},
    "hovermode": "x unified",
    "xaxis": {
        "showgrid": True,
        "gridcolor": "#dee2e6",
        "zeroline": False,
    },
    "yaxis": {
        "showgrid": True,
        "gridcolor": "#dee2e6",
        "zeroline": False,
    },
}
"""Configuration de layout par défaut pour tous les graphiques."""
