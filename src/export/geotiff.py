"""
Module pour l'exportation des données en GeoTIFF.

Ce module fournit une fonction pour exporter un GeoDataFrame en fichier GeoTIFF,
en rasterisant les géométries et en moyennant les valeurs par pixel lorsque plusieurs
valeurs tombent dans la même cellule.
"""

import warnings
from pathlib import Path
from typing import Optional, Any

import geopandas as gpd
import pandas as pd
import rasterio
import numpy as np
from loguru import logger
from rasterio.features import rasterize
from rasterio.transform import from_bounds, Affine
from rasterio.errors import NotGeoreferencedWarning
from rasterio.enums import MergeAlg
from datetime import datetime

from .crs import transform_geodataframe_crs
from .path import sanitize_path_name


LOGGER = logger.bind(name="CSB-Processing.Export.GeoTIFF")
WGS84 = 4326
BAND_NAME = "Depth"
BAND_UNIT = "m"
NODATA_FLOAT32 = np.float32(3.40282e38)


def _validate_and_transform_crs(
    geodataframe: gpd.GeoDataFrame, to_epsg: Optional[int]
) -> None:
    if geodataframe.crs is None:
        raise ValueError("Le GeoDataFrame doit avoir un système de coordonnées défini.")

    transform_geodataframe_crs(geodataframe, to_epsg)


def _compute_grid(
    geodataframe: gpd.GeoDataFrame, resolution: float
) -> tuple[int, int, Affine]:
    minx, miny, maxx, maxy = geodataframe.total_bounds
    width = int(np.ceil((maxx - minx) / resolution))
    height = int(np.ceil((maxy - miny) / resolution))

    if width <= 0 or height <= 0:
        raise ValueError("Les dimensions du raster doivent être positives.")

    transform = from_bounds(minx, miny, maxx, maxy, width, height)

    return width, height, transform


def _prepare_shapes(
    geodataframe: gpd.GeoDataFrame, column: str
) -> tuple[list[tuple[object, float]], list[tuple[object, float]]]:
    shapes_with_values = [
        (geom, -float(value))  # conserve la convention profondeur négative
        for geom, value in zip(geodataframe.geometry, geodataframe[column])
        if not pd.isna(value)
    ]

    ones_shapes = [(geom, 1.0) for geom, _ in shapes_with_values]

    return shapes_with_values, ones_shapes


def _rasterize_sum_and_count(
    shapes_with_values: list[tuple[object, float]],
    ones_shapes: list[tuple[object, float]],
    height: int,
    width: int,
    transform: Affine,
) -> tuple[np.ndarray, np.ndarray]:
    sum_arr = np.zeros((height, width), dtype=np.float32)
    count_arr = np.zeros((height, width), dtype=np.float32)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

        rasterize(
            shapes=shapes_with_values,
            out=sum_arr,
            transform=transform,
            fill=0.0,
            merge_alg=MergeAlg.add,
        )
        rasterize(
            shapes=ones_shapes,
            out=count_arr,
            transform=transform,
            fill=0.0,
            merge_alg=MergeAlg.add,
        )

    return sum_arr, count_arr


def _mean_with_nodata(
    sum_arr: np.ndarray, count_arr: np.ndarray, nodata_value: np.float32
) -> np.ndarray:
    mean_arr = np.full(sum_arr.shape, nodata_value, dtype=np.float32)
    np.divide(sum_arr, count_arr, out=mean_arr, where=count_arr > 0)

    return mean_arr


def _band_stats_tags(mean_arr: np.ndarray, nodata_value: np.float32) -> dict:
    valid = np.isfinite(mean_arr) & (mean_arr != nodata_value)
    if valid.any():
        vals = mean_arr[valid]
        return {
            "STATISTICS_APPROXIMATE": "YES",
            "STATISTICS_MINIMUM": str(float(np.min(vals))),
            "STATISTICS_MAXIMUM": str(float(np.max(vals))),
            "STATISTICS_MEAN": str(float(np.mean(vals))),
            "STATISTICS_STDDEV": str(float(np.std(vals))),
            "Band_Direction": "Height",
            "Band_Name": BAND_NAME,
        }
    return {
        "STATISTICS_MINIMUM": "nan",
        "STATISTICS_MAXIMUM": "nan",
        "STATISTICS_MEAN": "nan",
        "STATISTICS_STDDEV": "nan",
        "Band_Direction": "Height",
    }


def _write_geotiff(
    output_path: Path,
    mean_arr: np.ndarray,
    transform: Affine,
    to_epsg: Optional[int],
    nodata_value: np.float32,
) -> None:
    with rasterio.open(
        sanitize_path_name(output_path),
        "w",
        driver="GTiff",
        height=mean_arr.shape[0],
        width=mean_arr.shape[1],
        count=1,
        dtype=np.float32,
        crs=f"EPSG:{to_epsg}",
        transform=transform,
        compress="lzw",
        nodata=float(nodata_value),
    ) as dst:
        dst.write(mean_arr, 1)
        dst.set_band_description(1, BAND_NAME)
        dst.set_band_unit(1, BAND_UNIT)
        dst.update_tags(1, **_band_stats_tags(mean_arr, nodata_value))
        dst.update_tags(
            TIFFTAG_SOFTWARE="CSH-CSB-Processing",
            TIFFTAG_DATETIME=datetime.now().isoformat(),
            AREA_OR_POINT="Point",
        )


def export_geodataframe_to_geotiff(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    column: str = "Depth_processed_meter",
    resolution: Optional[float] = 0.00005,
    to_epsg: Optional[int] = WGS84,
    **kwargs: Any,
) -> None:
    """
    Exporte un GeoDataFrame en fichier GeoTIFF en rasterisant les géométries

    :param geodataframe: Le GeoDataFrame à exporter.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param column: Le nom de la colonne contenant les valeurs à rasteriser.
    :type column: str
    :param resolution: La résolution du raster en unités de la CRS
    :type resolution: float
    :param to_epsg: Le code EPSG de la CRS cible
    :type to_epsg: Optional[int]
    :raises ValueError: Si le GeoDataFrame n'a pas de CRS défini ou si les dimensions du raster sont invalides.
    """
    LOGGER.debug(
        f"Sauvegarde du GeoDataFrame en fichier GeoTIFF (résolution: {resolution}) : '{output_path}'."
    )

    _validate_and_transform_crs(geodataframe, to_epsg)
    width, height, transform = _compute_grid(geodataframe, resolution)
    shapes_with_values, ones_shapes = _prepare_shapes(geodataframe, column)
    sum_arr, count_arr = _rasterize_sum_and_count(
        shapes_with_values, ones_shapes, height, width, transform
    )
    mean_arr = _mean_with_nodata(sum_arr, count_arr, NODATA_FLOAT32)
    _write_geotiff(output_path, mean_arr, transform, to_epsg, NODATA_FLOAT32)
