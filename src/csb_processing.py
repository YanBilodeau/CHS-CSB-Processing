"""
Module principal pour le traitement des données des capteurs CSB.

Ce module expose :func:`processing_workflow`, le workflow end-to-end de traitement
des données de bathymétrie crowdsourcée (ingestion → nettoyage → géoréférencement →
export). Les helpers privés décomposent chaque étape en unités de ~20 lignes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Collection, Iterable

import i18n
from loguru import logger
import geopandas as gpd

from logger.loguru_config import configure_logger
from tide import voronoi, water_level_export, run_water_level_reduction
import config
import export
import ingestion
import iwls_api
import schema
import schema.model_ids as schema_ids
import transformation.georeference as georeference
import vessel as vessel_manager
from processing_context import ProcessingContext


__version__ = "0.8.0"

LOGGER = logger.bind(name="CSB-Processing.WorkFlow")
configure_logger()

CONFIG_FILE: Path = Path(__file__).parent / "CONFIG_csb-processing.toml"

# Ré-export pour compatibilité ascendante
# VesselConfigManagerError = vessel_manager.VesselConfigManagerError


@dataclass(frozen=True)
class WorkflowSetup:
    """
    Résultat de l'initialisation du workflow (répertoires, config, flags).

    :param export_data_path: Répertoire ``Data/`` de sortie.
    :type export_data_path: Path
    :param export_tide_path: Répertoire ``Tide/`` de sortie.
    :type export_tide_path: Path
    :param log_path: Répertoire ``Log/`` de sortie.
    :type log_path: Path
    :param processing_config: Configuration de traitement chargée et validée.
    :type processing_config: config.CSBprocessingConfig
    :param apply_water_level: Flag de réduction marégraphique (potentiellement forcé à
        ``False`` si ``already_at_chart_datum``).
    :type apply_water_level: bool
    """

    export_data_path: Path
    export_tide_path: Path
    log_path: Path
    processing_config: config.CSBprocessingConfig
    apply_water_level: bool


# ---------------------------------------------------------------------------
# Helpers privés — setup
# ---------------------------------------------------------------------------


def _setup_run(
    output: Path,
    config_path: Optional[Path],
    processing_config: Optional[config.CSBprocessingConfig],
    extra_logger: Optional[Iterable[dict]],
    apply_water_level: Optional[bool],
    already_at_chart_datum: bool,
) -> WorkflowSetup:
    """
    Crée les répertoires, charge la configuration et configure le logger.

    Force ``apply_water_level=False`` si ``already_at_chart_datum=True``.

    :param output: Racine du répertoire de sortie.
    :type output: Path
    :param config_path: Chemin du fichier de configuration TOML.
    :type config_path: Optional[Path]
    :param processing_config: Config pré-chargée (remplace ``config_path`` si fournie).
    :type processing_config: Optional[config.CSBprocessingConfig]
    :param extra_logger: Sinks loguru supplémentaires.
    :type extra_logger: Optional[Iterable[dict]]
    :param apply_water_level: Flag d'entrée (peut être ``None``).
    :type apply_water_level: Optional[bool]
    :param already_at_chart_datum: Si ``True``, force ``apply_water_level=False``.
    :type already_at_chart_datum: bool
    :return: Contexte d'exécution initialisé.
    :rtype: WorkflowSetup
    """
    export_data_path, export_tide_path, log_path = export.get_data_structure(output)

    configure_logger(
        log_path / "CHS-CSB-Processing.log",
        log_file_level="DEBUG",
        extra_logger=extra_logger,
    )
    if processing_config is None:
        processing_config = config.get_data_config(config_file=config_path)

    configure_logger(
        log_path / "CHS-CSB-Processing.log",
        std_level=processing_config.options.log_level,
        log_file_level="DEBUG",
        extra_logger=extra_logger,
    )

    effective_wl = bool(apply_water_level)
    if already_at_chart_datum and effective_wl:
        LOGGER.warning(i18n.t("csb_processing.already_at_chart_datum_warning"))
        effective_wl = False

    return WorkflowSetup(
        export_data_path=export_data_path,
        export_tide_path=export_tide_path,
        log_path=log_path,
        processing_config=processing_config,
        apply_water_level=effective_wl,
    )


def _get_caris_api_config(
    processing_config: config.CSBprocessingConfig,
    config_path: Optional[Path],
) -> Optional[config.CarisAPIConfig]:
    """
    Charge la configuration Caris si le format CSAR est demandé.

    Lève :exc:`config.CarisConfigError` (après log) si CSAR est demandé mais la
    configuration est invalide — le caller retourne alors ``None``.

    :param processing_config: Configuration de traitement.
    :type processing_config: config.CSBprocessingConfig
    :param config_path: Chemin du fichier de configuration TOML.
    :type config_path: Optional[Path]
    :return: Configuration Caris ou ``None`` si CSAR non demandé.
    :rtype: Optional[config.CarisAPIConfig]
    :raises config.CarisConfigError: Si CSAR est demandé mais la config Caris est invalide.
    """
    if config.FileTypes.CSAR not in processing_config.export.export_format:
        return None

    try:
        return config.get_caris_api_config(config_file=config_path)

    except config.CarisConfigError as error:
        LOGGER.error(i18n.t("csb_processing.caris_config_error", error=error))
        raise


def _get_vessel_config(
    vessel: str | vessel_manager.VesselConfig,
    processing_config: config.CSBprocessingConfig,
) -> vessel_manager.VesselConfig:
    """
    Valide le gestionnaire de navires et retourne la configuration du navire.

    :param vessel: Identifiant navire ou objet :class:`~vessel.VesselConfig`.
    :type vessel: str | vessel_manager.VesselConfig
    :param processing_config: Configuration de traitement.
    :type processing_config: config.CSBprocessingConfig
    :return: Configuration du navire.
    :rtype: vessel_manager.VesselConfig
    :raises vessel_manager.VesselConfigManagerError: Si l'identifiant est une chaîne mais
        que le gestionnaire de navires est absent ou incomplet.
    """
    if (
        processing_config.vessel_manager is None
        or processing_config.vessel_manager.manager_type is None
        or not processing_config.vessel_manager.kwargs
    ) and isinstance(vessel, str):
        LOGGER.error(i18n.t("csb_processing.vessel_manager_missing"))
        raise vessel_manager.VesselConfigManagerError(
            vessel_id=vessel, vessel_config_manager=processing_config.vessel_manager
        )

    vessel_id = vessel.id if isinstance(vessel, vessel_manager.VesselConfig) else vessel
    LOGGER.info(i18n.t("csb_processing.vessel_config_retrieving", vessel_id=vessel_id))

    return vessel_manager.get_vessel_config(vessel, processing_config.vessel_manager)


# ---------------------------------------------------------------------------
# Helpers privés — branches de traitement
# ---------------------------------------------------------------------------


def _process_without_water_level(
    data: gpd.GeoDataFrame,
    waterline,
    sounder,
    ctx: ProcessingContext,
    setup: WorkflowSetup,
    vessel_config: vessel_manager.VesselConfig,
    caris_api_config: Optional[config.CarisAPIConfig],
    vessel_name: Optional[str],
    output_file_name: Optional[str] = None,
) -> None:
    """
    Géoréférence sans réduction marégraphique et exporte les données.

    :param data: Données nettoyées.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param waterline: Configuration de la ligne d'eau.
    :param sounder: Configuration du sondeur.
    :param ctx: Contexte de traitement.
    :type ctx: ProcessingContext
    :param setup: Contexte d'exécution du workflow.
    :type setup: WorkflowSetup
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param caris_api_config: Configuration Caris (``None`` si CSAR non demandé).
    :type caris_api_config: Optional[config.CarisAPIConfig]
    :param vessel_name: Nom du navire pour l'export.
    :type vessel_name: Optional[str]
    :param output_file_name: Nom de fichier forcé (mode split). ``None`` → nom calculé.
    :type output_file_name: Optional[str]
    :rtype: None
    """
    LOGGER.info(i18n.t("csb_processing.no_water_level"))

    data = georeference.georeference_bathymetry(
        data=data,
        water_level=None,
        waterline=waterline,
        sounder=sounder,
        georeference_config=setup.processing_config.georeference,
        apply_water_level=setup.apply_water_level,
        decimal_precision=setup.processing_config.options.decimal_precision,
        processing_context=ctx,
    )
    export.export_processed_data_and_metadata(
        data_geodataframe=data,
        export_data_path=setup.export_data_path,
        vessel_config=vessel_config,
        processing_config=setup.processing_config,
        caris_api_config=caris_api_config,
        tide_stations=None,
        vessel_name=vessel_name,
        software_version=__version__,
        processing_context=ctx,
        output_file_name=output_file_name,
    )


def _process_with_water_level(
    data: gpd.GeoDataFrame,
    waterline,
    sounder,
    ctx: ProcessingContext,
    setup: WorkflowSetup,
    vessel_config: vessel_manager.VesselConfig,
    caris_api_config: Optional[config.CarisAPIConfig],
    vessel_name: Optional[str],
    water_level_stations: Optional[Collection[str]],
    excluded_stations: Optional[Collection[str]],
    config_path: Optional[Path],
    output_file_name: Optional[str] = None,
) -> None:
    """
    Exécute la boucle de réduction marégraphique IWLS, puis exporte les données.

    :param data: Données nettoyées.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param waterline: Configuration de la ligne d'eau.
    :param sounder: Configuration du sondeur.
    :param ctx: Contexte de traitement.
    :type ctx: ProcessingContext
    :param setup: Contexte d'exécution du workflow.
    :type setup: WorkflowSetup
    :param vessel_config: Configuration du navire.
    :type vessel_config: vessel_manager.VesselConfig
    :param caris_api_config: Configuration Caris.
    :type caris_api_config: Optional[config.CarisAPIConfig]
    :param vessel_name: Nom du navire pour l'export.
    :type vessel_name: Optional[str]
    :param water_level_stations: Stations forcées (``None`` → Voronoi automatique).
    :type water_level_stations: Optional[Collection[str]]
    :param excluded_stations: Codes de stations à exclure dès le départ.
    :type excluded_stations: Optional[Collection[str]]
    :param config_path: Chemin du fichier de configuration TOML.
    :type config_path: Optional[Path]
    :param output_file_name: Nom de fichier forcé (mode split). ``None`` → nom calculé.
    :type output_file_name: Optional[str]
    :rtype: None
    """
    iwls_api_config, stations_handler = iwls_api.initialize_iwls_api(
        config_path=config_path
    )
    resolved_excluded: list[str] = (
        [stations_handler.get_station_id_by_code(c) for c in excluded_stations]
        if excluded_stations
        else []
    )
    max_iterations: int = (
        setup.processing_config.options.max_iterations
        if not water_level_stations
        else 1
    )

    data, wl_combineds_dict, iteration = run_water_level_reduction(
        data=data,
        stations_handler=stations_handler,
        iwls_api_config=iwls_api_config,
        waterline=waterline,
        sounder=sounder,
        georeference_config=setup.processing_config.georeference,
        decimal_precision=setup.processing_config.options.decimal_precision,
        apply_water_level=setup.apply_water_level,
        processing_context=ctx,
        water_level_stations=water_level_stations,
        excluded_stations=resolved_excluded,
        max_iterations=max_iterations,
        export_tide_path=setup.export_tide_path,
    )

    if not log_sounding_results(data=data, iterations=iteration):
        return

    gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
        voronoi.get_voronoi_geodataframe(
            stations_handler=stations_handler,
            time_series=iwls_api_config.time_series.priority,
        )
    )
    if wl_combineds_dict:
        water_level_export.plot_water_levels(
            wl_combineds_dict=wl_combineds_dict,
            gdf_voronoi=gdf_voronoi,
            export_tide_path=setup.export_tide_path,
        )
    export.export_processed_data_and_metadata(
        data_geodataframe=data,
        export_data_path=setup.export_data_path,
        vessel_config=vessel_config,
        processing_config=setup.processing_config,
        caris_api_config=caris_api_config,
        tide_stations=[
            voronoi.get_station_title(gdf_voronoi=gdf_voronoi, station_id=sid)
            for sid in wl_combineds_dict.keys()
        ],
        vessel_name=vessel_name,
        software_version=__version__,
        processing_context=ctx,
        output_file_name=output_file_name,
    )


# ---------------------------------------------------------------------------
# Fonctions publiques
# ---------------------------------------------------------------------------


def run_processing_workflow(
    files: Collection[Path],
    merge_files: bool = True,
    **kwargs,
) -> None:
    """
    Dispatche le traitement en mode fusion ou mode split selon ``merge_files``.

    En mode fusion (défaut), tous les fichiers sont traités ensemble en un seul fichier
    de sortie nommé automatiquement. En mode split, chaque fichier est traité
    individuellement et le nom de sortie correspond au ``stem`` du fichier d'entrée.

    :param files: Fichiers bruts à traiter.
    :type files: Collection[Path]
    :param merge_files: Si ``True``, fusionne tous les fichiers en un seul traitement.
        Si ``False``, traite chaque fichier séparément.
    :type merge_files: bool
    :param kwargs: Arguments transmis directement à :func:`processing_workflow`.
    :rtype: None
    """
    files = list(files)

    if merge_files:
        LOGGER.info(i18n.t("csb_processing.merge_mode", count=len(files)))
        processing_workflow(files=files, **kwargs)
    else:
        LOGGER.info(i18n.t("csb_processing.split_mode", count=len(files)))
        for file in files:
            LOGGER.info(i18n.t("csb_processing.processing_file", filename=file.name))
            processing_workflow(files=[file], output_file_name=file.stem, **kwargs)


def log_sounding_results(data: gpd.GeoDataFrame, iterations: int) -> bool:
    """
    Vérifie et journalise les résultats du traitement des sondes.

    :param data: Données géoréférencées.
    :type data: gpd.GeoDataFrame
    :param iterations: Nombre d'itérations effectuées.
    :type iterations: int
    :return: ``True`` si au moins une sonde a été réduite au zéro des cartes.
    :rtype: bool
    """
    nan_count: int = data[schema_ids.DEPTH_PROCESSED_METER].isna().sum()
    ok_count: int = data[schema_ids.DEPTH_PROCESSED_METER].notna().sum()

    if not ok_count:
        LOGGER.warning(
            i18n.t(
                "csb_processing.no_soundings_reduced",
                iterations=iterations,
            )
        )
        return False

    if not nan_count:
        LOGGER.success(
            i18n.t("csb_processing.all_soundings_reduced", count=f"{ok_count:,}")
        )
    else:
        LOGGER.info(
            i18n.t(
                "csb_processing.partial_soundings_reduced",
                ok_count=f"{ok_count:,}",
                nan_count=f"{nan_count:,}",
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
    water_level_stations: Optional[Collection[str]] = None,
    excluded_stations: Optional[Collection[str]] = None,
    processing_config: Optional[config.CSBprocessingConfig] = None,
    vessel_name: Optional[str] = None,
    already_at_chart_datum: bool = False,
    output_file_name: Optional[str] = None,
) -> None:
    """
    Workflow de traitement des données CSB end-to-end.

    :param files: Fichiers bruts à traiter.
    :type files: Collection[Path]
    :param vessel: Identifiant navire ou objet :class:`~vessel.VesselConfig`.
    :type vessel: str | vessel_manager.VesselConfig
    :param output: Répertoire racine de sortie.
    :type output: Path
    :param config_path: Chemin du fichier de configuration TOML.
    :type config_path: Optional[Path]
    :param apply_water_level: Appliquer la réduction marégraphique.
    :type apply_water_level: Optional[bool]
    :param extra_logger: Sinks loguru supplémentaires (ex. NiceGUI).
    :type extra_logger: Optional[Iterable[dict]]
    :param water_level_stations: Codes de stations forcées (``None`` → Voronoi auto).
    :type water_level_stations: Optional[Collection[str]]
    :param excluded_stations: Codes de stations à exclure dès le départ.
    :type excluded_stations: Optional[Collection[str]]
    :param processing_config: Config pré-chargée (remplace ``config_path`` si fournie).
    :type processing_config: Optional[config.CSBprocessingConfig]
    :param vessel_name: Nom du navire pour l'export (surcharge vessel_config.name).
    :type vessel_name: Optional[str]
    :param already_at_chart_datum: ``True`` si les données sont déjà réduites au zéro
        des cartes — force ``apply_water_level=False``.
    :type already_at_chart_datum: bool
    :param output_file_name: Nom de fichier de sortie forcé (surcharge le nom calculé
        automatiquement). Utilisé en mode split (``merge_files=False``) pour conserver
        le nom du fichier d'entrée.
    :type output_file_name: Optional[str]
    :rtype: None
    """
    if not files:
        LOGGER.warning(i18n.t("csb_processing.no_files"))
        return None

    setup = _setup_run(
        output=output,
        config_path=config_path,
        processing_config=processing_config,
        extra_logger=extra_logger,
        apply_water_level=apply_water_level,
        already_at_chart_datum=already_at_chart_datum,
    )
    LOGGER.debug(
        i18n.t(
            "csb_processing.workflow_params",
            files=files,
            vessel=vessel,
            output=output,
            config_path=config_path,
            apply_water_level=setup.apply_water_level,
        )
    )

    try:
        caris_api_config = _get_caris_api_config(setup.processing_config, config_path)

    except config.CarisConfigError:
        return None

    vessel_config = _get_vessel_config(vessel, setup.processing_config)

    LOGGER.info(i18n.t("csb_processing.loading_raw_data", count=len(files)))
    ingestion_result = ingestion.load_and_clean_data(
        files=files,
        data_filter_config=setup.processing_config.filter,
        already_at_chart_datum=already_at_chart_datum,
    )

    if ingestion_result is None:
        return None

    data, ctx = ingestion_result

    sounder, waterline = vessel_manager.get_sensors_by_datetime(
        vessel_config=vessel_config,
        min_time=data[schema_ids.TIME_UTC].min(),
        max_time=data[schema_ids.TIME_UTC].max(),
    )

    if not setup.apply_water_level:
        return _process_without_water_level(
            data=data,
            waterline=waterline,
            sounder=sounder,
            ctx=ctx,
            setup=setup,
            vessel_config=vessel_config,
            caris_api_config=caris_api_config,
            vessel_name=vessel_name,
            output_file_name=output_file_name,
        )

    return _process_with_water_level(
        data=data,
        waterline=waterline,
        sounder=sounder,
        ctx=ctx,
        setup=setup,
        vessel_config=vessel_config,
        caris_api_config=caris_api_config,
        vessel_name=vessel_name,
        water_level_stations=water_level_stations,
        excluded_stations=excluded_stations,
        config_path=config_path,
        output_file_name=output_file_name,
    )

    # todo gérer la valeur np.nan dans les configurations des capteurs
    # todo optimiser les opérations dans tide.time_serie.time_serie_dataframe
    # todo mettre template pour le nom dans le fichier de config
    # todo web app pour convert
    # todo créer fichier vectoriel avec les stations et leurs incertitudes associées
    # todo option pour prendre un fichier vectoriel en entrée au lieu de calculer un voronoi

    # todo refaire le rapport pour style et theme comme dans S44-report
    # todo ajouter au métadonnée la longueur de ligne de sondage et le temps de sondage
