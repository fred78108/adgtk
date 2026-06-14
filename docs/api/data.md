# Data API

The data module manages dataset registration and loading. It keeps an inventory of available datasets in `.tracking/datasets.json`.

## Import

```python
from adgtk.data import DatasetManager
```

---

## `DatasetManager`

Manages dataset registration and loading via a JSON inventory file.

```python
manager = DatasetManager()
```

### Registering a dataset

```python
manager.register(
    source_file="data/labeled-extraction-v2.csv",
    encoding="utf-8",
    id="labeled-extraction-v2",
    tags=["extraction", "labeled"],
    use="evaluation",
    purpose="Labeled extraction evaluation set — 500 items",
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_file` | `str` | Path to the data file |
| `encoding` | `str` | File encoding (e.g. `"utf-8"`) |
| `id` | `str` | Unique identifier for lookups |
| `tags` | `list[str]` | Filter labels |
| `use` | `str` | Intended use (`"evaluation"`, `"training"`, etc.) |
| `purpose` | `str` | Free-text description |
| `metadata_file` | `str` (optional) | Path to a separate metadata JSON |

### Loading a dataset

```python
data = manager.load("labeled-extraction-v2")
```

Returns a Python object appropriate for the file type:

| File type | Returned as |
|-----------|-------------|
| CSV | `pandas.DataFrame` |
| JSON | `list` or `dict` |
| Parquet | `pandas.DataFrame` |
| HuggingFace Dataset | `datasets.Dataset` |

### Inspecting the inventory

```python
# List all registered datasets
entries = manager.list_registered()

# Get metadata for one dataset
meta = manager.get_metadata("labeled-extraction-v2")
```

---

## Supported file types

- **CSV** (`.csv`) — loaded with `pandas.read_csv`
- **JSON** (`.json`) — loaded with `json.load`
- **Parquet** (`.parquet`) — loaded with `pandas.read_parquet`
- **HuggingFace Datasets** — loaded with `datasets.load_from_disk`

---

## Example: loading a dataset inside a scenario

```python
from adgtk.data import DatasetManager
from adgtk.factory import SupportsFactory


class MyScenario(SupportsFactory):
    factory_id = "my-scenario"
    group = "scenario"
    summary = "Example scenario using DatasetManager"
    tags = ["example"]

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        self.dm = DatasetManager()

    def run_scenario(self, result_folders):
        dataset = self.dm.load(self.dataset_id)
        # dataset is a pandas DataFrame for CSV files
        for _, row in dataset.iterrows():
            ...
```
