"""
Constructeur de tableaux HTML pour statistiques de levé.

Ce module génère des fragments HTML pour les tableaux
détaillés de statistiques.
"""

import i18n

from ..statistic.models import DailyStats


def build_daily_stats_table_html(daily_stats: list[DailyStats]) -> str:
    """
    Construit un tableau HTML détaillé par jour avec une ligne de total en premier.

    :param daily_stats: Liste des statistiques journalières.
    :type daily_stats: list[DailyStats]
    :return: Fragment HTML <table>...</table>.
    :rtype: str
    """
    # Calculer les totaux
    total_points = sum(day.point_count for day in daily_stats)
    total_kilometers = sum(day.distance.kilometers for day in daily_stats)
    total_nautical_miles = sum(day.distance.nautical_miles for day in daily_stats)
    total_minutes = sum(day.time.total_minutes for day in daily_stats)
    total_hours = sum(day.time.total_hours for day in daily_stats)
    total_days = sum(day.time.total_days for day in daily_stats)

    html_rows = []

    # Ajouter la ligne de total en premier
    html_rows.append(
        f"<tr style='font-weight: bold; background-color: #e0e0e0;'>"
        f"<td style='padding: 10px 16px;'><strong>{i18n.t('metadata.plot.stats_column_total')}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_points:,}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_kilometers:,.3f}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_nautical_miles:,.3f}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_minutes:,.3f}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_hours:,.3f}</strong></td>"
        f"<td style='padding: 10px 16px;'><strong>{total_days:,.3f}</strong></td>"
        f"</tr>"
    )

    # Ajouter les lignes pour chaque jour
    for day in daily_stats:
        html_rows.append(
            f"<tr>"
            f"<td style='padding: 10px 16px;'>{day.date}</td>"
            f"<td style='padding: 10px 16px;'>{day.point_count:,}</td>"
            f"<td style='padding: 10px 16px;'>{day.distance.kilometers:,.3f}</td>"
            f"<td style='padding: 10px 16px;'>{day.distance.nautical_miles:,.3f}</td>"
            f"<td style='padding: 10px 16px;'>{day.time.total_minutes:,.3f}</td>"
            f"<td style='padding: 10px 16px;'>{day.time.total_hours:,.3f}</td>"
            f"<td style='padding: 10px 16px;'>{day.time.total_days:,.3f}</td>"
            f"</tr>"
        )

    return f"""
    <table class="table-striped">
        <thead>
            <tr>
                <th>{i18n.t("metadata.plot.stats_column_date")}</th>
                <th>{i18n.t("metadata.plot.stats_column_points")}</th>
                <th>{i18n.t("metadata.plot.stats_column_distance_km")}</th>
                <th>{i18n.t("metadata.plot.stats_column_distance_nm")}</th>
                <th>{i18n.t("metadata.plot.stats_column_time_min")}</th>
                <th>{i18n.t("metadata.plot.stats_column_time_h")}</th>
                <th>{i18n.t("metadata.plot.stats_column_time_day")}</th>
            </tr>
        </thead>
        <tbody>
            {"".join(html_rows)}
        </tbody>
    </table>
    """
