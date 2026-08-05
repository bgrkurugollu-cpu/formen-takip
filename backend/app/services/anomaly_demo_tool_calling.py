"""Gerçek bir LLM API anahtarı olmadığında `tool_calling` modunun demo karşılığı: sabit bir
araç çağrı sırası gerçekten çalıştırılır (sentetik sağlayıcılara karşı), yalnızca LLM'in hangi
aracı ne zaman çağıracağına karar verme adımı atlanır; nihai analiz metni `anomaly_demo_fallback`
ile üretilir."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.schemas.anomaly_analysis import AnalysisResult
from app.services.anomaly_context import build_analysis_package
from app.services.anomaly_demo_fallback import generate_demo_analysis
from app.services.anomaly_orchestrator import OrchestratorOutcome, infer_record_count, new_code
from app.services.data_providers import get_data_providers
from app.services.tools.definitions import get_tool, parse_tool_arguments
from app.services.tools.errors import ToolError

DEMO_INVESTIGATION_PLAN = [
    "Vardiyalar arasındaki farkı doğrula",
    "KPI geçmişini kontrol et",
    "Duruş dağılımını incele",
    "Bakım sinyallerini kontrol et",
    "Ürün dağılımının etkisini değerlendir",
    "Benzer geçmiş vakaları araştır",
]

_DEMO_TOOL_SEQUENCE = [
    "compare_shifts", "get_kpi_history", "get_downtime_breakdown",
    "get_maintenance_signals", "get_product_mix", "find_similar_anomalies",
]


def _demo_args(tool_name: str, anomaly: Anomaly) -> dict:
    plant_id = str(anomaly.plant_id)
    shift = str(anomaly.shift_id) if anomaly.shift_id else None
    kpi = str(anomaly.kpi_id)
    start = anomaly.period_start.isoformat()
    end = anomaly.period_end.isoformat()

    if tool_name == "compare_shifts":
        return {"plant_id": plant_id, "kpi": kpi, "start_date": start, "end_date": end}
    if tool_name == "get_kpi_history":
        return {"plant_id": plant_id, "shift": shift, "kpi": kpi, "start_date": start, "end_date": end, "granularity": "daily"}
    if tool_name == "get_downtime_breakdown":
        return {"plant_id": plant_id, "shift": shift, "start_date": start, "end_date": end}
    if tool_name == "get_maintenance_signals":
        return {"plant_id": plant_id, "start_date": start, "end_date": end}
    if tool_name == "get_product_mix":
        return {"plant_id": plant_id, "shift": shift, "start_date": start, "end_date": end}
    if tool_name == "find_similar_anomalies":
        return {"anomaly_id": str(anomaly.id), "kpi": kpi, "anomaly_type": anomaly.anomaly_type.value, "limit": 3}
    raise ValueError(f"Bilinmeyen demo araç adı: {tool_name}")


def run_demo_tool_calling(db: Session, anomaly: Anomaly, analysis: AnomalyAnalysis) -> OrchestratorOutcome:
    providers = get_data_providers(db)
    successful_codes: list[str] = []
    total_records = 0

    for step, tool_name in enumerate(_DEMO_TOOL_SEQUENCE, start=1):
        tool = get_tool(tool_name)
        raw_args = _demo_args(tool_name, anomaly)
        started = datetime.now(timezone.utc)
        perf_start = time.monotonic()
        result: dict | None = None
        status = "success"
        error_code = error_message = None
        try:
            args = parse_tool_arguments(tool, raw_args)
            result = tool.handler(db, providers, args)
        except ToolError as exc:
            status, error_code, error_message = "error", exc.code.value, exc.message
        duration_ms = round((time.monotonic() - perf_start) * 1000)
        record_count = infer_record_count(result) if result else None
        if record_count:
            total_records += record_count

        code = new_code("TOOL")
        db.add(
            AnomalyToolCall(
                code=code, analysis_id=analysis.id, anomaly_id=anomaly.id, step_number=step,
                tool_name=tool_name, arguments=raw_args, status=status, result=result,
                record_count=record_count, error_code=error_code, error_message=error_message,
                started_at=started, completed_at=datetime.now(timezone.utc), duration_ms=duration_ms,
            )
        )
        db.commit()
        if status == "success":
            successful_codes.append(code)

    package = build_analysis_package(db, anomaly)
    base_result = generate_demo_analysis(anomaly, package)

    primary_ref = [{"tool_call_id": successful_codes[0], "tool_name": _DEMO_TOOL_SEQUENCE[0]}] if successful_codes else []
    for finding in base_result["verified_findings"]:
        finding.setdefault("finding_id", "")
        finding["source_refs"] = primary_ref
    for cause in base_result["possible_causes"]:
        cause["source_refs"] = primary_ref

    base_result["tools_used"] = [
        {"tool_name": _DEMO_TOOL_SEQUENCE[i], "tool_call_id": code, "purpose": DEMO_INVESTIGATION_PLAN[i]}
        for i, code in enumerate(successful_codes)
    ]
    base_result["data_scope"] = {
        "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
        "record_count": total_records, "data_quality_status": anomaly.data_quality_status,
    }
    base_result.setdefault("analysis_limitations", [])

    validated = AnalysisResult.model_validate(base_result).model_dump(mode="json")
    return OrchestratorOutcome(result_payload=validated, investigation_plan=DEMO_INVESTIGATION_PLAN)
