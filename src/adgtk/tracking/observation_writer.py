"""observation_writer.py — class-based facade over the observations module.

Mirrors the AgentWriter pattern from measurements/agent_writer.py.
The module-level functions in observations.py remain the storage backend;
ObservationWriter adds a component namespace, instance-level default tags,
and a @track_step decorator.

Usage::

    obs = ObservationWriter(component="retriever", tags=["retrieval"])
    obs.note("Loading index")
    obs.metric_event("hit_rate", 0.88)

    @track_step(obs)
    def fetch(query: str) -> str:
        ...
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Optional

import adgtk.tracking.observations as observations


class ObservationWriter:
    """Namespaced facade over the module-level observations API.

    Every observation emitted through an instance automatically receives a
    ``component:<name>`` tag plus any instance-level default tags.

    Args:
        component: Logical component name (e.g. ``"retriever"``). Becomes
            the tag ``component:retriever`` on every observation.
        tags: Additional tags applied to every observation from this writer.
    """

    def __init__(self, component: str, tags: list[str] = []) -> None:
        self.component = component
        self._default_tags = list(tags)

    def _tags(self, extra: list[str] = []) -> list[str]:
        return (
            [f"component:{self.component}"]
            + self._default_tags + list(extra)
        )

    def note(self, message: str, tags: list[str] = []) -> None:
        observations.note(message, tags=self._tags(tags))

    def warn(self, message: str, tags: list[str] = []) -> None:
        observations.warn(message, tags=self._tags(tags))

    def agent_turn(
        self,
        prompt: str,
        response: str,
        model: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        latency_ms: Optional[float] = None,
        tags: list[str] = [],
    ) -> None:
        observations.agent_turn(
            prompt,
            response,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            tags=self._tags(tags),
        )

    def config_note(
        self, parameter: str, value: Any, rationale: str, tags: list[str] = []
    ) -> None:
        observations.config_note(
            parameter, value, rationale, tags=self._tags(tags)
        )

    def metric_event(
        self,
        metric: str,
        value: float,
        step: Optional[int] = None,
        note: Optional[str] = None,
        tags: list[str] = [],
    ) -> None:
        observations.metric_event(
            metric, value, step=step, note=note, tags=self._tags(tags)
        )


def track_step(
    writer: ObservationWriter,
    *,
    log_errors: bool = True,
) -> Callable:
    """Decorator that wraps a function with automatic observation capture.

    Records entry and exit as notes, and exceptions as warnings, all tagged
    with ``step``. Latency is included in the exit/error message.

    Args:
        writer: The ObservationWriter instance to emit observations through.
        log_errors: When True, exceptions are recorded as warnings before
            re-raising. Set to False to record entry/exit only.

    Usage::

        @track_step(obs)
        def fetch(query: str) -> str:
            ...

        @track_step(obs, log_errors=False)
        def probe() -> None:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            writer.note(f"→ {func.__name__}", tags=["step"])
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                writer.note(
                    f"← {func.__name__} ({elapsed:.0f}ms)",
                    tags=["step"],
                )
                return result
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                if log_errors:
                    writer.warn(
                        f"✗ {func.__name__} raised {type(exc).__name__}: {exc}"
                        f" ({elapsed:.0f}ms)",
                        tags=["step", "error"],
                    )
                raise
        return wrapper
    return decorator
