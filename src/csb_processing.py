"""
Module principal pour le traitement des données des capteurs à bord des navires.

Ce module contient le workflow de traitement des données des capteurs à bord des navires. Les données des capteurs sont
récupérées à partir de fichiers bruts, nettoyées, filtrées, georéférencées et exportées dans un format standardisé.
"""

from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Collection, Iterable

from loguru import logger
import geopandas as gpd
import pandas as pd

from ingestion import factory_parser, DataLoggerType
from logger.loguru_config import configure_logger
from tide import voronoi, time_serie, tide_zone, water_level_export
import config
import export
import iwls_api
import metadata
import schema
import schema.model_ids as schema_ids
import filter.data_cleaning as cleaner
import transformation.georeference as georeference
import vessel as vessel_manager


__version__ = "0.7.3"


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


def classify_iho_order(
    data_geodataframe: gpd.GeoDataFrame, decimal_precision: int
) -> metadata.IHOorderQualifiquation:
    """
    Classifie l'ordre IHO des données.

    :param data_geodataframe: Données traitées à classifier.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :return: La qualification des données selon les ordres IHO.
    :rtype: IHOorderQualifiquation
    """
    LOGGER.debug(f"Classification de l'ordre IHO des données.")

    return metadata.classify_iho_order(
        data_geodataframe=data_geodataframe, decimal_precision=decimal_precision
    )


def export_metadata(
    data_geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    vessel_config: vessel_manager.VesselConfig,
    datalogger_type: DataLoggerType,
    tide_stations: Optional[Collection[str]],
    decimal_precision: int,
    nbins_x: Optional[int] = 35,
    nbins_y: Optional[int] = 35,
) -> None:
    """
    Exporte les métadonnées des données traitées.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param output_path: Chemin du répertoire d'exportation.
    :type output_path: Path
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    :param tide_stations: Liste des stations de marées.
    :type tide_stations: Optional[Collection[str]]
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :param nbins_x: Nombre de cellules pour l'axe des X dans les graphiques.
    :type nbins_x: Optional[int]
    :param nbins_y: Nombre de cellules pour l'axe des Y dans les graphiques.
    :type nbins_y: Optional[int]
    """
    name: str = export.get_export_file_name(
        data_geodataframe=data_geodataframe,
        vessel_name=vessel_config.name,
        datalogger_type=datalogger_type,
    )
    output_path: Path = output_path / f"{name}_metadata.json"

    LOGGER.info(f"Exportation des métadonnées des données traitées : {output_path}.")

    min_time: datetime = data_geodataframe[schema_ids.TIME_UTC].min()
    max_time: datetime = data_geodataframe[schema_ids.TIME_UTC].max()
    attributes: vessel_config.BDBattributes = (
        vessel_config.get_sensor_config_by_datetime("attribute", min_time, max_time)
    )
    waterline: vessel_manager.Waterline = vessel_config.get_sensor_config_by_datetime(
        "waterline", min_time, max_time
    )
    sounder: vessel_manager.Sensor = vessel_config.get_sensor_config_by_datetime(
        "sounder", min_time, max_time
    )

    survey_metadata: metadata.CSBmetadata = metadata.CSBmetadata(
        start_date=min_time.strftime("%Y-%m-%d"),
        end_date=max_time.strftime("%Y-%m-%d"),
        vessel=f"{vessel_config.id} - {vessel_config.name}",
        sounding_hardware=f"{datalogger_type} - {attributes.sdghdw}",
        sounding_technique=attributes.tecsou,
        sounder_draft=sounder.z - waterline.z,
        sotfware_version=__version__,
        tide_stations=tide_stations,
        tvu=(
            data_geodataframe[data_geodataframe[schema_ids.DEPTH_PROCESSED_METER] < 50][
                schema_ids.UNCERTAINTY
            ].max()
            if not data_geodataframe[
                data_geodataframe[schema_ids.DEPTH_PROCESSED_METER] < 50
            ].empty
            else data_geodataframe[schema_ids.UNCERTAINTY].max()
        ),
        thu=(
            data_geodataframe[data_geodataframe[schema_ids.DEPTH_PROCESSED_METER] < 50][
                schema_ids.THU
            ].max()
            if not data_geodataframe[
                data_geodataframe[schema_ids.DEPTH_PROCESSED_METER] < 50
            ].empty
            else data_geodataframe[schema_ids.THU].max()
        ),
        iho_order_statistic=classify_iho_order(
            data_geodataframe=data_geodataframe, decimal_precision=decimal_precision
        ),
    )

    metadata.export_metadata_to_json(metadata=survey_metadata, output_path=output_path)

    metadata.plot_metadata(
        metadata=survey_metadata.__dict__(),
        title=name,
        output_path=output_path,
        dataframe=data_geodataframe,
        nbins_x=nbins_x,
        nbins_y=nbins_y,
    )


