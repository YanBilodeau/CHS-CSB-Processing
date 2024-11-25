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
    ONE_MINUTE: str = "ONE_MINUTE"
    THREE_MINUTES: str = "THREE_MINUTES"
    FIVE_MINUTES: str = "FIVE_MINUTES"
    FIFTEEN_MINUTES: str = "FIFTEEN_MINUTES"
    SIXTY_MINUTES: str = "SIXTY_MINUTES"


class TimeSeries(StrEnum):
    WLO: str = "wlo"
    WL1: str = "wl1"
    WL2: str = "wl2"
    WL3: str = "wl3"
    WS1: str = "ws1"
    WS2: str = "ws2"
    WT1: str = "wt1"
    WT2: str = "wt2"
    WT3: str = "wt3"
    AP1: str = "ap1"
    AP2: str = "ap2"
    V1: str = "v1"
    V2: str = "v2"
    WLF: str = "wlf"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLP: str = "wlp"
    WLP_HILO: str = "wlp-hilo"
    WLP_BORES: str = "wlp-bores"
    WCP_SLACK: str = "wcp-slack"
    WCSP: str = "wcsp"
    WCSP_EXTREMA: str = "wcsp-extrema"
    WCDP: str = "wcdp"
    WCDP_EXTREMA: str = "wcdp-extrema"
    DVCF: str = "dvcf"
    DVCF_SPINE1: str = "dvcf-spine1"

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
    UTC: str = "UTC"
    LOCAL: str = "LOCAL"


class TypeTideTable(StrEnum):
    VOLUME: str = "VOLUME"
    AREA: str = "AREA"
    SUB_AREA: str = "SUB_AREA"


from enum import StrEnum


class EndpointType(StrEnum):
    PRIVATE_PROD: str = "EndpointPrivateProd"
    PRIVATE_DEV: str = "EndpointPrivateDev"
    PUBLIC: str = "EndpointPublic"

    @classmethod
    def from_str(cls, value: str):
        for member in cls:
            if member.value == value:
                return member

        raise ValueError(
            f"'{value}' n'est pas valide. Vous devez choisir parmi les valeurs suivantes : {cls._value2member_map_.keys()}"
        )
