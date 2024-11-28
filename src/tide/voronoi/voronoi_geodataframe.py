"""
Module qui contient les fonctions pour manipuler les GeoDataFrame des polygones de Voronoi.

Les fonctions permettent de créer les polygones de Voronoi, de les joindre avec les stations et de fusionner les attributs.
"""

from typing import Optional, Collection

import dask_geopandas as dgpd
import geopandas as gpd
import shapely
from loguru import logger
from shapely import (
    Geometry,
    GeometryCollection,
)
from shapely.constructive import concave_hull

from .voronoi_algorithm import create_voronoi_polygons
from .voronoi_models import TimeSeriesProtocol, StationsHandlerProtocol
from schema import validate_schema, StationsSchema, TideZoneSchema

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Voronoi.Geodataframe")
WGS84: int = 4326
"""EPSG code pouur le système de coordonnées WGS84."""


def from_shapely_object_to_geodataframe(
    geometry: shapely.geometry, epsg: Optional[int] = WGS84
) -> gpd.GeoDataFrame:
    """
    Fonction qui transforme un objet Shapely en GeoDataFrame.

    :param geometry: La géométrie Shapely à transformer.
    :type geometry: shapely.geometry
    :param epsg: Le code EPSG du CRS à utiliser.
    :type epsg: Optional[int]
    :return: Le GeoDataFrame.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug(
        f"Transformation de la géométrie Shapely de type {geometry.geom_type} en GeoDataFrame."
    )
    if isinstance(geometry, GeometryCollection):
        geometries = list(geometry.geoms)
    else:
        geometries = [geometry]

    return gpd.GeoDataFrame(geometry=geometries, crs=epsg)


def create_voronoi_gdf(geometry: Geometry) -> gpd.GeoDataFrame:
    """
    Crée un GeoDataFrame de polygone de Voronoi à partir d'une geometrie Shapely.

    :param geometry: La géométrie Shapely à utiliser pour créer les polygones de Voronoi.
    :type geometry: Geometry
    :return: Le GeoDataFrame contenant les polygones de Voronoi.
    :rtype: gpd.GeoDataFrame
    """
    voronoi: GeometryCollection = create_voronoi_polygons(geometry=geometry)

    return from_shapely_object_to_geodataframe(geometry=voronoi)


def join_stations_voronoi(
    gdf_stations: gpd.GeoDataFrame, gdf_voronoi: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Crée une jointure spatiale entre les stations et les polygones de Voronoi.

    :param gdf_stations: Le GeoDataFrame des stations.
    :type gdf_stations: gpd.GeoDataFrame
    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame
    :return: Le GeoDataFrame joint.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug("Jointure spatiale entre les stations et les polygones de Voronoi.")

    return gpd.sjoin(gdf_stations, gdf_voronoi, how="inner", predicate="within")


def merge_attributes(
    gdf_voronoi: gpd.GeoDataFrame, gdf_joined: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Fusionne les attributs des stations avec les polygones de Voronoi.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param gdf_joined: Le GeoDataFrame avec le geodataframe des stations et des polygones de Voronoi joins.
    :type gdf_joined: gpd.GeoDataFrame
    :return: Le GeoDataFrame avec les attributs fusionnés.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug("Fusion des attributs des stations avec les polygones de Voronoi.")

    gdf_voronoi = gdf_voronoi.merge(
        gdf_joined[["index_right", "id", "code", "name", "time_series", "is_tidal"]],
        left_index=True,
        right_on="index_right",
    )
    gdf_voronoi.drop(columns=["index_right"], inplace=True)

    return gdf_voronoi


def get_voronoi_geodataframe(
    stations_handler: StationsHandlerProtocol,
    time_series: Optional[Collection[TimeSeriesProtocol] | None] = None,
    excluded_stations: Optional[Collection[str] | None] = None,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Récupère le GeoDataFrame des polygones de Voronoi.

    :param stations_handler: Gestionnaire des stations.
    :type stations_handler: StationsHandlerABC
    :param time_series: Liste des séries temporelles pour filtrer les stations. Si None, toutes les stations sont retournées.
    :type time_series: Collection[TimeSeriesProtocol] | None
    :param excluded_stations: Liste des stations à exclure.
    :type excluded_stations: Collection[str] | None
    :return: Le GeoDataFrame des polygones de Voronoi.
    :rtype: gpd.GeoDataFrame[TideZoneSchema]
    """
    gdf_stations: gpd.GeoDataFrame[StationsSchema] = (
        stations_handler.get_stations_geodataframe(
            filter_time_series=time_series,
            excluded_stations=excluded_stations,
            **kwargs,
        )
    )

    gdf_voronoi: gpd.GeoDataFrame = create_voronoi_gdf(
        geometry=gdf_stations.geometry.unary_union
    )

    gdf_joined: gpd.GeoDataFrame = join_stations_voronoi(
        gdf_stations=gdf_stations, gdf_voronoi=gdf_voronoi
    )

    gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema] = merge_attributes(
        gdf_voronoi=gdf_voronoi, gdf_joined=gdf_joined
    )
    validate_schema(df=gdf_voronoi, schema=TideZoneSchema)

    return gdf_voronoi


