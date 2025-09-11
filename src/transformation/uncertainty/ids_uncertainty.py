from pathlib import Path

UNCERTAINTY_PATH = Path(__file__).parent.parent.parent / "static" / "uncertainty"
STATION_UNCERTAINTY_JSON: Path = UNCERTAINTY_PATH / "station_uncertainty.json"
SSP_ERRORS_PATH: Path = UNCERTAINTY_PATH / "canadian_waters_ssp_errors.gpkg"
UNCERTAINTY_M: str = "uncertainty_m"
