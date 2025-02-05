"""
Module qui contient les classes abstraites pour les ordres de transformation.

Ce module contient les classes abstraites pour les ordres de transformation.
"""

from abc import ABC
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class OrderType(IntEnum):
    exclusive_order = 0
    special_order = 1
    order_1a = 2
    order_1b = 3
    order_2 = 4
    order_not_met = 5

    def __str__(self) -> str:
        return order_name_map.get(self)


order_name_map: dict[OrderType, str] = {
    OrderType.exclusive_order: "Exclusive Order",
    OrderType.special_order: "Special Order",
    OrderType.order_1a: "Order 1a",
    OrderType.order_1b: "Order 1b",
    OrderType.order_2: "Order 2",
    OrderType.order_not_met: "Order not met",
}


@dataclass
class TVUorder(ABC):
    a: Optional[float] = None
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    b: Optional[float] = None
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""


@dataclass
class THUorder(ABC):
    constant: Optional[float] = None
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    coefficient_depth: Optional[float] = None
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""
