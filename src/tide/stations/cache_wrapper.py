from functools import wraps
from pathlib import Path

from diskcache import Cache
from loguru import logger


LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Cache")
CACHE: Cache = Cache(str(Path(__file__).parent / "cache"))


def cache_result(ttl: int = 86400):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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
    Vide le cache.
    """
    CACHE.clear()
    LOGGER.debug("Le cache a été vidé.")
