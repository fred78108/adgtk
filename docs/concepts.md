# Concepts

This page explains the core ideas in ADGTK. Reading it first will make the rest of the documentation much easier to follow.

---

## The factory

The **factory** is a runtime registry of named components. Every scenario, measurement, and other pluggable component has a `factory_id` string. When ADGTK needs to instantiate something, it asks the factory for that ID.

```python
# Register at startup
from adgtk.factory import register_to_factory

@register_to_factory
class MyScenario(SupportsFactory):
    factory_id = "my-scenario"
    group = "scenario"
    ...
```

Then import the MyScenario in your bootstrap.py to make this scenario available for use within ADGTK.

The factory is **non-persistent** — it starts empty each time the process starts, and `bootstrap.py` refills it. This means you can change what's registered without touching any config files; just edit `bootstrap.py`.

The experiment builder (`adgtk build`) reads the factory to show you what's available. The runner (`adgtk run`) reads it to instantiate the correct scenario from a saved definition.

---

## Experiments

An **experiment** is defined in a YAML file stored in `blueprints/`. It captures:

- which scenario to run (by `factory_id`)
- the arguments to pass when constructing it
- nested attributes that may themselves be factory-created components

```yaml
description: Comparing prompt variants on extraction
factory_id: my-scenario
factory_init: true
init_config:
  model: gpt-4o
  prompt_variant:
    attribute: prompt_variant
    factory_id: prompt-cot
    factory_init: true
    init_config: {}
```

The experiment name is the blueprint filename without the `.yaml` extension — e.g. `blueprints/my-experiment.yaml` defines an experiment named `my-experiment`. You create this file interactively with `adgtk build`, or write it by hand. The file is the reproducibility record: running the same YAML on the same code and data should produce comparable results. When running an experiment the specific configuration used (to include defaults) is written to run.exp.config.yaml in the run folder.

---

## Scenarios

A **scenario** is a Python class that implements the actual experiment logic. It must:

1. Inherit from `SupportsFactory` (or implement `ScenarioProtocol`)
2. Declare `factory_id`, `group`, `summary`, and `tags` as class attributes
3. Implement `run_scenario(result_folders) -> RunResult`

Everything that happens during a run lives inside `run_scenario`. It records observations, calls agents, evaluates outputs, and returns a `RunResult`.

---

## Runs

Each time you call `adgtk run`, ADGTK creates a **run** — a numbered folder for tracking the results of one experiment. Runs are:

- Registered in `.tracking/runs.json`
- Written to `results/{run_id}/`

Every run produces a full config snapshot, observations, metrics, and a markdown report — regardless of whether it passed or failed.

---

## Observations

`ObservationWriter` is your lab journal for a run. Instantiate one with a component name and call it from inside `run_scenario` to record what happened:

```python
from adgtk.tracking import ObservationWriter

obs = ObservationWriter("my-component")
```

| Method | Purpose |
|--------|---------|
| `obs.note(message)` | General finding or comment |
| `obs.warn(message)` | Unexpected or anomalous event |
| `obs.agent_turn(prompt, response, ...)` | Full prompt/response pair with token counts and latency |
| `obs.config_note(parameter, value, rationale)` | Why you chose a config value |
| `obs.metric_event(metric, value, step, note)` | Annotate a point on a metric series |

Every observation is automatically tagged with `component:<name>`, so reports stay readable when multiple subsystems contribute entries. Observations are collected in memory and written to `run.manifest.json` and `report.md` at the end of the run.

See [Tracking & Results](tracking-results.md) for full details.

---

## Results

A **RunResult** is the structured summary your scenario returns. It contains:

- `metrics` — scalar measurements (accuracy, F1, etc.)
- `verdict` — `"pass"`, `"fail"`, or `"inconclusive"`
- `tags` — key-value labels for cross-run comparison
- `summary` — a free-text description of the run

Build it with `RunResultBuilder` for longer runs, or construct `RunResult` directly for simple scenarios.

Tags are especially important: they are exported as columns when you run `adgtk-results export`, making it easy to compare runs in a notebook.

---

## The manifest

Every run produces a `run.manifest.json` — a canonical JSON document that aggregates everything: timing, verdict, tags, result metrics, metric time-series summaries, all observations, and the config snapshot. It is the source of truth for a run. The markdown `report.md` is generated automatically from it.

---

## Studies

A **study** is a named collection of experiments whose results you want to compare side-by-side. Where an experiment rollup (`adgtk report`) looks across all runs *of the same blueprint*, a study looks across *different* blueprints — for example, the same task run with two different models.

Studies are defined in YAML files stored in `studies/` (created with `adgtk-study build`) and produce output in `study-results/`. Each study report pulls the configuration from the first run of each experiment, then recalculates all statistics fresh from the stored manifests.

See [Studies](user-guide/studies.md) for a step-by-step guide.

---

## Putting it together

```
bootstrap.py      ← registers components into the factory at startup
blueprints/       ← experiment YAML definitions (created by `adgtk build`)
    my-exp.yaml
studies/          ← study YAML definitions (created by `adgtk-study build`)
    my-study.yaml

adgtk run my-exp          ← runner loads YAML, instantiates scenario, calls run_scenario()
adgtk-study run my-study  ← collects manifests across experiments, generates rollup

results/
  1.my-exp/
    run.exp.config.yaml    ← the exact YAML used
    conclusion/
      run.manifest.json    ← all structured data
      report.md            ← human-readable summary
      results.yaml         ← quick-reference RunResult
    metrics/
      eval.accuracy.csv    ← one CSV per MetricTracker label
study-results/
  my-study/
    study_report.md        ← cross-experiment markdown report
    study_results.csv      ← combined CSV, one row per run
```
