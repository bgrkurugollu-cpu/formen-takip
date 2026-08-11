from sqlalchemy import select

from app.core.config import get_settings
from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnomalyAnalysisStatus
from app.services import llm_service
from app.services.anomaly_analysis_service import run_analysis


def _sample_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
    db_session.commit()
    return anomaly


def _enable_llm(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")


_VALID_LLM_RESPONSE = {
    "executive_summary": "Gerçek LLM analiz özeti.",
    "verified_findings": [],
    "possible_causes": [],
    "recommended_investigations": [],
    "immediate_actions": [],
    "medium_term_actions": [],
    "missing_information": [],
    "risk_level": "medium",
    "analysis_confidence": 0.7,
    "requires_human_review": True,
    "disclaimer": "Test uyarısı.",
}


class TestRunAnalysisWithRealLlm:
    def test_wrapped_response_is_unwrapped_and_accepted(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        monkeypatch.setattr(llm_service, "call_llm", lambda *a, **k: {"analysis": dict(_VALID_LLM_RESPONSE)})

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.status == AnomalyAnalysisStatus.COMPLETED
        assert analysis.is_demo is False
        assert analysis.result["executive_summary"] == "Gerçek LLM analiz özeti."

    def test_successful_llm_analysis_is_persisted(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        monkeypatch.setattr(llm_service, "call_llm", lambda *a, **k: dict(_VALID_LLM_RESPONSE))

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.status == AnomalyAnalysisStatus.COMPLETED
        assert analysis.is_demo is False
        assert analysis.result["executive_summary"] == "Gerçek LLM analiz özeti."
        assert anomaly.analysis_status == AnomalyAnalysisStatus.COMPLETED

    def test_invalid_json_response_falls_back_to_failed_after_retry(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)

        def _raise(*a, **k):
            raise llm_service.LLMResponseInvalidError("bozuk JSON")

        monkeypatch.setattr(llm_service, "call_llm", _raise)

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.status == AnomalyAnalysisStatus.FAILED
        assert analysis.result is None
        assert analysis.error_message
        assert anomaly.analysis_status == AnomalyAnalysisStatus.FAILED

    def test_missing_required_field_falls_back_to_failed(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        incomplete = dict(_VALID_LLM_RESPONSE)
        del incomplete["executive_summary"]
        monkeypatch.setattr(llm_service, "call_llm", lambda *a, **k: dict(incomplete))

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.status == AnomalyAnalysisStatus.FAILED
        assert anomaly.analysis_status == AnomalyAnalysisStatus.FAILED

    def test_timeout_falls_back_to_failed(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)

        def _raise(*a, **k):
            raise llm_service.LLMTimeoutError("zaman aşımı")

        monkeypatch.setattr(llm_service, "call_llm", _raise)

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.status == AnomalyAnalysisStatus.FAILED
        assert "yeniden deneyebilirsiniz" in analysis.error_message.lower()

    def test_retry_succeeds_on_second_attempt(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        calls = {"count": 0}

        def _flaky(*a, **k):
            calls["count"] += 1
            if calls["count"] == 1:
                raise llm_service.LLMResponseInvalidError("ilk deneme bozuk")
            return dict(_VALID_LLM_RESPONSE)

        monkeypatch.setattr(llm_service, "call_llm", _flaky)

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert calls["count"] == 2
        assert analysis.status == AnomalyAnalysisStatus.COMPLETED


class TestRunAnalysisDemoFallback:
    def test_no_api_key_uses_demo_fallback(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)

        anomaly = _sample_anomaly(db_session)
        analysis = run_analysis(db_session, anomaly)

        assert analysis.is_demo is True
        assert analysis.status == AnomalyAnalysisStatus.COMPLETED
        assert analysis.model == "demo-fallback-v1"


class TestAnalysisHistory:
    def test_reanalysis_creates_new_history_row_without_deleting_previous(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)

        anomaly = _sample_anomaly(db_session)
        first = run_analysis(db_session, anomaly)
        anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
        db_session.commit()
        second = run_analysis(db_session, anomaly)

        assert first.id != second.id
        history = list(db_session.scalars(select(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == anomaly.id)))
        assert len(history) >= 2
