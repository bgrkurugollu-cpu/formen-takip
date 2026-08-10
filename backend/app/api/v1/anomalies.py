from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.models.user import User
from app.schemas.common import PageParams, page_params
from app.services.anomaly_analysis_service import AnalysisInProgressError, run_analysis
from app.services.anomaly_context import build_analysis_package
from app.services.anomaly_kpi_defs import (
    ANALYSIS_STATUS_LABELS,
    ANOMALY_TYPE_LABELS,
    KPI_DEFINITIONS,
    SEVERITY_LABELS,
    STATUS_LABELS,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/anomalies", tags=["anomalies"])
analyses_router = APIRouter(prefix="/analyses", tags=["analyses"])

_COMPLETED_STATUSES = {AnomalyAnalysisStatus.COMPLETED, AnomalyAnalysisStatus.COMPLETED_WITH_WARNINGS}
_TOOL_LABELS = {
    "get_anomaly_details": "Tespit Detayları", "get_kpi_history": "KPI Geçmişi",
    "compare_shifts": "Vardiya Performansı Karşılaştırması", "compare_plants": "Tesisler Arası Karşılaştırma",
    "get_related_kpis": "İlişkili KPI Değişimleri", "get_downtime_breakdown": "Duruş Nedenleri İncelemesi",
    "get_maintenance_signals": "Bakım ve Arıza Sinyalleri", "get_product_mix": "Ürün Dağılımı İncelemesi",
    "get_changeover_records": "Ürün Değişim Kayıtları", "get_shift_notes": "Vardiya Notları İncelemesi",
    "find_similar_anomalies": "Benzer Geçmiş Tespitler",
}


class AnomalyStatusUpdate(BaseModel):
    status: AnomalyStatus


class AnalyzeRequest(BaseModel):
    mode: AnalysisMode | None = None
    force_refresh: bool = False


def _num(value) -> float | None:
    return float(value) if value is not None else None


def _plant_factory_refs(db: Session, plant_id: UUID) -> tuple[Plant | None, Factory | None]:
    plant = db.get(Plant, plant_id)
    factory = db.get(Factory, plant.factory_id) if plant else None
    return plant, factory


def _to_summary_dict(db: Session, a: Anomaly) -> dict:
    plant, factory = _plant_factory_refs(db, a.plant_id)
    shift = db.get(Shift, a.shift_id) if a.shift_id else None
    kpi = db.get(Kpi, a.kpi_id)

    return {
        "id": str(a.id),
        "code": a.code,
        "title": a.title,
        "factory_code": factory.code if factory else None,
        "factory_name": factory.name if factory else None,
        "plant_id": str(a.plant_id),
        "plant_name": plant.name if plant else None,
        "shift_id": str(a.shift_id) if a.shift_id else None,
        "shift_name": shift.name if shift else None,
        "kpi_id": str(a.kpi_id),
        "kpi_code": kpi.code if kpi else None,
        "kpi_name": kpi.name if kpi else None,
        "anomaly_type": a.anomaly_type.value,
        "anomaly_type_label": ANOMALY_TYPE_LABELS[a.anomaly_type],
        "detected_at": a.detected_at.isoformat(),
        "period_start": a.period_start.isoformat(),
        "period_end": a.period_end.isoformat(),
        "deviation_percent": _num(a.deviation_percent),
        "ml_confidence": _num(a.ml_confidence),
        "severity": a.severity.value,
        "severity_label": SEVERITY_LABELS[a.severity.value],
        "status": a.status.value,
        "status_label": STATUS_LABELS[a.status.value],
        "analysis_status": a.analysis_status.value,
        "analysis_status_label": ANALYSIS_STATUS_LABELS[a.analysis_status.value],
    }


def _analysis_to_dict(db: Session, an: AnomalyAnalysis) -> dict:
    tool_call_count = db.scalar(
        select(func.count()).select_from(AnomalyToolCall).where(AnomalyToolCall.analysis_id == an.id)
    )
    return {
        "id": str(an.id),
        "code": an.code,
        "mode": an.mode.value,
        "status": an.status.value,
        "status_label": ANALYSIS_STATUS_LABELS.get(an.status.value, an.status.value),
        "is_demo": an.is_demo,
        "model": an.model,
        "result": an.result,
        "investigation_plan": an.investigation_plan,
        "tool_call_count": tool_call_count or 0,
        "error_code": an.error_code,
        "error_message": an.error_message,
        "started_at": an.started_at.isoformat(),
        "completed_at": an.completed_at.isoformat() if an.completed_at else None,
    }


def _to_detail_dict(db: Session, a: Anomaly) -> dict:
    base = _to_summary_dict(db, a)
    kpi = db.get(Kpi, a.kpi_id)
    kpi_def = KPI_DEFINITIONS.get(kpi.code, {}) if kpi else {}

    foreman_codes = []
    for fid in a.foreman_ids:
        foreman = db.get(Foreman, fid)
        if foreman is not None:
            foreman_codes.append(foreman.employee_number)

    package = build_analysis_package(db, a)

    latest_analysis = db.scalar(
        select(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == a.id).order_by(AnomalyAnalysis.started_at.desc())
    )
    analysis_history = list(
        db.scalars(
            select(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == a.id).order_by(AnomalyAnalysis.started_at.desc())
        )
    )

    base.update(
        {
            "description": a.description,
            "observed_value": _num(a.observed_value),
            "expected_value": _num(a.expected_value),
            "unit": a.unit,
            "affected_days": a.affected_days,
            "total_days": a.total_days,
            "comparison": a.comparison,
            "related_signals": a.related_signals,
            "evidence": a.evidence,
            "foreman_codes": foreman_codes,
            "data_quality_status": a.data_quality_status,
            "data_quality_warnings": a.data_quality_warnings,
            "daily_history": package["context"]["daily_history"],
            "kpi_definition": {
                "name": kpi.name if kpi else None,
                "description": kpi_def.get("description"),
                "desired_direction": kpi_def.get("desired_direction"),
                "warning_threshold": kpi_def.get("warning_threshold"),
                "critical_threshold": kpi_def.get("critical_threshold"),
            },
            "latest_analysis": _analysis_to_dict(db, latest_analysis) if latest_analysis else None,
            "analysis_history": [_analysis_to_dict(db, x) for x in analysis_history],
        }
    )
    return base


@router.get("")
def list_anomalies(
    factory: str | None = Query(None, description="K1 veya K2"),
    plant_id: UUID | None = Query(None),
    shift_id: UUID | None = Query(None),
    kpi_id: UUID | None = Query(None),
    severity: AnomalySeverity | None = Query(None),
    status_filter: AnomalyStatus | None = Query(None, alias="status"),
    analysis_status: AnomalyAnalysisStatus | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = select(Anomaly)

    if factory:
        query = query.where(Anomaly.plant_id.in_(select(Plant.id).join(Factory).where(Factory.code == factory)))
    if plant_id:
        query = query.where(Anomaly.plant_id == plant_id)
    if shift_id:
        query = query.where(Anomaly.shift_id == shift_id)
    if kpi_id:
        query = query.where(Anomaly.kpi_id == kpi_id)
    if severity:
        query = query.where(Anomaly.severity == severity)
    if status_filter:
        query = query.where(Anomaly.status == status_filter)
    if analysis_status:
        query = query.where(Anomaly.analysis_status == analysis_status)
    if start_date:
        query = query.where(Anomaly.detected_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
    if end_date:
        query = query.where(
            Anomaly.detected_at < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    if search:
        like = f"%{search}%"
        query = query.where(or_(Anomaly.title.ilike(like), Anomaly.description.ilike(like)))

    total = db.scalar(select(func.count()).select_from(query.subquery()))

    # `id` ikincil sıralama anahtarı olarak eklenir: `detected_at` eşit olan satırlarda tek
    # başına DESC sıralama sayfa 1/sayfa 2 arasında (ayrı SQL sorguları olduğundan) tutarsız
    # sıra üretebilir — aynı satır iki sayfada birden görünebilir ya da hiç görünmeyebilir.
    query = (
        query.order_by(Anomaly.detected_at.desc(), Anomaly.id)
        .offset((page.page - 1) * page.page_size).limit(page.page_size)
    )
    page_items = list(db.scalars(query))

    return {
        "items": [_to_summary_dict(db, a) for a in page_items],
        "total": total or 0,
        "page": page.page,
        "page_size": page.page_size,
    }


@router.get("/summary")
def anomalies_summary(db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    anomalies = list(db.scalars(select(Anomaly)))
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    active_statuses = {AnomalyStatus.NEW, AnomalyStatus.IN_REVIEW, AnomalyStatus.ACTION_PENDING}
    return {
        "total_active": sum(1 for a in anomalies if a.status in active_statuses),
        "critical_count": sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL),
        "high_count": sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH),
        "pending_analysis_count": sum(
            1 for a in anomalies if a.analysis_status == AnomalyAnalysisStatus.NOT_ANALYZED
        ),
        "opened_last_7_days": sum(1 for a in anomalies if a.detected_at >= week_ago),
        "resolved_count": sum(
            1 for a in anomalies if a.status in (AnomalyStatus.RESOLVED, AnomalyStatus.CLOSED)
        ),
    }


@router.get("/{anomaly_id}")
def get_anomaly(anomaly_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, "Tespit bulunamadı.")
    return _to_detail_dict(db, anomaly)


@router.get("/{anomaly_id}/analysis")
def get_latest_analysis(anomaly_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, "Tespit bulunamadı.")
    latest = db.scalar(
        select(AnomalyAnalysis)
        .where(AnomalyAnalysis.anomaly_id == anomaly_id)
        .order_by(AnomalyAnalysis.started_at.desc())
    )
    if latest is None:
        raise HTTPException(404, "Bu tespit için henüz analiz yapılmamış.")
    return _analysis_to_dict(db, latest)


def _run_analysis_endpoint(
    anomaly_id: UUID, payload: AnalyzeRequest, request: Request, db: Session, current_user: User,
    action: str, force: bool,
) -> dict:
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, "Tespit bulunamadı.")

    if not force and not payload.force_refresh and anomaly.analysis_status in _COMPLETED_STATUSES:
        existing = db.scalar(
            select(AnomalyAnalysis)
            .where(AnomalyAnalysis.anomaly_id == anomaly_id)
            .order_by(AnomalyAnalysis.started_at.desc())
        )
        if existing is not None:
            return _to_detail_dict(db, anomaly)

    try:
        analysis = run_analysis(db, anomaly, mode=payload.mode)
    except AnalysisInProgressError as exc:
        raise HTTPException(409, str(exc)) from exc

    record_audit(
        db, current_user.id, action, entity="anomaly",
        new_value=f"{anomaly.code}: {analysis.status.value}",
        ip_address=request.client.host if request.client else None,
    )
    return _to_detail_dict(db, anomaly)


@router.post("/{anomaly_id}/analyze")
def analyze_anomaly(
    anomaly_id: UUID, request: Request, payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
) -> dict:
    return _run_analysis_endpoint(anomaly_id, payload or AnalyzeRequest(), request, db, current_user, "anomaly_analyzed", force=False)


@router.post("/{anomaly_id}/reanalyze")
def reanalyze_anomaly(
    anomaly_id: UUID, request: Request, payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
) -> dict:
    return _run_analysis_endpoint(anomaly_id, payload or AnalyzeRequest(), request, db, current_user, "anomaly_reanalyzed", force=True)


@router.patch("/{anomaly_id}/status")
def update_anomaly_status(
    anomaly_id: UUID,
    payload: AnomalyStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, "Tespit bulunamadı.")

    old_status = anomaly.status.value
    anomaly.status = payload.status
    db.commit()
    db.refresh(anomaly)

    if old_status != payload.status.value:
        record_audit(
            db, current_user.id, "anomaly_status_updated", entity="anomaly",
            old_value=old_status, new_value=payload.status.value,
            ip_address=request.client.host if request.client else None,
        )
    return _to_detail_dict(db, anomaly)


def _tool_call_to_dict(tc: AnomalyToolCall) -> dict:
    return {
        "id": str(tc.id),
        "code": tc.code,
        "step_number": tc.step_number,
        "tool_name": tc.tool_name,
        "tool_label": _TOOL_LABELS.get(tc.tool_name, tc.tool_name),
        "arguments": tc.arguments,
        "status": tc.status,
        "result": tc.result,
        "record_count": tc.record_count,
        "error_code": tc.error_code,
        "error_message": tc.error_message,
        "started_at": tc.started_at.isoformat(),
        "completed_at": tc.completed_at.isoformat() if tc.completed_at else None,
        "duration_ms": tc.duration_ms,
    }


@analyses_router.get("/{analysis_id}")
def get_analysis(analysis_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    analysis = db.get(AnomalyAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Analiz bulunamadı.")
    return _analysis_to_dict(db, analysis)


@analyses_router.get("/{analysis_id}/tool-calls")
def list_tool_calls(analysis_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    analysis = db.get(AnomalyAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Analiz bulunamadı.")
    calls = list(
        db.scalars(
            select(AnomalyToolCall)
            .where(AnomalyToolCall.analysis_id == analysis_id)
            .order_by(AnomalyToolCall.step_number)
        )
    )
    return {"items": [_tool_call_to_dict(c) for c in calls], "total": len(calls)}
