"""Tests for adgtk.api.server — create_app, login, dashboard.

Routes that call tracking modules are tested with mocked dependencies.

pytest test/api/test_server.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from adgtk.api.config import ServerConfig
from adgtk.api.server import create_app

TOKEN = "testtoken"


@pytest.fixture
def no_auth_config(tmp_path):
    return ServerConfig(project_dir=str(tmp_path), no_auth=True)


@pytest.fixture
def auth_config(tmp_path):
    return ServerConfig(project_dir=str(tmp_path), token=TOKEN)


def _client(config: ServerConfig, **kw) -> TestClient:
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        app = create_app(config)
    return TestClient(app, follow_redirects=False, **kw)


# ---------------------------------------------------------------------------
# create_app — basic smoke tests
# ---------------------------------------------------------------------------

def test_create_app_returns_fastapi_app(no_auth_config):
    from fastapi import FastAPI
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        app = create_app(no_auth_config)
    assert isinstance(app, FastAPI)


def test_create_app_with_auth_adds_middleware(auth_config):
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        app = create_app(auth_config)
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    assert any("TokenAuth" in t or "Middleware" in t for t in middleware_types)


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------

def test_get_config_after_create(no_auth_config):
    from adgtk.api.server import get_config
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        create_app(no_auth_config)
    cfg = get_config()
    assert cfg.no_auth is True


# ---------------------------------------------------------------------------
# Login endpoints
# ---------------------------------------------------------------------------

def test_login_page_accessible(no_auth_config):
    client = _client(no_auth_config)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        r = client.get("/login")
    assert r.status_code == 200


def test_auth_login_wrong_token_returns_401(auth_config):
    client = _client(auth_config)
    client.cookies.set("adgtk_token", TOKEN)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        r = client.post(
            "/auth/login",
            data={"token": "wrong", "next": "/"},
        )
    assert r.status_code == 401


def test_auth_login_correct_token_redirects(auth_config):
    client = _client(auth_config)
    client.cookies.set("adgtk_token", TOKEN)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        r = client.post(
            "/auth/login",
            data={"token": TOKEN, "next": "/"},
        )
    assert r.status_code == 302
    assert "adgtk_token" in r.cookies


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def test_dashboard_no_auth(no_auth_config):
    client = _client(no_auth_config)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        r = client.get("/")
    assert r.status_code == 200


def test_dashboard_recent_runs_partial(no_auth_config):
    client = _client(no_auth_config)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]):
        r = client.get("/dashboard/recent-runs")
    assert r.status_code == 200


def test_dashboard_stats_partial(no_auth_config):
    client = _client(no_auth_config)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]), \
         patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        r = client.get("/dashboard/stats")
    assert r.status_code == 200
