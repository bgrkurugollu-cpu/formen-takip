from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.json_schema_utils import strict_json_schema

__all__ = ["AnalysisResult", "strict_json_schema"]

Confidence = Literal["low", "medium", "high"]
Priority = Literal["low", "medium", "high", "critical"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class SourceRef(BaseModel):

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
