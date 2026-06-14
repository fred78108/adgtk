"""User-configurable project settings stored in settings.yaml.

The file lives at the project root and is created with defaults on first
access.  All values are optional — missing keys fall back to defaults so
existing projects are not broken when new settings are added.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

SETTINGS_FILENAME = "settings.yaml"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TaskSettings(BaseModel):
    """Settings that control task-record retention and automatic cleanup."""

    ttl_days: int = Field(
        default=30,
        ge=1,
        description=(
            "Delete finished task directories older than this many days."
        ),
    )
    max_count: int = Field(
        default=200,
        ge=10,
        description="Keep at most this many task directories on disk.",
    )
    auto_cleanup: bool = Field(
        default=True,
        description="Run cleanup automatically at web-server startup.",
    )


class ProjectSettings(BaseModel):
    """Top-level project settings."""

    tasks: TaskSettings = Field(default_factory=TaskSettings)


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _settings_path() -> Path:
    return Path(SETTINGS_FILENAME)


def load_project_settings() -> ProjectSettings:
    """Read settings.yaml and return a ProjectSettings instance.

    Creates the file with defaults if it does not exist.  Falls back to
    defaults silently if the file is corrupt or has unexpected keys.
    """
    path = _settings_path()
    if not path.exists():
        settings = ProjectSettings()
        save_project_settings(settings)
        return settings
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return ProjectSettings.model_validate(raw)
    except Exception:
        return ProjectSettings()


def save_project_settings(settings: ProjectSettings) -> None:
    """Write a ProjectSettings instance to settings.yaml."""
    _settings_path().write_text(
        yaml.dump(
            settings.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
