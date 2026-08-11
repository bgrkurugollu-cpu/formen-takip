
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.enums import CalculationType, DataQualityStatus
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.organization import Plant
from app.models.performance import PerformanceRecord, PerformanceScore
from app.schemas.common import Filters
from app.services.kpi_engine import (
    MIN_COVERED_WEIGHT_RATIO,
    CalculationRuleParams,
    ScoreResult,
    calculate_custom_score,
    calculate_score,
    plan_achievement_params,
    score_heavy_weight_from_period_ratio,
    score_plan_achievement,
    score_plan_compliance,
    score_plan_compliance_from_period_deviation,
    weighted_geometric_score,
)

WEIGHT_TOLERANCE = 0.5


def _base_query() -> Select:
    return (
        select(PerformanceRecord, PerformanceScore)
        .join(PerformanceScore, PerformanceScore.performance_record_id == PerformanceRecord.id)
    )


def _apply_filters(stmt: Select, filters: Filters) -> Select:
    stmt = stmt.where(
        PerformanceRecord.performance_date >= filters.date_from,
        PerformanceRecord.performance_date <= filters.date_to,
    )
    if filters.plant_ids:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(filters.plant_ids))
    if filters.factory_ids:
        stmt = stmt.where(
            PerformanceRecord.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(filters.factory_ids)))
        )
    if filters.chief_ids:
        stmt = stmt.where(PerformanceRecord.chief_id.in_(filters.chief_ids))
    if filters.shift_ids:
        stmt = stmt.where(PerformanceRecord.shift_id.in_(filters.shift_ids))
    if filters.kpi_ids:
        stmt = stmt.where(PerformanceRecord.kpi_id.in_(filters.kpi_ids))
    if filters.foreman_ids:
        stmt = stmt.where(PerformanceRecord.foreman_id.in_(filters.foreman_ids))
    return stmt


def active_kpi_weight_sum(db: Session, filters: Filters | None = None) -> float:
    """Kapsanan ağırlık oranının (bkz. MIN_COVERED_WEIGHT_RATIO) payda tarafı. `filters.kpi_ids`
    doluysa (kullanıcı KPI filtresi seçtiyse) yalnızca seçili KPI'ların ağırlığı toplam sayılır —
    aksi halde "GSF" gibi tek bir KPI'ya filtrelemek, kapsanan ağırlığı hep %100'ün altında
    göstererek genel puanı hep 0'a düşürürdü (filtre dışı kalan KPI'lar zaten hiç veri döndürmez)."""
    stmt = select(func.sum(Kpi.weight)).where(Kpi.is_active.is_(True))
    if filters is not None and filters.kpi_ids:
        stmt = stmt.where(Kpi.id.in_(filters.kpi_ids))
    total = db.scalar(stmt)
    return float(total or 0)


def _active_kpis(db: Session) -> dict[UUID, Kpi]:
    return {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}


def _active_rules(db: Session) -> dict[UUID, KpiCalculationRule]:
    return {r.kpi_id: r for r in db.scalars(select(KpiCalculationRule).where(KpiCalculationRule.is_active.is_(True)))}


# ---------------------------------------------------------------------------------------------
# Dönemsel toplulaştırma (spec bölüm 11): önce ham pay/payda toplanır, ardından KPI'a özel formüle
# TEK SEFERDE gönderilir — günlük puanların ortalaması hiçbir yerde alınmaz. Her yardımcı fonksiyon
# `group_col=None` ile tek bir toplam satır (ör. tekil bir formen için KPI kartı), bir SQL ifadesiyle
# de (foreman_id, plant_id, date_trunc(...) vb.) grup başına satır döndürebilir — bu sayede
# plant/foreman/chief/shift/trend kırılımlarının hepsi aynı koddan beslenir.
# ---------------------------------------------------------------------------------------------


@dataclass
class _KpiPeriodStats:
    record_count: int
    numerator_sum: float
    denominator_sum: float
    expected_sum: float


