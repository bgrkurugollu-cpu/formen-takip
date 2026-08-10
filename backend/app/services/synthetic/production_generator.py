
from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import SourceSystem
from app.models.production import CompanyCalendarDay, ForemanWorkCalendar, Product, ProductionLine, ProductionRecord
from app.services.shift_rotation import actual_shift_for_date
from app.services.synthetic.reference_data import ReferenceData

FIXED_HOLIDAYS_MMDD = {(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)}

# Şirket ürün kataloğu (SAP malzeme master'ının sentetik karşılığı). Bilinçli olarak
# iki üründe standart gramaj tanımlı bırakılmamıştır — bu ürünlere bağlı üretim
# kayıtları için Ağır Gitme KPI'sı hesaplanmayacaktır (bkz. production_kpi_derivation.py).
PRODUCT_CATALOG = [
    dict(code="MLZ-001", name="Yem Tipi A - 40gr Paket", standard_gram=40.0, tolerance_pct=0.05),
    dict(code="MLZ-002", name="Yem Tipi B - 25gr Paket", standard_gram=25.0, tolerance_pct=0.06),
    dict(code="MLZ-003", name="Yem Tipi C - 50gr Paket", standard_gram=50.0, tolerance_pct=0.04),
    dict(code="MLZ-004", name="Yem Tipi D - 20gr Paket", standard_gram=20.0, tolerance_pct=0.07),
    dict(code="MLZ-005", name="Yem Tipi E - 35gr Paket (standart tanımlanmadı)", standard_gram=None, tolerance_pct=None),
    dict(code="MLZ-006", name="Yem Tipi F - 60gr Paket", standard_gram=60.0, tolerance_pct=0.03),
    dict(code="MLZ-007", name="Yem Tipi G - 30gr Paket (standart tanımlanmadı)", standard_gram=None, tolerance_pct=None),
    dict(code="MLZ-008", name="Yem Tipi H - 45gr Paket", standard_gram=45.0, tolerance_pct=0.05),
]


@dataclass
class GenerationParams:
    missing_rate: float = 0.02
    error_rate: float = 0.01
    anomaly_rate: float = 0.015
    duplicate_rate: float = 0.005


@dataclass
class ProductionReferenceData:
    products: list[Product] = field(default_factory=list)
    lines_by_plant: dict = field(default_factory=dict)
    holiday_dates: set = field(default_factory=set)
    work_calendar: list[ForemanWorkCalendar] = field(default_factory=list)
    production_records: list[ProductionRecord] = field(default_factory=list)


def _is_holiday(d: date) -> bool:
    return (d.month, d.day) in FIXED_HOLIDAYS_MMDD


def _seasonal_factor(d: date) -> float:
    day_of_year = d.timetuple().tm_yday
    return 0.04 * math.sin(2 * math.pi * (day_of_year - 80) / 365)


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _seed_products(db: Session) -> list[Product]:
    products = []
    for spec in PRODUCT_CATALOG:
        std = spec["standard_gram"]
        tol = spec["tolerance_pct"]
        lower = (std * (1 - tol)) if (std is not None and tol is not None) else None
        upper = (std * (1 + tol)) if (std is not None and tol is not None) else None
        product = Product(
            code=spec["code"], name=spec["name"], unit="GR",
            standard_gram=std, lower_gram_limit=lower, upper_gram_limit=upper,
            is_active=True, sap_material_code=f"SAP-{spec['code']}",
        )
        db.add(product)
        products.append(product)
    db.flush()
    return products


def _seed_production_lines(db: Session, rng: random.Random, plants) -> dict:
    lines_by_plant: dict = {}
    for plant in plants:
        count = rng.randint(1, 2)
        plant_lines = []
        for i in range(1, count + 1):
            line = ProductionLine(
                code=f"HAT-{plant.sequence_number:02d}-{i}", name=f"{plant.name} - Hat {i}",
                plant_id=plant.id, is_active=True,
            )
            db.add(line)
            plant_lines.append(line)
        lines_by_plant[plant.id] = plant_lines
    db.flush()
    return lines_by_plant


def _seed_holidays(db: Session, period_start: date, period_end: date) -> set:
    holiday_dates: set = set()
    d = period_start
    while d <= period_end:
        if _is_holiday(d):
            db.add(CompanyCalendarDay(calendar_date=d, is_holiday=True, note="Resmi tatil"))
            holiday_dates.add(d)
        d += timedelta(days=1)
    db.flush()
    return holiday_dates


def _build_plant_profiles(plants, rng: random.Random) -> dict:
    return {p.id: {"base": rng.uniform(-0.12, 0.12), "trend": rng.uniform(-0.00015, 0.00025)} for p in plants}


