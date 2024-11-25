from typing import Optional

from loguru import logger
from shapely import (
    Geometry,
    GeometryCollection,
    voronoi_polygons,
)

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Voronoi.Algorithm")


def create_voronoi_polygons(
    geometry: Geometry,
    tolerance: Optional[float] = 0.0,
    extend_to: Optional[Geometry] = None,
    only_edges: Optional[bool] = False,
    **kwargs,
) -> GeometryCollection:
    """
    Fonction qui crée des polygones de Voronoi à partir d'un ensemble de points.
    https://shapely.readthedocs.io/en/stable/reference/shapely.voronoi_polygons.html

    :param geometry: (Geometry) Géométrie des objets.
    :param tolerance: (float) La tolérance pour l'intersection des lignes.
    :param extend_to: (Geometry) L'étendue de la géométrie des polygones de Voronoi.
    :param only_edges: (bool) Création de polylignes plutôt que des polygones.
    :param kwargs: (dict) Autres paramètres.
    :return: (GeometryCollection) Collection de polygones de Voronoi.
    """
    LOGGER.debug(
        f"Création des polygones de Voronoi à partir de la géométrie : {geometry}."
    )
    return voronoi_polygons(
        geometry=geometry,
        tolerance=tolerance,
        extend_to=extend_to,
        only_edges=only_edges,
        **kwargs,
    )
