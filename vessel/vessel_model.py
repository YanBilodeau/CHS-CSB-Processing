from typing import TypedDict


class SensorDict(TypedDict):
    time_stamp: str
    x: float
    y: float
    z: float


class WaterlineDict(TypedDict):
    time_stamp: str
    z: float


class SoundSpeedProfileDict(TypedDict):
    time_stamp: str
    ssp: str


class AttributeDict(TypedDict):
    time_stamp: str
    pltfrm: str
    sdghdw: str
    poshdw: str
    bureau: str
    restrn: str


class VesselConfigDict(TypedDict):
    id: str
    axis_convention: str
    nav: list[SensorDict]
    motion: list[SensorDict]
    sounder: list[SensorDict]
    waterline: list[WaterlineDict]
    ssp_applied: list[SoundSpeedProfileDict]
    attribute: list[AttributeDict]
