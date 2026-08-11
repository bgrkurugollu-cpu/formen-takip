from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import DataQualityStatus
from app.models.foreman import Foreman
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters, common_filters
from app.services import analytics
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    levels = get_performance_levels(db)

    total_plants = db.scalar(select(func.count()).select_from(Plant))
    active_plants = db.scalar(select(func.count()).select_from(Plant).where(Plant.is_active.is_(True)))

    f_scores = analytics.foreman_scores(db, filters)
    total_active_foremen = len(f_scores)
    company_avg = sum(s.total_score for s in f_scores) / len(f_scores) if f_scores else 0.0

    above_target = sum(1 for s in f_scores if s.total_score >= 100)
    below_target = sum(1 for s in f_scores if s.total_score < 100)
    critical = sum(1 for s in f_scores if resolve_performance_level(s.total_score, levels).name == "Kritik")
    excellent = sum(1 for s in f_scores if resolve_performance_level(s.total_score, levels).name == "Mükemmel")

    p_scores = analytics.plant_scores(db, filters)
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    best_plant = max(p_scores, key=lambda s: s.total_score, default=None)
    worst_plant = min(p_scores, key=lambda s: s.total_score, default=None)

    sh_scores = analytics.shift_scores(db, filters)
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    best_shift = max(sh_scores, key=lambda s: s.total_score, default=None)
    worst_shift = min(sh_scores, key=lambda s: s.total_score, default=None)

    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}
    best_foreman = max(f_scores, key=lambda s: s.total_score, default=None)

    kpi_sum = analytics.kpi_summary(db, filters)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}
    weakest_kpi = min(kpi_sum, key=lambda s: s.avg_capped_score, default=None)

    missing_plants = db.scalar(
        select(func.count(func.distinct(PerformanceRecord.plant_id))).where(
            PerformanceRecord.performance_date >= filters.date_from,
            PerformanceRecord.performance_date <= filters.date_to,
            PerformanceRecord.data_quality_status.in_(
                [DataQualityStatus.MISSING, DataQualityStatus.NEEDS_SOURCE_CORRECTION]
            ),
        )
    )

    last_run = db.scalar(select(IntegrationRun).order_by(IntegrationRun.finished_at.desc()).limit(1))

    def plant_ref(gs):
        if gs is None:
            return None
        p = plants_by_id.get(gs.key)
        return {"id": str(gs.key), "name": p.name if p else None, "code": p.code if p else None, "score": round(gs.total_score, 2)}

    def shift_ref(gs):
        if gs is None:
            return None
        s = shifts_by_id.get(gs.key)
        return {"id": str(gs.key), "name": s.name if s else None, "score": round(gs.total_score, 2)}

    def foreman_ref(gs):
        if gs is None:
            return None
        f = foremen_by_id.get(gs.key)
        return {
            "id": str(gs.key),
            "name": f"{f.first_name} {f.last_name}" if f else None,
            "employee_number": f.employee_number if f else None,
            "score": round(gs.total_score, 2),
        }

    return {
        "total_plants": total_plants,
        "active_plants": active_plants,
        "total_active_foremen": total_active_foremen,
        "avg_company_score": round(company_avg, 2),
        "foremen_above_target": above_target,
        "foremen_below_target": below_target,
        "foremen_critical": critical,
        "foremen_excellent": excellent,
        "best_plant": plant_ref(best_plant),
        "worst_plant": plant_ref(worst_plant),
        "best_shift": shift_ref(best_shift),
        "worst_shift": shift_ref(worst_shift),
        "best_foreman": foreman_ref(best_foreman),
        "weakest_kpi": (
            {"id": str(weakest_kpi.kpi_id), "name": kpis_by_id[weakest_kpi.kpi_id].name, "avg_score": round(weakest_kpi.avg_capped_score, 2)}
            if weakest_kpi else None
        ),
        "plants_with_missing_data": missing_plants or 0,
        "last_sync_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
        "data_source": "SYNTHETIC",
    }


