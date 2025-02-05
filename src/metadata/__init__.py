"""
Package pour la gestion des métadonnées.
"""

from .export import export_metadata_to_json
from .metadata_models import CSBmetadata

__all__ = ["CSBmetadata", "export_metadata_to_json"]
