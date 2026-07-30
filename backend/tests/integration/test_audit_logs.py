class TestAuditLogs:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/audit-logs")
        assert resp.status_code == 401

    def test_login_attempt_is_recorded(self, client, auth_headers):
        resp = client.get("/api/v1/audit-logs", params={"action": "login_success", "page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(item["action"] == "login_success" for item in body["items"])

    def test_failed_login_is_recorded(self, client, auth_headers):
        from tests.integration.conftest import TEST_EMAIL

        client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": "kesinlikle-yanlis"})
        resp = client.get("/api/v1/audit-logs", params={"action": "login_failed", "page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_pagination_shape(self, client, auth_headers):
        resp = client.get("/api/v1/audit-logs", params={"page": 1, "page_size": 3}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 3
        assert len(body["items"]) <= 3
