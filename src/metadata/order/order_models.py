"""
Modèles pour la qualification des données selon les ordres IHO.

Ce module contient les modèles pour la qualification des données selon les ordres IHO.
"""

from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Metadata.IHO.Order.Models")


class OrderEnum(StrEnum):
    """
    Types d'ordres IHO.
    """

    EXCLUSIVE_ORDER = "Exclusive Order"
    SPECIAL_ORDER = "Special Order"
    ORDER_1A = "Order 1a"
    ORDER_1B = "Order 1b"
    ORDER_2 = "Order 2"
    ORDER_NOT_MET = "Order Not Met"


ORDER_HIERARCHY: dict[OrderEnum, list[OrderEnum]] = {
    OrderEnum.EXCLUSIVE_ORDER: [OrderEnum.EXCLUSIVE_ORDER],
    OrderEnum.SPECIAL_ORDER: [OrderEnum.EXCLUSIVE_ORDER, OrderEnum.SPECIAL_ORDER],
    OrderEnum.ORDER_1A: [
        OrderEnum.EXCLUSIVE_ORDER,
        OrderEnum.SPECIAL_ORDER,
        OrderEnum.ORDER_1A,
    ],
    OrderEnum.ORDER_1B: [
        OrderEnum.EXCLUSIVE_ORDER,
        OrderEnum.SPECIAL_ORDER,
        OrderEnum.ORDER_1A,
        OrderEnum.ORDER_1B,
    ],
    OrderEnum.ORDER_2: [
        OrderEnum.EXCLUSIVE_ORDER,
        OrderEnum.SPECIAL_ORDER,
        OrderEnum.ORDER_1A,
        OrderEnum.ORDER_1B,
        OrderEnum.ORDER_2,
    ],
    OrderEnum.ORDER_NOT_MET: list(OrderEnum),
}


@dataclass
class OrderType:
    name: OrderEnum
    """Nom de l'ordre."""
    order_within: list[OrderEnum] = field(init=False)
    """Ordres inclus."""

    def __post_init__(self) -> None:
        self.order_within = ORDER_HIERARCHY[self.name]


@dataclass
class OrderStatistics:
    """
    Statistiques pour un ordre IHO.
    """

    sounding_count_within_order: int
    """Nombre de sondages respectant l'ordre."""
    sounding_pourcentage_within_order: float
    """Pourcentage du nombre de sondages respectant l'ordre."""
    min_depth: Optional[float] = None
    """Profondeur minimale."""
    max_depth: Optional[float] = None
    """Profondeur maximale."""
    mean_depth: Optional[float] = None
    """Profondeur moyenne."""
    median_depth: Optional[float] = None
    """Profondeur médiane."""
    min_tvu: Optional[float] = None
    """TVU minimale."""
    max_tvu: Optional[float] = None
    """TVU maximale."""
    mean_tvu: Optional[float] = None
    """TVU moyenne."""
    median_tvu: Optional[float] = None
    """TVU médiane."""
    min_thu: Optional[float] = None
    """THU minimale."""
    max_thu: Optional[float] = None
    """THU maximale."""
    mean_thu: Optional[float] = None
    """THU moyenne."""
    median_thu: Optional[float] = None
    """THU médiane."""

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            key: value
            for key, value in {
                "Sounding Count Within Order": self.sounding_count_within_order,
                "Sounding Within Order (%)": self.sounding_pourcentage_within_order,
                "Min Depth (m)": self.min_depth,
                "Max Depth (m)": self.max_depth,
                "Mean Depth (m)": self.mean_depth,
                "Median Depth (m)": self.median_depth,
                "Min TVU (m)": self.min_tvu,
                "Max TVU (m)": self.max_tvu,
                "Mean TVU (m)": self.mean_tvu,
                "Median TVU (m)": self.median_tvu,
                "Min THU (m)": self.min_thu,
                "Max THU (m)": self.max_thu,
                "Mean THU (m)": self.mean_thu,
                "Median THU (m)": self.median_thu,
            }.items()
            if value is not None
        }


@dataclass
class IHOorderQualifiquation:
    """
    Qualification des données selon les ordres IHO.
    """

    exclusive_order: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre exclusif."""
    special_order: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre spécial."""
    order_1a: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre 1a."""
    order_1b: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre 1b."""
    order_2: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre 2."""
    order_not_met: Optional[OrderStatistics] = None
    """Statistiques pour l'ordre non respecté."""

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            OrderEnum.EXCLUSIVE_ORDER: (
                self.exclusive_order.__dict__() if self.exclusive_order else None
            ),
            OrderEnum.SPECIAL_ORDER: (
                self.special_order.__dict__() if self.special_order else None
            ),
            OrderEnum.ORDER_1A: self.order_1a.__dict__() if self.order_1a else None,
            OrderEnum.ORDER_1B: self.order_1b.__dict__() if self.order_1b else None,
            OrderEnum.ORDER_2: self.order_2.__dict__() if self.order_2 else None,
            OrderEnum.ORDER_NOT_MET: (
                self.order_not_met.__dict__() if self.order_not_met else None
            ),
        }
