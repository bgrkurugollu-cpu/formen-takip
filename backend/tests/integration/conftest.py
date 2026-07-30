import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User

TEST_EMAIL = "test.integration@formen-demo.com"
TEST_PASSWORD = "TestPass!2026"


@pytest.fixture(scope="session", autouse=True)
def ensure_test_user():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == TEST_EMAIL))
        if user is None:
            user = User(
                email=TEST_EMAIL, password_hash=hash_password(TEST_PASSWORD),
                full_name="Test Entegrasyon Kullanıcısı", is_active=True,
            )
            db.add(user)
        else:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.is_active = True
        db.commit()
        yield
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
