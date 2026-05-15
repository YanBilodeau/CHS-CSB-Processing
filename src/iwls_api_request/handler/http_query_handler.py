from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Collection

import i18n
import pytz
import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore
from requests_cache import CachedSession

from .models_handler import (
    Response,
    ResponseType,
    SessionType,
    Rate,
    CachedSessionConfig,
)
from .rate_limiter import RateLimiter

LOGGER = logger.bind(name="IWLS.API.HTTPQueryHandler")


class HTTPQueryHandler(ABC):
    __slots__ = "_session"

    def __init__(self, session=None, **kwargs) -> None:
        self._session = session

        LOGGER.debug(
            i18n.t(
                "iwls_api_request.http_query_handler.handler_initialized",
                handler_type=type(self).__name__,
            )
        )

    @abstractmethod
    def query(
        self,
        url: str,
        params: Optional[dict] = None,
        response_type: ResponseType = ResponseType.JSON,
    ) -> Response:
        """
        Méthode permettant d'effectuer la requête http.

        :param url: (str) Une chaîne de caractères correspondant à l'adresse url.
        :param params: (dict) Un dictionnaire avec les paramètres de la requête.
        :param response_type: (ResponseType) Un objet ResponseType.
        :return: (Response) La réponse de la requête http.
        """


class RequestsHandler(HTTPQueryHandler):
    __slots__ = "_session", "_session_type", "_cache_config"

    def __init__(
        self,
        session=None,
        session_type: SessionType = SessionType.REQUESTS,
        cache_config: Optional[CachedSessionConfig] = None,
        **kwargs,
    ) -> None:
        self._session_type = session_type
        self._cache_config = cache_config or CachedSessionConfig()
        super().__init__(session=session, **kwargs)

    def __enter__(self):
        LOGGER.debug(
            i18n.t(
                "iwls_api_request.http_query_handler.session_type_retrieval",
                session_type=self._session_type,
            )
        )

        self._session = get_session(
            session_type=self._session_type, cache_config=self._cache_config
        )

        LOGGER.debug(
            i18n.t(
                "iwls_api_request.http_query_handler.session_opened",
                session=self._session,
            )
        )

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        self._session.close()

    def query(
        self,
        url: str,
        params: Optional[dict] = None,
        response_type: ResponseType = ResponseType.JSON,
    ) -> Response:
        """
        Méthode permettant d'effectuer la requête http.

        :param url: (str) Une chaîne de caractères correspondant à l'adresse url.
        :param params: (dict) Un dictionnaire avec les paramètres de la requête.
        :param response_type: (ResponseType) Un objet ResponseType.
        :return: (Response) La réponse de la requête http.
        """

        def get_cache_status(response_) -> str:
            return (
                f"from CachedSession (expires at {response.expires.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}"
                if getattr(response_, "from_cache", False)
                else "not from CachedSession"
            )

        try:
            with self._session.get(url, params=params) as response:
                response_data = Response(status_code=response.status_code)

                if response.ok:
                    if response_type == ResponseType.JSON:
                        response_data.data = response.json()

                    elif response_type == ResponseType.TEXT:
                        response_data.data = response.text

                    LOGGER.info(
                        i18n.t(
                            "iwls_api_request.http_query_handler.request_success",
                            status_code=response.status_code,
                            url=response.url,
                        )
                    )
                    return response_data

                if response.headers["Content-Type"] == "application/json":
                    response_data.error = response.json().get(
                        "code"
                    ) or response.json().get("errors")
                    response_data.message = response.json().get(
                        "message", "Unknown error"
                    )

                LOGGER.warning(
                    i18n.t(
                        "iwls_api_request.http_query_handler.request_warning",
                        status_code=response.status_code,
                        error=response_data.error,
                        message=response_data.message,
                        url=response.url,
                    )
                )
                return response_data

        except requests.exceptions.ConnectionError as e:
            LOGGER.error(i18n.t("iwls_api_request.http_query_handler.connection_error"))
            LOGGER.exception(e)

        except requests.exceptions.Timeout as e:
            LOGGER.error(i18n.t("iwls_api_request.http_query_handler.timeout_error"))
            LOGGER.exception(e)

        except requests.exceptions.TooManyRedirects as e:
            LOGGER.error(
                i18n.t(
                    "iwls_api_request.http_query_handler.too_many_redirects", url=url
                )
            )
            LOGGER.exception(e)

        except requests.exceptions.RequestException as e:
            LOGGER.error(i18n.t("iwls_api_request.http_query_handler.request_error"))
            LOGGER.exception(e)

        except Exception as e:
            LOGGER.error(i18n.t("iwls_api_request.http_query_handler.unexpected_error"))
            LOGGER.exception(e)

    def mount_adapter(
        self, adapter: HTTPAdapter, prefix: Optional[list[str]] = None
    ) -> None:
        """
        Méthode permettant de monter un adaptateur pour certains urls.

        :param adapter: (HTTPAdapter) Un adaptateur.
        :param prefix: (List[str]) Une liste de préfixe de urls sur lesquels monter l'adaptateur.
        """
        LOGGER.debug(
            i18n.t(
                "iwls_api_request.http_query_handler.adapter_mounted",
                adapter=adapter.__dict__,
            )
        )

        prefix = ["https://", "http://"] if prefix is None else prefix
        for pre in prefix:
            self._session.mount(pre, adapter)

    def clear_cache(self) -> None:
        """
        Méthode permettant de nettoyer la cache.
        """
        LOGGER.debug(i18n.t("iwls_api_request.http_query_handler.cache_cleared"))

        if self._session_type == SessionType.CACHE:
            self._session.cache.clear()


