"""agent_writer.py — runtime metric writer for agentic test runs.

Mirrors the SummaryWriter pattern from TensorBoard but for agent experiments.
Initialize once per run, call log_step / log_tool_call during execution,
log_outcome at completion, then save().

Usage::

    writer = AgentWriter(folders)

    for step_result in agent.run(prompt):
        writer.log_step(
            latency=step_result.duration,
            tokens_in=step_result.tokens_in,
            tokens_out=step_result.tokens_out,
        )
        for call in step_result.tool_calls:
            writer.log_tool_call(call.name, success=call.ok)

    writer.log_outcome(success=True, goal_completion=0.9, optimal_steps=3)
    writer.save()

    # Or use the decorator on a step method:
    @track_step(writer)
    def agent_step(prompt: str) -> str:
        ...
"""

import functools
import time
from typing import Callable, Optional

from adgtk.tracking.base import MetricTracker
from adgtk.tracking.structure import ExperimentRunFolders

# ----------------------------------------------------------------------
# Metric label constants
# ----------------------------------------------------------------------

_LATENCY = "latency"
_TOKENS_IN = "tokens_in"
_TOKENS_OUT = "tokens_out"
_STEP_ERROR = "error"
_TOOL_CALL_TOTAL = "tool_call_count"
_SUCCESS = "success"
_GOAL_COMPLETION = "goal_completion"
_RETRY_COUNT = "retry_count"
_PATH_EFFICIENCY = "path_efficiency"
_FIRST_ATTEMPT_SUCCESS = "first_attempt_success"

_SCALAR_LABELS = [
    _LATENCY,
    _TOKENS_IN,
    _TOKENS_OUT,
    _STEP_ERROR,
    _TOOL_CALL_TOTAL,
    _SUCCESS,
    _GOAL_COMPLETION,
    _RETRY_COUNT,
    _PATH_EFFICIENCY,
    _FIRST_ATTEMPT_SUCCESS,
]


# ----------------------------------------------------------------------
# AgentWriter
# ----------------------------------------------------------------------