def _kpi_period_stats(
    db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None
) -> dict:
    cols = [
        func.sum(PerformanceRecord.numerator_value).label("numerator_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
        func.sum(PerformanceRecord.denominator_value * PerformanceRecord.target_value / 100.0).label("expected_sum"),
        func.count().label("record_count"),
    ]
    if group_col is not None:
        cols = [group_col.label("key")] + cols
    stmt = select(*cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_col is not None:
        stmt = stmt.group_by(group_col)
    stmt = _apply_filters(stmt, filters)

    out = {}
    for row in db.execute(stmt):
        key = row.key if group_col is not None else None
        out[key] = _KpiPeriodStats(
            record_count=row.record_count,
            numerator_sum=float(row.numerator_sum or 0.0),
            denominator_sum=float(row.denominator_sum or 0.0),
            expected_sum=float(row.expected_sum or 0.0),
        )
    return out


def _agir_gitme_period_ratio(
    db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None
) -> dict:
    """Üretim ağırlıklı oran (spec bölüm 11.4): sum(denominator * abs(actual)/target) / sum(denominator).
    Payda (denominator_value) her zaman pozitiftir (standart gramaj x üretim miktarı) — işaretli
    numerator burada kullanılmaz, yalnızca oranın büyüklüğü ağırlıklandırılır."""
    ratio_expr = func.abs(PerformanceRecord.actual_value) / PerformanceRecord.target_value
    cols = [
        func.sum(PerformanceRecord.denominator_value * ratio_expr).label("weighted_ratio_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    if group_col is not None:
        cols = [group_col.label("key")] + cols
    stmt = select(*cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_col is not None:
        stmt = stmt.group_by(group_col)
    stmt = _apply_filters(stmt, filters)

    out = {}
    for row in db.execute(stmt):
        key = row.key if group_col is not None else None
        denom = float(row.denominator_sum or 0.0)
        out[key] = (float(row.weighted_ratio_sum or 0.0) / denom) if denom else 0.0
    return out


def _agir_gitme_avg_actual(
    db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None
) -> dict:
    """AGIR_GITME için EKRANDA gösterilen "gerçekleşen" — `_agir_gitme_period_ratio` ile AYNI
    temeli (|actual_value|, denominator ile ağırlıklı) paylaşır, yalnızca target'a bölünmeden
    doğrudan yüzde olarak döner. `numerator_sum/denominator_sum*100` (naif net ortalama)
    KULLANILMAZ: eşit büyüklükte +/- sapma günleri orada birbirini götürüp ekranda ~0 (mükemmel)
    gösterirken, gerçek puan (yukarıdaki fonksiyon → `score_heavy_weight_from_period_ratio`) her
    ikisini de kötü sayar — ekran ile puan farklı tanımlar kullanınca "sıfıra yakın ortalama, iki
    ayrı kötü sapma" tutarsızlığı doğardı (bkz. kpi_breakdown/foreman_kpi_values kullanımı)."""
    cols = [
        func.sum(PerformanceRecord.denominator_value * func.abs(PerformanceRecord.actual_value)).label("weighted_abs_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    if group_col is not None:
        cols = [group_col.label("key")] + cols
    stmt = select(*cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_col is not None:
        stmt = stmt.group_by(group_col)
    stmt = _apply_filters(stmt, filters)

    out = {}
    for row in db.execute(stmt):
        key = row.key if group_col is not None else None
        denom = float(row.denominator_sum or 0.0)
        out[key] = (float(row.weighted_abs_sum or 0.0) / denom) if denom else 0.0
    return out


def _plana_uyum_period_deviation(
    db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None
) -> dict:
    """Mutlak sapmaların toplamı (spec bölüm 11.5, birbirini götürmeyen): sum(abs(fiili - plan)) / sum(plan) * 100."""
    cols = [
        func.sum(func.abs(PerformanceRecord.numerator_value - PerformanceRecord.denominator_value)).label("abs_dev_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    if group_col is not None:
        cols = [group_col.label("key")] + cols
    stmt = select(*cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_col is not None:
        stmt = stmt.group_by(group_col)
    stmt = _apply_filters(stmt, filters)

    out = {}
    for row in db.execute(stmt):
        key = row.key if group_col is not None else None
        denom = float(row.denominator_sum or 0.0)
        out[key] = (float(row.abs_dev_sum or 0.0) / denom * 100.0) if denom else 0.0
    return out


def _plana_uyum_period_score_v3(
    db: Session, filters: Filters, group_col, kpi_id: UUID, params: dict, extra_where: list | None = None
) -> dict:
    """Plana Uyum v3 (asimetrik, formula_type="ASYMMETRIC_PLAN_ACHIEVEMENT") dönemsel puanı: ÖNCE
    her kayıt kendi (planlanan, fiili) çiftiyle AYRI AYRI puanlanır, SONRA planlanan miktarla
    ağırlıklandırılmış ortalaması alınır. Toplam fiili/toplam planlanandan TEK bir net sapma
    hesaplayıp bir kez puanlamak (matematiksel olarak buna eşdeğer: ağırlıklı sapma ortalaması =
    (Σaktüel-Σplanlanan)/Σplanlanan) tercih EDİLMEDİ — her performance_record bağımsız bir
    planlanan üretim koşusunu (tesis/hat/ürün/gün) temsil ediyor ve böyle bir netleme, bir
    hattaki fazla üretimin ilgisiz başka bir hattaki eksik üretimi birebir telafi etmesine izin
    verirdi. Kayıt bazlı puanlama + ağırlıklı ortalama, asimetrik cezayı (plan altı daha güçlü
    cezalandırılır) her bağımsız koşuda korur."""
    cols = [PerformanceRecord.numerator_value, PerformanceRecord.denominator_value]
    if group_col is not None:
        cols = [group_col.label("key")] + cols
    stmt = select(*cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        PerformanceRecord.numerator_value.isnot(None), PerformanceRecord.denominator_value.isnot(None),
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    stmt = _apply_filters(stmt, filters)

    plan_kwargs = plan_achievement_params(params)
    weighted_sum: dict[UUID | None, float] = defaultdict(float)
    weight_sum: dict[UUID | None, float] = defaultdict(float)
    for row in db.execute(stmt):
        key = row.key if group_col is not None else None
        planned = float(row.denominator_value)
        actual = float(row.numerator_value)
        if planned <= 0:
            continue
        result = score_plan_achievement(planned=planned, actual=actual, **plan_kwargs)
        weighted_sum[key] += result.capped_score * planned
        weight_sum[key] += planned

    return {key: total / weight_sum[key] for key, total in weighted_sum.items() if weight_sum[key] > 0}


def _kpi_period_scores(
    db: Session, filters: Filters, group_col, kpi: Kpi, rule: KpiCalculationRule | None, extra_where: list | None = None
) -> dict:
    """Bir KPI için grup başına (ScoreResult, _KpiPeriodStats) döner. Ağır Gitme/Plana Uyum kendi
    özel toplulaştırmalarını kullanır; GSF/Iskarta/İnkita (ve gelecekteki her ratio-vs-target
    custom KPI) ortak sum/sum-vs-ağırlıklı-hedef desenini paylaşır — hepsi aynı KPI'a özel
    formülleri (kpi_engine.py) çağırır, günlük skorların ortalaması hiçbir zaman alınmaz."""
    stats_by_key = _kpi_period_stats(db, filters, group_col, kpi.id, extra_where=extra_where)
    stats_by_key = {k: s for k, s in stats_by_key.items() if s.denominator_sum > 0}
    if not stats_by_key:
        return {}

    params: dict = (rule.parameters if rule else {}) or {}
    formula_type = params.get("formula_type")

    if kpi.code == "AGIR_GITME":
        ratio_by_key = _agir_gitme_period_ratio(db, filters, group_col, kpi.id, extra_where=extra_where)
        good = params.get("good_coefficient", 9.0)
        bad = params.get("bad_coefficient", 12.0)
        return {
            key: (score_heavy_weight_from_period_ratio(ratio_by_key.get(key, 0.0), good, bad), stats)
            for key, stats in stats_by_key.items()
        }

    if kpi.code == "PLANA_UYUM":
        if formula_type == "ASYMMETRIC_PLAN_ACHIEVEMENT":
            score_by_key = _plana_uyum_period_score_v3(db, filters, group_col, kpi.id, params, extra_where=extra_where)
            return {
                key: (ScoreResult(raw_score=score_by_key[key], capped_score=score_by_key[key]), stats)
                for key, stats in stats_by_key.items() if key in score_by_key
            }
        # v1/v2 (formula_type="PIECEWISE_LINEAR_LOGARITHMIC") — artık aktif kural olarak
        # kullanılmıyor (bkz. kpi_calculation_rules version geçmişi) ama tarihsel/downgrade
        # senaryosu için kasıtlı olarak kaldırılmadı.
        dev_by_key = _plana_uyum_period_deviation(db, filters, group_col, kpi.id, extra_where=extra_where)
        limit = params.get("normal_deviation_limit", 5.0)
        coef = params.get("excess_deviation_coefficient", 10.0)
        return {
            key: (score_plan_compliance_from_period_deviation(dev_by_key.get(key, 0.0), limit, coef), stats)
            for key, stats in stats_by_key.items()
        }

    result: dict = {}
    for key, stats in stats_by_key.items():
        period_actual = stats.numerator_sum / stats.denominator_sum * 100.0
        period_target = stats.expected_sum / stats.denominator_sum * 100.0
        result[key] = (calculate_custom_score(period_actual, period_target, formula_type, params), stats)
    return result


@dataclass
class GroupScore:
    key: UUID
    total_score: float
    is_reliable: bool
    record_count: int
    weight_covered: float


def _grouped_scores(
    db: Session, filters: Filters, group_col, total_active_weight: float, extra_where: list | None = None
) -> list[GroupScore]:
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)

    per_group: dict[UUID, list[tuple[float, float, int]]] = defaultdict(list)
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        for key, (score_result, stats) in _kpi_period_scores(db, filters, group_col, kpi, rule, extra_where).items():
            per_group[key].append((score_result.capped_score, float(kpi.weight), stats.record_count))

    results = []
    for key, items in per_group.items():
        components = [(score, weight) for score, weight, _ in items]
        covered_weight = sum(weight for _, weight, _ in items)
        record_count = sum(count for _, _, count in items)
        # Kapsanan ağırlık toplam ağırlığın yarısının altındaysa genel puan üretilmez (spec bölüm 10:
        # "eksik KPI sayısı izin verilen sınırı aşarsa genel puan üretme") — bkz. MIN_COVERED_WEIGHT_RATIO.
        insufficient = covered_weight < (total_active_weight * MIN_COVERED_WEIGHT_RATIO)
        is_reliable = (not insufficient) and covered_weight >= (total_active_weight - WEIGHT_TOLERANCE)
        total_score = 0.0 if insufficient else weighted_geometric_score(components)
        results.append(
            GroupScore(
                key=key, total_score=total_score, is_reliable=is_reliable,
                record_count=record_count, weight_covered=covered_weight,
            )
        )
    return results


def foreman_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.foreman_id, total_weight)


def plant_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.plant_id, total_weight)


def shift_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.shift_id, total_weight)


def chief_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.chief_id, total_weight)


@dataclass
class ChiefTeamScore:
    chief_id: UUID
    total_score: float
    foreman_count: int
    is_reliable: bool
    record_count: int
    foreman_scores: list[GroupScore]


def chief_team_scores(db: Session, filters: Filters) -> list[ChiefTeamScore]:
    """Şef ekip puanı: formen puanlarının ortalaması DEĞİL, şefin sorumluluğundaki tüm
    kayıtların toplam pay/paydasından doğrudan yeniden hesaplanan tek bir puan. Formen
    kırılımı (foreman_scores) ayrıca, her formenin kendi doğru puanıyla sağlanır."""
    chief_scores_by_id = {s.key: s for s in chief_scores(db, filters)}
    foreman_scores_by_id = {s.key: s for s in foreman_scores(db, filters)}

    membership_stmt = _apply_filters(
        select(PerformanceRecord.chief_id, PerformanceRecord.foreman_id).distinct(), filters
    )
    foremen_by_chief: dict[UUID, set[UUID]] = defaultdict(set)
    for chief_id, foreman_id in db.execute(membership_stmt):
        foremen_by_chief[chief_id].add(foreman_id)

    results = []
    for chief_id, foreman_ids in foremen_by_chief.items():
        chief_score = chief_scores_by_id.get(chief_id)
        foreman_list = [foreman_scores_by_id[fid] for fid in foreman_ids if fid in foreman_scores_by_id]
        results.append(
            ChiefTeamScore(
                chief_id=chief_id,
                total_score=chief_score.total_score if chief_score else 0.0,
                foreman_count=len(foreman_list),
                is_reliable=chief_score.is_reliable if chief_score else False,
                record_count=chief_score.record_count if chief_score else 0,
                foreman_scores=foreman_list,
            )
        )
    return results


@dataclass
class KpiSummary:
    kpi_id: UUID
    avg_capped_score: float
    avg_target: float | None
    avg_actual: float | None
    record_count: int


def kpi_summary(db: Session, filters: Filters) -> list[KpiSummary]:
    return [
        KpiSummary(
            kpi_id=row["kpi_id"], avg_capped_score=row["avg_capped_score"],
            avg_target=row["avg_target"], avg_actual=row["avg_actual"], record_count=row["record_count"],
        )
        for row in kpi_breakdown(db, filters)
    ]


@dataclass
class TrendPoint:
    bucket: date
    total_score: float
    is_reliable: bool


_GRANULARITY_TRUNC = {"day": "day", "week": "week", "month": "month", "quarter": "quarter", "year": "year"}


def trend(db: Session, filters: Filters, granularity: str = "day", foreman_id: UUID | None = None) -> list[TrendPoint]:
    trunc_unit = _GRANULARITY_TRUNC.get(granularity, "day")
    bucket_col = func.date_trunc(trunc_unit, PerformanceRecord.performance_date)
    total_weight = active_kpi_weight_sum(db, filters)
    extra_where = [PerformanceRecord.foreman_id == foreman_id] if foreman_id is not None else None

    grouped = _grouped_scores(db, filters, bucket_col, total_weight, extra_where=extra_where)
    grouped.sort(key=lambda g: g.key)
    return [TrendPoint(bucket=g.key.date(), total_score=g.total_score, is_reliable=g.is_reliable) for g in grouped]


def kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID | None = None) -> list[dict]:
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)
    extra_where = [PerformanceRecord.foreman_id == foreman_id] if foreman_id is not None else None

    results = []
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        scores = _kpi_period_scores(db, filters, None, kpi, rule, extra_where=extra_where)
        entry = scores.get(None)
        if entry is None:
            continue
        score_result, stats = entry
        weight = float(kpi.weight)
        avg_target = (stats.expected_sum / stats.denominator_sum * 100) if stats.denominator_sum else None
        if kpi.code == "AGIR_GITME":
            avg_actual = _agir_gitme_avg_actual(db, filters, None, kpi.id, extra_where=extra_where).get(None)
        else:
            avg_actual = (stats.numerator_sum / stats.denominator_sum * 100) if stats.denominator_sum else None
        results.append(
            {
                "kpi_id": kpi.id,
                "avg_target": avg_target,
                "avg_actual": avg_actual,
                "numerator_sum": stats.numerator_sum,
                "denominator_sum": stats.denominator_sum,
                "avg_raw_score": score_result.raw_score,
                "avg_capped_score": score_result.capped_score,
                "weight": weight,
                "contrib_sum": score_result.capped_score * (weight / 100.0),
                "record_count": stats.record_count,
                "calculation_version": rule.version if rule else None,
            }
        )
    return results


def foreman_kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID) -> list[dict]:
    return kpi_breakdown(db, filters, foreman_id=foreman_id)


@dataclass
class ForemanKpiValue:
    foreman_id: UUID
    avg_actual: float
    avg_target: float
    capped_score: float
    record_count: int


def _point_score(kpi: Kpi, rule: KpiCalculationRule | None, actual: float, target: float) -> float:
    """Bir (gerçekleşen, hedef) çiftine, o KPI'nın gerçek formülü DOĞRUDAN uygulanarak hesaplanan
    puan. Formen kırılımı grafiğinde tüm noktalar `reference_target`'a (tek yatay çizgi) göre
    puanlanır — her formen kendi hedefine göre puanlansaydı, çizgiye yakın duran bir nokta yine de
    kendi (farklı) hedefine göre kırmızı görünebilirdi (bkz. `foreman_kpi_values` docstring'i).

    Girdi `actual`, KPI'a göre değişir: Ağır Gitme için artık gerçek puanla (bkz.
    `_agir_gitme_avg_actual` → `score_heavy_weight_from_period_ratio`) AYNI mutlak/ağırlıklı
    temeli paylaşır. Plana Uyum'da ise hâlâ net (numerator_sum/denominator_sum) bir ortalamadır —
    gerçek puanı (`_plana_uyum_period_score_v3`) KAYIT BAZINDA ayrı ayrı puanlayıp SONRA ağırlıklı
    ortalamasını alır (asimetrik ceza her koşuda korunsun diye, bkz. o fonksiyonun docstring'i);
    bu, tek bir (actual, target) çiftine geri döndürülemeyen bir toplulaştırmadır, bu yüzden Plana
    Uyum noktalarının rengi gerçek dönem puanıyla hâlâ tam örtüşmeyebilir."""
    params: dict = (rule.parameters if rule else {}) or {}
    if kpi.calculation_type == CalculationType.CUSTOM_FORMULA:
        formula_type = params.get("formula_type")
        if formula_type == "ASYMMETRIC_PLAN_ACHIEVEMENT":
            result = score_plan_achievement(planned=target, actual=actual, **plan_achievement_params(params))
        elif formula_type == "PIECEWISE_LINEAR_LOGARITHMIC":
            result = score_plan_compliance(
                planned=target, actual=actual,
                normal_deviation_limit=params.get("normal_deviation_limit", 5.0),
                excess_deviation_coefficient=params.get("excess_deviation_coefficient", 10.0),
            )
        else:
            result = calculate_custom_score(actual, target, formula_type, params)
        return result.capped_score
    rule_params = CalculationRuleParams(
        calculation_type=kpi.calculation_type, min_score=float(kpi.min_score), max_score=float(kpi.max_score), **params
    )
    return calculate_score(actual, target, rule_params).capped_score


def foreman_kpi_values(db: Session, filters: Filters, kpi: Kpi, reference_target: float) -> list[ForemanKpiValue]:
    """Tek bir KPI için formen kırılımında (gerçekleşen, hedef, puan) — `kpi_breakdown`'ın
    formen bazında tersi: orada tek formen için tüm KPI'lar, burada tek KPI için tüm formenler.

    `reference_target`: puan (dolayısıyla renk/seviye), her formenin kendi hedefine göre DEĞİL,
    grafikte tek bir yatay çizgi olarak çizilen `reference_target`'a (şirket ortalama hedefi) göre
    hesaplanır — foremenler farklı tesislere atandığı için PLANT-seviyeli hedefler birbirinden
    belirgin şekilde ayrışabiliyor (bkz. kpi_targets); her nokta kendi hedefine göre puanlanırsa,
    ekranda görünen TEK ortalama çizgiye göre "yakın" duran bir nokta yine de kırmızı görünebilir.
    `avg_target` (formenin kendi ortalama hedefi) yine de bilgi amaçlı döndürülür."""
    rule = _active_rules(db).get(kpi.id)
    stats_by_foreman = _kpi_period_stats(db, filters, PerformanceRecord.foreman_id, kpi.id)
    # AGIR_GITME için net (işaretli) numerator_sum/denominator_sum yerine mutlak/ağırlıklı ortalama
    # kullanılır — aksi halde eşit büyüklükte +/- sapması olan bir formen ekranda ~hedef (yeşil)
    # görünürken gerçek puanı (aşağıdaki _point_score de dahil, aynı bu değeri kullanır) kötü olurdu.
    agir_gitme_actual_by_foreman = (
        _agir_gitme_avg_actual(db, filters, PerformanceRecord.foreman_id, kpi.id)
        if kpi.code == "AGIR_GITME" else {}
    )
    results = []
    for foreman_id, stats in stats_by_foreman.items():
        if stats.denominator_sum <= 0:
            continue
        if kpi.code == "AGIR_GITME":
            avg_actual = agir_gitme_actual_by_foreman.get(foreman_id, 0.0)
        else:
            avg_actual = stats.numerator_sum / stats.denominator_sum * 100
        avg_target = stats.expected_sum / stats.denominator_sum * 100
        results.append(
            ForemanKpiValue(
                foreman_id=foreman_id,
                avg_actual=avg_actual,
                avg_target=avg_target,
                capped_score=_point_score(kpi, rule, avg_actual, reference_target),
                record_count=stats.record_count,
            )
        )
    return results


def latest_foreman_kpi_record(db: Session, foreman_id: UUID, kpi_id: UUID):
    stmt = (
        _base_query()
        .where(
            PerformanceRecord.foreman_id == foreman_id,
            PerformanceRecord.kpi_id == kpi_id,
            PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        )
        .order_by(PerformanceRecord.performance_date.desc())
        .limit(1)
    )
    return db.execute(stmt).first()
