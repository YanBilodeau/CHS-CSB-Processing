"""
Module de gestion de l'exportation de données vers un fichier CSAR avec Caris Batch.

Ce module contient les fonctions permettant d'exporter des données vers un fichier CSAR avec Caris Batch.
"""

from pathlib import Path

from loguru import logger

from ..model_caris import CarisConfigProtocol
from .response import CarisBatchResponse
from .batch_processor import make_command_line, run_command_line

LOGGER = logger.bind(name="CSB-Processing.Caris.Batch.ExportCSAR")


INFO_FILE_PATH: Path = Path(__file__).parent / "csb.info"
EPSG_WGS84: str = "EPSG:4326"


def export_geodataframe_to_csar(
    data: Path, output_path: Path, config: CarisConfigProtocol
) -> None:
    """
    Exporte un Geodataframe vers un fichier CSAR.

    :param data: Le fichier *.csv contenant les données à exporter.
    :type data: Path
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param config: La configuration de Caris.
    :type config: CarisConfigProtocol
    """
    command: list[str] = make_command_line(
        caris_batch_environment=config.caris_batch,
        process="ImportPoints",
        options=[
            "--input-format",
            "ASCII",
            "--primary-band",
            "Depth",
            "--input-crs",
            EPSG_WGS84,
            "--output-crs",
            EPSG_WGS84,
            "--include-band",
            "Uncertainty",
            "--include-band",
            "DepthRaw",
            "--include-band",
            "WaterLevelInfo",
            "--include-band",
            "THU",
            "--include-band",
            "IHO Order",
            "--info-file",
            INFO_FILE_PATH,
            # "--output-vertical-crs",
            # "PACD",
        ],
        source=[str(data)],
        destination=[str(output_path)],
    )

    LOGGER.debug(f"Commande Caris Batch : {command}.")

    response: CarisBatchResponse = run_command_line(command)

    LOGGER.debug(f"Réponse Caris Batch : {response}.")

    if not response.is_ok:
        LOGGER.error(
            f"Erreur lors de l'exportation du fichier '{data}' vers '{output_path}'."
        )
        LOGGER.error(f"Message d'erreur : {response.stderr}.")
