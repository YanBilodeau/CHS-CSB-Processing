"""
Module qui contient les classes abstraites pour les ordres de transformation.

Ce module contient les classes abstraites pour les ordres de transformation.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class OrderType(IntEnum):
    EXCLUSIVE_ORDER = 0
    SPECIAL_ORDER = 1
    ORDER_1A = 2
    ORDER_1B = 3
    ORDER_2 = 4
    ORDER_NOT_MET = 5

    def __str__(self) -> str:
        return ORDER_NAME_MAP.get(self)


ORDER_NAME_MAP: dict[OrderType, str] = {
    OrderType.EXCLUSIVE_ORDER: "Exclusive Order",
    OrderType.SPECIAL_ORDER: "Special Order",
    OrderType.ORDER_1A: "Order 1a",
    OrderType.ORDER_1B: "Order 1b",
    OrderType.ORDER_2: "Order 2",
    OrderType.ORDER_NOT_MET: "Order Not Met",
}


@dataclass
class TVUorder:
    a: Optional[float]
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    b: Optional[float]
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""


@dataclass
class THUorder:
    constant: Optional[float]
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    coefficient_depth: Optional[float]
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""
