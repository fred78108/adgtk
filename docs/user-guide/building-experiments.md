# Building Experiments

An **experiment definition** is a YAML file in your project's `blueprints/` directory. It specifies which scenario to run and how to configure it. You can create one interactively with `adgtk build` or write it by hand.

---

## Interactive builder

From within your project directory:

```bash
adgtk build
```

Or pass a name directly:

```bash
adgtk build my-experiment
```

The wizard walks you through:

1. **Description** — used in reports and the results registry
2. **Scenario selection** — lists all `scenario` components registered in the factory
3. **Attribute configuration** — runs the scenario's `interview_blueprint`, prompting for each constructor argument; nested factory components (declared with `expand_field`) are configured recursively

The questions, help text, defaults, and valid choices shown in step 3 are all defined by the scenario author via `interview_blueprint`. See [Creating Scenarios](creating-scenarios.md#defining-the-interview-blueprint) for how to write one.

When finished, the definition is saved to `blueprints/my-experiment.exp.yaml`.

---

## Experiment YAML format

```yaml
description: "Compare chain-of-thought vs zero-shot on extraction"
attribute: ExtractionEvalScenario
factory_id: extraction-eval
factory_init: true
init_config:
  model: gpt-4o
  temperature: 0.7
  dataset_id: labeled-extraction-v2
  evaluator:
    attribute: evaluator
    factory_id: exact-match-evaluator
    factory_init: true
    init_config: {}
```

The experiment name is the blueprint filename without the `.yaml` extension. For example, `blueprints/exp.1.2.yaml` defines an experiment named `exp.1.2`.

### Top-level fields

| Field | Description |
|-------|-------------|
| `description` | Free-text description included in reports |
| `attribute` | Class name (informational — not used at runtime) |
| `factory_id` | ID used to look up and instantiate the scenario in the factory |
| `factory_init` | Always `true` for factory-managed components |
| `init_config` | Key-value pairs passed to `__init__` |

### Nested components

When a constructor argument is itself a factory-registered component, it appears as a nested object in `init_config`:

```yaml
init_config:
  prompt_template:
    attribute: prompt_template
    factory_id: chain-of-thought-template
    factory_init: true
    init_config:
      max_examples: 3
```

ADGTK will instantiate `chain-of-thought-template` via the factory and pass the result as the `prompt_template` argument.

---

## Running an experiment

```bash
adgtk run                  # prompts you to select
adgtk run my-experiment    # run directly by name
```

ADGTK will:

1. Load and validate the YAML definition
2. Run `bootstrap.py` to populate the factory
3. Instantiate the scenario (recursively instantiating nested components)
4. Call `run_scenario(result_folders)`
5. Write the full config snapshot, manifest, and report to `results/{run_id}/`

---

## Listing experiments

```bash
adgtk list
```

Shows all YAML files in `blueprints/` with their names and descriptions.

---

## Editing a definition

Just open the YAML file directly — it's plain text. Re-run with `adgtk run` after saving. The previous run's config snapshot is preserved in `results/{run_id}/run.exp.config.yaml`, so you always know what was used for any given run even after the blueprint changes.

---

## Tips for reproducibility

- **Commit your blueprints** to version control alongside code changes.
- **Use tags** in `RunResultBuilder` to label the key variables you're sweeping — they become columns when you export results.
