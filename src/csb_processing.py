"""
Module principal pour le traitement des données des capteurs à bord des navires.

Ce module contient le workflow de traitement des données des capteurs à bord des navires. Les données des capteurs sont
récupérées à partir de fichiers bruts, nettoyées, filtrées, géoréférencées et exportées dans un format standardisé.
"""

import concurrent.futures
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Collection, Sequence

import geopandas as gpd
from loguru import logger
import pandas as pd

import config
import export
from config.processing_config import FileTypes
from ingestion import factory_parser, DataLoggerType
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
import vessel as vessel_manager


LOGGER = logger.bind(name="CSB-Processing.WorkFlow")
configure_logger()

CONFIG_FILE: Path = Path(__file__).parent / "CONFIG_csb-processing.toml"


@dataclass(frozen=True)
class VesselConfigManagerError(Exception):
    """
    Exception levée lorsque la configuration du gestionnaire de navires est manquante pour récupérer la configuration du navire.
    """

    vessel_id: str
    """L'identifiant du navire."""
    vessel_config_manager: Optional[config.VesselManagerConfig]
    """La configuration du gestionnaire de navires."""

    def __str__(self) -> str:
        return (
            f"La configuration du gestionnaire de navires [{self.vessel_config_manager}] est "
            f"manquante ou incomplète pour récupérer la configuration du navire : {self.vessel_id}."
        )


def get_data_structure(output_path: Path) -> tuple[Path, Path, Path]:
    """
    Récupère la structure de répertoires pour les données.

    :param output_path: Chemin du répertoire de sortie.
    :type output_path: Path
    :return: Chemin des répertoires pour les données.
    :rtype: tuple[Path, Path, Path]
    """
    LOGGER.debug(
        f"Initialisation de la structure de répertoires pour les données : {output_path}."
    )

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


def get_iwls_environment(iwls_config: config.IWLSAPIConfig) -> iwls.APIEnvironment:
    """
    Réccupère l'environnement de l'API IWLS à partir du fichier de configuration.

    :param iwls_config: Configuration de l'API IWLS.
    :type iwls_config: IWLSAPIConfig
    :return: Environnement de l'API IWLS.
    :rtype: APIEnvironment
    """
    activated_profile: iwls.EnvironmentType = iwls_config.profile.active
    activated_environment: iwls.APIEnvironment = iwls_config.__dict__.get(
        activated_profile
    )

    LOGGER.debug(
        f"Chargement du profil '{iwls_config.profile.active}' pour l'API IWLS. [{activated_environment}]."
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
    endpoint_type: stations.EndpointTypeProtocol,
    api: stations.IWLSapiProtocol,
    ttl: int,
    cache_path: Path,
) -> stations.StationsHandlerABC:
    """
    Récupère le gestionnaire des stations.

    :param endpoint_type: Type de l'endpoint.
    :type endpoint_type: EndpointTypeProtocol
    :param api: API IWLS.
    :type api: IWLSapiProtocol
    :param ttl: Durée de vie du cache.
    :type ttl: int
    :param cache_path: Chemin du répertoire du cache.
    :type cache_path: Path
    :return: Gestionnaire des stations.
    :rtype: StationsHandlerABC
    """
    return stations.get_stations_factory(enpoint_type=endpoint_type)(
        api=api, ttl=ttl, cache_path=cache_path
    )


