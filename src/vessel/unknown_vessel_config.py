from datetime import datetime, timezone

from .vessel_config import (
    VesselConfig,
    AxisConvention,
    Sensor,
    Waterline,
    SoundSpeedProfile,
    BDBattribute,
    UNKNOWN,
    DEFAULT_TECSOU,
    UNKNOWN_DATE,
)


UNKNOWN_VESSEL_CONFIG: VesselConfig = VesselConfig(
    id=UNKNOWN,
    name=UNKNOWN,
    axis_convention=AxisConvention.CARIS,
    navigation=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    motion=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    sounder=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    waterline=[Waterline(time_stamp=UNKNOWN_DATE, z=0.0)],
    sound_speed=[
        SoundSpeedProfile(time_stamp=UNKNOWN_DATE, ssp=False, sound_speed=1500.0)
    ],
    attribute=[
        BDBattribute(
            time_stamp=UNKNOWN_DATE,
            pltfrm=UNKNOWN,
            tecsou=DEFAULT_TECSOU,
            sdghdw=UNKNOWN,
            poshdw=UNKNOWN,
            bureau=UNKNOWN,
            restrn=UNKNOWN,
        )
    ],
)
