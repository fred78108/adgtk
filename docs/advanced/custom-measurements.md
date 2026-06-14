# Custom Measurements

ADGTK's measurement system is extensible. You can register your own measurement functions into the factory and use them via `MeasurementEngine` or directly.

---

## Built-in measurements

These are registered automatically and available out of the box:

| Factory ID | Type | Tags | Description |
|---|---|---|---|
| `string_length` | measurement | string | Character count |
| `exact_match` | comparison | string | 1.0 if identical, else 0.0 |
| `token_f1` | comparison | string | Word-overlap F1 (case-insensitive) |
| `json_valid` | measurement | string | 1.0 if valid JSON, else 0.0 |
| `dict_total_str_length` | measurement | dict | Total char count of all string values |
| `key_overlap` | comparison | dict | Shallow key overlap ratio |
| `dict_schema_match` | comparison | dict | Recursive key-path overlap (ignores values) |
| `schema_key_depth` | measurement | dict | Maximum nesting depth |
| `list_item_type_consistency` | measurement | list | Proportion of items sharing the dominant type |

```python
from adgtk.measurements import MeasurementEngine, create_measurement

# Use via engine
engine = MeasurementEngine(add_by_tag="comparison")
engine.compare(list(zip(predictions, references)))

# Use directly
m = create_measurement("token_f1")
score = m("the cat sat", "the cat")   # → 0.8
```

See the [Measurements API](../api/measurements.md) for the full reference.

---

---

## Measurement types

| Type | Input → Output | Use case |
|------|---------------|----------|
| `direct_measurement` | single input → scalar | Score one item |
| `distribution_measurement` | single input → distribution | Characterize a dataset |
| `direct_comparison` | two inputs → scalar | Diff between two items |
| `distribution_comparison` | two distributions → scalar | Compare two datasets |

---

## Registering a custom measurement

Use the `register_to_measurement_factory` decorator:

```python
from adgtk.measurements import register_to_measurement_factory


@register_to_measurement_factory
class ExactMatchMeasurement:
    factory_id = "exact-match"
    measurement_type = "direct_comparison"
    summary = "Exact string match between prediction and reference"
    tags = ["text", "classification"]

    def measure(self, prediction: str, reference: str) -> float:
        return 1.0 if prediction.strip() == reference.strip() else 0.0
```

Register it in `bootstrap.py`:

```python
from measurements.exact_match import ExactMatchMeasurement
from adgtk.measurements import register_to_measurement_factory

register_to_measurement_factory(ExactMatchMeasurement)
```

---

## Using custom measurements via MeasurementEngine

```python
from adgtk.measurements import MeasurementEngine

# Add by factory_id
engine = MeasurementEngine()
engine.add_measurement("exact-match")

# Or add all measurements with a tag
engine = MeasurementEngine(add_by_tag="text")

# Measure
engine.measure(predictions, references)    # for comparison types
engine.measure(outputs)                    # for direct/distribution types

engine.save_data(result_folders)
```

---

## Browsing registered measurements

```bash
adgtk-factory list measurement
adgtk-factory list measurement --tags text
```

---

## Direct use without MeasurementEngine

```python
from adgtk.measurements import create_measurement

m = create_measurement("exact-match", init_args={})
score = m.measure(prediction, reference)
```
