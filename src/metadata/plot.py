"""
Module de génération du rapport HTML des métadonnées.

Ce module orchestre la génération du rapport HTML complet.
Supporte deux modes :
  - Métadonnées seules (ancien comportement)
  - Métadonnées + Statistiques avec visualisations Plotly (nouveau)
"""

from pathlib import Path
from typing import Optional

import i18n
from loguru import logger

from .metadata_renderer import render_metadata_sections
from .statistic.models import SurveyStatistics
from .plotting.page_assembler import assemble_metadata_only_report

LOGGER = logger.bind(name="CSB-Processing.Metadata.Plot")

# ── Chemins des templates ──────────────────────────────────────────────────

_TEMPLATES_DIR: Path = Path(__file__).parent / "templates"
_TEMPLATE_NAME: str = "metadata_export.html.j2"


# ── Point d'entrée public ──────────────────────────────────────────────────


def plot_metadata(
    metadata: dict,
    title: str,
    output_path: Path,
    *,
    statistics: Optional[SurveyStatistics] = None,
    show_in_browser: bool = False,
) -> None:
    """
    Génère le rapport HTML des métadonnées (avec ou sans statistiques).

    Si ``statistics`` est fourni, génère un rapport complet avec visualisations.
    Sinon, génère uniquement l'onglet métadonnées (ancien comportement).

    :param metadata: Dictionnaire des métadonnées.
    :type metadata: dict
    :param title: Titre du rapport.
    :type title: str
    :param output_path: Chemin du fichier HTML de sortie.
    :type output_path: Path
    :param statistics: Statistiques de levé (optionnel).
    :type statistics: Optional[SurveyStatistics]
    :param show_in_browser: Ouvrir dans le navigateur après génération.
    :type show_in_browser: bool
    """
    LOGGER.info(i18n.t("metadata.plot.generating_report", title=title))

    metadata_sections_html = render_metadata_sections(metadata)
    html_output_path = output_path.with_suffix(".html")
    template_path = _TEMPLATES_DIR / _TEMPLATE_NAME

    if statistics is not None:
        from .plotting import generate_statistics_report

        generate_statistics_report(
            stats=statistics,
            metadata_sections_html=metadata_sections_html,
            title=title,
            output_path=html_output_path,
            show_in_browser=show_in_browser,
        )
    else:
        _generate_metadata_only_report(
            metadata_sections_html, title, html_output_path, template_path
        )


def _generate_metadata_only_report(
    metadata_sections_html: str, title: str, output_path: Path, template_path: Path
) -> None:
    """
    Génère un rapport avec métadonnées seulement (onglet stats vide).

    :param metadata_sections_html: HTML des sections de métadonnées.
    :type metadata_sections_html: str
    :param title: Titre du rapport.
    :type title: str
    :param output_path: Chemin du fichier HTML de sortie.
    :type output_path: Path
    :param template_path: Chemin du template HTML.
    :type template_path: Path
    """
    try:
        assemble_metadata_only_report(
            metadata_sections_html=metadata_sections_html,
            title=title,
            output_path=output_path,
            template_path=template_path,
        )
        LOGGER.success(
            i18n.t("metadata.plot.html_save_success", output_path=output_path)
        )
    except Exception as error:
        LOGGER.error(i18n.t("metadata.plot.html_save_error", error=error))
