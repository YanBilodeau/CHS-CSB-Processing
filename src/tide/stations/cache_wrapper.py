"""
Module permettant de gérer un cache pour les données des stations de marées.

Ce module contient les fonctions suivantes qui permettent de gérer un cache pour les données des stations de marées.
"""

from functools import wraps
from pathlib import Path

from diskcache import Cache
from loguru import logger


LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Cache")
CACHE: Cache = Cache(str(Path(__file__).parent / "cache"))


def cache_result(ttl: int = 86400):
    """
    Décorateur pour mettre en cache le résultat d'une fonction.

    :param ttl: (int) Durée de vie du cache en secondes.
    """

    def decorator(func):
        """
        Décorateur pour mettre en cache le résultat d'une fonction.

        :param func: Fonction à décorer.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            Fonction pour mettre en cache le résultat d'une fonction.

            :param args: Arguments de la fonction.
            :param kwargs: Arguments nommés de la fonction

            """
            cache_key = f"{func.__name__}_{args}_{kwargs}"

            if cache_key in CACHE:
                logger.debug(f"Récupération des données depuis la cache : {cache_key}.")
                return CACHE[cache_key]

            result = func(*args, **kwargs)

            logger.debug(
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
