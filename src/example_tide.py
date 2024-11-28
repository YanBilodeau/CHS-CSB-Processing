from pathlib import Path

import geopandas as gpd
import pandas as pd
from loguru import logger

import iwls_api_request as iwls
from export.export_utils import (
    export_geodataframe_to_geojson,
    export_dataframe_to_csv,
)
from tide.plot import plot_time_series_dataframe
from tide.schema import TimeSerieDataSchema, TideZoneSchema
from tide.stations import (
    StationsHandlerABC,
    get_stations_factory,
    IWLSapiProtocol,
    TimeSeriesProtocol,
    EndpointTypeProtocol,
)
from tide.time_serie import (
    get_water_level_data,
)
from tide.voronoi import (
    get_voronoi_geodataframe,
    get_time_series_by_station_id,
    get_name_by_station_id,
    get_code_by_station_id,
)
from config.iwls_api_config import (
    get_api_config,
    IWLSAPIConfig,
    CONFIG_FILE,
)

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station")

EXPORT: Path = Path(__file__).parent.parent / "TideFileExport"


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


def initialize_station_info() -> tuple:
    """
    Initialize the information of the stations for the example.

    :return: (tuple) Information of the stations.
    """
    station_rimouski: str = "5cebf1e03d0f4a073c4bbd92"
    from_time_rimouski: str = "2024-10-01T12:00:00Z"
    to_time_rimouski: str = "2024-10-29T13:00:00Z"

    station_winter = "5cebf1de3d0f4a073c4bba71"
    from_time_winter = "2024-08-01T8:00:00Z"
    to_time_winter = "2024-10-28T10:00:00Z"

    station_montreal = "5cebf1e03d0f4a073c4bbdd7"
    from_time_montreal = "2024-10-07T8:00:00Z"
    to_time_montreal = "2024-10-28T10:00:00Z"

    station_quebec = "5cebf1e23d0f4a073c4bc0f6"
    from_time_quebec = "2024-07-07T8:00:00Z"
    to_time_quebec = "2024-10-28T10:00:00Z"

    memphremagog = "5dd3064de0fdc4b9b4be664c"
    from_time_memphremagog: str = "2024-10-01T00:00:00Z"
    to_time_memphremagog: str = "2024-10-15T00:00:00Z"

    rsp = "5dd30650e0fdc4b9b4be6bee"
    from_time_rsp: str = "2024-09-29T00:00:00Z"
    to_time_rsp: str = "2024-11-15T00:00:00Z"

    info_stations = (
        (station_rimouski, from_time_rimouski, to_time_rimouski),
        # (station_winter, from_time_winter, to_time_winter),
        # (station_montreal, from_time_montreal, to_time_montreal),
        # (station_quebec, from_time_quebec, to_time_quebec),
        # (memphremagog, from_time_memphremagog, to_time_memphremagog),
        # (rsp, from_time_rsp, to_time_rsp),
    )

    return info_stations


def initialize_all_station_info(
    gdf_voronoi: gpd.GeoDataFrame, stations: slice = slice(0, 10)
) -> list[tuple]:
    gdf_voronoi.sort_values(by="id", inplace=True)
    stations = gdf_voronoi.iloc[stations]["id"].to_list()

    from_time: str = "2024-10-01T00:00:00Z"
    to_time: str = "2024-10-15T00:00:00Z"

    info_stations = [(station_id, from_time, to_time) for station_id in stations]

    return info_stations


