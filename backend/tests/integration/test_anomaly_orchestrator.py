import json
import time
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus
from app.services import llm_service
from app.services.anomaly_analysis_service import run_analysis
from app.services.anomaly_orchestrator import AnomalyAnalysisOrchestrator
from app.services.tools.definitions import get_tool

_VALID_RESULT = {
    "executive_summary": "Test özeti.",
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


def _fresh_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    db_session.execute(delete(AnomalyToolCall).where(AnomalyToolCall.anomaly_id == anomaly.id))
    db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == anomaly.id))
    anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
    db_session.commit()
    return anomaly


def _enable_llm(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")


def _new_analysis(db_session, anomaly) -> AnomalyAnalysis:
    analysis = AnomalyAnalysis(
        code=f"ANA-TEST-{time.monotonic_ns()}", anomaly_id=anomaly.id, model="pending", is_demo=True,
        mode=AnalysisMode.TOOL_CALLING, status=AnomalyAnalysisStatus.QUEUED,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


def _assistant_tool_call(tool_name: str, args: dict, call_id: str = "call_1") -> dict:
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": call_id, "type": "function", "function": {"name": tool_name, "arguments": json.dumps(args)}}],
    }


def _assistant_text(text: str = "Yeterli veri topladım.") -> dict:
    return {"role": "assistant", "content": text}


def _final_message(payload: dict = _VALID_RESULT) -> dict:
    return {"role": "assistant", "content": json.dumps(payload)}


def _plan_message(steps: list[str] | None = None) -> dict:
    return {"role": "assistant", "content": json.dumps({"investigation_plan": steps or ["adım 1"]})}


def _queue_mock(monkeypatch, responses: list[dict]):
    it = iter(responses)

    def fake_call_chat(messages, tools=None, tool_choice=None, response_format=None):
        return next(it)

    monkeypatch.setattr(llm_service, "call_chat", fake_call_chat)


class TestSingleAndMultipleToolCalls:
    def test_single_tool_call_then_final_answer(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        args = {
            "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
            "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
        }
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("compare_shifts", args),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        outcome = orchestrator.run(analysis)

        assert outcome.result_payload is not None
        assert outcome.warnings == []
        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert len(calls) == 1
        assert calls[0].tool_name == "compare_shifts"
        assert calls[0].status == "success"
        assert calls[0].step_number == 1

    def test_multiple_tool_calls_across_turns(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        details_args = {"anomaly_id": anomaly.code}
        notes_args = {"plant_id": str(anomaly.plant_id), "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat()}
        _queue_mock(monkeypatch, [
            _plan_message(["adım 1", "adım 2"]),
            _assistant_tool_call("get_anomaly_details", details_args, "call_1"),
            _assistant_tool_call("get_shift_notes", notes_args, "call_2"),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        outcome = orchestrator.run(analysis)

        calls = list(
            db_session.scalars(
                select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id).order_by(AnomalyToolCall.step_number)
            )
        )
        assert [c.tool_name for c in calls] == ["get_anomaly_details", "get_shift_notes"]
        assert [c.step_number for c in calls] == [1, 2]
        assert outcome.result_payload is not None


class TestLimitsAndCaching:
    def test_max_tool_calls_limit_produces_warning(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_max_tool_calls", 1)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        args = {"anomaly_id": anomaly.code}
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("get_anomaly_details", args, "call_1"),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        outcome = orchestrator.run(analysis)

        assert outcome.warnings, "Sınır aşıldığında uyarı bildirilmeli."
        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert len(calls) == 1

    def test_repeated_identical_call_uses_cache(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        args = {"anomaly_id": anomaly.code}
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("get_anomaly_details", args, "call_1"),
            _assistant_tool_call("get_anomaly_details", args, "call_2"),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        orchestrator.run(analysis)

        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert len(calls) == 1, "Aynı araç aynı parametrelerle tekrar çağrıldığında yeni bir kayıt oluşturulmamalı."
        assert orchestrator._tool_call_count == 1


class TestToolErrorHandling:
    def test_unknown_tool_name_recorded_as_error_and_analysis_continues(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("delete_everything", {}, "call_1"),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        outcome = orchestrator.run(analysis)

        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert len(calls) == 1
        assert calls[0].status == "error"
        assert calls[0].error_code == "TOOL_NOT_FOUND"
        assert outcome.result_payload is not None, "Bir araç hata verse bile analiz tamamlanabilmeli."

    def test_invalid_arguments_recorded_as_validation_error(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        bad_args = {
            "plant_id": "NOT-A-REAL-PLANT", "kpi": str(anomaly.kpi_id),
            "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
        }
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("compare_shifts", bad_args, "call_1"),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        orchestrator.run(analysis)

        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert calls[0].status == "error"
        assert calls[0].error_code == "TOOL_VALIDATION_ERROR"

    def test_slow_tool_recorded_as_timeout(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_tool_timeout_seconds", 0)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        tool = get_tool("get_anomaly_details")
        original_handler = tool.handler

        def slow_handler(db, providers, args):
            time.sleep(0.05)
            return original_handler(db, providers, args)

        monkeypatch.setattr(tool, "handler", slow_handler)

        args = {"anomaly_id": anomaly.code}
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("get_anomaly_details", args, "call_1"),
            _assistant_text(),
            _final_message(),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        orchestrator.run(analysis)

        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert calls[0].status == "timeout"
        assert calls[0].error_code == "TOOL_TIMEOUT"


class TestSourceRefValidation:
    def test_fabricated_source_ref_is_stripped_from_final_result(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)
        analysis = _new_analysis(db_session, anomaly)

        args = {"anomaly_id": anomaly.code}
        result_with_fake_ref = {
            **_VALID_RESULT,
            "verified_findings": [
                {"finding": "x", "evidence": "y", "source_refs": [{"tool_call_id": "TOOL-FAKE-0000", "tool_name": "get_anomaly_details"}]}
            ],
        }
        _queue_mock(monkeypatch, [
            _plan_message(),
            _assistant_tool_call("get_anomaly_details", args, "call_1"),
            _assistant_text(),
            _final_message(result_with_fake_ref),
        ])

        orchestrator = AnomalyAnalysisOrchestrator(db_session, anomaly)
        outcome = orchestrator.run(analysis)

        assert outcome.result_payload["verified_findings"][0]["source_refs"] == []
        assert outcome.result_payload["analysis_limitations"]


class TestToolCallingUnsupportedFallback:
    def test_falls_back_to_single_context_when_tools_unsupported(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        anomaly = _fresh_anomaly(db_session)

        def fake_call_chat(messages, tools=None, tool_choice=None, response_format=None):
            if tools:
                raise llm_service.LLMToolCallingUnsupportedError("bu model tool calling desteklemiyor")
            return _plan_message()

        monkeypatch.setattr(llm_service, "call_chat", fake_call_chat)
        monkeypatch.setattr(llm_service, "call_llm", lambda *a, **k: dict(_VALID_RESULT))

        analysis = run_analysis(db_session, anomaly, mode=AnalysisMode.TOOL_CALLING)

        assert analysis.mode == AnalysisMode.SINGLE_CONTEXT
        # Düşüş gerçekleştiği için şeffaflık amacıyla "uyarılarla tamamlandı" işaretlenir.
        assert analysis.status == AnomalyAnalysisStatus.COMPLETED_WITH_WARNINGS
        assert analysis.result["executive_summary"] == _VALID_RESULT["executive_summary"]


class TestDemoToolCallingFlow:
    def test_demo_tool_calling_executes_real_tools(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)
        anomaly = _fresh_anomaly(db_session)

        analysis = run_analysis(db_session, anomaly, mode=AnalysisMode.TOOL_CALLING)

        assert analysis.mode == AnalysisMode.TOOL_CALLING
        assert analysis.is_demo is True
        assert analysis.status == AnomalyAnalysisStatus.COMPLETED
        assert analysis.model == "demo-tool-calling-v1"
        assert analysis.result["tools_used"]
        assert analysis.result["data_scope"] is not None

        calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert len(calls) == 6
        assert all(c.status == "success" for c in calls)


class TestSingleContextStillWorks:
    def test_explicit_single_context_mode(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)
        anomaly = _fresh_anomaly(db_session)

        analysis = run_analysis(db_session, anomaly, mode=AnalysisMode.SINGLE_CONTEXT)

        assert analysis.mode == AnalysisMode.SINGLE_CONTEXT
        assert analysis.is_demo is True
        assert analysis.status == AnomalyAnalysisStatus.COMPLETED
        assert analysis.model == "demo-fallback-v1"
        tool_calls = list(db_session.scalars(select(AnomalyToolCall).where(AnomalyToolCall.analysis_id == analysis.id)))
        assert tool_calls == [], "single_context modu hiçbir araç çağırmamalı."

    def test_default_mode_is_single_context_when_unspecified(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)
        monkeypatch.setattr(settings, "llm_analysis_mode", "single_context")
        anomaly = _fresh_anomaly(db_session)

        analysis = run_analysis(db_session, anomaly)

        assert analysis.mode == AnalysisMode.SINGLE_CONTEXT
