from enum import StrEnum
from typing import Optional

from loguru import logger

from .api.endpoint import Endpoint, EndpointType
from .api.iwls_api_abc import IWLSapiABC
from .api.iwls_private import IWLSapiPrivate
from .api.iwls_public import IWLSapiPublic
from .handler.http_query_handler import (
    RateLimiterHandler,
    get_retry_adapter,
    RequestsHandler,
    CachedSessionConfig,
    SessionType,
)
from .handler.models_handler import RetryAdapterConfig

LOGGER = logger.bind(name="IWLS.API.APIFacade")


class EnvironmentType(StrEnum):
    DEV: str = "dev"
    PROD: str = "prod"
    PUBLIC: str = "public"


class HandlerType(StrEnum):
    RATE_LIMITER: str = "rate_limiter"
    REQUESTS: str = "request"


API_FACTORY: dict[EndpointType, type[IWLSapiABC]] = {
    EndpointType.PRIVATE_DEV: IWLSapiPrivate,
    EndpointType.PRIVATE_PROD: IWLSapiPrivate,
    EndpointType.PUBLIC: IWLSapiPublic,
}


def get_api_factory(endpoint: EndpointType) -> type[IWLSapiABC]:
    """
    Retournes la classe de l'API IWLS en fonction du profil.

    :param endpoint: (Endpoint) L'endpoint de l'API IWLS.
    :return: (type[IWLSapi]) La classe de l'API IWLS.
    :return: La classe de l'API IWLS.
    :rtype: type[IWLSapiABC]
    """
    LOGGER.debug(f"Initialisation de l'API IWLS pour le l'endpoint : '{endpoint}'.")

    return API_FACTORY.get(endpoint)


def _configure_session_type(
    session_type_config: SessionType | CachedSessionConfig,
) -> tuple[SessionType, CachedSessionConfig | None]:
    """
    Fonction qui configure le type de session en fonction de la configuration.

    :param session_type_config: (SessionType | CachedSessionConfig) Le type de session ou la configuration pour la cache.
    :return: (tuple[SessionType, CachedSessionConfig | None]) Le type de session et la configuration pour la cache.
    """
    if isinstance(session_type_config, CachedSessionConfig):
        return SessionType.CACHE, session_type_config

    return session_type_config, None


def _get_handler(
    handler_type: HandlerType,
    calls: int,
    period: int,
    session_type_config: SessionType | CachedSessionConfig,
) -> RequestsHandler:
    """
    Fonction qui retourne un gestionnaire de requêtes en fonction du type de gestionnaire.

    :param handler_type: (HandlerType) Le type de gestionnaire de requêtes.
    :param calls: (int) Le nombre de requêtes autorisées (nécessaire pour 'HandlerType.RATE_LIMITER).
    :param period: (int) La période de temps pour les requêtes autorisées (nécessaire pour HandlerType.RATE_LIMITER).
    :param session_type_config: (SessionType | CachedSessionConfig) Le type de session ou la configuration pour la cache.
    :return: (RequestsHandler) Le gestionnaire de requêtes.
    """
    session_type, cache_config = _configure_session_type(
        session_type_config=session_type_config
    )

    handler_factory = {
        HandlerType.RATE_LIMITER: lambda: RateLimiterHandler(
            session_type=session_type,
            calls=calls,
            period=period,
            cache_config=cache_config,
        ),
        HandlerType.REQUESTS: lambda: RequestsHandler(
            session_type=session_type, cache_config=cache_config
        ),
    }

    return handler_factory.get(handler_type)()


def _mount_retry_adapter(
    handler: RequestsHandler, retry_adapter_config: RetryAdapterConfig | bool
):
    """
    Fonction qui monte un adaptateur de réessai sur le gestionnaire de requêtes.

    :param handler: (RequestsHandler) Le gestionnaire de requêtes.
    :param retry_adapter_config: (RetryAdapterConfig | bool) La configuration pour l'adaptateur de réessai ou un booléen.
                                            Si True, une configuration par défaut est utilisé, si False, aucun
                                            adaptateur est utilisé.
    :return: (None)
    """
    if retry_adapter_config:
        config = (
            retry_adapter_config.__dict__
            if isinstance(retry_adapter_config, RetryAdapterConfig)
            else {}
        )
        handler.mount_adapter(get_retry_adapter(**config))


def get_iwls_api(
    endpoint: Endpoint,
    handler_type: Optional[HandlerType] = HandlerType.RATE_LIMITER,
    calls: Optional[int] = 10,
    period: Optional[int] = 1,
    session_type_config: Optional[
        SessionType | CachedSessionConfig
    ] = SessionType.REQUESTS,
    retry_adapter_config: Optional[RetryAdapterConfig | bool] = True,
) -> IWLSapiABC | IWLSapiPrivate | IWLSapiPublic:
    """
    Fonction qui retourne l'API IWLS.

    :param endpoint: (Endpoint) L'endpoint de l'API IWLS.
    :param handler_type: (HandlerType) Le type de gestionnaire de requêtes.
    :param calls: (int) Le nombre de requêtes autorisées (nécessaire pour 'HandlerType.RATE_LIMITER).
    :param period: (int) La période de temps pour les requêtes autorisées (nécessaire pour HandlerType.RATE_LIMITER).
    :param session_type_config: (SessionType) Le type de session ou la configuration pour la cache. Si une configuration
                                            est fourni, le session_type est alors automatiquement SessionType.CACHE.
    :param retry_adapter_config: (RetryAdapterConfig | bool) La configuration pour l'adaptateur de réessai ou un booléen.
                                            Si True, une configuration par défaut est utilisé, si False, aucun
                                            adaptateur est utilisé.
    :return: (IWLSapi) L'API IWLS.
    """
    with _get_handler(
        handler_type=handler_type,
        calls=calls,
        period=period,
        session_type_config=session_type_config,
    ) as handler:
        _mount_retry_adapter(
            handler=handler, retry_adapter_config=retry_adapter_config
        )  # Seulement si un RequestsHandler

        return get_api_factory(endpoint=endpoint.TYPE)(
            query_handler=handler, endpoint=endpoint
        )
