"""
Ce module contient la fonction principale de la ligne de commande.

Il permet de traiter des fichiers de données bathymétriques et de les géoréférencer.
"""

import click
from pathlib import Path
import sys
from typing import Collection, Optional

from loguru import logger

from csb_processing import processing_workflow
from logger.loguru_config import configure_logger
from vessel import UNKNOWN_VESSEL_CONFIG

LOGGER = logger.bind(name="CSB-Processing.CLI")


def is_valid_file(file: Path) -> bool:
    """
    Vérifie si le fichier est valide pour le traitement.

    :param file: Chemin du fichier.
    :type file: Path
    :return: Vrai si le fichier est valide, faux sinon.
    :rtype: bool
    """
    return file.suffix.lower() in {".csv", ".txt", ".xyz"}


def get_files(paths: Collection[Path]) -> list[Path]:
    """
    Récupère les fichiers à traiter.

    :param paths: Chemins des fichiers ou répertoires.
    :type paths: Collection[Path]
    :return: Liste des fichiers à traiter.
    :rtype: list[Path]
    """
    files: list[Path] = []

    for path in paths:
        path = Path(path)

        if path.is_file() and is_valid_file(path):
            files.append(path)

        elif path.is_dir():
            files.extend(file for file in path.glob("**/*") if is_valid_file(file))

    return files


@click.command(
    help="""
    Ce script permet de traiter des fichiers de données bathymétriques et de les géoréférencer.\n
    This script allows to process bathymetric data files and georeference them.
    """
)
@click.option(
    "--files",
    type=click.Path(exists=False),
    multiple=True,
    help="""
    Chemins des fichiers ou répertoires à traiter.\n
    Paths of the files or directories to process.
    """,
)
@click.option(
    "--output",
    type=click.Path(),
    help="""
    Chemin du répertoire de sortie.\n
    Path of the output directory.
    """,
)
@click.option(
    "--vessel",
    type=str,
    required=False,
    help="""
    Identifiant du navire. Si aucun identifiant de navire est utilisé, un navire par défaut
    avec des bras de levier à 0 sera utilisé.\n
    Vessel identifier. If no vessel identifier is used, a default vessel with lever arms at 0 will be used.
    """,
)
def cli(files: Collection[Path], output: Path, vessel: Optional[str]) -> None:
    configure_logger()

    LOGGER.info(f"Ligne de commande exécutée : python {' '.join(sys.argv)}")

    # Get the files to parse
    files: list[Path] = get_files(files)

    # Check if there are files to process
    if not files:
        LOGGER.error("Aucun fichier valide à traiter.")
        return None

    if not vessel:
        LOGGER.warning(
            "Aucun identifiant de navire n'a été fourni. Un navire par défaut sera utilisé."
        )
        vessel = UNKNOWN_VESSEL_CONFIG

    processing_workflow(files=files, vessel=vessel, output=Path(output))
