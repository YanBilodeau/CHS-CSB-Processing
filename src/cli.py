"""
Ce module contient la fonction principale de la ligne de commande.

Il permet de traiter des fichiers de données bathymétriques et de les géoréférencer.
"""

import click
from pathlib import Path
import sys
from typing import Collection

from loguru import logger

from csb_processing import processing_workflow

LOGGER = logger.bind(name="CSB-Processing.CLI")


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
    LOGGER.info(f"Ligne de commande exécutée : {' '.join(sys.argv)}")
    processing_workflow(files=files, vessel_id=vessel_id, output=Path(output))


if __name__ == "__main__":
    cli()