@router.get("/trend")
def trend(
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    points = analytics.trend(db, filters, granularity)
    return {
        "granularity": granularity,
        "points": [
            {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
            for p in points
        ],
    }


@router.get("/kpi-summary")
def kpi_summary(filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    items = analytics.kpi_summary(db, filters)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}
    return {
        "items": [
            {
                "kpi_id": str(i.kpi_id),
                "code": kpis_by_id[i.kpi_id].code if i.kpi_id in kpis_by_id else None,
                "name": kpis_by_id[i.kpi_id].name if i.kpi_id in kpis_by_id else None,
                "unit": kpis_by_id[i.kpi_id].unit if i.kpi_id in kpis_by_id else None,
                "avg_score": round(i.avg_capped_score, 2),
                "avg_target": round(i.avg_target, 2) if i.avg_target is not None else None,
                "avg_actual": round(i.avg_actual, 2) if i.avg_actual is not None else None,
                "record_count": i.record_count,
            }
            for i in items
        ]
    }


@router.get("/plant-ranking")
def plant_ranking(
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=50),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    levels = get_performance_levels(db)
    scores = analytics.plant_scores(db, filters)
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    scores.sort(key=lambda s: s.total_score, reverse=(order == "desc"))
    scores = scores[:limit]
    return {
        "items": [
            {
                "plant_id": str(s.key),
                "code": plants_by_id[s.key].code if s.key in plants_by_id else None,
                "name": plants_by_id[s.key].name if s.key in plants_by_id else None,
                "total_score": round(s.total_score, 2),
                "is_reliable": s.is_reliable,
                "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
            for s in scores
        ]
    }


@router.get("/shift-comparison")
def shift_comparison(filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    levels = get_performance_levels(db)
    scores = analytics.shift_scores(db, filters)
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    scores.sort(key=lambda s: shifts_by_id[s.key].sequence if s.key in shifts_by_id else 0)
    return {
        "items": [
            {
                "shift_id": str(s.key),
                "code": shifts_by_id[s.key].code if s.key in shifts_by_id else None,
                "name": shifts_by_id[s.key].name if s.key in shifts_by_id else None,
                "total_score": round(s.total_score, 2),
                "record_count": s.record_count,
                "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
            for s in scores
        ]
    }


@router.get("/foreman-ranking")
def foreman_ranking(
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(10, ge=1, le=100),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    levels = get_performance_levels(db)
    scores = analytics.foreman_scores(db, filters)
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}
    scores.sort(key=lambda s: s.total_score, reverse=(order == "desc"))
    scores = scores[:limit]
    return {
        "items": [
            {
                "foreman_id": str(s.key),
                "employee_number": foremen_by_id[s.key].employee_number if s.key in foremen_by_id else None,
                "full_name": (
                    f"{foremen_by_id[s.key].first_name} {foremen_by_id[s.key].last_name}" if s.key in foremen_by_id else None
                ),
                "total_score": round(s.total_score, 2),
                "is_reliable": s.is_reliable,
                "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
            for s in scores
        ]
    }


@router.get("/foreman-trend-ranking")
def foreman_trend_ranking(
    direction: str = Query("improving", pattern="^(improving|declining)$"),
    limit: int = Query(5, ge=1, le=100),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """Seçili dönem ile ondan hemen önceki eşit uzunluktaki dönem arasındaki skor
    değişimine göre formenleri sıralar. Yalnızca her iki dönemde de veri bulunan
    formenler dahil edilir — aksi halde yeni işe başlayan bir formen anlamsız
    şekilde en büyük "gelişim" olarak görünür."""
    levels = get_performance_levels(db)

    period_days = (filters.date_to - filters.date_from).days + 1
    previous_filters = replace(
        filters,
        date_from=filters.date_from - timedelta(days=period_days),
        date_to=filters.date_from - timedelta(days=1),
    )

    current_scores = {s.key: s for s in analytics.foreman_scores(db, filters)}
    previous_scores = {s.key: s for s in analytics.foreman_scores(db, previous_filters)}
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}

    deltas = [
        (foreman_id, current, previous_scores[foreman_id])
        for foreman_id, current in current_scores.items()
        if foreman_id in previous_scores
    ]
    deltas.sort(
        key=lambda item: item[1].total_score - item[2].total_score,
        reverse=(direction == "improving"),
    )
    deltas = deltas[:limit]

    return {
        "items": [
            {
                "foreman_id": str(foreman_id),
                "employee_number": foremen_by_id[foreman_id].employee_number if foreman_id in foremen_by_id else None,
                "full_name": (
                    f"{foremen_by_id[foreman_id].first_name} {foremen_by_id[foreman_id].last_name}"
                    if foreman_id in foremen_by_id else None
                ),
                "total_score": round(current.total_score, 2),
                "previous_score": round(previous.total_score, 2),
                "delta": round(current.total_score - previous.total_score, 2),
                "is_reliable": current.is_reliable and previous.is_reliable,
                "level": level_to_dict(resolve_performance_level(current.total_score, levels)),
            }
            for foreman_id, current, previous in deltas
        ]
    }


@router.get("/performance-distribution")
def performance_distribution(filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    levels = get_performance_levels(db)
    scores = analytics.foreman_scores(db, filters)
    counts = {lv.name: 0 for lv in levels}
    for s in scores:
        level = resolve_performance_level(s.total_score, levels)
        counts[level.name] += 1
    return {
        "items": [
            {**level_to_dict(lv), "count": counts[lv.name]}
            for lv in sorted(levels, key=lambda lv: lv.sort_order)
        ]
    }
