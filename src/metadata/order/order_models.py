"""
Modèles pour la qualification des données selon les ordres IHO.

Ce module contient les modèles pour la qualification des données selon les ordres IHO.
"""

from __future__ import annotations

from abc import ABC
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


@dataclass(frozen=True)
class OrderType(ABC):
    name: OrderEnum
    """Nom de l'ordre."""
    order_within: list[OrderEnum] = None
    """Ordres inclus."""


@dataclass(frozen=True)
class ExclusiveOrder(OrderType):
    """
    Ordre exclusif.
    """

    name: OrderEnum = OrderEnum.EXCLUSIVE_ORDER
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [OrderEnum.EXCLUSIVE_ORDER]
    )


@dataclass(frozen=True)
class SpecialOrder(OrderType):
    """
    Ordre spécial.
    """

    name: OrderEnum = OrderEnum.special_order
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [OrderEnum.EXCLUSIVE_ORDER, OrderEnum.special_order]
    )


@dataclass(frozen=True)
class Order1a(OrderType):
    """
    Ordre 1a.
    """

    name: OrderEnum = OrderEnum.order_1a
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [
            OrderEnum.EXCLUSIVE_ORDER,
            OrderEnum.special_order,
            OrderEnum.order_1a,
        ]
    )


@dataclass(frozen=True)
class Order1b(OrderType):
    """
    Ordre 1b.
    """

    name: OrderEnum = OrderEnum.order_1b
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [
            OrderEnum.EXCLUSIVE_ORDER,
            OrderEnum.special_order,
            OrderEnum.order_1a,
            OrderEnum.order_1b,
        ]
    )


@dataclass(frozen=True)
class Order2(OrderType):
    """
    Ordre 2.
    """

    name: OrderEnum = OrderEnum.order_2
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [
            OrderEnum.EXCLUSIVE_ORDER,
            OrderEnum.special_order,
            OrderEnum.order_1a,
            OrderEnum.order_1b,
            OrderEnum.order_2,
        ]
    )


@dataclass(frozen=True)
class OrderNotMet(OrderType):
    """
    Ordre non respecté.
    """

    name: OrderEnum = OrderEnum.order_not_met
    order_within: list[OrderEnum] = field(
        default_factory=lambda: [
            OrderEnum.EXCLUSIVE_ORDER,
            OrderEnum.special_order,
            OrderEnum.order_1a,
            OrderEnum.order_1b,
            OrderEnum.order_2,
            OrderEnum.order_not_met,
        ]
    )


@dataclass
class OrderStatistics:
    """
    Statistiques pour un ordre IHO.
    """

    sounding_count_within_order: int
    """Nombre de sondages respectant l'ordre."""
    sounding_pourcentage_within_order: float
    """Pourcentage du nombre de sondages respectant l'ordre."""
    min_depth: float
    """Profondeur minimale."""
    max_depth: float
    """Profondeur maximale."""
    mean_depth: float
    """Profondeur moyenne."""
    min_tvu: float
    """TVU minimale."""
    max_tvu: float
    """TVU maximale."""
    mean_tvu: float
    """TVU moyenne."""
    min_thu: float
    """THU minimale."""
    max_thu: float
    """THU maximale."""
    mean_thu: float
    """THU moyenne."""

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            "Sounding Count Within Order": self.sounding_count_within_order,
            "Sounding Pourcentage Within Order (%)": self.sounding_pourcentage_within_order,
            "Min Depth (m)": self.min_depth,
            "Max Depth (m)": self.max_depth,
            "Mean Depth (m)": self.mean_depth,
            "Min TVU (m)": self.min_tvu,
            "Max TVU (m)": self.max_tvu,
            "Mean TVU (m)": self.mean_tvu,
            "Min THU (m)": self.min_thu,
            "Max THU (m)": self.max_thu,
            "Mean THU (m)": self.mean_thu,
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

    # def round_percentages(self, decimal_precision: int) -> IHOorderQualifiquation:
    #     """
    #     Arrondit les pourcentages de chaque OrderStatistics selon la précision décimale,
    #     en s'assurant que le total des pourcentages soit de 100.
    #
    #     :param decimal_precision: Précision des décimales.
    #     :type decimal_precision: int
    #     :return: Qualification des données selon les ordres IHO.
    #     :rtype: IHOorderQualifiquation
    #     """
    #     LOGGER.debug("Arrondissement des pourcentages des statistiques des ordres IHO.")
    #
    #     stats = [
    #         self.exclusive_order,
    #         self.special_order,
    #         self.order_1a,
    #         self.order_1b,
    #         self.order_2,
    #         self.order_not_met,
    #     ]
    #
    #     valid_stats = [stat for stat in stats if stat is not None]
    #
    #     total_percentage = sum(
    #         stat.sounding_pourcentage_within_order for stat in valid_stats
    #     )
    #     rounded_total = round(total_percentage, decimal_precision)
    #     difference = 100 - rounded_total
    #
    #     if valid_stats:
    #         valid_stats[0].sounding_pourcentage_within_order += difference
    #
    #     for stat in valid_stats:
    #         stat.sounding_pourcentage_within_order = round(
    #             stat.sounding_pourcentage_within_order, decimal_precision
    #         )
    #
    #     final_total = sum(
    #         stat.sounding_pourcentage_within_order for stat in valid_stats
    #     )
    #     if final_total != 100:
    #         valid_stats[0].sounding_pourcentage_within_order += round(
    #             100 - final_total, decimal_precision
    #         )
    #
    #     return self

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            "Exclusive Order": (
                self.exclusive_order.__dict__() if self.exclusive_order else None
            ),
            "Special Order": (
                self.special_order.__dict__() if self.special_order else None
            ),
            "Order 1a": self.order_1a.__dict__() if self.order_1a else None,
            "Order 1b": self.order_1b.__dict__() if self.order_1b else None,
            "Order 2": self.order_2.__dict__() if self.order_2 else None,
            "Order Not Met": (
                self.order_not_met.__dict__() if self.order_not_met else None
            ),
        }
