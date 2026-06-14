"""Tests for adgtk.api.auth — TokenAuthMiddleware.

pytest test/api/test_auth.py
"""

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from adgtk.api.auth import TokenAuthMiddleware

TOKEN = "test-token-123"


def _make_app(token: str = TOKEN) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TokenAuthMiddleware, token=token)

    @app.get("/protected")
    async def protected():
        return PlainTextResponse("ok")

    @app.get("/login")
    async def login_page():
        return PlainTextResponse("login page")

    @app.get("/auth/login")
    async def do_login():
        return PlainTextResponse("login action")

    @app.get("/static/style.css")
    async def static_file():
        return PlainTextResponse("css")

    @app.get("/tasks/status")
    async def tasks_status():
        return PlainTextResponse("tasks")

    return app


@pytest.fixture
def client():
    return TestClient(_make_app(), follow_redirects=False)


# ---------------------------------------------------------------------------
# Unauthenticated requests
# ---------------------------------------------------------------------------

def test_no_cookie_redirects_to_login(client):
    r = client.get("/protected")
    assert r.status_code == 302
    assert "/login" in r.headers["location"]


def test_wrong_cookie_redirects_to_login(client):
    client.cookies.set("adgtk_token", "wrong")
    r = client.get("/protected")
    assert r.status_code == 302


# ---------------------------------------------------------------------------
# Cookie auth
# ---------------------------------------------------------------------------

def test_valid_cookie_passes_through(client):
    client.cookies.set("adgtk_token", TOKEN)
    r = client.get("/protected")
    assert r.status_code == 200
    assert r.text == "ok"


# ---------------------------------------------------------------------------
# Query-string token (first-time link)
# ---------------------------------------------------------------------------

def test_valid_query_token_sets_cookie_and_redirects(client):
    r = client.get(f"/protected?token={TOKEN}")
    assert r.status_code == 302
    assert "adgtk_token" in r.cookies


def test_invalid_query_token_redirects_to_login(client):
    r = client.get("/protected?token=wrong")
    assert r.status_code == 302
    assert "/login" in r.headers["location"]


# ---------------------------------------------------------------------------
# Skip paths — should pass through without auth
# ---------------------------------------------------------------------------

def test_login_page_skipped(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_auth_login_skipped(client):
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_static_prefix_skipped(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200


def test_tasks_prefix_skipped(client):
    r = client.get("/tasks/status")
    assert r.status_code == 200
