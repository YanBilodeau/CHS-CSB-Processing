"""
Module permettant d'importer les modules de l'API de Caris.

Ce module permet d'importer les modules de l'API de Caris. Il permet de valider la version de
Python utilisée et d'ajouter le chemin du module à importer dans le système.
"""

from abc import ABC, abstractmethod
from enum import Enum
from importlib import util, import_module
import os
from pathlib import Path
import sys
from typing import Any, Protocol

Module = Any

BATHY: str = "bathy"
CARIS: str = "caris"
COVERAGE: str = "coverage"
DB: str = "db"
INIT: str = "__init__.py"
PYTHON: str = "python"
PYTHON_PATH: str = "Python_path"


class CarisAPIConfigProtocol(Protocol):
    base_path: str
    software: str
    version: float
    python_version: float
    python_path: Path


class VersionError(Exception): ...


def import_lib_from_file(module_name: str, module_path: str) -> Module:
    """
    Méthode permettant d'importer un module à partir d'un fichier et de ses spécifications.

    :param module_name: Le nom du module
    :type module_name: str
    :param module_path: Le chemin du module.
    :type module_path: str
    :return: Un module chargé à partir d'un fichier.
    :rtype: Module
    :raise: ImportError si le module n'est pas importé.
    """
    try:
        spec = util.spec_from_file_location(module_name, module_path)
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return import_module(module_name)

    except ImportError:
        raise sys.exit(f"Erreur à l'importation du module '{module_name}'.")


class CarisModule(Enum):
    CARIS: Module = "caris"
    BATHY_DB: Module = "caris.bathy.db"
    COVERAGE: Module = "caris.coverage"


class CarisModuleImporterAbstract(ABC):
    @property
    @abstractmethod
    def configuration(self) -> CarisAPIConfigProtocol: ...

    @property
    @abstractmethod
    def caris(self) -> CarisModule: ...

    @property
    @abstractmethod
    def bathy_db(self) -> CarisModule: ...

    @property
    @abstractmethod
    def coverage(self) -> CarisModule: ...


class CarisModuleImporter(CarisModuleImporterAbstract):
    """
    Classe permettant d'importer les modules de lAPI de Caris.
    """

    def __init__(self, config: CarisAPIConfigProtocol) -> None:
        """
        Construteur de la classe.

        :param config: Un objet CarisAPIConfig.
        :type config: CarisAPIConfig
        :raise: VersionError si la version de Python ne correspond pas.
        """
        self._configuration: CarisAPIConfigProtocol = config
        self.validate_python_version()

        self._python_env: Path = config.python_path

        self._caris = self._import_caris()
        self._bathy_db = self._import_bathy_db()
        self._coverage = self._import_coverage()

    def validate_python_version(self) -> None:
        """
        Méthode permettant de valider que la version de python utilisée correspond avec celle de l'API de Caris.

        :raise: VersionError si la version ne correspond pas.
        """
        sys_version = f"{str(sys.version_info.major)}.{str(sys.version_info.minor)}"
        if sys_version != str(self._configuration.python_version):
            raise VersionError(
                f"La version système de Python ({sys_version}) doit correspondre avec la version de l'API de "
                f"Caris {self._configuration.python_version}."
            )

    def _add_environment(self) -> None:
        """
        Méthode permettant d'ajouter self._python_env des chemins du système.
        """
        sys.path.insert(0, str(self._python_env))

    def _delete_environment(self) -> None:
        """
        Méthode permettant d'enlever self._python_env des chemins du système.
        """
        sys.path.remove(str(self._python_env))

    def _import_module_wrapper(self, module: CarisModule, module_path: str) -> Module:
        """
        Méthode permettant d'importer un module.

        :param module: Un objet CarisModule.
        :type module: CarisModule
        :param module_path:Le chemin du fichier du module.
        :type module_path: str
        :return: Retourne le module importé.
        :rtype: CarisModule
        :raise: ImportError si le module n'est pas importé.
        """
        self._add_environment()
        module: Module = import_lib_from_file(module.value, module_path)
        self._delete_environment()

        return module

    def _import_caris(self) -> Module:
        """
        Méthode permettant d'importer le module caris.

        :return: Retourne le module caris.
        :rtype: Module
        """
        return self._import_module_wrapper(
            CarisModule.CARIS, os.path.join(self._python_env, CARIS, INIT)
        )

    def _import_bathy_db(self) -> Module:
        """
        Méthode permettant d'importer le module caris.bathy.db.

        :return: Retourne le module caris.bathy.db.
        :rtype: Module
        """
        return self._import_module_wrapper(
            CarisModule.BATHY_DB,
            os.path.join(self._python_env, CARIS, BATHY, DB, INIT),
        )

    def _import_coverage(self) -> Module:
        """
        Méthode permettant d'importer le module caris.coverage.

        :return: Retourne le module caris.coverage.
        :rtype: Module
        """
        return self._import_module_wrapper(
            CarisModule.COVERAGE,
            os.path.join(self._python_env, CARIS, COVERAGE, INIT),
        )

    @property
    def configuration(self) -> CarisAPIConfigProtocol:
        return self._configuration

    @property
    def caris(self) -> Module:
        return self._caris

    @property
    def bathy_db(self) -> Module:
        return self._bathy_db

    @property
    def coverage(self) -> Module:
        return self._coverage
