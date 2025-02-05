"""
Module contwenant les ordres de l'IHO.

Ce module contient les classes représentant les ordres de l'IHO pour la THU.
"""

from dataclasses import dataclass

from .abc_order import THUorder


@dataclass
class THUexclusiveOrder(THUorder):
    constant: float = 1.0
    coefficient_depth: float = 0.0


@dataclass
class THUspecialOrder(THUorder):
    constant: float = 2.0
    coefficient_depth: float = 0.0


@dataclass
class THUorder1a(THUorder):
    constant: float = 5.0
    coefficient_depth: float = 0.05


@dataclass
class THUorder1b(THUorder):
    constant: float = 5.0
    coefficient_depth: float = 0.05


@dataclass
class THUorder2(THUorder):
    constant: float = 20.0
    coefficient_depth: float = 0.1
