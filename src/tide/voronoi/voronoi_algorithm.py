"""
Module qui contient l'algorithme de création des polygones de Voronoi.
"""

from typing import Optional

from loguru import logger
import i18n
from shapely import voronoi_polygons
from shapely.geometry import box, GeometryCollection
from shapely.geometry.base import BaseGeometry as Geometry

LOGGER = logger.bind(name="CSB-Processing.Tide.Voronoi.Algorithm")

CANADA_EXTENT: Optional[Geometry] = box(-175, 10, -10, 89)


def create_voronoi_polygons(
    geometry: Geometry,
    tolerance: Optional[float] = 0.0,
    extend_to: Optional[Geometry] = CANADA_EXTENT,
    only_edges: Optional[bool] = False,
    **kwargs,
) -> GeometryCollection:
    """
    Fonction qui crée des polygones de Voronoi à partir d'un ensemble de points.
    https://shapely.readthedocs.io/en/stable/reference/shapely.voronoi_polygons.html

    :param geometry: Géométrie des objets.
    :type geometry: Geometry
    :param tolerance: La tolérance pour l'intersection des lignes.
    :type tolerance: float
    :param extend_to: L'étendue de la géométrie des polygones de Voronoi.
    :type extend_to: Geometry
    :param only_edges: Création de polylignes plutôt que des polygones.
    :type only_edges: bool
    :param kwargs: Autres paramètres.
    :type kwargs: dict
    :return: Collection de polygones de Voronoi.
    :rtype: GeometryCollection
    """
    LOGGER.debug(i18n.t("tide.voronoi.voronoi_algorithm.creating_voronoi"))

    return voronoi_polygons(
        geometry=geometry,
        tolerance=tolerance,
        extend_to=extend_to,
        only_edges=only_edges,
        **kwargs,
    )
