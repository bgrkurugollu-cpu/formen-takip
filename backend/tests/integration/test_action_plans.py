import uuid
from datetime import date, timedelta


def _create_payload(plant_id: str) -> dict:
    today = date.today()
    return {
        "title": "Fire oranını düşürme aksiyonu",
        "description": "Kaynak bölümünde fire oranı hedefin üzerinde, kök neden analizi yapılacak.",
        "plant_id": plant_id,
        "owner": "Kalite Ekibi",
        "priority": "high",
        "status": "open",
        "start_date": today.isoformat(),
        "target_end_date": (today + timedelta(days=30)).isoformat(),
        "completion_percentage": 0,
    }


class TestActionPlanCrud:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/action-plans")
        assert resp.status_code == 401

    def test_create_requires_valid_dates(self, client, auth_headers):
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        plant_id = plants[0]["id"]
        payload = _create_payload(plant_id)
        payload["target_end_date"] = payload["start_date"]
        payload["start_date"] = (date.today() + timedelta(days=10)).isoformat()
        resp = client.post("/api/v1/action-plans", json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_list_get_update_flow(self, client, auth_headers):
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        plant_id = plants[0]["id"]

        create_resp = client.post("/api/v1/action-plans", json=_create_payload(plant_id), headers=auth_headers)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["status"] == "open"
        assert created["plant"]["id"] == plant_id
        plan_id = created["id"]

        list_resp = client.get("/api/v1/action-plans", params={"plant_id": plant_id}, headers=auth_headers)
        assert list_resp.status_code == 200
        assert any(item["id"] == plan_id for item in list_resp.json()["items"])

        get_resp = client.get(f"/api/v1/action-plans/{plan_id}", headers=auth_headers)
        assert get_resp.status_code == 200

        update_resp = client.patch(
            f"/api/v1/action-plans/{plan_id}",
            json={"status": "in_progress", "completion_percentage": 40},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["status"] == "in_progress"
        assert updated["completion_percentage"] == 40

        audit_resp = client.get(
            "/api/v1/audit-logs", params={"action": "action_plan_updated", "page_size": 5}, headers=auth_headers
        )
        assert audit_resp.status_code == 200
        assert audit_resp.json()["total"] >= 1

    def test_completing_plan_sets_actual_end_date(self, client, auth_headers):
        plants = client.get("/api/v1/plants", params={"page_size": 1}, headers=auth_headers).json()["items"]
        plant_id = plants[0]["id"]
        plan_id = client.post("/api/v1/action-plans", json=_create_payload(plant_id), headers=auth_headers).json()["id"]

        resp = client.patch(f"/api/v1/action-plans/{plan_id}", json={"status": "completed"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["actual_end_date"] is not None

    def test_get_unknown_plan_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/action-plans/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
