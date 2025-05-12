from enum import StrEnum


class Status(StrEnum):
    """
    Enum pour les statuts de filtrage des données.
    """

    ACCEPTED = "accepted"
    REJECTED_BY_SPEED_FILTER = "rejected by speed filter"
    REJECTED_BY_LATITUDE_FILTER = "rejected by latitude filter"
    REJECTED_BY_LONGITUDE_FILTER = "rejected by longitude filter"
    REJECTED_BY_TIME_FILTER = "rejected by time filter"
    REJECTED_BY_DEPTH_FILTER = "rejected by depth filter"


class FiltersEnum(StrEnum):
    """
    Enum for status codes.
    """

    SPEED_FILTER = "SPEED_FILTER"
    LATITUDE_FILTER = "LATITUDE_FILTER"
    LONGITUDE_FILTER = "LONGITUDE_FILTER"
    TIME_FILTER = "TIME_FILTER"
    DEPTH_FILTER = "DEPTH_FILTER"


FILTER_STATUS_MAPPING: dict[FiltersEnum, Status] = {
    FiltersEnum.SPEED_FILTER: Status.REJECTED_BY_SPEED_FILTER,
    FiltersEnum.LATITUDE_FILTER: Status.REJECTED_BY_LATITUDE_FILTER,
    FiltersEnum.LONGITUDE_FILTER: Status.REJECTED_BY_LONGITUDE_FILTER,
    FiltersEnum.TIME_FILTER: Status.REJECTED_BY_TIME_FILTER,
    FiltersEnum.DEPTH_FILTER: Status.REJECTED_BY_DEPTH_FILTER,
}
