from loguru import logger

from iwls_api_request import IWLSapiPublic, RetryAdapterConfig
from iwls_api_request import (
    TimeSeries,
    get_iwls_api,
    Response,
    HandlerType,
    EndpointPublic,
    # RetryAdapterConfig,
    SessionType
)

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station")


def main():
    # Initialize the API
    api: IWLSapiPublic = get_iwls_api(
        # EndpointPublic() is the only endpoint available outside the DFO network
        endpoint=EndpointPublic(),
        # Choice of handler type (HandlerType.RATE_LIMITER or HandlerType,REQUESTS).
        # HandlerType.RATE_LIMITER is recommended to limit the number of API calls.
        handler_type=HandlerType.RATE_LIMITER,
        calls=10,  # Number of calls allow per period
        period=1,  # Period in seconds
        # Retry adapter configuration. Allow to retry the call if the http status code is in the list of status code.
        # If True, a RetryAdapterConfig object is created with the following parameters:
            # max_retry: Optional[int] = 5
            # backoff_factor: Optional[int] = 2
            # status_code: Optional[Collection[int]] = field(default=(429, 500, 502, 503, 504))
        # A custom RetryAdapterConfig object can be passed as parameters
        retry_adapter_config=True, # Can be a boolean or a custom RetryAdapterConfig object
        # Session type configuration. Allow to choose the type of session to use.
        # Choice of session type (SessionType.REQUESTS or SessionType.CACHE).
        # If a SessionType.CACHE is chosen, a CachedSessionConfig is created with the following parameters:
            # db: Optional[Path] = field(default=Path(__file__).resolve().parent / ".cache/IWLS")
            # backend: Optional[str] = field(default="sqlite")
            # allowable_methods: Optional[tuple[str]] = field(default=("GET",))
            # expire_after: Optional[int] = field(default=600)
            # timeout: Optional[int] = field(default=5)
        # A custom CachedSessionConfig object can be passed as parameters
        session_type_config=SessionType.REQUESTS, # Can be a SessionType object or a CachedSessionConfig object
    )

    stations: Response = api.get_all_stations()  # Get all stations

    station: Response = api.get_all_stations(code="02985") # Get a specific station.
    # The code is the station code. See https://www.tides.gc.ca/en/stations for the station code.
    LOGGER.info(station)


    if not station.is_ok:
        LOGGER.warning("No station found.")
        return

    station_id: str = station.data[0].get("id")  # Get the station id
    LOGGER.info(f"Station id : {station_id}")

    station_metadata: Response = api.get_metadata_station(station=station_id)  # Get the station metadata
    LOGGER.info(f"Station metadata : {station_metadata.data}")

    from_time: str = "2024-04-27T00:00:00Z"  # Start date in UTC ISO 8601 format
    to_time: str = "2024-04-28T00:00:00Z"  # End date in UTC ISO 8601 format

    wlo: Response = api.get_time_serie_block_data(
        time_serie_code=TimeSeries.WLO, # TimeSeries.WLP for water level predictions, TimeSeries.WLO for water level observations, etc.
        station=station_id,
        from_time=from_time,
        to_time=to_time,
    )
    LOGGER.info(wlo)

    wlo_and_wlp: dict[TimeSeries, Response] = api.get_time_series_data(  # Get multiple time series data
        time_series=[TimeSeries.WLO, TimeSeries.WLP],  # List of TimeSeries
        station=station_id,
        from_time=from_time,
        to_time=to_time,
    )
    LOGGER.info(wlo_and_wlp)

    closest_station = api.get_closest_station(  # The Vincenty's formulae is used to calculate the distance between the location and the stations
        stations_list=stations.data,
        latitude=49.11,  # Latitude of the location in decimal degrees
        longitude=-67.66,  # Longitude of the location in decimal degrees
    )
    LOGGER.info(closest_station)

    # See https://api-iwls.dfo-mpo.gc.ca/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config#/ for more information on the API
    # All API endpoints are available in this library. See the documentation for more information.


if __name__ == '__main__':
    main()
