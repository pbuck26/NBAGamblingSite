"""Time helpers. NBA schedules run on US Eastern time; the database stores naive UTC."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_et():
    return datetime.now(ET).date()


def to_et(naive_utc):
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(ET)