def main():
    if not EXPORT.exists():
        EXPORT.mkdir()

    # Read the configuration file 'iwls_API_config.toml'
    iwls_config: IWLSAPIConfig = get_api_config(config_file=CONFIG_FILE)

    # Get the environment of the API IWLS from the configuration file and the active profile
    api_environment: iwls.APIEnvironment = get_iwls_environment(config=iwls_config)
    # Get the API IWLS from the environment
    api: IWLSapiProtocol = get_api(environment=api_environment)

    # Get the handler of the stations
    stations_handler: StationsHandlerABC = get_stations_handler(
        api=api, endpoint_type=api_environment.endpoint.TYPE
    )

    # Get the Voronoi diagram of the stations. The stations are selected based on the priority of the time series.
    # The time series priority is defined in the configuration file.
    gdf_voronoi: gpd.GeoDataFrame[TideZoneSchema] = get_voronoi_geodataframe(
        stations_handler=stations_handler,
        time_series=iwls_config.time_series.priority,
        # excluded_stations=("5cebf1df3d0f4a073c4bbced", "5cebf1e23d0f4a073c4bc021"),
    )

    # Export the Voronoi diagram to a GeoJSON file
    export_geodataframe_to_geojson(
        geodataframe=gdf_voronoi,
        output_path=EXPORT / "voronoi_merged.geojson",
    )

    # Initialize the information of the stations for the example
    # info_stations = initialize_station_info()
    # Initialize the information of the stations for the example
    info_stations = initialize_all_station_info(
        gdf_voronoi=gdf_voronoi, stations=slice(0, 10)  #  1000, 1150)
    )

    wl_combineds = []
    titles = []
    empty = []
    exceptions = []

    # Get the water level data for each station
    for station, from_time, to_time in info_stations:
        # Get the time series priority for the station based on the Voronoi diagram
        time_series_priority: list[iwls.TimeSeries] = [
            iwls.TimeSeries.from_str(ts)
            for ts in get_time_series_by_station_id(
                gdf_voronoi=gdf_voronoi, station_id=station
            )
        ]

        LOGGER.info(
            get_water_level_data_retrieval_message(
                station, from_time, to_time, time_series_priority
            )
        )

        # Get the water level data for the station
        try:
            wl_combined: pd.DataFrame[TimeSerieDataSchema] = get_water_level_data(
                stations_handler=stations_handler,
                station_id=station,
                from_time=from_time,
                to_time=to_time,
                # Retrieve the data based on the priority of the time series.
                time_series_priority=time_series_priority,
                # Maximum time gap allowed for the data. The maximum time gap is defined in the configuration file.
                # If the gap is greater than this value, data from the next time series will be retrieved to fill
                # the gaps. For example, if the time series priority is [wlo, wlp] and the maximum time gap is 1 hour, the
                # data for the time series wlo will be retrieved first. If the gap between two consecutive
                # data points is greater than 1 hour, the data for the time series wlp will be retrieved to fill the gap.
                max_time_gap=iwls_config.time_series.max_time_gap,
                # Threshold for the interpolation versus filling of the gaps in the data.
                threshold_interpolation_filling=iwls_config.time_series.threshold_interpolation_filling,
                # Quality control flag filter for the wlo time series.
                wlo_qc_flag_filter=iwls_config.time_series.wlo_qc_flag_filter,
                # Buffer time to add before and after the requested time range for the interpolation.
                buffer_time=iwls_config.time_series.buffer_time,
            )
        except Exception as e:
            LOGGER.exception(f"Erreur pour la station {station} : {e}")
            exceptions.append((station, e))
            wl_combined = pd.DataFrame()

        if wl_combined.empty:
            empty.append(station)
            continue
        #     raise WaterLevelDataError(
        #         station_id=station,
        #         from_time=from_time,
        #         to_time=to_time
        #     )

        LOGGER.info(wl_combined)

        station_title = (
            f"{get_name_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station)} "
            f"({get_code_by_station_id(gdf_voronoi=gdf_voronoi, station_id=station)})"
        )

        # Export the water level data to a CSV file
        export_dataframe_to_csv(
            dataframe=wl_combined,
            output_path=EXPORT / f"{station_title} ({from_time} - {to_time}).csv",
        )

        wl_combineds.append(wl_combined)
        titles.append(station_title)

    # Plot the water level data for each station
    if wl_combineds:
        plot_time_series_dataframe(
            dataframes=wl_combineds,
            titles=titles,
            show_plot=True,  # Show the plot in a web browser
            output_path=EXPORT / "WaterLevel.html",  # Export the plot to an HTML file
        )

    LOGGER.debug(f"Stations vides : {empty}.")

    LOGGER.debug(f"Exceptions : {exceptions}.")

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
