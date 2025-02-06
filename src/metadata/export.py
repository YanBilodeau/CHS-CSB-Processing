"""
Module pour exporter les métadonnées.

Ce module contient les fonctions pour exporter les métadonnées.
"""

import json
from pathlib import Path

from loguru import logger

from .metadata_models import CSBmetadata


LOGGER = logger.bind(name="CSB-Processing.Metadata.Export")


def export_metadata_to_json(metadata: CSBmetadata, output_path: Path) -> None:
    """
    Fonction pour exporter les métadonnées au format JSON.

    :param metadata: Métadonnées à exporter.
    :type metadata: CSBmetadata
    :param output_path: Chemin du fichier de sortie.
    :type output_path: Path
    """
    LOGGER.debug(f"Export des métadonnées au format JSON : {output_path}")

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metadata.__dict__(), file, indent=4)  # type: ignore
