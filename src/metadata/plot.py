"""
Module pour la visualisation des métadonnées des levés hydrographiques.

Ce module contient les fonctions pour afficher les métadonnées des levés hydrographiques.
"""

from pathlib import Path
from typing import Optional

from loguru import logger
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


LOGGER = logger.bind(name="CSB-Processing.Metadata.Plot")


COLOR_PALETTE: list[str] = [
    "rgba(205,92,92, 0.2)",
    "rgba(205,92,92, 0.3)",
    "rgba(205,92,92, 0.45)",
    "rgba(205,92,92, 0.6)",
    "rgba(205,92,92, 0.8)",
    "rgba(205,92,92, 1.0)",
]
HEADER_COLOR: str = "rgba(205,92,92, 0.65)"
CELL_COLOR: str = "lavender"


def create_plotly_table(df: pd.DataFrame, header_labels: list[str]) -> go.Table:
    """
    Génère une table Plotly à partir d'un DataFrame.

    :param df: DataFrame contenant les données à afficher.
    :type df: pd.DataFrame
    :param header_labels: Liste des étiquettes d'en-tête.
    :type header_labels: list[str]
    :return: Table Plotly contenant les données du DataFrame.
    :rtype: go.Table
    """
    return go.Table(
        columnwidth=[2, 3],
        header=dict(
            values=header_labels,
            fill_color=HEADER_COLOR,
            align="left",
            font=dict(size=14, weight="bold"),
        ),
        cells=dict(
            values=[df[col] for col in df.columns],
            fill_color=CELL_COLOR,
            align="left",
        ),
    )


def plot_iho_order_statistic_bar(iho_order_statistic: dict) -> go.Bar:
    """
    Génère un graphique en barres pour les statistiques des ordres IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Graphique en barres des statistiques des ordres IHO.
    :rtype: go.Bar
    """
    labels, values, colors = [], [], []

    for index, (order, stats) in enumerate(iho_order_statistic.items()):
        value = stats["Sounding Within Order (%)"]
        labels.append(order)
        values.append(value)
        colors.append(
            "rgba(205,92,92, 1.0)"
            if value == 100
            else COLOR_PALETTE[index % len(COLOR_PALETTE)]
        )

    return go.Bar(
        x=labels,
        y=values,
        text=values,
        textposition="auto",
        marker=dict(color=colors),
        showlegend=False,
    )


def plot_iho_order_statistics(iho_order_statistic: dict) -> go.Figure:
    """
    Crée une figure contenant les statistiques des ordres IHO sous forme de tableaux.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Figure Plotly contenant les statistiques des ordres IHO.
    :rtype: go.Figure
    """
    data: dict = {
        order: stats
        for order, stats in iho_order_statistic.items()
        if stats["Sounding Count Within Order"] != 0
    }

    fig = make_subplots(
        rows=len(data),
        cols=1,
        subplot_titles=list(data.keys()),
        vertical_spacing=0.1,
        specs=[[{"type": "domain"}] for _ in data],
    )

    for index, (order, stats) in enumerate(data.items(), start=1):
        df = pd.DataFrame([stats]).transpose().reset_index()
        df.columns = [order, "Value"]
        fig.add_trace(create_plotly_table(df, [order, "Value"]), row=index, col=1)

    return fig


def plot_depth_statistics(iho_order_statistic: dict) -> go.Figure:
    """
    Génère un graphique des statistiques de profondeur par ordre IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Figure Plotly contenant les statistiques de profondeur.
    :rtype: go.Figure
    """
    orders = [
        order
        for order in iho_order_statistic
        if any(
            iho_order_statistic[order].get(key) is not None
            for key in ["Min Depth (m)", "Max Depth (m)", "Mean Depth (m)"]
        )
    ]

    depth_data = {
        "Min Depth (m)": [
            iho_order_statistic[order].get("Min Depth (m)", None) for order in orders
        ],
        "Max Depth (m)": [
            iho_order_statistic[order].get("Max Depth (m)", None) for order in orders
        ],
        "Mean Depth (m)": [
            iho_order_statistic[order].get("Mean Depth (m)", None) for order in orders
        ],
    }

    fig = go.Figure()
    colors = ["rgba(205,92,92, 0.25)", "rgba(205,92,92, 0.95)", "rgba(205,92,92, 0.65)"]

    for (name, data), color in zip(depth_data.items(), colors):
        fig.add_trace(
            go.Scatter(
                x=orders,
                y=data,
                mode="lines+markers",
                name=name,
                marker=dict(size=10, color=color),
                showlegend=True,
            )
        )

    return fig


