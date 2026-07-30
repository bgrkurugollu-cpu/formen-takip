
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CalculationType, TargetScopeType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget, PerformanceLevelRule
from app.models.organization import Factory, Plant, Shift

LOCATION = "Karaman"
FACTORY_SEED = [
    dict(code="K1", name="K1 Fabrikası", plant_count=27),
    dict(code="K2", name="K2 Fabrikası", plant_count=23),
]
TOTAL_PLANTS = sum(f["plant_count"] for f in FACTORY_SEED)

FIRST_NAMES = [
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Osman", "Yusuf", "Murat",
    "Kemal", "Cengiz", "Serkan", "Onur", "Burak", "Emre", "Kaan", "Tolga", "Volkan", "Selim",
    "Barış", "Cem", "Ercan", "Fatih", "Gökhan", "Halil", "İsmail", "Kadir", "Levent", "Mert",
    "Oğuz", "Recep", "Sinan", "Tarık", "Ufuk", "Alper", "Hakan", "Kerem", "Umut", "Yavuz",
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife", "Sultan", "Esra",
    "Aslı", "Buse", "Ceren", "Damla", "Ebru", "Filiz", "Gamze", "Hülya", "İpek", "Kübra",
    "Leyla", "Melis", "Özlem", "Pınar", "Rabia", "Sevgi", "Tuğba", "Yasemin", "Zehra", "Aynur",
    "Berna", "Canan", "Dilek", "Emel", "Funda", "Handan", "Merve", "Nazlı", "Selin", "Tülay",
]
LAST_NAMES = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk", "Aydın", "Özdemir",
    "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek",
    "Polat", "Korkmaz", "Çakır", "Erdoğan", "Güneş", "Aksoy", "Bulut", "Yalçın", "Turan", "Avcı",
    "Şen", "Bozkurt", "Ateş", "Erdem", "Tekin", "Acar", "Karaca", "Sarı", "Uysal", "Toprak",
    "Duman", "Genç", "Tunç", "Başaran", "Fidan", "Gündüz", "Işık", "Kaplan", "Keskin", "Köse",
    "Ocak", "Sağlam", "Solmaz", "Taş", "Ünal", "Vural", "Yaman", "Akın", "Balcı", "Çiftçi",
    "Dinç", "Ergün", "Güler", "Koçak", "Öztaş", "Sezer", "Tanrıverdi", "Uçar", "Sevinç", "Zorlu",
]

DEFAULT_KPI_SEED = [
    dict(
        code="URETIM_GERCEKLESME", name="Üretim Hedef Gerçekleşme Oranı",
        description="Gerçekleşen üretim miktarının hedef üretim miktarına oranı.",
        unit="adet", calculation_type=CalculationType.HIGHER_IS_BETTER, success_direction_higher=True,
        default_target_value=1000, min_valid_value=0, max_valid_value=5000,
        min_score=0, max_score=120, weight=30, is_critical=True, display_order=1,
        rule_params={},
    ),
    dict(
        code="FIRE_ORANI", name="Fire Oranı",
        description="Üretilen miktara göre fireye ayrılan miktarın yüzdesi.",
        unit="%", calculation_type=CalculationType.LOWER_IS_BETTER, success_direction_higher=False,
        default_target_value=3.0, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=120, weight=20, is_critical=True, display_order=2,
        rule_params={},
    ),
    dict(
        code="PLANSIZ_DURUS", name="Plansız Duruş Süresi",
        description="Vardiya içindeki toplam plansız duruş süresi.",
        unit="dakika", calculation_type=CalculationType.PROPORTIONAL_PENALTY, success_direction_higher=False,
        default_target_value=30, min_valid_value=0, max_valid_value=480,
        min_score=0, max_score=120, weight=20, is_critical=True, display_order=3,
        rule_params={"penalty_per_unit": 5, "unit_size": 5},
    ),
    dict(
        code="KALITE_UYGUNLUK", name="Kalite Uygunluk Oranı",
        description="Kalite kontrolden uygun geçen üretimin yüzdesi.",
        unit="%", calculation_type=CalculationType.RANGE_TARGET, success_direction_higher=True,
        default_target_value=97, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=120, weight=20, is_critical=True, display_order=4,
        rule_params={"lower_bound": 95, "upper_bound": 100, "tolerance": 2, "penalty_rate": 4},
    ),
    dict(
        code="IS_GUVENLIGI", name="İş Güvenliği ve Süreç Uyum Puanı",
        description="Vardiya bazlı iş güvenliği ve süreç uyum denetim puanı.",
        unit="puan", calculation_type=CalculationType.DIRECT_SCORE, success_direction_higher=True,
        default_target_value=90, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=100, weight=10, is_critical=True, display_order=5,
        rule_params={},
    ),
]

