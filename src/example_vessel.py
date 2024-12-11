from datetime import datetime
from dateutil import parser
from pathlib import Path

import vessel

ROOT: Path = Path(__file__).parent

VESSEL_JSON_PATH: Path = ROOT / "vessel" / "TCSB_VESSELSLIST.json"
VESSEL_JSON_UPDATE_PATH: Path = ROOT / "vessel" / "TCSB_VESSELSLIST_UPDATE.json"

VESSEL_SQLITE_PATH: Path = ROOT / "vessel" / "vessel_config.db"


if __name__ == "__main__":
    vessel_config_manager = vessel.VesselConfigJsonManager(
        json_config_path=VESSEL_JSON_PATH
    )

    vessels: list[vessel.VesselConfig] = vessel_config_manager.get_vessel_configs()
    print(vessels)

    # vessel_config_manager.delete_vessel_config("Frosti")
    # vessel_config_manager.commit_vessel_configs(VESSEL_JSON_UPDATE_PATH)

    frosti: vessel.VesselConfig = vessel_config_manager.get_vessel_config("Frosti")
    print(frosti)

    time_stamp: datetime = parser.isoparse("2024-09-25T00:00:00Z")
    nav: vessel.Sensor = frosti.get_navigation(timestamp=time_stamp)
    print(nav)

    motion: vessel.Sensor = frosti.get_motion(timestamp=time_stamp)
    print(motion)

    sounder: vessel.Sensor = frosti.get_sounder(timestamp=time_stamp)
    print(sounder)

    waterline: vessel.Waterline = frosti.get_waterline(timestamp=time_stamp)
    print(waterline)

    ssp_applied: vessel.SoundSpeedProfile = frosti.get_ssp_applied(timestamp=time_stamp)
    print(ssp_applied)

    attribute: vessel.BDBattribute = frosti.get_attribute(timestamp=time_stamp)
    print(attribute)

    vessel_config_sqlite_manager: vessel.VesselConfigSQLiteManager = vessel.VesselConfigSQLiteManager(
        sqlite_config_path=VESSEL_SQLITE_PATH
    )
    print(vessel_config_sqlite_manager)
