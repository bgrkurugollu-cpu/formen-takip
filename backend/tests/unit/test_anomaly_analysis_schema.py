import pytest
from pydantic import ValidationError

from app.schemas.anomaly_analysis import AnalysisResult

_VALID = {
    "executive_summary": "Özet metin.",
    "verified_findings": [{"finding": "Bulgu", "evidence": "Kanıt"}],
    "possible_causes": [
        {
            "cause": "Neden",
            "confidence": "medium",
            "supporting_evidence": ["Destek"],
            "contradicting_evidence": [],
            "verification_required": "Saha kontrolü",
        }
    ],
    "recommended_investigations": [
        {"step": "Adım", "responsible_unit": "Üretim", "priority": "high", "expected_output": "Sonuç"}
    ],
    "immediate_actions": [
        {
            "action": "Aksiyon",
            "responsible_unit": "Üretim",
            "priority": "high",
            "timeframe": "1 gün",
            "expected_impact": "Etki",
            "requires_approval": True,
        }
    ],
    "medium_term_actions": [{"action": "Aksiyon", "responsible_unit": "Planlama", "expected_impact": "Etki"}],
    "missing_information": ["Eksik bilgi"],
    "risk_level": "high",
    "analysis_confidence": 0.82,
    "requires_human_review": True,
    "disclaimer": "Uyarı metni.",
}


class TestAnalysisResultSchema:
    def test_valid_payload_parses(self):
        result = AnalysisResult.model_validate(_VALID)
        assert result.risk_level == "high"

    def test_missing_required_field_raises(self):
        payload = dict(_VALID)
        del payload["executive_summary"]
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate(payload)

    def test_confidence_out_of_range_raises(self):
        payload = {**_VALID, "analysis_confidence": 1.5}
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate(payload)

    def test_invalid_enum_value_raises(self):
        payload = {**_VALID, "risk_level": "extreme"}
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate(payload)

    def test_invalid_confidence_literal_in_cause_raises(self):
        payload = dict(_VALID)
        payload["possible_causes"] = [{**_VALID["possible_causes"][0], "confidence": "very-high"}]
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate(payload)
