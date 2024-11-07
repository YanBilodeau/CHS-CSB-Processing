from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Collection

import geopandas as gpd


@dataclass
class DataParserABC(ABC):
    @abstractmethod
    def read(self, files: Collection[Path]):  # todo ajouter type hint
        pass

    @abstractmethod
    def transform(self, data) -> gpd.GeoDataFrame:  # todo ajouter type hint
        pass


class DataParserOFM(DataParserABC):
    def read(self, files: Collection[Path]):
        pass

    def transform(self, data) -> gpd.GeoDataFrame:
        pass
