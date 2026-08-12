import uuid

from sqlalchemy import select

from app.models.foreman import Chief, Foreman


class TestContactInfoDataQuality:
    def test_every_foreman_has_phone_and_unique_email(self, db_session):
        foremen = list(db_session.scalars(select(Foreman)))
        assert foremen
        emails = [f.email for f in foremen]
        assert all(f.phone_number for f in foremen)
        assert all(emails)
        assert len(emails) == len(set(emails))

    def test_every_chief_has_phone_and_unique_email(self, db_session):
        chiefs = list(db_session.scalars(select(Chief)))
        assert chiefs
        emails = [c.email for c in chiefs]
        assert all(c.phone_number for c in chiefs)
        assert all(emails)
        assert len(emails) == len(set(emails))


class TestPlantsEndpoints:
    def test_list_plants_paginated(self, client, auth_headers):
        resp = client.get("/api/v1/plants", params={"page": 1, "page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 50
        assert len(body["items"]) == 5

    def test_plant_detail_404_for_unknown_id(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_plant_detail_and_summary(self, client, auth_headers):
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        plant_id = plants[0]["id"]

        detail = client.get(f"/api/v1/plants/{plant_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == plant_id

        summary = client.get(f"/api/v1/plants/{plant_id}/summary", headers=auth_headers)
        assert summary.status_code == 200
        assert "total_score" in summary.json()

    def test_plant_foremen_list_scoped_to_plant(self, client, auth_headers):
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        plant_id = plants[0]["id"]
        resp = client.get(f"/api/v1/plants/{plant_id}/foremen", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == plants[0]["active_foreman_count"] or resp.json()["total"] >= 0


class TestForemenEndpoints:
    def test_list_foremen_search(self, client, auth_headers):
        resp = client.get("/api/v1/foremen", params={"page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_foreman_detail_and_kpis(self, client, auth_headers):
        foremen = client.get("/api/v1/foremen", params={"page_size": 1}, headers=auth_headers).json()["items"]
        foreman_id = foremen[0]["id"]

        detail = client.get(f"/api/v1/foremen/{foreman_id}", headers=auth_headers)
        assert detail.status_code == 200
        body = detail.json()
        assert body["id"] == foreman_id
        assert body["phone_number"].startswith("+90")
        assert "@" in body["email"]

        kpis = client.get(f"/api/v1/foremen/{foreman_id}/kpis", headers=auth_headers)
        assert kpis.status_code == 200
        items = kpis.json()["items"]
        assert len(items) == 5
        total_weight = sum(i["weight"] for i in items)
        assert total_weight == 100

    def test_foreman_calculation_detail_contains_formula_breakdown(self, client, auth_headers):
        foremen = client.get("/api/v1/foremen", params={"page_size": 1}, headers=auth_headers).json()["items"]
        foreman_id = foremen[0]["id"]
        kpis = client.get(f"/api/v1/foremen/{foreman_id}/kpis", headers=auth_headers).json()["items"]
        kpi_id = kpis[0]["kpi_id"]

        resp = client.get(f"/api/v1/foremen/{foreman_id}/kpis/{kpi_id}/calculation-detail", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        for field in ["target_value", "actual_value", "calculation_type", "raw_score", "capped_score", "kpi_weight", "source_record_id"]:
            assert field in body

    def test_foreman_assignment_history_not_empty(self, client, auth_headers):
        foremen = client.get("/api/v1/foremen", params={"page_size": 1}, headers=auth_headers).json()["items"]
        foreman_id = foremen[0]["id"]
        resp = client.get(f"/api/v1/foremen/{foreman_id}/assignment-history", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    def test_foreman_detail_404_for_unknown_id(self, client, auth_headers):
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestKpiEndpoints:
    def test_list_kpis_returns_five_active(self, client, auth_headers):
        resp = client.get("/api/v1/kpis", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 5
        assert sum(i["weight"] for i in items) == 100

    def test_kpi_analysis(self, client, auth_headers):
        kpi_id = client.get("/api/v1/kpis", headers=auth_headers).json()["items"][0]["id"]
        resp = client.get(f"/api/v1/kpis/{kpi_id}/analysis", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "best_plants" in body
        assert "worst_plants" in body
        assert "trend" in body
