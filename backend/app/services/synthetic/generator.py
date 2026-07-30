
from __future__ import annotations

import random
import uuid
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.services.providers.base import RawPerformanceRecord
from app.services.synthetic.reference_data import ReferenceData

FIXED_HOLIDAYS_MMDD = {(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)}


@dataclass
class GenerationParams:
    missing_rate: float = 0.02
    error_rate: float = 0.01
    anomaly_rate: float = 0.015
    duplicate_rate: float = 0.005


def _is_holiday(d: date) -> bool:
    return (d.month, d.day) in FIXED_HOLIDAYS_MMDD


def _seasonal_factor(d: date) -> float:
    import math

    day_of_year = d.timetuple().tm_yday
    return 0.04 * math.sin(2 * math.pi * (day_of_year - 80) / 365)


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _build_plant_profiles(ref: ReferenceData, rng: random.Random) -> dict:
    profiles = {}
    for plant in ref.plants:
        profiles[plant.id] = {
            "base": rng.uniform(-0.12, 0.12),
            "trend": rng.uniform(-0.00015, 0.00025),
        }
    return profiles


def _build_foreman_profiles(ref: ReferenceData, rng: random.Random) -> dict:
    profiles = {}
    for foreman in ref.foremen:
        profiles[foreman.id] = {
            "skill": rng.uniform(-0.15, 0.15),
            "trend": rng.uniform(-0.0004, 0.0004),
        }
    return profiles


def _build_maintenance_windows(ref: ReferenceData, rng: random.Random, period_start: date, period_end: date) -> dict:
    windows: dict = defaultdict(list)
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return windows
    for plant in ref.plants:
        for _ in range(rng.randint(1, 3)):
            start_offset = rng.randint(0, total_days - 1)
            start = period_start + timedelta(days=start_offset)
            length = rng.randint(1, 3)
            for i in range(length):
                windows[plant.id].append(start + timedelta(days=i))
    return windows


