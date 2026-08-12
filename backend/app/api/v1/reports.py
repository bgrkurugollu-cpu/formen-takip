from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ReportFormat, ReportStatus, ReportType
from app.models.report import ReportExport
from app.models.user import User
from app.schemas.common import Filters, PageParams, page_params
from app.services.audit import record_audit
from app.services.reporting import (
    REPORT_TITLES,
    build_filters_summary,
    build_report_rows,
    render_csv,
    render_pdf,
    render_xlsx,
)

router = APIRouter(prefix="/reports", tags=["reports"])

_CONTENT_TYPES = {
    ReportFormat.CSV: "text/csv",
    ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ReportFormat.PDF: "application/pdf",
}


class ReportGenerateRequest(BaseModel):
    report_type: ReportType
    format: ReportFormat
    date_from: date | None = None
    date_to: date | None = None
    plant_ids: list[UUID] | None = None
    factory_ids: list[UUID] | None = None
    chief_ids: list[UUID] | None = None
    shift_ids: list[UUID] | None = None
    kpi_ids: list[UUID] | None = None


def _filters_from_request(payload: ReportGenerateRequest) -> Filters:
    resolved_to = payload.date_to or date.today()
    resolved_from = payload.date_from or (resolved_to - timedelta(days=30))
    if resolved_from > resolved_to:
        resolved_from, resolved_to = resolved_to, resolved_from
    return Filters(
        date_from=resolved_from, date_to=resolved_to,
        plant_ids=payload.plant_ids, factory_ids=payload.factory_ids,
        chief_ids=payload.chief_ids, shift_ids=payload.shift_ids, kpi_ids=payload.kpi_ids,
    )


@router.post("/generate", status_code=201)
def generate_report(
    payload: ReportGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    filters = _filters_from_request(payload)
    headers, rows = build_report_rows(db, payload.report_type, filters)
    title = REPORT_TITLES[payload.report_type]

    if payload.format == ReportFormat.CSV:
        content = render_csv(headers, rows)
        ext = "csv"
    elif payload.format == ReportFormat.XLSX:
        content = render_xlsx(title, headers, rows)
        ext = "xlsx"
    else:
        content = render_pdf(title, build_filters_summary(db, filters), headers, rows)
        ext = "pdf"

    file_name = f"{payload.report_type.value}_{filters.date_from}_{filters.date_to}.{ext}"

    export = ReportExport(
        report_type=payload.report_type, format=payload.format,
        filters_json=payload.model_dump(mode="json", exclude={"report_type", "format"}),
        requested_by_user_id=current_user.id,
        file_name=file_name, file_content=content, row_count=len(rows),
        status=ReportStatus.COMPLETED, completed_at=datetime.now(timezone.utc),
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    record_audit(
        db, current_user.id, "report_generated", entity="report_export",
        new_value=file_name, ip_address=request.client.host if request.client else None,
    )

    return {
        "id": str(export.id), "file_name": file_name, "report_type": payload.report_type.value,
        "format": payload.format.value, "row_count": len(rows), "created_at": export.created_at.isoformat(),
    }


@router.get("")
def list_reports(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    total = db.scalar(select(func.count()).select_from(ReportExport))
    exports = list(db.scalars(
        select(ReportExport).order_by(ReportExport.created_at.desc())
        .offset((page.page - 1) * page.page_size).limit(page.page_size)
    ))

    requester_ids = {e.requested_by_user_id for e in exports}
    requesters_by_id = (
        {u.id: u for u in db.scalars(select(User).where(User.id.in_(requester_ids)))} if requester_ids else {}
    )

    items = [
        {
            "id": str(e.id), "file_name": e.file_name, "report_type": e.report_type.value,
            "format": e.format.value, "row_count": e.row_count, "status": e.status.value,
            "requested_by": requesters_by_id[e.requested_by_user_id].full_name
            if e.requested_by_user_id in requesters_by_id else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]
    return {"items": items, "total": total or 0, "page": page.page, "page_size": page.page_size}


@router.get("/{report_id}/download")
def download_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    export = db.get(ReportExport, report_id)
    if export is None:
        raise HTTPException(404, "Rapor bulunamadı.")

    record_audit(
        db, current_user.id, "report_downloaded", entity="report_export",
        new_value=export.file_name, ip_address=request.client.host if request.client else None,
    )

    return Response(
        content=export.file_content,
        media_type=_CONTENT_TYPES[export.format],
        headers={"Content-Disposition": f'attachment; filename="{export.file_name}"'},
    )
