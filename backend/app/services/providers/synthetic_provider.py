
from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date

from sqlalchemy.orm import Session

from app.models.enums import SourceSystem
from app.services.production_kpi_derivation import derive_raw_performance_records
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord


class SyntheticDataProvider(PerformanceDataProvider):

    source_system = SourceSystem.SYNTHETIC

    def __init__(self, db: Session, rng: random.Random | None = None, duplicate_rate: float = 0.0) -> None:
        self._db = db
        self._rng = rng
        self._duplicate_rate = duplicate_rate

    def fetch(
        self,
        date_from: date,
        date_to: date,
        plant_codes: list[str] | None = None,
    ) -> Iterator[RawPerformanceRecord]:
        yield from derive_raw_performance_records(
            self._db, date_from, date_to, plant_codes,
            duplicate_rate=self._duplicate_rate, rng=self._rng,
        )
