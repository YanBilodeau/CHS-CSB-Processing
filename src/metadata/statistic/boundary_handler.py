"""
Gestion des frontières de journée UTC et des distances physiquement impossibles.

Ce module neutralise les trajets retour au port en mettant NaN/NaT
aux premiers points de chaque nouvelle journée UTC, et filtre les distances
implausibles causées par l'entrelacement de données multi-capteurs.
"""

import geopandas as gpd
import pandas as pd

MAX_SPEED_M_S: float = 20.0
"""Vitesse maximale plausible pour un navire de levé : ~40 nœuds ≈ 20 m/s."""


def detect_day_boundaries(gdf: gpd.GeoDataFrame) -> pd.Series:
    """
    Détecte les frontières de journée UTC dans un GeoDataFrame.

    :param gdf: GeoDataFrame avec un DatetimeIndex UTC.
    :type gdf: gpd.GeoDataFrame
    :return: Série booléenne, True au premier point de chaque journée.
    :rtype: pd.Series
    """
    dt_index = pd.DatetimeIndex(gdf.index)
    dates = pd.Series(dt_index.date, index=gdf.index)
    day_change = dates != dates.shift(1)

    return day_change


def reset_day_boundaries(
    gdf: gpd.GeoDataFrame,
    distance_col: str = "distance_m",
    deltatime_col: str = "deltatime",
) -> gpd.GeoDataFrame:
    """
    Neutralise les trajets retour au port aux frontières de journée UTC.

    Pour le premier point de chaque nouvelle journée :
      - met distance_col à NaN  → le trajet retour n'est pas du sondage
      - met deltatime_col à NaT → garantit conservation par filtres

    Doit être appelé après add_distance_column() et add_deltatime_column().

    :param gdf: GeoDataFrame avec DatetimeIndex UTC, distance et deltatime.
    :type gdf: gpd.GeoDataFrame
    :param distance_col: Nom de la colonne distance (mètres).
    :type distance_col: str
    :param deltatime_col: Nom de la colonne deltatime.
    :type deltatime_col: str
    :return: GeoDataFrame avec NaN/NaT aux frontières de journée.
    :rtype: gpd.GeoDataFrame
    :raises KeyError: Si l'une des colonnes est absente.
    """
    for col in (distance_col, deltatime_col):
        if col not in gdf.columns:
            raise KeyError(
                f"Colonne '{col}' introuvable. "
                f"Appelez d'abord add_distance_column() et add_deltatime_column()."
            )

    gdf = gdf.copy()
    day_change = detect_day_boundaries(gdf)

    gdf.loc[day_change, distance_col] = float("nan")
    gdf.loc[day_change, deltatime_col] = pd.NaT

    return gdf


def reset_implausible_distances(
    gdf: gpd.GeoDataFrame,
    distance_col: str = "distance_m",
    deltatime_col: str = "deltatime",
    max_speed_m_s: float = MAX_SPEED_M_S,
) -> gpd.GeoDataFrame:
    """
    Met à NaN les distances physiquement impossibles.

    Deux cas sont traités :

    - **Deltatime = 0 s** : deux points distincts au même instant (capteurs
      simultanés). La distance inter-capteurs est sans relation avec le
      déplacement réel du navire.
    - **Vitesse implicite > max_speed_m_s** : saut entre capteurs consécutifs
      après entrelacement temporel des séries de plusieurs unités d'acquisition
      (ex. deux HydroBlock opérant en parallèle sur le même navire).

    Doit être appelé après add_distance_column() et add_deltatime_column().

    :param gdf: GeoDataFrame avec DatetimeIndex UTC, distance_col et deltatime_col.
    :type gdf: gpd.GeoDataFrame
    :param distance_col: Nom de la colonne distance (mètres).
    :type distance_col: str
    :param deltatime_col: Nom de la colonne deltatime.
    :type deltatime_col: str
    :param max_speed_m_s: Vitesse maximale plausible en m/s (défaut : 5 m/s ≈ 10 nœuds).
    :type max_speed_m_s: float
    :return: GeoDataFrame avec NaN pour les distances implausibles.
    :rtype: gpd.GeoDataFrame
    :raises KeyError: Si l'une des colonnes est absente.
    """
    for col in (distance_col, deltatime_col):
        if col not in gdf.columns:
            raise KeyError(
                f"Colonne '{col}' introuvable. "
                f"Appelez d'abord add_distance_column() et add_deltatime_column()."
            )

    gdf = gdf.copy()
    dt_s = gdf[deltatime_col].dt.total_seconds()  # NaT → NaN

    zero_dt_mask = dt_s == 0
    speed_mask = (gdf[distance_col] / dt_s.replace(0, float("nan"))) > max_speed_m_s
    mask = zero_dt_mask | speed_mask

    gdf.loc[mask, distance_col] = float("nan")

    return gdf
