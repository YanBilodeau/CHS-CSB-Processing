"""
Module de génération de rapports HTML avec visualisations statistiques.

Ce package fournit les outils pour créer des rapports HTML complets
combinant métadonnées et visualisations Plotly des statistiques de levé.
"""

from .report_generator import generate_statistics_report

__all__ = ["generate_statistics_report"]
