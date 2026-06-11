"""
Constructeur de figures Plotly pour statistiques de levé.

Ce module fournit les fonctions de construction de chaque figure
individuelle (graphiques, histogrammes, scatter plots, etc.).
"""

import i18n
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..statistic.models import DailyStats
from .constants import COLOR_PALETTE, LAYOUT_DEFAULTS


def build_daily_distance_time_chart(daily_stats: list[DailyStats]) -> go.Figure:
    """
    Construit un histogramme groupé distance + temps + points par jour.

    Utilise trois axes Y : distance (gauche), temps (droite) et
    nombre de points (droite décalé).

    :param daily_stats: Liste des statistiques journalières.
    :type daily_stats: list[DailyStats]
    :return: Figure Plotly avec barres groupées et ligne de points.
    :rtype: go.Figure
    """
    dates = [day.date for day in daily_stats]
    distances_nm = [day.distance.nautical_miles for day in daily_stats]
    times_h = [day.time.total_hours for day in daily_stats]
    counts = [day.point_count for day in daily_stats]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Barres de distance (axe gauche)
    fig.add_trace(
        go.Bar(
            x=dates,
            y=distances_nm,
            name=i18n.t("metadata.plot.legend_distance"),
            marker_color=COLOR_PALETTE["distance"],
            yaxis="y",
            offsetgroup=0,
            hovertemplate="<b>%{x}</b><br>"
            + i18n.t("metadata.plot.legend_distance")
            + ": %{y:.2f} NM<extra></extra>",
        ),
        secondary_y=False,
    )

    # Barres de temps (axe droit)
    fig.add_trace(
        go.Bar(
            x=dates,
            y=times_h,
            name=i18n.t("metadata.plot.legend_time"),
            marker_color=COLOR_PALETTE["time"],
            yaxis="y2",
            offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>"
            + i18n.t("metadata.plot.legend_time")
            + ": %{y:.2f} h<extra></extra>",
        ),
        secondary_y=True,
    )

    # Ligne de points (3e axe, décalé à droite)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=counts,
            name=i18n.t("metadata.plot.legend_points"),
            mode="lines+markers",
            line={"color": COLOR_PALETTE["points"], "width": 2},
            marker={"size": 8},
            yaxis="y3",
            hovertemplate="<b>%{x}</b><br>"
            + i18n.t("metadata.plot.legend_points")
            + ": %{y:,}<extra></extra>",
        )
    )

    # Fusionner les layouts avec marge personnalisée
    layout_dict = dict(LAYOUT_DEFAULTS)
    layout_dict["margin"] = {"l": 60, "r": 110, "t": 40, "b": 60}

    fig.update_layout(
        **layout_dict,
        barmode="group",
        autosize=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "center",
            "x": 0.5,
        },
        yaxis3={
            "overlaying": "y",
            "side": "right",
            "position": 1.0,
            "anchor": "free",
            "showgrid": False,
            "title": {
                "text": i18n.t("metadata.plot.axis_point_count"),
                "font": {"color": COLOR_PALETTE["points"]},
            },
            "tickfont": {"color": COLOR_PALETTE["points"]},
        },
    )

    fig.update_xaxes(
        title_text=i18n.t("metadata.plot.axis_date"),
        tickangle=-45,
        showgrid=False,
        type="category",
    )
    fig.update_yaxes(
        title_text=i18n.t("metadata.plot.axis_distance_nm"),
        secondary_y=False,
        showgrid=False,
    )
    fig.update_yaxes(
        title_text=i18n.t("metadata.plot.axis_time_hours"),
        secondary_y=True,
        showgrid=False,
    )

    return fig


