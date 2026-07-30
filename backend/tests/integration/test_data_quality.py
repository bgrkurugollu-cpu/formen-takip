from app.db.session import SessionLocal
from app.services.ingestion import backfill_data_quality_issues


class TestDataQualityEndpoints:
    def test_issues_requires_auth(self, client):
        resp = client.get("/api/v1/data-quality/issues")
        assert resp.status_code == 401

    def test_list_issues_returns_shape(self, client, auth_headers):
        resp = client.get("/api/v1/data-quality/issues", params={"page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body and "total" in body
        if body["items"]:
            item = body["items"][0]
            for field in ["issue_type", "description", "detected_at", "status"]:
                assert field in item

    def test_filter_by_issue_type(self, client, auth_headers):
        resp = client.get("/api/v1/data-quality/issues", params={"issue_type": "missing", "page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["issue_type"] == "missing"

    def test_summary_returns_by_type_breakdown(self, client, auth_headers):
        resp = client.get("/api/v1/data-quality/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "by_type" in body
        assert "top_plants" in body


class TestBackfillIdempotency:
    def test_running_backfill_twice_second_time_creates_nothing_new(self):
        db = SessionLocal()
        try:
            backfill_data_quality_issues(db)
            second_run_count = backfill_data_quality_issues(db)
            assert second_run_count == 0
        finally:
            db.close()
