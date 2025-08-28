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
from rasterio.windows import transform as window_transform, bounds as window_bounds
from datetime import datetime
from shapely.geometry import box  # for spatial filtering

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
    """
    Fonction pour valider et transformer le CRS d'un GeoDataFrame.

    :param geodataframe: Le GeoDataFrame à valider et transformer.
    :param to_epsg: Le code EPSG cible pour la transformation.
    :raises ValueError: Si le GeoDataFrame n'a pas de CRS défini.
    """
    if geodataframe.crs is None:
        raise ValueError("Le GeoDataFrame doit avoir un système de coordonnées défini.")

    transform_geodataframe_crs(geodataframe, to_epsg)


def _compute_grid(
    geodataframe: gpd.GeoDataFrame, resolution: float
) -> tuple[int, int, Affine]:
    """
    Fonction pour calculer la grille raster (largeur, hauteur, transformation)
    basée sur les limites du GeoDataFrame et la résolution spécifiée.

    :param geodataframe: Le GeoDataFrame pour lequel calculer la grille.
    :param resolution: La résolution du raster en unités du CRS.
    :return: Un tuple contenant la largeur, la hauteur et la transformation affine.
    :raises ValueError: Si les dimensions du raster ne sont pas positives.
    :returns: tuple[int, int, Affine] - (width, height, transform)
    """
    minx, miny, maxx, maxy = geodataframe.total_bounds
    width = int(np.ceil((maxx - minx) / resolution))
    height = int(np.ceil((maxy - miny) / resolution))

    if width <= 0 or height <= 0:
        raise ValueError("Les dimensions du raster doivent être positives.")

    transform = from_bounds(minx, miny, maxx, maxy, width, height)

    return width, height, transform


def _prepare_shapes_window(
    geodataframe: gpd.GeoDataFrame,
    column: str,
    bounds: tuple[float, float, float, float],
) -> tuple[list[tuple[object, float]], list[tuple[object, float]]]:
    """
    Prépare les formes et les valeurs pour une fenêtre raster donnée.
    Effectue un sous-ensemble spatial pour n'inclure que les géométries
    qui intersectent les limites de la fenêtre.

    :param geodataframe: Le GeoDataFrame contenant les géométries et les valeurs.
    :param column: Le nom de la colonne contenant les valeurs à rasteriser.
    :param bounds: Les limites de la fenêtre raster (minx, miny, maxx, maxy).
    :return: Un tuple contenant deux listes :
             - La première liste contient des tuples de (géométrie, valeur).
             - La deuxième liste contient des tuples de (géométrie, 1.0) pour le comptage.
    """
    # Spatial subset by window bounds to avoid rasterizing irrelevant features
    try:
        idx = list(geodataframe.sindex.intersection(bounds))
        sub = geodataframe.iloc[idx]

    except Exception as e:
        LOGGER.warning(f"Erreur lors de l'utilisation de l'index spatial : {e}")
        sub = geodataframe[geodataframe.geometry.intersects(box(*bounds))]

    shapes_with_values = [
        (geom, -float(val))
        for geom, val in zip(sub.geometry, sub[column])
        if geom is not None and not pd.isna(val)
    ]

    ones_shapes = [(geom, 1.0) for geom, _ in shapes_with_values]

    return shapes_with_values, ones_shapes


class _RunningStats:
    """
    Classe pour calculer les statistiques (min, max, mean, stddev).
    """

    def __init__(self) -> None:
        self.count = 0
        self.sum = 0.0
        self.sumsq = 0.0
        self.min = np.inf
        self.max = -np.inf

    def update(self, tile: np.ndarray, nodata_value: np.float32) -> None:
        """
        Met à jour les statistiques avec une nouvelle tuile de données.
        Ignore les valeurs nodata et NaN.

        :param tile: La tuile de données à intégrer dans les statistiques.
        :param nodata_value: La valeur nodata à ignorer.
        """
        mask = np.isfinite(tile) & (tile != nodata_value)

        if not np.any(mask):
            return

        vals = tile[mask].astype(np.float64, copy=False)
        self.count += vals.size
        self.sum += float(vals.sum())
        self.sumsq += float(np.square(vals).sum())
        self.min = float(min(self.min, float(vals.min())))
        self.max = float(max(self.max, float(vals.max())))

    def tags(self) -> dict:
        """
        Retourne les statistiques sous forme de dictionnaire de tags.
        Si aucune donnée n'a été ajoutée, retourne "nan" pour toutes les statistiques.

        :return: Un dictionnaire contenant les statistiques.
        """
        if self.count == 0:
            return {
                "STATISTICS_MINIMUM": "nan",
                "STATISTICS_MAXIMUM": "nan",
                "STATISTICS_MEAN": "nan",
                "STATISTICS_STDDEV": "nan",
                "Band_Direction": "Height",
            }

        mean = self.sum / self.count
        var = max(self.sumsq / self.count - mean * mean, 0.0)
        std = np.sqrt(var)

        return {
            "STATISTICS_APPROXIMATE": "YES",
            "STATISTICS_MINIMUM": str(self.min),
            "STATISTICS_MAXIMUM": str(self.max),
            "STATISTICS_MEAN": str(mean),
            "STATISTICS_STDDEV": str(float(std)),
            "Band_Direction": "Height",
            "Band_Name": BAND_NAME,
        }


