
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime

from app.models.enums import SourceSystem


@dataclass
class RawPerformanceRecord:

    source_record_id: str
    performance_date: date
    plant_code: str
    chief_employee_number: str
    shift_code: str
    foreman_employee_number: str
    kpi_code: str
    actual_value: float | None
    unit: str
    target_value: float | None = None
    numerator_value: float | None = None
    denominator_value: float | None = None
    source_updated_at: datetime | None = None


class PerformanceDataProvider(ABC):

    source_system: SourceSystem

    @abstractmethod
    def fetch(
        self,
        date_from: date,
        date_to: date,
        plant_codes: list[str] | None = None,
    ) -> Iterator[RawPerformanceRecord]:
        raise NotImplementedError
