from pathlib import Path
from typing import Type

import geopandas as gpd
from loguru import logger

from export.export_utils import export_geodataframe_to_geojson
from ingestion import factory_parser
from ingestion.parser_abc import DataParserABC
from ingestion.parser_dcdb import DataParserBCDB
from ingestion.parser_lowrance import DataParserLowrance
import transformation.data_cleaning as cleaner
from config.data_config import get_data_config, DataFilterConfig

LOGGER = logger.bind(name="Example.Parser")

ROOT: Path = Path(__file__).parent
EXPORT: Path = ROOT.parent / "DataLogger"


def get_ofm_files() -> tuple[list[Path], Type[DataParserABC]]:
    return [
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241001183031_20241001194143-singlefile.xyz",
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241002132309_20241002144241-singlefile.xyz",
    ], DataParserBCDB


def get_dcdb_files() -> tuple[list[Path], Type[DataParserABC]]:
    return [
        ROOT
        / "ingestion"
        / "DCDB"
        / "20240605215519876796_08b05f2b-eb9f-11ee-a43c-bd300fe11e8a_pointData.csv"
    ], DataParserBCDB


def get_lowrance_files() -> tuple[list[Path], Type[DataParserABC]]:
    return [
        ROOT / "ingestion" / "Lowrance" / "Sonar_2022-08-05_16.04.31-route.csv"
    ], DataParserLowrance


def get_blackbox_files() -> tuple[list[Path], Type[DataParserABC]]:
    return [ROOT / "ingestion" / "BlackBox" / "NMEALOG.TXT"], None


def get_actisense_files() -> tuple[list[Path], Type[DataParserABC]]:
    return [
        ROOT / "ingestion" / "ActiSense" / "composite_RDL_2024_ALL.n2kdecoded.csv"
    ], None


def main() -> None:
    if not EXPORT.exists():
        EXPORT.mkdir()

    data_config: DataFilterConfig = get_data_config()

    LOGGER.info("Parser Test")
    files, parser = get_ofm_files()
    # files, parser = get_dcdb_files()
    # files, parser = get_lowrance_files()
    # files, parser = get_blackbox_files()
    # files, parser = get_actisense_files()

    for file in files:
        LOGGER.info(f"File: {file}")
        header = factory_parser.get_parser_factory(file)
        print(header)

    data: gpd.GeoDataFrame = parser.from_files(files=files)
    data = cleaner.clean_data(data, data_filter=data_config)

    export_geodataframe_to_geojson(data, EXPORT / "ParsedData.geojson")

    print(data)
    print(data.info())
    print(data.columns)
    print(data.dtypes)
    print()

    # for row in data.iterrows():
    #     print(row)


if __name__ == "__main__":
    main()
