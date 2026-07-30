class TestDashboardSummary:
    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_summary_returns_expected_shape(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/summary",
            params={"date_from": "2026-06-27", "date_to": "2026-07-27"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_plants"] == 50
        assert body["active_plants"] == 50
        assert body["data_source"] == "SYNTHETIC"
        assert 0 <= body["avg_company_score"] <= 200

    def test_summary_with_plant_filter_narrows_results(self, client, auth_headers):
        meta = client.get("/api/v1/meta/filters", headers=auth_headers).json()
        plant_id = meta["plants"][0]["id"]

        resp = client.get(
            "/api/v1/dashboard/summary",
            params={"date_from": "2026-06-27", "date_to": "2026-07-27", "plant_ids": plant_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_trend_endpoint_returns_points(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/trend",
            params={"date_from": "2026-01-01", "date_to": "2026-07-27", "granularity": "month"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        assert len(points) > 0
        for p in points:
            assert "total_score" in p
            assert "is_reliable" in p

    def test_plant_ranking_sorted_desc_by_default(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/plant-ranking", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        scores = [i["total_score"] for i in items]
        assert scores == sorted(scores, reverse=True)

    def test_performance_distribution_covers_all_levels(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/performance-distribution", headers=auth_headers)
        assert resp.status_code == 200
        names = {item["name"] for item in resp.json()["items"]}
        assert names == {"Kritik", "Geliştirilmeli", "İyi", "Çok İyi", "Mükemmel"}
