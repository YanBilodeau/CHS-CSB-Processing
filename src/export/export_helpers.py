"""
Module d'exportation des données traitées.

Ce module contient des fonctions utilitaires pour finaliser, séparer et exporter les données traitées.
"""

import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Optional, Collection

import geopandas as gpd
import i18n
import pandas as pd
from loguru import logger

from schema import model_ids as schema_ids
import schema
from .factory_export import FileTypes, export_geodataframe


LOGGER = logger.bind(name="CSB-Processing.Export.Helpers")


def get_export_file_name(
    data_geodataframe: gpd.GeoDataFrame,
    datalogger_type: str,
    vessel_name: Optional[str],
) -> str:
    """
    Récupère le nom du fichier d'exportation.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param datalogger_type: Type de capteur.
    :type datalogger_type: str
    :param vessel_name: Nom du navire.
    :type vessel_name: Optional[str]
    :return: Nom du fichier d'exportation.
    :rtype: str
    """
    return (
        f"CH-"
        f"{datalogger_type}-"
        f"{vessel_name if vessel_name else 'Unknown'}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].min().strftime('%Y%m%d')}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].max().strftime('%Y%m%d')}"
    )


def finalize_geodataframe(data_geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Finalise le GeoDataFrame des données.

    :param data_geodataframe: GeoDataFrame des données.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: GeoDataFrame des données finalisé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(i18n.t("export.export_helpers.finalizing_geodataframe"))

    # Création vectorisée des objets WaterLevelInfo
    water_level_infos = [
        schema.WaterLevelInfo(
            water_level_meter=wl_meter,
            time_series=ts,
            id=zone_id,
            code=zone_code,
            name=zone_name,
        )
        for wl_meter, ts, zone_id, zone_code, zone_name in zip(
            data_geodataframe[schema_ids.WATER_LEVEL_METER],
            data_geodataframe[schema_ids.TIME_SERIE],
            data_geodataframe[schema_ids.TIDE_ZONE_ID],
            data_geodataframe[schema_ids.TIDE_ZONE_CODE],
            data_geodataframe[schema_ids.TIDE_ZONE_NAME],
        )
    ]

    data_geodataframe[schema_ids.WATER_LEVEL_INFO] = water_level_infos

    return data_geodataframe[schema.DataLoggerSchema.__annotations__.keys()]


def split_data_by_iho_order(
    data_geodataframe: gpd.GeoDataFrame,
) -> dict[str, gpd.GeoDataFrame]:
    """
    Regroupe et sépare le GeoDataFrame par ordre IHO.

    :param data_geodataframe: Le GeoDataFrame à séparer.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: Un dictionnaire contenant les GeoDataFrames séparés par ordre IHO.
    :rtype: dict[str, gpd.GeoDataFrame]
    """
    LOGGER.debug(i18n.t("export.export_helpers.splitting_by_iho_order"))

    grouped_data = {}
    for iho_order, group in data_geodataframe.groupby(
        schema_ids.IHO_ORDER
    ):  # todo : dropna=False ?
        key = "NAN" if pd.isna(iho_order) else str(iho_order)
        grouped_data[key] = group
        LOGGER.debug(
            i18n.t(
                "export.export_helpers.iho_order_group",
                iho_order=iho_order,
                count=f"{len(group):,}",
            )
        )

    LOGGER.debug(
        i18n.t("export.export_helpers.iho_order_keys", keys=grouped_data.keys())
    )

    return grouped_data


def export_processed_data(
    data_geodataframe: gpd.GeoDataFrame,
    output_data_path: Path,
    file_type: FileTypes,
    resolution: float,
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
    :param resolution: Résolution pour les formats raster.
    :type resolution: float
    """
    if file_type == FileTypes.CSAR and "config_caris" not in kwargs:
        LOGGER.warning(i18n.t("export.export_helpers.caris_config_required"))

    logger.info(
        i18n.t(
            "export.export_helpers.exporting_data",
            count=f"{len(data_geodataframe):,}",
            file_type=file_type,
            output_path=output_data_path,
        )
    )

    try:
        export_geodataframe(
            geodataframe=data_geodataframe,
            file_type=file_type,
            output_path=output_data_path,
            resolution=resolution,
            **kwargs,
        )
        LOGGER.success(
            i18n.t(
                "export.export_helpers.export_success",
                file_type=file_type,
                output_path=output_data_path,
            )
        )

    except Exception as error:
        LOGGER.error(
            i18n.t(
                "export.export_helpers.export_error",
                file_type=file_type,
                error=error,
            )
        )


def export_processed_data_to_file_types(
    data_geodataframe: gpd.GeoDataFrame,
    output_base_path: Path,
    file_types: Collection[FileTypes],
    resolution: Optional[float] = 0.00005,
    groub_by_iho_order: Optional[bool] = True,
    **kwargs,
) -> None:
    """
    Exporte les données traitées dans plusieurs formats de fichier.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param output_base_path: Chemin de base pour les fichiers d'exportation.
    :type output_base_path: Path
    :param file_types: Liste des types de fichiers de sortie.
    :type file_types: Collection[FileTypes]
    :param resolution: Résolution pour les formats raster.
    :type resolution: float
    :param groub_by_iho_order: Regrouper les données par ordre IHO.
    :type groub_by_iho_order: bool
    """
    grouped_data: dict[str | None, gpd.GeoDataFrame] = {"ALL": data_geodataframe}

    if groub_by_iho_order:
        iho_order_data: dict[str | None, gpd.GeoDataFrame] = split_data_by_iho_order(
            data_geodataframe=data_geodataframe
        )
        grouped_data.update(iho_order_data)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for group_key, group_df in grouped_data.items():
            if group_df.empty:
                continue

            suffix = "" if group_key == "ALL" else f"_{group_key}"
            output_path = output_base_path.with_name(f"{output_base_path.name}{suffix}")

            for file_type in file_types:
                executor.submit(
                    export_processed_data,
                    data_geodataframe=group_df,
                    output_data_path=output_path,
                    file_type=file_type,
                    resolution=resolution,
                    **kwargs,
                )


def export_metadata(
    data_geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    vessel_config,
    tide_stations: Optional[Collection[str]],
    decimal_precision: int,
    nbins_x: Optional[int] = 35,
    nbins_y: Optional[int] = 35,
    vessel_name: Optional[str] = None,
    software_version: str = "",
    processing_context=None,
    output_file_name: Optional[str] = None,
) -> None:
    """
    Exporte les métadonnées d'un levé CSB (JSON + rapport graphique).

    :param data_geodataframe: Données traitées.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param output_path: Répertoire de sortie (le fichier JSON sera nommé automatiquement).
    :type output_path: Path
    :param vessel_config: Configuration du navire.
    :param tide_stations: Liste des stations de marées utilisées.
    :type tide_stations: Optional[Collection[str]]
    :param decimal_precision: Précision des décimales.
    :type decimal_precision: int
    :param nbins_x: Nombre de colonnes dans les graphiques.
    :type nbins_x: Optional[int]
    :param nbins_y: Nombre de lignes dans les graphiques.
    :type nbins_y: Optional[int]
    :param vessel_name: Nom du navire pour l'export (surcharge vessel_config.name).
    :type vessel_name: Optional[str]
    :param software_version: Version du logiciel à inscrire dans les métadonnées.
    :type software_version: str
    :param processing_context: Contexte de traitement (type capteur, statut réduction).
    :param output_file_name: Nom de fichier de sortie forcé (surcharge le nom calculé automatiquement).
        Utilisé en mode split (merge_files=False) pour conserver le nom du fichier d'entrée.
    :type output_file_name: Optional[str]
    """
    import metadata as _metadata

    effective_vessel_name: str = vessel_name or vessel_config.name
    name: str = output_file_name or get_export_file_name(
        data_geodataframe=data_geodataframe,
        vessel_name=effective_vessel_name,
        datalogger_type=(
            processing_context.datalogger_type if processing_context else None
        ),
    )
    json_output_path: Path = output_path / f"{name}_metadata.json"

    LOGGER.info(
        i18n.t("export.export_helpers.exporting_metadata", output_path=json_output_path)
    )

    min_time: datetime = data_geodataframe[schema_ids.TIME_UTC].min()
    max_time: datetime = data_geodataframe[schema_ids.TIME_UTC].max()
    attributes = vessel_config.get_sensor_config_by_datetime(
        "attribute", min_time, max_time
    )
    waterline = vessel_config.get_sensor_config_by_datetime(
        "waterline", min_time, max_time
    )
    sounder = vessel_config.get_sensor_config_by_datetime("sounder", min_time, max_time)

    survey_metadata = _metadata.CSBmetadata(
        start_date=min_time.strftime("%Y-%m-%d"),
        end_date=max_time.strftime("%Y-%m-%d"),
        vessel=f"{vessel_config.id} - {effective_vessel_name}",
        sounding_hardware=(
            f"{processing_context.datalogger_type if processing_context else ''} - {attributes.sdghdw}"
        ),
        sounding_technique=attributes.tecsou,
        sounder_draft=(
            processing_context.resolve_sounder_draft(sounder, waterline)
            if processing_context is not None
            else sounder.z - waterline.z
        ),
        sotfware_version=software_version,
        tide_stations=tide_stations,
        processing_context=processing_context,
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
        iho_order_statistic=_metadata.classify_iho_order(
            data_geodataframe=data_geodataframe, decimal_precision=decimal_precision
        ),
        positioning_method=_metadata.get_positioning_method(
            processing_context.datalogger_type
            if processing_context is not None
            else None
        ),
    )

    _metadata.export_metadata_to_json(
        metadata=survey_metadata, output_path=json_output_path
    )

    _metadata.plot_metadata(
        metadata=survey_metadata.__dict__(),
        title=name,
        output_path=json_output_path,
        dataframe=data_geodataframe,
        nbins_x=nbins_x,
        nbins_y=nbins_y,
    )


def export_processed_data_and_metadata(
    data_geodataframe: gpd.GeoDataFrame,
    export_data_path: Path,
    vessel_config,
    processing_config,
    caris_api_config=None,
    tide_stations: Optional[Collection[str]] = None,
    vessel_name: Optional[str] = None,
    software_version: str = "",
    processing_context=None,
    output_file_name: Optional[str] = None,
) -> None:
    """
    Finalise, exporte les données traitées et génère les métadonnées.

    :param data_geodataframe: Données géoréférencées traitées.
    :type data_geodataframe: gpd.GeoDataFrame
    :param export_data_path: Répertoire de sortie pour les données.
    :type export_data_path: Path
    :param vessel_config: Configuration du navire.
    :param processing_config: Configuration du traitement.
    :param caris_api_config: Configuration de l'API Caris (optionnel).
    :param tide_stations: Liste des stations de marées.
    :type tide_stations: Optional[Collection[str]]
    :param vessel_name: Nom du navire pour l'export (surcharge vessel_config.name).
    :type vessel_name: Optional[str]
    :param software_version: Version du logiciel à inscrire dans les métadonnées.
    :type software_version: str
    :param processing_context: Contexte de traitement (type capteur, statut réduction).
    :param output_file_name: Nom de fichier de sortie forcé (surcharge le nom calculé automatiquement).
        Utilisé en mode split (merge_files=False) pour conserver le nom du fichier d'entrée.
    :type output_file_name: Optional[str]
    """
    effective_vessel_name: str = vessel_name or vessel_config.name

    data_geodataframe = finalize_geodataframe(data_geodataframe=data_geodataframe)

    computed_name: str = output_file_name or get_export_file_name(
        data_geodataframe=data_geodataframe,
        vessel_name=effective_vessel_name,
        datalogger_type=(
            processing_context.datalogger_type if processing_context else None
        ),
    )
    output_base_path: Path = export_data_path / computed_name

    export_processed_data_to_file_types(
        data_geodataframe=data_geodataframe,
        output_base_path=output_base_path,
        file_types=processing_config.export.export_format,
        config_caris=caris_api_config,
        resolution=processing_config.export.resolution,
        groub_by_iho_order=processing_config.export.group_by_iho_order,
    )

    export_metadata(
        data_geodataframe=data_geodataframe,
        output_path=export_data_path,
        vessel_config=vessel_config,
        tide_stations=tide_stations,
        decimal_precision=processing_config.options.decimal_precision,
        nbins_x=processing_config.plot.nbin_x,
        nbins_y=processing_config.plot.nbin_y,
        vessel_name=effective_vessel_name,
        software_version=software_version,
        processing_context=processing_context,
        output_file_name=output_file_name,
    )
