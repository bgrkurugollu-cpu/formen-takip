
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus
from app.models.kpi import Kpi
from app.models.organization import Plant
from app.models.performance import PerformanceRecord, PerformanceScore
from app.schemas.common import Filters

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
    return stmt


@dataclass
class GroupScore:
    key: UUID
    total_score: float
    is_reliable: bool
    record_count: int
    weight_covered: float


def _grouped_scores(db: Session, filters: Filters, group_col, total_active_weight: float) -> list[GroupScore]:
    stmt = _apply_filters(_base_query(), filters).with_only_columns(
        group_col.label("key"),
        func.sum(PerformanceScore.weighted_contribution).label("contrib_sum"),
        func.sum(PerformanceScore.kpi_weight).label("weight_sum"),
        func.count().label("record_count"),
    ).group_by(group_col)

    results = []
    for row in db.execute(stmt):
        if row.weight_sum and row.weight_sum > 0:
            total = float(row.contrib_sum) / float(row.weight_sum) * 100
        else:
            total = 0.0
        is_reliable = row.weight_sum is not None and float(row.weight_sum) >= (total_active_weight - WEIGHT_TOLERANCE)
        results.append(
            GroupScore(
                key=row.key, total_score=total, is_reliable=is_reliable,
                record_count=row.record_count, weight_covered=float(row.weight_sum or 0),
            )
        )
    return results


def active_kpi_weight_sum(db: Session, as_of: date | None = None) -> float:
    stmt = select(func.sum(Kpi.weight)).where(Kpi.is_active.is_(True))
    total = db.scalar(stmt)
    return float(total or 0)


def foreman_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db)
    return _grouped_scores(db, filters, PerformanceRecord.foreman_id, total_weight)


def plant_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db)
    return _grouped_scores(db, filters, PerformanceRecord.plant_id, total_weight)


def shift_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db)
    return _grouped_scores(db, filters, PerformanceRecord.shift_id, total_weight)


def chief_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db)
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
    total_weight = active_kpi_weight_sum(db)
    stmt = _apply_filters(_base_query(), filters).with_only_columns(
        PerformanceRecord.chief_id.label("chief_id"),
        PerformanceRecord.foreman_id.label("foreman_id"),
        func.sum(PerformanceScore.weighted_contribution).label("contrib_sum"),
        func.sum(PerformanceScore.kpi_weight).label("weight_sum"),
        func.count().label("record_count"),
    ).group_by(PerformanceRecord.chief_id, PerformanceRecord.foreman_id)

    by_chief: dict[UUID, list[GroupScore]] = {}
    for row in db.execute(stmt):
        weight_sum = float(row.weight_sum or 0)
        total = float(row.contrib_sum) / weight_sum * 100 if weight_sum > 0 else 0.0
        by_chief.setdefault(row.chief_id, []).append(
            GroupScore(
                key=row.foreman_id,
                total_score=total,
                is_reliable=weight_sum >= (total_weight - WEIGHT_TOLERANCE),
                record_count=row.record_count,
                weight_covered=weight_sum,
            )
        )

    results = []
    for chief_id, scores in by_chief.items():
        results.append(
            ChiefTeamScore(
                chief_id=chief_id,
                total_score=sum(s.total_score for s in scores) / len(scores),
                foreman_count=len(scores),
                is_reliable=all(s.is_reliable for s in scores),
                record_count=sum(s.record_count for s in scores),
                foreman_scores=scores,
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
    stmt = _apply_filters(_base_query(), filters).with_only_columns(
        PerformanceRecord.kpi_id.label("key"),
        func.avg(PerformanceScore.capped_score).label("avg_score"),
        func.avg(PerformanceRecord.target_value).label("avg_target"),
        func.avg(PerformanceRecord.actual_value).label("avg_actual"),
        func.count().label("record_count"),
    ).where(PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE).group_by(PerformanceRecord.kpi_id)

    return [
        KpiSummary(
            kpi_id=row.key,
            avg_capped_score=float(row.avg_score or 0),
            avg_target=float(row.avg_target) if row.avg_target is not None else None,
            avg_actual=float(row.avg_actual) if row.avg_actual is not None else None,
            record_count=row.record_count,
        )
        for row in db.execute(stmt)
    ]


@dataclass
class TrendPoint:
    bucket: date
    total_score: float
    is_reliable: bool


_GRANULARITY_TRUNC = {"day": "day", "week": "week", "month": "month", "quarter": "quarter", "year": "year"}


def trend(db: Session, filters: Filters, granularity: str = "day", foreman_id: UUID | None = None) -> list[TrendPoint]:
    trunc_unit = _GRANULARITY_TRUNC.get(granularity, "day")
    bucket_col = func.date_trunc(trunc_unit, PerformanceRecord.performance_date).label("bucket")
    total_weight = active_kpi_weight_sum(db)

    stmt = _apply_filters(_base_query(), filters)
    if foreman_id is not None:
        stmt = stmt.where(PerformanceRecord.foreman_id == foreman_id)
    stmt = stmt.with_only_columns(
        bucket_col,
        func.sum(PerformanceScore.weighted_contribution).label("contrib_sum"),
        func.sum(PerformanceScore.kpi_weight).label("weight_sum"),
    ).group_by(bucket_col).order_by(bucket_col)

    points = []
    for row in db.execute(stmt):
        if row.weight_sum and row.weight_sum > 0:
            total = float(row.contrib_sum) / float(row.weight_sum) * 100
        else:
            total = 0.0
        is_reliable = row.weight_sum is not None and float(row.weight_sum) >= (total_weight - WEIGHT_TOLERANCE)
        points.append(TrendPoint(bucket=row.bucket.date(), total_score=total, is_reliable=is_reliable))
    return points


def kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID | None = None) -> list[dict]:
    stmt = _apply_filters(_base_query(), filters).where(
        PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
    )
    if foreman_id is not None:
        stmt = stmt.where(PerformanceRecord.foreman_id == foreman_id)
    stmt = stmt.with_only_columns(
        PerformanceRecord.kpi_id.label("kpi_id"),
        func.avg(PerformanceRecord.target_value).label("avg_target"),
        func.avg(PerformanceRecord.actual_value).label("avg_actual"),
        func.avg(PerformanceScore.raw_score).label("avg_raw_score"),
        func.avg(PerformanceScore.capped_score).label("avg_capped_score"),
        func.sum(PerformanceScore.weighted_contribution).label("contrib_sum"),
        func.max(PerformanceScore.kpi_weight).label("weight"),
        func.count().label("record_count"),
    ).group_by(PerformanceRecord.kpi_id)
    return [dict(row._mapping) for row in db.execute(stmt)]


def foreman_kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID) -> list[dict]:
    return kpi_breakdown(db, filters, foreman_id=foreman_id)


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
