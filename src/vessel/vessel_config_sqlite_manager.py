"""
Module permettant de gérer la configuration des navires à partir d'une base de données SQLite.

Ce module contient la classe VesselConfigSQLiteManager qui permet de gérer la configuration des navires à partir
d'une base de données SQLite.
"""

from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from .exception_vessel import VesselConfigNotFoundError
from .vessel_config_manager_abc import VesselConfigManagerABC
from .vessel_config import (
    VesselConfig,
    get_vessel_config_from_config_dict,
    VesselConfigDict,
)
from . import vessel_ids as ids

LOGGER = logger.bind(name="CSB-Processing.Vessel.VesselConfigManager.SQLite")


class VesselConfigSQLiteManager(VesselConfigManagerABC):
    """
    Classe permettant de gérer la configuration des navires à partir d'une base de données SQLite.
    """

    def __init__(self, sqlite_config_path: Path | str):
        """
        Initialisation du gestionnaire de configuration des navires à partir d'une base de données SQLite.

        :param sqlite_config_path: Chemin de la base de données SQLite.
        :type sqlite_config_path: Path | str
        """
        super().__init__()
        self.session: Session = self._connect_to_db(
            sqlite_config_path=sqlite_config_path
        )

    @staticmethod
    def _connect_to_db(sqlite_config_path: Path) -> Session:
        """
        Méthode permettant de se connecter à la base de données SQLite.

        :param sqlite_config_path: Chemin de la base de données SQLite.
        :type sqlite_config_path: Path
        :return: Session de la base de données SQLite.
        :rtype: Session
        :raises FileNotFoundError: Le fichier de configuration de la base de données SQLite n'existe pas.
        """
        sqlite_config_path: Path = Path(sqlite_config_path)
        if not sqlite_config_path.is_absolute():
            sqlite_config_path = Path(__file__).parent.parent / sqlite_config_path

        if not sqlite_config_path.exists():
            raise FileNotFoundError(
                f"Le fichier de configuration de la base de données SQLite n'existe pas : {sqlite_config_path}."
            )

        LOGGER.debug(f"Connexion à la base de données SQLite : {sqlite_config_path}.")

        engine: Engine = create_engine(f"sqlite:///{sqlite_config_path}")
        session_maker: sessionmaker = sessionmaker(bind=engine)

        return session_maker()

    def get_vessel_config(self, vessel_id: str) -> VesselConfig:
        """
        Méthode permettant de récupérer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :return: Configuration du navire.
        :rtype: VesselConfig
        """
        raise NotImplementedError

    def get_vessel_configs(self) -> list[VesselConfig]:
        """
        Méthode permettant de récupérer la configuration de tous les navires.

        :return: Configurations des navires.
        :rtype: list[VesselConfig]
        """
        raise NotImplementedError

    def add_veessel_config(self, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant d'ajouter la configuration d'un navire.

        :param vessel_config: Configuration du navire.
        :type vessel_config: VesselConfig
        """
        raise NotImplementedError

    def update_vessel_config(self, vessel_id: str, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant de mettre à jour la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :param vessel_config: Configuration du navire.
        :type vessel_config: Vessel
        """
        raise NotImplementedError

    def delete_vessel_config(self, vessel_id: str) -> None:
        """
        Méthode permettant de supprimer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        """
        raise NotImplementedError

    def commit_vessel_configs(self, **kwargs) -> None:
        """
        Méthode permettant de sauvegarder les configurations des navires.

        :param kwargs: Dictionnaire des paramètres.
        :type kwargs: dict
        """
        raise NotImplementedError
