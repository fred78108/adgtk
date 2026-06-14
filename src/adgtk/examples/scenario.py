"""builtin.py provides built-in scenario's for testing and user usage."""

import time
from typing import Callable, ClassVar

import adgtk.tracking.observations as obs
from adgtk.experiment.result import RunResult, RunResultBuilder
from adgtk.factory import SupportsFactory, BlueprintQuestion
from adgtk.tracking import MetricTracker
from adgtk.tracking.structure import ExperimentRunFolders

# ----------------------------------------------------------------------
# Interview
# ----------------------------------------------------------------------
_q1 = BlueprintQuestion(
    attribute="delay",
    question="This is the delay before saying hello",
    entry_type="float",
    default_value=1
)

_q2 = BlueprintQuestion(
    attribute="measurement",
    question="Which measurement",
    entry_type="expand",
    group="measure"
)

hello_world_interview = [
    _q1
]
nested_interview = [
    _q1,
    _q2
]

# Sample data used by NestedWorld to exercise the injected measurement
_SAMPLE_TEXTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Agentic systems require careful evaluation strategies.",
    "Reproducibility is a cornerstone of good research.",
    "Configuration choices should always be documented.",
    "Observations help you understand what the agent actually did.",
]

# ----------------------------------------------------------------------
# Class
# ----------------------------------------------------------------------


class HelloWorldScenario(SupportsFactory):
    """A simple scenario that validates your environment.

    Demonstrates the observations and RunResultBuilder APIs. Useful as
    a reference when writing your own scenarios.
    """
    factory_id: ClassVar = "hello.world"
    group: ClassVar = "scenario"
    tags: ClassVar = ["demo", "development"]
    summary: ClassVar = "A simple scenario to validate your environment"
    interview_blueprint: ClassVar = hello_world_interview
    factory_can_init: ClassVar = True

    def __init__(self, delay: float) -> None:
        super().__init__()
        self.delay = delay

    def run_scenario(
        self,
        result_folders: ExperimentRunFolders
    ) -> RunResult:
        result = RunResultBuilder()

        # Tag the run so it appears as a column in cross-run comparison tables.
        result.tag("scenario", "hello.world")
        result.tag("delay", self.delay)

        # config_note records *why* a parameter was set to this value.
        # Invaluable when reviewing runs later or sharing results.
        obs.config_note(
            parameter="delay",
            value=self.delay,
            rationale="Configurable pause to simulate agent latency"
        )

        obs.note("HelloWorldScenario starting — validating environment")

        t_start = time.monotonic()
        time.sleep(self.delay)
        elapsed_ms = (time.monotonic() - t_start) * 1000

        print(f"Hello World from the Scenario! - delay={self.delay}s")

        # metric_event annotates a point-in-time value in the report.
        obs.metric_event(
            metric="elapsed_ms",
            value=elapsed_ms,
            note=f"Expected ~{self.delay * 1000:.0f}ms, got {elapsed_ms:.1f}ms"
        )

        result.set("elapsed_ms", round(elapsed_ms, 2))
        result.set("delay_configured", self.delay)

        # Warn if elapsed time drifted significantly from configured delay.
        drift_ms = abs(elapsed_ms - self.delay * 1000)
        if drift_ms > 100:
            obs.warn(
                f"Elapsed time drifted {drift_ms:.0f}ms from configured delay",
                tags=["timing"]
            )
            result.mark_inconclusive(
                f"Timing drift of {drift_ms:.0f}ms exceeds 100ms tolerance"
            )
        else:
            obs.note(f"Timing within tolerance — drift={drift_ms:.0f}ms")
            result.mark_pass()

        result.summarize(
            f"HelloWorld completed in {elapsed_ms:.1f}ms "
            f"(configured delay={self.delay}s)"
        )

        return result.finalize()


class NestedWorld(SupportsFactory):
    """A demo scenario that exercises a nested factory-injected measurement.

    Demonstrates RunResultBuilder, MetricTracker, and observations together.
    The measurement callable is injected by the factory at build time, making
    this a useful template for scenarios that evaluate a pluggable component.
    """
    factory_id: ClassVar = "nested.world"
    group: ClassVar = "scenario"
    tags: ClassVar = ["demo", "development"]
    summary: ClassVar = "A nested scenario to validate your environment"
    interview_blueprint: ClassVar = nested_interview
    factory_can_init: ClassVar = True

    def __init__(self, delay: float, measurement: Callable) -> None:
        super().__init__()
        self.delay = delay
        self.measure = measurement

    def run_scenario(
        self,
        result_folders: ExperimentRunFolders
    ) -> RunResult:
        result = RunResultBuilder()
        result.tag("scenario", "nested.world")
        result.tag("delay", self.delay)
        result.tag(
            "measurement", getattr(self.measure, "factory_id", "unknown"))

        obs.config_note(
            parameter="delay",
            value=self.delay,
            rationale="Configurable pause to simulate agent latency"
        )
        obs.config_note(
            parameter="measurement",
            value=getattr(self.measure, "factory_id", str(self.measure)),
            rationale="Injected by the factory — set via experiment blueprint"
        )
        note_str = (
            "NestedWorld starting — will apply injected measurement to "
            "sample texts"
        )
        obs.note(
            note_str,
            tags=["setup"]
        )

        # MetricTracker records one value per call; at run end these become
        # per-label CSVs in metrics/ and summary stats in the manifest.
        tracker = MetricTracker(name="nested", purpose="measurement")
        tracker.register_metric("score")
        tracker.register_metric("elapsed_ms")

        time.sleep(self.delay)
        print(f"Hello NestedWorld from the Scenario! - delay={self.delay}s")

        zero_results = 0
        for i, text in enumerate(_SAMPLE_TEXTS):
            t_start = time.monotonic()
            try:
                score = self.measure(text)
            except Exception as exc:
                obs.warn(
                    f"Measurement raised on item {i}: {exc}",
                    tags=["measurement-error"]
                )
                continue

            elapsed_ms = (time.monotonic() - t_start) * 1000
            tracker.add_data("score", float(score))
            tracker.add_data("elapsed_ms", elapsed_ms)

            if score == 0:
                zero_results += 1

        # Save CSVs; also registers each file as an artifact automatically.
        tracker.save_data(result_folders)

        n = tracker.measurement_count("score")
        if n == 0:
            obs.warn(
                "Measurement produced no results — check the measurement",
                tags=["no-data"]
            )
            result.mark_fail("Zero measurements recorded")
        else:
            mean_score = tracker.get_average("score")
            mean_ms = tracker.get_average("elapsed_ms")

            obs.metric_event(
                metric="score",
                value=mean_score,
                step=n,
                note=f"Mean over {n} items"
            )

            if zero_results > 0:
                obs.warn(
                    f"{zero_results} of {n} items scored zero — "
                    "may indicate measurement incompatibility with text input",
                    tags=["zero-score"]
                )

            obs.note(
                f"Measurement complete: mean_score={mean_score:.4f}, "
                f"mean_latency={mean_ms:.1f}ms over {n} items"
            )

            result.set("mean_score", round(mean_score, 4))
            result.set("mean_elapsed_ms", round(mean_ms, 2))
            result.set("n_measured", n)
            result.set("n_zero", zero_results)
            result.mark_pass()

        result.summarize(
            f"NestedWorld: measurement={getattr(
                self.measure, 'factory_id', '?')}, "
            f"n={tracker.measurement_count('score')}"
        )

        return result.finalize()
