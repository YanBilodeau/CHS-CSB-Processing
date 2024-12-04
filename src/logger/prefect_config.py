from os import getlogin
from pathlib import Path
from socket import gethostname
from typing import Optional

from loguru import logger
from prefect import get_run_logger

from .ids_logger import LOG_FORMAT

FORMAT = "{extra[name]} | {name}:{module}:{function}:{line}:{extra[hostname]}:{extra[username]} - {message}"


def formatter(_) -> str:
    return FORMAT.strip()


def configure_prefect_logger(
    log_file: Optional[Path] = None,
    rotation: str | int = "1 day",
    retention: str | int = "30 days",
    log_file_level: str = "TRACE",
    enqueue: bool = True,
) -> None:
    """
    Fonction de configuration du logger pour Prefect.

    :param log_file: Chemin du fichier de log.
    :type log_file: Optional[Path]
    :param log_file_level: Niveau de log pour le fichier de log.
    :type log_file_level: str
    :param rotation: Durée de rotation des fichiers de log.
    :type rotation: str | int
    :param retention: Durée de rétention des fichiers de log.
    :type retention: str | int
    :param enqueue: Indique si les messages doivent être enfilés.
    :type enqueue: bool
    """
    logger.remove()
    prefect_logger = get_run_logger()

    prefect_logger.debug("Ajout du soutien de Loguru dans Prefect.")

    handlers = [
        {
            "sink": prefect_logger.debug,
            "filter": lambda record: record["level"].name in ["DEBUG", "TRACE"],
            "level": "TRACE",
            "format": formatter,
        },
        {
            "sink": prefect_logger.warning,
            "filter": lambda record: record["level"].name == "WARNING",
            "level": "TRACE",
            "format": formatter,
        },
        {
            "sink": prefect_logger.error,
            "filter": lambda record: record["level"].name == "ERROR",
            "level": "TRACE",
            "format": formatter,
        },
        {
            "sink": prefect_logger.critical,
            "filter": lambda record: record["level"].name == "CRITICAL",
            "level": "TRACE",
            "format": formatter,
        },
        {
            "sink": prefect_logger.info,
            "filter": lambda record: record["level"].name
            not in ["TRACE", "DEBUG", "WARNING", "ERROR", "CRITICAL"],
            "level": "TRACE",
            "format": formatter,
        },
    ]

    if log_file:
        handlers.append(
            dict(
                sink=log_file,
                backtrace=True,
                diagnose=True,
                format=LOG_FORMAT,
                level=log_file_level,
                rotation=rotation,
                retention=retention,
                enqueue=enqueue,
            )
        )

    logger.configure(
        handlers=handlers,
        extra={
            "name": "CSB-Processing",
            "hostname": gethostname(),
            "username": getlogin(),
        },
    )
