
class TestShiftAnalysisCards:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/shift-analysis/cards").status_code == 401

    def test_cards_response_includes_summary_in_one_request(self, client, auth_headers):
        # `/summary` ayrı bir endpoint olarak kaldırıldı — `build_cards`'ın (aylık ham kayıt
        # çekme + hücre gruplama + karşılaştırma) tekrar çalıştırılmasını gerektirirdi (bkz.
        # app/api/v1/shift_analysis.py::get_cards). Artık tek istekte hem kartlar hem özet gelir.
        resp = client.get("/api/v1/shift-analysis/cards", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "summary" in body
        summary = body["summary"]
        for key in ("period", "total_anomalies", "high_count", "medium_count", "top_plant", "top_kpi", "max_pct_diff"):
            assert key in summary
        assert summary["total_anomalies"] == len(body["items"])

    def test_standalone_summary_endpoint_removed(self, client, auth_headers):
        resp = client.get("/api/v1/shift-analysis/summary", headers=auth_headers)
        assert resp.status_code == 404
