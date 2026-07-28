import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("OWNER_EMAIL", "owner@example.com")
os.environ.setdefault("OWNER_PASSWORD", "changeme123")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.routers.auth import _failed_attempts


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    # The login rate limiter's failed-attempt counts live in module-level
    # state, not the DB — without this, one test's failed-login attempts
    # would bleed into the next test's count (TestClient requests all share
    # the same "testclient" IP), risking a flaky lockout unrelated to what
    # that later test is actually checking.
    _failed_attempts.clear()
    yield
    _failed_attempts.clear()


@pytest.fixture()
def client():
    # Fresh tables per test — the app's startup hook re-seeds the owner user
    # into them, so each test starts from a clean, known DB state.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def token(client):
    r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "changeme123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
