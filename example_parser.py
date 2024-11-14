from pathlib import Path

import geopandas as gpd
from loguru import logger

from ingestion.parser_ofm import DataParserOFM


LOGGER = logger.bind(name="Example.Parser")

ROOT: Path = Path(__file__).parent


def main() -> None:
    LOGGER.info("Parser")
    files = [
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241001183031_20241001194143-singlefile.xyz",
        ROOT
        / "ingestion"
        / "OFM"
        / "CHS9-Aventure9_20241002132309_20241002144241-singlefile.xyz",
    ]

    parser = DataParserOFM
    data: gpd.GeoDataFrame = parser.from_files(files=files)

    print(data)


if __name__ == "__main__":
    main()
