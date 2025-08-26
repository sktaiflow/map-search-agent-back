import datetime
from zoneinfo import ZoneInfo
from dateutil.parser import parse
from configs import config

KST = ZoneInfo("Asia/Seoul")
UTC = datetime.timezone.utc

PHASE = config.stack_type.lower()
WEEKDAY_MAP = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


def get_korean_weekday(date: datetime.datetime) -> str:
    return WEEKDAY_MAP.get(date.weekday())


def strptime_with_tz(date_string: str, format: str, tzinfo: ZoneInfo):
    dt = datetime.datetime.strptime(date_string, format)
    return datetime.datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, tzinfo=tzinfo
    )


def strftime_with_tz(date: datetime.datetime, format: str, tzinfo: ZoneInfo):
    return date.astimezone(tzinfo).strftime(format)


def parse_to_utc(dt_str: str):
    dt = parse(dt_str)
    return (
        dt.replace(tzinfo=datetime.timezone.utc)
        if dt.tzinfo is None
        else dt.astimezone(datetime.timezone.utc)
    )


def parse_utc_str_to_kst_date_str(dt_str: str | None) -> str | None:
    if dt_str is None:
        return None
    dt = parse(dt_str)
    return dt.astimezone(KST).strftime("%Y-%m-%d")
