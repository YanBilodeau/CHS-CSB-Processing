"""
Ce package contient les classes et fonctions permettant de gérer les stations marégraphiques.
"""

from .exception_stations import StationsError
from .factory_stations import get_stations_factory
from .stations_abc import StationsHandlerABC
from .stations_models import IWLSapiProtocol, TimeSeriesProtocol, EndpointTypeProtocol
from .stations_private import StationsHandlerPrivate
from .stations_public import StationsHandlerPublic

__all__ = [
    "StationsHandlerABC",
    "StationsHandlerPrivate",
    "StationsHandlerPublic",
    "get_stations_factory",
    "StationsError",
    "IWLSapiProtocol",
    "TimeSeriesProtocol",
    "EndpointTypeProtocol",
]
