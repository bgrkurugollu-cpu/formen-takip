import uuid

from sqlalchemy import delete, select

from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnomalyAnalysisStatus


def _sample_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


def _fresh_anomaly(db_session) -> Anomaly:
    anomaly = _sample_anomaly(db_session)
    db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == anomaly.id))
    anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
    db_session.commit()
    return anomaly


class TestAnomalyList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/anomalies").status_code == 401

    def test_list_returns_at_least_20_items_with_expected_fields(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"page_size": 100}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 20
        item = body["items"][0]
        for key in (
            "id", "code", "title", "factory_code", "plant_name", "kpi_name", "anomaly_type",
            "detected_at", "period_start", "period_end", "deviation_percent", "ml_confidence",
            "severity", "status", "analysis_status",
        ):
            assert key in item

    def test_pagination(self, client, auth_headers):
        first = client.get("/api/v1/anomalies", params={"page": 1, "page_size": 5}, headers=auth_headers).json()
        second = client.get("/api/v1/anomalies", params={"page": 2, "page_size": 5}, headers=auth_headers).json()
        assert len(first["items"]) == 5
        assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})

    def test_filter_by_factory(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"factory": "K1", "page_size": 100}, headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        assert all(i["factory_code"] == "K1" for i in items)

    def test_filter_by_severity(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"severity": "critical", "page_size": 100}, headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        assert all(i["severity"] == "critical" for i in items)

    def test_search(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"search": "Tesis", "page_size": 100}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


class TestAnomalySummary:
    def test_summary_shape(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "total_active", "critical_count", "high_count", "pending_analysis_count",
            "opened_last_7_days", "resolved_count",
        ):
            assert key in body
            assert body[key] >= 0


class TestAnomalyDetail:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/anomalies/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_detail_shape(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "description", "observed_value", "expected_value", "comparison", "related_signals",
            "evidence", "daily_history", "kpi_definition", "latest_analysis", "analysis_history",
        ):
            assert key in body


class TestAnomalyInvestigation:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/anomalies/{uuid.uuid4()}/investigation", headers=auth_headers).status_code == 404

    def test_investigation_shape(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for key in (
            "responsible_foreman", "baseline_comparison", "related_kpi_changes",
            "downtime_breakdown", "impact", "similar_cases",
        ):
            assert key in body

        foreman = body["responsible_foreman"]
        assert "resolved" in foreman and "shift_specific" in foreman

        baseline = body["baseline_comparison"]
        assert "available" in baseline

        impact = body["impact"]
        assert "production_loss_note" in impact
        assert "cost_note" in impact

    def test_inkita_anomaly_includes_downtime_breakdown(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly)).all()
        inkita = next((a for a in anomaly if a.unit and _kpi_code(db_session, a) == "INKITA"), None)
        if inkita is None:
            return
        resp = client.get(f"/api/v1/anomalies/{inkita.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["downtime_breakdown"] is not None


def _kpi_code(db_session, anomaly: Anomaly) -> str | None:
    from app.models.kpi import Kpi

    kpi = db_session.get(Kpi, anomaly.kpi_id)
    return kpi.code if kpi else None


class TestAnomalyAnalysis:
    def test_analysis_before_any_run_returns_404(self, client, auth_headers, db_session):
        anomaly = _fresh_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers)
        assert resp.status_code == 404

    def test_analyze_uses_demo_fallback_when_llm_disabled(self, client, auth_headers, db_session):
        anomaly = _fresh_anomaly(db_session)
        resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["analysis_status"] == "completed"
        latest = body["latest_analysis"]
        assert latest["is_demo"] is True
        assert latest["status"] == "completed"
        result = latest["result"]
        assert result["requires_human_review"] is True
        assert 0.0 <= result["analysis_confidence"] <= 1.0
        assert result["executive_summary"]

        analysis_resp = client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers)
        assert analysis_resp.status_code == 200
        assert analysis_resp.json()["id"] == latest["id"]

    def test_double_submit_returns_409(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        anomaly.analysis_status = AnomalyAnalysisStatus.ANALYZING
        db_session.commit()
        resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
        assert resp.status_code == 409
        anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
        db_session.commit()


class TestAnomalyStatusUpdate:
    def test_update_status(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "in_review"}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_review"

    def test_invalid_status_value_returns_422(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "not-a-real-status"}, headers=auth_headers
        )
        assert resp.status_code == 422
