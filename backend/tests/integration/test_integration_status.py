from datetime import date, timedelta


class TestIntegrationRuns:
    def test_list_runs_requires_auth(self, client):
        resp = client.get("/api/v1/integration/runs")
        assert resp.status_code == 401

    def test_list_runs_returns_at_least_one(self, client, auth_headers):
        resp = client.get("/api/v1/integration/runs", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        run = body["items"][0]
        for field in ["id", "source_system", "started_at", "status", "processed_count", "success_count"]:
            assert field in run

    def test_get_run_detail(self, client, auth_headers):
        runs = client.get("/api/v1/integration/runs", params={"page_size": 1}, headers=auth_headers).json()["items"]
        run_id = runs[0]["id"]
        resp = client.get(f"/api/v1/integration/runs/{run_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == run_id


class TestResync:
    def test_resync_rejects_range_over_31_days(self, client, auth_headers):
        resp = client.post(
            "/api/v1/integration/resync",
            json={"date_from": "2026-01-01", "date_to": "2026-03-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_resync_rejects_inverted_range(self, client, auth_headers):
        resp = client.post(
            "/api/v1/integration/resync",
            json={"date_from": "2026-03-01", "date_to": "2026-01-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_resync_small_range_is_idempotent_noop_on_existing_data(self, client, auth_headers):
        meta = client.get("/api/v1/meta/filters", headers=auth_headers).json()
        plant_code = None
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        if plants:
            plant_code = plants[0]["code"]

        date_to = date.today() - timedelta(days=5)
        date_from = date_to - timedelta(days=2)
        payload = {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}
        if plant_code:
            payload["plant_codes"] = [plant_code]

        resp = client.post("/api/v1/integration/resync", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("success", "partial_success")
        assert body["success_count"] == 0
