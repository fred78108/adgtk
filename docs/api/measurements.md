# Measurements API

The measurements module provides two complementary metric systems:

- **`MeasurementEngine`** — applies registered measurement functions to a dataset after the fact (output quality, similarity, structure)
- **`AgentWriter`** — records runtime behavioral metrics *while* an agent runs (latency, tokens, tool calls, outcome)

---

## Import

```python
from adgtk.measurements import (
    # Runtime writer
    AgentWriter,
    track_step,
    # Dataset engine
    MeasurementEngine,
    MeasurementData,
    MeasurementReport,
    # Registry
    create_measurement,
    get_measurement_factory_entry,
    get_measurements_by_tag,
    get_measurements_by_type,
    register_to_measurement_factory,
)
```

---

## `AgentWriter`

Runtime metric writer for agentic test runs. See the [full guide](../advanced/agent-writer.md) for examples.

```python
writer = AgentWriter(result_folders)               # name="agent" by default
writer = AgentWriter(result_folders, name="planner")
```

### Methods

| Method | Description |
|--------|-------------|
| `log_step(latency, tokens_in, tokens_out, error)` | Record metrics for one agent step |
| `log_tool_call(tool, success)` | Record one tool invocation |
| `log_outcome(success, goal_completion, optimal_steps)` | Record task result |
| `save()` | Write all CSVs to `folders.metrics/` |
| `step_count()` | Number of steps logged |
| `tool_distribution()` | `{tool_name: call_count}` dict |
| `summary()` | Latest value snapshot for all metrics |

### Built-in metrics written to disk

| Label | Logged by | What it captures |
|---|---|---|
| `latency` | `log_step` | Wall-clock seconds per step |
| `tokens_in` | `log_step` | Input tokens per step |
| `tokens_out` | `log_step` | Output tokens per step |
| `error` | `log_step` | 1.0 if step errored, else 0.0 |
| `tool_call_count` | `log_tool_call` | 1.0 per call (sum = total) |
| `tool.{name}` | `log_tool_call` | Per-tool: 1.0 success / 0.0 failure |
| `success` | `log_outcome` | 1.0 = pass, 0.0 = fail |
| `goal_completion` | `log_outcome` | Partial-credit score 0–1 |
| `retry_count` | `log_outcome` | Failed attempts before this call |
| `path_efficiency` | `log_outcome` | min(optimal / actual steps, 1.0) |
| `first_attempt_success` | `log_outcome` (first call) | 1.0 if first attempt succeeded |

### Minimal example

```python
writer = AgentWriter(result_folders)

for step_result in agent.run(task):
    writer.log_step(
        latency=step_result.elapsed,
        tokens_in=step_result.tokens_in,
        tokens_out=step_result.tokens_out,
    )
    for call in step_result.tool_calls:
        writer.log_tool_call(call.name, success=call.ok)

writer.log_outcome(success=True, goal_completion=0.9, optimal_steps=3)
writer.save()
```

---

## `track_step`

Decorator that wraps a step function with automatic latency and error capture.

```python
from adgtk.measurements import AgentWriter, track_step

writer = AgentWriter(result_folders)

@track_step(writer)
def agent_step(prompt: str) -> str:
    return call_llm(prompt)

# Disable error flagging (latency only):
@track_step(writer, log_errors=False)
def best_effort_step(prompt: str) -> str:
    ...
```

Latency is always recorded — `log_step` fires in the `finally` block even when the wrapped function raises.

---

## `MeasurementEngine`

Applies one or more registered measurement functions to a dataset. Results are stored in the same `MetricTracker` / CSV format used by `AgentWriter`.

```python
engine = MeasurementEngine()
engine = MeasurementEngine(add_by_tag="built-in")   # pre-load all built-ins
engine = MeasurementEngine(add_by_tag="comparison") # pre-load comparison functions
```

### Methods

