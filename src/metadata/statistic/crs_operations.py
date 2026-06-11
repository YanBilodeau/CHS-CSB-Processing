"""
Opérations de validation et de projection des systèmes de coordonnées.

Ce module gère la validation CRS, la détection automatique de zone UTM
et les reprojections nécessaires pour les calculs de distance.
"""

import geopandas as gpd

WGS84_EPSG: int = 4326
"""Code EPSG pour WGS84 (longitude/latitude)."""


def validate_and_normalize_crs(
    gdf: gpd.GeoDataFrame, target_epsg: int = WGS84_EPSG
) -> gpd.GeoDataFrame:
    """
    Valide que le GeoDataFrame possède un CRS et le reprojette si nécessaire.

    :param gdf: GeoDataFrame à valider.
    :type gdf: gpd.GeoDataFrame
    :param target_epsg: Code EPSG cible (défaut : 4326 WGS84).
    :type target_epsg: int
    :return: GeoDataFrame garanti dans le CRS cible.
    :rtype: gpd.GeoDataFrame
    :raises ValueError: Si le GeoDataFrame n'a pas de CRS défini.
    """
    if gdf.crs is None:
        raise ValueError("Le GeoDataFrame n'a pas de CRS défini.")

    if gdf.crs.to_epsg() != target_epsg:
        gdf = gdf.to_crs(epsg=target_epsg)

    return gdf


def detect_utm_zone(gdf: gpd.GeoDataFrame) -> int:
    """
    Détecte automatiquement la zone UTM WGS84 appropriée.

    La détection est basée sur le centroïde de l'union de toutes les géométries.

    :param gdf: GeoDataFrame en WGS84 (EPSG:4326).
    :type gdf: gpd.GeoDataFrame
    :return: Code EPSG de la zone UTM appropriée.
    :rtype: int
    """
    centroid = gdf.geometry.union_all().centroid
    lon, lat = centroid.x, centroid.y

    utm_zone = int((lon + 180) / 6) + 1
    epsg_code = 32600 + utm_zone if lat >= 0 else 32700 + utm_zone

    return epsg_code


def project_to_utm(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, int]:
    """
    Projette le GeoDataFrame dans la zone UTM WGS84 appropriée.

    La zone UTM est détectée automatiquement via :func:`detect_utm_zone`.

    :param gdf: GeoDataFrame en WGS84 (EPSG:4326).
    :type gdf: gpd.GeoDataFrame
    :return: Tuple (GeoDataFrame projeté en UTM, code EPSG utilisé).
    :rtype: tuple[gpd.GeoDataFrame, int]
    """
    epsg_code = detect_utm_zone(gdf)
    gdf_utm = gdf.to_crs(epsg=epsg_code)

    return gdf_utm, epsg_code
