# Experiment API

The experiment module handles experiment definitions, building, running, and result structures.

## Import

```python
from adgtk.experiment.result import RunResult, RunResultBuilder
from adgtk.experiment.runner import run_experiment
```

---

## `RunResult`

The structured summary returned by a scenario's `run_scenario` method.

```python
@dataclass
class RunResult:
    metrics: dict[str, Any]       # scalar result measurements
    verdict: str                  # "pass", "fail", or "inconclusive"
    verdict_note: str             # explanation of the verdict
    tags: dict[str, str]          # key-value labels for cross-run comparison
    summary: str                  # free-text run summary
```

Construct directly for simple scenarios:

```python
return RunResult(
    metrics={"accuracy": 0.91, "f1": 0.88},
    verdict="pass",
    verdict_note="Both metrics above threshold",
    tags={"model": "gpt-4o", "variant": "v2"},
    summary="Standard prompting baseline",
)
```

---

## `RunResultBuilder`

Fluent API for building a `RunResult` incrementally during a run.

```python
result = RunResultBuilder()
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `.set(key, value)` | `self` | Record a result metric |
| `.tag(key, value)` | `self` | Attach a cross-run comparison label |
| `.mark_pass(note="")` | `self` | Set verdict to `"pass"` |
| `.mark_fail(reason)` | `self` | Set verdict to `"fail"` |
| `.mark_inconclusive(note="")` | `self` | Set verdict to `"inconclusive"` |
| `.pass_if(fn, on_fail="")` | `self` | Evaluate `fn(metrics)` and set verdict |
| `.summarize(text)` | `self` | Set the free-text summary |
| `.finalize()` | `RunResult` | Build and return the `RunResult` |

All methods except `.finalize()` return `self` for chaining:

```python
result.tag("model", "gpt-4o").set("accuracy", 0.91).mark_pass()
return result.finalize()
```

### `pass_if`

```python
result.pass_if(
    lambda m: m["accuracy"] >= 0.85 and m["n_refusals"] == 0,
    on_fail="accuracy below threshold or refusals detected"
)
```

The lambda receives the current `metrics` dict. If it returns `True`, verdict is set to `"pass"`; otherwise `"fail"` with the `on_fail` message as the note.

---

## `ExperimentDefinition`

Pydantic model representing an experiment YAML definition.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Experiment name |
| `description` | `str` | Free-text description |
| `factory_id` | `str` | Scenario factory ID |
| `factory_init` | `bool` | Always `True` for factory components |
| `init_config` | `dict` | Constructor arguments |

Loaded automatically by the runner from `blueprints/{name}.exp.yaml`.

---

## `ExperimentRunFolders`

Passed to `run_scenario` by the runner. Provides paths to the run's output directories.

| Attribute | Path |
|-----------|------|
| `.metrics` | `results/{run_id}/metrics/` |
| `.datasets` | `results/{run_id}/datasets/` |
| `.images` | `results/{run_id}/images/` |
| `.other` | `results/{run_id}/other/` |
| `.conclusion` | `results/{run_id}/conclusion/` |

Pass to `tracker.save_data(result_folders)` and `engine.save_data(result_folders)`.

---

## `ScenarioProtocol`

The interface a scenario class must satisfy. `SupportsFactory` already implements this; you only need to reference it directly if you're type-checking.

```python
class ScenarioProtocol(Protocol):
    def run_scenario(self, result_folders: ExperimentRunFolders) -> RunResult:
        ...
```
