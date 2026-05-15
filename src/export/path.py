"""
Module pour la gestion des chemins de fichiers, y compris la validation et la correction des noms de fichiers.
"""

import re
from pathlib import Path

import i18n
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
    LOGGER.debug(i18n.t("export.path.sanitizing_path", name=path.name))

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized_name = re.sub(invalid_chars, "_", path.name)

    return path.with_name(sanitized_name)


def get_data_structure(output_path: Path) -> tuple[Path, Path, Path]:
    """
    Crée et retourne la structure de répertoires standard pour les sorties de traitement.

    Les trois répertoires ``Data/``, ``Tide/`` et ``Log/`` sont créés sous *output_path*
    s'ils n'existent pas encore.

    :param output_path: Chemin racine du répertoire de sortie.
    :type output_path: Path
    :return: Triplet ``(data_path, tide_path, log_path)``.
    :rtype: tuple[Path, Path, Path]
    """
    LOGGER.debug(i18n.t("export.path.init_data_structure", output_path=output_path))

    data_path: Path = output_path / "Data"
    tide_path: Path = output_path / "Tide"
    log_path: Path = output_path / "Log"

    if not data_path.exists():
        data_path.mkdir(parents=True)
    if not tide_path.exists():
        tide_path.mkdir()
    if not log_path.exists():
        log_path.mkdir()

    return data_path, tide_path, log_path
