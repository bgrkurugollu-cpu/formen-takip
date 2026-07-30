from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.action_plan import ActionPlan
from app.models.enums import ActionPlanPriority, ActionPlanStatus
from app.models.foreman import Chief, Foreman
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.user import User
from app.schemas.action_plan import ActionPlanCreate, ActionPlanUpdate
from app.schemas.common import PageParams, page_params
from app.services.audit import record_audit

router = APIRouter(prefix="/action-plans", tags=["action-plans"])


def _ref(db: Session, model, id_: UUID | None, name_attr: str = "name") -> dict | None:
    if id_ is None:
        return None
    obj = db.get(model, id_)
    if obj is None:
        return None
    if model in (Foreman, Chief):
        return {"id": str(obj.id), "name": f"{obj.first_name} {obj.last_name}"}
    return {"id": str(obj.id), "name": getattr(obj, name_attr)}


def _to_dict(db: Session, plan: ActionPlan) -> dict:
    creator = db.get(User, plan.created_by_user_id)
    return {
        "id": str(plan.id),
        "title": plan.title,
        "description": plan.description,
        "plant": _ref(db, Plant, plan.plant_id),
        "chief": _ref(db, Chief, plan.chief_id),
        "shift": _ref(db, Shift, plan.shift_id),
        "foreman": _ref(db, Foreman, plan.foreman_id),
        "kpi": _ref(db, Kpi, plan.kpi_id),
        "owner": plan.owner,
        "created_by": creator.full_name if creator else None,
        "priority": plan.priority.value,
        "status": plan.status.value,
        "start_date": plan.start_date.isoformat(),
        "target_end_date": plan.target_end_date.isoformat(),
        "actual_end_date": plan.actual_end_date.isoformat() if plan.actual_end_date else None,
        "completion_percentage": plan.completion_percentage,
        "outcome_notes": plan.outcome_notes,
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }


@router.get("")
def list_action_plans(
    status_filter: ActionPlanStatus | None = Query(None, alias="status"),
    priority: ActionPlanPriority | None = Query(None),
    plant_id: UUID | None = Query(None),
    foreman_id: UUID | None = Query(None),
    kpi_id: UUID | None = Query(None),
    chief_id: UUID | None = Query(None),
    search: str | None = Query(None),
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = select(ActionPlan)
    if status_filter:
        query = query.where(ActionPlan.status == status_filter)
    if priority:
        query = query.where(ActionPlan.priority == priority)
    if plant_id:
        query = query.where(ActionPlan.plant_id == plant_id)
    if foreman_id:
        query = query.where(ActionPlan.foreman_id == foreman_id)
    if kpi_id:
        query = query.where(ActionPlan.kpi_id == kpi_id)
    if chief_id:
        query = query.where(ActionPlan.chief_id == chief_id)
    if search:
        query = query.where(ActionPlan.title.ilike(f"%{search}%"))

    all_plans = list(db.scalars(query.order_by(ActionPlan.created_at.desc())))
    total = len(all_plans)
    start = (page.page - 1) * page.page_size
    page_plans = all_plans[start : start + page.page_size]

    return {
        "items": [_to_dict(db, p) for p in page_plans],
        "total": total, "page": page.page, "page_size": page.page_size,
    }


@router.post("", status_code=201)
def create_action_plan(
    payload: ActionPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if payload.target_end_date < payload.start_date:
        raise HTTPException(400, "target_end_date, start_date'ten önce olamaz.")

    plan = ActionPlan(
        title=payload.title, description=payload.description,
        plant_id=payload.plant_id, chief_id=payload.chief_id,
        shift_id=payload.shift_id,
        foreman_id=payload.foreman_id, kpi_id=payload.kpi_id,
        owner=payload.owner, created_by_user_id=current_user.id,
        priority=payload.priority, status=payload.status,
        start_date=payload.start_date, target_end_date=payload.target_end_date,
        completion_percentage=payload.completion_percentage, outcome_notes=payload.outcome_notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    record_audit(
        db, current_user.id, "action_plan_created", entity="action_plan",
        new_value=payload.title, ip_address=request.client.host if request.client else None,
    )
    return _to_dict(db, plan)


@router.get("/{plan_id}")
def get_action_plan(plan_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    plan = db.get(ActionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "Aksiyon planı bulunamadı.")
    return _to_dict(db, plan)


@router.patch("/{plan_id}")
def update_action_plan(
    plan_id: UUID,
    payload: ActionPlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    plan = db.get(ActionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "Aksiyon planı bulunamadı.")

    changes: list[str] = []
    updates = payload.model_dump(exclude_unset=True)
    for field, new_value in updates.items():
        old_value = getattr(plan, field)
        old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
        new_str = new_value.value if hasattr(new_value, "value") else str(new_value)
        if old_str != new_str:
            changes.append(f"{field}: {old_str} -> {new_str}")
        setattr(plan, field, new_value)

    if plan.status == ActionPlanStatus.COMPLETED and plan.actual_end_date is None:
        from datetime import date as date_cls

        plan.actual_end_date = date_cls.today()

    db.commit()
    db.refresh(plan)

    if changes:
        record_audit(
            db, current_user.id, "action_plan_updated", entity="action_plan",
            old_value=None, new_value="; ".join(changes),
            ip_address=request.client.host if request.client else None,
        )
    return _to_dict(db, plan)
