"""result.py — RunResult and RunResultBuilder.

RunResult replaces ScenarioResults. Scenarios return this from run_scenario().
RunResultBuilder is an optional fluent API for building results incrementally.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel


class RunResult(BaseModel):
    """What a scenario returns. The runner promotes this into a RunManifest."""

    # Key results for this run — any scalar or string values that matter
    metrics: dict[str, Any] = {}

    # Explicit verdict rather than leaving pass/fail implicit
    verdict: Literal["pass", "fail", "inconclusive"] = "inconclusive"
    verdict_note: str = ""

    # Key=value labels for cross-run comparison and filtering.
    # Values are always strings so they serialize cleanly and work as
    # query params in a future web interface.
    # e.g. {"model": "gpt-4o", "prompt_variant": "v2", "temperature": "0.7"}
    tags: dict[str, str] = {}

    # Optional free-text summary included in the report header
    summary: str = ""


class RunResultBuilder:
    """Fluent builder — accumulate results incrementally during a run.

    Example::

        result = RunResultBuilder()
        result.tag("model", "gpt-4o").tag("prompt_variant", "v2")
        # ... run the agent ...
        result.set("accuracy", 0.92).set("f1", 0.87)
        result.pass_if(lambda m: m["accuracy"] > 0.85, on_fail="below target")
        return result.finalize()
    """

    def __init__(self) -> None:
        self._metrics: dict[str, Any] = {}
        self._verdict: Literal["pass", "fail", "inconclusive"] = "inconclusive"
        self._verdict_note: str = ""
        self._tags: dict[str, str] = {}
        self._summary: str = ""

    def set(self, key: str, value: Any) -> "RunResultBuilder":
        """Record a result metric."""
        self._metrics[key] = value
        return self

    def tag(self, key: str, value: Any) -> "RunResultBuilder":
        """Attach a label for cross-run filtering (value coerced to str)."""
        self._tags[key] = str(value)
        return self

    def mark_pass(self, note: str = "") -> "RunResultBuilder":
        self._verdict = "pass"
        self._verdict_note = note
        return self

    def mark_fail(self, reason: str) -> "RunResultBuilder":
        self._verdict = "fail"
        self._verdict_note = reason
        return self

    def mark_inconclusive(self, note: str = "") -> "RunResultBuilder":
        self._verdict = "inconclusive"
        self._verdict_note = note
        return self

    def pass_if(
        self,
        condition: Callable[[dict[str, Any]], bool],
        on_fail: str = "",
    ) -> "RunResultBuilder":
        """Evaluate condition against current metrics and set verdict."""
        if condition(self._metrics):
            self._verdict = "pass"
        else:
            self._verdict = "fail"
            self._verdict_note = on_fail
        return self

    def summarize(self, text: str) -> "RunResultBuilder":
        """Set a free-text summary for the report header."""
        self._summary = text
        return self

    def finalize(self) -> RunResult:
        return RunResult(
            metrics=self._metrics,
            verdict=self._verdict,
            verdict_note=self._verdict_note,
            tags=self._tags,
            summary=self._summary,
        )
