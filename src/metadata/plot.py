"""
Module pour la visualisation des métadonnées des levés hydrographiques.

Ce module contient les fonctions pour afficher les métadonnées des levés hydrographiques.
"""

from pathlib import Path
from typing import Optional

from loguru import logger
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots

from .order.order_models import OrderEnum
from .order.s44_computation import ORDERS_CONFIG, compute_threshold
from schema import model_ids as schema_ids


LOGGER = logger.bind(name="CSB-Processing.Metadata.Plot")


COLOR_PALETTE: list[str] = [
    "rgba(205,92,92, 0.2)",
    "rgba(205,92,92, 0.3)",
    "rgba(205,92,92, 0.45)",
    "rgba(205,92,92, 0.6)",
    "rgba(205,92,92, 0.8)",
    "rgba(205,92,92, 1.0)",
]

HEADER_COLOR: str = "rgba(205,92,92, 1.0)"

CELL_COLOR: str = "lavender"

ORDER_LABELS: dict[int, str] = {
    0: "Exclusive Order",
    1: "Special Order",
    2: "Order 1a",
    3: "Order 2",
}

ORDER_LINE_COLORS: dict[int, str] = {
    0: "rgba(220,220,220,0.85)",  # Gris très pâle
    1: "rgba(160,160,160,0.85)",  # Gris moyen-pâle
    2: "rgba(100,100,100,0.85)",  # Gris moyen-foncé
    3: "rgba(40,40,40,0.85)",  # Gris très foncé
}


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
        hovertemplate="<b>%{x}</b><br>Percentage: %{y:.2f}%<extra></extra>",
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


def format_order_label(value: object) -> str:
    """
    Formate une valeur d'ordre en une étiquette lisible.

    :param value: Valeur de l'ordre (int ou None)
    :type value: object
    :return: Étiquette formatée
    :rtype: str
    """
    if value is None:
        return ""

    try:
        iv = int(value)  # type: ignore

    except Exception as e:
        LOGGER.debug(f"Ne peut pas convertir en int: {value} ({e})")

        return str(value)

    return ORDER_LABELS.get(iv, str(iv))


def plot_depth_uncertainty_statistics_trace(
    dataframe: pd.DataFrame,
    nbins_x: int,
    nbins_y: int,
    uncertainty_band=schema_ids.UNCERTAINTY,
    depth_band=schema_ids.DEPTH_PROCESSED_METER,
    order_band=schema_ids.IHO_ORDER,
) -> go.Heatmap:
    """
    Génère une trace heatmap 2D pour integration dans une figure existante.

    :param dataframe: DataFrame contenant les données
    :type dataframe: pd.DataFrame
    :param nbins_x: Nombre de bins en X
    :type nbins_x: int
    :param nbins_y: Nombre de bins en Y
    :type nbins_y: int
    :param uncertainty_band: Nom de la colonne d'incertitude (TVU ou TH
    :type uncertainty_band: str
    :param depth_band: Nom de la colonne de profondeur
    :type depth_band: str
    :param order_band: Nom de la colonne d'ordre S44
    :type order_band: str
    :return: Trace heatmap 2D
    :rtype: go.Heatmap
    """
    clean_data = dataframe[[uncertainty_band, depth_band, order_band]].dropna()
    x_data = clean_data[uncertainty_band].values
    y_data = clean_data[depth_band].values

    counts, x_edges, y_edges = np.histogram2d(x_data, y_data, bins=[nbins_x, nbins_y])
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2

    return go.Heatmap(
        z=counts.T,
        x=x_centers,
        y=y_centers,
        colorscale=[
            [0.0, "white"],
            [0.01, "rgb(245,185,185)"],
            [1.0, "rgb(140,20,20)"],
        ],
        colorbar=dict(title="Nombre de points"),
        hovertemplate=(
            "<b>Uncertainty:</b> %{x:.3f}<br>"
            "<b>Depth:</b> %{y:.2f}<br>"
            "<b>Number of points:</b> %{z}<br>"
            "<extra></extra>"
        ),
        showlegend=False,
        showscale=False,
    )