# def build_contribution_pie_chart(
#     daily_stats: list[DailyStats], metric: str = "distance"
# ) -> go.Figure:
#     """
#     Construit un diagramme circulaire de contribution par jour.
#
#     :param daily_stats: Liste des statistiques journalières.
#     :type daily_stats: list[DailyStats]
#     :param metric: Métrique à afficher ("distance" ou "time").
#     :type metric: str
#     :return: Figure Plotly diagramme circulaire.
#     :rtype: go.Figure
#     """
#     dates = [day.date for day in daily_stats]
#
#     if metric == "distance":
#         values = [day.distance.nautical_miles for day in daily_stats]
#         label_suffix = "NM"
#     else:  # time
#         values = [day.time.total_hours for day in daily_stats]
#         label_suffix = "h"
#
#     fig = go.Figure()
#
#     fig.add_trace(
#         go.Pie(
#             labels=dates,
#             values=values,
#             hovertemplate="<b>%{label}</b><br>%{value:.2f} "
#             + label_suffix
#             + "<br>%{percent}<extra></extra>",
#             textinfo="percent",
#             textposition="inside",
#         )
#     )
#
#     fig.update_layout(
#         **{k: v for k, v in LAYOUT_DEFAULTS.items() if k != "xaxis" and k != "yaxis"},
#         showlegend=True,
#         legend={
#             "orientation": "v",
#             "yanchor": "middle",
#             "y": 0.5,
#             "xanchor": "center",
#             "x": 1.02,
#         },
#         legend_title={
#             "text": "<b>" + i18n.t("metadata.plot.legend_date") + "</b>",
#             "side": "top",
#             "font": {"size": 12},
#         },
#         autosize=True,
#     )
#
#     return fig


def build_contribution_pie_chart(
    daily_stats: list[DailyStats],
) -> go.Figure:
    """
    Construit trois diagrammes circulaires côte à côte : distance, temps et points.

    Affiche trois subplots horizontaux avec chaque métrique dans sa propre
    pie chart.

    :param daily_stats: Liste des statistiques journalières.
    :type daily_stats: list[DailyStats]
    :return: Figure Plotly avec 3 pie charts en ligne horizontale.
    :rtype: go.Figure
    """
    dates = [day.date for day in daily_stats]
    distances_nm = [day.distance.nautical_miles for day in daily_stats]
    times_h = [day.time.total_hours for day in daily_stats]
    points = [day.point_count for day in daily_stats]

    # Créer 3 subplots côte à côte (1 ligne, 3 colonnes)
    fig = make_subplots(
        rows=1,
        cols=3,
        specs=[[{"type": "pie"}, {"type": "pie"}, {"type": "pie"}]],
        subplot_titles=(
            i18n.t("metadata.plot.legend_distance"),
            i18n.t("metadata.plot.legend_time"),
            i18n.t("metadata.plot.legend_points"),
        ),
    )

    # Pie 1 : Distance
    fig.add_trace(
        go.Pie(
            labels=dates,
            values=distances_nm,
            name=i18n.t("metadata.plot.legend_distance"),
            hovertemplate="<b>%{label}</b><br>%{value:.2f} NM<br>%{percent}<extra></extra>",
            textinfo="percent",
            textposition="inside",
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    # Pie 2 : Temps
    fig.add_trace(
        go.Pie(
            labels=dates,
            values=times_h,
            name=i18n.t("metadata.plot.legend_time"),
            hovertemplate="<b>%{label}</b><br>%{value:.2f} h<br>%{percent}<extra></extra>",
            textinfo="percent",
            textposition="inside",
            showlegend=True,
        ),
        row=1,
        col=2,
    )

    # Pie 3 : Points (Sondes)
    fig.add_trace(
        go.Pie(
            labels=dates,
            values=points,
            name=i18n.t("metadata.plot.legend_points"),
            hovertemplate="<b>%{label}</b><br>%{value:,} points<br>%{percent}<extra></extra>",
            textinfo="percent",
            textposition="inside",
            showlegend=True,
        ),
        row=1,
        col=3,
    )

    # Configuration du layout
    layout_dict = dict(LAYOUT_DEFAULTS)
    layout_dict["margin"] = {"l": 20, "r": 250, "t": 80, "b": 40}

    fig.update_layout(
        **layout_dict,
        height=600,
        autosize=True,
        showlegend=True,
        legend={
            "orientation": "v",
            "yanchor": "middle",
            "y": 0.5,
            "xanchor": "left",
            "x": 1.02,
            "bgcolor": "rgba(255,255,255,0.8)",
            "bordercolor": "rgba(0,0,0,0.2)",
            "font": {"size": 10},
        },
    )

    return fig
