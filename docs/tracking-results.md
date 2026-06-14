# Tracking & Results

This page covers the tools available inside a scenario for recording what happened during a run, returning results, and understanding what gets written to disk.

---

## Concepts

Three distinct concerns map to three distinct APIs:

| Concern | API | Written to |
|---------|-----|-----------|
| What happened during the run | `observations` module | `run.manifest.json`, `report.md` |
| What the run concluded | `RunResult` / `RunResultBuilder` | `run.manifest.json`, `results.yaml` |
| Numeric time-series metrics | `MetricTracker` / `MeasurementEngine` | `metrics/*.csv`, summarized in manifest |

The **manifest** (`run.manifest.json`) is the aggregate document that brings all three together. The **markdown report** (`report.md`) is generated from the manifest automatically at run end.

---

## Observations

Use `ObservationWriter` to record observations. It namespaces every entry with a `component` name and merges in default tags, making run reports much easier to read when multiple subsystems are active.

```python
from adgtk.tracking import ObservationWriter

obs = ObservationWriter("extractor", tags=["extraction"])
```

The writer delegates to the module-level observation store, which is reset automatically by the runner at the start of each run — you do not need to manage lifecycle yourself.

### `obs.note` — general findings

Record a researcher observation. Use this for anything you want to remember: a finding, a hypothesis, a comparison.

```python
obs.note("Prompt variant A consistently outperformed B on coherence tasks")
obs.note("Output length spiked on items with ambiguous entity types", tags=["edge-case"])
```

**Parameters:**

