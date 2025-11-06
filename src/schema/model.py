"""
Module qui contient les schémas des dataframes.

Ce module contient les schémas des dataframes des DataLoggers, des stations, des séries temporelles et des zones de marées.
"""

from dataclasses import dataclass, field
from enum import StrEnum
import functools
from typing import Optional, Callable, Type, Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pandera.pandas as pa
from loguru import logger
from pandas import DataFrame
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries

from . import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Schema")


@dataclass
class WaterLevelInfo:
    """
    Classe pour les informations sur les niveaux d'eau.
    """

    water_level_meter: float = np.nan
    """Le niveau d'eau en mètre."""
    time_series: str = None
    """Le code de la série temporelle."""
    id: str = None
    """L'identifiant de la station."""
    name: str = None
    """Le nom de la station."""
    code: str = None
    """Le code de la station."""

    def __str__(self) -> str:
        water_level: str = (
            f"{self.water_level_meter} m"
            if not np.isnan(self.water_level_meter)
            else None
        )

        return (
            f"WaterLevelInfo("
            f"{self.time_series if water_level else '<NA>'} - "
            f"{self.id if water_level else '<NA>'} - "
            f"{self.name if water_level else '<NA>'} - "
            f"{self.code if water_level else '<NA>'})"
        )


class Status(StrEnum):
    """
    Enum pour les statuts de filtrage des données.
    """

    ACCEPTED = "accepted"
    REJECTED_BY_SPEED_FILTER = "rejected by speed filter"
    REJECTED_BY_LATITUDE_FILTER = "rejected by latitude filter"
    REJECTED_BY_LONGITUDE_FILTER = "rejected by longitude filter"
    REJECTED_BY_TIME_FILTER = "rejected by time filter"
    REJECTED_BY_DEPTH_FILTER = "rejected by depth filter"


@dataclass
class OutlierInfo:
    tags: list[Status] = field(default_factory=list)

    def __str__(self) -> str:
        return " | ".join(map(str, self.tags)) if self.tags else ""


class DataLoggerSchema(pa.DataFrameModel):
    """
    Schéma des données des DataLoggers.
    """

    Latitude_WGS84: Series[pd.Float64Dtype()]
    Longitude_WGS84: Series[pd.Float64Dtype()]
    Time_UTC: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    Depth_raw_meter: Series[pd.Float64Dtype()]
    Depth_processed_meter: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    Speed_kn: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    Water_level_meter: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    Water_level_info: Series[object] = pa.Field(nullable=True)
    Uncertainty_station_meter: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    SSP_uncertainty_percent: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    Uncertainty: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    THU: Series[pd.Float64Dtype()] = pa.Field(nullable=True)
    IHO_order: Series[str] = pa.Field(nullable=True)
    Outlier: Series[object] = pa.Field(nullable=True)
    geometry: GeoSeries

    class Config:
        coerce = True


class DataLoggerWithTideZoneSchema(DataLoggerSchema):
    """
    Schéma des données des DataLoggers avec les zones de marées.
    """

    Time_serie: Series[str] = pa.Field(nullable=True)
    Tide_zone_id: Series[str] = pa.Field(nullable=True)
    Tide_zone_code: Series[str] = pa.Field(nullable=True)
    Tide_zone_name: Series[str] = pa.Field(nullable=True)

    class Config:
        coerce = True


class DataLoggerWithVoronoiSchema(DataLoggerSchema):
    """
    Schéma des données des DataLoggers avec les zones de Voronoi.
    """

    id: Series[str] = pa.Field(nullable=True)
    code: Series[str] = pa.Field(nullable=True)
    name: Series[str] = pa.Field(nullable=True)
    Time_serie: Series[object] = pa.Field(nullable=True)


class WaterLevelSerieDataSchema(pa.DataFrameModel):
    """
    Schéma des séries temporelles.
    """

    event_date: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    value: Series[pd.Float64Dtype()]
    time_serie_code: Series[str]

    class Config:
        coerce = True


class WaterLevelSerieDataWithMetaDataSchema(WaterLevelSerieDataSchema):
    """
    Schéma des séries temporelles avec les métadonnées.
    """

    @classmethod
    def validate(cls, df: DataFrame, *args: Any, **kwargs: Any) -> DataFrame:
        """
        Valide les métadonnées des séries temporelles en surchargeant la méthode de validation par défaut.

        :param df: Les séries temporelles.
        :type df: DataFrame
        :param args: Les arguments.
        :type args: Any
        :param kwargs: Les paramètres.
        :type kwargs: Any
        :return: Les séries temporelles validées.
        :rtype: DataFrame
        """
        required_attrs = [
            schema_ids.NAME_METADATA,
            schema_ids.STATION_ID,
            schema_ids.START_TIME,
            schema_ids.END_TIME,
            schema_ids.STATION_POSITION,
        ]
        validated_df = super().validate(df, *args, **kwargs)

        missing_attrs = [attr for attr in required_attrs if attr not in validated_df.attrs]  # type: ignore
        if missing_attrs:
            raise ValueError(
                f"Attributs manquants dans les métadonnées de {cls.__name__} : {', '.join(missing_attrs)}"
            )

        LOGGER.debug(
            f"Métadonnées des séries temporelles de {cls.__name__} validées avec succès."
        )

        return validated_df  # type: ignore


class StationsSchema(pa.DataFrameModel):
    """
    Schéma des stations.
    """

    id: Series[str]
    code: Series[str]
    name: Series[str]
    time_series: Series[object]
    is_tidal: Series[object] = pa.Field(
        nullable=True
    )  # On utilise object pour accepter les booléens et les None
    geometry: GeoSeries

    class Config:
        coerce = True


class TideZoneProtocolSchema(pa.DataFrameModel):
    """
    Schéma des protocoles des zones de marées.
    """

    id: Series[str]
    time_series: Series[object]

    class Config:
        coerce = True


class TideZoneStationSchema(TideZoneProtocolSchema):
    """
    Schéma des zones de marées extraite des stations.
    """

    code: Series[str]
    name: Series[str]
    is_tidal: Series[object] = pa.Field(
        nullable=True
    )  # On utilise object pour accepter les booléens et les None
    geometry: GeoSeries
    station_position: GeoSeries


class TideZoneInfoSchema(pa.DataFrameModel):
    """
    Schéma des informations des zones de marées.
    """

    Tide_zone_id: Series[str]
    time_series: Series[object]
    min_time: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    max_time: Series[pd.DatetimeTZDtype("ns", tz="UTC")]


def validate_schema(
    data: gpd.GeoDataFrame | DataFrame, schema: Type[pa.DataFrameModel]
) -> None:
    """
    Valide le schéma des stations.

    :param data: Les stations.
    :type data: gpd.GeoDataFrame | DataFrame
    :param schema: Le schéma.
    :type schema: Type[pa.DataFrameModel]
    """
    try:
        LOGGER.debug(f"Validation du schéma {schema}.")
        schema.validate(data)

    except pa.errors.SchemaError as error:
        LOGGER.error(f"Erreur de validation du schéma {schema} : {error}.")
        LOGGER.error(
            f"Attributs attendus dans le schéma {schema} : {schema.__annotations__}"
        )

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
            if return_schema is not None and not result.empty:
                validate_schema(result, return_schema)

            return result

        return wrapper_validate

    return decorator_validate
