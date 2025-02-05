"""
Module de calcul des incertitudes de mesure selon l'ordre de l'IHO.

Ce module contient les fonctions de calcul des incertitudes de mesure selon l'ordre de l'IHO.
"""

import numpy as np
from typing import Callable

from loguru import logger

from .abc_order import TVUorder, THUorder, OrderType
from . import tvu_order
from . import thu_order


LOGGER = logger.bind(name="CSB-Processing.Transformation.IHO.Order")


tvu_order_map: dict[OrderType, TVUorder] = {
    OrderType.exclusive_order: tvu_order.TVUexclusiveOrder(),
    OrderType.special_order: tvu_order.TVUspecialOrder(),
    OrderType.order_1a: tvu_order.TVUorder1a(),
    OrderType.order_1b: tvu_order.TVUorder1b(),
    OrderType.order_2: tvu_order.TVUorder2(),
}

thu_order_map: dict[OrderType, THUorder] = {
    OrderType.exclusive_order: thu_order.THUexclusiveOrder(),
    OrderType.special_order: thu_order.THUspecialOrder(),
    OrderType.order_1a: thu_order.THUorder1a(),
    OrderType.order_1b: thu_order.THUorder1b(),
    OrderType.order_2: thu_order.THUorder2(),
}


def calculate_tvu_max(order: TVUorder, depth: float) -> float:
    """
    Fonction de calcul de la TVU max.

    :param order: L'ordre de l'IHO.
    :type order: TVUorder
    :param depth: La profondeur de la sonde.
    :type depth: float
    :return: La TVU max selon la formule : sqrt(a^2 + (b * depth)^2).
    :rtype: float
    """
    return np.sqrt(np.square(order.a) + np.square(order.b * depth))


def calculate_thu_max(order: THUorder, depth: float) -> float:
    """
    Fonction de calcul de la THU max.

    :param order: L'ordre de l'IHO.
    :type order: THUorder
    :param depth: La profondeur de la sonde.
    :type depth: float
    :return: La THU max selon la formule : constant + (coefficient_depth * depth).
    :rtype: float
    """
    return order.constant + (order.coefficient_depth * depth)


def _calulate_order(
    depth: float,
    uncertainty: float,
    func_tpu: Callable[[TVUorder | THUorder, float], float],
    orders: dict[OrderType, THUorder | TVUorder],
) -> OrderType:
    """
    Fonction de calcul de la TPU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param uncertainty: L'incertitude de la sonde.
    :type uncertainty: float
    :param func_tpu: La fonction de calcul de la TPU.
    :type func_tpu: Callable
    :return: L'ordre de la TPU.
    :rtype: OrderType
    """
    return next(
        (
            order_type
            for order_type, order in orders.items()
            if func_tpu(order, depth) >= uncertainty
        ),
        OrderType.order_not_met,
    )


def calculate_vertical_order(depth: float, tvu: float) -> OrderType:
    """
    Fonction de calcul de l'ordre de la TVU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param tvu: La TVU de la sonde.
    :type tvu: float
    :return: L'ordre de la TVU.
    :rtype: OrderType
    """
    return _calulate_order(
        depth=depth,
        uncertainty=tvu,
        func_tpu=calculate_tvu_max,
        orders=tvu_order_map,
    )


def calculate_horizontal_order(depth: float, thu: float) -> OrderType:
    """
    Fonction de calcul de l'ordre de la THU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param thu: La THU de la sonde.
    :type thu: float
    :return: L'ordre de la THU.
    :rtype: OrderType
    """
    return _calulate_order(
        depth=depth,
        uncertainty=thu,
        func_tpu=calculate_thu_max,
        orders=thu_order_map,
    )


def calculate_order(depth: float, tvu: float, thu: float) -> OrderType:
    """
    Fonction de calcul de l'ordre de la TPU.

    :param depth: La profondeur de la sonde.
    :type depth: float
    :param tvu: La TVU de la sonde.
    :type tvu: float
    :param thu: La THU de la sonde.
    :type thu: float
    :return: L'ordre de la TPU.
    :rtype: OrderType
    """
    return max(
        calculate_vertical_order(depth=depth, tvu=tvu),
        calculate_horizontal_order(depth=depth, thu=thu),
    )