def _build_foreman_profiles(foremen, rng: random.Random) -> dict:
    # Formenler arası kalıcı beceri farkı (bkz. KPI'lara özgü katsayılar aşağıda) — dar bir aralık
    # günlük gürültü içinde kaybolup her formeni hedefin aynı tarafında bırakıyordu; bu aralık
    # gerçek bir formen sıralaması (bazıları hedefin üstünde, bazıları altında) üretecek kadar geniş.
    return {f.id: {"skill": rng.uniform(-0.35, 0.35), "trend": rng.uniform(-0.0004, 0.0004)} for f in foremen}


def _build_maintenance_windows(plants, rng: random.Random, period_start: date, period_end: date) -> dict:
    windows: dict = defaultdict(set)
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return windows
    for plant in plants:
        for _ in range(rng.randint(1, 3)):
            start = period_start + timedelta(days=rng.randint(0, total_days - 1))
            for i in range(rng.randint(1, 3)):
                windows[plant.id].add(start + timedelta(days=i))
    return windows


def _plant_product_pool(plants, products: list[Product], rng: random.Random) -> dict:
    pool: dict = {}
    for plant in plants:
        count = rng.randint(2, 4)
        pool[plant.id] = rng.sample(products, k=min(count, len(products)))
    return pool


def seed_production_data(
    db: Session,
    rng: random.Random,
    ref: ReferenceData,
    period_start: date,
    period_end: date,
    params: GenerationParams,
) -> ProductionReferenceData:
    result = ProductionReferenceData()
    result.products = _seed_products(db)
    result.lines_by_plant = _seed_production_lines(db, rng, ref.plants)
    result.holiday_dates = _seed_holidays(db, period_start, period_end)

    plant_profiles = _build_plant_profiles(ref.plants, rng)
    foreman_profiles = _build_foreman_profiles(ref.foremen, rng)
    maintenance_days = _build_maintenance_windows(ref.plants, rng, period_start, period_end)
    plant_products = _plant_product_pool(ref.plants, result.products, rng)

    shifts_by_id = {s.id: s for s in ref.shifts}
    assignments_by_foreman: dict = defaultdict(list)
    for a in ref.assignments:
        assignments_by_foreman[a.foreman_id].append(a)

    seq = 0

    for foreman in ref.foremen:
        f_profile = foreman_profiles[foreman.id]
        foreman_assignments = assignments_by_foreman[foreman.id]
        if not foreman_assignments:
            continue

        # Bir formenin tüm eşzamanlı atamaları (2-4 tesis) aynı vardiya çıpasını ve aynı tenure
        # aralığını paylaşır (bkz. reference_data.py) — her atama kendi tesisi için ayrı
        # günlük kayıt üretir (natural key'ler artık plant_id içeriyor, bkz. production.py).
        # Gerçek günlük vardiya bu çıpadan haftalık olarak dönüşümlü hesaplanır (aşağıdaki
        # gün döngüsünde `actual_shift_for_date` ile), çıpanın kendisi değil.
        tenure_start = foreman_assignments[0].start_date
        tenure_end = foreman_assignments[0].end_date
        range_start = max(tenure_start, period_start)
        range_end = min(tenure_end or period_end, period_end)
        if range_start > range_end:
            continue

        anchor_shift = shifts_by_id[foreman_assignments[0].shift_id]

        for assignment in foreman_assignments:
            plant_profile = plant_profiles[assignment.plant_id]
            plant_lines = result.lines_by_plant[assignment.plant_id]
            products = plant_products[assignment.plant_id]

            d = range_start
            while d <= range_end:
                shift = actual_shift_for_date(d, anchor_shift, ref.shifts)
                night_penalty = -0.05 if shift.code == "V2" else 0.0

                is_holiday = d in result.holiday_dates
                is_absent = (not is_holiday) and rng.random() < 0.03
                is_working = not is_holiday and not is_absent
                line = rng.choice(plant_lines)

                calendar_row = ForemanWorkCalendar(
                    foreman_id=foreman.id, work_date=d, plant_id=assignment.plant_id,
                    chief_id=assignment.chief_id, shift_id=shift.id, line_id=line.id,
                    is_working=is_working,
                )
                db.add(calendar_row)
                result.work_calendar.append(calendar_row)

                if not is_working:
                    d += timedelta(days=1)
                    continue

                weekday = d.weekday()
                weekend_factor = -0.10 if weekday >= 5 else 0.0
                is_maintenance = d in maintenance_days.get(assignment.plant_id, set())
                maintenance_factor = -0.55 if is_maintenance else 0.0

                anomaly = 0.0
                if rng.random() < params.anomaly_rate:
                    anomaly = rng.choice([-1, 1]) * rng.uniform(0.15, 0.35)

                pf = (
                    plant_profile["base"] + plant_profile["trend"] * (d - period_start).days
                    + f_profile["skill"] + f_profile["trend"] * (d - tenure_start).days
                    + night_penalty + weekend_factor + maintenance_factor
                    + _seasonal_factor(d) + anomaly + rng.gauss(0, 0.05)
                )
                pf = _clip(pf, -0.6, 0.45)

                # Teknik + İmalat puanlamaya dahil edilir (spec bölüm 3.4/7); Diğer (format değişimi,
                # temizlik, planlı bakım) puanlamaya hiç dahil edilmez — eski planned/unplanned ikilisi
                # yerini bu üç bileşene bırakır (bkz. production_kpi_derivation.py).
                downtime_multiplier = _clip(1.0 - pf * 1.4, 0.15, 3.2)
                # Taban dakikalar İnkita hedefine (~%10) yakın oturacak şekilde ölçeklenir — eski
                # düşük taban (18/12dk), gevşek hedefle birleşince downtime_multiplier ne olursa
                # olsun herkesi hedefin rahatça altında bırakıyordu.
                technical_minutes = max(0.0, 45.0 * downtime_multiplier + rng.gauss(0, 6))
                manufacturing_minutes = max(0.0, 30.0 * downtime_multiplier + rng.gauss(0, 4))
                other_minutes = max(0.0, rng.uniform(10, 25) + rng.gauss(0, 3))
                if is_maintenance:
                    other_minutes += rng.uniform(90, 220)

                production_factor = _clip(1.0 + pf - max(0.0, downtime_multiplier - 1) * 0.12, 0.15, 1.45)
                planned_qty = 1000.0
                actual_qty = max(0.0, planned_qty * production_factor + rng.gauss(0, 15))

                scrap_fraction = _clip(
                    0.03 * (1 + max(0.0, downtime_multiplier - 1) * 0.6) - pf * 0.01 + rng.gauss(0, 0.004), 0.0, 0.35
                )
                scrap_qty = actual_qty * scrap_fraction
                recoverable_fraction = _clip(0.65 + rng.gauss(0, 0.08), 0.3, 0.9)
                iskarta_qty = scrap_qty * recoverable_fraction
                gsf_qty = scrap_qty - iskarta_qty

                product = rng.choice(products)
                gram_baseline = float(product.standard_gram) if product.standard_gram is not None else 35.0
                # Katsayı (3.0 -> 5.5) ve taban (0.4 -> 1.4) formen becerisinin tolerans bandını
                # (ürün başına ~%3-7) gerçekten aşıp aşmayacağını belirleyecek kadar güçlü —
                # eskisi günlük gürültü içinde kaybolup herkesi bandın içinde bırakıyordu.
                gram_overage = _clip(1.4 - pf * 5.5 + rng.gauss(0, 0.5), -1.2, 8.0)
                measured_avg_gram = gram_baseline + gram_overage
                gram_sample_count = rng.randint(15, 40)

                planned_start = datetime.combine(d, shift.start_time, tzinfo=timezone.utc)
                end_date = d + timedelta(days=1) if shift.crosses_midnight else d
                planned_end = datetime.combine(end_date, shift.end_time, tzinfo=timezone.utc)
                actual_start = planned_start + timedelta(minutes=rng.gauss(0, 4))
                actual_end = planned_end + timedelta(minutes=rng.gauss(0, 6))
                shift_hours = (planned_end - planned_start).total_seconds() / 3600.0

                roll = rng.random()
                if roll < params.missing_rate:
                    actual_qty = None
                    actual_speed = None
                    actual_start_val = None
                    actual_end_val = None
                elif roll < params.missing_rate + params.error_rate:
                    actual_qty = -abs(actual_qty) - rng.uniform(1, 50)
                    actual_speed = actual_qty / shift_hours if actual_qty else None
                    actual_start_val = actual_start
                    actual_end_val = actual_end
                else:
                    actual_speed = actual_qty / shift_hours
                    actual_start_val = actual_start
                    actual_end_val = actual_end

                seq += 1
                record = ProductionRecord(
                    source_system=SourceSystem.SYNTHETIC,
                    source_record_id=f"PROD-{seq:09d}-{uuid.uuid4().hex[:8]}",
                    production_order_number=f"45{seq:08d}",
                    batch_number=f"LOT-{d.strftime('%y%m%d')}-{seq % 100:02d}",
                    plant_id=assignment.plant_id, line_id=line.id, product_id=product.id,
                    foreman_id=foreman.id, chief_id=assignment.chief_id, shift_id=shift.id,
                    production_date=d, unit="KG",
                    planned_qty=planned_qty, actual_qty=actual_qty,
                    planned_start_at=planned_start, planned_end_at=planned_end,
                    actual_start_at=actual_start_val, actual_end_at=actual_end_val,
                    standard_speed=planned_qty / shift_hours, actual_speed=actual_speed,
                    measured_avg_gram=measured_avg_gram, gram_sample_count=gram_sample_count,
                    gsf_qty=gsf_qty, iskarta_qty=iskarta_qty,
                    technical_downtime_minutes=technical_minutes, manufacturing_downtime_minutes=manufacturing_minutes,
                    other_downtime_minutes=other_minutes,
                    plan_revision_no=1, plan_revision_at=planned_start - timedelta(days=1),
                    source_updated_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
                    imported_at=datetime.now(timezone.utc),
                )
                db.add(record)
                result.production_records.append(record)

                d += timedelta(days=1)

    db.commit()
    return result
