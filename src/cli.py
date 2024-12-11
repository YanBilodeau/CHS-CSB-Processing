"""
Ce module contient la fonction principale de la ligne de commande.

Il permet de traiter des fichiers de données bathymétriques et de les géoréférencer.
"""

import click
from pathlib import Path
from typing import Collection

from loguru import logger

from csb_processing import processing_workflow

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
    help="Ce script permet de traiter des fichiers de données bathymétriques et de les géoréférencer."
)
@click.option(
    "--files",
    type=click.Path(exists=False),
    multiple=True,
    help="Chemins des fichiers ou répertoires à traiter.",
)
@click.option(
    "--vessel_id",
    type=str,
    help="Identifiant du navire.",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Chemin du répertoire de sortie.",
)
def cli(files: Collection[Path], vessel_id: str, output: Path) -> None:
    # Get the files to parse
    files: list[Path] = get_files(files)

    # Check if there are files to process
    if not files:
        LOGGER.error("Aucun fichier valide à traiter.")
        return None

    processing_workflow(files=files, vessel_id=vessel_id, output=Path(output))
