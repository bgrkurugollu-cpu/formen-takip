from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.json_schema_utils import strict_json_schema

__all__ = ["AnalysisResult", "strict_json_schema"]

Confidence = Literal["low", "medium", "high"]
Priority = Literal["low", "medium", "high", "critical"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class SourceRef(BaseModel):
    """Bir bulgunun/nedenin hangi tool çağrısından geldiğini gösterir (yalnızca tool_calling
    modunda doldurulur). Backend, bu referansların gerçekten yapılmış tool çağrılarına ait
    olduğunu doğrular — LLM'nin uydurduğu tool_call_id'ler kabul edilmez
    (bkz. anomaly_orchestrator.py::_sanitize_source_refs)."""

    tool_call_id: str
    tool_name: str


class VerifiedFinding(BaseModel):
    finding_id: str = ""
    finding: str
    evidence: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class PossibleCause(BaseModel):
    cause: str
    confidence: Confidence
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    verification_required: str


class RecommendedInvestigation(BaseModel):
    step: str
    responsible_unit: str
    priority: Priority
    expected_output: str


class ImmediateAction(BaseModel):
    action: str
    responsible_unit: str
    priority: Priority
    timeframe: str
    expected_impact: str
    requires_approval: bool = True


class MediumTermAction(BaseModel):
    action: str
    responsible_unit: str
    expected_impact: str


class ToolUsedRef(BaseModel):
    tool_name: str
    tool_call_id: str
    purpose: str


class DataScope(BaseModel):
    start_date: str
    end_date: str
    record_count: int
    data_quality_status: str


class AnalysisResult(BaseModel):
    """LLM'den (veya demo modda sabit üreticiden) beklenen yapılandırılmış çıktı şeması.

    Backend, hem gerçek LLM cevabını hem de demo fallback cevabını bu şemadan geçirerek
    doğrular — geçersiz JSON veya eksik alan durumunda ValidationError fırlatılır ve
    çağıran servis (bkz. anomaly_analysis_service.py) bunu kontrollü bir hataya çevirir.

    `tools_used`, `data_scope`, `analysis_limitations` yalnızca `tool_calling` modunda
    doldurulur; `single_context` modunda (tool kullanılmadığında) boş/None bırakılabilir — bu
    yüzden hepsi varsayılan değerlidir ve Pydantic doğrulamasında zorunlu değildir (yalnızca
    LLM'e gönderilen strict JSON şemasında, OpenAI'ın kısıtı gereği tüm alanlar zorunlu görünür)."""

    executive_summary: str
    verified_findings: list[VerifiedFinding] = Field(default_factory=list)
    possible_causes: list[PossibleCause] = Field(default_factory=list)
    recommended_investigations: list[RecommendedInvestigation] = Field(default_factory=list)
    immediate_actions: list[ImmediateAction] = Field(default_factory=list)
    medium_term_actions: list[MediumTermAction] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    analysis_confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = True
    tools_used: list[ToolUsedRef] = Field(default_factory=list)
    data_scope: DataScope | None = None
    analysis_limitations: list[str] = Field(default_factory=list)
    disclaimer: str
