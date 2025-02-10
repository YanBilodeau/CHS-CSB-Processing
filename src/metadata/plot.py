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

from metadata.order.order_models import OrderEnum

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


def create_table_data(df: pd.DataFrame, header_labels: list[str]) -> go.Table:
    """
    Génère une table Plotly à partir d'un DataFrame.

    :param df: DataFrame contenant les données à afficher.
    :type df: pd.DataFrame
    :param header_labels: Liste des étiquettes d'en-tête.
    :type header_labels: list[str]
    :return: Table Plotly contenant les données du DataFrame.
    :rtype: go.Table
    """
    formats = [
        ",.0f" if row[0] == "Sounding Count Within Order" else None
        for row in df.itertuples(index=False)
    ]

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
            format=[None, formats],
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


def create_table_iho_order_statistics(iho_order_statistic: dict) -> go.Figure:
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

    fig: go.Figure = make_subplots(
        rows=len(data),
        cols=1,
        subplot_titles=list(data.keys()),
        vertical_spacing=0.1,
        specs=[[{"type": "domain"}] for _ in data],
    )

    for index, (order, stats) in enumerate(data.items(), start=1):
        df = pd.DataFrame([stats]).transpose().reset_index()
        df.columns = [order, "Value"]
        fig.add_trace(create_table_data(df, [order, "Value"]), row=index, col=1)

    return fig


def plot_statistics(
    iho_order_statistic: dict, keys: list[str], colors: list[str], y_title: str
) -> go.Figure:
    """
    Génère un graphique des statistiques par ordre IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: dict
    :param keys: Liste des clés pour les données à tracer.
    :type keys: list[str]
    :param colors: Liste des couleurs pour les traces.
    :type colors: list[str]
    :param y_title: Titre de l'axe des y.
    :type y_title: str
    :return: Figure Plotly contenant les statistiques.
    :rtype: go.Figure
    """
    orders = [
        order
        for order in iho_order_statistic
        if any(iho_order_statistic[order].get(key) is not None for key in keys)
    ]

    data = {
        key: [iho_order_statistic[order].get(key, None) for order in orders]
        for key in keys
    }

    fig = go.Figure()

    for (name, values), color in zip(data.items(), colors):
        fig.add_trace(
            go.Scatter(
                x=orders,
                y=values,
                mode="lines+markers",
                name=name,
                marker=dict(size=10, color=color),
                showlegend=True,
            )
        )

    fig.update_layout(yaxis_title=y_title)

    return fig


def plot_depth_statistics(iho_order_statistic: dict) -> go.Figure:
    """
    Génère un graphique des statistiques de profondeur par ordre IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Figure Plotly contenant les statistiques de profondeur.
    :rtype: go.Figure
    """
    return plot_statistics(
        iho_order_statistic,
        keys=["Min Depth (m)", "Max Depth (m)", "Mean Depth (m)"],
        colors=[
            "rgba(205,92,92, 0.35)",
            "rgba(205,92,92, 0.95)",
            "rgba(205,92,92, 0.65)",
        ],
        y_title="Depth (m)",
    )


def plot_tvu_statistics(iho_order_statistic: dict) -> go.Figure:
    """
    Génère un graphique des statistiques de TVU par ordre IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Figure Plotly contenant les statistiques de profondeur.
    :rtype: go.Figure
    """
    return plot_statistics(
        iho_order_statistic,
        keys=["Min TVU (m)", "Max TVU (m)", "Mean TVU (m)"],
        colors=[
            "rgba(92,205,92, 0.35)",
            "rgba(92,205,92, 0.95)",
            "rgba(92,205,92, 0.65)",
        ],
        y_title="TVU (m)",
    )


def plot_thu_statistics(iho_order_statistic: dict) -> go.Figure:
    """
    Génère un graphique des statistiques de THU par ordre IHO.

    :param iho_order_statistic: Dictionnaire contenant les statistiques des ordres IHO.
    :type iho_order_statistic: Dict
    :return: Figure Plotly contenant les statistiques de profondeur.
    :rtype: go.Figure
    """
    return plot_statistics(
        iho_order_statistic,
        keys=["Min THU (m)", "Max THU (m)", "Mean THU (m)"],
        colors=[
            "rgba(92,92,205, 0.35)",
            "rgba(92,92,205, 0.95)",
            "rgba(92,92,205, 0.65)",
        ],
        y_title="THU (m)",
    )


def create_legend(
    x=0.009, y=0.37, xanchor="left", yanchor="top", bgcolor="rgba(255, 255, 255, 0.7)"
) -> dict:
    """
    Crée une légende pour un graphique Plotly.

    :param x: Position x de la légende.
    :type x: float
    :param y: Position y de la légende.
    :type y: float
    :param xanchor: Ancrage horizontal de la légende.
    :type xanchor: str
    :param yanchor: Ancrage vertical de la légende.
    :type yanchor: str
    :param bgcolor: Couleur de fond de la légende.
    :type bgcolor: str
    :return: Dictionnaire de configuration de la légende.
    :rtype: dict
    """
    return dict(
        x=x,
        y=y,
        xanchor=xanchor,
        yanchor=yanchor,
        bgcolor=bgcolor,
    )


