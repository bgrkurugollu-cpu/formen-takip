
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID


class AnomalyDataProvider(ABC):
    @abstractmethod
    def get_anomaly_details(self, anomaly_id: UUID) -> dict:
        raise NotImplementedError


class KPIDataProvider(ABC):
    @abstractmethod
    def get_kpi_history(
        self, plant_id: UUID, shift_id: UUID | None, kpi_id: UUID, start_date: date, end_date: date, granularity: str
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def compare_shifts(self, plant_id: UUID, kpi_id: UUID, start_date: date, end_date: date) -> dict:
        raise NotImplementedError

    @abstractmethod
    def compare_plants(self, factory_code: str, plant_id: UUID, kpi_id: UUID, start_date: date, end_date: date) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_related_kpis(
        self, plant_id: UUID, shift_id: UUID | None, kpi_id: UUID, start_date: date, end_date: date
    ) -> dict:
        raise NotImplementedError


class DowntimeDataProvider(ABC):
    @abstractmethod
    def get_downtime_breakdown(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        raise NotImplementedError


class MaintenanceDataProvider(ABC):
    @abstractmethod
    def get_maintenance_signals(self, plant_id: UUID, start_date: date, end_date: date) -> dict:
        raise NotImplementedError


class ProductDataProvider(ABC):
    @abstractmethod
    def get_product_mix(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_changeover_records(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        raise NotImplementedError


class ShiftDataProvider(ABC):
    @abstractmethod
    def get_shift_notes(self, plant_id: UUID, shift_id: UUID | None, start_date: date, end_date: date) -> dict:
        raise NotImplementedError


class HistoricalCaseDataProvider(ABC):
    @abstractmethod
    def find_similar_anomalies(
        self, anomaly_id: UUID, kpi_id: UUID | None, anomaly_type: str | None, factory_code: str | None,
        plant_id: UUID | None, limit: int,
    ) -> dict:
        raise NotImplementedError
