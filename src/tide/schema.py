"""
Module qui contient les schémas des stations.

Ce module contient les schémas des stations, des séries temporelles et des Voronoïs.
"""

import geopandas as gpd
import pandas as pd
import pandera as pa
from loguru import logger
from pandas import DataFrame
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries


LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Schema")


class StationsSchema(pa.DataFrameModel):
    """
    Schéma des stations.
    """

    id: Series[str]
    code: Series[str]
    name: Series[str]
    time_series: Series[list]
    is_tidal: Series[object] = pa.Field(nullable=True)
    geometry: GeoSeries


class TimeSerieDataSchema(pa.DataFrameModel):
    """
    Schéma des séries temporelles.
    """

    event_date: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    value: Series[pd.Float64Dtype()]
    time_serie_code: Series[str]


class VoronoiSchema(pa.DataFrameModel):
    """
    Schéma des Voronoïs.
    """

    id: Series[str]
    code: Series[str]
    name: Series[str]
    time_series: Series[list]
    is_tidal: Series[object] = pa.Field(nullable=True)
    geometry: GeoSeries


def validate_schema(
    df: gpd.GeoDataFrame | DataFrame, schema: type[pa.DataFrameModel]
) -> None:
    """
    Valide le schéma des stations.

    :param df: Les stations.
    :type df: gpd.GeoDataFrame | DataFrame
    :param schema: Le schéma.
    :type schema: type[pa.DataFrameModel]
    """
    try:
        LOGGER.debug(f"Validation du schéma {schema}.")
        schema.validate(df)

    except pa.errors.SchemaError as error:
        LOGGER.error(f"Erreur de validation du schéma {schema} : {error}.")
        LOGGER.error(f"Attributs attendus : {schema.__annotations__}")

        raise error
