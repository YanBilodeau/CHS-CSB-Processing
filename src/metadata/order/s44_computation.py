import numpy as np


def compute_threshold(
    valid_depth: np.ndarray, valid_mask: np.ndarray, a: float, b: float
) -> np.ndarray:
    """
    Calcule le seuil en fonction d'une valeur de a et d'un facteur b multiplié par la profondeur.

    :param valid_depth: Tableau contenant les valeurs de profondeur valides (0 sinon)
    :param valid_mask: Masque indiquant les pixels valides
    :param a: Valeur de a (exemple : 0.15 pour l'ordre exclusif)
    :param b: Facteur b utilisé pour le calcul (exemple : 0.0075 pour l'ordre exclusif)
    :return: Tableau des seuils calculés pour chaque pixel
    """
    # On applique le calcul uniquement sur les pixels valides, sinon on ajoute 0
    return np.sqrt(a**2 + np.where(valid_mask, (b * valid_depth) ** 2, 0))


# Configuration des paramètres pour les différents ordres
ORDERS_CONFIG = [
    {"order": 0, "a": 0.15, "b": 0.0075, "pos_func": lambda vd: 1},
    {"order": 1, "a": 0.25, "b": 0.0075, "pos_func": lambda vd: 2},
    {
        "order": 2,
        "a": 0.5,
        "b": 0.013,
        "pos_func": lambda vd: 5 + 0.05 * vd,
    },
    {
        "order": 3,
        "a": 1,
        "b": 0.023,
        "pos_func": lambda vd: 20 + 0.1 * vd,
    },
]
