"""
Module de calcul des incertitudes de mesure selon l'ordre de l'IHO.

Ce module contient les fonctions de calcul des incertitudes de mesure selon l'ordre de l'IHO.
"""

from functools import lru_cache

import numpy as np
from typing import Callable

from loguru import logger

from .order_models import TVUorder, THUorder, OrderType


LOGGER = logger.bind(name="CSB-Processing.Transformation.IHO.Order")


tvu_order_map: dict[OrderType, TVUorder] = {
    OrderType.EXCLUSIVE_ORDER: TVUorder(a=0.15, b=0.0075),
    OrderType.SPECIAL_ORDER: TVUorder(a=0.25, b=0.0075),
    OrderType.ORDER_1A: TVUorder(a=0.5, b=0.013),
    OrderType.ORDER_1B: TVUorder(a=0.5, b=0.013),
    OrderType.ORDER_2: TVUorder(a=1.0, b=0.023),
}

thu_order_map: dict[OrderType, THUorder] = {
    OrderType.EXCLUSIVE_ORDER: THUorder(constant=1.0, coefficient_depth=0.0),
    OrderType.SPECIAL_ORDER: THUorder(constant=2.0, coefficient_depth=0.0),
    OrderType.ORDER_1A: THUorder(constant=5.0, coefficient_depth=0.05),
    OrderType.ORDER_1B: THUorder(constant=5.0, coefficient_depth=0.05),
    OrderType.ORDER_2: THUorder(constant=20.0, coefficient_depth=0.1),
}


@lru_cache(maxsize=None)
def calculate_tvu_max(
    order_type: OrderType, depth: int, decimal_precision: int
) -> float:
    """
    Fonction de calcul de la TVU max.

    :param order_type: L'ordre de l'IHO.
    :type order_type: OrderType
    :param depth: La profondeur de la sonde.
    :type depth: int
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: La TVU max selon la formule : sqrt(a^2 + (b * depth)^2).
    :rtype: float
    """
    order_type: TVUorder = tvu_order_map[order_type]

    return np.sqrt(
        np.square(order_type.a)
        + np.square(order_type.b * (depth / 10**decimal_precision))
    )


@lru_cache(maxsize=None)
def calculate_thu_max(
    order_type: OrderType, depth: int, decimal_precision: int
) -> float:
    """
    Fonction de calcul de la THU max.

    :param order_type: L'ordre de l'IHO.
    :type order_type: OrderType
    :param depth: La profondeur de la sonde.
    :type depth: int
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: La THU max selon la formule : constant + (coefficient_depth * depth).
    :rtype: float
    """
    order_type: THUorder = thu_order_map[order_type]

    return order_type.constant + (
        order_type.coefficient_depth * (depth / 10**decimal_precision)
    )


def _calculate_order(
    depth: float,
    uncertainty: float,
    func_tpu: Callable[[OrderType, int, int], float],
    orders: dict[OrderType, THUorder | TVUorder],
    decimal_precision: int,
) -> OrderType:
    """
    Fonction de calcul de la TPU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param uncertainty: L'incertitude de la sonde.
    :type uncertainty: float
    :param func_tpu: La fonction de calcul de la TPU.
    :type func_tpu: Callable
    :param orders: Les ordres de l'IHO.
    :type orders: dict[OrderType, THUorder | TVUorder]
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: L'ordre de la TPU.
    :rtype: OrderType
    """
    return next(
        (
            order_type
            for order_type in orders.keys()
            if func_tpu(
                order_type, int(depth * 10**decimal_precision), decimal_precision
            )
            >= uncertainty
        ),
        OrderType.ORDER_NOT_MET,
    )


def calculate_vertical_order(
    depth: float, tvu: float, decimal_precision: int
) -> OrderType:
    """
    Fonction de calcul de l'ordre de la TVU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param tvu: La TVU de la sonde.
    :type tvu: float
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: L'ordre de la TVU.
    :rtype: OrderType
    """
    return _calculate_order(
        depth=depth,
        uncertainty=tvu,
        func_tpu=calculate_tvu_max,
        orders=tvu_order_map,
        decimal_precision=decimal_precision,
    )


def calculate_horizontal_order(
    depth: float, thu: float, decimal_precision: int
) -> OrderType:
    """
    Fonction de calcul de l'ordre de la THU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param thu: La THU de la sonde.
    :type thu: float
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: L'ordre de la THU.
    :rtype: OrderType
    """
    return _calculate_order(
        depth=depth,
        uncertainty=thu,
        func_tpu=calculate_thu_max,
        orders=thu_order_map,
        decimal_precision=decimal_precision,
    )


def calculate_order(
    depth: float, tvu: float, thu: float, decimal_precision: int
) -> OrderType:
    """
    Fonction de calcul de l'ordre de la TPU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param tvu: La TVU de la sonde.
    :type tvu: float
    :param thu: La THU de la sonde.
    :type thu: float
    :param decimal_precision: La précision des calculs.
    :type decimal_precision: int
    :return: L'ordre de la TPU.
    :rtype: OrderType
    """
    return max(
        calculate_vertical_order(
            depth=depth, tvu=tvu, decimal_precision=decimal_precision
        ),
        calculate_horizontal_order(
            depth=depth, thu=thu, decimal_precision=decimal_precision
        ),
    )
