from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.models.performance import PerformanceRecord
from app.services.shift_rotation import ROTATION_EPOCH

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


# Vardiya Analizi sayfasının anomali eşikleri — tek yerde tutulan, kolayca ayarlanabilir
# sabitler (bkz. anomaly_kpi_defs.py'deki KPI_DEFINITIONS ile aynı desen). DB'ye taşınmadı
# çünkü bu sayfa DB'ye hiçbir şey yazmıyor, tamamen istek anında hesaplanıyor (spec: "yönetime
# anlamlı içgörü" — akademik bir istatistik modeli değil).
@dataclass(frozen=True)
class ShiftAnomalyThresholds:
    medium_pct: float = 8.0
    high_pct: float = 15.0
    # Bir formen tarafının o ay/vardiya/tesis/KPI hücresinde anlamlı sayılması için gereken
    # asgari kayıt sayısı — çok az veri üzerinden "anomali" etiketlemeyi engeller.
    min_records_per_side: int = 4
    # Yüzdesel eşiğe EK OLARAK aranan asgari mutlak fark (yüzde puanı cinsinden — tüm KPI'ların
    # birimi "%"). Ağır Gitme/GSF/Iskarta/İnkita gibi ideal değeri sıfıra yakın KPI'larda iki
    # tarafın da neredeyse sıfır olduğu durumlarda (ör. %0.04 vs %0.43) yüzdesel fark kolayca
    # eşiği geçer ama mutlak fark yönetim için anlamsız kalır — bu taban, gerçekten önemsiz
    # sapmaların kart listesini gürültüyle doldurmasını engeller.
    min_abs_diff_points: float = 1.0


DEFAULT_THRESHOLDS = ShiftAnomalyThresholds()


def month_label(d: date) -> str:
    return f"{TR_MONTHS[d.month - 1]} {d.year}"


def previous_completed_month(today: date) -> tuple[date, date]:
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    return last_of_prev_month.replace(day=1), last_of_prev_month


def _week_index(d: date) -> int:
    """Formen rotasyonuyla aynı hafta sınırlarını kullanır (bkz. shift_rotation.py) — bu sayede
    bir hafta bucket'ı içinde hangi formenin hangi fiziksel vardiyada olduğu asla değişmez."""
    return (d - ROTATION_EPOCH).days // 7


@dataclass
class _RawRow:
    plant_id: UUID
    shift_id: UUID
    foreman_id: UUID
    kpi_id: UUID
    performance_date: date
    numerator: float
    denominator: float


def _fetch_raw_rows(
    db: Session, month_start: date, month_end: date, *,
    plant_ids: list[UUID] | None = None, factory_ids: list[UUID] | None = None,
    kpi_ids: list[UUID] | None = None, shift_ids: list[UUID] | None = None,
) -> list[_RawRow]:
    stmt = select(
        PerformanceRecord.plant_id, PerformanceRecord.shift_id, PerformanceRecord.foreman_id,
        PerformanceRecord.kpi_id, PerformanceRecord.performance_date,
        PerformanceRecord.numerator_value, PerformanceRecord.denominator_value,
    ).where(
        PerformanceRecord.performance_date >= month_start,
        PerformanceRecord.performance_date <= month_end,
        PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        PerformanceRecord.numerator_value.isnot(None),
        PerformanceRecord.denominator_value.isnot(None),
    )
    if plant_ids:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(plant_ids))
    if factory_ids:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(factory_ids))))
    if kpi_ids:
        stmt = stmt.where(PerformanceRecord.kpi_id.in_(kpi_ids))
    if shift_ids:
        stmt = stmt.where(PerformanceRecord.shift_id.in_(shift_ids))

    return [
        _RawRow(
            plant_id=r.plant_id, shift_id=r.shift_id, foreman_id=r.foreman_id, kpi_id=r.kpi_id,
            performance_date=r.performance_date,
            numerator=float(r.numerator_value), denominator=float(r.denominator_value),
        )
        for r in db.execute(stmt).all()
    ]


