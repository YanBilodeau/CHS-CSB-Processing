"""
Module pour le traitement parallèle avec Dask et GeoPandas.

Ce module fournit des fonctions pour exécuter des opérations en parallèle sur des GeoDataFrames
en utilisant Dask, optimisant ainsi les performances pour les grands ensembles de données géospatiales.
"""

from multiprocessing import cpu_count


import dask_geopandas as dgpd
import geopandas as gpd
from loguru import logger
from typing import Callable


LOGGER = logger.bind(name="CSB-Processing.Transformation.DaskComputing")

CPU_COUNT: int = cpu_count()


def run_dask_function_in_parallel(
    data: gpd.GeoDataFrame,
    func: Callable[[gpd.GeoDataFrame], gpd.GeoDataFrame],
    npartitions: int = CPU_COUNT,
) -> gpd.GeoDataFrame:
    """
    Exécute une fonction Dask en parallèle sur les partitions d'un GeoDataFrame.

    :param data: Données de profondeur.
    :type data: gpd.GeoDataFrame
    :param func: Fonction à exécuter sur chaque partition.
    :type func: Callable[[gpd.GeoDataFrame], gpd.GeoDataFrame]
    :param npartitions: Nombre de partitions pour Dask.
    :type npartitions: int
    :return: Données traitées.
    :rtype: gpd.GeoDataFrame
    """
    dask_data: dgpd.GeoDataFrame = dgpd.from_geopandas(data, npartitions=npartitions)
    dask_data = dask_data.map_partitions(func)  # type: ignore

    return dask_data.compute().pipe(gpd.GeoDataFrame)
