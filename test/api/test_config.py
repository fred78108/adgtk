"""Tests for adgtk.api.config — ServerConfig.

pytest test/api/test_config.py
"""

from adgtk.api.config import ServerConfig


def test_server_config_defaults():
    cfg = ServerConfig(project_dir="/tmp/proj")
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.no_auth is False


def test_server_config_generates_token_when_no_auth_false():
    cfg = ServerConfig(project_dir="/tmp/proj", no_auth=False)
    assert cfg.token is not None
    assert len(cfg.token) > 0


def test_server_config_no_token_when_no_auth_true():
    cfg = ServerConfig(project_dir="/tmp/proj", no_auth=True)
    assert cfg.token is None


def test_server_config_explicit_token_preserved():
    cfg = ServerConfig(project_dir="/tmp/proj", token="mysecret")
    assert cfg.token == "mysecret"


def test_server_config_requires_auth_true_by_default():
    cfg = ServerConfig(project_dir="/tmp/proj")
    assert cfg.requires_auth is True


def test_server_config_requires_auth_false_when_no_auth():
    cfg = ServerConfig(project_dir="/tmp/proj", no_auth=True)
    assert cfg.requires_auth is False


def test_server_config_base_url():
    cfg = ServerConfig(project_dir="/tmp", host="0.0.0.0", port=9000, no_auth=True)
    assert cfg.base_url == "http://0.0.0.0:9000"


def test_server_config_launch_url_with_auth():
    cfg = ServerConfig(project_dir="/tmp", token="abc123")
    assert "token=abc123" in cfg.launch_url


def test_server_config_launch_url_no_auth():
    cfg = ServerConfig(project_dir="/tmp", no_auth=True)
    assert "token" not in cfg.launch_url
    assert cfg.launch_url == cfg.base_url


def test_server_config_tokens_differ_per_instance():
    cfg1 = ServerConfig(project_dir="/tmp")
    cfg2 = ServerConfig(project_dir="/tmp")
    assert cfg1.token != cfg2.token