- `message: str` — the observation text
- `tags: list[str]` — extra labels for this observation (merged with the writer's default tags)

Every observation also receives the writer's `component:<name>` tag automatically.

---

### `obs.warn` — anomalies and surprises

Use this when something unexpected happened that you want to flag but didn't stop the run.

```python
obs.warn("Agent looped 7 times before producing a final answer")
obs.warn("Response contained refusal text despite benign prompt", tags=["refusal", "investigate"])
```

---

### `obs.agent_turn` — prompt/response pairs

Record a single exchange with an agent. This is the most important observation type for agent research — it gives you a full trace of what the agent saw and said, alongside cost and latency data.

```python
response = client.chat(prompt)

obs.agent_turn(
    prompt=prompt,
    response=response.text,
    model="claude-sonnet-4-6",
    tokens_in=response.usage.prompt_tokens,
    tokens_out=response.usage.completion_tokens,
    latency_ms=response.elapsed_ms,
    tags=["extraction-step"],
)
```

**Parameters:**

- `prompt: str` — the full prompt sent to the agent
- `response: str` — the agent's response
- `model: str` (optional) — model identifier, e.g. `"gpt-4o"`, `"claude-sonnet-4-6"`
- `tokens_in: int` (optional) — input token count
- `tokens_out: int` (optional) — output token count
- `latency_ms: float` (optional) — round-trip latency in milliseconds
- `tags: list[str]` (optional)

---

### `obs.config_note` — parameter decisions

Record why you chose a configuration value. This becomes invaluable when reviewing runs weeks later or comparing across experiments.

```python
obs.config_note(
    parameter="temperature",
    value=0.7,
    rationale="Lower temperature reduced hallucination rate in pilot runs"
)
```

**Parameters:**

- `parameter: str` — the parameter name
- `value: Any` — the value used
- `rationale: str` — why this value was chosen

---

### `obs.metric_event` — spot annotations on metrics

Annotate a specific metric value at a point in the run. Useful for flagging a breakpoint, a phase transition, or an unexpected jump.

```python
if step == warmup_steps:
    obs.metric_event(
        metric="accuracy",
        value=score,
        step=step,
        note="Post-warmup baseline"
    )
```

**Parameters:**

- `metric: str` — the metric name
- `value: float` — the value at this moment
- `step: int` (optional) — iteration or step index
- `note: str` (optional) — free-text annotation

---

### `@observation_track_step` — automatic entry/exit/error recording

Wrap any function to automatically record entry, exit timing, and exceptions as observations, without adding boilerplate to the function body:

```python
from adgtk.tracking import ObservationWriter, observation_track_step

obs = ObservationWriter("retriever")

@observation_track_step(obs)
def fetch_documents(query: str) -> list:
    ...

# Exceptions become warnings but are still re-raised.
# Set log_errors=False to capture timing only:
@observation_track_step(obs, log_errors=False)
def best_effort_step(query: str) -> list:
    ...
```

---

### Multiple components in one scenario

Create one writer per logical subsystem. Each writer uses its own `component` name, so observations from different parts of your code are clearly labelled in the report:

```python
retriever_obs = ObservationWriter("retriever", tags=["retrieval"])
evaluator_obs = ObservationWriter("evaluator", tags=["eval"])

retriever_obs.note("Loaded index")
evaluator_obs.metric_event("f1", 0.82)
```

---

### Module-level API

The underlying module-level functions (`adgtk.tracking.observations`) are still available directly. They are the storage backend that `ObservationWriter` delegates to. Prefer the writer in scenario code; the module-level API is useful in framework utilities that run outside a scenario context.

---

## Returning results from a scenario

Your `run_scenario` method must return a `RunResult`. There are two ways to build one.

### Option 1: `RunResultBuilder` (recommended for longer runs)

Build results incrementally throughout the run, then finalize at the end.

```python
from adgtk.experiment.result import RunResultBuilder

class MyScenario:
    def run_scenario(self, result_folders):
        result = RunResultBuilder()
        result.tag("model", "gpt-4o")
        result.tag("prompt_variant", "chain-of-thought")

        # ... run logic ...
        accuracy = 0.91

        result.set("accuracy", accuracy)
        result.pass_if(
            lambda m: m["accuracy"] >= 0.85,
            on_fail=f"Accuracy {accuracy:.3f} below threshold"
        )
        result.summarize(f"Chain-of-thought: accuracy={accuracy:.3f}")

        return result.finalize()
```

### Option 2: `RunResult` directly (for simpler scenarios)

```python
from adgtk.experiment.result import RunResult

return RunResult(
    metrics={"accuracy": 0.91, "f1": 0.88},
    verdict="pass",
    verdict_note="Both metrics above threshold",
    tags={"model": "gpt-4o", "prompt_variant": "v2"},
    summary="Baseline run with standard prompting",
)
```

### `RunResultBuilder` method reference

| Method | Description |
|--------|-------------|
| `.set(key, value)` | Record a result metric |
| `.tag(key, value)` | Attach a label for cross-run filtering |
| `.mark_pass(note="")` | Set verdict to `"pass"` |
| `.mark_fail(reason)` | Set verdict to `"fail"` |
| `.mark_inconclusive(note="")` | Set verdict to `"inconclusive"` |
| `.pass_if(condition, on_fail="")` | Evaluate a lambda against current metrics |
| `.summarize(text)` | Set a free-text summary for the report |
| `.finalize()` | Return the `RunResult` |

All methods return `self`, so calls can be chained:

```python
result.tag("model", "gpt-4o").tag("variant", "v2").mark_pass()
```

### Tags

Tags are `str → str` key-value pairs attached to a run. They serve two purposes:

1. **Cross-run comparison** — `adgtk-results export` includes tags as columns
2. **Filtering** — useful for grouping runs by configuration axis

Good tag candidates: model name, prompt variant, temperature, dataset split, any parameter you're sweeping. Values are always coerced to strings.

---

## Numeric metrics with MetricTracker

`MetricTracker` records numeric time-series values. At run end it writes each label to a CSV and the manifest summarizes them (mean, std, min, max, n).

```python
from adgtk.tracking import MetricTracker

class MyScenario:
    def __init__(self, ...):
        self.tracker = MetricTracker(name="eval", purpose="measurement")
        self.tracker.register_metric("accuracy")
        self.tracker.register_metric("latency_ms")

    def run_scenario(self, result_folders):
        for item in self.dataset:
            score = self.evaluate(item)
            self.tracker.add_data("accuracy", score)

        self.tracker.save_data(result_folders)

        result = RunResultBuilder()
        result.set("accuracy_mean", self.tracker.get_average("accuracy"))
        result.pass_if(lambda m: m["accuracy_mean"] >= 0.85)
        return result.finalize()
```

### Key MetricTracker methods

| Method | Description |
|--------|-------------|
| `register_metric(label)` | Declare a metric before recording data |
| `add_data(label, value)` | Append a single float or int |
| `add_raw_data(label, values)` | Append multiple values from an iterable |
| `get_average(label)` | Mean of all recorded values |
| `get_latest_value(label)` | Most recently recorded value |
| `get_sum(label)` | Sum of all recorded values |
| `get_all_data(label)` | Full list of all recorded values |
| `measurement_count(label)` | Number of data points recorded |
| `save_data(result_folders)` | Write CSVs and register as artifacts |

---

## Measurements with MeasurementEngine

`MeasurementEngine` wraps `MetricTracker` with registered measurement functions from the factory. Use it when you want to apply standard measurements to a dataset without writing the evaluation loop yourself.

```python
from adgtk.measurements import MeasurementEngine

engine = MeasurementEngine(add_by_tag="text")
engine.measure(generated_outputs)
engine.save_data(result_folders)

for label, value in engine.export_last_val_to_dict().items():
    result.set(label, value)
```

---

## What gets written to disk

After every run the following files are written to `results/{run_id}/`:

```
results/
  {run_id}/
    run.exp.config.yaml      ← full experiment YAML as run
    conclusions/
      run.manifest.json      ← canonical JSON (all run data)
      report.md              ← human-readable markdown report
      results.yaml           ← RunResult fields
    metrics/
      {name}.{label}.csv     ← one file per tracked metric label
    datasets/
    images/
    other/
```

### `run.manifest.json`

The canonical document. Contains everything: timing, verdict, tags, result metrics, per-metric summaries, all observations, all artifacts, and the full config snapshot.

```json
{
  "manifest_version": "1.0",
  "run_id": "3.my-experiment",
  "experiment_name": "my-experiment",
  "timestamp_start": "2026-05-09 14:02:11",
  "timestamp_end": "2026-05-09 14:06:44",
  "duration_seconds": 273.4,
  "status": "complete",
  "verdict": "pass",
  "tags": {"model": "gpt-4o", "prompt_variant": "chain-of-thought"},
  "result_metrics": {"accuracy_mean": 0.91, "n_evaluated": 120},
  "metric_summaries": {
    "eval.accuracy": {"n": 120, "mean": 0.91, "std": 0.04, "min": 0.75, "max": 1.0}
  },
  "observations": [
    {"kind": "config_note", "parameter": "temperature", "value": 0.7, "rationale": "..."},
    {"kind": "agent_turn", "model": "gpt-4o", "tokens_in": 312, "tokens_out": 88, "latency_ms": 940.0}
  ]
}
```

### `report.md`

Auto-generated from the manifest. Shows verdict, tags, result metrics, measurement summaries, observations, and artifacts. Check this after a run for a quick human summary.

---

## Cross-run comparison

### Experiment rollup report

After accumulating several runs, generate a rolled-up view with:

```bash
adgtk report my-experiment
```

This writes two files:

- `results/my-experiment/experiment_report.md` — a Markdown document covering verdict and status distributions, timing statistics, a per-run summary table, cross-run metric statistics, tag distributions, and a config-consistency warning if any run deviated from the majority configuration.
- `results/my-experiment/common/results.csv` — a flat CSV with one row per run, ready for notebook analysis.

**Config consistency check:** The report compares `run.exp.config.yaml` across all runs. If any run used a different configuration than the majority, those runs are listed in a warning block at the top and marked with ⚠ in the per-run table. This catches runs made after editing a blueprint, accidental re-runs against a modified config, or batch jobs that mixed different experiment versions.

### Raw export with adgtk-results

```bash
adgtk-results export my-experiment --format csv --output runs.csv
```

Tags appear as columns:

```
run_id,verdict,accuracy_mean,model,prompt_variant,temperature
3.my-experiment,pass,0.91,gpt-4o,chain-of-thought,0.7
2.my-experiment,fail,0.79,gpt-4o,zero-shot,0.9
```

Load in a notebook:

```python
import pandas as pd
df = pd.read_csv("runs.csv")
df.groupby("prompt_variant")["accuracy_mean"].mean()
```

---

## Studies — cross-experiment rollup

An experiment rollup operates within a single experiment (multiple runs of the same blueprint). A **study** operates across experiments — collecting results from several different blueprints into a single comparison.

Use a study when you want to compare, for example:

- Two models running the same scenario
- Three prompt strategies against the same dataset
- A baseline experiment and its successors over time

### Create a study blueprint

```bash
adgtk-study build
```

The interactive wizard lists available experiments and lets you select them by index or name. The blueprint is saved to `studies/{name}.yaml`:

```yaml
name: model-comparison
description: GPT-4o vs Claude on the extraction task
tags:
  - extraction
experiments:
  - exp-gpt4o
  - exp-claude
```

Edit this file at any time to change which experiments are included.

### Generate the study report

```bash
adgtk-study run model-comparison
```

This reads all run manifests for each listed experiment, recalculates statistics from scratch, and writes two files to `study-results/model-comparison/`:

| File | Purpose |
|------|---------|
| `study_report.md` | Overview table + per-experiment config, verdicts, timing, metrics |
| `study_results.csv` | Combined CSV — one row per run across all experiments |

The `study_report.md` opens with a **cross-experiment overview table** — one row per experiment showing run count, pass/fail counts, average duration, and mean values for every result metric and measurement. This is the at-a-glance comparison.

Each experiment then gets its own section with its configuration from the first run (the canonical "what was this experiment?"), verdict distribution, timing stats, and per-run metric tables.

### Study CSV for notebooks

The combined CSV uses the same column schema as `results.csv` but spans all experiments and leads with `experiment_name`:

```python
import pandas as pd
df = pd.read_csv("study-results/model-comparison/study_results.csv")

# Compare mean accuracy per experiment
df.groupby("experiment_name")["metric_accuracy"].mean()

# Filter to passing runs only
df[df["verdict"] == "pass"].groupby("experiment_name").size()
```

See [adgtk-study](cli-reference.md#adgtk-study) for the full CLI reference.

---

## Complete scenario example

See the [Creating Scenarios](user-guide/creating-scenarios.md) page for a full end-to-end example combining observations, `RunResultBuilder`, and `MetricTracker`.
