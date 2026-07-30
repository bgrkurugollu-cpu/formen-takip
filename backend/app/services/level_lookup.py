from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kpi import PerformanceLevelRule
from app.services.kpi_engine import PerformanceLevel


def get_performance_levels(db: Session) -> list[PerformanceLevel]:
    rows = db.scalars(select(PerformanceLevelRule).order_by(PerformanceLevelRule.sort_order))
    return [
        PerformanceLevel(
            name=r.name, min_score=float(r.min_score), max_score=float(r.max_score),
            description=r.description, color=r.color, icon=r.icon, sort_order=r.sort_order,
        )
        for r in rows
    ]


def level_to_dict(level: PerformanceLevel) -> dict:
    return {
        "name": level.name, "description": level.description,
        "color": level.color, "icon": level.icon,
    }
