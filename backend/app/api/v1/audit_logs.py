from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import AuditLog, User
from app.schemas.common import PageParams, page_params

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs(
    action: str | None = Query(None),
    user_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.user_id)

    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if date_from:
        query = query.where(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
    if date_to:
        query = query.where(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))

    total = db.scalar(select(func.count()).select_from(query.subquery()))

    query = query.order_by(AuditLog.created_at.desc()).offset((page.page - 1) * page.page_size).limit(page.page_size)

    items = [
        {
            "id": str(log.id),
            "action": log.action,
            "entity": log.entity,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "user_name": full_name,
            "ip_address": log.ip_address,
            "success": log.success,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
        }
        for log, full_name in db.execute(query)
    ]

    return {"items": items, "total": total or 0, "page": page.page, "page_size": page.page_size}
