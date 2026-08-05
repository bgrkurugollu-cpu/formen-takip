from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.integration import IntegrationRun
from app.models.organization import Plant
from app.models.user import User
from app.schemas.common import PageParams, page_params
from app.services.audit import record_audit
from app.services.ingestion import run_ingestion
from app.services.providers.synthetic_provider import SyntheticDataProvider

router = APIRouter(prefix="/integration", tags=["integration"])

MAX_RESYNC_DAYS = 31


class ResyncRequest(BaseModel):
    date_from: date
    date_to: date
    plant_codes: list[str] | None = None


def _run_to_dict(run: IntegrationRun) -> dict:
    return {
        "id": str(run.id),
        "source_system": run.source_system.value,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status.value,
        "processed_count": run.processed_count,
        "success_count": run.success_count,
        "error_count": run.error_count,
        "skipped_count": run.skipped_count,
        "duration_seconds": (
            (run.finished_at - run.started_at).total_seconds() if run.finished_at else None
        ),
    }


@router.get("/runs")
def list_runs(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    total = db.scalar(select(func.count()).select_from(IntegrationRun))
    runs = db.scalars(
        select(IntegrationRun)
        .order_by(IntegrationRun.started_at.desc())
        .offset((page.page - 1) * page.page_size)
        .limit(page.page_size)
    )
    return {
        "items": [_run_to_dict(r) for r in runs],
        "total": total or 0, "page": page.page, "page_size": page.page_size,
    }


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    run = db.get(IntegrationRun, run_id)
    if run is None:
        raise HTTPException(404, "Senkronizasyon koşusu bulunamadı.")
    return _run_to_dict(run)


@router.post("/resync")
def trigger_resync(
    payload: ResyncRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if payload.date_from > payload.date_to:
        raise HTTPException(400, "date_from, date_to'dan sonra olamaz.")
    if (payload.date_to - payload.date_from).days > MAX_RESYNC_DAYS:
        raise HTTPException(400, f"Yeniden senkronizasyon aralığı en fazla {MAX_RESYNC_DAYS} gün olabilir.")

    plant_codes = payload.plant_codes
    if not plant_codes:
        plant_codes = list(db.scalars(select(Plant.code)))

    provider = SyntheticDataProvider(db)
    run = run_ingestion(db, provider, payload.date_from, payload.date_to, plant_codes=plant_codes)

    record_audit(
        db, current_user.id, "resync_triggered", entity="integration_run",
        new_value=f"{payload.date_from} -> {payload.date_to}, {len(plant_codes)} tesis",
        ip_address=request.client.host if request.client else None,
    )

    return _run_to_dict(run)
