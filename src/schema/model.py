"""
Module qui contient les schémas des dataframes.

Ce module contient les schémas des dataframes des DataLoggers, des stations, des séries temporelles et des zones de marées.
"""

import functools
from typing import Optional, Callable, Type

import geopandas as gpd
import pandas as pd
import pandera as pa
from loguru import logger
from pandas import DataFrame
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries

LOGGER = logger.bind(name="CSB-Pipeline.Schema")


class DataLoggerSchema(pa.DataFrameModel):
    """
    Schéma des données des DataLoggers.
    """

    Longitude_WGS84: Series[pd.Float64Dtype()]
    Latitude_WGS84: Series[pd.Float64Dtype()]
    Depth_meter: Series[pd.Float64Dtype()]
    Time_UTC: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    geometry: GeoSeries


class DataLoggerWithTideZoneSchema(DataLoggerSchema):
    """
    Schéma des données des DataLoggers avec les zones de marées.
    """

    Tide_zone_id: Series[str]


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


class TideZoneProtocolSchema(pa.DataFrameModel):
    """
    Schéma des protocoles des zones de marées.
    """

    id: Series[str]


class TideZoneSchema(TideZoneProtocolSchema):
    """
    Schéma des zones de marées.
    """

    code: Series[str]
    name: Series[str]
    time_series: Series[list]
    is_tidal: Series[object] = pa.Field(nullable=True)
    geometry: GeoSeries


def validate_schema(
    df: gpd.GeoDataFrame | DataFrame, schema: Type[pa.DataFrameModel]
) -> None:
    """
    Valide le schéma des stations.

    :param df: Les stations.
    :type df: gpd.GeoDataFrame | DataFrame
    :param schema: Le schéma.
    :type schema: Type[pa.DataFrameModel]
    """
    try:
        LOGGER.debug(f"Validation du schéma {schema}.")
        schema.validate(df)

    except pa.errors.SchemaError as error:
        LOGGER.error(f"Erreur de validation du schéma {schema} : {error}.")
        LOGGER.error(f"Attributs attendus : {schema.__annotations__}")

        raise error


def validate_schemas(
    return_schema: Optional[Type[pa.DataFrameModel]] = None,
    **schemas: Type[pa.DataFrameModel],
) -> Callable:
    """
    Valide les schémas des dataframes.

    :param return_schema: Le schéma de retour.
    :type return_schema: Optional[Type[pa.DataFrameModel]]
    :param schemas: Les schémas.
    :type schemas: : Type[pa.DataFrameModel]]
    :return: La fonction décorée.
    :rtype: Callable
    """

    def decorator_validate(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper_validate(*args, **kwargs):
            # Valider les arguments d'entrée
            for arg_name, arg_schema in schemas.items():
                if arg_name in kwargs:
                    validate_schema(kwargs[arg_name], arg_schema)
                else:
                    raise ValueError(
                        f"Paramètre '{arg_name}' non trouvé dans les kwargs."
                    )

            # Appeler la fonction originale
            result = func(*args, **kwargs)

            # Valider le résultat de la fonction
            if return_schema is not None:
                validate_schema(result, return_schema)

            return result

        return wrapper_validate

    return decorator_validate
