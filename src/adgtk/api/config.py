"""Server configuration."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass
class ServerConfig:
    project_dir: str
    host: str = "127.0.0.1"
    port: int = 8000
    token: str | None = None
    no_auth: bool = False

    def __post_init__(self) -> None:
        if not self.no_auth and self.token is None:
            self.token = secrets.token_hex(16)

    @property
    def requires_auth(self) -> bool:
        return not self.no_auth

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def launch_url(self) -> str:
        if self.requires_auth and self.token:
            return f"{self.base_url}/?token={self.token}"
        return self.base_url