PERFORMANCE_LEVEL_SEED = [
    dict(name="Kritik", min_score=0, max_score=69.99, description="Acil aksiyon gerektiren kritik performans.", color="#DC2626", icon="alert-triangle", sort_order=1),
    dict(name="Geliştirilmeli", min_score=70, max_score=79.99, description="Hedefin altında, iyileştirme gerekiyor.", color="#EA580C", icon="trending-down", sort_order=2),
    dict(name="İyi", min_score=80, max_score=89.99, description="Hedefe yakın, kabul edilebilir performans.", color="#CA8A04", icon="thumbs-up", sort_order=3),
    dict(name="Çok İyi", min_score=90, max_score=99.99, description="Hedefin büyük ölçüde karşılandığı güçlü performans.", color="#2563EB", icon="star", sort_order=4),
    dict(name="Mükemmel", min_score=100, max_score=120, description="Hedefi aşan üstün performans.", color="#16A34A", icon="trophy", sort_order=5),
]

SHIFT_SEED = [
    dict(code="V1", name="1. Vardiya", start="08:00", end="16:00", sequence=1),
    dict(code="V2", name="2. Vardiya", start="16:00", end="00:00", sequence=2),
    dict(code="V3", name="3. Vardiya", start="00:00", end="08:00", sequence=3),
]


@dataclass
class ReferenceData:
    factories: list[Factory] = field(default_factory=list)
    plants: list[Plant] = field(default_factory=list)
    shifts: list[Shift] = field(default_factory=list)
    chiefs: list[Chief] = field(default_factory=list)
    foremen: list[Foreman] = field(default_factory=list)
    assignments: list[ForemanAssignment] = field(default_factory=list)
    kpis: list[Kpi] = field(default_factory=list)
    calculation_rules: dict[str, KpiCalculationRule] = field(default_factory=dict)
    targets: list[KpiTarget] = field(default_factory=list)
    performance_levels: list[PerformanceLevelRule] = field(default_factory=list)

    def chiefs_by_plant(self, plant_id) -> list[Chief]:
        return [c for c in self.chiefs if c.plant_id == plant_id]


def _parse_time(value: str):
    from datetime import time

    h, m = value.split(":")
    return time(int(h), int(m))


def _build_unique_name_pool(rng: random.Random) -> list[tuple[str, str]]:
    combos = [(first, last) for first in FIRST_NAMES for last in LAST_NAMES]
    rng.shuffle(combos)
    return combos


def _take_name(pool: list[tuple[str, str]]) -> tuple[str, str]:
    if not pool:
        raise ValueError(
            "Benzersiz ad-soyad havuzu tükendi — FIRST_NAMES/LAST_NAMES listelerini genişletin."
        )
    return pool.pop()