@schema.validate_schemas(
    data_geodataframe=schema.DataLoggerWithTideZoneSchema,
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
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
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
        schema_ids.WATER_LEVEL_INFO,
        schema_ids.UNCERTAINTY,
        schema_ids.GEOMETRY,
        schema_ids.ID,
        schema_ids.CODE,
        schema_ids.NAME,
        schema_ids.TIME_SERIE,
    ]

    gdf_data_time_zone: gpd.GeoDataFrame[
        schema.DataLoggerWithTideZoneSchema
    ] = gpd.sjoin(
        data_geodataframe,
        tide_zone,
        how="left",
        predicate="within",
    )[
        columns
    ].rename(
        columns={
            schema_ids.ID: schema_ids.TIDE_ZONE_ID,
            schema_ids.CODE: schema_ids.TIDE_ZONE_CODE,
            schema_ids.NAME: schema_ids.TIDE_ZONE_NAME,
        }
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
    :param tide_zone: Les zones de marées.
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
        data_geodataframe[data_geodataframe[schema_ids.DEPTH_PROCESSED_METER].isna()]
        .groupby(schema_ids.TIDE_ZONE_ID)[schema_ids.TIME_UTC]
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


def get_station_title(gdf_voronoi: gpd.GeoDataFrame, station_id: str) -> str:
    """
    Récupère le titre de la station.

    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema]
    :param station_id: Identifiant de la station.
    :type station_id: str
    :return: Titre de la station.
    :rtype: str
    """
    return (
        f"{voronoi.get_name_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)} "
        f"({voronoi.get_code_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)})"
    )


def export_station_water_levels(
    wl_combineds: dict[str, pd.DataFrame],
    gdf_voronoi: gpd.GeoDataFrame,
    export_tide_path: Path,
) -> None:
    """
    Exporte les données de niveaux d'eau pour chaque station dans des fichiers CSV.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: dict[str, pd.DataFrame]
    :param gdf_voronoi: GeoDataFrame contenant les informations des stations.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers CSV.
    :type export_tide_path: Path
    """
    for station_id, wl_dataframe in wl_combineds.items():
        export_water_level_dataframe(
            station_title=get_station_title(
                gdf_voronoi=gdf_voronoi, station_id=station_id
            ),
            wl_dataframe=wl_dataframe,
            export_tide_path=export_tide_path,
        )


def export_plot_water_level_data(
    wl_combineds: Collection[pd.DataFrame],
    station_titles: Sequence[str],
    export_path: Path,
) -> None:
    """
    Trace les données de niveaux d'eau pour chaque station et les enregistre dans un fichier HTML.

    :param wl_combineds: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds: Collection[pd.DataFrame]
    :param station_titles: Liste des titres des stations.
    :type station_titles: Sequence[str]
    :param export_path: Chemin du répertoire d'exportation des fichiers HTML.
    :type export_path: Path
    """
    LOGGER.info(
        f"Enregistrement des graphiques des données de niveaux d'eau {station_titles}: {export_path}."
    )

    plot_time_series_dataframe(
        dataframes=wl_combineds,
        titles=station_titles,
        show_plot=False,  # Afficher le graphique dans un navigateur web
        output_path=export_path,  # Exporter le graphique dans un fichier HTML
    )


def plot_water_levels(
    wl_combineds_dict: dict[str, list[pd.DataFrame]],
    stations_handler: stations.StationsHandlerABC,
    time_series: Collection[iwls.TimeSeries],
    export_tide_path: Path,
) -> None:
    """
    Trace les données de niveaux d'eau pour chaque station et les enregistre dans un fichier HTML.

    :param wl_combineds_dict: Dictionnaire contenant les DataFrames des niveaux d'eau par station.
    :type wl_combineds_dict: dict[str, list[pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]]
    :param stations_handler: Gestionnaire des stations.
    :type stations_handler: stations.StationsHandlerABC
    :param time_series: Liste des séries temporelles.
    :type time_series: Collection[iwls.TimeSeries]
    :param export_tide_path: Chemin du répertoire d'exportation des fichiers HTML.
    :type export_tide_path: Path
    """
    wl_combineds_list = [
        pd.concat(value)
        .drop_duplicates(subset=[schema_ids.EVENT_DATE])
        .reset_index(drop=True)
        .sort_values(by=schema_ids.EVENT_DATE)
        for value in wl_combineds_dict.values()
    ]

    gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneInfoSchema] = (
        voronoi.get_voronoi_geodataframe(
            stations_handler=stations_handler,
            time_series=time_series,
        )
    )
    station_titles_list: list[str] = [
        get_station_title(
            gdf_voronoi=gdf_voronoi,
            station_id=key,
        )
        for key in wl_combineds_dict.keys()
    ]

    export_plot_water_level_data(
        wl_combineds=wl_combineds_list,
        station_titles=station_titles_list,
        export_path=export_tide_path / "WaterLevel.html",
    )


