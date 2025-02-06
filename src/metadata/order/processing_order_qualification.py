"""
Module de classification de l'ordre IHO des données.

Ce module contient les fonctions pour classifier l'ordre IHO des données.
"""

from __future__ import annotations

import geopandas as gpd
from loguru import logger

import schema.model_ids as schema_ids
from .order_models import OrderStatistics, IHOorderQualifiquation, OrderType


LOGGER = logger.bind(name="CSB-Processing.Metadata.IHO.Order.Qualification")


def calculate_order_statistics(
    group: gpd.GeoDataFrame, data_count: int, decimal_precision: int
) -> OrderStatistics:
    """
    Calcule les statistiques pour un groupe de sondes selon son ordre IHO.

    :param group: Groupe de données à traiter.
    :type group: gpd.GeoDataFrame
    :param data_count: Nombre total de sondes.
    :type data_count: int
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :return: Statistiques pour le groupe.
    :rtype: OrderStatistics
    """
    LOGGER.debug(f"Calcul des statistiques pour un groupe de sondes.")

    return OrderStatistics(
        sounding_count=len(group),
        count_pourcentage=(len(group) / data_count) * 100,
        min_depth=group[schema_ids.DEPTH_PROCESSED_METER].min(),
        max_depth=group[schema_ids.DEPTH_PROCESSED_METER].max(),
        mean_depth=round(
            group[schema_ids.DEPTH_PROCESSED_METER].mean(), decimal_precision
        ),
        min_tvu=group[schema_ids.UNCERTAINTY].min(),
        max_tvu=group[schema_ids.UNCERTAINTY].max(),
        mean_tvu=round(group[schema_ids.UNCERTAINTY].mean(), decimal_precision),
        min_thu=group[schema_ids.THU].min(),
        max_thu=group[schema_ids.THU].max(),
        mean_thu=round(group[schema_ids.THU].mean(), decimal_precision),
    )


def classify_iho_order(
    data_geodataframe: gpd.GeoDataFrame, decimal_precision: int
) -> IHOorderQualifiquation:
    """
    Classification les données selon les ordres IHO.

    :param data_geodataframe: Données traitées à classifier.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :return: La qualification des données selon les ordres IHO.
    :rtype: IHOorderQualifiquation
    """
    LOGGER.debug(f"Classification de l'ordre IHO des données.")

    grouped = data_geodataframe.groupby(schema_ids.IHO_ORDER)
    data_count: int = len(data_geodataframe)

    def _calulate_order_statistics(order_type: OrderType) -> OrderStatistics | None:
        return (
            calculate_order_statistics(
                group=grouped.get_group(order_type),
                data_count=data_count,
                decimal_precision=decimal_precision,
            )
            if order_type in grouped.groups
            else None
        )

    return IHOorderQualifiquation(
        exclusive_order=_calulate_order_statistics(OrderType.exclusive_order),
        special_order=_calulate_order_statistics(OrderType.special_order),
        order_1a=_calulate_order_statistics(OrderType.order_1a),
        order_1b=_calulate_order_statistics(OrderType.order_1b),
        order_2=_calulate_order_statistics(OrderType.order_2),
        order_not_met=_calulate_order_statistics(OrderType.order_not_met),
    ).round_percentages(decimal_precision)
