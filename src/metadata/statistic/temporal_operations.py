"""
Opérations temporelles sur les GeoDataFrames.

Ce module gère la manipulation des colonnes temporelles : conversion,
indexation, calcul de deltatime et extraction de dates.
"""

import geopandas as gpd
import pandas as pd


def set_datetime_index(
    gdf: gpd.GeoDataFrame, time_col: str = "Time_UTC"
) -> gpd.GeoDataFrame:
    """
    Convertit la colonne temporelle en DatetimeIndex UTC et trie.

    :param gdf: GeoDataFrame source.
    :type gdf: gpd.GeoDataFrame
    :param time_col: Nom de la colonne temporelle.
    :type time_col: str
    :return: GeoDataFrame avec DatetimeIndex UTC trié en ordre croissant.
    :rtype: gpd.GeoDataFrame
    :raises KeyError: Si la colonne time_col est absente.
    """
    if time_col not in gdf.columns:
        raise KeyError(f"Colonne '{time_col}' introuvable dans le GeoDataFrame.")

    gdf = gdf.copy()
    gdf[time_col] = pd.to_datetime(gdf[time_col], utc=True)
    gdf = gdf.set_index(time_col).sort_index()

    return gdf


def add_deltatime_column(
    gdf: gpd.GeoDataFrame, col: str = "deltatime"
) -> gpd.GeoDataFrame:
    """
    Ajoute une colonne deltatime (Timedelta) entre points consécutifs.

    Le premier point reçoit NaT (Not a Time).

    :param gdf: GeoDataFrame indexé par un DatetimeIndex trié.
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne à créer.
    :type col: str
    :return: GeoDataFrame enrichi de la colonne deltatime.
    :rtype: gpd.GeoDataFrame
    """
    gdf = gdf.copy()
    gdf[col] = gdf.index.to_series().diff()

    return gdf


def extract_date_column(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ajoute une colonne 'date' (YYYY-MM-DD) extraite de l'index DatetimeIndex.

    :param gdf: GeoDataFrame avec un DatetimeIndex UTC.
    :type gdf: gpd.GeoDataFrame
    :return: GeoDataFrame enrichi de la colonne 'date'.
    :rtype: gpd.GeoDataFrame
    """
    gdf = gdf.copy()
    dt_index = pd.DatetimeIndex(gdf.index)
    gdf["date"] = dt_index.date

    return gdf