def plot_metadata(
    metadata: dict,
    title: str,
    output_path: Optional[Path] = None,
    show_plot: bool = False,
) -> None:
    """
    Affiche et sauvegarde les métadonnées des levés hydrographiques.

    :param metadata: Dictionnaire contenant les métadonnées du levé hydrographique.
    :type metadata: Dict
    :param title: Titre de la figure.
    :type title: str
    :param output_path: Chemin de sortie pour la figure.
    :type output_path: Optional[Path]
    :param show_plot: Indique si la figure doit être affichée.
    :type show_plot: bool
    """
    LOGGER.debug(f"Génération des graphiques des métadonnées pour : {title}.")

    df = (
        pd.DataFrame(
            [{k: v for k, v in metadata.items() if k != "IHO Order Statistic"}]
        )
        .transpose()
        .reset_index()
    )
    df.columns = ["Metadata", "Value"]

    fig = make_subplots(
        rows=6,
        cols=2,
        specs=[
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}],
            [None, {"type": "domain"}],
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}],
            [None, {"type": "domain"}],
            [None, {"type": "domain"}],
        ],
        subplot_titles=(
            "Metadata Table",
            "Survey Order Statistics",
            "Percentage of Soundings in Survey Order",
            "",
            "",
            "Depths by Order",
        ),
        vertical_spacing=0.045,
        horizontal_spacing=0.05,
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19, 0.19],
        column_widths=[0.6, 0.4],
    )

    fig.add_trace(create_plotly_table(df, ["Metadata", "Value"]), row=1, col=1)
    fig.add_trace(
        plot_iho_order_statistic_bar(metadata["IHO Order Statistic"]), row=2, col=1
    )

    iho_order_fig = plot_iho_order_statistics(metadata["IHO Order Statistic"])
    for i, trace in enumerate(iho_order_fig.data, start=1):
        fig.add_trace(trace, row=i, col=2)

    depth_fig = plot_depth_statistics(metadata["IHO Order Statistic"])
    for trace in depth_fig.data:
        fig.add_trace(trace, row=4, col=1)

    # Mettre à jour la mise en page de la figure
    fig.update_layout(
        height=2200,
        showlegend=True,
        title=dict(
            text=title,
            font=dict(size=24, weight="bold"),
            x=0.5,
            y=0.99,
            xanchor="center",
        ),
        xaxis_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis_title=dict(
            text="Percentage of Soundings in Survey Order",
            font=dict(weight="bold"),
        ),
        xaxis2_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis2_title=dict(
            text="Depth (m)",
            font=dict(weight="bold"),
        ),
        yaxis2=dict(autorange="reversed"),
        template="plotly",
        annotations=[
            dict(
                text=annotation["text"],
                x=annotation["x"],
                y=annotation["y"],
                xanchor=annotation["xanchor"],
                yanchor=annotation["yanchor"],
                font=dict(size=20, weight="bold"),
                showarrow=False,
            )
            for annotation in fig["layout"]["annotations"]
        ],
        legend=dict(
            x=0.01,  # Position horizontale (1 = à droite, 0 = à gauche)
            y=0.21,  # Position verticale (1 = en haut, 0 = en bas)
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255, 255, 255, 0.7)",
        ),
    )

    if show_plot:
        fig.show()
    if output_path:
        fig.write_html(output_path)
