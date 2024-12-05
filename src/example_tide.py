from pathlib import Path

import geopandas as gpd
from loguru import logger
import pandas as pd

from config.iwls_api_config import (
    get_api_config,
    IWLSAPIConfig,
    CONFIG_FILE,
)
import iwls_api_request as iwls
from export.export_utils import (
    export_geodataframe_to_geojson,
    export_dataframe_to_csv,
)
from schema import TideZoneStationSchema
import schema.model_ids as schema_ids
from tide.plot import plot_time_series_dataframe
from tide.stations import (
    StationsHandlerABC,
    get_stations_factory,
    IWLSapiProtocol,
    TimeSeriesProtocol,
    EndpointTypeProtocol,
)
from tide import time_serie
import tide.voronoi as voronoi


LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station")

ROOT: Path = Path(__file__).parent
EXPORT_TIDE: Path = ROOT.parent / "TideFileExport"


def get_iwls_environment(config: IWLSAPIConfig) -> iwls.APIEnvironment:
    """
    Réccupère l'environnement de l'API IWLS à partir du fichier de configuration.

    :param config: (IWLSAPIConfig) Configuration de l'API IWLS.
    :return: (APIEnvironment) Environnement de l'API IWLS.
    """
    activated_profile: iwls.EnvironmentType = config.profile.active
    activated_environment: iwls.APIEnvironment = config.__dict__.get(activated_profile)

    LOGGER.debug(
        f"Chargement du profil '{config.profile.active}' pour l'API IWLS. [{activated_environment}]."
    )

    return activated_environment


def get_api(environment: iwls.APIEnvironment) -> IWLSapiProtocol:
    """
    Récupère l'API IWLS à partir de l'environnement spécifié.

    :param environment: (APIEnvironment) Environnement de l'API IWLS.
    :return: (IWLSapiProtocol) API IWLS.
    """
    return iwls.get_iwls_api(  # type: ignore
        endpoint=environment.endpoint,
        handler_type=iwls.HandlerType.RATE_LIMITER,
        calls=environment.calls,
        period=environment.period,
    )


def get_stations_handler(
    endpoint_type: EndpointTypeProtocol, api: IWLSapiProtocol
) -> StationsHandlerABC:
    """
    Récupère le gestionnaire des stations.

    :param endpoint_type: (EndpointType) Type de l'endpoint.
    :param api: (EndpointTypeProtocol) API IWLS.
    :return: (StationsHandlerABC) Gestionnaire des stations.
    """
    return get_stations_factory(enpoint_type=endpoint_type)(api=api)


def get_water_level_data_retrieval_message(
    station_id: str,
    from_time: str,
    to_time: str,
    time_serie_priority: list[TimeSeriesProtocol],
) -> str:
    """
    Récupère le message de log pour la récupération des données de niveau d'eau.

    :param station_id: (str) L'identifiant de la station.
    :param from_time: (str) La date de début.
    :param to_time: (str) La date de fin.
    :param time_serie_priority: (list[TimeSeriesProtocol]) Les séries temporelles prioritaires.
    :return: (str) Le message de log.
    """
    series_label = (
        "les séries temporelles"
        if len(time_serie_priority) > 1
        else "la série temporelle"
    )
    return f"Récupération des données de niveau d'eau pour la station '{station_id}' de {from_time} à {to_time} avec {series_label} : {time_serie_priority}."


def create_random_points_geodataframe(numbers_points: int) -> gpd.GeoDataFrame:
    from shapely.geometry import Point
    import numpy as np

    LOGGER.debug(f"Génération de {numbers_points} points aléatoires.")

    latitudes = np.random.uniform(46.5, 50.5, numbers_points)
    longitudes = np.random.uniform(-75.5, -57.5, numbers_points)

    points = [Point(lon, lat) for lon, lat in zip(longitudes, latitudes)]

    return gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")


def get_time_series_for_station(
    station_id: str, tide_zone: gpd.GeoDataFrame
) -> list[iwls.TimeSeries]:
    return [
        iwls.TimeSeries.from_str(ts)
        for ts in voronoi.get_time_series_by_station_id(
            gdf_voronoi=tide_zone, station_id=station_id
        )
    ]


