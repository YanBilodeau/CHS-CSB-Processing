"""
Module de réduction marégraphique itérative (boucle IWLS).

Ce module expose :func:`run_water_level_reduction` qui orchestre les itérations de
réduction au zéro des cartes, et les helpers privés qui décomposent chaque itération
en étapes discrètes et testables.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from loguru import logger
import i18n

from . import voronoi
from . import tide_zone_processing as tide_zone
from . import time_serie
from . import water_level_export
import export
import schema
import schema.model_ids as schema_ids
import transformation.georeference as georeference
from processing_context import ProcessingContext


LOGGER = logger.bind(name="CSB-Processing.Tide.WaterLevelWorkflow")


@dataclass(frozen=True)
class IterationResult:
    """
    Résultat d'une itération de réduction marégraphique.

    :param data: Données géoréférencées (ou avec zone de marée si pas de niveaux d'eau).
    :type data: gpd.GeoDataFrame
    :param wl_combineds: Séries temporelles de niveaux d'eau par station.
    :type wl_combineds: dict
    :param wl_exceptions: Stations en erreur lors de la récupération.
    :type wl_exceptions: dict
    """

    data: gpd.GeoDataFrame = field(compare=False, hash=False)
    wl_combineds: dict = field(compare=False, hash=False)
    wl_exceptions: dict = field(compare=False, hash=False)


def _export_voronoi(
    wl_combineds: dict,
    gdf_voronoi: gpd.GeoDataFrame,
    export_tide_path: Path,
    iteration: int,
) -> None:
    """
    Exporte le diagramme de Voronoi au format GPKG si des niveaux d'eau ont été récupérés.

    :param wl_combineds: Séries temporelles de niveaux d'eau par station.
    :type wl_combineds: dict
    :param gdf_voronoi: Diagramme de Voronoi des stations marégraphiques.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param export_tide_path: Répertoire d'export des fichiers marégraphiques.
    :type export_tide_path: Path
    :param iteration: Numéro de l'itération courante (pour nommer le fichier).
    :type iteration: int
    :rtype: None
    """
    if not wl_combineds:
        return

    gdf_voronoi = _join_station_uncertainty(gdf_voronoi)

    voronoi_path = export_tide_path / f"StationVoronoi-{iteration}.gpkg"
    LOGGER.info(
        i18n.t("tide.water_level_workflow.exporting_voronoi", path=voronoi_path)
    )
    export.export_geodataframe_to_gpkg(
        geodataframe=gdf_voronoi, output_path=voronoi_path
    )


def _join_station_uncertainty(gdf_voronoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Joint la colonne ``uncertainty_wlp_m`` depuis le fichier JSON des incertitudes station.

    La jointure se fait sur la colonne ``code`` du GeoDataFrame et les clés du JSON.
    Retourne une copie du GeoDataFrame avec la colonne ajoutée, ou le GeoDataFrame
    original si le fichier n'existe pas.

    :param gdf_voronoi: Diagramme de Voronoi des stations marégraphiques.
    :type gdf_voronoi: gpd.GeoDataFrame
    :return: GeoDataFrame avec la colonne ``uncertainty_wlp_m`` ajoutée.
    :rtype: gpd.GeoDataFrame
    """
    uncertainty_path = (
        Path(__file__).parent.parent
        / "static"
        / "uncertainty"
        / "station_uncertainty.json"
    )

    if not uncertainty_path.is_file():
        LOGGER.warning(
            i18n.t(
                "tide.water_level_workflow.uncertainty_file_not_found",
                path=uncertainty_path,
            )
        )
        return gdf_voronoi

    import json

    with uncertainty_path.open(encoding="utf-8") as f:
        uncertainty_data: dict = json.load(f)

    # Series indexée sur le code de station → colonne incertitude
    uncertainty_series = pd.Series(
        {k: v.get("uncertainty_m") for k, v in uncertainty_data.items()}
    )
    uncertainty_series.name = "uncertainty_m"

    gdf_voronoi = gdf_voronoi.copy()
    gdf_voronoi["uncertainty_wlp_m"] = gdf_voronoi[schema_ids.CODE].map(
        uncertainty_series
    )

    LOGGER.info(
        i18n.t(
            "tide.water_level_workflow.uncertainty_joined",
            count=len(gdf_voronoi),
        )
    )

    return gdf_voronoi


def _fetch_and_export_water_levels(
    data: gpd.GeoDataFrame,
    gdf_voronoi: gpd.GeoDataFrame,
    stations_handler,
    iwls_api_config,
    export_tide_path: Path,
    iteration: int,
) -> Optional[IterationResult]:
    """
    Ajoute les zones de marée, récupère les niveaux d'eau et exporte les artefacts de l'itération.

    Retourne ``None`` si aucune zone de marée n'intersecte les données — signal d'arrêt
    de la boucle.

    :param data: Données brutes avec colonnes de zone de marée à remplir.
    :type data: gpd.GeoDataFrame
    :param gdf_voronoi: Diagramme de Voronoi des stations marégraphiques.
    :type gdf_voronoi: gpd.GeoDataFrame
    :param stations_handler: Gestionnaire des stations IWLS.
    :param iwls_api_config: Configuration IWLS (séries temporelles, buffer, etc.).
    :param export_tide_path: Répertoire d'export des fichiers marégraphiques.
    :type export_tide_path: Path
    :param iteration: Numéro de l'itération courante (pour nommer le Voronoi exporté).
    :type iteration: int
    :return: :class:`IterationResult` ou ``None`` si aucune zone de marée intersecte.
    :rtype: Optional[IterationResult]
    """
    data = tide_zone.add_tide_zone_id_to_geodataframe(
        data_geodataframe=data, tide_zone=gdf_voronoi
    )
    tide_zone_info: pd.DataFrame = tide_zone.get_intersected_tide_zone_info(
        data_geodataframe=data, tide_zone=gdf_voronoi
    )
    if tide_zone_info.empty:
        LOGGER.warning(
            i18n.t(
                "tide.water_level_workflow.no_tide_zone_intersection",
                count=data[schema_ids.DEPTH_PROCESSED_METER].isna().sum(),
            )
        )
        return None

    for zone, min_time, max_time, time_series in tide_zone_info.itertuples(index=False):
        LOGGER.info(
            i18n.t(
                "tide.water_level_workflow.tide_zone_info",
                zone=zone,
                min_time=min_time,
                max_time=max_time,
                time_series=time_series,
            )
        )

    LOGGER.info(i18n.t("tide.water_level_workflow.fetching_water_levels"))
    wl_combineds, wl_exceptions = time_serie.get_water_level_data_for_stations(
        stations_handler=stations_handler,
        tide_zone_info=tide_zone_info,
        wlo_qc_flag_filter=iwls_api_config.time_series.wlo_qc_flag_filter,
        buffer_time=pd.Timedelta(iwls_api_config.time_series.buffer_time),
        max_time_gap=iwls_api_config.time_series.max_time_gap,
        threshold_interpolation_filling=iwls_api_config.time_series.threshold_interpolation_filling,
    )
    water_level_export.export_station_water_levels(
        wl_combineds=wl_combineds,
        gdf_voronoi=gdf_voronoi,
        export_tide_path=export_tide_path,
    )
    LOGGER.debug(
        i18n.t("tide.water_level_workflow.exceptions", exceptions=wl_exceptions)
    )

    _export_voronoi(wl_combineds, gdf_voronoi, export_tide_path, iteration)

    return IterationResult(
        data=data, wl_combineds=wl_combineds, wl_exceptions=wl_exceptions
    )


def _run_single_iteration(
    data: gpd.GeoDataFrame,
    gdf_voronoi: gpd.GeoDataFrame,
    stations_handler,
    iwls_api_config,
    waterline,
    sounder,
    georeference_config,
    decimal_precision: int,
    apply_water_level: bool,
    processing_context: Optional[ProcessingContext],
    export_tide_path: Path,
    iteration: int,
) -> Optional[IterationResult]:
    """
    Exécute une itération complète : fetch niveaux + géoréférencement.

    :return: :class:`IterationResult` avec données géoréférencées, ou ``None`` si
        aucune zone de marée n'intersecte (signal d'arrêt de boucle).
    :rtype: Optional[IterationResult]
    """
    result = _fetch_and_export_water_levels(
        data=data,
        gdf_voronoi=gdf_voronoi,
        stations_handler=stations_handler,
        iwls_api_config=iwls_api_config,
        export_tide_path=export_tide_path,
        iteration=iteration,
    )
    if result is None or not result.wl_combineds:
        return result

    georeferenced = georeference.georeference_bathymetry(
        data=result.data,
        water_level=result.wl_combineds,
        waterline=waterline,
        sounder=sounder,
        georeference_config=georeference_config,
        apply_water_level=apply_water_level,
        decimal_precision=decimal_precision,
        processing_context=processing_context,
    )
    return IterationResult(
        data=georeferenced,
        wl_combineds=result.wl_combineds,
        wl_exceptions=result.wl_exceptions,
    )


def _extend_excluded_stations(
    data: gpd.GeoDataFrame,
    wl_exceptions: dict,
    excluded_stations: list[str],
) -> None:
    """
    Étend la liste des stations exclues avec les stations en erreur et celles
    associées aux sondes encore sans niveau d'eau.

    :param data: Données après géoréférencement de l'itération.
    :type data: gpd.GeoDataFrame
    :param wl_exceptions: Stations ayant levé une exception lors de la récupération.
    :type wl_exceptions: dict
    :param excluded_stations: Liste mutée en place.
    :type excluded_stations: list[str]
    :rtype: None
    """
    excluded_stations.extend(wl_exceptions.keys())
    nan_tide_zones = (
        data[data[schema_ids.DEPTH_PROCESSED_METER].isna()][schema_ids.TIDE_ZONE_ID]
        .dropna()
        .unique()
    )
    excluded_stations.extend(nan_tide_zones)


def run_water_level_reduction(
    data: gpd.GeoDataFrame,
    stations_handler,
    iwls_api_config,
    waterline,
    sounder,
    georeference_config,
    decimal_precision: int,
    apply_water_level: bool,
    processing_context: Optional[ProcessingContext],
    water_level_stations: Optional[Collection[str]],
    excluded_stations: list[str],
    max_iterations: int,
    export_tide_path: Path,
) -> tuple[gpd.GeoDataFrame, dict, int]:
    """
    Orchestre la boucle de réduction marégraphique IWLS.

    À chaque itération, reconstruit le Voronoi sans les stations défaillantes,
    récupère les niveaux d'eau et géoréférence les sondes sans résultat.
    S'arrête dès que ``DEPTH_PROCESSED_METER`` ne contient plus de NaN ou que
    ``max_iterations`` est atteint.

    :param data: Données brutes à réduire.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param stations_handler: Gestionnaire des stations marégraphiques.
    :param iwls_api_config: Configuration IWLS.
    :param waterline: Configuration de la ligne d'eau.
    :param sounder: Configuration du sondeur.
    :param georeference_config: Configuration du géoréférencement.
    :param decimal_precision: Précision décimale pour l'arrondi.
    :type decimal_precision: int
    :param apply_water_level: Toujours ``True`` dans ce chemin d'exécution.
    :type apply_water_level: bool
    :param processing_context: Contexte de traitement.
    :type processing_context: Optional[ProcessingContext]
    :param water_level_stations: Stations forcées (``None`` → diagramme de Voronoi).
    :type water_level_stations: Optional[Collection[str]]
    :param excluded_stations: Stations à exclure (mutée à chaque itération).
    :type excluded_stations: list[str]
    :param max_iterations: Nombre maximum d'itérations.
    :type max_iterations: int
    :param export_tide_path: Répertoire d'export des artefacts marégraphiques.
    :type export_tide_path: Path
    :return: ``(data, wl_combineds_dict, iteration)`` — données réduites, séries
        temporelles accumulées par station, numéro de la dernière itération.
    :rtype: tuple[gpd.GeoDataFrame, dict, int]
    """
    wl_combineds_dict: dict = defaultdict(list)
    iteration: int = 0

    for iteration in range(1, max_iterations + 1):
        LOGGER.info(
            i18n.t(
                "tide.water_level_workflow.iteration",
                iteration=iteration,
                excluded_stations=excluded_stations,
            )
        )
        gdf_voronoi: gpd.GeoDataFrame[schema.TideZoneStationSchema] = (
            voronoi.get_voronoi_geodataframe(
                stations_handler=stations_handler,
                time_series=iwls_api_config.time_series.priority,
                excluded_stations=excluded_stations,
                water_level_stations=water_level_stations,
            )
        )
        result = _run_single_iteration(
            data=data,
            gdf_voronoi=gdf_voronoi,
            stations_handler=stations_handler,
            iwls_api_config=iwls_api_config,
            waterline=waterline,
            sounder=sounder,
            georeference_config=georeference_config,
            decimal_precision=decimal_precision,
            apply_water_level=apply_water_level,
            processing_context=processing_context,
            export_tide_path=export_tide_path,
            iteration=iteration,
        )
        if result is None:
            break

        data = result.data
        for key, value in result.wl_combineds.items():
            wl_combineds_dict[key].append(value)

        if not data[schema_ids.DEPTH_PROCESSED_METER].isna().any():
            break

        _extend_excluded_stations(data, result.wl_exceptions, excluded_stations)

    return data, wl_combineds_dict, iteration
