"""`base.py`'deki arayüzlerin sentetik implementasyonları. Her sınıf yalnızca
`app/services/synthetic/world.py`'deki belirleyici fonksiyonları çağırır — kendi başına
rastgele/tutarsız veri üretmez."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.services.data_providers.base import (
    AnomalyDataProvider,
    DowntimeDataProvider,
    HistoricalCaseDataProvider,
    KPIDataProvider,
    MaintenanceDataProvider,
    ProductDataProvider,
    ShiftDataProvider,
)
from app.services.synthetic import world


class SyntheticAnomalyDataProvider(AnomalyDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_anomaly_details(self, anomaly_id: UUID) -> dict:
        anomaly = self.db.get(Anomaly, anomaly_id)
        if anomaly is None:
            raise world.WorldLookupError(f"Tespit bulunamadı: {anomaly_id}")
        return world.get_anomaly_details(self.db, anomaly)


class SyntheticKPIDataProvider(KPIDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_kpi_history(
        self, plant_id: UUID, shift_id: UUID | None, kpi_id: UUID, start_date: date, end_date: date, granularity: str
    ) -> dict:
        plant = self.db.get(Plant, plant_id)
        kpi = self.db.get(Kpi, kpi_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        daily = world.kpi_daily_series(self.db, plant, kpi, shift, start_date, end_date)

        if granularity == "daily":
            points = daily
        elif granularity == "weekly":
            points = _bucket(daily, 7)
        else:  # "shift" granülaritesi: tek vardiya seçiliyse günlük seriyle aynıdır
            points = daily if shift is not None else _bucket(daily, 1)

        return {
            "plant_name": plant.name, "kpi_name": kpi.name, "shift_name": shift.name if shift else "Tüm vardiyalar",
            "unit": kpi.unit, "granularity": granularity, "points": points, "record_count": len(daily),
        }

    def compare_shifts(self, plant_id: UUID, kpi_id: UUID, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        kpi = self.db.get(Kpi, kpi_id)
        result = world.compare_shifts(self.db, plant, kpi, start_date, end_date)
        return {
            "plant_name": result.plant_name, "kpi_name": result.kpi_name, "unit": result.unit,
            "shift_averages": result.per_shift, "plant_average": result.plant_average,
            "best_shift": result.best_shift, "worst_shift": result.worst_shift,
            "max_deviation_between_shifts": result.max_deviation_between_shifts,
            "observation_count": result.observation_count,
        }

    def compare_plants(self, factory_code: str, plant_id: UUID, kpi_id: UUID, start_date: date, end_date: date) -> dict:
        factory = self.db.scalar(select(Factory).where(Factory.code == factory_code))
        plant = self.db.get(Plant, plant_id)
        kpi = self.db.get(Kpi, kpi_id)
        result = world.compare_plants(self.db, factory, plant, kpi, start_date, end_date)
        return {
            "plant_name": result.plant_name, "plant_value": result.plant_value, "factory_code": result.factory_code,
            "factory_average": result.factory_average, "peers": result.peers, "rank": result.rank,
            "compared_plant_count": result.compared_plant_count,
        }

    def get_related_kpis(self, plant_id: UUID, shift_id: UUID | None, kpi_id: UUID, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        kpi = self.db.get(Kpi, kpi_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        related = world.related_kpi_changes(self.db, plant, shift, kpi, start_date, end_date)
        return {"plant_name": plant.name, "primary_kpi": kpi.name, "related_kpis": related}


class SyntheticDowntimeDataProvider(DowntimeDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_downtime_breakdown(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        return world.downtime_breakdown(self.db, plant, shift, None, start_date, end_date)


class SyntheticMaintenanceDataProvider(MaintenanceDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_maintenance_signals(self, plant_id: UUID, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        return world.maintenance_signals(self.db, plant, None, start_date, end_date)


class SyntheticProductDataProvider(ProductDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_product_mix(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        mix = world.product_mix(self.db, plant, shift, start_date, end_date)
        return {"plant_name": plant.name, "shift_name": shift.name if shift else "Tüm vardiyalar", "product_groups": mix}

    def get_changeover_records(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        records = world.changeover_records(self.db, plant, shift, start_date, end_date)
        return {"plant_name": plant.name, "shift_name": shift.name if shift else "Tüm vardiyalar", "records": records}


class SyntheticShiftDataProvider(ShiftDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def get_shift_notes(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        plant = self.db.get(Plant, plant_id)
        shift = self.db.get(Shift, shift_id) if shift_id else None
        notes = world.shift_notes(self.db, plant, shift, None, start_date, end_date)
        return {"plant_name": plant.name, "shift_name": shift.name if shift else "Tüm vardiyalar", "notes": notes}


class SyntheticHistoricalCaseDataProvider(HistoricalCaseDataProvider):
    def __init__(self, db: Session):
        self.db = db

    def find_similar_anomalies(
        self, anomaly_id: UUID, kpi_id: UUID | None, anomaly_type: str | None, factory_code: str | None,
        plant_id: UUID | None, limit: int,
    ) -> dict:
        kpi = self.db.get(Kpi, kpi_id) if kpi_id else None
        plant = self.db.get(Plant, plant_id) if plant_id else None
        factory = self.db.scalar(select(Factory).where(Factory.code == factory_code)) if factory_code else None
        cases = world.similar_historical_cases(self.db, anomaly_id, kpi, anomaly_type, factory, plant, limit)
        return {"cases": cases, "count": len(cases)}


def _bucket(points: list[dict], size: int) -> list[dict]:
    if size <= 1:
        return points
    buckets = []
    for i in range(0, len(points), size):
        chunk = points[i : i + size]
        avg_value = round(sum(p["value"] for p in chunk) / len(chunk), 2)
        buckets.append(
            {
                "date": chunk[0]["date"], "period_end": chunk[-1]["date"], "value": avg_value,
                "target": chunk[0]["target"], "deviation": round(avg_value - chunk[0]["target"], 2),
                "unit": chunk[0]["unit"], "data_quality": "valid",
            }
        )
    return buckets
