"""
Module permettant d'importer les modules de l'API de Caris.

Ce module permet d'importer les modules de l'API de Caris. Il permet de valider la version de
Python utilisée et d'ajouter le chemin du module à importer dans le système.
"""

from pathlib import Path
import sys
from types import ModuleType

import i18n
from loguru import logger

from ..model_caris import CarisConfigProtocol

LOGGER = logger.bind(name="CSB-Processing.Caris.Importer")


class VersionError(Exception): ...


class CarisModuleImporter:
    """
    Classe permettant d'importer les modules de lAPI de Caris.
    """

    def __init__(self, config: CarisConfigProtocol) -> None:
        """
        Construteur de la classe.

        :param config: Un objet CarisAPIConfigProtocol.
        :type config: CarisConfigProtocol
        :raise: VersionError si la version de Python ne correspond pas.
        """
        LOGGER.debug(i18n.t("caris_api.import_caris_module.init_importer"))

        self._configuration: CarisConfigProtocol = config
        self.validate_python_version()

        self._python_env: Path = config.python_path

        self._add_environment()
        self._caris: ModuleType = self._import_caris()
        self._coverage: ModuleType = self._import_coverage()
        self._bathy_db: ModuleType = self._import_bathy_db()
        self._delete_environment()

    def validate_python_version(self) -> None:
        """
        Méthode permettant de valider que la version de python utilisée correspond à celle de l'API de Caris.

        :raise: VersionError si la version ne correspond pas.
        """
        LOGGER.debug(i18n.t("caris_api.import_caris_module.validating_python_version"))

        sys_version = f"{str(sys.version_info.major)}.{str(sys.version_info.minor)}"
        if sys_version != str(self._configuration.python_version):
            raise VersionError(
                i18n.t(
                    "caris_api.import_caris_module.version_error",
                    sys_version=sys_version,
                    python_version=self._configuration.python_version,
                )
            )

    def _add_environment(self) -> None:
        """
        Méthode permettant d'ajouter self._python_env des chemins du système.
        """
        LOGGER.debug(
            i18n.t(
                "caris_api.import_caris_module.adding_path", python_env=self._python_env
            )
        )

        sys.path.insert(0, str(self._python_env))

    def _delete_environment(self) -> None:
        """
        Méthode permettant d'enlever self._python_env des chemins du système.
        """
        LOGGER.debug(
            i18n.t(
                "caris_api.import_caris_module.removing_path",
                python_env=self._python_env,
            )
        )

        sys.path.remove(str(self._python_env))

    @staticmethod
    def _import_caris() -> ModuleType:
        """
        Méthode permettant d'importer le module caris.

        :return: Retourne le module caris.
        :rtype: ModuleType
        """
        LOGGER.debug(i18n.t("caris_api.import_caris_module.importing_caris"))

        import caris  # type: ignore

        return caris

    @staticmethod
    def _import_bathy_db() -> ModuleType:
        """
        Méthode permettant d'importer le module caris.bathy.db.

        :return: Retourne le module caris.bathy.db.
        :rtype: ModuleType
        """
        LOGGER.debug(i18n.t("caris_api.import_caris_module.importing_bathy_db"))

        import caris.bathy.db as bathy_db  # type: ignore

        return bathy_db

    @staticmethod
    def _import_coverage() -> ModuleType:
        """
        Méthode permettant d'importer le module caris.coverage.

        :return: Retourne le module caris.coverage.
        :rtype: ModuleType
        """
        LOGGER.debug(i18n.t("caris_api.import_caris_module.importing_coverage"))

        from caris import coverage as coverage  # type: ignore

        return coverage

    @property
    def configuration(self) -> CarisConfigProtocol:
        return self._configuration

    @property
    def caris(self) -> ModuleType:
        return self._caris

    @property
    def bathy_db(self) -> ModuleType:
        return self._bathy_db

    @property
    def coverage(self) -> ModuleType:
        return self._coverage
