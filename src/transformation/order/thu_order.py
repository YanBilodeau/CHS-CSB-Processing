"""
Module contwenant les ordres de l'IHO.

Ce module contient les classes représentant les ordres de l'IHO pour la THU.
"""

from .abc_order import THUorder


class THUexclusiveOrder(THUorder):
    constant: float = 1.0
    coefficient_depth: float = 0.0


class THUspecialOrder(THUorder):
    constant: float = 2.0
    coefficient_depth: float = 0.0


class THUorder1a(THUorder):
    constant: float = 5.0
    coefficient_depth: float = 0.05


class THUorder1b(THUorder):
    constant: float = 5.0
    coefficient_depth: float = 0.05


class THUorder2(THUorder):
    constant: float = 20.0
    coefficient_depth: float = 0.1
