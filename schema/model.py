import geopandas as gpd
import pandas as pd
import pandera as pa
from loguru import logger
from pandas import DataFrame
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Schema")


class DataLoggerSchema(pa.DataFrameModel):
    Longitude_WGS84: Series[pd.Float64Dtype()]
    Latitude_WGS84: Series[pd.Float64Dtype()]
    Depth_meter: Series[pd.Float64Dtype()]
    Time_UTC: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
    geometry: GeoSeries


def validate_schema(
    df: gpd.GeoDataFrame | DataFrame, schema: type[pa.DataFrameModel]
) -> None:
    """
    Valide le schéma des stations.

    :param df: (gpd.GeoDataFrame | DataFrame) Les stations.
    :param schema: (GeoDataFrameSchema) Le schéma.
    """
    try:
        LOGGER.debug(f"Validation du schéma {schema}.")
        schema.validate(df)

    except pa.errors.SchemaError as error:
        LOGGER.error(f"Erreur de validation du schéma {schema} : {error}.")
        LOGGER.error(f"Attributs attendus : {schema.__annotations__}")

        raise error
