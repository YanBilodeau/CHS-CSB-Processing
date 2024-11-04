from loguru import logger

from .stations_abc import StationsHandlerABC
from .stations_models import EndpointTypeProtocol
from .stations_private import StationsHandlerPrivate
from .stations_public import StationsHandlerPublic

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Factory")


STATIONS_FACTORY: dict[EndpointTypeProtocol, type[StationsHandlerABC]] = {
    EndpointTypeProtocol.PUBLIC: StationsHandlerPublic,
    EndpointTypeProtocol.PRIVATE_PROD: StationsHandlerPrivate,
    EndpointTypeProtocol.PRIVATE_DEV: StationsHandlerPrivate,
}


def get_stations_factory(
    enpoint_type: EndpointTypeProtocol,
) -> type[StationsHandlerABC]:
    LOGGER.debug(
        f"Récupération de la factory de stations pour le endpoint '{enpoint_type}'."
    )

    return STATIONS_FACTORY.get(enpoint_type)
