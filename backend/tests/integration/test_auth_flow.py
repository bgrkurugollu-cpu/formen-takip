from tests.integration.conftest import TEST_EMAIL, TEST_PASSWORD


class TestLoginFlow:
    def test_login_success_returns_tokens(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": "yanlis-parola"})
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "olmayan@formen-demo.com", "password": "x"})
        assert resp.status_code == 401

    def test_me_requires_authentication(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_returns_current_user(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == TEST_EMAIL

    def test_protected_dashboard_requires_authentication(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_refresh_returns_new_access_token(self, client):
        login = client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        refresh_token = login.json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_account_locks_after_repeated_failures(self, client):
        email = "lockout.test@formen-demo.com"
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.user import User

        from app.models.user import AuditLog

        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                db.query(AuditLog).filter(AuditLog.user_id == existing.id).delete()
                db.delete(existing)
                db.commit()
            db.add(User(email=email, password_hash=hash_password("CorrectPass!1"), full_name="Kilit Testi", is_active=True))
            db.commit()
        finally:
            db.close()

        for _ in range(5):
            resp = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
            assert resp.status_code == 401

        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "CorrectPass!1"})
        assert resp.status_code == 423
