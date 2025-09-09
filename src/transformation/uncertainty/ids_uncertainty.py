from pathlib import Path

STATION_UNCERTAINTY_JSON: Path = Path(__file__).parent / "station_uncertainty.json"
DEFAULT_CONSTANT_TVU_WLP: float = 0.35  # en mètre
DEFAULT_CONSTANT_TVU_WLO: float = 0.04  # en mètre
UNCERTAINTY_M: str = "uncertainty_m"
