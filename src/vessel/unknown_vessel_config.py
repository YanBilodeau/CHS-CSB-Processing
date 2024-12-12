from datetime import datetime, timezone

from .vessel_config import (
    VesselConfig,
    AxisConvention,
    Sensor,
    Waterline,
    SoundSpeedProfile,
    BDBattribute,
)


UNKNOWN_DATE: datetime = datetime(1960, 1, 1, tzinfo=timezone.utc)
UNKNOWN_VESSEL_CONFIG: VesselConfig = VesselConfig(
    id="unknown",
    axis_convention=AxisConvention.CARIS,
    navigation=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    motion=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    sounder=[Sensor(time_stamp=UNKNOWN_DATE, x=0.0, y=0.0, z=0.0)],
    waterline=[Waterline(time_stamp=UNKNOWN_DATE, z=0.0)],
    ssp_applied=[SoundSpeedProfile(time_stamp=UNKNOWN_DATE, ssp=False)],
    attribute=[
        BDBattribute(
            time_stamp=UNKNOWN_DATE,
            pltfrm="unknown",
            sdghdw="unknown",
            poshdw="unknown",
            bureau="unknown",
            restrn="unknown",
        )
    ],
)
