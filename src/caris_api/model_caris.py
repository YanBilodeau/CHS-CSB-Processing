"""
Module définissant les modèles de données pour Caris.
"""

from pathlib import Path
from typing import Protocol


class CarisConfigProtocol(Protocol):
    base_path: str
    software: str
    version: str
    python_version: str
    python_path: Path
    caris_batch: Path