| Method | Description |
|--------|-------------|
| `add(factory_id)` | Register a measurement by factory ID |
| `measure(data)` | Apply all measurements; iterates per-item if needed |
| `compare(pairs)` | Apply comparison measurements to `[(a, b), ...]` |
| `measure_dataset_distribution(dataset)` | Distribution measurements over the full dataset |
| `compare_dataset_distribution(ds1, ds2)` | Distribution comparisons |
| `save_data(result_folders)` | Write CSVs via the internal `MetricTracker` |
| `export_last_val_to_dict()` | `{label: latest_value}` for each measurement |
| `report()` | `MeasurementReport` with all labels and recorded data |

### Example

```python
engine = MeasurementEngine(add_by_tag="comparison")
engine.compare(list(zip(predictions, references)))
engine.save_data(result_folders)

for label, value in engine.export_last_val_to_dict().items():
    result.set(label, value)
```

---

## Built-in measurements

These ship with ADGTK and are registered automatically at import time. Use them directly via `MeasurementEngine` or `create_measurement`.

### String measurements

| Factory ID | Tags | Input | Returns | Description |
|---|---|---|---|---|
| `string_length` | string, built-in | `str` | `int` | Character count |
| `exact_match` | string, comparison, built-in | `str, str` | `float` | 1.0 if identical, else 0.0 |
| `token_f1` | string, comparison, built-in | `str, str` | `float` | Word-overlap F1 (case-insensitive) |
| `json_valid` | string, built-in | `str` | `float` | 1.0 if valid JSON, else 0.0 |

### Dictionary measurements

| Factory ID | Tags | Input | Returns | Description |
|---|---|---|---|---|
| `dict_total_str_length` | dict, built-in | `dict` | `int` | Total character count of all string values |
| `key_overlap` | dict, comparison, built-in | `dict, dict` | `float` | Shallow key overlap ratio |
| `dict_schema_match` | dict, comparison, built-in | `dict, dict` | `float` | Recursive key-path overlap (ignores values) |
| `schema_key_depth` | dict, built-in | `dict` | `int` | Maximum nesting depth (root = 1) |

### List measurements

| Factory ID | Tags | Input | Returns | Description |
|---|---|---|---|---|
| `list_item_type_consistency` | list, built-in | `list` | `float` | Proportion of items sharing the dominant type |

### Browsing via CLI

```bash
adgtk-factory list measurement
adgtk-factory list measurement --tags built-in
adgtk-factory list measurement --tags comparison
```

---

## Registry functions

```python
# Instantiate a measurement by ID
m = create_measurement("exact_match")
score = m("the cat sat", "the cat")

# Look up an entry without instantiating
entry = get_measurement_factory_entry("token_f1")

# Filter by tag
entries = get_measurements_by_tag("comparison")

# Filter by measurement type
entries = get_measurements_by_type("direct_comparison")
```

---

## `register_to_measurement_factory`

Decorator to register a custom measurement function or class. See [Custom Measurements](../advanced/custom-measurements.md) for the full guide.

```python
from adgtk.measurements import register_to_measurement_factory

@register_to_measurement_factory(tags=["text", "custom"])
def my_score(a: str, b: str) -> float:
    """My custom similarity metric."""
    ...
```

---

## `MeasurementData` / `MeasurementReport`

TypedDicts returned by `engine.report()`.

```python
class MeasurementData(TypedDict):
    label: str
    description: str
    data: list

class MeasurementReport(TypedDict):
    engine_id: str
    measurements: list[MeasurementData]
```

---

## Measurement types reference

| Type | Signature | Use case |
|------|-----------|----------|
| `direct_measurement` | `f(a) -> float` | Score one item |
| `direct_comparison` | `f(a, b) -> float` | Diff between two items |
| `distribution_measurement` | `f(data) -> list[float]` | Characterise a dataset |
| `distribution_comparison` | `f(dist_a, dist_b) -> float` | Compare two datasets |
