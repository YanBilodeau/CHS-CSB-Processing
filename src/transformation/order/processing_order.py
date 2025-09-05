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


def calculate_tvu_max_vectorized(
    order_type: OrderType, depths: np.ndarray
) -> np.ndarray:
    """
    Fonction de calcul vectorisé de la TVU max.

    :param order_type: L'ordre de l'IHO.
    :type order_type: OrderType
    :param depths: Les profondeurs des sondes.
    :type depths: np.ndarray

    :return: La TVU max selon la formule : sqrt(a^2 + (b * depth)^2).
    :rtype: np.ndarray
    """
    order_params = tvu_order_map[order_type]

    return np.sqrt(np.square(order_params.a) + np.square(order_params.b * depths))


def calculate_thu_max_vectorized(
    order_type: OrderType,
    depths: np.ndarray,
) -> np.ndarray:
    """
    Fonction de calcul vectorisé de la THU max.

    :param order_type: L'ordre de l'IHO.
    :type order_type: OrderType
    :param depths: Les profondeurs des sondes.
    :type depths: np.ndarray
    :return: La THU max selon la formule : constant + (coefficient_depth * depth).
    :rtype: np.ndarray
    """
    order_params = thu_order_map[order_type]

    return order_params.constant + (order_params.coefficient_depth * depths)


def _calculate_order_vectorized(
    depths: np.ndarray,
    uncertainties: np.ndarray,
    func_tpu: Callable[[OrderType, np.ndarray], np.ndarray],
    orders: dict[OrderType, THUorder | TVUorder],
) -> np.ndarray:
    """
    Fonction de calcul vectorisé de la TPU.

    :param depths: Les profondeurs des sondes.
    :type depths: np.ndarray
    :param uncertainties: Les incertitudes des sondes.
    :type uncertainties: np.ndarray
    :param func_tpu: La fonction de calcul de la TPU.
    :type func_tpu: Callable
    :param orders: Les ordres de l'IHO.
    :type orders: dict[OrderType, THUorder | TVUorder]
    :return: Les ordres de la TPU.
    :rtype: np.ndarray
    """
    result = np.full(len(depths), OrderType.ORDER_NOT_MET, dtype=object)

    # Tester chaque ordre dans l'ordre de priorité
    for order_type in orders.keys():
        tpu_max = func_tpu(order_type, depths)
        mask = (tpu_max >= uncertainties) & (result == OrderType.ORDER_NOT_MET)
        result[mask] = order_type

    return result


def calculate_vertical_order_vectorized(
    depth: np.ndarray, tvu: np.ndarray
) -> np.ndarray:
    """
    Fonction de calcul de l'ordre de la TVU.

    :param depth: Les profondeurs des sondes.
    :type depth: np.ndarray
    :param tvu: Les TVU des sondes.
    :type tvu: np.ndarray
    :return: Les ordres des TVU.
    :rtype: np.ndarray
    """
    return _calculate_order_vectorized(
        depths=depth,
        uncertainties=tvu,
        func_tpu=calculate_tvu_max_vectorized,
        orders=tvu_order_map,
    )


def calculate_horizontal_order_vectorized(
    depth: np.ndarray, thu: np.ndarray
) -> np.ndarray:
    """
    Fonction de calcul de l'ordre de la THU.

    :param depth: Les profondeurs des sondes.
    :type depth: np.ndarray
    :param thu: Les THU des sondes.
    :type thu: np.ndarray
    :return: Les ordres des THU.
    :rtype: np.ndarray
    """
    return _calculate_order_vectorized(
        depths=depth,
        uncertainties=thu,
        func_tpu=calculate_thu_max_vectorized,
        orders=thu_order_map,
    )