def _chief_bucket_sizes(rng: random.Random, foreman_count: int) -> list[int]:
    if foreman_count <= 0:
        return []
    low = max(1, foreman_count // 6)
    high = max(1, foreman_count // 3)
    chief_count = min(foreman_count, rng.randint(low, high))
    sizes = [1] * chief_count
    remaining = foreman_count - chief_count
    for _ in range(remaining):
        sizes[rng.randrange(chief_count)] += 1
    return sizes


def seed_reference_data(
    db: Session,
    rng: random.Random,
    min_foremen_per_plant: int,
    max_foremen_per_plant: int,
    period_start: date,
    period_end: date,
) -> ReferenceData:
    ref = ReferenceData()

    for s in SHIFT_SEED:
        shift = Shift(
            code=s["code"], name=s["name"],
            start_time=_parse_time(s["start"]), end_time=_parse_time(s["end"]),
            sequence=s["sequence"], crosses_midnight=_parse_time(s["end"]) <= _parse_time(s["start"]),
            is_active=True,
        )
        db.add(shift)
        ref.shifts.append(shift)
    db.flush()

    for spec in DEFAULT_KPI_SEED:
        kpi = Kpi(
            code=spec["code"], name=spec["name"], description=spec["description"], unit=spec["unit"],
            calculation_type=spec["calculation_type"], success_direction_higher=spec["success_direction_higher"],
            default_target_value=spec["default_target_value"], min_valid_value=spec["min_valid_value"],
            max_valid_value=spec["max_valid_value"], min_score=spec["min_score"], max_score=spec["max_score"],
            weight=spec["weight"], valid_from=date(2020, 1, 1), is_active=True,
            aggregation_method=_default_aggregation_for(spec["calculation_type"]),
            decimal_places=2, is_critical=spec["is_critical"], display_order=spec["display_order"],
        )
        db.add(kpi)
        db.flush()
        rule = KpiCalculationRule(
            kpi_id=kpi.id, version=1, calculation_type=spec["calculation_type"],
            parameters=spec["rule_params"], valid_from=date(2020, 1, 1), is_active=True,
        )
        db.add(rule)
        ref.kpis.append(kpi)
        ref.calculation_rules[kpi.code] = rule
    db.flush()

    weights = [k.weight for k in ref.kpis]
    from app.services.kpi_engine import validate_kpi_weights

    ok, msg = validate_kpi_weights([float(w) for w in weights])
    if not ok:
        raise ValueError(f"Sentetik KPI seed verisi geçersiz ağırlıkla tanımlandı: {msg}")

    for lv in PERFORMANCE_LEVEL_SEED:
        level = PerformanceLevelRule(**lv)
        db.add(level)
        ref.performance_levels.append(level)
    db.flush()

    for kpi in ref.kpis:
        target = KpiTarget(
            kpi_id=kpi.id, scope_type=TargetScopeType.COMPANY, scope_id=None,
            target_value=kpi.default_target_value, valid_from=date(2020, 1, 1), is_active=True,
        )
        db.add(target)
        ref.targets.append(target)
    db.flush()

    factories_by_code: dict[str, Factory] = {}
    for spec in FACTORY_SEED:
        factory = Factory(code=spec["code"], name=spec["name"], location=LOCATION, is_active=True)
        db.add(factory)
        db.flush()
        ref.factories.append(factory)
        factories_by_code[spec["code"]] = factory

    name_pool = _build_unique_name_pool(rng)
    sequence_number = 0
    for spec in FACTORY_SEED:
        factory = factories_by_code[spec["code"]]
        for _ in range(spec["plant_count"]):
            sequence_number += 1
            plant = Plant(
                code=f"PLT{sequence_number:02d}",
                name=f"{sequence_number}. Tesis",
                sequence_number=sequence_number,
                factory_id=factory.id,
                description=f"{factory.name} bünyesindeki {sequence_number}. Tesis.",
                is_active=True,
                sap_plant_code=f"SAP-{sequence_number:04d}",
            )
            db.add(plant)
            db.flush()
            ref.plants.append(plant)

            foreman_count = rng.randint(min_foremen_per_plant, max_foremen_per_plant)
            bucket_sizes = _chief_bucket_sizes(rng, foreman_count)

            plant_chiefs: list[Chief] = []
            for chief_idx, size in enumerate(bucket_sizes, start=1):
                chief_hire = _random_date(
                    rng, period_start - timedelta(days=365 * 5), period_end - timedelta(days=1)
                )
                chief_first, chief_last = _take_name(name_pool)
                chief = Chief(
                    employee_number=f"SEF-{sequence_number:02d}-{chief_idx:02d}",
                    first_name=chief_first, last_name=chief_last,
                    plant_id=plant.id, hire_date=chief_hire, is_active=True,
                    sap_personnel_number=f"SAP-S-{sequence_number:02d}{chief_idx:02d}",
                )
                db.add(chief)
                db.flush()
                ref.chiefs.append(chief)
                plant_chiefs.append(chief)

            chief_assignment_plan: list[Chief] = []
            for chief, size in zip(plant_chiefs, bucket_sizes):
                chief_assignment_plan.extend([chief] * size)
            rng.shuffle(chief_assignment_plan)

            for foreman_idx, chief_for_foreman in enumerate(chief_assignment_plan, start=1):
                hire_earliest = period_start - timedelta(days=365 * 3)
                hire_latest = period_end - timedelta(days=1)
                hire_date = _random_date(rng, hire_earliest, hire_latest)

                is_terminated = rng.random() < 0.04
                termination_date = None
                is_active = True
                if is_terminated:
                    term_earliest = max(hire_date, period_start) + timedelta(days=30)
                    if term_earliest < period_end:
                        termination_date = _random_date(rng, term_earliest, period_end)
                        is_active = termination_date < period_end

                foreman_first, foreman_last = _take_name(name_pool)
                foreman = Foreman(
                    employee_number=f"SCL-{sequence_number:02d}-{foreman_idx:03d}",
                    first_name=foreman_first, last_name=foreman_last,
                    hire_date=hire_date, termination_date=termination_date, is_active=is_active,
                    sap_personnel_number=f"SAP-P-{sequence_number:02d}{foreman_idx:03d}",
                )
                db.add(foreman)
                db.flush()
                ref.foremen.append(foreman)

                shift = rng.choice(ref.shifts)
                assignment_start = hire_date
                changes_mid_period = rng.random() < 0.15 and not is_terminated

                if changes_mid_period:
                    change_earliest = max(assignment_start, period_start) + timedelta(days=30)
                    if change_earliest < period_end:
                        change_date = _random_date(rng, change_earliest, period_end)
                        first = ForemanAssignment(
                            foreman_id=foreman.id, plant_id=plant.id, chief_id=chief_for_foreman.id,
                            shift_id=shift.id,
                            start_date=assignment_start, end_date=change_date - timedelta(days=1), is_active=False,
                        )
                        db.add(first)
                        ref.assignments.append(first)

                        new_shift = rng.choice(ref.shifts)
                        second = ForemanAssignment(
                            foreman_id=foreman.id, plant_id=plant.id, chief_id=chief_for_foreman.id,
                            shift_id=new_shift.id,
                            start_date=change_date, end_date=termination_date, is_active=is_active,
                        )
                        db.add(second)
                        ref.assignments.append(second)
                        continue

                assignment = ForemanAssignment(
                    foreman_id=foreman.id, plant_id=plant.id, chief_id=chief_for_foreman.id,
                    shift_id=shift.id,
                    start_date=assignment_start, end_date=termination_date, is_active=is_active,
                )
                db.add(assignment)
                ref.assignments.append(assignment)

    db.commit()
    return ref


def regenerate_personnel_identities(db: Session, rng: random.Random) -> tuple[int, int]:
    plants = {p.id: p for p in db.scalars(select(Plant))}
    name_pool = _build_unique_name_pool(rng)

    chiefs = list(db.scalars(select(Chief)))
    chiefs.sort(key=lambda c: (plants[c.plant_id].sequence_number, c.employee_number))

    plant_by_foreman: dict = {}
    for assignment in db.scalars(select(ForemanAssignment).order_by(ForemanAssignment.start_date)):
        plant_by_foreman.setdefault(assignment.foreman_id, assignment.plant_id)

    foremen = [f for f in db.scalars(select(Foreman)) if f.id in plant_by_foreman]
    foremen.sort(key=lambda f: (plants[plant_by_foreman[f.id]].sequence_number, f.employee_number))

    chief_idx_by_plant: dict[int, int] = {}
    for chief in chiefs:
        seq = plants[chief.plant_id].sequence_number
        idx = chief_idx_by_plant.get(seq, 0) + 1
        chief_idx_by_plant[seq] = idx
        chief.first_name, chief.last_name = _take_name(name_pool)
        chief.employee_number = f"SEF-{seq:02d}-{idx:02d}"
        chief.sap_personnel_number = f"SAP-S-{seq:02d}{idx:02d}"

    foreman_idx_by_plant: dict[int, int] = {}
    for foreman in foremen:
        seq = plants[plant_by_foreman[foreman.id]].sequence_number
        idx = foreman_idx_by_plant.get(seq, 0) + 1
        foreman_idx_by_plant[seq] = idx
        foreman.first_name, foreman.last_name = _take_name(name_pool)
        foreman.employee_number = f"SCL-{seq:02d}-{idx:03d}"
        foreman.sap_personnel_number = f"SAP-P-{seq:02d}{idx:03d}"

    db.commit()
    return len(chiefs), len(foremen)


def _default_aggregation_for(calc_type: CalculationType):
    from app.models.enums import AggregationMethod

    if calc_type in (CalculationType.HIGHER_IS_BETTER, CalculationType.LOWER_IS_BETTER, CalculationType.RANGE_TARGET):
        return AggregationMethod.RATIO_RECOMPUTE
    if calc_type == CalculationType.PROPORTIONAL_PENALTY:
        return AggregationMethod.SUM
    return AggregationMethod.AVERAGE


def _random_date(rng: random.Random, start: date, end: date) -> date:
    if end <= start:
        return start
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))