class RateLimiterHandler(RequestsHandler):
    __slots__ = (
        "_session",
        "_session_type",
        "_cache_config",
        "_calls",
        "_period",
        "_rate_limiter",
    )

    def __init__(
        self,
        session_type: SessionType = SessionType.REQUESTS,
        calls: int = Rate.calls,
        period: int = Rate.period,
        cache_config: Optional[CachedSessionConfig] = None,
        **kwargs,
    ):
        self._calls = calls
        self._period = period
        self._rate_limiter = RateLimiter(max_calls=self._calls, period=self._period)
        super().__init__(session_type=session_type, cache_config=cache_config, **kwargs)

        LOGGER.debug(
            i18n.t(
                "iwls_api_request.http_query_handler.rate_limit",
                calls=self._calls,
                period=self._period,
            )
        )

    def query(
        self,
        url: str,
        params: Optional[dict] = None,
        response_type: ResponseType = ResponseType.JSON,
    ) -> Response:
        """ "
        Méthode permettant d'effectuer la requête http.

        :param url: (str) Une chaîne de caractères correspondant à l'adresse url.
        :param params: (dict) Un dictionnaire avec les paramètres de la requête.
        :param response_type: (ResponseType) Un objet ResponseType.
        :return: (Response) La réponse de la requête http.
        """
        with self._rate_limiter:
            return super().query(url=url, params=params, response_type=response_type)


def get_retry_adapter(
    status_code: Optional[Collection[int]] = None,
    max_retry: Optional[int] = 5,
    backoff_factor: Optional[int] = 2,
) -> HTTPAdapter:
    """
    Fonction permettant de retourner un adaptateur avec une stratégie de réessayage.

    :param status_code: (Collection[int]) Un liste contenant les codes http à réessayer.
    :param max_retry: (int) Nombre d'essais lorsqu'un code de la liste p_status_code est retourné.py
    :param backoff_factor: (int) Le facteur à appliqué.
    :return: Un objet HTTPAdapter avec une stratégie de réessayage.
    """
    status_code = (429, 500, 502, 503, 504) if status_code is None else status_code

    LOGGER.debug(
        i18n.t(
            "iwls_api_request.http_query_handler.retry_adapter",
            status_code=status_code,
            max_retry=max_retry,
            backoff_factor=backoff_factor,
        )
    )

    return HTTPAdapter(
        max_retries=Retry(
            total=max_retry,
            status_forcelist=status_code,
            backoff_factor=backoff_factor,
            backoff_jitter=3,
        )
    )


def get_session(
    session_type: SessionType,
    cache_config: CachedSessionConfig,
) -> requests.Session | CachedSession:
    """
    Fonction permettant d'obtenir un objet session.

    :param session_type: (SessionType) Le type de session.
    :param cache_config: (CachedSessionConfig) La configuration de la cache.
    :return: requests.Session | CachedSession) Un objet Session ou CacheSession.
    """
    session_dict = {
        SessionType.CACHE: lambda: get_cache_session(
            db=cache_config.db,
            backend=cache_config.backend,
            allowable_methods=cache_config.allowable_methods,
            expire_after=cache_config.expire_after,
            timeout=cache_config.timeout,
        ),
        SessionType.REQUESTS: requests.Session,
    }

    return session_dict[session_type]()


def get_cache_session(
    db: Path = Path(__file__).resolve().parent / ".cache/IWLS",
    backend: str = "sqlite",
    allowable_methods: tuple[str] = ("GET",),
    expire_after: int = 600,
    timeout: int = 5,
) -> CachedSession:
    """
    Fonction permettant d'initialiser la cache.

    :param db: (str) Le nom de la base de données.
    :param backend: (str) Le type de cache utilisé.
    :param allowable_methods: (Tuple[str]) Les méthodes pouvant être utilisées pour la cache.
    :param expire_after: (int) La durée de vie des données dans la cache.
    :param timeout: (int) Le délai d'attente maximal pour les opérations de lecture et écriture sur la cache.
    :return: (requests_cache.CachedSession) Un objet requests_cache.CachedSession.
    """
    LOGGER.debug(
        i18n.t(
            "iwls_api_request.http_query_handler.cache_loading",
            db=db,
            backend=backend,
            expire_after=expire_after,
            timeout=timeout,
        )
    )

    return CachedSession(
        str(db),
        backend=backend,
        allowable_methods=allowable_methods,
        expire_after=expire_after,
        timeout=timeout,
    )
