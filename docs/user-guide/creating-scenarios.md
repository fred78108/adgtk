# Creating Scenarios

A **scenario** is the unit of work in ADGTK. It defines what happens during a run: what agents are called, how outputs are evaluated, and what results are returned. You write scenarios as Python classes.

---

## Minimal scenario

```python
from adgtk.factory import SupportsFactory
from adgtk.experiment.result import RunResultBuilder, register_to_factory
from adgtk.tracking import ObservationWriter

@register_to_factory
class MyScenario(SupportsFactory):
    factory_id = "my-scenario"
    group = "scenario"
    summary = "A one-line description shown in adgtk-factory list"
    tags = ["example"]

    def __init__(self):
        pass

    def run_scenario(self, result_folders):
        result = RunResultBuilder()
        obs = ObservationWriter("my-scenario")

        obs.note("Starting run")
        # ... your experiment logic ...
        result.mark_pass()
        return result.finalize()
```

In your bootstrap.py you ensure MyScenario is imported. Using the decorator @register_to_factory ensures that the Scenario is available to ADGTK for running based on a blueprint.

---

## Required class attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `factory_id` | `str` | Unique identifier used in experiment YAML and factory lookups |
| `group` | `str` | Logical group — use `"scenario"` for runnable scenarios |
| `summary` | `str` | One-line description displayed by `adgtk-factory list` |
| `tags` | `list[str]` | Labels for filtering in `adgtk-factory list --tags` |

---

## The `run_scenario` method

```python
def run_scenario(self, result_folders: ExperimentRunFolders) -> RunResult:
    ...
```

`result_folders` gives you paths to the run's output directories:

| Attribute | Path |
|-----------|------|
| `result_folders.metrics` | `results/{run_id}/metrics/` |
| `result_folders.datasets` | `results/{run_id}/datasets/` |
| `result_folders.images` | `results/{run_id}/images/` |
| `result_folders.other` | `results/{run_id}/other/` |
| `result_folders.conclusion` | `results/{run_id}/conclusion/` |

Pass `result_folders` to `tracker.save_data()` and `engine.save_data()` to write metric CSVs to the right place.

---

## Registering your scenario

Add it to `bootstrap.py` in your project:

```python
from adgtk.factory import register_to_factory
from scenarios.my_scenario import MyScenario

register_to_factory(MyScenario)
```

You can also use the decorator form:

```python
from adgtk.factory import register_to_factory

@register_to_factory
class MyScenario(SupportsFactory):
    ...
```

After registering, `adgtk-factory list scenario` will show your scenario and `adgtk build` will let you select it.

---

## Constructor arguments and experiment YAML

Arguments to `__init__` become configurable attributes in the experiment YAML. When you run `adgtk build` and select your scenario, ADGTK runs an interactive interview to collect each value. The `interview_blueprint` class attribute controls exactly what that interview asks.

```yaml
factory_id: my-scenario
init_config:
  model: gpt-4o
  temperature: 0.7
  dataset_id: my-dataset
  evaluator:
    factory_id: my-evaluator
    factory_init: true
    init_config: {}
```

---

## Defining the interview blueprint

The `interview_blueprint` is a list of `BlueprintQuestion` objects — one per `__init__` argument you want to configure interactively. The `attribute` in each question must match the parameter name in `__init__` exactly.

```python
from adgtk.factory import BlueprintQuestion, SupportsFactory
```

### Scalar fields

Use the named classmethods to avoid spelling the entry type as a raw string:

```python
interview_blueprint = [
    BlueprintQuestion.str_field("dataset_id", "Dataset ID to evaluate against?"),
    BlueprintQuestion.int_field("max_samples", "Maximum number of samples to run?"),
    BlueprintQuestion.float_field("temperature", "Sampling temperature?"),
    BlueprintQuestion.bool_field("verbose", "Enable verbose logging?"),
]
```

### Hints, defaults, and constraints

Every field accepts `helper` (shown as a tooltip during the interview), `default_value`, and for numeric fields `min_value` / `max_value`:

```python
interview_blueprint = [
    BlueprintQuestion.float_field(
        "temperature",
        "Sampling temperature?",
        helper="lower values reduce variance; 0.0 is fully deterministic",
        default_value=0.7,
        min_value=0.0,
        max_value=2.0,
    ),
    BlueprintQuestion.int_field(
        "max_samples",
        "Maximum samples per run?",
        helper="use -1 for the full dataset",
        default_value=100,
        min_value=-1,
    ),
]
```

### Restricting to a fixed set of choices

Pass `choices` to limit the researcher to a specific list of values:

```python
interview_blueprint = [
    BlueprintQuestion.str_field(
        "model",
        "Which model?",
        choices=["gpt-4o", "gpt-4o-mini", "o3"],
        default_value="gpt-4o",
    ),
]
```

