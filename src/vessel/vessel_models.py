class SensorDict(dict):
    time_stamp: str
    x: float
    y: float
    z: float


class WaterlineDict(dict):
    time_stamp: str
    z: float


class SoundSpeedProfileDict(dict):
    time_stamp: str
    ssp: str


class AttributeDict(dict):
    time_stamp: str
    pltfrm: str
    sdghdw: str
    poshdw: str
    bureau: str
    restrn: str


class VesselConfigDict(dict):
    id: str
    axis_convention: str
    nav: list[SensorDict]
    motion: list[SensorDict]
    sounder: list[SensorDict]
    waterline: list[WaterlineDict]
    ssp_applied: list[SoundSpeedProfileDict]
    attribute: list[AttributeDict]
