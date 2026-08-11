
from __future__ import annotations

from datetime import date, datetime, time, timedelta



def shift_crosses_midnight(start_time: time, end_time: time) -> bool:
    return end_time <= start_time


def resolve_production_date(clock_dt: datetime, shift_start: time, shift_end: time) -> date:
    if shift_crosses_midnight(shift_start, shift_end) and clock_dt.time() < shift_start:
        return (clock_dt - timedelta(days=1)).date()
    return clock_dt.date()