def create_threshold_line_uncertainty_traces(
    dataframe: pd.DataFrame, nbins_x, nbins_y
) -> list[go.Scatter]:
    """
    Crée une liste de traces Scatter représentant les lignes de seuil TVU=f(depth)
    pour chaque ordre, en utilisant les mêmes formules (a, b) que le calcul de bande.
    Les lignes sont calculées sur les centres des mêmes binnings que la heatmap.

    :param dataframe: DataFrame contenant les données
    :type dataframe: pd.DataFrame
    :param nbins_x: Nombre de bins en X
    :type nbins_x: int
    :param nbins_y: Nombre de bins en Y
    :type nbins_y: int
    :return: Liste de traces Scatter représentant les lignes de seuil TVU=f(depth)
    :rtype: list[go.Scatter]
    """
    clean_data = dataframe[
        [schema_ids.UNCERTAINTY, schema_ids.DEPTH_PROCESSED_METER]
    ].dropna()
    if clean_data.empty:
        return []

    x_data = clean_data[schema_ids.UNCERTAINTY].values
    y_data = clean_data[schema_ids.DEPTH_PROCESSED_METER].values

    # Recréer les mêmes centres que la heatmap pour un overlay parfait
    _, x_edges, y_edges = np.histogram2d(x_data, y_data, bins=[nbins_x, nbins_y])
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2

    valid_mask = np.ones_like(y_centers, dtype=bool)
    traces: list[go.Scatter] = []

    for cfg in ORDERS_CONFIG:
        a = float(cfg["a"])
        b = float(cfg["b"])
        thresholds = compute_threshold(
            valid_depth=y_centers, valid_mask=valid_mask, a=a, b=b
        )

        order: int = int(cfg["order"])
        name = f"{ORDER_LABELS.get(order, f'Order {order}')} Threshold"
        color = ORDER_LINE_COLORS.get(order, "rgba(0,0,0,0.85)")

        traces.append(
            go.Scatter(
                x=thresholds,
                y=y_centers,
                mode="lines",
                name=name,
                line=dict(color=color, width=3, dash="solid"),
                hovertemplate="<b>%{text}</b><br>Uncertainty: %{x:.3f}<br>Depth: %{y:.2f}<extra></extra>",
                text=[name] * thresholds.shape[0],
                showlegend=False,
            )
        )

    return traces


def create_threshold_line_thu_traces(
    dataframe: pd.DataFrame, nbins_x: int, nbins_y: int
) -> list[go.Scatter]:
    """
    Crée une liste de traces Scatter représentant les lignes de seuil THU=f(depth)
    pour chaque ordre, en utilisant pos_func défini dans ORDERS_CONFIG.
    Les lignes sont calculées sur les centres des mêmes binnings que la heatmap THU.

    :param dataframe: DataFrame contenant les données
    :type dataframe: pd.DataFrame
    :param nbins_x: Nombre de bins en X
    :type nbins_x: int
    :param nbins_y: Nombre de bins en Y
    :type nbins_y: int
    :return: Liste de traces Scatter représentant les lignes de seuil THU=f(depth)
    :rtype: list[go.Scatter]
    """
    clean_data = dataframe[[schema_ids.THU, schema_ids.DEPTH_PROCESSED_METER]].dropna()
    if clean_data.empty:
        return []

    x_data = clean_data[schema_ids.THU].values
    y_data = clean_data[schema_ids.DEPTH_PROCESSED_METER].values

    # Même binning que la heatmap THU pour un overlay parfait
    _, x_edges, y_edges = np.histogram2d(x_data, y_data, bins=[nbins_x, nbins_y])
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2

    traces: list[go.Scatter] = []
    for cfg in ORDERS_CONFIG:
        order: int = int(cfg["order"])
        name = f"{ORDER_LABELS.get(order, f'Order {order}')} Threshold"
        color = ORDER_LINE_COLORS.get(order, "rgba(0,0,0,0.85)")

        thresholds = np.vectorize(cfg["pos_func"])(y_centers)

        traces.append(
            go.Scatter(
                x=thresholds,
                y=y_centers,
                mode="lines",
                name=name,
                line=dict(color=color, width=3, dash="solid"),
                hovertemplate="<b>%{text}</b><br>THU: %{x:.3f}<br>Depth: %{y:.2f}<extra></extra>",
                text=[name] * thresholds.shape[0],
                showlegend=True,
            )
        )

    return traces


