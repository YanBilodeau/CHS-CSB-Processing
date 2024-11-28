from pathlib import Path

import geopandas as gpd
from loguru import logger

from export.export_utils import export_geodataframe_to_geojson
from ingestion import factory_parser
import transformation.data_cleaning as cleaner
from config.data_config import get_data_config, DataFilterConfig

LOGGER = logger.bind(name="Example.WaterLevelZones")

ROOT: Path = Path(__file__).parent
EXPORT: Path = ROOT.parent / "DataLogger"


def get_ofm_files() -> list[Path]:
    return [
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241001183031_20241001194143-singlefile.xyz",
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241002132309_20241002144241-singlefile.xyz",
    ]


def get_dcdb_files() -> list[Path]:
    return [
        ROOT
        / "ingestion"
        / "DCDB"
        / "20240605215519876796_08b05f2b-eb9f-11ee-a43c-bd300fe11e8a_pointData.csv"
    ]


def get_lowrance_files() -> list[Path]:
    return [ROOT / "ingestion" / "Lowrance" / "Sonar_2022-08-05_16.04.31-route.csv"]


def get_blackbox_files() -> list[Path]:
    return [ROOT / "ingestion" / "BlackBox" / "NMEALOG.TXT"]


def get_actisense_files() -> list[Path]:
    return [ROOT / "ingestion" / "ActiSense" / "composite_RDL_2024_ALL.n2kdecoded.csv"]


def main() -> None:
    if not EXPORT.exists():
        EXPORT.mkdir()

    data_config: DataFilterConfig = get_data_config()

    files: list[Path] = get_ofm_files()

    data_parser_dict: factory_parser.ParserFiles = factory_parser.get_files_parser(
        files=files
    )

    LOGGER.debug(data_parser_dict)


if __name__ == "__main__":
    main()
