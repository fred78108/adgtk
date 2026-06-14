# Tracking API

The tracking module provides the observations interface, MetricTracker, dataset file tracking, and the manifest/report generation.

## Import

```python
from adgtk.tracking import (
    ObservationWriter,
    observation_track_step,
    MetricTracker,
    JsonFileTracker,
    RunManifest,
    AnyObservation,
    NoteObs,
    WarnObs,
    AgentTurnObs,
    ConfigNoteObs,
    MetricEventObs,
    build_manifest,
    generate_markdown,
)
```

---

## `ObservationWriter`

The preferred API for recording observations. Wraps the module-level observation store with a component namespace and default tags.

```python
obs = ObservationWriter(component="retriever", tags=["retrieval"])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `component` | `str` | Logical name for this subsystem. Added as `component:<name>` on every observation. |
| `tags` | `list[str]` | Default tags merged into every observation from this writer. |

### Methods

```python
obs.note(message: str, tags: list[str] = []) -> None
```
Record a general finding or researcher note.

```python
obs.warn(message: str, tags: list[str] = []) -> None
```
Record an anomaly or unexpected event.

```python
obs.agent_turn(
    prompt: str,
    response: str,
    model: str = None,
    tokens_in: int = None,
    tokens_out: int = None,
    latency_ms: float = None,
    tags: list[str] = [],
) -> None
```
Record a single prompt/response exchange.

```python
obs.config_note(
    parameter: str,
    value: Any,
    rationale: str,
    tags: list[str] = [],
) -> None
```
Record a configuration decision with justification.

```python
obs.metric_event(
    metric: str,
    value: float,
    step: int = None,
    note: str = None,
    tags: list[str] = [],
) -> None
```
Annotate a specific point in a metric time series.

All methods merge tags as: `[component:<name>] + default_tags + per-call tags`.

---

## `observation_track_step`

Decorator that wraps a function with automatic observation recording — entry note, exit note with elapsed time, and exception warning.

```python
from adgtk.tracking import ObservationWriter, observation_track_step

obs = ObservationWriter("retriever")

@observation_track_step(obs)
def fetch(query: str) -> list:
    ...

@observation_track_step(obs, log_errors=False)  # timing only
def probe() -> None:
    ...
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `writer` | — | `ObservationWriter` instance to emit through |
| `log_errors` | `True` | When `True`, exceptions are recorded as warnings before re-raising |

---

## Observations module (low-level)

The `observations` module (`adgtk.tracking.observations`) is the storage backend that `ObservationWriter` delegates to. It holds run-scoped state and is reset automatically by the runner — you do not need to manage it in scenario code.

```python
import adgtk.tracking.observations as obs_module
obs_module.get_all()    # list[AnyObservation] — all recorded observations
```

---

## Observation types

All observations are typed dataclasses.

### `NoteObs`

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | Always `"note"` |
| `timestamp` | `str` | ISO timestamp |
| `message` | `str` | Observation text |
| `tags` | `list[str]` | Filter labels |

### `WarnObs`

Same fields as `NoteObs` with `kind = "warn"`.

### `AgentTurnObs`

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | Always `"agent_turn"` |
| `timestamp` | `str` | ISO timestamp |
| `prompt` | `str` | Full prompt sent |
| `response` | `str` | Agent response |
| `model` | `str` | Model identifier |
| `tokens_in` | `int` | Input token count |
| `tokens_out` | `int` | Output token count |
| `latency_ms` | `float` | Round-trip latency |
| `tags` | `list[str]` | Filter labels |

### `ConfigNoteObs`

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | Always `"config_note"` |
| `timestamp` | `str` | ISO timestamp |
| `parameter` | `str` | Parameter name |
| `value` | `Any` | Value used |
| `rationale` | `str` | Justification |

### `MetricEventObs`

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | Always `"metric_event"` |
| `timestamp` | `str` | ISO timestamp |
| `metric` | `str` | Metric name |
| `value` | `float` | Value at this point |
| `step` | `int` | Step index |
| `note` | `str` | Free-text annotation |

---

## `MetricTracker`

Records numeric time-series values during a run.

```python
tracker = MetricTracker(name="eval", purpose="measurement")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Prefix for CSV filenames (`{name}.{label}.csv`) |
| `purpose` | `str` | Metadata stored in artifacts registry |

### Methods

| Method | Description |
|--------|-------------|
| `register_metric(label)` | Declare a metric before recording data |
| `add_data(label, value)` | Append one float or int |
| `add_raw_data(label, values)` | Append multiple values |
| `get_average(label)` | Mean of all values |
| `get_latest_value(label)` | Most recently appended value |
| `get_sum(label)` | Sum of all values |
| `get_all_data(label)` | Full list of recorded values |
| `measurement_count(label)` | Number of data points |
| `save_data(result_folders)` | Write CSVs and register as artifacts |

---

## `RunManifest`

The canonical structured document for a run. Generated automatically by the runner — you do not construct this yourself.

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | `str` | Schema version |
| `run_id` | `str` | e.g. `"3.my-experiment"` |
| `experiment_name` | `str` | Experiment name |
| `timestamp_start` | `str` | Run start time |
| `timestamp_end` | `str` | Run end time |
| `duration_seconds` | `float` | Wall-clock duration |
| `status` | `str` | `"complete"` or `"incomplete"` |
| `verdict` | `str` | `"pass"`, `"fail"`, `"inconclusive"` |
| `verdict_note` | `str` | Explanation |
| `tags` | `dict[str, str]` | Cross-run labels |
| `result_metrics` | `dict[str, Any]` | Scalar results from `RunResult` |
| `metric_summaries` | `dict` | Per-label stats from `MetricTracker` |
| `observations` | `list[AnyObservation]` | All recorded observations |
| `artifacts` | `list` | Files written during the run |
| `config_snapshot` | `dict` | Full experiment definition used |

---

## `JsonFileTracker`

JSON-backed inventory for tracking dataset files used across experiments. Used internally by `DatasetManager`; import directly if you need lower-level control over the dataset inventory.

```python
from adgtk.tracking import JsonFileTracker
```

| Method | Description |
|--------|-------------|
| `register(source_file, encoding, id, tags, use, purpose)` | Add a file to the inventory |
| `retire(id)` | Remove an entry (file is not deleted) |
| `find_by_filename(filename)` | Look up an ID by filename |
| `list_registered()` | Return all active entries |
| `get_metadata(id)` | Return the `FileMetaData` for one entry |

The inventory is persisted to `.tracking/datasets.json`. `DatasetManager` wraps this class and is the preferred API for most scenarios — see [Data API](data.md).

---

## Manifest and report generation

These functions are called automatically by the runner. You do not need to call them in your scenario.

```python
manifest = build_manifest(run_data, observations, metric_summaries, artifacts)
markdown_text = generate_markdown(manifest)
```
