import json
from pathlib import Path

from vessel.vessel_config import (
    VesselConfig,
    get_vessel_config_from_config_dict,
    VesselConfigDict,
)

ROOT: Path = Path(__file__).parent

VESSEL_JSON_PATH: Path = ROOT / "vessel" / "TCSB_VESSELSLIST.json"


if __name__ == "__main__":
    with open(VESSEL_JSON_PATH, "r") as file:
        config_dict: list[VesselConfigDict] = json.load(file)

    for vessel_config in config_dict:
        vessel: VesselConfig = get_vessel_config_from_config_dict(config=vessel_config)
        print(vessel)
