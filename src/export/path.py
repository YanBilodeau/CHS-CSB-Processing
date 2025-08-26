"""
Module pour la gestion des chemins de fichiers, y compris la validation et la correction des noms de fichiers.
"""

import re
from pathlib import Path

from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Export.Path")


def sanitize_path_name(path: Path) -> Path:
    """
    Fonction qui remplace les caractères invalides dans le nom d'un fichier.

    :param path: Le chemin du fichier.
    :type path: Path
    :return: Le chemin du fichier avec un nom sans caractères invalides.
    :rtype: Path
    """
    LOGGER.debug(f"Validation du nom du fichier : '{path.name}'.")

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized_name = re.sub(invalid_chars, "_", path.name)

    return path.with_name(sanitized_name)