def add_regression_line_trace(
    dataframe: pd.DataFrame,
    uncertainty_band: str,
    x_range: Optional[tuple[float, float]] = None,
    y_range: Optional[tuple[float, float]] = None,
) -> go.Scatter:
    """
    Compute a linear regression of Uncertainty as a function of Depth and
    return a trace plotting x = a·Depth + b (x=uncertainty, y=depth).
    """
    clean_data = dataframe[
        [uncertainty_band, schema_ids.DEPTH_PROCESSED_METER]
    ].dropna()

    if clean_data.empty or len(clean_data) < 2:
        return go.Scatter(
            x=[], y=[], mode="lines", name="Regression Line", visible=False
        )

    # Auto ranges if not provided
    if x_range is None:
        x_range = (
            float(clean_data[uncertainty_band].min()),
            float(clean_data[uncertainty_band].max()),
        )
    if y_range is None:
        y_range = (
            float(clean_data[schema_ids.DEPTH_PROCESSED_METER].min()),
            float(clean_data[schema_ids.DEPTH_PROCESSED_METER].max()),
        )

    # Fit: Uncertainty = a * Depth + b
    a, b = np.polyfit(
        clean_data[schema_ids.DEPTH_PROCESSED_METER], clean_data[uncertainty_band], 1
    )

    # Generate the line over the visible Y range, then compute X
    y_line = np.linspace(y_range[0], y_range[1], 200)
    x_line = a * y_line + b

    # Keep points within the visible X range
    mask = (x_line >= x_range[0]) & (x_line <= x_range[1])
    x_line_filtered = x_line[mask]
    y_line_filtered = y_line[mask]

    # R² (same as squared correlation in simple linear regression)
    r2 = (
        np.corrcoef(
            clean_data[uncertainty_band], clean_data[schema_ids.DEPTH_PROCESSED_METER]
        )[0, 1]
        ** 2
    )

    return go.Scatter(
        x=x_line_filtered,
        y=y_line_filtered,
        mode="lines",
        name=f"Linear regression (R² = {r2:.3f})",
        line=dict(color="black", width=3, dash="dash"),
        hovertemplate=(
            f"<b>Linear Regression</b>"
            f"<br>Uncertainty = {a:.3f} × Depth + {b:.3f}<br>"
            f"R² = {r2:.3f}<br>"
            "<extra></extra>"
        ),
        showlegend=True,
        visible="legendonly",
    )


def determine_optimal_bins(
    data: np.ndarray, min_bins: int = 10, max_bins: int = 100
) -> int:
    """
    Détermine le nombre optimal de bins pour un histogramme en utilisant la règle de Freedman-Diaconis.

    :param data: Données pour lesquelles déterminer le nombre de bins
    :type data: np.ndarray
    :param min_bins: Nombre minimum de bins
    :type min_bins: int
    :param max_bins: Nombre maximum de bins
    :type max_bins: int
    :return: Nombre optimal de bins
    :rtype: int
    """
    if len(data) < 2:
        return min_bins

    # Freedman-Diaconis rule
    iqr = np.subtract(*np.percentile(data, [75, 25]))
    if iqr == 0:
        bin_width = 3.5 * np.std(data) / (len(data) ** (1 / 3))
    else:
        bin_width = 2 * iqr / (len(data) ** (1 / 3))

    if bin_width == 0:  # Handle case of constant data
        return min_bins

    data_range = np.ptp(data)  # max - min
    bin_count = int(np.ceil(data_range / bin_width))

    # Apply limits
    return max(min(bin_count, max_bins), min_bins)


