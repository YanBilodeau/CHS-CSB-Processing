import geopandas as gpd
import pandas as pd
import pandera as pa
from loguru import logger
from pandas import DataFrame
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Schema")


class StationsSchema(pa.DataFrameModel):
    LON: Series[pd.Float64Dtype()]
    LAT: Series[pd.Float64Dtype()]
    DEPTH: Series[pd.Float64Dtype()]
    DATE: Series[pd.DatetimeTZDtype("ns", tz="UTC")]
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
