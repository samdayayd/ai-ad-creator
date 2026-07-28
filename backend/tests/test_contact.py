import pytest

from app import contact as contact_module
from app.routers import contact as contact_router


def _configure_smtp(monkeypatch):
    monkeypatch.setattr(contact_module, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(contact_module, "SMTP_USERNAME", "owner@example.com")
    monkeypatch.setattr(contact_module, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(contact_module, "CONTACT_EMAIL", "owner@example.com")


def test_contact_returns_clear_error_when_smtp_not_configured(client):
    r = client.post("/api/contact", json={"name": "A", "email": "a@example.com", "message": "hi"})
    assert r.status_code == 503


def test_contact_sends_email_when_configured(client, monkeypatch):
    _configure_smtp(monkeypatch)
    sent = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, msg):
            sent["message"] = msg

    monkeypatch.setattr(contact_module.smtplib, "SMTP", _FakeSMTP)

    r = client.post(
        "/api/contact",
        json={"name": "Jane Doe", "email": "jane@example.com", "message": "The video generator is broken."},
    )
    assert r.status_code == 200, r.text
    assert sent["login"] == ("owner@example.com", "app-password")
    assert sent["message"]["To"] == "owner@example.com"
    assert sent["message"]["Reply-To"] == "jane@example.com"
    assert "Jane Doe" in sent["message"]["Subject"]


def test_contact_rejects_header_injection_in_email(client, monkeypatch):
    _configure_smtp(monkeypatch)
    r = client.post(
        "/api/contact",
        json={"name": "Jane", "email": "jane@example.com\r\nBcc: victim@example.com", "message": "hi"},
    )
    assert r.status_code == 400


def test_contact_rejects_missing_fields(client, monkeypatch):
    _configure_smtp(monkeypatch)
    r = client.post("/api/contact", json={"name": "  ", "email": "jane@example.com", "message": "hi"})
    assert r.status_code == 400


def test_contact_rejects_oversized_message(client, monkeypatch):
    _configure_smtp(monkeypatch)
    r = client.post(
        "/api/contact",
        json={"name": "Jane", "email": "jane@example.com", "message": "x" * 6000},
    )
    assert r.status_code == 400


def test_contact_rate_limits_repeated_submissions(client, monkeypatch):
    _configure_smtp(monkeypatch)
    monkeypatch.setattr(contact_module.smtplib, "SMTP", lambda *a, **k: _NullSMTP())

    for _ in range(5):
        r = client.post(
            "/api/contact", json={"name": "Jane", "email": "jane@example.com", "message": "hi"}
        )
        assert r.status_code == 200, r.text
    blocked = client.post("/api/contact", json={"name": "Jane", "email": "jane@example.com", "message": "hi"})
    assert blocked.status_code == 429


class _NullSMTP:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, *args):
        pass

    def send_message(self, *args):
        pass
