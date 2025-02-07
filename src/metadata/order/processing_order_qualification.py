"""
Module de classification de l'ordre IHO des données.

Ce module contient les fonctions pour classifier l'ordre IHO des données.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from loguru import logger

import schema.model_ids as schema_ids
from .order_models import (
    OrderStatistics,
    IHOorderQualifiquation,
    OrderEnum,
    OrderType,
)


LOGGER = logger.bind(name="CSB-Processing.Metadata.IHO.Order.Qualification")


order_map: dict[OrderEnum, OrderType] = {
    OrderEnum.EXCLUSIVE_ORDER: OrderType(OrderEnum.EXCLUSIVE_ORDER),
    OrderEnum.SPECIAL_ORDER: OrderType(OrderEnum.SPECIAL_ORDER),
    OrderEnum.ORDER_1A: OrderType(OrderEnum.ORDER_1A),
    OrderEnum.ORDER_1B: OrderType(OrderEnum.ORDER_1B),
    OrderEnum.ORDER_2: OrderType(OrderEnum.ORDER_2),
    OrderEnum.ORDER_NOT_MET: OrderType(OrderEnum.ORDER_NOT_MET),
}


def calculate_order_statistics(
    group: pd.DataFrame, data_count: int, decimal_precision: int
) -> OrderStatistics:
    """
    Calcule les statistiques pour un groupe de sondes selon son ordre IHO.

    :param group: Groupe de données à traiter.
    :type group: pd.DataFrame
    :param data_count: Nombre total de sondes.
    :type data_count: int
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :return: Statistiques pour le groupe.
    :rtype: OrderStatistics
    """
    LOGGER.debug(f"Calcul des statistiques pour un groupe de sondes.")

    return OrderStatistics(
        sounding_count_within_order=len(group),
        sounding_pourcentage_within_order=round(
            (len(group) / data_count) * 100, decimal_precision
        ),
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

    def _calulate_order_statistics(order_type: OrderEnum) -> OrderStatistics:
        grouped_orders_list: list[gpd.GeoDataFrame] = [
            grouped.get_group(order)
            for order in order_map[order_type].order_within
            if order in grouped.groups
        ]

        if not grouped_orders_list:
            LOGGER.debug(f"Aucun groupe trouvé pour l'ordre {order_type}.")

            return OrderStatistics(
                sounding_pourcentage_within_order=0, sounding_count_within_order=0
            )

        return calculate_order_statistics(
            group=pd.concat(grouped_orders_list),
            data_count=data_count,
            decimal_precision=decimal_precision,
        )

    return IHOorderQualifiquation(
        exclusive_order=_calulate_order_statistics(OrderEnum.EXCLUSIVE_ORDER),
        special_order=_calulate_order_statistics(OrderEnum.SPECIAL_ORDER),
        order_1a=_calulate_order_statistics(OrderEnum.ORDER_1A),
        order_1b=_calulate_order_statistics(OrderEnum.ORDER_1B),
        order_2=_calulate_order_statistics(OrderEnum.ORDER_2),
        order_not_met=_calulate_order_statistics(OrderEnum.ORDER_NOT_MET),
    )
