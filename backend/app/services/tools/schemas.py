from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class _DateRangeArgs(BaseModel):
    start_date: date = Field(description="Başlangıç tarihi (YYYY-MM-DD)")
    end_date: date = Field(description="Bitiş tarihi (YYYY-MM-DD)")

    @model_validator(mode="after")
    def _check_order(self) -> "_DateRangeArgs":
        if self.start_date > self.end_date:
            raise ValueError("start_date, end_date'ten sonra olamaz.")
        return self


class GetAnomalyDetailsArgs(BaseModel):
    anomaly_id: str = Field(description="Tespit ID'si veya kodu (ör. ANM-2026-0001)")


class GetKpiHistoryArgs(_DateRangeArgs):
    plant_id: str = Field(description="Tesis kodu (ör. PLT12) veya ID'si")
    shift: str | None = Field(default=None, description="Vardiya kodu (V1/V2) veya numarası (1-2); boşsa tüm vardiyalar")
    kpi: str = Field(description="KPI kodu (ör. PLANA_UYUM) veya adı")
    granularity: Literal["daily", "shift", "weekly"] = "daily"


class CompareShiftsArgs(_DateRangeArgs):
    plant_id: str
    kpi: str


class ComparePlantsArgs(_DateRangeArgs):
    factory: str = Field(description="Fabrika kodu (K1/K2)")
    plant_id: str
    kpi: str


class GetRelatedKpisArgs(_DateRangeArgs):
    plant_id: str
    shift: str | None = None
    primary_kpi: str


class GetDowntimeBreakdownArgs(_DateRangeArgs):
    plant_id: str
    shift: str | None = None


class GetMaintenanceSignalsArgs(_DateRangeArgs):
    plant_id: str


class GetProductMixArgs(_DateRangeArgs):
    plant_id: str
    shift: str | None = None


class GetChangeoverRecordsArgs(_DateRangeArgs):
    plant_id: str
    shift: str | None = None


class GetShiftNotesArgs(_DateRangeArgs):
    plant_id: str
    shift: str | None = None


class FindSimilarAnomaliesArgs(BaseModel):
    anomaly_id: str
    kpi: str | None = None
    anomaly_type: str | None = None
    factory: str | None = None
    plant_id: str | None = None
    limit: int = Field(default=5, ge=1, le=10)