def plot_depth_uncertainty_with_thresholds(
    fig: go.Figure,
    dataframe: pd.DataFrame,
    row: int,
    col: int,
    uncertainty_band: str,
    x_ref_domain: str,
    y_ref_domain: str,
    threshold_function,
    nbins_x: Optional[int] = None,
    nbins_y: Optional[int] = None,
) -> None:
    """
    Fonction générique pour créer une heatmap depth/uncertainty avec les lignes de seuil
    et mettre à jour le layout du subplot.

    :param fig: Figure Plotly à modifier
    :type fig: go.Figure
    :param dataframe: DataFrame contenant les données
    :type dataframe: pd.DataFrame
    :param row: Numéro de ligne du subplot
    :type row: int
    :param col: Numéro de colonne du subplot
    :type col: int
    :param uncertainty_band: Nom de la colonne d'incertitude (TVU ou THU)
    :type uncertainty_band: str
    :param x_ref_domain: Référence du domaine X pour les formes
    :type x_ref_domain: str
    :param y_ref_domain: Référence du domaine Y pour les formes
    :type y_ref_domain: str
    :param threshold_function: Fonction pour créer les lignes de seuil
    :type threshold_function: Callable
    :param nbins_x: Nombre de bins en X
    :type nbins_x: int
    :param nbins_y: Nombre de bins en Y
    :type nbins_y: int
    """
    clean_data = dataframe[
        [uncertainty_band, schema_ids.DEPTH_PROCESSED_METER]
    ].dropna()

    # Automatically determine bins if not provided
    if nbins_x is None:
        nbins_x = determine_optimal_bins(clean_data[uncertainty_band].values)
    if nbins_y is None:
        nbins_y = determine_optimal_bins(
            clean_data[schema_ids.DEPTH_PROCESSED_METER].values
        )

    LOGGER.debug(
        f"Utilisation de nbins_x={nbins_x}, nbins_y={nbins_y} pour {uncertainty_band}."
    )

    # Créer la heatmap
    heatmap_trace = plot_depth_uncertainty_statistics_trace(
        dataframe,
        nbins_x=nbins_x,
        nbins_y=nbins_y,
        uncertainty_band=uncertainty_band,
    )
    fig.add_trace(heatmap_trace, row=row, col=col)

    # Ajouter la ligne de régression
    regression_trace = add_regression_line_trace(
        dataframe,
        uncertainty_band,
    )
    fig.add_trace(regression_trace, row=row, col=col)

    # Ajouter les lignes de seuil
    threshold_traces = threshold_function(dataframe, nbins_x, nbins_y)
    for line_trace in threshold_traces:
        fig.add_trace(line_trace, row=row, col=col)

    # Mettre à jour les axes et ajouter le fond blanc
    heatmap_x = np.asarray(heatmap_trace.x)
    heatmap_y = np.asarray(heatmap_trace.y)
    if heatmap_x.size > 0 and heatmap_y.size > 0:
        x_min, x_max = float(np.nanmin(heatmap_x)), float(np.nanmax(heatmap_x))
        y_min, y_max = float(np.nanmin(heatmap_y)), float(np.nanmax(heatmap_y))

        # Add buffer to ranges
        buffer_value = 0.25
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_buffer = x_range * buffer_value
        y_buffer = y_range * buffer_value

        fig.update_xaxes(range=[x_min - x_buffer, x_max + x_buffer], row=row, col=col)
        fig.update_yaxes(range=[y_max + y_buffer, y_min - y_buffer], row=row, col=col)

        fig.add_shape(
            type="rect",
            xref=f"{x_ref_domain} domain",
            yref=f"{y_ref_domain} domain",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            fillcolor="white",
            layer="below",
            line=dict(width=0),
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
        xaxis2_title=dict(text="TVU (m)", font=dict(weight="bold")),
        yaxis2_title=dict(
            text="Depth (m)",
            font=dict(weight="bold"),
        ),
        yaxis2=dict(autorange="reversed"),
        xaxis3_title=dict(text="THU (m)", font=dict(weight="bold")),
        yaxis3_title=dict(
            text="Depth (m)",
            font=dict(weight="bold"),
        ),
        yaxis3=dict(autorange="reversed"),
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
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}],
            [None, None],
        ],
        subplot_titles=(
            "Metadata Table",
            "Survey Order Statistics",
            "Soundings in Survey Order",
            "",
            "",
            "Depth and TVU Distribution",
            "",
            "",
            "Depth and THU Distribution",
            "",
            "",
        ),
        vertical_spacing=0.045,
        horizontal_spacing=0.05,
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19, 0.19, 0.19],
        column_widths=[0.6, 0.4],
    )

    return fig


