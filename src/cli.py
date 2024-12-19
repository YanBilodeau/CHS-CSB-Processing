"""
Ce module contient la fonction principale de la ligne de commande.

Il permet de traiter des fichiers de données bathymétriques et de les géoréférencer.
"""

import click
from pathlib import Path
import sys
from typing import Collection, Optional

from loguru import logger

from csb_processing import processing_workflow, CONFIG_FILE
from logger.loguru_config import configure_logger
from vessel import UNKNOWN_VESSEL_CONFIG, UNKNOWN_DATE, Waterline

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
@click.argument(
    "files",
    type=click.Path(exists=True),
    required=True,
    nargs=-1,
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
    avec des bras de levier à 0 sera utilisé. Cet option ne peut pas être utilisé conjointement avec --waterline\n
    Vessel identifier. If no vessel identifier is used, a default vessel with lever arms at 0 will be used.
    """,
)
@click.option(
    "--waterline",
    type=float,
    required=False,
    help="""
    Ligne de flottaison du navire. Cette mesure correspond à la distance entre le sondeur et la surface de 
    l'eau (mesure verticale). Si aucune ligne de flottaison n'est fournie, une valeur de 0 sera utilisée.
    \n
    Waterline of the vessel. This measurement corresponds to the distance between the sounder and the surface of
    the water (vertical measurement). If no waterline is provided, a value of 0 will be used.
    """,
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=False,
    help="""
    Chemin du fichier de configuration. si aucun fichier de configuration n'est fourni, le fichier de configuration
    par défaut sera utilisé.\n
    Path of the configuration file. If no configuration file is provided, the default configuration file will be used.
    """,
)
@click.option(
    "--apply-water-level",
    type=bool,
    required=False,
    default=True,
    help="""
    Appliquer la réduction des niveaux d'eau lors du géoréférencement des sondes. Par défaut, 
    la réduction des niveaux d'eau est appliqués.\n
    Apply the water level reduction when georeferencing the soundings. 
    By default, the water level reduction is applied.
    """,
)
def cli(
    files: Collection[Path],
    output: Path,
    vessel: Optional[str],
    waterline: Optional[float],
    config: Optional[Path],
    apply_water_level: Optional[bool] = True,
) -> None:
    """
    Fonction principale de la ligne de commande.

    :param files: Chemins des fichiers ou répertoires à traiter.
    :type files: Collection[Path]
    :param output: Chemin du répertoire de sortie.
    :type output: Path
    :param vessel: Identifiant du navire.
    :type vessel: Optional[str]
    :param waterline: La mesure de la ligne de flottaison. Distance verticale entre le sondeur et la surface de l'eau.
    :type waterline: Optional[float]
    :param config: Chemin du fichier de configuration.
    :type config: Optional[Path]
    :param apply_water_level: Appliquer la réduction des nivaeux d'eau lors du géoréférencement des sondes.
    :type apply_water_level: Optional[bool]
    :raise click.UsageError: Si les options --vessel et --waterline sont utilisées en même temps.
    :raise click.UsageError: Si la valeur de l'option --waterline est négative.
    :raise click.UsageError: Si aucun fichier valide n'est fourni.
    """
    configure_logger()
    LOGGER.info(f"Ligne de commande exécutée : python {' '.join(sys.argv)}")

    if vessel and waterline is not None:
        raise click.UsageError(
            "Vous ne pouvez utiliser que l'option --vessel ou --waterline, pas les deux en même temps.\n"
            "You can only use the --vessel or --waterline option, not both at the same time."
        )

    if waterline is not None and waterline < 0:
        raise click.UsageError(
            "La valeur de l'option --waterline doit être positive.\n"
            "The value of the --waterline option must be positive."
        )

    # Get the files to parse
    files: list[Path] = get_files(files)

    # Check if there are files to process
    if not files:
        LOGGER.error("Aucun fichier valide à traiter.")
        raise click.UsageError(
            "Aucun fichier valide à traiter.\nNo valid file to process."
        )

    if not vessel and waterline is None:
        LOGGER.warning(
            "Aucun identifiant de navire n'a été fourni. Un navire par défaut sera utilisé."
        )
        vessel = UNKNOWN_VESSEL_CONFIG

    if waterline is not None:
        LOGGER.info(f"Ligne de flottaison fournie : {waterline}.")
        UNKNOWN_VESSEL_CONFIG.waterline = [
            Waterline(time_stamp=UNKNOWN_DATE, z=-waterline)
        ]
        vessel = UNKNOWN_VESSEL_CONFIG

    if not config:
        LOGGER.warning(
            "Aucun fichier de configuration n'a été fourni. Le fichier de configuration par défaut sera utilisé."
        )
        config = CONFIG_FILE

    processing_workflow(
        files=files,
        vessel=vessel,
        output=Path(output),
        config_path=Path(config),
        apply_water_level=apply_water_level,
    )


if __name__ == "__main__":
    cli()
