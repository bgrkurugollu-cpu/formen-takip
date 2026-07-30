
from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget, PerformanceLevelRule
from app.models.organization import Plant, Shift
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord
from app.services.synthetic.generator import GenerationParams, generate_synthetic_records
from app.services.synthetic.reference_data import ReferenceData


class SyntheticDataProvider(PerformanceDataProvider):
    source_system = SourceSystem.SYNTHETIC

    def __init__(self, db: Session, rng: random.Random, params: GenerationParams | None = None) -> None:
        self._db = db
        self._rng = rng
        self._params = params or GenerationParams()

    def _load_reference_data(self, plant_codes: list[str] | None) -> ReferenceData:
        ref = ReferenceData()
        plant_query = select(Plant)
        if plant_codes:
            plant_query = plant_query.where(Plant.code.in_(plant_codes))
        ref.plants = list(self._db.scalars(plant_query))
        plant_ids = [p.id for p in ref.plants]

        ref.chiefs = list(self._db.scalars(select(Chief).where(Chief.plant_id.in_(plant_ids))))
        ref.shifts = list(self._db.scalars(select(Shift)))
        ref.kpis = list(self._db.scalars(select(Kpi).where(Kpi.is_active.is_(True))))
        ref.performance_levels = list(self._db.scalars(select(PerformanceLevelRule)))
        ref.targets = list(self._db.scalars(select(KpiTarget)))
        for rule in self._db.scalars(select(KpiCalculationRule).where(KpiCalculationRule.is_active.is_(True))):
            kpi = next((k for k in ref.kpis if k.id == rule.kpi_id), None)
            if kpi:
                ref.calculation_rules[kpi.code] = rule

        assignments = list(self._db.scalars(select(ForemanAssignment).where(ForemanAssignment.plant_id.in_(plant_ids))))
        ref.assignments = assignments
        foreman_ids = {a.foreman_id for a in assignments}
        ref.foremen = list(self._db.scalars(select(Foreman).where(Foreman.id.in_(foreman_ids)))) if foreman_ids else []
        return ref

    def fetch(
        self,
        date_from: date,
        date_to: date,
        plant_codes: list[str] | None = None,
    ) -> Iterator[RawPerformanceRecord]:
        ref = self._load_reference_data(plant_codes)
        yield from generate_synthetic_records(ref, date_from, date_to, self._rng, self._params)
