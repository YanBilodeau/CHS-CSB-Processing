"""
Module contenant les ordres de l'IHO.

Ce module contient les classes représentant les ordres de l'IHO pour la TVU.
"""

from .abc_order import TVUorder


class TVUexclusiveOrder(TVUorder):
    a: float = 0.15
    b: float = 0.0075


class TVUspecialOrder(TVUorder):
    a: float = 0.25
    b: float = 0.0075


class TVUorder1a(TVUorder):
    a: float = 0.5
    b: float = 0.013


class TVUorder1b(TVUorder):
    a: float = 0.5
    b: float = 0.013


class TVUorder2(TVUorder):
    a: float = 1.0
    b: float = 0.023