class AgentWriter:
    """Runtime metric writer for agentic test runs.

    Wraps MetricTracker with semantic, step-aware methods suited to agent
    evaluation. Per-step scalars (latency, tokens, errors) accumulate as
    time series; per-outcome scalars (success, goal_completion, retries,
    path_efficiency) record results at the end of a task attempt.

    CSV output uses the pattern ``{name}.{label}.csv`` inside the run's
    metrics folder, matching the convention used by MeasurementEngine.

    Args:
        folders: Run output folders. Metrics are written to folders.metrics.
        name: Prefix for output CSV files. Use a distinct name when running
            multiple writers in one experiment.
    """

    def __init__(
        self,
        folders: ExperimentRunFolders,
        name: str = "agent",
    ) -> None:
        self.folders = folders
        self._tracker = MetricTracker(name=name, purpose="other")
        self._step: int = 0
        self._outcome_count: int = 0
        self._tool_counts: dict[str, int] = {}

        for label in _SCALAR_LABELS:
            self._tracker.register_metric(label)

    # ------------------------------------------------------------------
    # Step-level logging
    # ------------------------------------------------------------------

    def log_step(
        self,
        latency: Optional[float] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        error: bool = False,
    ) -> None:
        """Record metrics for a single agent step.

        Only provided values are stored; omitted fields produce no entry
        for that step, keeping the per-metric series sparse rather than
        zero-padded.

        Args:
            latency: Wall-clock seconds elapsed for this step.
            tokens_in: Input tokens consumed by the model call.
            tokens_out: Output tokens produced by the model call.
            error: True if this step raised an unhandled exception.
        """
        self._step += 1
        if latency is not None:
            self._tracker.add_data(_LATENCY, latency)
        if tokens_in is not None:
            self._tracker.add_data(_TOKENS_IN, float(tokens_in))
        if tokens_out is not None:
            self._tracker.add_data(_TOKENS_OUT, float(tokens_out))
        self._tracker.add_data(_STEP_ERROR, 1.0 if error else 0.0)

    def log_tool_call(self, tool: str, success: bool = True) -> None:
        """Record a single tool invocation.

        Each call appends 1.0 to the ``tool_call_count`` series and
        creates a per-tool metric ``tool.<name>`` tracking success rate
        (1.0 = success, 0.0 = failure).

        Args:
            tool: Tool name or identifier.
            success: Whether the tool call completed without error.
        """
        self._tracker.add_data(_TOOL_CALL_TOTAL, 1.0)
        label = f"tool.{tool}"
        if not self._tracker.metric_exists(label):
            self._tracker.register_metric(label)
        self._tracker.add_data(label, 1.0 if success else 0.0)
        self._tool_counts[tool] = self._tool_counts.get(tool, 0) + 1

    # ------------------------------------------------------------------
    # Outcome logging
    # ------------------------------------------------------------------

    def log_outcome(
        self,
        success: bool,
        goal_completion: float = 1.0,
        optimal_steps: Optional[int] = None,
    ) -> None:
        """Record the result of a task attempt.

        Can be called multiple times for retry scenarios. On the first
        call, ``first_attempt_success`` is recorded. Each call appends
        to ``success``, ``goal_completion``, and ``retry_count`` (which
        reflects the number of prior failed attempts at time of logging).

        Args:
            success: Whether the agent completed the task.
            goal_completion: Partial-credit score in [0.0, 1.0]. Use 1.0
                for binary pass/fail tasks.
            optimal_steps: Known oracle step count. When provided,
                path_efficiency = min(optimal / actual, 1.0) is recorded.
        """
        is_first = self._outcome_count == 0
        self._outcome_count += 1

        self._tracker.add_data(_SUCCESS, 1.0 if success else 0.0)
        self._tracker.add_data(_GOAL_COMPLETION, float(goal_completion))
        self._tracker.add_data(_RETRY_COUNT, float(self._outcome_count - 1))

        if is_first:
            self._tracker.add_data(
                _FIRST_ATTEMPT_SUCCESS, 1.0 if success else 0.0
            )

        if optimal_steps is not None and self._step > 0:
            efficiency = float(optimal_steps) / float(self._step)
            self._tracker.add_data(_PATH_EFFICIENCY, min(efficiency, 1.0))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist all tracked metrics to the run's metrics folder."""
        self._tracker.save_data(self.folders)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def step_count(self) -> int:
        """Return the number of steps logged so far."""
        return self._step

    def tool_distribution(self) -> dict[str, int]:
        """Return a copy of per-tool invocation counts."""
        return dict(self._tool_counts)

    def summary(self) -> dict:
        """Return a snapshot dict of latest values for all tracked metrics.

        Includes scalar metrics, total step count, unique tool count, and
        the full tool distribution. Useful for quick console inspection or
        logging to observations.
        """
        result: dict = {}
        for label in _SCALAR_LABELS:
            try:
                result[label] = self._tracker.get_latest_value(label)
            except KeyError:
                pass
        dist = self.tool_distribution()
        result["total_steps"] = self._step
        result["tool_unique_count"] = len(dist)
        result["tool_distribution"] = dist
        return result


# ----------------------------------------------------------------------
# track_step decorator
# ----------------------------------------------------------------------


def track_step(
    writer: AgentWriter,
    *,
    log_errors: bool = True,
) -> Callable:
    """Decorator that wraps an agent step function with automatic
    metric capture.

    Measures wall-clock latency and, optionally, whether the call raised
    an exception. Calls ``writer.log_step()`` in the ``finally`` block so
    latency is always recorded even when the wrapped function raises.

    Args:
        writer: The AgentWriter instance to log to.
        log_errors: When True, exceptions are logged as errors before
            re-raising. Set to False to measure latency only.

    Usage::

        @track_step(writer)
        def solve(self, prompt: str) -> str:
            ...

        # With error logging disabled:
        @track_step(writer, log_errors=False)
        def fetch(url: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            error = False
            try:
                return func(*args, **kwargs)
            except Exception:
                if log_errors:
                    error = True
                raise
            finally:
                writer.log_step(
                    latency=time.monotonic() - start,
                    error=error,
                )
        return wrapper
    return decorator
