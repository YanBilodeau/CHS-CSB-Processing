"""
Module permettant de gérer une cache pour les données des stations de marées.

Ce module contient les fonctions suivantes qui permettent de gérer une cache pour les données des stations de marées.
"""

from functools import wraps
from pathlib import Path
from typing import Callable

from diskcache import Cache
from loguru import logger
import i18n

LOGGER = logger.bind(name="CSB-Processing.Tide.Station.Cache")
cache: Cache | None = None


def init_cache(cache_path: Path) -> None:
    """
    Fonction pour initialiser le cache.

    :param cache_path: Chemin du cache.
    :type cache_path: Path
    """
    global cache

    if cache is None:
        LOGGER.debug(i18n.t("tide.stations.cache_wrapper.init_cache", path=cache_path))
        cache = Cache(str(cache_path))


def cache_result(ttl: int = 86400) -> Callable:
    """
    Décorateur pour mettre en cache le résultat d'une fonction.

    :param ttl: Durée de vie du cache en secondes.
    :type ttl: int
    """

    def decorator(func: Callable):
        """
        Décorateur pour mettre en cache le résultat d'une fonction.

        :param func: Fonction à décorer.
        :type func: Callable
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            Fonction pour mettre en cache le résultat d'une fonction.

            :param args: Arguments de la fonction.
            :type args: tuple
            :param kwargs: Arguments nommés de la fonction
            :type kwargs: dict

            """
            cache_key = f"{func.__name__}_{args}_{kwargs}"

            if cache_key in cache:
                LOGGER.trace(
                    i18n.t("tide.stations.cache_wrapper.cache_hit", key=cache_key)
                )
                return cache[cache_key]

            result = func(*args, **kwargs)

            LOGGER.trace(
                i18n.t("tide.stations.cache_wrapper.cache_set", ttl=ttl, key=cache_key)
            )
            cache.set(key=cache_key, value=result, expire=ttl)

            return result

        return wrapper

    return decorator


def clear_cache():
    """
    Fonction pour vider le cache.
    """
    cache.clear()
    LOGGER.debug(i18n.t("tide.stations.cache_wrapper.cache_cleared"))
