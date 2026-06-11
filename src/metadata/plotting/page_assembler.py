"""
Assembleur de page HTML complète (métadonnées + statistiques).

Ce module fusionne les deux onglets dans le template principal.
"""

from datetime import datetime
from pathlib import Path

import i18n

_STATS_PLACEHOLDER = "<!--STATS_CONTENT-->"


def _build_empty_stats_content() -> str:
    """
    Construit le contenu HTML pour l'onglet statistiques vide.

    :return: HTML de remplacement quand aucune statistique n'est disponible.
    :rtype: str
    """
    return """
        <div class="content-card">
            <div class="content-card-title">
                <span class="material-symbols-outlined">monitoring</span>
                {tab_stats}
            </div>
            <p class="none-text">{stats_empty_desc}</p>
        </div>

        <details class="info-card">
            <summary>
                <span class="material-symbols-outlined" style="font-size:18px;line-height:1;vertical-align:middle;">info</span>
                {stats_placeholder_title}
            </summary>
            <div class="info-card-body">
                <p>{stats_placeholder_body}</p>
            </div>
        </details>
    """.format(
        tab_stats=i18n.t("metadata.plot.tab_stats"),
        stats_empty_desc=i18n.t("metadata.plot.stats_empty_desc"),
        stats_placeholder_title=i18n.t("metadata.plot.stats_placeholder_title"),
        stats_placeholder_body=i18n.t("metadata.plot.stats_placeholder_body"),
    )


def _apply_common_replacements(html_content: str, title: str) -> str:
    """
    Applique les remplacements de variables communs aux deux modes de rapport.

    :param html_content: Contenu HTML du template.
    :type html_content: str
    :param title: Titre du rapport.
    :type title: str
    :return: HTML avec variables remplacées.
    :rtype: str
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_lang = i18n.get("locale") or "en"
    favicon_href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>"
    font_family = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

    replacements = {
        "__EXPORT_TITLE__": title,
        "__GENERATED_AT__": generated_at,
        "{{ html_lang }}": html_lang,
        "{{ favicon_href }}": favicon_href,
        "{{ font_family }}": font_family,
        "{{ labels.report_subtitle }}": i18n.t("metadata.plot.report_subtitle"),
        "{{ labels.tab_metadata }}": i18n.t("metadata.plot.tab_metadata"),
        "{{ labels.tab_stats }}": i18n.t("metadata.plot.tab_stats"),
        "{{ labels.generated_at }}": i18n.t("metadata.plot.generated_at"),
    }

    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    return html_content


def assemble_full_report(
    metadata_sections_html: str,
    statistics_content_html: str,
    title: str,
    output_path: Path,
    template_path: Path,
) -> None:
    """
    Assemble les deux onglets dans le template principal et écrit le fichier.

    :param metadata_sections_html: HTML de l'onglet métadonnées.
    :type metadata_sections_html: str
    :param statistics_content_html: HTML de l'onglet statistiques.
    :type statistics_content_html: str
    :param title: Titre du rapport.
    :type title: str
    :param output_path: Chemin du fichier HTML de sortie.
    :type output_path: Path
    :param template_path: Chemin du template metadata_export.html.j2.
    :type template_path: Path
    :return: None
    :rtype: None
    """
    html_content = template_path.read_text(encoding="utf-8")

    html_content = _apply_common_replacements(html_content, title)
    html_content = html_content.replace("__METADATA_SECTIONS__", metadata_sections_html)
    html_content = html_content.replace(_STATS_PLACEHOLDER, statistics_content_html)

    output_path.write_text(html_content, encoding="utf-8")


def assemble_metadata_only_report(
    metadata_sections_html: str,
    title: str,
    output_path: Path,
    template_path: Path,
) -> None:
    """
    Assemble un rapport métadonnées-seulement (onglet stats vide).

    :param metadata_sections_html: HTML de l'onglet métadonnées.
    :type metadata_sections_html: str
    :param title: Titre du rapport.
    :type title: str
    :param output_path: Chemin du fichier HTML de sortie.
    :type output_path: Path
    :param template_path: Chemin du template metadata_export.html.j2.
    :type template_path: Path
    :return: None
    :rtype: None
    """
    html_content = template_path.read_text(encoding="utf-8")

    html_content = _apply_common_replacements(html_content, title)
    html_content = html_content.replace("__METADATA_SECTIONS__", metadata_sections_html)
    html_content = html_content.replace(
        _STATS_PLACEHOLDER, _build_empty_stats_content()
    )

    output_path.write_text(html_content, encoding="utf-8")
