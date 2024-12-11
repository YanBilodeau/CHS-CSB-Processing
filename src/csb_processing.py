from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from config import data_config as data_config
from config import iwls_api_config as iwls_config
import export.export_utils as export
from ingestion import factory_parser
import iwls_api_request as iwls
from logger.loguru_config import configure_logger
import schema
import schema.model_ids as schema_ids
from tide.plot import plot_time_series_dataframe
import tide.stations as stations
import tide.voronoi as voronoi
import tide.time_serie as time_serie
import transformation.data_cleaning as cleaner
import transformation.georeference as georeference
import vessel


LOGGER = logger.bind(name="CSB-Processing.WorkFlow")

ROOT: Path = Path(__file__).parent
OUTPUT: Path = ROOT.parent / "Output"
VESSEL_JSON_PATH: Path = ROOT / "vessel" / "TCSB_VESSELSLIST.json"


@dataclass(frozen=True)
class SensorConfigurationError(Exception):
    """
    Exception levée lorsque la configuration du capteur change durant la période de temps couverte par les données.
    """

    sensor_type: str
    """Le type de capteur."""

    def __str__(self) -> str:
        return f"La configuration du capteur {self.sensor_type} a changé durant la période de temps couverte par les données."


def get_data_structure(output_path: Path) -> tuple[Path, Path, Path]:
    """
    Récupère la structure de répertoires pour les données.

    :param output_path: Chemin du répertoire de sortie.
    :type output_path: Path
    :return: Chemin des répertoires pour les données.
    :rtype: tuple[Path, Path, Path]
    """
    data_path: Path = output_path / "Data"
    tide_path: Path = output_path / "Tide"
    log_path: Path = output_path / "Log"

    # Create the directories if they do not exist
    if not data_path.exists():
        data_path.mkdir(parents=True)
    if not tide_path.exists():
        tide_path.mkdir()
    if not log_path.exists():
        log_path.mkdir()

    return data_path, tide_path, log_path


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


