# Bootstrap Configuration

`bootstrap.py` is the entry point for registering custom components into the factory. It runs automatically every time `adgtk`, `adgtk-batch`, `adgtk-factory`, or `adgtk-results` is invoked from within a project directory.

---

## Default bootstrap.py

When you run `adgtk-project create`, the generated `bootstrap.py` looks like this:

```python
"""bootstrap.py

This script is your startup script. Use this to load your custom code
into the factory.
"""

import adgtk.factory.component as factory
from adgtk.examples.scenario import HelloWorldScenario


def foundation():
    """Built-in components that should not be removed unless you are
    replacing them with another. Loss of these will impact overall operations.
    """
    pass
    # factory.register()


def builtin():
    """Optional built-in components that can be removed if desired."""
    factory.register(HelloWorldScenario)


def user_code():
    pass
    # factory.register()
```

The framework calls `foundation()`, `builtin()`, and `user_code()` in that order on startup. Add your own `register_to_factory` calls inside `user_code()` — or replace the `builtin()` body entirely once you no longer need `HelloWorldScenario`.

---

## Registering components

Import your classes and call the appropriate registration function:

```python
from adgtk.factory import register_to_factory
from adgtk.measurements import register_to_measurement_factory

# Scenarios
from scenarios.extraction_eval import ExtractionEvalScenario
from scenarios.summarization_eval import SummarizationEvalScenario

register_to_factory(ExtractionEvalScenario)
register_to_factory(SummarizationEvalScenario)

# Custom measurements
from measurements.rouge_score import RougeScoreMeasurement
from measurements.exact_match import ExactMatchMeasurement

register_to_measurement_factory(RougeScoreMeasurement)
register_to_measurement_factory(ExactMatchMeasurement)
```

Alternatively, use the decorator form directly in your class files and just import the modules:

```python
# bootstrap.py
import scenarios.extraction_eval    # decorator runs on import
import scenarios.summarization_eval
import measurements.rouge_score
import measurements.exact_match
```

---

## Load order

On startup the framework imports `bootstrap.py` and calls its three hooks in order:

1. `foundation()` — framework-level registrations that must always be present
2. `builtin()` — optional built-in components (ships with `HelloWorldScenario`)
3. `user_code()` — your project-specific registrations

This happens before:

- Building the scenario list in `adgtk build`
- Instantiating a scenario in `adgtk run`
- Listing components in `adgtk-factory list`
- Any batch run step

The factory is fully populated by the time any of these operations run.

---

## Multiple registration files

For larger projects, split registration across files and import them all from `bootstrap.py`:

```python
# bootstrap.py
import project.register_scenarios
import project.register_measurements
import project.register_evaluators
```

Each sub-file handles its own imports and `register_to_factory` calls.

---

## Verifying registration

After editing `bootstrap.py`, verify your components are registered:

```bash
adgtk-factory list
adgtk-factory list scenario
adgtk-factory list measurement
```

If a component doesn't appear, check:

1. The import in `bootstrap.py` is correct
2. The class declares `factory_id`, `group`, `summary`, and `tags`
3. `register_to_factory(MyClass)` was called (or the decorator is present)