def export_processed_data_and_metadata(
    data_geodataframe: gpd.GeoDataFrame,
    export_data_path: Path,
    vessel_config: vessel_manager.VesselConfig,
    datalogger_type: DataLoggerType,
    processing_config: config.CSBprocessingConfig,
    caris_api_config: Optional[config.CarisAPIConfig] = None,
    tide_stations: Optional[Collection[str]] = None,
) -> None:
    """
    Exporte les données traitées et les métadonnées.

    :param data_geodataframe: Données géoréférencées traitées.
    :type data_geodataframe: gpd.GeoDataFrame
    :param export_data_path: Chemin du répertoire d'exportation des données.
    :type export_data_path: Path
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    :param processing_config: Configuration du traitement.
    :type processing_config: config.CSBprocessingConfig
    :param caris_api_config: Configuration de l'API Caris.
    :type caris_api_config: Optional[config.CarisAPIConfig]
    :param tide_stations: Liste des stations de marées.
    :type tide_stations: Optional[Collection[str]]
    """
    # Finalize the geodataframe by ensuring correct data types, sorting and columns
    data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = (
        export.finalize_geodataframe(data_geodataframe=data_geodataframe)
    )

    # Define the base path for output files
    output_base_path: Path = export_data_path / export.get_export_file_name(
        data_geodataframe=data_geodataframe,
        vessel_name=vessel_config.name,
        datalogger_type=datalogger_type,
    )

    # Export the processed data
    export.export_processed_data_to_file_types(
        data_geodataframe=data_geodataframe,
        output_base_path=output_base_path,
        file_types=processing_config.export.export_format,
        config_caris=caris_api_config,
        resolution=processing_config.export.resolution,
        groub_by_iho_order=processing_config.export.group_by_iho_order,
    )

    # Export the metadata
    export_metadata(
        data_geodataframe=data_geodataframe,
        output_path=export_data_path,
        vessel_config=vessel_config,
        datalogger_type=datalogger_type,
        tide_stations=tide_stations,
        decimal_precision=processing_config.options.decimal_precision,
        nbins_x=processing_config.plot.nbin_x,
        nbins_y=processing_config.plot.nbin_y,
    )


def log_sounding_results(data: gpd.GeoDataFrame, iterations: int) -> bool:
    """
    Vérifie et affiche les résultats du traitement des sondes.

    :param data: Données géoréférencées.
    :type data: gpd.GeoDataFrame
    :param iterations: Nombre d'itérations effectuées.
    :type iterations: int
    :return: True si des sondes ont été traitées avec succès, False sinon.
    :rtype: bool
    """
    nan_sounding_count: int = data[schema_ids.DEPTH_PROCESSED_METER].isna().sum()
    sounding_count: int = data[schema_ids.DEPTH_PROCESSED_METER].notna().sum()

    if not sounding_count:
        LOGGER.warning(
            f"Aucune sonde n'a été réduite au zéro des cartes. Aucune information de niveau d'eau est disponible pour "
            f"ces dates et ces stations dans IWLS avec {iterations} itérations. Vous pouvez traiter les données "
            f"avec un nombre d'itération plus élevé ou sans appliquer le niveau d'eau (--apply-water-level False)."
        )
        return False

    (
        LOGGER.success(
            f"{sounding_count:,} sondes ont été réduites au zéro des cartes."
        )
        if not nan_sounding_count
        else LOGGER.info(
            f"{sounding_count:,} sondes ont été réduites au zéro des cartes. "
            f"{nan_sounding_count:,} sondes sont sans niveau d'eau pour la réduction."
        )
    )

    return True


