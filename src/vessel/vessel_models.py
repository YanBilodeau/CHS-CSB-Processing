"""
Module qui contient les modèles de données pour les navires.

Ce module contient les classes qui définissent les modèles de données pour les navires.
"""


class SensorDict(dict):
    """
    Dictionnaire de données pour un capteur.

    :param time_stamp: (str) Date et heure.
    :param x: (float) Bras de levier X.
    :param y: (float) Bras de levier Y.
    :param z: (float) Bras de levier Z.
    """

    time_stamp: str
    x: float
    y: float
    z: float


class WaterlineDict(dict):
    """
    Dictionnaire de données pour une ligne d'eau.

    :param time_stamp: (str) Date et heure.
    :param z: (float) Bras de levier Z.
    """

    time_stamp: str
    z: float


class SoundSpeedProfileDict(dict):
    """
    Dictionnaire de données pour un profil de vitesse du son.

    :param time_stamp: (str) Date et heure.
    :param ssp: (str) True si le profil de vitesse du son est appliqué.
    """

    time_stamp: str
    ssp: str


class AttributeDict(dict):
    """
    Dictionnaire de données pour un attribut BDB.

    :param time_stamp: (str) Date et heure.
    :param pltfrm: (str) Plateforme.
    :param sdghdw: (str) Système de sondage.
    :param poshdw: (str) Système de positionnement.
    :param bureau: (str) Bureau du fournisseur de données.
    :param restrn: (str) Restrictions de données.
    """

    time_stamp: str
    pltfrm: str
    sdghdw: str
    poshdw: str
    bureau: str
    restrn: str


class VesselConfigDict(dict):
    """
    Dictionnaire de données pour la configuration d'un navire.

    :param id: (str) Identifiant unique.
    :param axis_convention: (str) Convention des axes.
    :param nav: (list[SensorDict]) Capteurs de navigation.
    :param motion: (list[SensorDict]) Capteurs de mouvement.
    :param sounder: (list[SensorDict]) Capteurs de sonde.
    :param waterline: (list[WaterlineDict]) Lignes d'eau.
    :param ssp_applied: (list[SoundSpeedProfileDict]) Profils de vitesse du son appliqués.
    :param attribute: (list[AttributeDict]) Attributs BDB.
    """

    id: str
    axis_convention: str
    nav: list[SensorDict]
    motion: list[SensorDict]
    sounder: list[SensorDict]
    waterline: list[WaterlineDict]
    ssp_applied: list[SoundSpeedProfileDict]
    attribute: list[AttributeDict]
