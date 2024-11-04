from pathlib import Path
from typing import Optional, Collection, Sequence

import pandas as pd
import plotly.graph_objects as go
from loguru import logger

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Plot")


def create_scatter_traces(dataframe: pd.DataFrame) -> list[go.Scatter]:
    """
    Crée une liste de traces de type Scatter pour chaque série temporelle.

    :param dataframe: (pd.DataFrame) Le DataFrame de la série temporelle.
    :return: (list[go.Scatter]) La liste des traces Scatter.
    """
    return [
        go.Scatter(
            x=dataframe[dataframe["time_serie_code"] == code]["event_date"],
            y=dataframe[dataframe["time_serie_code"] == code]["value"],
            mode="markers",
            marker=dict(size=6),
            name=f"{code}",
            text=dataframe[dataframe["time_serie_code"] == code]["time_serie_code"],
            showlegend=True,
        )
        for code in dataframe["time_serie_code"].unique()
    ]


def add_traces(fig: go.Figure, dataframes: Collection[pd.DataFrame]) -> None:
    """
    Ajoute les traces Scatter pour chaque série temporelle dans la figure.

    :param fig: (go.Figure) La figure Plotly.
    :param dataframes: (Collection[pd.DataFrame]) La collection de DataFrames.
    """
    for index, dataframe in enumerate(dataframes):
        for trace in create_scatter_traces(dataframe=dataframe):
            fig.add_trace(trace)


def create_annotations() -> list[dict]:
    """
    Crée une liste d'annotations pour le graphique.

    :return: (list[dict]) La liste des annotations.
    """
    return [
        dict(
            text="Station :",
            x=1.01,
            y=1,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16, weight="bold"),
            xanchor="left",
        ),
        dict(
            text="Niveau d'eau selon le temps",
            x=0.029,
            y=1.035,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16, color="black"),
        ),
    ]


def create_buttons(
    fig: go.Figure,
    dataframes: Collection[pd.DataFrame],
    titles: Collection[str],
    x_label: str,
    y_label: str,
) -> list[dict]:
    """
    Crée une liste de boutons pour le menu déroulant.

    :param fig: (go.Figure) La figure Plotly.
    :param dataframes: (Collection[pd.DataFrame]) La collection de DataFrames.
    :param titles: (Collection[str]) Les titres des graphiques.
    :param x_label: (str) Le titre de l'axe des x.
    :param y_label: (str) Le titre de l'axe des y.
    :return: (list[dict]) La liste des boutons.
    """
    buttons = []

    cumulative_counts = [0] + [len(df["time_serie_code"].unique()) for df in dataframes]
    cumulative_counts = [
        sum(cumulative_counts[: i + 1]) for i in range(len(cumulative_counts))
    ]

    for index, title in enumerate(titles):
        visibility = [False] * len(fig.data)
        start_idx = cumulative_counts[index]
        end_idx = cumulative_counts[index + 1]

        for j in range(start_idx, end_idx):
            visibility[j] = True

        buttons.append(
            dict(
                label=title,
                method="update",
                args=[
                    {"visible": visibility},
                    {
                        "title": title,
                        "xaxis": {"autorange": True, "title": x_label},
                        "yaxis": {"autorange": True, "title": y_label},
                        "annotations": create_annotations(),
                    },
                ],
            )
        )

    return buttons


def set_initial_visibility(
    fig: go.Figure, dataframes: Collection[pd.DataFrame]
) -> list[bool]:
    """
    Définit la visibilité initiale des traces pour chaque série temporelle.

    :param fig: (go.Figure) La figure Plotly.
    :param dataframes: (Collection[pd.DataFrame]) La collection de DataFrames.
    :return: (list[bool]) La liste de visibilité initiale.
    """
    initial_visibility = [False] * len(fig.data)
    for j in range(len(dataframes[0]["time_serie_code"].unique())):
        initial_visibility[j] = True

    return initial_visibility


def update_layout(
    fig: go.Figure,
    buttons: list[dict],
    x_label: str,
    y_label: str,
    title: str,
    template: str,
) -> None:
    """
    Met à jour la mise en page de la figure.

    :param fig: (go.Figure) La figure Plotly.
    :param buttons: (list[dict]) La liste des boutons.
    :param x_label: (str) Le titre de l'axe des x.
    :param y_label: (str) Le titre de l'axe des y.
    :param title: (str) Le titre du graphique.
    :param template: (str) Le template du graphique.
    """
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                x=1.01,
                y=0.975,
                xanchor="left",
            )
        ],
        annotations=create_annotations(),
        title=dict(
            text=title,
            font=dict(size=24, weight="bold"),
        ),
        xaxis_title=x_label,
        yaxis_title=y_label,
        template=template,
        legend=dict(
            title=dict(text="Série temporelle", font=dict(weight="bold", size=16)),
            x=1.01,
            y=0.935,
        ),
    )


def plot_time_series_dataframe(
    dataframes: Collection[pd.DataFrame],
    titles: Sequence[str],
    x_label: str = "Date de l'événement",
    y_label: str = "Niveu d'eau (m)",
    template: str = "plotly",
    output_path: Optional[Path] = None,
    show_plot: bool = False,
) -> None:
    """
    Fonction qui affiche un graphique de la série temporelle avec un menu déroulant.

    :param dataframes: (Collection[pd.DataFrame]) Le DataFrame de la série temporelle.
    :param titles: (Sequence[str]) Le titre du graphique.
    :param x_label: (str) Le titre de l'axe des x.
    :param y_label: (str) Le titre de l'axe des y.
    :param output_path: (Path) Le chemin du fichier de sortie.
    :param show_plot: (bool) Afficher le graphique.
    :param template: (str) Le template du graphique.
    """
    LOGGER.debug(f"Affichage des graphiques des niveaux d'eau pour : {titles}.")

    if len(dataframes) != len(titles):
        raise ValueError("Le nombre de DataFrames doit être égal au nombre de titres.")

    fig = go.Figure()

    add_traces(fig=fig, dataframes=dataframes)
    buttons = create_buttons(
        fig=fig, dataframes=dataframes, titles=titles, x_label=x_label, y_label=y_label
    )
    initial_visibility: list[bool] = set_initial_visibility(
        fig=fig, dataframes=dataframes
    )
    update_layout(
        fig=fig,
        buttons=buttons,
        x_label=x_label,
        y_label=y_label,
        title=titles[0],
        template=template,
    )

    for i, visible in enumerate(initial_visibility):
        fig.data[i].visible = visible

    if show_plot:
        fig.show()

    if output_path:
        fig.write_html(output_path)
