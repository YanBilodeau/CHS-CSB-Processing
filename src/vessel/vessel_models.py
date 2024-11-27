"""
Module qui contient les modèles de données pour les navires.

Ce module contient les classes qui définissent les modèles de données pour les navires.
"""


class SensorDict(dict):
    """
    Dictionnaire de données pour un capteur.

    :param time_stamp: Date et heure.
    :type time_stamp: str
    :param x: Bras de levier X.
    :type x: float
    :param y: Bras de levier Y.
    :type y: float
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: str
    """Date et heure."""
    x: float
    """Bras de levier X."""
    y: float
    """Bras de levier Y."""
    z: float
    """Bras de levier Z."""


class WaterlineDict(dict):
    """
    Dictionnaire de données pour une ligne d'eau.

    :param time_stamp: (Date et heure.
    :type time_stamp: str
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: str
    """Date et heure."""
    z: float
    """Bras de levier Z."""


class SoundSpeedProfileDict(dict):
    """
    Dictionnaire de données pour un profil de vitesse du son.

    :param time_stamp: Date et heure.
    :type time_stamp: str
    :param ssp: True si le profil de vitesse du son est appliqué.
    :type ssp: str
    """

    time_stamp: str
    """Date et heure."""
    ssp: str
    """True si le profil de vitesse du son est appliqué."""


class AttributeDict(dict):
    """
    Dictionnaire de données pour un attribut BDB.

    :param time_stamp: Date et heure.
    :type time_stamp: str
    :param pltfrm: Plateforme.
    :type pltfrm: str
    :param sdghdw: Système de sondage.
    :type sdghdw: str
    :param poshdw: Système de positionnement.
    :type poshdw: str
    :param bureau: Organisation du fournisseur de données.
    :type bureau: str
    :param restrn: Restrictions de données.
    :type restrn: str
    """

    time_stamp: str
    """Date et heure."""
    pltfrm: str
    """Plateforme."""
    sdghdw: str
    """Système de sondage."""
    poshdw: str
    """Système de positionnement."""
    bureau: str
    """Organisation du fournisseur de données."""
    restrn: str
    """Restrictions de données."""


class VesselConfigDict(dict):
    """
    Dictionnaire de données pour la configuration d'un navire.

    :param id: Identifiant unique.
    :type id: str
    :param axis_convention: Convention des axes.
    :type axis_convention: str
    :param nav: Capteurs de navigation.
    :type nav: list[SensorDict]
    :param motion: Capteurs de mouvement.
    :type motion: list[SensorDict]
    :param sounder: Capteurs de sonde.
    :type sounder: list[SensorDict]
    :param waterline: Lignes d'eau.
    :type waterline: list[WaterlineDict]
    :param ssp_applied: Profils de vitesse du son appliqués.
    :type ssp_applied: list[SoundSpeedProfileDict]
    :param attribute: Attributs BDB.
    :type attribute: list[AttributeDict]
    """

    id: str
    """Identifiant du navire."""
    axis_convention: str
    """Convention des axes."""
    nav: list[SensorDict]
    """Données des bras de leviers du capteur de navigation."""
    motion: list[SensorDict]
    """Données des bras de leviers du capteur de mouvement."""
    sounder: list[SensorDict]
    """Données des bras de leviers du sondeur."""
    waterline: list[WaterlineDict]
    """Données des bras de leviers de la lignes d'eau."""
    ssp_applied: list[SoundSpeedProfileDict]
    """Profils de vitesse du son appliqués."""
    attribute: list[AttributeDict]
    """Données des attributs BDB."""
