from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Collection, Callable

from cachetools.func import ttl_cache
from loguru import logger

from . import ids_iwls as ids
from .endpoint import EndpointPublic
from .iwls_api_abc import IWLSapiABC
from .models_api import Regions, TimeSeries, TypeTideTable, TimeZone, TimeResolution
from ..handler.http_query_handler import Response, HTTPQueryHandler

LOGGER = logger.bind(name="IWLS.API")


class IWLSapiPublic(IWLSapiABC):
    def __init__(
        self,
        query_handler: HTTPQueryHandler,
        endpoint: Optional[EndpointPublic] = EndpointPublic,
    ) -> None:
        """
        Constructeur de la classe IWLSapiPublic.

        :param query_handler: (HTTPQueryHandler) Un objet HTTPQueryHandler.
        :param endpoint: (EndpointPublic) Un objet EndpointPublic.
        """
        super().__init__(query_handler=query_handler, endpoint=endpoint)

    def get_time_serie_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeries] = TimeSeries.WLO,
        time_resolution: Optional[TimeResolution] = TimeResolution.ONE_MINUTE,
    ) -> Response:
        """
        Méthode permttant de récupérer des données à partir de l'API de iWLS.

            /api/v1/stations/{stationId}/data

        :param station: (str) Le stationId de la station.
        :param time_serie_code: (TimeSeries) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
        :param from_time: (str) La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z). La durée maximale est de
                            7 jours pour la majorité des TimeSeries.
        :param time_resolution: (TimeResolution) La résolution temporelle désirée.
        :return: (Response) Un objet Response contenant les données reçues de l'API de iWLS.
        """
        query_params = self._validate_query_parameters(
            **{
                ids.STATION: station,
                ids.TIME_SERIES_CODE: time_serie_code,
                ids.FROM: from_time,
                ids.TO: to_time,
                ids.RESOLUTION: time_resolution,
            }
        )

        url = self._construct_url(
            self.endpoint.STATION_DATA,
            stationId=query_params[ids.STATION],
        )

        return self._query_handler.query(url, query_params)

    def get_wlo_latest_data(self) -> Response:
        """
        Méthode permettant de récupérer les 20 dernières minutes de données de la série temporelle WLO pour toutes
        les stations.

            /api/v1/stations/data/latest

        :return: (Response) Un objet Response contenant les 20 dernières minutes de données de la série temporelle WLO.
        """
        url = self._construct_url(self.endpoint.STATION_DATA_LATEST)

        return self._query_handler.query(url)

    def get_info_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer les informations concernant une station.

            /api/v1/stations/{stationId}

        :param station: (str) L'identifiant de la station.
        :return: (Response) Un objet Response contenant les informations de la station.
        """
        url = self._construct_url(
            self.endpoint.STATION, stationId=self._validate_station_id(station)
        )

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_metadata_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées concernant une station.

            /api/v1/stations/{stationId}/metadata

        :param station: (str) Le stationId de la station.
        :return: (Response) Un objet Response contenant les métadonnées de la station.
        """
        url = self._construct_url(
            self.endpoint.STATION_METADATA,
            stationId=self._validate_station_id(station),
        )

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_all_stations(
        self,
        code: Optional[str] = None,
        chs_region_code: Optional[Regions] = None,
        time_serie_code: Optional[TimeSeries] = None,
    ) -> Response:
        """
        Méthode permettant de récupérer une liste de stations ainsi que les informations les concernant.

            /api/v1/stations

        :param code: (str) Le code d'une station. Écrase les autres paramètres.
        :param chs_region_code: (Regions) Le code d'une région (PAC, CNA, ATL, QUE).
        :param time_serie_code: (TimeSeries) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
        :return: (Response) Un objet Response contenant les stations ainsi que les informations les concernant
        """
        query_params = self._validate_query_parameters(
            **{
                ids.CODE: code,
                ids.CHS_REGION_CODE: chs_region_code,
                ids.TIME_SERIES_CODE: time_serie_code,
            }
        )
        url = self._construct_url(self.endpoint.STATIONS)

        return self._query_handler.query(url, query_params)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_height_types(self) -> Response:
        """
        Méthode permettant de récupérer les types de hauteur.

            /api/v1/height-types

        :return: (Response) Un objet Response contenant les différents types de hauteur.
        """
        url = self._construct_url(self.endpoint.HEIGHT_TYPES)

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_height(self, height: str) -> Response:
        """
        Méthode permettant de récupérer un type de hauteur.

            /api/v1/height-types/{heightTypeId}

        :param height: (str) L'identifiant de la hauteur.
        :return: (Response) Un objet Response contenant les informations concernant ce type de hauteur.
        """
        url = self._construct_url(self.endpoint.HEIGHT_TYPE, heightTypeId=height)

        return self._query_handler.query(url)

    def get_station_montly_mean(
        self,
        station: str,
        year: str,
        month: str,
        time_zone: Optional[TimeZone] = TimeZone.UTC,
    ) -> Response:
        """
        Méthode permettant d'obtenir la moyenne mensuelle pour une station.

            /api/v1/stations/{stationId}/stats/calculate-monthly-mean

        :param station: (str) Le stationId de la station.
        :param year: (str) L'année désirée.
        :param month: (str) Le mois désiré.
        :param time_zone: (TimeZone) Le fuseau horaire désiré.
        :return: (Response) Un objet Response contenant la moyenne mensuelle de la station.
        """
        query_params = self._validate_query_parameters(
            **{
                ids.STATION: station,
                ids.YEAR: year,
                ids.MONTH: month,
                ids.TIME_ZONE: time_zone,
            }
        )
        url = self._construct_url(
            self.endpoint.STATION_STATS_MONTHLY, stationId=query_params[ids.STATION]
        )

        return self._query_handler.query(url, query_params)

    def get_station_daily_mean(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_zone: Optional[TimeZone] = TimeZone.UTC,
    ) -> Response:
        """
        Méthode permettant d'obtenir les moyennes journalières pour une station.

            /api/v1/stations/{stationId}/stats/calculate-daily-means

        :param station: (str) Le stationId de la station.
        :param from_time: (str) La date de début en format (ex: 2019-11-13).
        :param to_time: (str) La date de fin en format (ex: 2019-11-13).
        :param time_zone: (TimeZone) Le fuseau horaire désiré.
        :return: (Response) Un objet Response contenant les moyenne journalières de la station.
        """
        query_params = self._validate_query_parameters(
            **{ids.STATION: station, ids.TIME_ZONE: time_zone}
        )
        query_params[ids.FROM] = from_time
        query_params[ids.TO] = to_time

        url = self._construct_url(
            self.endpoint.STATION_STATS_DAILY, stationId=query_params[ids.STATION]
        )

        return self._query_handler.query(url, query_params)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_phenomena(self) -> Response:
        """
        Méthode permettant de récupérer les phénomènes.

            /api/v1/phenomena

        :return: (Response) Un objet Response contenant les différents phénomènes.
        """
        url = self._construct_url(self.endpoint.PHENOMENA)

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_phenomenon(self, phenomenon: str) -> Response:
        """
        Méthode permettant de récupérer les informations d'un phénomène.

            /api/v1/phenomena/{phenomenonId}

        :return: (Response) Un objet Response contenant les informations concernant un phénomène.
        """
        url = self._construct_url(
            self.endpoint.PHENOMENON,
            phenomenonId=phenomenon,
        )

        return self._query_handler.query(url)

    def get_tide_tables(
        self,
        type_table: Optional[TypeTideTable] = None,
        parent_tide_table: Optional[str] = None,
    ) -> Response:
        """
        Méthode permettant de recupérer la liste des tables de marées.

            /api/v1/tide-tables

        :param type_table: (TypeTideTable) Un type de table. {VOLUME, AREA, SUB_AREA}
        :param parent_tide_table: (str) L'identifiant d'une table.
        :return: (Response) Un objet Response contenant l'ensemble des tables de marées correspondant
                            aux critères de la recherche.
        """
        query_params = self._validate_query_parameters(
            **{ids.TYPE: type_table, ids.PARENT_TIDE_TABLE: parent_tide_table}
        )
        url = self._construct_url(self.endpoint.TIDE_TABLES)

        return self._query_handler.query(url, query_params)

    def get_tide_table(self, tide_table: str) -> Response:
        """
        Méthode permettant de recupérer une table de marées.

            /api/v1/tide-tables/{tideTableId}

        :param tide_table: (str) L'identifiant d'une table de marées.
        :return: (Response) Un objet Response contenant les informations d'une table de marées.
        """
        url = self._construct_url(
            self.endpoint.TIDE_TABLE,
            tideTableId=tide_table,
        )

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_time_series_definitions(
        self, time_serie: Optional[TimeSeries] = None
    ) -> Response:
        """
        Méthode permettant de récupérer les définitions des séries temporelles.

            /api/v1/time-series-definitions

        :param time_serie: (TimeSeries) Le code de la série temporelle désirée.
        :return: (Response) Un objet Response contenant les définitions des séries temporelles.
        """
        query_params = self._validate_query_parameters(**{ids.CODE: time_serie})

        url = self._construct_url(self.endpoint.TIME_SERIES_DEFINITION)

        return self._query_handler.query(url, query_params)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_time_serie_definition(self, time_serie_definition_id: str) -> Response:
        """
        Méthode permettant de récupérer la définition d'une série temporelle.

            /api/v1/time-series-definitions/{timeSeriesDefinitionId}

        :param time_serie_definition_id: (str) L'identifiant de la série temporelle.
        :return: (Response) Un objet Response contenant la définition de la série temporelle.
        """
        url = self._construct_url(
            self.endpoint.TIME_SERIES_DEFINITION,
            timeSeriesDefinitionId=time_serie_definition_id,
        )

        return self._query_handler.query(url)

    def _get_benchmarks(self, station_id: Optional[str] = None) -> Response:
        """
        Méthode permettant de récupérer les repères d'une station.

            /api/v1/benchmarks

        :param station_id: (str) L'identifiant d'une station.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """
        query_params = self._validate_query_parameters(**{ids.STATION: station_id})
        url = self._construct_url(self.endpoint.BENCHMARKS)

        return self._query_handler.query(url, query_params)

    @staticmethod
    def _aggregate_benchmarks(futures: Collection) -> tuple[list[dict], list[str]]:
        """
        Méthode permettant d'agréger les données des repères des stations.

        :param futures: (Collection) Une collection de futures.
        :return: (tuple) Une liste contenant les données agrégées et une liste contenant les erreurs.
        """
        data_aggregated = []
        errors = []

        for future in as_completed(futures):
            station_id, data = future.result()

            if data.is_ok:
                data_aggregated.extend(data.data)

            else:
                error: str = (
                    f"{data.message} - {data.error} MISSING BENCHMARKS FOR STATION {station_id}"
                )
                errors.append(error)
                LOGGER.warning(f"Impossible de récupérer les données : {error}.")

        return data_aggregated, errors

    def _fetch_and_aggregate_benchmarks(
        self, function: Callable, station_ids: Collection[str]
    ) -> Response:
        """
        Méthode permettant de récupérer et d'agréger les données des repères des stations.

        :param function: (Callable) Une fonction permettant de récupérer les données des repères.
        :param station_ids: (Collection[str]) Une liste contenant les identifiants des stations.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """

        response = Response(status_code=200)

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(function, station_id) for station_id in station_ids
            ]
            data_aggregated, errors = self._aggregate_benchmarks(futures=futures)

        if data_aggregated:
            response.data = data_aggregated

        if errors:
            response.status_code = 400
            response.error = errors
            response.message = "MISSING DATA"

        return response

    def get_benchmarks(self, station_ids: Collection[str] = None, **kwargs) -> Response:
        """
        Méthode permettant de récupérer les repères des stations.

            /api/v1/benchmarks

        :param station_ids: (Collection[str]) Une liste contenant les identifiants des stations.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """

        def fetch_data(station_id: str) -> tuple[str, Response]:
            data: Response = self._get_benchmarks(station_id=station_id)

            return station_id, data

        if station_ids:
            return self._fetch_and_aggregate_benchmarks(
                function=fetch_data, station_ids=station_ids
            )

        return self._get_benchmarks()

    def get_benchmark(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les informations d'un repère.

                /api/v1/benchmarks/{benchmarkId}

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les informations du repère.
        """
        url = self._construct_url(
            self.endpoint.BENCHMARK,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)

    def get_benchmark_metadata(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

                /api/v1/benchmarks/{benchmarkId}/metadata

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées du repère.
        """
        url = self._construct_url(
            self.endpoint.BENCHMARK_METADATA,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)

    def get_elevations(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

                /api/v1/benchmarks/{benchmarkId}/elevations

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées sur le repère.
        """
        url = self._construct_url(
            self.endpoint.ELEVVATIONS,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)
