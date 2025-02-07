"""
Module pour la visualisation des métadonnées des levés hydrographiques.

Ce module contient les fonctions pour afficher les métadonnées des levés hydrographiques.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_metadata_plotly_table(df: pd.DataFrame) -> go.Table:
    return go.Table(
        columnwidth=[1, 3],  # Ajuster les largeurs des colonnes
        header=dict(
            values=list(df.columns),
            fill_color="rgba(205,92,92, 0.65)",
            align="left",
            font=dict(size=14, weight="bold"),
        ),
        cells=dict(
            values=[df[col] for col in df.columns],
            fill_color="lavender",
            align="left",
        ),
    )


def plot_iho_order_statistic_bar(iho_order_statistic: dict) -> go.Bar:
    # Extraire les valeurs count_pourcentage de chaque ordre
    labels, values, colors = [], [], []

    # Définir une liste de couleurs
    color_palette = [
        "rgba(205,92,92, 0.05)",
        "rgba(205,92,92, 0.2)",
        "rgba(205,92,92, 0.35)",
        "rgba(205,92,92, 0.5)",
        "rgba(205,92,92, 0.75)",
        "rgba(205,92,92, 1.0)",
    ]
    for index, (order, stats) in enumerate(iho_order_statistic.items(), start=0):
        labels.append(order)

        value = stats["Sounding Within Order (%)"]
        values.append(value)

        colors.append("rgba(205,92,92, 1.0)" if value == 100 else color_palette[index])

    # Créer un graphique à bandes verticales
    return go.Bar(
        x=labels, y=values, text=values, textposition="auto", marker=dict(color=colors)
    )


def create_order_table(order_name: str, stats: dict) -> go.Table:
    df = pd.DataFrame([stats]).transpose().reset_index()
    df.columns = ["Métadonnée", "Valeur"]

    return go.Table(
        header=dict(
            values=[order_name, "Valeur"],
            fill_color="rgba(205,92,92, 0.65)",
            align="left",
            font=dict(size=14, weight="bold"),
        ),
        cells=dict(
            values=[df[col] for col in df.columns],
            fill_color="lavender",
            align="left",
        ),
    )


def plot_iho_order_statistics(iho_order_statistic: dict) -> go.Figure:
    num_orders = len(iho_order_statistic)

    fig = make_subplots(
        rows=num_orders,
        cols=1,
        subplot_titles=[order for order in iho_order_statistic.keys()],
        vertical_spacing=0.0,
        specs=[[{"type": "domain"}] for _ in range(len(iho_order_statistic))],
    )

    for i, (order, stats) in enumerate(iho_order_statistic.items(), start=1):
        if stats is not None:
            fig.add_trace(create_order_table(order, stats), row=i, col=1)

    return fig


def plot_metadata(metadata: dict, output_path: Path) -> None:
    filtered_data = {
        key: value for key, value in metadata.items() if key != "IHO Order Statistic"
    }

    # Créer un DataFrame à partir des données filtrées
    df = pd.DataFrame([filtered_data]).transpose().reset_index()
    df.columns = ["Métadonnée", "Valeur"]

    # Créer une figure avec deux sous-graphiques
    fig = make_subplots(
        rows=4,
        cols=3,
        specs=[
            [{"type": "domain", "colspan": 3}, None, None],
            [{"type": "xy", "rowspan": 2}, {"type": "domain"}, {"type": "domain"}],
            [None, {"type": "domain"}, {"type": "domain"}],
            [None, {"type": "domain"}, {"type": "domain"}],
        ],
        subplot_titles=(
            "Tableau des métadonnées",
            "Pourcentage de sondes dans l'ordre de levé",
            "Statistiques des ordre de levé",
        ),
        vertical_spacing=0.03,
    )

    # Ajouter le tableau des métadonnées à la première sous-figure
    fig.add_trace(create_metadata_plotly_table(df), row=1, col=1)

    # Ajouter le graphique en pointe de tarte à la deuxième sous-figure
    fig.add_trace(
        plot_iho_order_statistic_bar(metadata["IHO Order Statistic"]), row=2, col=1
    )

    # Ajouter les tables des ordres IHO à la troisième sous-figure
    iho_order_fig = plot_iho_order_statistics(metadata["IHO Order Statistic"])

    row, col = 2, 2
    for i, trace in enumerate(iho_order_fig.data):
        fig.add_trace(trace, row=row, col=col)
        col = 3 if i % 2 == 0 else 2
        row += i % 2

    # Mettre à jour la mise en page de la figure
    fig.update_layout(
        height=1550,
        showlegend=False,
        title=dict(
            text="Information sur le levé",
            font=dict(size=24, weight="bold"),
            x=0.5,
            y=0.98,
            xanchor="center",
        ),
        xaxis_title=dict(text="Ordre de levé", font=dict(weight="bold")),
        yaxis_title=dict(
            text="Pourcentage de sondage dans l'ordre (%)", font=dict(weight="bold")
        ),
        template="plotly",
    )
    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(size=20, weight="bold")

    # Afficher la figure
    fig.show()
    fig.write_html(output_path)