def initialize_station_info(tide_zone: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Initialize the information of the stations for the example.

    :param tide_zone: (gpd.GeoDataFrame) The tide zone.
    :return: (pd.DataFrame) The information of the stations.
    """

    def create_station_info(station_id: str, from_time: str, to_time: str) -> tuple:
        return (
            station_id,
            from_time,
            to_time,
            get_time_series_for_station(station_id, tide_zone),
        )

    station_rimouski = create_station_info(
        "5cebf1e03d0f4a073c4bbd92", "2024-10-01T12:00:00Z", "2024-10-29T13:00:00Z"
    )
    station_winter = create_station_info(
        "5cebf1de3d0f4a073c4bba71", "2024-08-01T8:00:00Z", "2024-10-28T10:00:00Z"
    )
    station_montreal = create_station_info(
        "5cebf1e03d0f4a073c4bbdd7", "2024-10-07T8:00:00Z", "2024-10-28T10:00:00Z"
    )
    station_quebec = create_station_info(
        "5cebf1e23d0f4a073c4bc0f6", "2024-07-07T8:00:00Z", "2024-10-28T10:00:00Z"
    )
    memphremagog = create_station_info(
        "5dd3064de0fdc4b9b4be664c", "2024-10-01T00:00:00Z", "2024-10-15T00:00:00Z"
    )
    rsp = create_station_info(
        "5dd30650e0fdc4b9b4be6bee", "2024-09-29T00:00:00Z", "2024-11-15T00:00:00Z"
    )

    # Convertissez la liste de tuples en DataFrame
    tide_zone_info = pd.DataFrame(
        [
            station_rimouski,
            station_winter,
            station_montreal,
            station_quebec,
            memphremagog,
            rsp,
        ],
        columns=[
            schema_ids.TIDE_ZONE_ID,
            "min_time",
            "max_time",
            schema_ids.TIME_SERIES,
        ],
    )

    return tide_zone_info


def initialize_all_station_info(
    tide_zone: gpd.GeoDataFrame, stations_index: slice = slice(0, 10)
) -> pd.DataFrame:
    tide_zone.sort_values(by="id", inplace=True)
    stations = tide_zone.iloc[stations_index]["id"].to_list()

    from_time: str = "2024-10-01T00:00:00Z"
    to_time: str = "2024-10-15T00:00:00Z"

    # Créez une liste de tuples contenant les informations des stations
    tide_zone_info_list = [
        (
            station_id,
            from_time,
            to_time,
            get_time_series_for_station(tide_zone=tide_zone, station_id=station_id),
        )
        for station_id in stations
    ]

    # Convertissez la liste de tuples en DataFrame
    tide_zone_info = pd.DataFrame(
        tide_zone_info_list,
        columns=[
            schema_ids.TIDE_ZONE_ID,
            "min_time",
            "max_time",
            schema_ids.TIME_SERIES,
        ],
    )

    return tide_zone_info


def main():
    if not EXPORT_TIDE.exists():
        EXPORT_TIDE.mkdir()

    # Read the configuration file 'iwls_API_config.toml'
    iwls_api_config: IWLSAPIConfig = get_api_config(config_file=CONFIG_FILE)

    # Get the environment of the API IWLS from the configuration file and the active profile
    api_environment: iwls.APIEnvironment = get_iwls_environment(config=iwls_api_config)
    # Get the API IWLS from the environment
    api: IWLSapiProtocol = get_api(environment=api_environment)

    # Get the handler of the stations
    stations_handler: StationsHandlerABC = get_stations_handler(
        api=api, endpoint_type=api_environment.endpoint.TYPE
    )

    # Get the Voronoi diagram of the stations. The stations are selected based on the priority of the time series.
    # The time series priority is defined in the configuration file.
    gdf_voronoi: gpd.GeoDataFrame[TideZoneStationSchema] = (
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

    # Initialize the information of the stations for the example
    # tide_zonde_info = initialize_station_info(tide_zone=gdf_voronoi)
    # Initialize the information of the stations for the example
    tide_zonde_info = initialize_all_station_info(
        tide_zone=gdf_voronoi, stations_index=slice(600, 800)
    )

    # Get the water level data for each station
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

    station_titles = []
    for station_id, wl_dataframe in wl_combineds.items():
        station_title = (
            f"{voronoi.get_name_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)} "
            f"({voronoi.get_code_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station_id)})"
        )
        station_titles.append(station_title)

        output_path: Path = (
            EXPORT_TIDE / f"{station_title} "
            f"({wl_dataframe.attrs.get(schema_ids.START_TIME).strftime('%Y-%m-%d %H-%M-%S')} - "
            f"{wl_dataframe.attrs.get(schema_ids.END_TIME).strftime('%Y-%m-%d %H-%M-%S')}).csv"
        )

        # Export the water level data to a CSV file
        LOGGER.info(f"Enregistrement des données de niveaux d'eau : {output_path}.")
        export_dataframe_to_csv(
            dataframe=wl_dataframe,
            output_path=output_path,
        )

    # Plot the water level data for each station
    if wl_combineds:
        output_path: Path = EXPORT_TIDE / "WaterLevel.html"
        LOGGER.info(
            f"Enregistrement des graphiques des données de niveaux d'eau [{station_titles}]: {output_path}."
        )
        plot_time_series_dataframe(
            dataframes=list(wl_combineds.values()),
            titles=station_titles,
            show_plot=True,  # Show the plot in a web browser
            output_path=output_path,  # Export the plot to an HTML file
        )

    LOGGER.debug(wl_combineds)
    LOGGER.debug(f"Exceptions : {wl_exceptions}.")

    # Create a GeoDataFrame with random points
    # data: gpd.GeoDataFrame = create_random_points_geodataframe(1_000_000)
    # export_geodataframe_to_geojson(data, EXPORT / "random.geojson")

    # Get the polygon of the Voronoi diagram that intersects with the random points
    # interseted_data: gpd.GeoDataFrame[VoronoiSchema] = get_polygon_by_geometry(gdf_voronoi=gdf_voronoi, geometry=data)
    # export_geodataframe_to_geojson(interseted_data, EXPORT / "interseted.geojson")


if __name__ == "__main__":
    main()

    # Liste des stations avec les séries temporelles dans les métadonnées de la station mais aucune donnée dans le holding

    # QC Private ['5cebf1de3d0f4a073c4bba5b', '5cebf1de3d0f4a073c4bbaf3', '5cebf1df3d0f4a073c4bbb5b',
    # '5cebf1e43d0f4a073c4bc49e', '62a328b7bacf3e2d38aeb2f9']

    # ATL [01569 - 5dd3064ce0fdc4b9b4be65e3, 00175 - 5cebf1df3d0f4a073c4bbc3c, 16500 - 5dd3064ce0fdc4b9b4be658f,
    # 02002 - 5dd3064ce0fdc4b9b4be6604, 00075 - 5dd3064de0fdc4b9b4be6657, 00089 - 5dd3064de0fdc4b9b4be665a,
    # 00096 - 5dd3064de0fdc4b9b4be665c, 00124 - 5dd3064de0fdc4b9b4be665f, 00174 - 5dd3064de0fdc4b9b4be6663,
    # 00536 - 5dd3064de0fdc4b9b4be667d, 00652 - 5dd3064de0fdc4b9b4be6686, 01384 - 5dd3064de0fdc4b9b4be66c2,
    # 01472 - 5dd3064de0fdc4b9b4be66c7, 00099 - 5dd3064ee0fdc4b9b4be671b, 00289 - 5dd3064ee0fdc4b9b4be672a,
    # 00494 - 5dd3064ee0fdc4b9b4be672d, 03932 - 5dd3064ee0fdc4b9b4be6786, 05260 - 5dd3064ee0fdc4b9b4be67b7,
    # 10100 - 5dd3064ee0fdc4b9b4be67db, 10240 - 5dd3064ee0fdc4b9b4be67dd, 11110 - 5dd3064ee0fdc4b9b4be67e4,
    # 11150 - 5dd3064ee0fdc4b9b4be67e6, 11187 - 5dd3064ee0fdc4b9b4be67eb, 11220 - 5dd3064ee0fdc4b9b4be67ee] wlo rien dans le holding
    # [40555 - 5cebf1e23d0f4a073c4bc053, 50550 - 5cebf1e23d0f4a073c4bc055, 08868 - 5cebf1e23d0f4a073c4bc0af]

    # PAC [07843 - 5cebf1de3d0f4a073c4bb956, 09511 - 5cebf1de3d0f4a073c4bba1a] wlp avant 2023
    # [07107- 5dd3064de0fdc4b9b4be66e1] wlo rien dans le holding
    # [07810 - 5dd3064ee0fdc4b9b4be6709]

    # à valider
    # CNA ['5cebf1dd3d0f4a073c4bb8c9', '5cebf1dd3d0f4a073c4bb8e3', '5cebf1de3d0f4a073c4bb9d5',
    # '5cebf1de3d0f4a073c4bb9d9', '5cebf1de3d0f4a073c4bba7f', '5cebf1df3d0f4a073c4bbbf7',
    # '5cebf1df3d0f4a073c4bbcfb', '5cebf1df3d0f4a073c4bbcfd', '5cebf1e13d0f4a073c4bbf75',
    # '5cebf1e13d0f4a073c4bbf77', '5cebf1e13d0f4a073c4bbf7f', '5cebf1e13d0f4a073c4bbfa1',
    # '5cebf1e23d0f4a073c4bbfa5', '5cebf1e23d0f4a073c4bbfc9', '5cebf1e23d0f4a073c4bbfcb',
    # '5cebf1e23d0f4a073c4bc019', '5cebf1e23d0f4a073c4bc01b', '5cebf1e23d0f4a073c4bc01d',
    # '5cebf1e23d0f4a073c4bc01f', '5cebf1e23d0f4a073c4bc021', '5cebf1e43d0f4a073c4bc3b8',
    # '5cebf1e43d0f4a073c4bc3ba', '5cebf1e43d0f4a073c4bc3d1', '5cebf1e43d0f4a073c4bc3f9',
    # '5dd3064ee0fdc4b9b4be67f4', '5dd3064ee0fdc4b9b4be67f6', '5dd3064ee0fdc4b9b4be67f8',
    # '5dd3064ee0fdc4b9b4be6808', '5dd3064ee0fdc4b9b4be6812', '5dd3064ee0fdc4b9b4be6818',
    # '5dd3064fe0fdc4b9b4be69f2', '5dd3064fe0fdc4b9b4be6afd', '5dd3064fe0fdc4b9b4be6b18',
    # '5dd3064fe0fdc4b9b4be6b1b', '5dd30650e0fdc4b9b4be6d36', '5dd30650e0fdc4b9b4be6d89',
    # '5dd30650e0fdc4b9b4be6db5', '5dd30650e0fdc4b9b4be6db8', 5d1babeb44fdf300010bdf4d,
    # 5dd3064ce0fdc4b9b4be65a7, 5dd3064ce0fdc4b9b4be65ad, 5dd3064ce0fdc4b9b4be65b0, 5dd3064ce0fdc4b9b4be65d4,
    # 5dd3064ce0fdc4b9b4be65e1, 5dd3064ee0fdc4b9b4be6757, 5dd3064ee0fdc4b9b4be675f, 5dd3064ee0fdc4b9b4be6763,
    # 5dd3064ee0fdc4b9b4be676b, 5dd3064ee0fdc4b9b4be676d, 5dd3064ee0fdc4b9b4be6778, 5dd3064ee0fdc4b9b4be677b,
    # 5dd3064ee0fdc4b9b4be67a7, 5dd3064ee0fdc4b9b4be67aa, 5dd3064ee0fdc4b9b4be67ad, 5dd3064ee0fdc4b9b4be67b0,
    # 5dd3064ee0fdc4b9b4be67c2]
