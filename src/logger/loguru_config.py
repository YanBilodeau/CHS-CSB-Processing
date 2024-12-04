import sys
from collections import defaultdict
from os import getlogin
from pathlib import Path
from random import choice, seed
from socket import gethostname
from threading import Lock

from loguru import logger

from .ids_logger import LOG_FORMAT

seed(6)
lock: Lock = Lock()

COLORS: tuple[str, ...] = (
    "blue",
    "light-blue",
    "cyan",
    "light-cyan",
    "green",
    "light-green",
    "magenta",
    "light-magenta",
    "yellow",
    "light-yellow",
    "red",
    "light-red",
    "white",
    "light-white",
)

COLORS_DICT: defaultdict[str, str] = defaultdict(lambda: choice(COLORS))


def formatter(record) -> str:
    with lock:
        color_tag = COLORS_DICT[record["extra"]["name"]]

    return (
        "<bold><white>"
        f"<{color_tag}>"
        "{extra[name]: <35}"
        f"</{color_tag}> | "
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | </white></bold> "
        "<level>{level: ^8}</level> <bold><white>-</white></bold> <level>{message}</level>\n"
        "<level>{exception}</level>"
    )


def configure_logger(
    log_file: Path,
    std_level: str = "INFO",
    log_file_level: str = "TRACE",
    rotation: str | int = "1 day",
    retention: str | int = "30 days",
    enqueue: bool = True,
) -> None:
    logger.remove()

    handlers = [
        dict(
            sink=sys.stderr,
            backtrace=True,
            diagnose=True,
            format=formatter,
            level=std_level,
            enqueue=enqueue,
        ),
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
        extra={"name": "SHCoutils", "hostname": gethostname(), "username": getlogin()},
    )
