"""
Générateur de rapport HTML complet avec statistiques.

Ce module orchestre la génération complète du rapport HTML
combinant métadonnées et visualisations statistiques.
"""

import webbrowser
from pathlib import Path

from loguru import logger

from ..statistic.models import SurveyStatistics
from .constants import PLOTLY_CONFIG
from .figure_builder import (
    build_daily_distance_time_chart,
    build_contribution_pie_chart,
)
from .page_assembler import assemble_full_report
from .table_builder import build_daily_stats_table_html
from .template_builder import render_statistics_tab_content

LOGGER = logger.bind(name="CSB-Processing.Statistic.Plotting.ReportGenerator")


def _serialize_figure_to_html(fig, div_id: str, include_plotlyjs: bool = False) -> str:
    """
    Sérialise une figure Plotly en HTML.

    :param fig: Figure Plotly à sérialiser.
    :param div_id: Identifiant du div HTML.
    :type div_id: str
    :param include_plotlyjs: Inclure Plotly.js dans le HTML.
    :type include_plotlyjs: bool
    :return: Fragment HTML.
    :rtype: str
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config=PLOTLY_CONFIG,
        div_id=div_id,
        default_width="100%",
        default_height="500px",
    )


def generate_statistics_report(
    stats: SurveyStatistics,
    metadata_sections_html: str,
    title: str,
    output_path: Path,
    *,
    show_in_browser: bool = False,
) -> None:
    """
    Génère le rapport HTML complet avec métadonnées et statistiques.

    Pipeline complet :
      1. Générer toutes les figures Plotly
      2. Sérialiser les figures en HTML
      3. Générer les tableaux HTML
      4. Rendre le template de l'onglet statistiques
      5. Assembler avec l'onglet métadonnées
      6. Écrire le fichier
      7. (Optionnel) Ouvrir dans le navigateur

    :param stats: Statistiques complètes du levé.
    :type stats: SurveyStatistics
    :param metadata_sections_html: HTML de l'onglet métadonnées.
    :type metadata_sections_html: str
    :param title: Titre du rapport.
    :type title: str
    :param output_path: Chemin du fichier HTML de sortie.
    :type output_path: Path
    :param show_in_browser: Ouvrir le rapport dans le navigateur.
    :type show_in_browser: bool
    :return: None
    :rtype: None
    """
    LOGGER.info(f"Génération du rapport de statistiques : {title}")

    # ── 1. Générer les figures Plotly ──────────────────────────────────
    LOGGER.debug("Génération des figures Plotly...")

    figures = {
        "chart-daily-distance-time": build_daily_distance_time_chart(stats.daily_stats),
        "chart-contribution-distance": build_contribution_pie_chart(
            stats.daily_stats  # , metric="distance"
        ),
    }

    # ── 2. Sérialiser les figures en HTML ──────────────────────────────
    LOGGER.debug("Sérialisation des figures...")

    figures_html = {}
    first_figure = True

    for fig_id, fig in figures.items():
        # Inclure Plotly.js seulement dans la première figure
        html = _serialize_figure_to_html(fig, fig_id, include_plotlyjs=first_figure)
        figures_html[fig_id] = html
        first_figure = False

    # ── 3. Générer les tableaux HTML ───────────────────────────────────
    LOGGER.debug("Génération des tableaux HTML...")

    daily_table_html = build_daily_stats_table_html(stats.daily_stats)

    # ── 4. Rendre le template de l'onglet statistiques ────────────────
    LOGGER.debug("Rendu du template statistiques...")

    statistics_content_html = render_statistics_tab_content(
        daily_table_html, figures_html
    )

    # ── 5. Assembler avec l'onglet métadonnées ─────────────────────────
    LOGGER.debug("Assemblage de la page complète...")

    # Trouver le template
    template_path = (
        Path(__file__).parent.parent / "templates" / "metadata_export.html.j2"
    )

    assemble_full_report(
        metadata_sections_html,
        statistics_content_html,
        title,
        output_path,
        template_path,
    )

    LOGGER.success(f"Rapport généré : {output_path}")

    # ── 6. (Optionnel) Ouvrir dans le navigateur ───────────────────────
    if show_in_browser:
        LOGGER.info("Ouverture du rapport dans le navigateur...")
        webbrowser.open(output_path.as_uri())
