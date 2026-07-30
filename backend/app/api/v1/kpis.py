from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.schemas.common import Filters, common_filters
from app.services import analytics

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("")
def list_kpis(db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    kpis = list(db.scalars(select(Kpi).where(Kpi.is_active.is_(True)).order_by(Kpi.display_order)))
    return {
        "items": [
            {
                "id": str(k.id), "code": k.code, "name": k.name, "description": k.description,
                "unit": k.unit, "calculation_type": k.calculation_type.value, "weight": float(k.weight),
                "default_target_value": float(k.default_target_value), "is_critical": k.is_critical,
            }
            for k in kpis
        ]
    }


@router.get("/{kpi_id}")
def get_kpi(kpi_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise HTTPException(404, "KPI bulunamadı.")
    return {
        "id": str(kpi.id), "code": kpi.code, "name": kpi.name, "description": kpi.description,
        "unit": kpi.unit, "calculation_type": kpi.calculation_type.value,
        "success_direction_higher": kpi.success_direction_higher,
        "default_target_value": float(kpi.default_target_value),
        "min_score": float(kpi.min_score), "max_score": float(kpi.max_score),
        "weight": float(kpi.weight), "aggregation_method": kpi.aggregation_method.value,
        "is_critical": kpi.is_critical,
    }


@router.get("/{kpi_id}/analysis")
def kpi_analysis(
    kpi_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise HTTPException(404, "KPI bulunamadı.")
    filters.kpi_ids = [kpi_id]

    company_summary = analytics.kpi_summary(db, filters)
    company_avg = company_summary[0].avg_capped_score if company_summary else 0.0
    company_avg_target = company_summary[0].avg_target if company_summary else None
    company_avg_actual = company_summary[0].avg_actual if company_summary else None

    plant_scores = analytics.plant_scores(db, filters)
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    plant_scores.sort(key=lambda s: s.total_score, reverse=True)
    best_plants = plant_scores[:5]
    worst_plants = list(reversed(plant_scores[-5:])) if len(plant_scores) > 5 else []

    shift_scores = analytics.shift_scores(db, filters)
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    shift_scores.sort(key=lambda s: s.total_score, reverse=True)

    foreman_scores = analytics.foreman_scores(db, filters)
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}
    foreman_scores.sort(key=lambda s: s.total_score, reverse=True)
    best_foremen = foreman_scores[:5]
    worst_foremen = list(reversed(foreman_scores[-5:])) if len(foreman_scores) > 5 else []

    trend = analytics.trend(db, filters, "week")

    def plant_ref(gs):
        p = plants_by_id.get(gs.key)
        return {"id": str(gs.key), "name": p.name if p else None, "score": round(gs.total_score, 2)}

    def foreman_ref(gs):
        f = foremen_by_id.get(gs.key)
        return {
            "id": str(gs.key),
            "name": f"{f.first_name} {f.last_name}" if f else None,
            "score": round(gs.total_score, 2),
        }

    return {
        "kpi": {"id": str(kpi.id), "code": kpi.code, "name": kpi.name, "unit": kpi.unit},
        "company_avg_score": round(company_avg, 2),
        "company_avg_target": round(company_avg_target, 2) if company_avg_target is not None else None,
        "company_avg_actual": round(company_avg_actual, 2) if company_avg_actual is not None else None,
        "best_plants": [plant_ref(s) for s in best_plants],
        "worst_plants": [plant_ref(s) for s in worst_plants],
        "shift_comparison": [
            {"id": str(s.key), "name": shifts_by_id[s.key].name if s.key in shifts_by_id else None, "score": round(s.total_score, 2)}
            for s in shift_scores
        ],
        "best_foremen": [foreman_ref(s) for s in best_foremen],
        "worst_foremen": [foreman_ref(s) for s in worst_foremen],
        "trend": [
            {"date": p.bucket.isoformat(), "score": round(p.total_score, 2)}
            for p in trend
        ],
    }