def _group_cells(rows: list[_RawRow]) -> dict[tuple[UUID, UUID, UUID], dict[UUID, list[_RawRow]]]:
    cells: dict[tuple[UUID, UUID, UUID], dict[UUID, list[_RawRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cells[(r.plant_id, r.shift_id, r.kpi_id)][r.foreman_id].append(r)
    return cells


@dataclass
class ForemanCellStat:
    foreman_id: UUID
    avg_actual: float
    record_count: int
    week_indices: list[int]


def _foreman_stat(foreman_id: UUID, records: list[_RawRow]) -> ForemanCellStat | None:
    denom_sum = sum(r.denominator for r in records)
    if denom_sum == 0:
        return None
    numer_sum = sum(r.numerator for r in records)
    weeks = sorted({_week_index(r.performance_date) for r in records})
    return ForemanCellStat(
        foreman_id=foreman_id, avg_actual=numer_sum / denom_sum * 100.0,
        record_count=len(records), week_indices=weeks,
    )


@dataclass
class PairComparison:
    better: ForemanCellStat
    worse: ForemanCellStat
    abs_diff: float
    pct_diff: float
    severity: str  # "medium" | "high"


def _extreme_pair(stats: list[ForemanCellStat], thresholds: ShiftAnomalyThresholds) -> tuple[ForemanCellStat, ForemanCellStat] | None:
    """Bir hücrede (tesis/vardiya/KPI) normalde tam olarak 2 formen bulunur (zon başına 2
    formen, haftalık dönüşümle her ikisi de her iki fiziksel vardiyada görünür). Ama personel
    değişikliği (işten çıkış/yeni işe alım) aynı ay içine denk gelirse 3+ farklı formen aynı
    hücrede kayıt bırakabilir — kayıt sayısına göre "ilk iki"yi almak (eski davranış) o durumda
    hangi ikisinin karşılaştırılacağını rastgele/ilgisiz bir kritere (hacim) bırakırdı ve asıl
    en büyük farkı (en iyi/en kötü performans) sessizce kaçırabilirdi. Bunun yerine, anlamlı
    sayıda kaydı olan (min_records_per_side) adaylar arasından değere göre en uç ikisi seçilir —
    yalnızca 2 aday varken (asıl/beklenen durum) davranış değişmez."""
    qualifying = [s for s in stats if s.record_count >= thresholds.min_records_per_side]
    if len(qualifying) < 2:
        return None
    best = max(qualifying, key=lambda s: s.avg_actual)
    worst = min(qualifying, key=lambda s: s.avg_actual)
    return best, worst


def _compare_pair(
    a: ForemanCellStat, b: ForemanCellStat, higher_is_better: bool, thresholds: ShiftAnomalyThresholds,
) -> PairComparison | None:
    if a.record_count < thresholds.min_records_per_side or b.record_count < thresholds.min_records_per_side:
        return None
    if higher_is_better:
        better, worse = (a, b) if a.avg_actual >= b.avg_actual else (b, a)
    else:
        better, worse = (a, b) if a.avg_actual <= b.avg_actual else (b, a)

    abs_diff = abs(better.avg_actual - worse.avg_actual)
    # Yüzdesel farkın tabanı olarak KÜÇÜK tarafın kendisi DEĞİL, iki değerin ORTALAMASI kullanılır.
    # Ağır Gitme/GSF/Iskarta/İnkita gibi "düşük değer iyi" KPI'larda ideal değer sıfıra çok yakındır
    # (ör. 0.01 vs 4.04) — küçük tarafı taban almak orada yüzdesel farkı binlerce yüzdeye
    # şişirerek kartı anlamsız kılar. Ortalamayı taban almak her iki yönde de (küçük/büyük fark)
    # simetrik ve sayısal olarak kararlıdır; yalnızca iki taraf da tam sıfırsa (zaten fark da
    # sıfır demektir) tanımsız kalır.
    base = (abs(a.avg_actual) + abs(b.avg_actual)) / 2.0
    if base == 0:
        return None
    pct_diff = abs_diff / base * 100.0

    if abs_diff < thresholds.min_abs_diff_points:
        return None
    if pct_diff >= thresholds.high_pct:
        severity = "high"
    elif pct_diff >= thresholds.medium_pct:
        severity = "medium"
    else:
        return None
    return PairComparison(better=better, worse=worse, abs_diff=abs_diff, pct_diff=pct_diff, severity=severity)


@dataclass
class ForemanNamedStat:
    id: UUID
    name: str
    employee_number: str
    avg_actual: float
    record_count: int
    week_count: int


def _named(stat: ForemanCellStat, foreman: Foreman) -> ForemanNamedStat:
    return ForemanNamedStat(
        id=stat.foreman_id, name=f"{foreman.first_name} {foreman.last_name}",
        employee_number=foreman.employee_number, avg_actual=stat.avg_actual,
        record_count=stat.record_count, week_count=len(stat.week_indices),
    )


def _build_title(worse_name: str, better_name: str, shift_name: str, kpi_name: str) -> str:
    return f"{worse_name} ile {better_name} arasında {shift_name} vardiyasında {kpi_name} farkı tespit edildi"


@dataclass
class ShiftAnomalyCard:
    plant_id: UUID
    plant_name: str
    plant_sequence: int
    factory_id: UUID
    factory_code: str
    shift_id: UUID
    shift_name: str
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    kpi_unit: str
    success_direction_higher: bool
    severity: str
    title: str
    better: ForemanNamedStat
    worse: ForemanNamedStat
    abs_diff: float
    pct_diff: float
    compared_weeks: int
    month_start: date
    month_end: date
    period_label: str


def build_cards(
    db: Session, month_start: date, month_end: date, *,
    plant_ids: list[UUID] | None = None, factory_ids: list[UUID] | None = None,
    kpi_ids: list[UUID] | None = None, shift_ids: list[UUID] | None = None,
    severity: str | None = None, thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> list[ShiftAnomalyCard]:
    rows = _fetch_raw_rows(
        db, month_start, month_end, plant_ids=plant_ids, factory_ids=factory_ids,
        kpi_ids=kpi_ids, shift_ids=shift_ids,
    )
    if not rows:
        return []
    cells = _group_cells(rows)

    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    foreman_ids = {r.foreman_id for r in rows}
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_(foreman_ids)))}

    period_label = month_label(month_end)
    cards: list[ShiftAnomalyCard] = []

    for (plant_id, shift_id, kpi_id), by_foreman in cells.items():
        kpi = kpis_by_id.get(kpi_id)
        plant = plants_by_id.get(plant_id)
        shift = shifts_by_id.get(shift_id)
        if kpi is None or plant is None or shift is None:
            continue

        stats = [s for s in (_foreman_stat(fid, recs) for fid, recs in by_foreman.items()) if s is not None]
        extreme = _extreme_pair(stats, thresholds)
        if extreme is None:
            continue
        comparison = _compare_pair(*extreme, kpi.success_direction_higher, thresholds)
        if comparison is None:
            continue
        if severity and comparison.severity != severity:
            continue

        better_f = foremen_by_id.get(comparison.better.foreman_id)
        worse_f = foremen_by_id.get(comparison.worse.foreman_id)
        if better_f is None or worse_f is None:
            continue
        factory = factories_by_id.get(plant.factory_id)
        better_named = _named(comparison.better, better_f)
        worse_named = _named(comparison.worse, worse_f)

        cards.append(
            ShiftAnomalyCard(
                plant_id=plant_id, plant_name=plant.name, plant_sequence=plant.sequence_number,
                factory_id=plant.factory_id, factory_code=factory.code if factory else "",
                shift_id=shift_id, shift_name=shift.name,
                kpi_id=kpi_id, kpi_code=kpi.code, kpi_name=kpi.name, kpi_unit=kpi.unit,
                success_direction_higher=kpi.success_direction_higher,
                severity=comparison.severity,
                title=_build_title(worse_named.name, better_named.name, shift.name, kpi.name),
                better=better_named, worse=worse_named,
                abs_diff=comparison.abs_diff, pct_diff=comparison.pct_diff,
                compared_weeks=len(set(comparison.better.week_indices) | set(comparison.worse.week_indices)),
                month_start=month_start, month_end=month_end, period_label=period_label,
            )
        )

    severity_order = {"high": 0, "medium": 1}
    cards.sort(key=lambda c: (severity_order[c.severity], -c.pct_diff))
    return cards


@dataclass
class ShiftAnomalySummary:
    month_start: date
    month_end: date
    period_label: str
    total: int
    high_count: int
    medium_count: int
    top_plant: tuple[UUID, str, int] | None
    top_kpi: tuple[UUID, str, int] | None
    max_pct_diff: float | None


def build_summary(cards: list[ShiftAnomalyCard], month_start: date, month_end: date) -> ShiftAnomalySummary:
    plant_counts = Counter((c.plant_id, c.plant_name) for c in cards)
    kpi_counts = Counter((c.kpi_id, c.kpi_name) for c in cards)
    top_plant = None
    if plant_counts:
        (pid, pname), count = plant_counts.most_common(1)[0]
        top_plant = (pid, pname, count)
    top_kpi = None
    if kpi_counts:
        (kid, kname), count = kpi_counts.most_common(1)[0]
        top_kpi = (kid, kname, count)

    return ShiftAnomalySummary(
        month_start=month_start, month_end=month_end, period_label=month_label(month_end),
        total=len(cards),
        high_count=sum(1 for c in cards if c.severity == "high"),
        medium_count=sum(1 for c in cards if c.severity == "medium"),
        top_plant=top_plant, top_kpi=top_kpi,
        max_pct_diff=max((c.pct_diff for c in cards), default=None),
    )


def _weekly_breakdown(records_by_foreman: dict[UUID, list[_RawRow]], foreman_ids: set[UUID]) -> list[dict]:
    relevant = {fid: recs for fid, recs in records_by_foreman.items() if fid in foreman_ids}
    all_weeks = sorted({_week_index(r.performance_date) for recs in relevant.values() for r in recs})
    ordinal = {w: i + 1 for i, w in enumerate(all_weeks)}

    out = []
    for foreman_id, recs in relevant.items():
        by_week: dict[int, list[_RawRow]] = defaultdict(list)
        for r in recs:
            by_week[_week_index(r.performance_date)].append(r)
        for w, week_records in by_week.items():
            denom = sum(x.denominator for x in week_records)
            numer = sum(x.numerator for x in week_records)
            out.append(
                {
                    "week_index": ordinal[w],
                    "week_label": f"Hafta {ordinal[w]}",
                    "foreman_id": foreman_id,
                    "avg_actual": (numer / denom * 100.0) if denom else 0.0,
                    "day_count": len(week_records),
                }
            )
    out.sort(key=lambda x: (x["week_index"], str(x["foreman_id"])))
    return out


def _is_consistent_pattern(weekly_points: list[dict], better_id: UUID, worse_id: UUID, higher_is_better: bool) -> bool:
    better_vals = [p["avg_actual"] for p in weekly_points if p["foreman_id"] == better_id]
    worse_vals = [p["avg_actual"] for p in weekly_points if p["foreman_id"] == worse_id]
    if not better_vals or not worse_vals:
        return False
    if higher_is_better:
        return min(better_vals) > max(worse_vals)
    return max(better_vals) < min(worse_vals)


@dataclass
class CrossKpiSignal:
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    pct_diff: float
    severity: str
    same_foreman_better: bool


def _cross_kpi_signals(
    by_kpi: dict[UUID, dict[UUID, list[_RawRow]]], current_kpi_id: UUID,
    better_id: UUID, worse_id: UUID, kpis_by_id: dict[UUID, Kpi], thresholds: ShiftAnomalyThresholds,
) -> list[CrossKpiSignal]:
    signals = []
    for kid, by_foreman in by_kpi.items():
        if kid == current_kpi_id:
            continue
        kpi = kpis_by_id.get(kid)
        if kpi is None:
            continue
        better_recs = by_foreman.get(better_id)
        worse_recs = by_foreman.get(worse_id)
        if not better_recs or not worse_recs:
            continue
        better_stat = _foreman_stat(better_id, better_recs)
        worse_stat = _foreman_stat(worse_id, worse_recs)
        if better_stat is None or worse_stat is None:
            continue
        comparison = _compare_pair(better_stat, worse_stat, kpi.success_direction_higher, thresholds)
        if comparison is None:
            continue
        signals.append(
            CrossKpiSignal(
                kpi_id=kid, kpi_code=kpi.code, kpi_name=kpi.name,
                pct_diff=comparison.pct_diff, severity=comparison.severity,
                same_foreman_better=comparison.better.foreman_id == better_id,
            )
        )
    signals.sort(key=lambda s: -s.pct_diff)
    return signals


def _build_pattern_commentary(
    *, kpi_name: str, worse_name: str, better_name: str, is_consistent: bool, has_enough_weeks: bool,
    cross_kpi_signals: list[CrossKpiSignal],
) -> str:
    if not has_enough_weeks:
        parts = [
            "Bu karşılaştırma sınırlı sayıda hafta verisine dayanmaktadır; farkın kalıcı bir örüntü mü "
            "yoksa tek seferlik bir sapma mı olduğu bu ayın verisiyle netleştirilemedi."
        ]
    elif is_consistent:
        parts = [
            f"Bu fark tek haftalık bir sapmadan ziyade ay içinde tekrarlayan bir örüntü göstermektedir. "
            f"Aynı tesiste aynı vardiyada {worse_name} ile {better_name} arasında {kpi_name} KPI'ında görülen "
            f"bu fark dönem boyunca sürmektedir; {worse_name} sonuçları daha düşük seyretmektedir."
        ]
    else:
        parts = [
            "Bu fark ay geneline yayılmış tutarlı bir örüntüden ziyade belirli haftalarda yoğunlaşan bir "
            "sapma olabilir; haftalık kırılıma bakılması önerilir."
        ]

    signal_names = [s.kpi_name for s in cross_kpi_signals]
    if signal_names:
        joined = ", ".join(signal_names)
        parts.append(f"Aynı formen çifti arasında benzer yönde bir fark {joined} KPI'ında da gözlemlenmektedir.")
    else:
        parts.append(f"Bu fark yalnızca {kpi_name} KPI'ında gözlemlenmektedir; diğer KPI'larda benzer bir sapma tespit edilmedi.")

    return " ".join(parts)


@dataclass
class ShiftAnomalyDetail(ShiftAnomalyCard):
    weekly_breakdown: list[dict] = field(default_factory=list)
    cross_kpi_signals: list[CrossKpiSignal] = field(default_factory=list)
    pattern_commentary: str = ""
    is_recurring_pattern: bool = False


def build_detail(
    db: Session, *, plant_id: UUID, shift_id: UUID, kpi_id: UUID, month_start: date, month_end: date,
    thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> ShiftAnomalyDetail | None:
    rows = _fetch_raw_rows(db, month_start, month_end, plant_ids=[plant_id], shift_ids=[shift_id])
    if not rows:
        return None

    by_kpi: dict[UUID, dict[UUID, list[_RawRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_kpi[r.kpi_id][r.foreman_id].append(r)
    if kpi_id not in by_kpi:
        return None

    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    kpi = kpis_by_id.get(kpi_id)
    if kpi is None:
        return None

    stats = [s for s in (_foreman_stat(fid, recs) for fid, recs in by_kpi[kpi_id].items()) if s is not None]
    extreme = _extreme_pair(stats, thresholds)
    if extreme is None:
        return None
    comparison = _compare_pair(*extreme, kpi.success_direction_higher, thresholds)
    if comparison is None:
        return None

    plant = db.get(Plant, plant_id)
    shift = db.get(Shift, shift_id)
    if plant is None or shift is None:
        return None
    factory = db.get(Factory, plant.factory_id)

    better_id, worse_id = comparison.better.foreman_id, comparison.worse.foreman_id
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_([better_id, worse_id])))}
    better_f, worse_f = foremen_by_id.get(better_id), foremen_by_id.get(worse_id)
    if better_f is None or worse_f is None:
        return None
    better_named = _named(comparison.better, better_f)
    worse_named = _named(comparison.worse, worse_f)
    period_label = month_label(month_end)

    weekly_points = _weekly_breakdown(by_kpi[kpi_id], {better_id, worse_id})
    has_enough_weeks = comparison.better.week_indices and comparison.worse.week_indices and (
        len(comparison.better.week_indices) >= 2 or len(comparison.worse.week_indices) >= 2
    )
    is_consistent = has_enough_weeks and _is_consistent_pattern(
        weekly_points, better_id, worse_id, kpi.success_direction_higher
    )
    signals = _cross_kpi_signals(by_kpi, kpi_id, better_id, worse_id, kpis_by_id, thresholds)
    commentary = _build_pattern_commentary(
        kpi_name=kpi.name, worse_name=worse_named.name, better_name=better_named.name,
        is_consistent=is_consistent, has_enough_weeks=bool(has_enough_weeks), cross_kpi_signals=signals,
    )

    return ShiftAnomalyDetail(
        plant_id=plant_id, plant_name=plant.name, plant_sequence=plant.sequence_number,
        factory_id=plant.factory_id, factory_code=factory.code if factory else "",
        shift_id=shift_id, shift_name=shift.name,
        kpi_id=kpi_id, kpi_code=kpi.code, kpi_name=kpi.name, kpi_unit=kpi.unit,
        success_direction_higher=kpi.success_direction_higher,
        severity=comparison.severity,
        title=_build_title(worse_named.name, better_named.name, shift.name, kpi.name),
        better=better_named, worse=worse_named,
        abs_diff=comparison.abs_diff, pct_diff=comparison.pct_diff,
        compared_weeks=len(set(comparison.better.week_indices) | set(comparison.worse.week_indices)),
        month_start=month_start, month_end=month_end, period_label=period_label,
        weekly_breakdown=weekly_points, cross_kpi_signals=signals,
        pattern_commentary=commentary, is_recurring_pattern=is_consistent,
    )
