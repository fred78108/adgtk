"""observations.py — module-level observation and artifact tracking for a run.

Replaces journal.py. Two concerns live here:
  - Observations: researcher-facing typed events (notes, warnings,
        agent turns, etc.)
  - Artifacts: files produced during the run (internal, consumed by
        manifest builder)

Call reset() at the start of each run (the runner does this automatically).
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from adgtk.data.structure import PurposeTypes
from adgtk.tracking.structure import ArtifactEntry

# ----------------------------------------------------------------------
# Observation models
# ----------------------------------------------------------------------


class _BaseObs(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )
    tags: list[str] = []


class NoteObs(_BaseObs):
    kind: Literal["note"] = "note"
    message: str


class WarnObs(_BaseObs):
    kind: Literal["warn"] = "warn"
    message: str


class AgentTurnObs(_BaseObs):
    kind: Literal["agent_turn"] = "agent_turn"
    prompt: str
    response: str
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[float] = None


class ConfigNoteObs(_BaseObs):
    kind: Literal["config_note"] = "config_note"
    parameter: str
    value: Any
    rationale: str


class MetricEventObs(_BaseObs):
    kind: Literal["metric_event"] = "metric_event"
    metric: str
    value: float
    step: Optional[int] = None
    note: Optional[str] = None


AnyObservation = Annotated[
    Union[NoteObs, WarnObs, AgentTurnObs, ConfigNoteObs, MetricEventObs],
    Field(discriminator="kind"),
]

# ----------------------------------------------------------------------
# Module-level state
# ----------------------------------------------------------------------

_observations: list[AnyObservation] = []
_artifacts: list[ArtifactEntry] = []

# ----------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------


def reset() -> None:
    """Clear all observations and artifacts. Called by the runner
    between runs.
    """
    global _observations, _artifacts
    _observations = []
    _artifacts = []


# ----------------------------------------------------------------------
# Researcher-facing API
# ----------------------------------------------------------------------


def note(message: str, tags: list[str] = []) -> None:
    """Record a general finding or observation."""
    _observations.append(NoteObs(message=message, tags=tags))


def warn(message: str, tags: list[str] = []) -> None:
    """Record an anomaly or unexpected behavior."""
    _observations.append(WarnObs(message=message, tags=tags))


def agent_turn(
    prompt: str,
    response: str,
    model: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    latency_ms: Optional[float] = None,
    tags: list[str] = [],
) -> None:
    """Record a single agent prompt/response exchange."""
    _observations.append(
        AgentTurnObs(
            prompt=prompt,
            response=response,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            tags=tags,
        )
    )


def config_note(
    parameter: str, value: Any, rationale: str, tags: list[str] = []
) -> None:
    """Record why a configuration parameter was set to a specific value."""
    _observations.append(
        ConfigNoteObs(
            parameter=parameter, value=value,
            rationale=rationale, tags=tags,
        )
    )


def metric_event(
    metric: str,
    value: float,
    step: Optional[int] = None,
    note: Optional[str] = None,
    tags: list[str] = [],
) -> None:
    """Annotate a metric value at a specific point in the run."""
    _observations.append(
        MetricEventObs(
            metric=metric, value=value,
            step=step, note=note, tags=tags,
        )
    )


def get_all() -> list[AnyObservation]:
    """Return a copy of all recorded observations."""
    return list(_observations)


# ----------------------------------------------------------------------
# Internal artifact tracking (called by MetricTracker, DatasetManager, etc.)
# ----------------------------------------------------------------------


def add_artifact(
    path: str,
    purpose: PurposeTypes,
    size_bytes: Optional[int] = None,
) -> None:
    """Register a file produced during the run."""
    entry = ArtifactEntry(path=path, purpose=purpose, size_bytes=size_bytes)
    if entry not in _artifacts:
        _artifacts.append(entry)


def get_artifacts() -> list[ArtifactEntry]:
    """Return a copy of all registered artifacts."""
    return list(_artifacts)