### Nested factory components

When a constructor argument is itself a factory-registered component, use `expand_field`. The `group` argument is the factory group to list — the researcher picks from whatever is registered in that group at build time:

```python
interview_blueprint = [
    BlueprintQuestion.expand_field(
        "agent",
        "Which agent should perform the extraction?",
        group="agent",
    ),
    BlueprintQuestion.expand_field(
        "evaluator",
        "Which evaluator should score the outputs?",
        group="evaluator",
    ),
]
```

`expand_field` triggers a recursive interview for whichever component the researcher selects, so nested configuration is handled automatically.

### Lists

Use the `list_*` variants to collect multiple values for a single argument. The interview always captures at least one entry, then asks whether to add more:

```python
interview_blueprint = [
    BlueprintQuestion.list_str_field(
        "tags",
        "Add a tag for this run (enter one at a time)?",
    ),
    BlueprintQuestion.list_expand_field(
        "evaluators",
        "Add an evaluator?",
        group="evaluator",
    ),
]
```

### Multi-line text

For prompts, instructions, or other long free-form text, use `ml_string_field`. The interview opens a multi-line editor:

```python
interview_blueprint = [
    BlueprintQuestion.ml_string_field(
        "system_prompt",
        "Enter the system prompt for this scenario?",
    ),
]
```

### Using EntryType directly

If the classmethods don't cover a combination you need, you can construct `BlueprintQuestion` directly. Import `EntryType` for IDE autocompletion on the `entry_type` field:

```python
from adgtk.factory import BlueprintQuestion, EntryType

BlueprintQuestion(
    attribute="mode",
    question="Operating mode?",
    entry_type=EntryType.STR,
    choices=["fast", "thorough"],
    default_value="fast",
    helper="fast skips secondary validation",
)
```

---

## Full example

```python
import time
from adgtk.factory import BlueprintQuestion, SupportsFactory
from adgtk.experiment.result import RunResultBuilder
from adgtk.tracking import MetricTracker, ObservationWriter


class ExtractionEvalScenario(SupportsFactory):
    factory_id = "extraction-eval"
    group = "scenario"
    summary = "Evaluate an extraction agent on a labeled dataset"
    tags = ["extraction", "eval"]

    interview_blueprint = [
        BlueprintQuestion.expand_field(
            "agent",
            "Which agent should perform the extraction?",
            group="agent",
        ),
        BlueprintQuestion.str_field(
            "dataset_id",
            "Dataset ID to evaluate against?",
        ),
        BlueprintQuestion.str_field(
            "model",
            "Which model?",
            choices=["gpt-4o", "gpt-4o-mini", "o3"],
            default_value="gpt-4o",
        ),
        BlueprintQuestion.float_field(
            "temperature",
            "Sampling temperature?",
            helper="lower values reduce variance; 0.0 is fully deterministic",
            default_value=0.7,
            min_value=0.0,
            max_value=2.0,
        ),
    ]

    def __init__(self, agent, dataset_id: str, model: str = "gpt-4o", temperature: float = 0.7):
        self.agent = agent
        self.dataset_id = dataset_id
        self.model = model
        self.temperature = temperature

    def run_scenario(self, result_folders):
        result = RunResultBuilder()
        obs = ObservationWriter("extraction-eval", tags=["extraction"])

        result.tag("model", self.model)
        result.tag("temperature", self.temperature)

        obs.config_note("model", self.model, "Model under evaluation")
        obs.config_note("temperature", self.temperature, "Set low to reduce variance")

        tracker = MetricTracker(name="eval", purpose="measurement")
        tracker.register_metric("accuracy")
        tracker.register_metric("latency_ms")

        dataset = self.agent.load_dataset(self.dataset_id)

        for step, item in enumerate(dataset):
            t0 = time.monotonic()
            response = self.agent.extract(item["text"], model=self.model, temperature=self.temperature)
            elapsed_ms = (time.monotonic() - t0) * 1000

            obs.agent_turn(
                prompt=item["text"],
                response=str(response),
                model=self.model,
                latency_ms=elapsed_ms,
            )

            score = 1.0 if response == item["expected"] else 0.0
            tracker.add_data("accuracy", score)
            tracker.add_data("latency_ms", elapsed_ms)

        tracker.save_data(result_folders)

        accuracy = tracker.get_average("accuracy")
        result.set("accuracy_mean", accuracy)
        result.set("latency_ms_mean", tracker.get_average("latency_ms"))
        result.set("n", tracker.measurement_count("accuracy"))

        result.pass_if(
            lambda m: m["accuracy_mean"] >= 0.85,
            on_fail=f"accuracy {accuracy:.3f} below 0.85 threshold",
        )
        result.summarize(f"{self.model} extraction eval: accuracy={accuracy:.3f}")

        return result.finalize()
```
