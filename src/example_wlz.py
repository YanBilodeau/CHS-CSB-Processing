from pathlib import Path

import geopandas as gpd
from loguru import logger

from config import data_config as data_config
from config import iwls_api_config as iwls_config
from export.export_utils import export_geodataframe_to_geojson
from ingestion import factory_parser
import iwls_api_request as iwls
import schema
import schema.model_ids as schema_ids
import tide.stations as stations
import tide.voronoi as voronoi
import transformation.data_cleaning as cleaner


LOGGER = logger.bind(name="Example.WaterLevelZones")

ROOT: Path = Path(__file__).parent
EXPORT_DATA: Path = ROOT.parent / "DataLogger"
EXPORT_TIDE: Path = ROOT.parent / "TideFileExport"


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


def get_iwls_environment(config: iwls_config.IWLSAPIConfig) -> iwls.APIEnvironment:
    """
    Réccupère l'environnement de l'API IWLS à partir du fichier de configuration.

    :param config: Configuration de l'API IWLS.
    :type config: IWLSAPIConfig
    :return: Environnement de l'API IWLS.
    :rtype: APIEnvironment
    """
    activated_profile: iwls.EnvironmentType = config.profile.active
    activated_environment: iwls.APIEnvironment = config.__dict__.get(activated_profile)

    LOGGER.debug(
        f"Chargement du profil '{config.profile.active}' pour l'API IWLS. [{activated_environment}]."
    )

    return activated_environment


def get_api(environment: iwls.APIEnvironment) -> stations.IWLSapiProtocol:
    """
    Récupère l'API IWLS à partir de l'environnement spécifié.

    :param environment: Environnement de l'API IWLS.
    :type environment: APIEnvironment
    :return: API IWLS.
    :rtype: IWLSapiProtocol
    """
    return iwls.get_iwls_api(  # type: ignore
        endpoint=environment.endpoint,
        handler_type=iwls.HandlerType.RATE_LIMITER,
        calls=environment.calls,
        period=environment.period,
    )


def get_stations_handler(
    endpoint_type: stations.EndpointTypeProtocol, api: stations.IWLSapiProtocol
) -> stations.StationsHandlerABC:
    """
    Récupère le gestionnaire des stations.

    :param endpoint_type: Type de l'endpoint.
    :type endpoint_type: EndpointTypeProtocol
    :param api: API IWLS.
    :type api: IWLSapiProtocol
    :return: Gestionnaire des stations.
    :rtype: StationsHandlerABC
    """
    return stations.get_stations_factory(enpoint_type=endpoint_type)(api=api)


def add_tide_zone_to_geodataframe(
    data_geodataframe: gpd.GeoDataFrame,
    tide_zone: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Récupère les zones de marées pour les données.

    :param data_geodataframe: Les données des DataLoggers.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param tide_zone: Les zones de marées.
    :type tide_zone: gpd.GeoDataFrame[schema.TideZoneSchema]
    :return: Les données des DataLoggers avec les zones de marées.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    columns: list[str] = [
        schema_ids.TIME_UTC,
        schema_ids.LATITUDE_WGS84,
        schema_ids.LONGITUDE_WGS84,
        schema_ids.DEPTH_METER,
        schema_ids.GEOMETRY,
        schema_ids.ID,
    ]

    gdf_data_time_zone: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        gpd.sjoin(
            data_geodataframe,
            tide_zone,
            how="left",
            predicate="within",
        )[
            columns
        ].rename(columns={schema_ids.ID: schema_ids.TIDE_ZONE_ID})
    )

    schema.validate_schema(gdf_data_time_zone, schema.DataLoggerWithTideZoneSchema)

    return gdf_data_time_zone


def get_time_tide_zone(): ...


def main() -> None:
    # Create the directories if they do not exist
    if not EXPORT_DATA.exists():
        EXPORT_DATA.mkdir()
    if not EXPORT_TIDE.exists():
        EXPORT_TIDE.mkdir()

    # Read the configuration file 'data_config.toml'
    data_filter_config: data_config.DataFilterConfig = data_config.get_data_config()

    # Read the configuration file 'iwls_API_config.toml'
    iwls_api_config: iwls_config.IWLSAPIConfig = iwls_config.get_api_config(
        config_file=iwls_config.CONFIG_FILE
    )

    # Get the files to parse
    files: list[Path] = get_ofm_files()
    # files = get_dcdb_files()
    # files = get_lowrance_files()
    # files = get_blackbox_files()
    # files = get_actisense_files()
    # files = (
    #     get_ofm_files()
    #     + get_dcdb_files()
    #     + get_lowrance_files()
    #     + get_blackbox_files()
    #     + get_actisense_files()
    # )

    # Get the parser and the parsed data
    parser_files: factory_parser.ParserFiles = factory_parser.get_files_parser(
        files=files
    )
    LOGGER.debug(parser_files)

    # Clean the data
    data: gpd.GeoDataFrame[schema.DataLoggerSchema] = parser_files.parser.from_files(
        files=parser_files.files
    )
    data = cleaner.clean_data(data, data_filter=data_filter_config)
    # Export the parsed data to a GeoJSON file
    export_geodataframe_to_geojson(data, EXPORT_DATA / "ParsedData.geojson")

    # Get the environment of the API IWLS from the configuration file and the active profile
    api_environment: iwls.APIEnvironment = get_iwls_environment(config=iwls_api_config)
    # Get the API IWLS from the environment
    api: stations.IWLSapiProtocol = get_api(environment=api_environment)

    # Get the handler of the stations
    stations_handler: stations.StationsHandlerABC = get_stations_handler(
        api=api, endpoint_type=api_environment.endpoint.TYPE
    )

    # Get the Voronoi diagram of the stations. The stations are selected based on the priority of the time series.
    # The time series priority is defined in the configuration file.
    gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneSchema] = (
        voronoi.get_voronoi_geodataframe(
            stations_handler=stations_handler,
            time_series=iwls_api_config.time_series.priority,
            # excluded_stations=("5cebf1df3d0f4a073c4bbced", "5cebf1e23d0f4a073c4bc021"),
        )
    )
    # Export the Voronoi diagram to a GeoJSON file
    export_geodataframe_to_geojson(
        geodataframe=gdf_voronoi,
        output_path=EXPORT_TIDE / "voronoi_merged.geojson",
    )

    # Add the tide zone to the data
    gdf_data_tide_zone: gpd.GeoDataFrame = add_tide_zone_to_geodataframe(
        data_geodataframe=data, tide_zone=gdf_voronoi
    )
    # Export the data with the tide zone to a GeoJSON file
    export_geodataframe_to_geojson(
        geodataframe=gdf_data_tide_zone,
        output_path=EXPORT_DATA / "ParsedDataWithTideZone.geojson",
    )
    print(gdf_data_tide_zone)
    print(gdf_data_tide_zone.columns)


if __name__ == "__main__":
    main()