def _write_geotiff_windowed(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    column: str,
    width: int,
    height: int,
    transform: Affine,
    to_epsg: Optional[int],
    nodata_value: np.float32,
    blocksize: int = 512,
) -> None:
    """
    Écrit un GeoDataFrame dans un fichier GeoTIFF en utilisant une écriture par fenêtres.

    :param geodataframe: Le GeoDataFrame à écrire.
    :param output_path: Le chemin du fichier de sortie.
    :param column: Le nom de la colonne contenant les valeurs à rasteriser.
    :param width: La largeur du raster en pixels.
    :param height: La hauteur du raster en pixels.
    :param transform: La transformation affine du raster.
    :param to_epsg: Le code EPSG pour le CRS du raster.
    :param nodata_value: La valeur nodata à utiliser dans le raster.
    :param blocksize: La taille des blocs pour l'écriture par fenêtres.
    :raises ValueError: Si la largeur ou la hauteur sont non positives.
    """
    stats = _RunningStats()

    with rasterio.open(
        sanitize_path_name(output_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=np.float32,
        crs=(f"EPSG:{to_epsg}" if to_epsg is not None else None),
        transform=transform,
        tiled=True,
        blockxsize=blocksize,
        blockysize=blocksize,
        compress="deflate",
        zlevel=9,
        predictor=3,
        NUM_THREADS="ALL_CPUS",
        BIGTIFF="IF_NEEDED",
        nodata=float(nodata_value),
    ) as dst:
        for _, window in dst.block_windows(1):
            w_transform = window_transform(window, transform)
            w_bounds = window_bounds(window, transform)

            shapes_with_values, ones_shapes = _prepare_shapes_window(
                geodataframe, column, w_bounds
            )

            if not shapes_with_values:
                # Nothing to write in this tile; fill with nodata
                mean_tile = np.full(
                    (window.height, window.width), nodata_value, dtype=np.float32
                )
                dst.write(mean_tile, 1, window=window)
                continue

            sum_tile = np.zeros((window.height, window.width), dtype=np.float32)
            count_tile = np.zeros((window.height, window.width), dtype=np.float32)

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
                rasterize(
                    shapes=shapes_with_values,
                    out=sum_tile,
                    transform=w_transform,
                    fill=0.0,
                    merge_alg=MergeAlg.add,
                )
                rasterize(
                    shapes=ones_shapes,
                    out=count_tile,
                    transform=w_transform,
                    fill=0.0,
                    merge_alg=MergeAlg.add,
                )

            mean_tile = np.full(
                (window.height, window.width), nodata_value, dtype=np.float32
            )
            np.divide(sum_tile, count_tile, out=mean_tile, where=count_tile > 0)

            dst.write(mean_tile, 1, window=window)
            stats.update(mean_tile, nodata_value)

        dst.set_band_description(1, BAND_NAME)
        dst.set_band_unit(1, BAND_UNIT)
        dst.update_tags(1, **stats.tags())
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
    et en moyennant les valeurs par pixel lorsque plusieurs valeurs tombent dans la même cellule.

    :param geodataframe: Le GeoDataFrame à exporter.
    :param output_path: Le chemin du fichier de sortie.
    :param column: Le nom de la colonne contenant les valeurs à rasteriser.
    :param resolution: La résolution du raster en unités du CRS.
    :param to_epsg: Le code EPSG pour le CRS du raster.
    """
    if resolution is None or resolution <= 0:
        raise ValueError("La résolution doit être un flottant positif.")
    LOGGER.debug(
        f"Sauvegarde du GeoDataFrame en fichier GeoTIFF (résolution: {resolution}) : '{output_path}'."
    )

    _validate_and_transform_crs(geodataframe, to_epsg)
    width, height, transform = _compute_grid(geodataframe, float(resolution))

    # Windowed writer keeps memory usage bounded (blocksize^2 per tile)
    _write_geotiff_windowed(
        geodataframe=geodataframe,
        output_path=output_path,
        column=column,
        width=width,
        height=height,
        transform=transform,
        to_epsg=to_epsg,
        nodata_value=NODATA_FLOAT32,
        blocksize=512,
    )
