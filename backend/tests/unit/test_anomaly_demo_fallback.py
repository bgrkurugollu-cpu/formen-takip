import uuid
from datetime import date, datetime, timezone

import pytest

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType
from app.schemas.anomaly_analysis import AnalysisResult
from app.services.anomaly_demo_fallback import generate_demo_analysis


def _make_anomaly(anomaly_type: AnomalyType, severity: AnomalySeverity, ml_confidence: float) -> Anomaly:
    return Anomaly(
        code="ANM-2026-TEST",
        title="Test Tespiti",
        description="Test açıklaması.",
        anomaly_type=anomaly_type,
        severity=severity,
        status=AnomalyStatus.NEW,
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED,
        detected_at=datetime.now(timezone.utc),
        plant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        shift_id=None,
        kpi_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 10),
        observed_value=12.3,
        expected_value=5.0,
        unit="%",
        deviation_percent=146.0,
        ml_confidence=ml_confidence,
        affected_days=7,
        total_days=10,
        comparison={"plant_average": 5.0, "factory_average": 5.2},
        related_signals=[],
        evidence=[{"type": "metric", "label": "Gözlenen değer", "value": 12.3, "unit": "%"}],
        foreman_ids=[],
        data_quality_status="valid",
        data_quality_warnings=[],
    )


_PACKAGE = {
    "anomaly": {
        "plant_name": "12. Tesis",
        "shift_name": "3. Vardiya",
        "deviation_percent": 146.0,
        "evidence": [{"type": "metric", "label": "Gözlenen değer", "value": 12.3, "unit": "%"}],
    },
    "kpi_definition": {"name": "Iskarta Oranı"},
}


class TestGenerateDemoAnalysis:
    @pytest.mark.parametrize("anomaly_type", list(AnomalyType))
    def test_validates_against_schema_for_every_anomaly_type(self, anomaly_type):
        anomaly = _make_anomaly(anomaly_type, AnomalySeverity.HIGH, 0.9)
        raw = generate_demo_analysis(anomaly, _PACKAGE)
        result = AnalysisResult.model_validate(raw)
        assert result.requires_human_review is True
        assert 0.0 <= result.analysis_confidence <= 1.0

    def test_risk_level_matches_severity(self):
        anomaly = _make_anomaly(AnomalyType.CRITICAL_PRODUCTION_LOSS, AnomalySeverity.CRITICAL, 0.9)
        raw = generate_demo_analysis(anomaly, _PACKAGE)
        assert raw["risk_level"] == "critical"

    def test_does_not_blame_employees(self):
        anomaly = _make_anomaly(AnomalyType.FOREMAN_DEVIATION, AnomalySeverity.MEDIUM, 0.8)
        raw = generate_demo_analysis(anomaly, _PACKAGE)
        text = " ".join(c["cause"] for c in raw["possible_causes"]).lower()
        assert "formen" not in text and "çalışan" not in text

    def test_disclaimer_mentions_demo(self):
        anomaly = _make_anomaly(AnomalyType.RISING_TREND, AnomalySeverity.LOW, 0.75)
        raw = generate_demo_analysis(anomaly, _PACKAGE)
        assert "demo" in raw["disclaimer"].lower()
