
from __future__ import annotations

from datetime import date, datetime, time, timedelta

# Sentetik üretici hiçbir zaman ham bir zaman damgasından tarih çıkarmaz (üretim günü baştan
# bilinir, oradan zaman damgaları türetilir — bkz. production_generator.py) ve `SAPDataProvider`
# henüz implement edilmemiştir (bkz. providers/sap_provider.py) — bu yüzden bu fonksiyonların
# şu an hiçbir gerçek çağıranı yoktur. Gerçek SAP entegrasyonu ham konfirmasyon zaman damgalarını
# üretim gününe bağlamak için bunları kullanmalıdır, yeniden yazmamalıdır.


def shift_crosses_midnight(start_time: time, end_time: time) -> bool:
    return end_time <= start_time


def resolve_production_date(clock_dt: datetime, shift_start: time, shift_end: time) -> date:
    if shift_crosses_midnight(shift_start, shift_end) and clock_dt.time() < shift_start:
        return (clock_dt - timedelta(days=1)).date()
    return clock_dt.date()