def processing_workflow(
    files: Collection[Path],
    vessel: str | vessel_manager.VesselConfig,
    output: Path,
    config_path: Optional[Path] = CONFIG_FILE,
    apply_water_level: Optional[bool] = True,
    extra_logger: Optional[Iterable[dict]] = None,
    water_level_station: Optional[str] = None,
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
    :param extra_logger: Liste d'objets de configuration supplémentaires pour le logger.
    :type extra_logger: Optional[Iterable[dict]]
    :param water_level_station: Station de niveau d'eau à utiliser pour toutes les données. Si une station est
                                spécifiée, seulement cette station sera utilisée.
    :type water_level_station: Optional[str]
    """
    if not files:
        LOGGER.warning(f"Aucun fichier à traiter.")
        return None

    export_data_path, export_tide_path, log_path = get_data_structure(output)

    # Read the configuration file
    processing_config: config.CSBprocessingConfig = config.get_data_config(
        config_file=config_path
    )

    # Configure the logger
    configure_logger(
        log_path / f"CHS-CSB-Processing.log",
        std_level=processing_config.options.log_level,
        log_file_level="DEBUG",
        extra_logger=extra_logger,
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
            if config.FileTypes.CSAR in processing_config.export.export_format
            else None
        )
    except config.CarisConfigError as error:
        if config.FileTypes.CSAR in processing_config.export.export_format:
            LOGGER.error(
                f"La configuration de Caris est obligatoire pour l'exportation en format *csar : {error}."
            )
            return None

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
    datalogger_type: DataLoggerType = parser_files.datalogger_type

    LOGGER.debug(parser_files)

    if not parser_files.files:
        LOGGER.warning(f"Aucun fichier valide à traiter.")
        return None

    # Parse the data
    data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        parser_files.parser.from_files(files=parser_files.files)
    )

    if data.empty:
        LOGGER.warning(f"Aucune donnée valide à traiter.")
        return None

    # Clean the data
    LOGGER.info(f"Nettoyage et filtrage des données.")
    data = cleaner.clean_data(data, data_filter_config=processing_config.filter)
    if data.empty:
        LOGGER.warning(f"Aucune sonde valide à traiter.")
        return None

    LOGGER.success(f"{len(data):,} sondes valides récupérées.")

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
                georeference_config=processing_config.georeference,
                apply_water_level=apply_water_level,
                decimal_precision=processing_config.options.decimal_precision,
            )
        )

        export_processed_data_and_metadata(
            data_geodataframe=data,
            export_data_path=export_data_path,
            vessel_config=vessel_config,
            datalogger_type=datalogger_type,
            processing_config=processing_config,
            caris_api_config=caris_api_config,
            tide_stations=None,
        )

        return None

    # Initialize the IWLS API and the stations handler
    iwls_api_config, stations_handler = iwls_api.initialize_iwls_api(
        config_path=config_path
    )

    excluded_stations: list[str] = []
    wl_combineds_dict: dict[
        str, list[pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]  # type: ignore
    ] = defaultdict(list)

    last_run_stations: list[str] = []
    iteration: int = 0
    max_iterations: int = (
        processing_config.options.max_iterations if not water_level_station else 1
    )

    for iteration in range(1, max_iterations + 1):
        LOGGER.info(
            f"Transformation des données : {iteration}. Stations exclues : {excluded_stations}."
        )
        # Get the Voronoi diagram of the stations. The stations are selected based on the priority of the time series.
        # The time series priority is defined in the configuration file.
        LOGGER.info("Récupération des zones de marée (diagramme de Voronoi).")
        gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
            voronoi.get_voronoi_geodataframe(
                stations_handler=stations_handler,
                time_series=iwls_api_config.time_series.priority,
                excluded_stations=excluded_stations,
                water_level_station=water_level_station,
            )
        )

        # Add the tide zone id to the data
        data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
            tide_zone.add_tide_zone_id_to_geodataframe(
                data_geodataframe=data, tide_zone=gdf_voronoi
            )
        )

        # Get the time and tide zone
        LOGGER.info(
            "Récupération des information sur les zones de marées qui intersetent les données brutes."
        )
        tide_zonde_info: pd.DataFrame = tide_zone.get_intersected_tide_zone_info(
            data_geodataframe=data,
            tide_zone=gdf_voronoi,
        )

        if tide_zonde_info.empty:
            LOGGER.warning(
                f"Aucune zone de marée ne touche les données brutes restantes ("
                f"{data[schema_ids.DEPTH_PROCESSED_METER].isna().sum()} sondes). "
                f"Valider la position des sondes et les zones de marée."
            )
            break

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
            tide_zone_info=tide_zonde_info,
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
        water_level_export.export_station_water_levels(
            wl_combineds=wl_combineds,
            gdf_voronoi=gdf_voronoi,
            export_tide_path=export_tide_path,
        )

        # Log the exceptions
        LOGGER.debug(f"Exceptions : {wl_exceptions}.")
        LOGGER.debug(wl_combineds)

        if wl_combineds:
            # Export the Voronoi diagram to a GeoJSON file
            voronoi_output_path: Path = (
                export_tide_path / f"StationVoronoi-{iteration}.gpkg"
            )
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
                    georeference_config=processing_config.georeference,
                    apply_water_level=apply_water_level,
                    decimal_precision=processing_config.options.decimal_precision,
                )
            )

        # Check if there are any missing values in the processed data
        if not data[schema_ids.DEPTH_PROCESSED_METER].isna().any():
            break

        # Add the stations with missing values to the excluded stations
        excluded_stations.extend(wl_exceptions.keys())

        # Check if the stations are the same as the last iteration and if there are no exceptions
        if not wl_exceptions and (last_run_stations == list(wl_combineds.keys())):
            excluded_stations.extend(list(wl_combineds.keys()))

        last_run_stations = list(wl_combineds.keys())

    if not log_sounding_results(data=data, iterations=iteration):
        return None

    # Get the Voronoi diagram of the stations for the final plot
    gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
        voronoi.get_voronoi_geodataframe(
            stations_handler=stations_handler,
            time_series=iwls_api_config.time_series.priority,
        )
    )

    # Plot the water level data for each station
    if wl_combineds_dict:
        water_level_export.plot_water_levels(
            wl_combineds_dict=wl_combineds_dict,
            gdf_voronoi=gdf_voronoi,
            export_tide_path=export_tide_path,
        )

    export_processed_data_and_metadata(
        data_geodataframe=data,
        export_data_path=export_data_path,
        vessel_config=vessel_config,
        datalogger_type=datalogger_type,
        processing_config=processing_config,
        caris_api_config=caris_api_config,
        tide_stations=[
            get_station_title(gdf_voronoi=gdf_voronoi, station_id=station_id)
            for station_id in wl_combineds_dict.keys()
        ],
    )

    return None

    # todo gérer la valeur np.nan dans les configurations des capteurs

    # todo dans ce fichier, dans tide.time_serie.time_serie_dataframe, optimiser les opérations

    # todo -> mettre template pour le nom dans le fichier de config

    # todo : web app pour convert

    # todo : fichier vectoriel avec les stations et leurs incertitudes associées

    # todo : option pour prendre un fichier vectoriel en entré au lieu de calculer un voronoi