def get_polygon_by_station_id(
    gdf_voronoi: gpd.GeoDataFrame, station_id: str
) -> gpd.GeoDataFrame:
    """
    Récupère le polygone de Voronoi pour une station donnée.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema]
    :param station_id: L'identifiant de la station.
    :type station_id: str
    :return: Le polygone de Voronoi de la station.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug(f"Récupération du polygone de Voronoi de la station '{station_id}'.")

    return gdf_voronoi.loc[gdf_voronoi["id"] == station_id]


def get_time_series_by_station_id(
    gdf_voronoi: gpd.GeoDataFrame, station_id: str
) -> list[str]:
    """
    Récupère les séries temporelles pour une station donnée.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema]
    :param station_id: L'identifiant de la station.
    :type station_id: str
    :return: Les séries temporelles de la station.
    :rtype: list[str]
    """
    LOGGER.debug(f"Récupération des séries temporelles de la station '{station_id}'.")

    return gdf_voronoi.loc[gdf_voronoi["id"] == station_id]["time_series"].values[0]


def get_code_by_station_id(gdf_voronoi: gpd.GeoDataFrame, station_id: str) -> str:
    """
    Récupère le code de la station.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema]
    :param station_id: L'identifiant de la station.
    :type station_id: str
    :return: Le code de la station.
    :rtype: str
    """
    LOGGER.debug(f"Récupération du code de la station '{station_id}'.")

    return gdf_voronoi.loc[gdf_voronoi["id"] == station_id]["code"].values[0]


def get_name_by_station_id(gdf_voronoi: gpd.GeoDataFrame, station_id: str) -> str:
    """
    Récupère le nom de la station.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema]
    :param station_id: L'identifiant de la station.
    :type station_id: str
    :return: Le nom de la station.
    :rtype: str
    """
    LOGGER.debug(f"Récupération du nom de la station '{station_id}'.")

    return gdf_voronoi.loc[gdf_voronoi["id"] == station_id]["name"].values[0]


def get_polygon_by_geometry(
    gdf_voronoi: gpd.GeoDataFrame,
    geometry: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Récupère les polygones de Voronoi qui intersectent les géométries données.

    :param gdf_voronoi: Le GeoDataFrame des polygones de Voronoi.
    :type gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema]
    :param geometry: La géométrie a utilisé pour l'intersection.
    :type geometry: gpd.GeoDataFrame
    :return: Le GeoDataFrame des polygones de Voronoi qui intersectent les géométries.
    :rtype: gpd.GeoDataFrame[TideZoneSchema]
    """
    LOGGER.debug(
        "Récupération des polygones de Voronoi qui intersectent les géométries."
    )

    dask_gdf_voronoi: dgpd.GeoDataFrame[TideZoneSchema] = dgpd.from_geopandas(
        gdf_voronoi, npartitions=12
    )
    dask_geometry: dgpd.GeoDataFrame = dgpd.from_geopandas(geometry, npartitions=12)

    result: dgpd.GeoDataFrame = dgpd.sjoin(
        dask_gdf_voronoi, dask_geometry, how="inner", predicate="intersects"
    )
    result_computed: gpd.GeoDataFrame = result.compute()
    result_unique: gpd.GeoDataFrame[TideZoneSchema] = result_computed.drop_duplicates(
        subset=["id"]
    ).reset_index(drop=True)

    return result_unique[gdf_voronoi.columns]


def get_concave_hull(
    geometry: Geometry, ratio: float = 0.5, allow_holes: bool = True
) -> Geometry:
    """
    Récupère l'enveloppe concave des polygones de Voronoi.

    :param geometry: La géométrie a utilisé pour l'enveloppe concave.
    :type geometry: Geometry
    :param ratio: Le ratio de l'enveloppe concave.
    :type ratio: float
    :param allow_holes: Autorise les trous dans l'enveloppe concave.
    :type allow_holes: bool
    :return: L'enveloppe concave des polygones.
    :rtype: Geometry
    """
    LOGGER.debug(f"Création de l'enveloppe concave avec un ratio de {ratio}.")

    return concave_hull(geometry, ratio=ratio, allow_holes=allow_holes)
