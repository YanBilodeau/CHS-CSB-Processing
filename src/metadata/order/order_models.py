"""
Modèles pour la qualification des données selon les ordres IHO.

Ce module contient les modèles pour la qualification des données selon les ordres IHO.
"""

from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass
from typing import Optional

from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Metadata.IHO.Order.Models")


class OrderType(StrEnum):
    """
    Types d'ordres IHO.
    """

    exclusive_order = "Exclusive Order"
    special_order = "Special Order"
    order_1a = "Order 1a"
    order_1b = "Order 1b"
    order_2 = "Order 2"
    order_not_met = "Order not met"


@dataclass
class OrderStatistics:
    """
    Statistiques pour un ordre IHO.
    """

    sounding_count: int
    """Nombre de sondages."""
    count_pourcentage: float
    """Pourcentage du nombre de sondages."""
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
            "Sounding Count": self.sounding_count,
            "Count Pourcentage (%)": self.count_pourcentage,
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

    def round_percentages(self, decimal_precision: int) -> IHOorderQualifiquation:
        """
        Arrondit les pourcentages de chaque OrderStatistics selon la précision décimale,
        en s'assurant que le total des pourcentages soit de 100.

        :param decimal_precision: Précision des décimales.
        :type decimal_precision: int
        :return: Qualification des données selon les ordres IHO.
        :rtype: IHOorderQualifiquation
        """
        LOGGER.debug("Arrondissement des pourcentages des statistiques des ordres IHO.")

        stats = [
            self.exclusive_order,
            self.special_order,
            self.order_1a,
            self.order_1b,
            self.order_2,
            self.order_not_met,
        ]

        valid_stats = [stat for stat in stats if stat is not None]

        total_percentage = sum(stat.count_pourcentage for stat in valid_stats)
        rounded_total = round(total_percentage, decimal_precision)
        difference = 100 - rounded_total

        if valid_stats:
            valid_stats[0].count_pourcentage += difference

        for stat in valid_stats:
            stat.count_pourcentage = round(stat.count_pourcentage, decimal_precision)

        final_total = sum(stat.count_pourcentage for stat in valid_stats)
        if final_total != 100:
            valid_stats[0].count_pourcentage += round(
                100 - final_total, decimal_precision
            )

        return self

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            order_type: (
                getattr(self, order_type).__dict__()
                if getattr(self, order_type)
                else None
            )
            for order_type in [
                "exclusive_order",
                "special_order",
                "order_1a",
                "order_1b",
                "order_2",
                "order_not_met",
            ]
        }
