"""
Module pour l'exportation et la visualisation des données de niveaux d'eau.

Ce module contient les fonctions pour exporter les données de niveaux d'eau
des stations de marée et créer des visualisations.
"""

from pathlib import Path
from typing import Collection, Sequence

import pandas as pd
import geopandas as gpd
from loguru import logger

from . import voronoi, plot
import schema
import schema.model_ids as schema_ids
import export


LOGGER = logger.bind(name="CSB-Processing.Tide.WaterLevelExport")


def get_station_title(gdf_voronoi: gpd.GeoDataFrame, station_id: str) -> str:
    """
    Récupère le titre de la station.

    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema]
    :param station_id: Identifiant de la station.
    :type station_id: str
    :return: Titre de la station.
    :rtype: str
    """
    return (
        f"{voronoi.get_name_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)} "
        f"({voronoi.get_code_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)})"
    )


def export_water_level_dataframe(
    station_title: str, wl_dataframe: pd.DataFrame, export_tide_path: Path
) -> None:
    """
    Exporte les données de niveaux d'eau pour une station dans un fichier CSV.

    :param station_title: Titre de la station.
    :type station_title: str
    :param wl_dataframe: DataFrame contenant les données de niveaux d'eau.
    :type wl_dataframe: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers CSV.
    :type export_tide_path: Path
    """
    output_path: Path = (
        export_tide_path / f"{station_title} "
        f"({wl_dataframe.attrs.get(schema_ids.START_TIME).strftime('%Y-%m-%d %H-%M-%S')} - "
        f"{wl_dataframe.attrs.get(schema_ids.END_TIME).strftime('%Y-%m-%d %H-%M-%S')}).csv"
    )

    # Export the water level data to a CSV file
    LOGGER.info(f"Enregistrement des données de niveaux d'eau : {output_path}.")
    export.export_dataframe_to_csv(
        dataframe=wl_dataframe,
        output_path=output_path,
    )


def export_station_water_levels(
    wl_combineds: dict[str, pd.DataFrame],
    gdf_voronoi: gpd.GeoDataFrame,
    export_tide_path: Path,
) -> None:
    """
    Exporte les données de niveaux d'eau pour chaque station dans des fichiers CSV.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: dict[str, pd.DataFrame]
    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers CSV.
    :type export_tide_path: Path
    """
    for station_id, wl_dataframe in wl_combineds.items():
        export_water_level_dataframe(
            station_title=get_station_title(
                gdf_voronoi=gdf_voronoi, station_id=station_id
            ),
            wl_dataframe=wl_dataframe,
            export_tide_path=export_tide_path,
        )


def export_plot_water_level_data(
    wl_combineds: Collection[pd.DataFrame],
    station_titles: Sequence[str],
    export_path: Path,
) -> None:
    """
    Trace les données de niveaux d'eau pour chaque station et les enregistre dans un fichier HTML.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: Collection[pd.DataFrame]
    :param station_titles: Liste des titres des stations.
    :type station_titles: Sequence[str]
    :param export_path: Chemin du répertoire d'exportation des fichiers HTML.
    :type export_path: Path
    """
    LOGGER.info(
        f"Enregistrement des graphiques des données de niveaux d'eau {station_titles}: {export_path}."
    )

    plot.plot_time_series_dataframe(
        dataframes=wl_combineds,
        titles=station_titles,
        show_plot=False,  # Afficher le graphique dans un navigateur web
        output_path=export_path,  # Exporter le graphique dans un fichier HTML
    )


def plot_water_levels(
    wl_combineds_dict: dict[str, list[pd.DataFrame]],
    gdf_voronoi: gpd.GeoDataFrame,
    export_tide_path: Path,
) -> None:
    """
    Trace les données de niveaux d'eau pour chaque station et les enregistre dans un fichier HTML.

    :param wl_combineds_dict: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds_dict: dict[str, list[pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]]
    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema]
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers HTML.
    :type export_tide_path: Path
    """
    wl_combineds_list = [
        pd.concat(value)
        .drop_duplicates(subset=[schema_ids.EVENT_DATE])
        .reset_index(drop=True)
        .sort_values(by=schema_ids.EVENT_DATE)
        for value in wl_combineds_dict.values()
    ]

    station_titles_list: list[str] = [
        get_station_title(
            gdf_voronoi=gdf_voronoi,
            station_id=key,
        )
        for key in wl_combineds_dict.keys()
    ]

    export_plot_water_level_data(
        wl_combineds=wl_combineds_list,
        station_titles=station_titles_list,
        export_path=export_tide_path / "WaterLevel.html",
    )
