from datetime import datetime, timedelta
from typing import Optional, Generator


def get_datetime_from_iso8601(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def get_iso8601_from_datetime(date: datetime) -> str:
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")


def split_time(
    from_time: str,
    to_time: str,
    time_delta: Optional[timedelta] = timedelta(days=7),
) -> Generator[tuple[str, str], None, None]:
    from_datetime: datetime = get_datetime_from_iso8601(from_time)
    to_datetime: datetime = get_datetime_from_iso8601(to_time)

    current_start = from_datetime

    while current_start < to_datetime:
        current_end = min(current_start + time_delta, to_datetime)
        yield get_iso8601_from_datetime(current_start), get_iso8601_from_datetime(
            current_end
        )
        current_start = current_end
