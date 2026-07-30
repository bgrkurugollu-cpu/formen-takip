from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.foreman import Foreman
from app.models.integration import DataQualityIssue
from app.models.kpi import Kpi
from app.models.organization import Plant
from app.models.performance import PerformanceRecord
from app.schemas.common import PageParams, page_params

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/issues")
def list_issues(
    issue_type: str | None = Query(None),
    plant_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = (
        select(
            DataQualityIssue.id, DataQualityIssue.issue_type, DataQualityIssue.description,
            DataQualityIssue.detected_at, DataQualityIssue.status,
            PerformanceRecord.performance_date, PerformanceRecord.source_system, PerformanceRecord.source_record_id,
            Plant.name.label("plant_name"), Foreman.first_name, Foreman.last_name, Kpi.name.label("kpi_name"),
        )
        .select_from(DataQualityIssue)
        .outerjoin(PerformanceRecord, PerformanceRecord.id == DataQualityIssue.performance_record_id)
        .outerjoin(Plant, Plant.id == PerformanceRecord.plant_id)
        .outerjoin(Foreman, Foreman.id == PerformanceRecord.foreman_id)
        .outerjoin(Kpi, Kpi.id == PerformanceRecord.kpi_id)
    )

    if issue_type:
        query = query.where(DataQualityIssue.issue_type == issue_type)
    if plant_id:
        query = query.where(PerformanceRecord.plant_id == plant_id)
    if date_from:
        query = query.where(PerformanceRecord.performance_date >= date_from)
    if date_to:
        query = query.where(PerformanceRecord.performance_date <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery()))

    query = query.order_by(DataQualityIssue.detected_at.desc())
    query = query.offset((page.page - 1) * page.page_size).limit(page.page_size)

    items = []
    for row in db.execute(query):
        items.append(
            {
                "id": str(row.id),
                "issue_type": row.issue_type.value,
                "description": row.description,
                "detected_at": row.detected_at.isoformat(),
                "status": row.status,
                "performance_date": row.performance_date.isoformat() if row.performance_date else None,
                "source_system": row.source_system.value if row.source_system else None,
                "source_record_id": row.source_record_id,
                "plant_name": row.plant_name,
                "foreman_name": f"{row.first_name} {row.last_name}" if row.first_name else None,
                "kpi_name": row.kpi_name,
            }
        )

    return {"items": items, "total": total or 0, "page": page.page, "page_size": page.page_size}


@router.get("/summary")
def data_quality_summary(db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    by_type = db.execute(
        select(DataQualityIssue.issue_type, func.count()).group_by(DataQualityIssue.issue_type)
    ).all()

    top_plants = db.execute(
        select(Plant.id, Plant.name, func.count().label("issue_count"))
        .select_from(DataQualityIssue)
        .join(PerformanceRecord, PerformanceRecord.id == DataQualityIssue.performance_record_id)
        .join(Plant, Plant.id == PerformanceRecord.plant_id)
        .group_by(Plant.id, Plant.name)
        .order_by(func.count().desc())
        .limit(10)
    ).all()

    return {
        "by_type": [{"issue_type": t.value, "count": c} for t, c in by_type],
        "top_plants": [{"plant_id": str(pid), "plant_name": name, "issue_count": cnt} for pid, name, cnt in top_plants],
    }
