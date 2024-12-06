"""
Module permettant de gérer une cache pour les données des stations de marées.

Ce module contient les fonctions suivantes qui permettent de gérer une cache pour les données des stations de marées.
"""

from functools import wraps
from pathlib import Path
from typing import Callable

from diskcache import Cache
from loguru import logger


LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Cache")
CACHE: Cache = Cache(str(Path(__file__).parent / "cache"))


def cache_result(ttl: int = 86400):
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

            if cache_key in CACHE:
                LOGGER.trace(f"Récupération des données depuis la cache : {cache_key}.")
                return CACHE[cache_key]

            result = func(*args, **kwargs)

            LOGGER.trace(
                f"Ajout de données dans la cache avec un ttl de {ttl} secondes : '{cache_key}'."
            )
            CACHE.set(key=cache_key, value=result, expire=ttl)

            return result

        return wrapper

    return decorator


def clear_cache():
    """
    Fonction pour vider le cache.
    """
    CACHE.clear()
    LOGGER.debug("Le cache a été vidé.")
