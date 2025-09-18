from enum import StrEnum


class Regions(StrEnum):
    PAC = "PAC"
    CNA = "CNA"
    ATL = "ATL"
    QUE = "QUE"

    @staticmethod
    def get_values() -> list[str]:
        return [region for region in Regions]


class TimeResolution(StrEnum):
    ONE_MINUTE = "ONE_MINUTE"
    THREE_MINUTES = "THREE_MINUTES"
    FIVE_MINUTES = "FIVE_MINUTES"
    FIFTEEN_MINUTES = "FIFTEEN_MINUTES"
    SIXTY_MINUTES = "SIXTY_MINUTES"


class TimeSeries(StrEnum):
    WLO = "wlo"
    WL1 = "wl1"
    WL2 = "wl2"
    WL3 = "wl3"
    WS1 = "ws1"
    WS2 = "ws2"
    WT1 = "wt1"
    WT2 = "wt2"
    WT3 = "wt3"
    AP1 = "ap1"
    AP2 = "ap2"
    V1 = "v1"
    V2 = "v2"
    WLF = "wlf"
    WLF_SPINE = "wlf-spine"
    WLF_VTG = "wlf-vtg"
    WLP = "wlp"
    WLP_HILO = "wlp-hilo"
    WLP_BORES = "wlp-bores"
    WCP_SLACK = "wcp-slack"
    WCSP = "wcsp"
    WCSP_EXTREMA = "wcsp-extrema"
    WCDP = "wcdp"
    WCDP_EXTREMA = "wcdp-extrema"
    DVCF = "dvcf"
    DVCF_SPINE1 = "dvcf-spine1"

    @staticmethod
    def get_values() -> list[str]:
        return [time_series for time_series in TimeSeries]

    @classmethod
    def from_str(cls, value: str):
        for member in cls:
            if member.value == value:
                return member

        raise ValueError(
            f"'{value}' n'est pas valide. Vous devez choisir parmi les valeurs suivantes : {cls._value2member_map_.keys()}"
        )


class TimeZone(StrEnum):
    UTC = "UTC"
    LOCAL = "LOCAL"


class TypeTideTable(StrEnum):
    VOLUME = "VOLUME"
    AREA = "AREA"
    SUB_AREA = "SUB_AREA"


from enum import StrEnum


class EndpointType(StrEnum):
    PRIVATE_PROD = "EndpointPrivateProd"
    PRIVATE_DEV = "EndpointPrivateDev"
    PUBLIC = "EndpointPublic"

    @classmethod
    def from_str(cls, value: str):
        for member in cls:
            if member.value == value:
                return member

        raise ValueError(
            f"'{value}' n'est pas valide. Vous devez choisir parmi les valeurs suivantes : {cls._value2member_map_.keys()}"
        )
