"""
Module qui contient les fonctions permettant de construire et d'exécuter des commandes Caris Batch.

Ce module contient les fonctions qui permettent de construire une ligne de commande Caris Batch et de les exécuter.
"""

from pathlib import Path
import subprocess
from typing import Optional

from loguru import logger

from . import ids_batch as ids
from .response import CarisBatchResponse

Command = list[str]

LOGGER = logger.bind(name="CSB-Processing.Caris.Batch.Processor")


def make_command_line(
    caris_batch_environment: Path,
    process: Optional[str],
    options: Optional[list[str]] = None,
    source: Optional[list[str]] = None,
    destination: Optional[list[str]] = None,
    write_log: bool = False,
) -> Command:
    """
    Méthode qui construit une ligne de commande Caris Batch.

    :param caris_batch_environment: Le chemin de l'environnement de Caris Batch.
    :type caris_batch_environment: Path
    :param process: Le nom du processus.
    :type process: str
    :param options: Les options du processus.
    :type options: Optional[List[str]]
    :param source: Les fichiers sources.
    :type source: Optional[List[str]]
    :param destination: La destination.
    :type destination: Optional[List[str]]
    :param write_log: True pour écrire dans le log de Caris, False sinon.
    :type write_log: bool
    :return: Une commande Caris Batch prête à être exécutée.
    :rtype: Command
    """
    LOGGER.debug("Construction de la ligne de commande Caris Batch.")

    destination_list = destination or []
    source_list = source or []
    options = options or []
    run = [ids.RUN, process]
    log = [ids.WRITE_LOG] if write_log else []

    return (
        [str(caris_batch_environment)]
        + run
        + options
        + source_list
        + destination_list
        + log
    )


def run_command_line(command: Command) -> CarisBatchResponse:
    """
    Méthode qui exécute une commande Caris Batch.

    :param command: La commande à exécuter.
    :type command: Command
    :return: Un objet CarisBatchResponse.
    :rtype: CarisBatchResponse
    """
    LOGGER.debug(f"Exécution de la commande Caris Batch.")

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    out, err = process.communicate()

    stdout = _format_std(out)
    stderr = _format_std(err)

    return CarisBatchResponse(stdout=stdout, stderr=stderr)


def _format_std(std: bytes, codec: str = ids.LATIN) -> list[str]:
    """
    Méthode permettant de décoder un objet bytes et de retourner une liste de chaînes de caractères.

    :param std: Un objet bytes représentant le stdout ou le stderr.
    :type std: bytes
    :param codec: L'encodage à utiliser.
    :type codec: str
    :return: Une liste de chaînes de caractères représentant le stdout ou le stderr.
    :rtype: list[str]
    """
    std = std.decode(codec).split(ids.NEW_LINE)
    return [line for line in std if line != ids.EMPTY_STRING]