def create_annotations(annotations_data: list[dict]) -> list[dict]:
    """
    Crée une liste d'annotations pour un graphique Plotly.

    :param annotations_data: Liste de dictionnaires contenant les données des annotations.
    :type annotations_data: list[dict]
    :return: Liste de dictionnaires de configuration des annotations.
    :rtype: list[dict]
    """
    return [
        dict(
            text=annotation["text"],
            x=annotation["x"],
            y=annotation["y"],
            xanchor=annotation["xanchor"],
            yanchor=annotation["yanchor"],
            font=dict(size=20, weight="bold"),
            showarrow=False,
        )
        for annotation in annotations_data
    ]


def update_layout(
    fig: go.Figure, title: str, cell_color: str, annotations: list[dict], legend: dict
) -> None:
    """
    Met à jour la mise en page d'une figure Plotly.

    :param fig: Figure Plotly à mettre à jour.
    :type fig: go.Figure
    :param title: Titre de la figure.
    :type title: str
    :param cell_color: Couleur de fond de la figure.
    :type cell_color: str
    :param annotations: Liste des annotations à ajouter à la figure.
    :type annotations: list[dict]
    :param legend: Dictionnaire de configuration de la légende.
    :type legend: dict
    """
    fig.update_layout(
        height=2800,
        plot_bgcolor=cell_color,
        # showlegend=True,
        title=dict(
            text=title,
            font=dict(size=24, weight="bold"),
            x=0.5,
            y=0.99,
            xanchor="center",
        ),
        xaxis_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis_title=dict(
            text="Percentage (%)",
            font=dict(weight="bold"),
        ),
        xaxis2_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis2_title=dict(
            text="Depth (m)",
            font=dict(weight="bold"),
        ),
        yaxis2=dict(autorange="reversed"),
        xaxis3_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis3_title=dict(
            text="TVU (m)",
            font=dict(weight="bold"),
        ),
        yaxis3=dict(autorange="reversed"),
        xaxis4_title=dict(text="Survey Order", font=dict(weight="bold")),
        yaxis4_title=dict(
            text="THU (m)",
            font=dict(weight="bold"),
        ),
        yaxis4=dict(autorange="reversed"),
        template="plotly",
        annotations=annotations,
        legend=legend,
    )


def create_metadata_figure() -> go.Figure:
    """
    Crée une figure Plotly avec des sous-graphiques pour les métadonnées des levés hydrographiques.

    :return: Figure Plotly contenant les sous-graphiques.
    :rtype: go.Figure
    """
    fig: go.Figure = make_subplots(
        rows=7,
        cols=2,
        specs=[
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}],
            [None, {"type": "domain"}],
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}],
            [None, {"type": "domain"}],
            [{"type": "xy"}, {"type": "domain"}],
            [{"type": "xy"}, None],
        ],
        subplot_titles=(
            "Metadata Table",
            "Survey Order Statistics",
            "Soundings in Survey Order",
            "",
            "",
            "Depths by Order",
            "",
            "",
            "TVU by Order",
            "",
            "THU by Order",
        ),
        vertical_spacing=0.045,
        horizontal_spacing=0.05,
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19, 0.19, 0.19],
        column_widths=[0.6, 0.4],
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

    fig: go.Figure = create_metadata_figure()

    df: pd.DataFrame = (
        pd.DataFrame(
            [{k: v for k, v in metadata.items() if k != "IHO Order Statistic"}]
        )
        .transpose()
        .reset_index()
    )
    df.columns = ["Metadata", "Value"]

    fig.add_trace(create_table_data(df, ["Metadata", "Value"]), row=1, col=1)

    statistic: dict[OrderEnum, dict[str, float | int]] = {}
    for key, value in metadata["IHO Order Statistic"].items():
        statistic[key] = value

        if value["Sounding Within Order (%)"] == 100:
            break

    fig.add_trace(plot_iho_order_statistic_bar(statistic), row=2, col=1)

    iho_order_fig: go.Figure = create_table_iho_order_statistics(statistic)
    for i, trace in enumerate(iho_order_fig.data, start=1):
        fig.add_trace(trace, row=i, col=2)

    def add_traces_to_figure(figure: go.Figure, row: int, col: int) -> None:
        for trace_ in figure.data:
            fig.add_trace(trace_, row=row, col=col)

    thu_fig: go.Figure = plot_thu_statistics(statistic)
    add_traces_to_figure(thu_fig, row=7, col=1)

    tvu_fig: go.Figure = plot_tvu_statistics(statistic)
    add_traces_to_figure(tvu_fig, row=6, col=1)

    depth_fig: go.Figure = plot_depth_statistics(statistic)
    add_traces_to_figure(depth_fig, row=4, col=1)

    update_layout(
        fig=fig,
        title=title,
        cell_color=CELL_COLOR,
        annotations=create_annotations(fig["layout"]["annotations"]),
        legend=create_legend(),
    )

    if show_plot:
        fig.show()
    if output_path:
        fig.write_html(output_path)