def get_sensors_by_datetime(
    vessel_config: vessel_manager.VesselConfig, min_time: datetime, max_time: datetime
) -> tuple[vessel_manager.Sensor, vessel_manager.Waterline]:
    """
    Méthode pour récupérer les données des capteurs et valider que la configuration du navire couvre la période de temps.

    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param min_time: Date et heure minimale.
    :type min_time: datetime
    :param max_time: Date et heure maximale.
    :type max_time: datetime
    :return: Données des capteurs pour le moment donné.
    :rtype: tuple[vessel_manager.Sensor, vessel_manager.Waterline]
    """
    sounder: vessel_manager.Sensor = vessel_config.get_sensor_config_by_datetime(
        "sounder", min_time, max_time
    )
    waterline: vessel_manager.Waterline = vessel_config.get_sensor_config_by_datetime(
        "waterline", min_time, max_time
    )

    return sounder, waterline


def finalize_geodataframe(data_geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Finalise le GeoDataFrame des données.

    :param data_geodataframe: GeoDataFrame des données.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: GeoDataFrame des données finalisé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(f"Finalisation du GeoDataFrame des données.")

    data_geodataframe[schema_ids.WATER_LEVEL_INFO] = data_geodataframe.apply(
        lambda row: schema.WaterLevelInfo(
            water_level_meter=row[schema_ids.WATER_LEVEL_METER],
            time_series=row[schema_ids.TIME_SERIE],
            id=row[schema_ids.TIDE_ZONE_ID],
            code=row[schema_ids.TIDE_ZONE_CODE],
            name=row[schema_ids.TIDE_ZONE_NAME],
        ),
        axis=1,
    )

    return data_geodataframe[schema.DataLoggerSchema.__annotations__.keys()]


def get_export_file_name(
    data_geodataframe: gpd.GeoDataFrame,
    vessel_config: vessel_manager.VesselConfig,
    datalogger_type: DataLoggerType,
) -> str:
    """
    Récupère le nom du fichier d'exportation.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    :return: Nom du fichier d'exportation.
    :rtype: str
    """
    return (
        f"CH-"
        f"{datalogger_type}-"
        f"{vessel_config.name if vessel_config.name else 'Unknown'}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].min().strftime('%Y%m%d')}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].max().strftime('%Y%m%d')}"
    )


def export_processed_data(
    data_geodataframe: gpd.GeoDataFrame,
    output_data_path: Path,
    file_type: export.FileTypes,
    **kwargs,
) -> None:
    """
    Exporte les données traitées dans un fichier GeoPackage.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param output_data_path: Chemin du répertoire d'exportation.
    :type output_data_path: Path
    :param file_type: Type de fichier de sortie.
    :type file_type: FileTypes
    """
    if "config_caris" not in kwargs and file_type == export.FileTypes.CSAR:
        LOGGER.warning(
            "La configuration de l'API Caris est requise pour exporter les données au format CSAR."
        )

    logger.info(
        f"Exportation des données traitées ({len(data_geodataframe)} sondes) au format {file_type} : {output_data_path}."
    )

    try:
        export.export_geodataframe(
            geodataframe=data_geodataframe,
            file_type=file_type,
            output_path=output_data_path,
            **kwargs,
        )
        LOGGER.success(
            f"Exportation des données traitées au format {file_type} complété."
        )

    except Exception as error:
        LOGGER.error(
            f"Erreur lors de l'exportation des données au format {file_type} : {error}."
        )


def export_processed_data_to_file_types(
    data_geodataframe: gpd.GeoDataFrame,
    export_data_path: Path,
    file_types: Collection[export.FileTypes],
    vessel_config: vessel_manager.VesselConfig,
    datalogger_type: DataLoggerType,
    **kwargs,
) -> None:
    """
    Exporte les données traitées dans plusieurs formats de fichier.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param export_data_path: Chemin du répertoire d'exportation.
    :type export_data_path: Path
    :param file_types: Liste des types de fichiers de sortie.
    :type file_types: Collection[FileTypes]
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    """
    data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = (
        finalize_geodataframe(data_geodataframe=data_geodataframe)
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        [
            executor.submit(
                export_processed_data,
                data_geodataframe=data_geodataframe,
                output_data_path=export_data_path
                / get_export_file_name(
                    data_geodataframe=data_geodataframe,
                    vessel_config=vessel_config,
                    datalogger_type=datalogger_type,
                ),
                file_type=file_type,
                **kwargs,
            )
            for file_type in file_types
        ]


def processing_workflow(
    files: Collection[Path],
    vessel: str | vessel_manager.VesselConfig,
    output: Path,
    config_path: Optional[Path] = CONFIG_FILE,
    apply_water_level: Optional[bool] = True,
) -> None:
    """
    Workflow de traitement des données.

    :param files: Liste des fichiers à traiter.
    :type files: Collection[Path]
    :param vessel: Identifiant du navire ou configuration du navire.
    :type vessel: str | vessel_manager.VesselConfig
    :param output: Chemin du répertoire de sortie.
    :type output: Path
    :param config_path: Chemin du fichier de configuration.
    :type config_path: Optional[Path]
    :param apply_water_level: Appliquer le niveau d'eau aux données.
    :type apply_water_level: Optional[bool]
    """
    if not files:
        LOGGER.warning(f"Aucun fichier à traiter.")
        return

    export_data_path, export_tide_path, log_path = get_data_structure(output)

    # Read the configuration file
    processing_config: config.CSBprocessingConfig = config.get_data_config(
        config_file=config_path
    )
    # Configure the logger
    configure_logger(
        log_path / f"{datetime.now().strftime('%Y-%m-%d')}_CSB-Processing.log",
        std_level=processing_config.options.log_level,
        log_file_level="DEBUG",
    )

    # Log the parameters of the workflow
    LOGGER.debug(
        f"Paramètres du workflow :\n"
        f"files = {files}\n"
        f"vessel = {vessel}\n"
        f"output = {output}\n"
        f"config_path = {config_path}\n"
        f"apply_water_level = {apply_water_level}"
    )

    # Get the configuration for the API Caris
    try:
        caris_api_config: config.CarisAPIConfig | None = (
            config.get_caris_api_config(config_file=config_path)
            if FileTypes.CSAR in processing_config.options.export_format
            else None
        )
    except config.CarisConfigError as error:
        if FileTypes.CSAR in processing_config.options.export_format:
            LOGGER.error(
                f"La configuration de Caris est obligatoire pour l'exportation en format *csar : {error}."
            )
            return

        raise error

    # Check if the vessel configuration is missing
    if (
        processing_config.vessel_manager is None
        or processing_config.vessel_manager.manager_type is None
        or not processing_config.vessel_manager.kwargs
    ) and isinstance(vessel, str):
        LOGGER.error(f"La configuration du gestionnaire de navires est manquante.")

        raise VesselConfigManagerError(
            vessel_id=vessel, vessel_config_manager=processing_config.vessel_manager
        )

    # Get the vessel configuration
    LOGGER.info(
        f"Récupération de la configuration du navire {vessel.id if isinstance(vessel, vessel_manager.VesselConfig) else vessel}."
    )
    # Get the sensors for the vessel
    vessel_config: vessel_manager.VesselConfig = vessel_manager.get_vessel_config(
        vessel, processing_config.vessel_manager
    )

    # Get the parser and the parsed data
    LOGGER.info(f"Récupération des données brutes des fichiers : {files}.")
    parser_files: factory_parser.ParserFiles = factory_parser.get_files_parser(
        files=files
    )

    LOGGER.debug(parser_files)

    if not parser_files.files:
        LOGGER.warning(f"Aucun fichier valide à traiter.")
        return

    # Parse the data
    data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        parser_files.parser.from_files(files=parser_files.files)
    )

    # Clean the data
    LOGGER.info(f"Nettoyage et filtrage des données.")
    data = cleaner.clean_data(data, data_filter=processing_config.filter)

    LOGGER.success(f"{len(data)} sondes valides récupérées.")

    sounder, waterline = get_sensors_by_datetime(
        vessel_config=vessel_config,
        min_time=data[schema_ids.TIME_UTC].min(),
        max_time=data[schema_ids.TIME_UTC].max(),
    )

    if not apply_water_level:
        LOGGER.info("Le niveau d'eau ne sera pas appliqué aux données.")

        # Georeference the bathymetry data
        data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
            georeference.georeference_bathymetry(
                data=data,
                water_level=None,
                waterline=waterline,
                sounder=sounder,
                water_level_tolerance=pd.Timedelta(
                    processing_config.georeference.water_level_tolerance
                ),
                apply_water_level=apply_water_level,
            )
        )

        export_processed_data_to_file_types(
            data_geodataframe=data,
            export_data_path=export_data_path,
            file_types=processing_config.options.export_format,
            vessel_config=vessel_config,
            datalogger_type=parser_files.datalogger_type,
            config_caris=caris_api_config,
        )

        return None

    # Read the configuration file
    iwls_api_config: config.IWLSAPIConfig = config.get_api_config(
        config_file=config_path
    )
    # Get the environment of the API IWLS from the configuration file and the active profile
    api_environment: iwls.APIEnvironment = get_iwls_environment(
        iwls_config=iwls_api_config
    )
    # Get the API IWLS from the environment
    api: stations.IWLSapiProtocol = get_api(environment=api_environment)
    # Get the handler of the stations
    stations_handler: stations.StationsHandlerABC = get_stations_handler(
        api=api,
        endpoint_type=api_environment.endpoint.TYPE,
        ttl=iwls_api_config.cache.ttl,
        cache_path=iwls_api_config.cache.cache_path,
    )

    excluded_stations: list[str] = []
    wl_combineds_dict: dict[
        str, list[pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    ] = defaultdict(list)

    last_run_stations: list[str] = []
    run: int = 1

    while run <= processing_config.options.max_iterations:
        LOGGER.info(
            f"Transformation des données : {run}. Stations exclues : {excluded_stations}."
        )
        # Get the Voronoi diagram of the stations. The stations are selected based on the priority of the time series.
        # The time series priority is defined in the configuration file.
        LOGGER.info("Récupération des zones de marée (diagramme de Voronoi).")
        gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
            voronoi.get_voronoi_geodataframe(
                stations_handler=stations_handler,
                time_series=iwls_api_config.time_series.priority,
                excluded_stations=excluded_stations,
            )
        )

        # Add the tide zone id to the data
        data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
            add_tide_zone_id_to_geodataframe(
                data_geodataframe=data, tide_zone=gdf_voronoi
            )
        )

        # Get the time and tide zone
        LOGGER.info(
            "Récupération des information sur les zones de marées qui intersetent les données brutes."
        )
        tide_zonde_info: pd.DataFrame = get_intersected_tide_zone_info(
            data_geodataframe=data,
            tide_zone=gdf_voronoi,
        )

        for zone, min_time, max_time, time_series in tide_zonde_info.itertuples(
            index=False
        ):
            LOGGER.info(
                f"Zone de marée {zone} : temps minimum - {min_time}, temps maximum - {max_time}, séries temporelles - {time_series}."
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
            buffer_time=pd.Timedelta(iwls_api_config.time_series.buffer_time),
            # Maximum time gap allowed for the data. The maximum time gap is defined in the configuration file.
            # If the gap is greater than this value, data from the next time series will be retrieved to fill
            # the gaps. For example, if the time series priority is [wlo, wlp] and the maximum time gap is 1 hour, the
            # data for the time series wlo will be retrieved first. If the gap between two consecutive
            # data points is greater than 1 hour, the data for the time series wlp will be retrieved to fill the gap.
            max_time_gap=iwls_api_config.time_series.max_time_gap,
            # Threshold for the interpolation versus filling of the gaps in the data.
            threshold_interpolation_filling=iwls_api_config.time_series.threshold_interpolation_filling,
        )
        # Add the water level data to the list for the plot
        for key, value in wl_combineds.items():
            wl_combineds_dict[key].append(value)

        # Export the water level data for each station
        export_station_water_levels(
            wl_combineds=wl_combineds,
            gdf_voronoi=gdf_voronoi,
            export_tide_path=export_tide_path,
        )

        # Log the exceptions
        LOGGER.debug(f"Exceptions : {wl_exceptions}.")
        LOGGER.debug(wl_combineds)

        if wl_combineds:
            # Export the Voronoi diagram to a GeoJSON file
            voronoi_output_path: Path = export_tide_path / f"StationVoronoi-{run}.gpkg"
            LOGGER.info(
                f"Exportation du diagramme de Voronoi des stations marégraphiques : {voronoi_output_path}."
            )
            export.export_geodataframe_to_gpkg(
                geodataframe=gdf_voronoi,
                output_path=export_tide_path / voronoi_output_path,
            )

            # Georeference the bathymetry data
            data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
                georeference.georeference_bathymetry(
                    data=data,
                    water_level=wl_combineds,
                    waterline=waterline,
                    sounder=sounder,
                    water_level_tolerance=pd.Timedelta(
                        processing_config.georeference.water_level_tolerance
                    ),
                    apply_water_level=apply_water_level,
                )
            )

        # Check if there are any missing values in the processed data
        if not data[schema_ids.DEPTH_PROCESSED_METER].isna().any():
            break

        # Add the stations with missing values to the excluded stations
        excluded_stations.extend(wl_exceptions.keys())

        # Check if the stations are the same as the last run and if there are no exceptions
        if not wl_exceptions and (last_run_stations == list(wl_combineds.keys())):
            excluded_stations.extend(list(wl_combineds.keys()))

        run += 1
        last_run_stations = list(wl_combineds.keys())

    # Plot the water level data for each station
    if wl_combineds_dict:
        plot_water_levels(
            wl_combineds_dict=wl_combineds_dict,
            stations_handler=stations_handler,
            time_series=iwls_api_config.time_series.priority,
            export_tide_path=export_tide_path,
        )

    # Export the processed data
    export_processed_data_to_file_types(
        data_geodataframe=data,
        export_data_path=export_data_path,
        file_types=processing_config.options.export_format,
        vessel_config=vessel_config,
        datalogger_type=parser_files.datalogger_type,
        config_caris=caris_api_config,
    )

    # todo gérer la valeur np.nan dans les configurations des capteurs

    # todo à ajouter au BaseModel ?
    #  [DATA.Georeference.tpu]
    #  base_tpu_wlo = 1
    #  base_tpu_wlp = 2
    # todo mettre en paramètre (wlo 1 ? et wlp 2 ?), mettre le coefficient et la constante en paramètre
    # todo tpu si apply_water_level=False ?

    # todo utilise cache pour les TimeSeries, peut-être utile si plusieurs itérations

    # todo dans ce fichier, dans tide.time_serie.time_serie_dataframe et transformation.georeference

    # todo Identification des périodes en enlevant les trous de x temps dans add_tide_zone_id_to_geodataframe

    # todo export en csar avec CarisBatchUtils -> mettre PACD ?
    # todo couche THU ?

    # todo -> mettre template pour le nom dans le fichier de config dans le fichier de config
    # todo Fichier de config de vessel centralisé ?
