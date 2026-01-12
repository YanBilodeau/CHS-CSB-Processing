"""
Ce module contient la fonction principale de la ligne de commande.

Il permet de traiter des fichiers de données bathymétriques et de les géoréférencer.
"""

import click
from pathlib import Path
import sys
from typing import Collection, Optional

from loguru import logger

from config import FileTypes
import converter
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
    extension = file.suffix.lower()

    # Vérifier les extensions connues
    if extension in {".csv", ".txt", ".xyz", ".geojson"}:
        return True

    # Vérifier si l'extension est un nombre (ex: .1, .2, .3)
    if extension.startswith(".") and extension[1:].isdigit():
        return True

    return False


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


@click.group()
def cli_group():
    """
    Groupe de commandes pour le traitement des données bathymétriques.
    """
    pass


@cli_group.command(name="process")
@click.argument(
    "files",
    type=click.Path(exists=True),
    required=True,
    nargs=-1,
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
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
    avec des bras de levier à 0 sera utilisé. Cette option ne peut pas être utilisé conjointement avec --waterline.\n
    Vessel identifier. If no vessel identifier is used, a default vessel with lever arms at 0 will be used.
    This option cannot be used together with --waterline.
    """,
)
@click.option(
    "--waterline",
    type=float,
    required=False,
    help="""
    Ligne de flottaison du navire. Cette mesure correspond à la distance entre le sondeur et la surface de 
    l'eau (mesure verticale). Si aucune ligne de flottaison n'est fournie, une valeur de 0 sera utilisée.
    Cette option ne peut pas être utilisée conjointement avec --vessel.\n
    Waterline of the vessel. This measurement corresponds to the distance between the sounder and the surface of
    the water (vertical measurement). If no waterline is provided, a value of 0 will be used.
    This option cannot be used together with --vessel.
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
    la réduction des niveaux d'eau est appliqué.\n
    Apply the water level reduction when georeferencing the soundings. 
    By default, the water level reduction is applied.
    """,
)
@click.option(
    "--water-level-stations",
    type=str,
    multiple=True,
    required=False,
    help="""
    Code(s) des stations marégraphiques à utiliser pour le traitement. Si une station est spécifiée, 
    seulement cette station sera utilisée. (https://egisp.dfo-mpo.gc.ca/apps/tides-stations-marees/?locale=fr)\n
    Water level station code(s) to use for processing. If a station is specified, only that station will be used.
     (https://egisp.dfo-mpo.gc.ca/apps/tides-stations-marees/?locale=en)
    """,
)
@click.option(
    "--excluded-stations",
    type=str,
    multiple=True,
    required=False,
    help="""
    Code(s) des stations marégraphiques à exclure du traitement. Peut être spécifié plusieurs fois pour exclure 
    plusieurs stations.\n
    Water level station code(s) to exclude from processing. Can be specified multiple times to exclude 
    multiple stations.
    """,
)
def process_bathymetric_data(
    files: Collection[Path],
    output: Path,
    vessel: Optional[str],
    waterline: Optional[float],
    config: Optional[Path],
    apply_water_level: Optional[bool] = True,
    water_level_stations: Optional[tuple[str, ...]] = None,
    excluded_stations: Optional[tuple[str, ...]] = None,
) -> None:
    """
    Traite les fichiers de données bathymétriques et les géoréférence. Processes bathymetric data files and georeferences them.

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
    :param water_level_stations: Stations de niveau d'eau à utiliser pour le traitement.
    :type water_level_stations: Optional[tuple[str, ...]]
    :param excluded_stations: Stations de niveau d'eau à exclure du traitement.
    :type excluded_stations: Optional[tuple[str, ...]]
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
        water_level_stations=(
            list(water_level_stations) if water_level_stations else None
        ),
        excluded_stations=list(excluded_stations) if excluded_stations else None,
    )


@cli_group.command(name="convert")
@click.argument(
    "input_files",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    nargs=-1,
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="""
    Chemin du répertoire de sortie.\n
    Path of the output directory.
    """,
)
@click.option(
    "--format",
    "file_formats",
    type=click.Choice([ft.value for ft in FileTypes], case_sensitive=False),
    multiple=True,
    required=True,
    help="""
    Format(s) de sortie désirés. Peut être spécifié plusieurs fois pour exporter vers plusieurs formats.\n
    Desired output format(s). Can be specified multiple times to export to multiple formats.
    """,
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    help="""
    Chemin du fichier de configuration. Si aucun fichier de configuration n'est fourni, le fichier de configuration
    par défaut sera utilisé.\n
    Path of the configuration file. If no configuration file is provided, the default configuration file will be used.
    """,
)
@click.option(
    "--group-by-iho-order",
    type=bool,
    default=False,
    help="""
    Regrouper les données par ordre IHO lors de l'exportation.\n
    Group data by IHO order during export.
    """,
)
def convert_gpkg(
    input_files: Collection[Path],
    output: Path,
    file_formats: Collection[str],
    config: Optional[Path],
    group_by_iho_order: Optional[bool],
) -> None:
    """
    Convertit des fichiers GPKG/GeoJSON vers différents formats. Convert GPKG/GeoJSON files to different formats.

    :param input_files: Chemins des fichiers GPKG/GeoJSON d'entrée.
    :type input_files: Collection[Path]
    :param output: Chemin du répertoire de sortie.
    :type output: Path
    :param file_formats: Formats de sortie désirés.
    :type file_formats: Collection[str]
    :param config: Chemin du fichier de configuration.
    :type config: Optional[Path]
    :param group_by_iho_order: Regrouper par ordre IHO.
    :type group_by_iho_order: bool
    :raise click.UsageError: Si aucun fichier valide n'est fourni.
    """
    configure_logger()
    LOGGER.info(f"Ligne de commande exécutée : python {' '.join(sys.argv)}")

    # Filtrer les fichiers valides
    valid_files = [
        file for file in input_files if file.suffix.lower() in {".gpkg", ".geojson"}
    ]

    if not valid_files:
        LOGGER.error("Aucun fichier GPKG ou GeoJSON valide trouvé.")
        raise click.UsageError(
            "Aucun fichier GPKG ou GeoJSON valide trouvé.\n"
            "No valid GPKG or GeoJSON file found."
        )

    # Convertir les formats string en enum
    file_types = [FileTypes(fmt) for fmt in file_formats]

    # Utiliser le fichier de configuration par défaut si non spécifié
    if not config:
        LOGGER.warning(
            "Aucun fichier de configuration n'a été fourni. Le fichier de configuration par défaut sera utilisé."
        )
        config = CONFIG_FILE

    LOGGER.info(
        f"Conversion de {len(valid_files)} fichier{'s' if len(valid_files) > 1 else ''} : "
        f"{', '.join(str(path) for path in [valid_files])}"
    )
    LOGGER.info(f"Vers les formats : {file_formats}")
    LOGGER.info(f"Répertoire de sortie : {output}")

    converter.convert_files_to_formats(
        input_files=valid_files,
        output_path=output,
        file_types=file_types,
        config_path=config,
        group_by_iho_order=group_by_iho_order,
    )


if __name__ == "__main__":
    cli_group()
