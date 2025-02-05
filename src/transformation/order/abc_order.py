"""
Module qui contient les classes abstraites pour les ordres de transformation.

Ce module contient les classes abstraites pour les ordres de transformation.
"""

from abc import ABC
from dataclasses import dataclass
from enum import StrEnum


class OrderType(StrEnum):
    exclusive_order = "Exclusive Order"
    special_order = "Special Order"
    order_1a = "Order 1a"
    order_1b = "Order 1b"
    order_2 = "Order 2"
    order_not_met = "Order not met"


@dataclass
class TVUorder(ABC):
    a: float
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    b: float
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""


@dataclass
class THUorder(ABC):
    constant: float
    """Représente la partie de l'incertitude qui ne varie pas avec la profondeur."""
    coefficient_depth: float
    """Un coefficient qui représente la partie de l'incertitude qui varie avec la profondeur."""
