from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Collection, Sequence

from cachetools.func import ttl_cache
from loguru import logger

from . import ids_iwls as ids
from .endpoint import EndpointPrivateDev, EndpointPrivateProd
from .iwls_api_abc import IWLSapiABC
from .models_api import Regions, TimeSeries, TypeTideTable
from ..handler.http_query_handler import HTTPQueryHandler, Response, ResponseType

LOGGER = logger.bind(name="IWLS.API")


class IWLSapiPrivate(IWLSapiABC):
    def __init__(
        self,
        query_handler: HTTPQueryHandler,
        endpoint: Optional[
            EndpointPrivateDev | EndpointPrivateProd
        ] = EndpointPrivateProd,
    ):
        super().__init__(query_handler=query_handler, endpoint=endpoint)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_time_series_station(self, station: str) -> Response:
        """
        Méthode permttant de récupérer la liste des times series disponibles pour une station.

            /rest/stations/{stationId}/time-series/

        :param station: (str) Le stationId de la station.
        :return: (Response) Un objet Response concernant les times series d'une station.
        """
        url = self._construct_url(
            self.endpoint.STATION_TIME_SERIES,
            stationId=self._validate_station_id(station),
        )

        return self._query_handler.query(url)

    def get_time_series_stations(
        self, stations: Sequence[str] = None
    ) -> dict[str, Response]:
        """
        Méthode permettant de récupérer les séries temporelles concernant une liste de stations.

        :param stations: (Sequence[str]) Une liste contenant les stations.
        :return: (dict[str, Response]) Un objet Response contenant les séries temporelles des stations.
        """
        with ThreadPoolExecutor() as executor:
            results = {
                stations[index]: result
                for index, result in enumerate(
                    executor.map(self.get_time_series_station, stations)
                )
            }

        return results

    def get_time_serie_id_from_code(
        self, station: str, time_serie_code: Optional[TimeSeries] = TimeSeries.WLO
    ) -> str:
        """
        Méthode permttant de récupérer la liste des times sereies disponibles pour une station.

        :param station: (str) Le stationId de la station.
        :param time_serie_code: (TimeSeries) Le code de la série temporelle désirée.
        :return: (str) L'identifiant d'une time serie pour une station.

        """
        time_series = self.get_time_series_station(station)

        for ts in time_series.data:
            if ts.get(ids.CODE) == time_serie_code.value:
                return ts.get(ids.ID)

    def get_time_serie_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeries] = TimeSeries.WLO,
        **kwargs,
    ) -> Response:
        """
        Méthode permttant de récupérer des données à partir de l'API de iWLS.

            /rest/stations/{stationId}/time-series/{tsId}/data

        :param station: (str) Le stationId de la station.
        :param time_serie_code: (TimeSerie) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
                                    ...
        :param from_time: (str) La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :return: (Response) Un objet Response contenant les données de la série temporelle.
        """
        query_params = self._validate_query_parameters(
            **{ids.FROM: from_time, ids.TO: to_time}
        )

        ts_id = self.get_time_serie_id_from_code(station, time_serie_code)
        if ts_id is None:
            message = (
                f"Le code de série temporelle '{time_serie_code.value}' n'est pas disponible pour "
                f"la station '{station}'. Liste des choix disponibles : "
                f"{', '.join([ts.get(ids.CODE) for ts in self.get_time_series_station(station).data])}."
            )
            LOGGER.warning(message)
            return Response(
                data=[], message=message, status_code=400, error="INVALID_DATA"
            )

        url = self._construct_url(
            self.endpoint.STATION_DATA,
            stationId=self._validate_station_id(station),
            tsId=ts_id,
        )

        return self._query_handler.query(url, query_params)

    def get_info_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer les informations concernant une station.

            /rest/stations/{stationId}

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

            /rest/stations/{stationId}/metadata

        :param station: (str) Le stationId de la station.
        :return: (Response) Un objet Response contenant les métadonnées de la station.
        """
        url = self._construct_url(
            self.endpoint.STATION_METADATA,
            stationId=self._validate_station_id(station),
        )

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_chs_regions(self) -> Response:
        """
        Méthode permettant de récupérer les informations concernant les régions.

            /rest/chsRegions

        :return: (Response) Un objet Response des régions ainsi que les informations les concernant.
        """
        url = self._construct_url(self.endpoint.REGIONS)

        return self._query_handler.query(url)

    def _filter_stations_by_region(
        self, stations: list[dict], chs_region_code: Regions = None
    ) -> list[dict]:
        """
        Méthode permettant de filtrer les stations selon le code d'une région.

        :param stations: (list[dict]) Une liste de stations à filtrer.
        :param chs_region_code: (str) Le code d'une région (PAC, CNA, ATL, QUE).
        :return: (list[dict]) Une liste contenant les stations filtrées.
        """
        if chs_region_code is None:
            return stations

        regions_dict = {
            region.get(ids.ID): region.get(ids.CODE)
            for region in self.get_chs_regions().data
        }

        stations_list = [
            station
            for station in stations
            if regions_dict[station[ids.DFO_REGION]] == chs_region_code.value
        ]
        return stations_list

    def _filter_stations_by_ts(
        self, stations: list[dict], time_serie_code: TimeSeries = None
    ) -> list[dict]:
        """
        Méthode permettant de filtrer les stations selon le code d'une série temporelle.

        :param stations: (list[dict]) Une liste de stations à filtrer.
        :param time_serie_code: (TimeSeries) Le code d'une région (PAC, CNA, ATL, QUE).
        :return: (list[dict]) Une liste contenant les stations filtrées.
        """
        if time_serie_code is None:
            return stations

        station_id = [station[ids.ID] for station in stations]
        with ThreadPoolExecutor() as executor:
            results = executor.map(self.get_time_series_station, station_id)

        station_ts = {}
        for index, result in enumerate(results):
            station_ts[station_id[index]] = result.data

        filtered_stations_ts = []
        for index, (station_id, time_series) in enumerate(station_ts.items()):
            for ts in time_series:
                if ts.get(ids.CODE) == time_serie_code.value:
                    filtered_stations_ts.append(stations[index])

        return filtered_stations_ts

    @staticmethod
    def _filter_station_by_code(stations: Collection[dict], code: str) -> list[dict]:
        """
        Méthode permettant de filtrer les stations selon leur code.

        :param stations: (Collection[dict]) Une liste de stations à filtrer.
        :param code: (str) Le code d'une station.
        :return: (list[dict]) Une liste contenant les stations filtrées.
        """
        return [station for station in stations if station[ids.CODE] == code]

    @ttl_cache(ttl=1200, maxsize=256)
    def get_all_stations(
        self,
        code: Optional[str] = None,
        chs_region_code: Optional[Regions] = None,
        time_serie_code: Optional[TimeSeries] = None,
    ) -> Response:
        """
        Méthode permettant de récupérer une liste de stations ainsi que les informations les concernant.

            /rest/stations

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
        :return: (Response) Un objet Response contenant les stations ainsi que les informations les concernant.
        """
        self._validate_query_parameters(**{ids.CHS_REGION_CODE: chs_region_code})

        url = self._construct_url(self.endpoint.STATIONS)
        stations = self._query_handler.query(url)
        if not stations.is_ok:
            return stations

        if code:
            return Response(
                data=self._filter_station_by_code(stations=stations.data, code=code)
            )

        if chs_region_code is None and time_serie_code is None:
            return stations

        filtered_stations_region = self._filter_stations_by_region(
            stations=stations.data, chs_region_code=chs_region_code
        )
        filtered_stations_ts = self._filter_stations_by_ts(
            stations=filtered_stations_region, time_serie_code=time_serie_code
        )

        return Response(data=filtered_stations_ts)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_height_types(self) -> Response:
        """
        Méthode permettant de récupérer les types de hauteur.

            /rest/heights

        :return: (Response) Un objet Response contenant les différents types de hauteur.
        """
        url = self._construct_url(self.endpoint.HEIGHT_TYPES)

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_height(self, height: str) -> Response:
        """
        Méthode permettant de récupérer un type de hauteur.

            /rest/heights/{heightTypeId}

        :param height: (str) L'identifiant de la hauteur.
        :return: (Response) Un objet Response contenant les informations concernant ce type de hauteur.
        """
        url = self._construct_url(self.endpoint.HEIGHT_TYPE, heightTypeId=height)

        return self._query_handler.query(url)

    def get_station_montly_mean(
        self, station: str, year: str, month: str, **kwargs
    ) -> Response:
        """
        Méthode permettant d'obtenir la moyenne mensuelle pour une station.

        :param station: (str) Le stationId de la station.
        :param year: (str) L'année désirée.
        :param month: (str) Le mois désiré.
        :return: (Response) La moyenne mensuelle de la station.
        """
        raise NotImplementedError

    def get_station_daily_mean(
        self, station: str, from_time: str, to_time: str, **kwargs
    ) -> Response:
        """
        Méthode permettant d'obtenir les moyennes journalières pour une station.

        :param station: (str) Le stationId de la station.
        :param from_time: (str) La date de début en format (ex: 2019-11-13).
        :param to_time: (str) La date de fin en format (ex: 2019-11-13).
        :return: (Response) Un objet Response contenant les moyenne journalières de la station.
        """
        raise NotImplementedError

    @ttl_cache(ttl=1200, maxsize=256)
    def get_time_series_definitions(
        self, time_serie: Optional[TimeSeries] = None
    ) -> Response:
        """
        Méthode permettant de récupérer les définitions des séries temporelles.

            /rest/time-series-definitions/

        :param time_serie: (TimeSeries) Le code de la série temporelle désirée.
        :return: (Response) Un objet Response contenant les définitions des séries temporelles.
        """
        query_params = self._validate_query_parameters(**{ids.CODES: time_serie})

        url = self._construct_url(self.endpoint.TIME_SERIES_DEFINITION)

        return self._query_handler.query(url, query_params)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_time_serie_definition(self, time_serie_definition_id: str) -> Response:
        """
        Méthode permettant de récupérer les définitions d'une série temporelle.

            /rest/time-series-definitions/{id}

        :param time_serie_definition_id: (str) L'identifiant d'une série temporelle.
        :return: (Response) Un objet Response contenant les définitions d'une série temporelle.
        """
        url = self._construct_url(
            self.endpoint.TIME_SERIE_DEFINITION,
            id=time_serie_definition_id,
        )

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_phenomena(self) -> Response:
        """
        Méthode permettant de récupérer les phénomènes.

            /rest/phenomena

        :return: (Response) Un objet Response contenant les différents phénomènes.
        """
        url = self._construct_url(self.endpoint.PHENOMENA)

        return self._query_handler.query(url)

    @ttl_cache(ttl=1200, maxsize=256)
    def get_phenomenon(self, phenomenon: str) -> Response:
        """
        Méthode permettant de récupérer les informations d'un phénomène.

            /rest/phenomena/{phenomenonId}

        :return: (Response) Un objet Response contenant les informations concernant un phénomène.
        """
        url = self._construct_url(
            self.endpoint.PHENOMENON,
            phenomenonId=phenomenon,
        )

        return self._query_handler.query(url)

    @staticmethod
    def _filter_tables_by_type(
        tables_list: list[dict], type_table: Optional[TypeTideTable] = None
    ) -> list[dict]:
        """
        Méthode permettant de filtrer les tables marée selon leur type.

        :param tables_list: (list[dict]) Une liste de tables.
        :pram p_type_table: (Optional[TypeTideTable]) Un type de table.
        :return: (list[dict]) Un liste contenant les tables filtrées selon le type.
        """
        if type_table is None:
            return tables_list

        return [
            table for table in tables_list if table[ids.TIDE_TABLE_TYPE] == type_table
        ]

    @staticmethod
    def _filter_tables_by_parent(
        tables_list: list[dict], parent_tide_table: Optional[str] = None
    ) -> list[dict]:
        """
        Méthode permettant de filtrer les tables marée selon la table parent.

        :param tables_list: (list[dict]) Une liste de tables.
        :pram p_parent_tide_table: (Optional[str]) L'identifiant de la table parent.
        :return: (list[dict]) Un liste contenant les tables filtrées selon la table parent.
        """
        if parent_tide_table is None:
            return tables_list

        filtered_tables_parent = []
        for table in tables_list:
            if ids.PARENT_TIDE_TABLE in table:
                if table[ids.PARENT_TIDE_TABLE] == parent_tide_table:
                    filtered_tables_parent.append(table)

        return filtered_tables_parent

    def get_tide_tables(
        self,
        type_table: Optional[TypeTideTable] = None,
        parent_tide_table: Optional[str] = None,
    ) -> Response:
        """
        Méthode permettant de recupérer la liste des tables de marées.

            /rest/tideTables/

        :param type_table: (TypeTideTable) Un type de table. {VOLUME, AREA, SUB_AREA}
        :param parent_tide_table: (str) L'identifiant d'une table.
        :return: (Response) Un objet Response contenant l'ensemble des tables de marées correspondant
                            aux critères de la recherche.
        """
        query_params = self._validate_query_parameters(
            **{ids.TYPE: type_table, ids.PARENT_TIDE_TABLE: parent_tide_table}
        )
        url = self._construct_url(self.endpoint.TIDE_TABLES)

        tide_tables = self._query_handler.query(url, query_params)

        if type_table is None and parent_tide_table is None:
            return tide_tables

        filtered_tide_tables = self._filter_tables_by_type(
            tables_list=tide_tables.data, type_table=type_table
        )
        filtered_tide_tables_parent = self._filter_tables_by_parent(
            tables_list=filtered_tide_tables, parent_tide_table=parent_tide_table
        )

        return Response(data=filtered_tide_tables_parent)

    def get_tide_table(self, tide_table: str) -> Response:
        """
        Méthode permettant de recupérer une table de marées.

            /rest/tideTables/{tideTableId}

        :param tide_table: (str) L'identifiant d'une table de marées.
        :return: (Response) Un objet Response contenant les informations d'une table de marées.
        """
        url = self._construct_url(
            self.endpoint.TIDE_TABLE,
            tideTableId=tide_table,
        )

        return self._query_handler.query(url)

    def get_all_gnss_from_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer la liste des GNSS pour une station.

            /rest/stations/{stationId}/gnss

        :param station: (str) Le stationId de la station.
        :return: (Response) Un objet Response contenant la liste des GNSS pour une station.
        """
        url = self._construct_url(
            self.endpoint.GNSS_STATIONS,
            stationId=self._validate_station_id(station),
        )

        return self._query_handler.query(url)

    def get_gnss_station(self, station: str, gnss_id: str) -> Response:
        """
        Méthode permettant de récupérer les informations d'une station GNSS.

            /rest/stations/{stationId}/gnss/{gnssId}

        :param station: (str) Le stationId de la station.
        :param gnss_id: (str) L'identifiant d'une station GNSS.
        :return: (Response) Un objet Response contenant les informations d'une station GNSS.
        """
        url = self._construct_url(
            self.endpoint.GNSS_STATION,
            stationId=self._validate_station_id(station),
            gnssId=gnss_id,
        )

        return self._query_handler.query(url)

    def get_gnss_station_sum(self, station: str, gnss_id: str) -> Response:
        """
        Méthode permettant de récupérer un fichier .sum d'une station GNSS.

            /rest/stations/{stationId}/gnss/{gnssId}/sum

        :param station: (str) Le stationId de la station.
        :param gnss_id: (str) L'identifiant d'une station GNSS.
        :return: (Response) Un objet Response contenant le sum d'une station.
        """
        url = self._construct_url(
            self.endpoint.GNSS_SUM,
            stationId=self._validate_station_id(station),
            gnssId=gnss_id,
        )

        return self._query_handler.query(url, response_type=ResponseType.TEXT)

    def _get_benchmarks(
        self,
        benchmarks_ids: Collection[str] = None,
        station_ids: Collection[str] = None,
        page: int = 0,
    ) -> Response:
        """
        Méthode permettant de récupérer les repères des stations.

            /rest/benchmarks/

        :param benchmarks_ids: (Collection[str]) Une liste contenant les identifiants des repères.
        :param station_ids: (Collection[str]) Une liste contenant les identifiants des stations.
        :param page: (int) Le numéro de la page de résultat.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """
        query_params = self._validate_query_parameters(
            **{
                ids.BENCHMARKS: benchmarks_ids,
                ids.STATIONS: station_ids,
                ids.PAGE: page,
            }
        )
        url = self._construct_url(self.endpoint.BENCHMARKS)

        return self._query_handler.query(url, query_params)

    def get_benchmarks(
        self,
        benchmarks_ids: Collection[str] = None,
        station_ids: Collection[str] = None,
    ) -> Response:
        """
        Méthode permettant de récupérer les repères des stations pour toutes les pages.

            /rest/benchmarks/

        :param benchmarks_ids: (Collection[str]) Une liste contenant les identifiants des repères.
        :param station_ids: (Collection[str]) Une liste contenant les identifiants des stations.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """
        response = Response(data=[])
        benchmarks = self._get_benchmarks(benchmarks_ids, station_ids)

        if benchmarks.data:
            response.data.extend(benchmarks.data[ids.CONTENT])
        else:
            return benchmarks

        while not benchmarks.data[ids.LAST]:
            benchmarks = self._get_benchmarks(
                benchmarks_ids=benchmarks_ids,
                station_ids=station_ids,
                page=benchmarks.data[ids.PAGE_NUMBER] + 1,
            )

            if response.data:
                response.data.extend(benchmarks.data[ids.CONTENT])
            if response.error is not None:
                response.error += benchmarks.error
            if response.message is not None:
                response.message += benchmarks.message

        if response.error or response.message:
            response.status_code = 400

        return response

    def get_benchmark(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer un repère.

            /rest/benchmarks/{benchmarkId}

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les informations sur le repère.
        """
        url = self._construct_url(
            self.endpoint.BENCHMARK,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)

    def get_benchmark_metadata(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

            /rest/benchmarks/{benchmarkId}/metadata

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées sur le repère.
        """
        url = self._construct_url(
            self.endpoint.BENCHMARK_METADATA,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)

    def get_elevations(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

            /rest/benchmarks/{benchmarkId}/metadata

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées sur le repère.
        """
        url = self._construct_url(
            self.endpoint.ELEVVATIONS,
            benchmarkId=benchmark_id,
        )

        return self._query_handler.query(url)