def _iter_dates(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def generate_synthetic_records(
    ref: ReferenceData,
    period_start: date,
    period_end: date,
    rng: random.Random,
    params: GenerationParams,
) -> Iterator[RawPerformanceRecord]:
    plant_profiles = _build_plant_profiles(ref, rng)
    foreman_profiles = _build_foreman_profiles(ref, rng)
    maintenance_days = _build_maintenance_windows(ref, rng, period_start, period_end)

    shifts_by_id = {s.id: s for s in ref.shifts}
    kpi_by_code = {k.code: k for k in ref.kpis}
    plant_code_by_id = {p.id: p.code for p in ref.plants}
    chief_employee_number_by_id = {c.id: c.employee_number for c in ref.chiefs}
    assignments_by_foreman: dict = defaultdict(list)
    for a in ref.assignments:
        assignments_by_foreman[a.foreman_id].append(a)

    seq = 0

    for foreman in ref.foremen:
        f_profile = foreman_profiles[foreman.id]
        for assignment in assignments_by_foreman[foreman.id]:
            range_start = max(assignment.start_date, period_start)
            range_end = min(assignment.end_date or period_end, period_end)
            if range_start > range_end:
                continue

            plant_profile = plant_profiles[assignment.plant_id]
            shift = shifts_by_id[assignment.shift_id]
            night_penalty = -0.05 if shift.code == "V3" else (-0.015 if shift.code == "V2" else 0.0)

            for d in _iter_dates(range_start, range_end):
                day_index = (d - period_start).days
                weekday = d.weekday()
                weekend_factor = -0.10 if weekday >= 5 else 0.0
                holiday_factor = -0.35 if _is_holiday(d) else 0.0
                is_maintenance = d in maintenance_days.get(assignment.plant_id, [])
                maintenance_factor = -0.55 if is_maintenance else 0.0

                anomaly = 0.0
                if rng.random() < params.anomaly_rate:
                    anomaly = rng.choice([-1, 1]) * rng.uniform(0.15, 0.35)

                pf = (
                    plant_profile["base"]
                    + plant_profile["trend"] * day_index
                    + f_profile["skill"]
                    + f_profile["trend"] * (d - assignment.start_date).days
                    + night_penalty
                    + weekend_factor
                    + holiday_factor
                    + maintenance_factor
                    + _seasonal_factor(d)
                    + anomaly
                    + rng.gauss(0, 0.05)
                )
                pf = _clip(pf, -0.6, 0.45)

                downtime_multiplier = _clip(1.0 - pf * 1.4, 0.15, 3.2)
                base_downtime = 30.0
                downtime_minutes = max(0.0, base_downtime * downtime_multiplier + rng.gauss(0, 6))
                if is_maintenance:
                    downtime_minutes += rng.uniform(120, 300)

                production_factor = _clip(1.0 + pf - max(0.0, downtime_multiplier - 1) * 0.12, 0.15, 1.45)
                planned_qty = 1000.0
                produced_qty = max(0.0, planned_qty * production_factor + rng.gauss(0, 15))

                scrap_fraction = _clip(0.03 * (1 + max(0.0, downtime_multiplier - 1) * 0.6) - pf * 0.01 + rng.gauss(0, 0.004), 0.0, 0.35)
                scrap_qty = produced_qty * scrap_fraction
                fire_pct = (scrap_qty / produced_qty * 100) if produced_qty > 0 else 0.0

                inspection_ratio = rng.uniform(0.85, 1.0)
                inspected_qty = produced_qty * inspection_ratio
                defect_qty = min(inspected_qty, scrap_qty * rng.uniform(0.6, 1.1))
                ok_qty = max(0.0, inspected_qty - defect_qty)
                quality_pct = (ok_qty / inspected_qty * 100) if inspected_qty > 0 else 100.0

                safety_score = rng.uniform(92, 100)
                if rng.random() < 0.02:
                    safety_score = rng.uniform(40, 75)

                kpi_actuals = {
                    "URETIM_GERCEKLESME": (produced_qty, produced_qty, planned_qty),
                    "FIRE_ORANI": (fire_pct, scrap_qty, produced_qty),
                    "PLANSIZ_DURUS": (downtime_minutes, None, None),
                    "KALITE_UYGUNLUK": (quality_pct, ok_qty, inspected_qty),
                    "IS_GUVENLIGI": (safety_score, None, None),
                }

                for kpi_code, (actual, numerator, denominator) in kpi_actuals.items():
                    kpi = kpi_by_code[kpi_code]
                    seq += 1
                    source_record_id = f"SYN-{seq:09d}-{uuid.uuid4().hex[:8]}"
                    record_actual = actual
                    unit = kpi.unit

                    roll = rng.random()
                    if roll < params.missing_rate:
                        record_actual = None
                        numerator = None
                        denominator = None
                    elif roll < params.missing_rate + params.error_rate:
                        record_actual = -abs(actual) - rng.uniform(1, 50)

                    yield RawPerformanceRecord(
                        source_record_id=source_record_id,
                        performance_date=d,
                        plant_code=plant_code_by_id[assignment.plant_id],
                        chief_employee_number=chief_employee_number_by_id[assignment.chief_id],
                        shift_code=shift.code,
                        foreman_employee_number=foreman.employee_number,
                        kpi_code=kpi_code,
                        actual_value=record_actual,
                        unit=unit,
                        numerator_value=numerator,
                        denominator_value=denominator,
                        source_updated_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
                    )

                    if rng.random() < params.duplicate_rate:
                        seq += 1
                        yield RawPerformanceRecord(
                            source_record_id=f"SYN-{seq:09d}-{uuid.uuid4().hex[:8]}",
                            performance_date=d,
                            plant_code=plant_code_by_id[assignment.plant_id],
                            chief_employee_number=chief_employee_number_by_id[assignment.chief_id],
                            shift_code=shift.code,
                            foreman_employee_number=foreman.employee_number,
                            kpi_code=kpi_code,
                            actual_value=record_actual,
                            unit=unit,
                            numerator_value=numerator,
                            denominator_value=denominator,
                            source_updated_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
                        )
