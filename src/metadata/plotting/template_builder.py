"""
Constructeur de template pour l'onglet statistiques.

Ce module rend le contenu HTML de l'onglet statistiques en combinant
tableaux et figures Plotly.
"""

import i18n


def render_statistics_tab_content(
    daily_table_html: str,
    figures_html: dict[str, str],
) -> str:
    """
    Rend le contenu HTML complet de l'onglet statistiques.

    Le tableau daily avec les totaux apparaît en premier.

    :param daily_table_html: HTML du tableau détaillé par jour (avec totaux).
    :type daily_table_html: str
    :param figures_html: Dict {figure_id: fragment_html}.
    :type figures_html: dict[str, str]
    :return: HTML complet de l'onglet statistiques.
    :rtype: str
    """
    # Construction du HTML
    html_parts = []

    # ── Tableau détaillé par jour (EN PREMIER) ────────────────────────
    html_parts.append(
        """
        <div class="content-card">
            <div class="content-card-title">
                <span class="material-symbols-outlined">table_chart</span>
                {title}
            </div>
            {daily_table}
        </div>
        """.format(
            title=i18n.t("metadata.plot.stats_daily_details_title"),
            daily_table=daily_table_html,
        )
    )

    # ── Graphique 1 : Distance + Temps par Jour ───────────────────────
    html_parts.append(
        """
        <div class="content-card content-card-figure">
            <div class="content-card-title">
                <span class="material-symbols-outlined">bar_chart</span>
                {title}
            </div>
            {chart}
        </div>
        """.format(
            title=i18n.t("metadata.plot.stats_chart_daily_title"),
            chart=figures_html.get("chart-daily-distance-time", ""),
        )
    )

    # ── Graphique 2 : Contribution par Jour (Distance) ────────────────
    html_parts.append(
        """
        <div class="content-card content-card-figure">
            <div class="content-card-title">
                <span class="material-symbols-outlined">pie_chart</span>
                {title}
            </div>
            {chart}
        </div>
        """.format(
            title=i18n.t("metadata.plot.stats_chart_contribution_title"),
            chart=figures_html.get("chart-contribution-distance", ""),
        )
    )

    return "\n".join(html_parts)