@schema.validate_schemas(
    data_geodataframe=schema.DataLoggerSchema,
    tide_zone=schema.TideZoneProtocolSchema,
    return_schema=schema.DataLoggerWithTideZoneSchema,
)
def add_tide_zone_id_to_geodataframe(
    data_geodataframe: gpd.GeoDataFrame,
    tide_zone: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Récupère les zones de marées pour les données.

    :param data_geodataframe: Les données des DataLoggers.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param tide_zone: Les zones de marées.
    :type tide_zone: gpd.GeoDataFrame[schema.TideZoneProtocolSchema]
    :return: Les données des DataLoggers avec les zones de marées.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Récupération des zones de marées selon l'extension des données.")

    columns: list[str] = [
        schema_ids.TIME_UTC,
        schema_ids.LATITUDE_WGS84,
        schema_ids.LONGITUDE_WGS84,
        schema_ids.DEPTH_RAW_METER,
        schema_ids.DEPTH_PROCESSED_METER,
        schema_ids.WATER_LEVEL_METER,
        schema_ids.UNCERTAINTY,
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

    return gdf_data_time_zone

    # todo Identification des périodes en enlevant les trous de x temps


@schema.validate_schemas(
    data_geodataframe=schema.DataLoggerWithTideZoneSchema,
    return_schema=schema.TideZoneInfoSchema,
)
def get_intersected_tide_zone_info(
    data_geodataframe: gpd.GeoDataFrame,
    tide_zone: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Récupère les zones de marées et le temps de début et de fin pour les données.

    :param data_geodataframe: Les données des DataLoggers.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    param tide_zone: Les zones de marées.
    :type tide_zone: gpd.GeoDataFrame[schema.TideZoneProtocolSchema]
    :return: Les zones de marées et le temps de début et de fin pour les données.
    :rtype: pd.DataFrame[schema.TideZoneInfoSchema]
    """

    def get_station_time_series(station_id: str) -> list[iwls.TimeSeries]:
        return [
            iwls.TimeSeries.from_str(ts)
            for ts in voronoi.get_time_series_by_station_id(
                gdf_voronoi=tide_zone, station_id=station_id
            )
        ]

    LOGGER.debug(
        f"Récupération du temps de début et de fin pour les données selon les zones de marées."
    )

    tide_zone_info: pd.DataFrame = (
        data_geodataframe.groupby(schema_ids.TIDE_ZONE_ID)[schema_ids.TIME_UTC]
        .agg(min_time="min", max_time="max")
        .reset_index()
    )

    tide_zone_info[schema_ids.TIME_SERIES] = tide_zone_info[
        schema_ids.TIDE_ZONE_ID
    ].apply(get_station_time_series)

    return tide_zone_info


def export_water_level_dataframe(
    station_title: str, wl_dataframe: pd.DataFrame, export_tide_path: Path
) -> None:
    """
    Exporte les données de niveaux d'eau pour une station dans un fichier CSV.

    :param station_title: Titre de la station.
    :type station_title: str
    :param wl_dataframe: DataFrame contenant les données de niveaux d'eau.
    :type wl_dataframe: pd.DataFrame
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers CSV.
    :type export_tide_path: Path
    """
    output_path: Path = (
        export_tide_path / f"{station_title} "
        f"({wl_dataframe.attrs.get(schema_ids.START_TIME).strftime('%Y-%m-%d %H-%M-%S')} - "
        f"{wl_dataframe.attrs.get(schema_ids.END_TIME).strftime('%Y-%m-%d %H-%M-%S')}).csv"
    )

    # Export the water level data to a CSV file
    LOGGER.info(f"Enregistrement des données de niveaux d'eau : {output_path}.")
    export.export_dataframe_to_csv(
        dataframe=wl_dataframe,
        output_path=output_path,
    )


def export_station_water_levels(
    wl_combineds: dict[str, pd.DataFrame],
    gdf_voronoi: gpd.GeoDataFrame,
    export_tide_path: Optional[Path] = None,
) -> list[str]:
    """
    Exporte les données de niveaux d'eau pour chaque station dans des fichiers CSV.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: dict[str, pd.DataFrame]
    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers CSV.
    :type export_tide_path: Optional[Path]
    :return: Liste des titres des stations.
    :rtype: list[str]
    """
    station_titles = []

    for station_id, wl_dataframe in wl_combineds.items():
        station_title = (
            f"{voronoi.get_name_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)} "
            f"({voronoi.get_code_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)})"
        )
        station_titles.append(station_title)

        if export_tide_path:
            export_water_level_dataframe(
                station_title=station_title,
                wl_dataframe=wl_dataframe,
                export_tide_path=export_tide_path,
            )

    return station_titles


def plot_water_level_data(
    wl_combineds: dict[str, pd.DataFrame],
    station_titles: list[str],
    export_path: Path,
) -> None:
    """
    Trace les données de niveaux d'eau pour chaque station et les enregistre dans un fichier HTML.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: dict[str, pd.DataFrame]
    :param station_titles: Liste des titres des stations.
    :type station_titles: list[str]
    :param export_path: Chemin du répertoire d'exportation des fichiers HTML.
    :type export_path: Path
    """
    LOGGER.info(
        f"Enregistrement des graphiques des données de niveaux d'eau {station_titles}: {export_path}."
    )

    plot_time_series_dataframe(
        dataframes=list(wl_combineds.values()),
        titles=station_titles,
        show_plot=False,  # Afficher le graphique dans un navigateur web
        output_path=export_path,  # Exporter le graphique dans un fichier HTML
    )


def get_sensor_with_validation(
    vessel_config: vessel.VesselConfig,
    sensor_type: str,
    min_time: datetime,
    max_time: datetime,
) -> vessel.Sensor | vessel.Waterline:
    """
    Récupère et valide les capteurs pour une période de temps donnée.

    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel.VesselConfig
    :param sensor_type: Type de capteur à récupérer.
    :type sensor_type: str
    :param min_time: Date et heure minimale.
    :type min_time: datetime
    :param max_time: Date et heure maximale.
    :type max_time: datetime
    :return: Capteur pour le moment donné.
    :rtype: vessel.Sensor | vessel.Waterline
    :raises SensorConfigurationError: Si la configuration du capteur change durant la période de temps couverte par les données.
    """
    min_time_sensor = getattr(vessel_config, f"get_{sensor_type}")(timestamp=min_time)
    max_time_sensor = getattr(vessel_config, f"get_{sensor_type}")(timestamp=max_time)

    if min_time_sensor.time_stamp != max_time_sensor.time_stamp:
        raise SensorConfigurationError(sensor_type=sensor_type)

    return min_time_sensor


def get_sensors(
    vessel_config: vessel.VesselConfig, min_time: datetime, max_time: datetime
) -> tuple[vessel.Sensor, vessel.Waterline]:
    """
    Méthode pour récupérer les données des capteurs et valider que la configuration du navire couvre la période de temps.

    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel.VesselConfig
    :param min_time: Date et heure minimale.
    :type min_time: datetime
    :param max_time: Date et heure maximale.
    :type max_time: datetime
    :return: Données des capteurs pour le moment donné.
    :rtype: tuple[vessel.Sensor, vessel.Waterline]
    """
    sounder: vessel.Sensor = get_sensor_with_validation(
        vessel_config, "sounder", min_time, max_time
    )
    waterline: vessel.Waterline = get_sensor_with_validation(
        vessel_config, "waterline", min_time, max_time
    )

    return sounder, waterline


def is_valid_file(file: Path) -> bool:
    """
    Vérifie si le fichier est valide pour le traitement.

    :param file: Chemin du fichier.
    :type file: Path
    :return: Vrai si le fichier est valide, faux sinon.
    :rtype: bool
    """
    return file.suffix.lower() in {".csv", ".txt", ".xyz"}


def get_files(paths: Collection[Path]) -> list[Path]:
    """
    Récupère les fichiers à traiter.

    :param paths: Chemins des fichiers ou répertoires.
    :type paths: Collection[Path]
    :return: Liste des fichiers à traiter.
    :rtype: list[Path]
    """
    files: list[Path] = []

    for path in paths:
        path = Path(path)

        if path.is_file() and is_valid_file(path):
            files.append(path)

        elif path.is_dir():
            files.extend(file for file in path.glob("**/*") if is_valid_file(file))

    return files


def processing_workflow(files: Collection[Path], vessel_id: str, output: Path) -> None:
    # Get the files to parse
    files: list[Path] = get_files(files)  # todo bouger dans cli.py

    # Check if there are files to process
    if not files:  # todo bouger dans cli.py
        LOGGER.error("Aucun fichier valide à traiter.")
        return None

    # Get the data structure
    export_data_path, export_tide_path, log_path = get_data_structure(output)

    # Configure the logger
    configure_logger(
        log_path / f"{datetime.now().strftime('%Y-%m-%d')}_CSB-Processing.log",
        std_level="INFO",
        log_file_level="DEBUG",
    )

    # Read the configuration file 'data_config.toml'
    data_filter_config, data_georef_config = data_config.get_data_config()

    # Get the parser and the parsed data
    LOGGER.info(f"Récupération des données brutes des fichiers : {files}.")
    parser_files: factory_parser.ParserFiles = factory_parser.get_files_parser(
        files=files
    )
    LOGGER.debug(parser_files)

    # Parse the data
    data: gpd.GeoDataFrame[schema.DataLoggerSchema] = parser_files.parser.from_files(
        files=parser_files.files
    )

    # Clean the data
    LOGGER.info(f"Nettoyage et filtrage des données.")
    data = cleaner.clean_data(data, data_filter=data_filter_config)

    LOGGER.success(f"{len(data)} sondes valides récupérées.")

    # Export the parsed data
    export.export_geodataframe_to_gpkg(data, export_data_path / "ParsedData.gpkg")

    # Get the vessel configuration
    vessel_config_manager = vessel.VesselConfigJsonManager(
        json_config_path=VESSEL_JSON_PATH
    )

    LOGGER.info(f"Récupération de la configuration du navire {vessel_id}.")
    tuktoyaktuk_vessel: vessel.VesselConfig = vessel_config_manager.get_vessel_config(
        vessel_id=vessel_id
    )

    # Read the configuration file 'iwls_API_config.toml'
    iwls_api_config: iwls_config.IWLSAPIConfig = iwls_config.get_api_config(
        config_file=iwls_config.CONFIG_FILE
    )
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
    LOGGER.info("Récupération des zones de marée (diagramme de Voronoi).")
    gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
        voronoi.get_voronoi_geodataframe(
            stations_handler=stations_handler,
            time_series=iwls_api_config.time_series.priority,
        )
    )
    # Export the Voronoi diagram to a GeoJSON file
    export.export_geodataframe_to_geojson(
        geodataframe=gdf_voronoi,
        output_path=export_tide_path / "voronoi_merged.geojson",
    )

    # Add the tide zone to the data
    gdf_data_tide_zone: gpd.GeoDataFrame = add_tide_zone_id_to_geodataframe(
        data_geodataframe=data, tide_zone=gdf_voronoi
    )

    # Get the time and tide zone
    LOGGER.info(
        "Récupération des information sur les zones de marées qui intersetent les données brutes."
    )
    tide_zonde_info: pd.DataFrame = get_intersected_tide_zone_info(
        data_geodataframe=gdf_data_tide_zone,
        tide_zone=gdf_voronoi,
    )

    for zone, min_time, max_time, time_series in tide_zonde_info.itertuples(
        index=False
    ):
        LOGGER.info(
            f"Zone de marée {zone} : temps minimum - {min_time}, temps maximum - {max_time}, séries temporelles - {time_series}."
        )

    tide_zonde_info[schema_ids.MAX_TIME].max()
    tide_zonde_info[schema_ids.MIN_TIME].min()

    # Get the sensors for the vessel
    sounder, waterline = get_sensors(
        vessel_config=tuktoyaktuk_vessel,
        min_time=tide_zonde_info[schema_ids.MIN_TIME].min(),
        max_time=tide_zonde_info[schema_ids.MAX_TIME].max(),
    )

    # Get the water level data for each station
    LOGGER.info(
        "Récupération des données de niveaux d'eau pour chaque station touchant les données brutes."
    )
    wl_combineds, wl_exceptions = time_serie.get_water_level_data_for_stations(
        # Stations handler to retrieve the water level data.
        stations_handler=stations_handler,
        # Tide zone information for the water level data. Tide zone id, start time, end time and time series.
        tide_zonde_info=tide_zonde_info,
        # Quality control flag filter for the wlo time series.
        wlo_qc_flag_filter=iwls_api_config.time_series.wlo_qc_flag_filter,
        # Buffer time to add before and after the requested time range for the interpolation.
        buffer_time=iwls_api_config.time_series.buffer_time,
        # Maximum time gap allowed for the data. The maximum time gap is defined in the configuration file.
        # If the gap is greater than this value, data from the next time series will be retrieved to fill
        # the gaps. For example, if the time series priority is [wlo, wlp] and the maximum time gap is 1 hour, the
        # data for the time series wlo will be retrieved first. If the gap between two consecutive
        # data points is greater than 1 hour, the data for the time series wlp will be retrieved to fill the gap.
        max_time_gap=iwls_api_config.time_series.max_time_gap,
        # Threshold for the interpolation versus filling of the gaps in the data.
        threshold_interpolation_filling=iwls_api_config.time_series.threshold_interpolation_filling,
    )

    # Export the water level data for each station
    station_titles: list[str] = export_station_water_levels(
        wl_combineds=wl_combineds,
        gdf_voronoi=gdf_voronoi,
        export_tide_path=export_tide_path,
    )

    # Plot the water level data for each station
    if wl_combineds:
        plot_water_level_data(
            wl_combineds=wl_combineds,
            station_titles=station_titles,
            export_path=export_tide_path / "WaterLevel.html",
        )

    LOGGER.debug(f"Exceptions : {wl_exceptions}.")
    LOGGER.debug(wl_combineds)

    # Georeference the bathymetry data
    processed_data: gpd.GeoDataFrame[schema.DataLoggerSchema] = (
        georeference.georeference_bathymetry(
            data=gdf_data_tide_zone,
            water_level=wl_combineds,
            waterline=waterline,
            sounder=sounder,
            water_level_tolerance=data_georef_config.water_level_tolerance,
        )
    )

    LOGGER.debug(processed_data)
    for idx, row in processed_data.head(5).iterrows():
        LOGGER.debug(row)

    # Export the processed data
    output_path: Path = export_data_path / "ProcessedData.gpkg"
    LOGGER.info(f"Exportation des données traitées : {output_path}.")
    export.export_geodataframe_to_gpkg(
        geodataframe=processed_data, output_path=output_path
    )


if __name__ == "__main__":
    import sys
    from cli import cli

    if sys.argv[1:]:
        LOGGER.info(f"Ligne de commande exécutée : {' '.join(sys.argv)}")
        cli()

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
        source_path = ROOT / "ingestion" / "Lowrance" / "Tuktoyaktuk"
        return list(source_path.glob("*.csv"))

    def get_blackbox_files() -> list[Path]:
        return [ROOT / "ingestion" / "BlackBox" / "NMEALOG.TXT"]

    def get_actisense_files() -> list[Path]:
        return [
            ROOT / "ingestion" / "ActiSense" / "composite_RDL_2024_ALL.n2kdecoded.csv"
        ]

    # Get the files to parse
    files_path: list[Path] = get_ofm_files()
    # files_path: list[Path] = get_dcdb_files()
    # files_path: list[Path] = get_lowrance_files()
    # files_path: list[Path] = get_blackbox_files()
    # files_path: list[Path] = get_actisense_files()
    # files_path: list[Path] = (
    #     get_ofm_files()
    #     + get_dcdb_files()
    #     + get_lowrance_files()
    #     + get_blackbox_files()
    #     + get_actisense_files()
    # )

    processing_workflow(files=files_path, vessel_id="Tuktoyaktuk", output=OUTPUT)

    # todo gérer la valeur np.nan dans les configurations des capteurs

    # todo dans ce fichier, dans le fichier de configuration CONFIG_csb-processing.toml et dans tide.time_serie.time_serie_dataframe et transformation.georeference

    # todo ajouter ttl pour l'instanciation de StationHandler