def plot_metadata(
    dataframe: pd.DataFrame,
    metadata: dict,
    title: str,
    output_path: Optional[Path] = None,
    show_plot: bool = False,
    nbins_x: Optional[int] = None,
    nbins_y: Optional[int] = None,
) -> go.Figure:
    """
    Affiche et sauvegarde les métadonnées des levés hydrographiques.

    :param dataframe: DataFrame contenant les données du levé hydrographique.
    :type dataframe: pd.DataFrame
    :param metadata: Dictionnaire contenant les métadonnées du levé hydrographique.
    :type metadata: Dict
    :param title: Titre de la figure.
    :type title: str
    :param output_path: Chemin de sortie pour la figure.
    :type output_path: Optional[Path]
    :param show_plot: Indique si la figure doit être affichée.
    :type show_plot: bool
    :param nbins_x: Nombre de bins en X pour les heatmaps (TVU et THU). Si None, calcul automatique.
    :type nbins_x: Optional[int]
    :param nbins_y: Nombre de bins en Y pour les heatmaps (TVUet THU). Si None, calcul automatique.
    :type nbins_y: Optional[int]
    :return: Figure Plotly contenant les métadonnées.
    :rtype: go.Figure
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

    metadata_table: go.Table = create_table_data(df, ["Metadata", "Value"])
    metadata_fig: go.Figure = go.Figure(data=[metadata_table])
    fig.add_trace(metadata_table, row=1, col=1)

    statistic: dict[OrderEnum, dict[str, float | int]] = {}
    for key, value in metadata["IHO Order Statistic"].items():
        statistic[key] = value

        if value["Sounding Within Order (%)"] == 100:
            break

    fig.add_trace(plot_iho_order_statistic_bar(statistic), row=2, col=1)

    iho_order_fig: go.Figure = create_table_iho_order_statistics(statistic)
    for i, trace in enumerate(iho_order_fig.data, start=1):
        fig.add_trace(trace, row=i, col=2)

    # Plot TVU heatmap avec lignes de seuil
    plot_depth_uncertainty_with_thresholds(
        fig=fig,
        dataframe=dataframe,
        row=4,
        col=1,
        uncertainty_band=schema_ids.UNCERTAINTY,
        x_ref_domain="x2",
        y_ref_domain="y2",
        threshold_function=create_threshold_line_uncertainty_traces,
        nbins_x=nbins_x,
        nbins_y=nbins_y,
    )

    # Plot THU heatmap avec lignes de seuil
    plot_depth_uncertainty_with_thresholds(
        fig=fig,
        dataframe=dataframe,
        row=6,
        col=1,
        uncertainty_band=schema_ids.THU,
        x_ref_domain="x3",
        y_ref_domain="y3",
        threshold_function=create_threshold_line_thu_traces,
        nbins_x=nbins_x,
        nbins_y=nbins_y,
    )

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
        fig.write_html(output_path.with_suffix(".html"))

        try:
            metadata_fig.write_image(
                output_path.with_suffix(".pdf"),
                height=1400,
                width=850,
                scale=2,
            )

        except Exception as e:
            LOGGER.error(f"Erreur lors de la sauvegarde du PDF : {e}")

    return fig
