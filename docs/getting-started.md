# Getting Started

## Requirements

- Python 3.12 or later
- A virtual environment (strongly recommended)

## Installation

```bash
pip install adgtk
```

### Install from source

```bash
git clone https://github.com/fred78108/adgtk
cd adgtk
python -m pip install -e .
```

---

## Create your first project

`adgtk-project create` scaffolds a new project directory with everything ADGTK needs:

```bash
adgtk-project create my-research
cd my-research
```

The project directory contains:

```
my-research/
  bootstrap.py        # register your custom components here
  results/            # run results land here
  logs/
    runs/
  .tracking/
    runs.json         # run registry
    datasets.json     # dataset inventory (managed by adgtk-ds)
  blueprints/         # experiment YAML definitions
  batches/            # batch job definitions
```

### Optional: install the IDE skill

ADGTK ships a skill file that gives your AI-powered IDE full knowledge of the framework — scenarios, blueprints, observations, and logging — so you can describe what you want to build without explaining ADGTK syntax.

```bash
# Claude Code (default — installs to .claude/skills/)
adgtk-project install-skills

# Cursor
adgtk-project install-skills --output-dir .cursor/rules

# Windsurf
adgtk-project install-skills --output-dir .windsurf/rules
```

This copies `adgtk.md` into the target directory. How you invoke it depends on your IDE:

| IDE | Invocation |
|-----|-----------|
| Claude Code | `/adgtk` |
| Cursor | `@adgtk` in the chat |
| Windsurf | `@adgtk` in the chat |

**Pairing the skill with the MCP server**

The skill and the MCP server cover different parts of your workflow and work well together:

- Use the **skill** while writing code — it scaffolds scenarios, observations, and logging from your intent without you needing to know the API.
- Use the **MCP server** to drive the experiment loop — run experiments, inspect results, and generate reports conversationally without touching the CLI.

See [MCP Server](mcp-server.md) for setup instructions.

---

## Run the built-in Hello World scenario

ADGTK ships with a `hello-world` scenario you can run without writing any code. Use the interactive experiment builder to create a definition for it:

```bash
adgtk build
```

The wizard asks for a name and description, then lets you select a scenario from the factory. Choose `hello-world`. Accept the defaults and save.

Now run it:

```bash
adgtk run
```

Select the experiment you just built. To run it multiple times in one command, pass `--n`:

```bash
adgtk run --n 5          # run 5 times after a single interactive selection
adgtk run hello-world --n 10
```

ADGTK will:

1. Load `bootstrap.py` to register all components
2. Instantiate the `hello-world` scenario via the factory
3. Call `run_scenario()` on it
4. Write results, manifest, and report to `results/{run_id}/`

When it finishes:

```bash
adgtk-results list
```

You'll see one run logged per execution. To read the auto-generated per-run report:

```bash
cat results/1.hello-world/conclusions/report.md
```

After accumulating multiple runs, generate a rollup report across all of them:

```bash
adgtk report hello-world
```

This writes `results/hello-world/experiment_report.md` (verdict distributions, timing stats, per-run table, and a config-consistency warning if any run deviated from the baseline) and `results/hello-world/common/results.csv` for notebook analysis.

---

## Write your first scenario

Create a file in your project — e.g. `scenarios/my_scenario.py`:

```python
from typing import ClassVar
from adgtk.factory import SupportsFactory
from adgtk.experiment.result import RunResultBuilder
from adgtk.tracking import ObservationWriter


class MyFirstScenario(SupportsFactory):
    factory_id: ClassVar[str] = "my-first-scenario"
    group: ClassVar[str] = "scenario"
    summary: ClassVar[str] = "A minimal custom scenario"
    tags: ClassVar[list[str]] = ["example"]

    def __init__(self, greeting: str = "hello"):
        self.greeting = greeting

    def run_scenario(self, result_folders):
        result = RunResultBuilder()
        obs = ObservationWriter("my-first-scenario")

        obs.note(f"Running with greeting: {self.greeting}")
        obs.note("Scenario completed successfully")

        result.set("greeting_length", len(self.greeting))
        result.mark_pass()
        result.summarize(f"Completed with greeting '{self.greeting}'")

        return result.finalize()
```

Register it in `bootstrap.py`:

```python
from adgtk.factory import register_to_factory
from scenarios.my_scenario import MyFirstScenario

register_to_factory(MyFirstScenario)
```

Now build an experiment that uses it:

```bash
adgtk build
```

Select `my-first-scenario` from the factory list. Configure the `greeting` attribute when prompted. Run it:

```bash
adgtk run
```

---

## Next steps

- **[Concepts](concepts.md)** — understand factories, experiments, observations, and results
- **[Creating Scenarios](user-guide/creating-scenarios.md)** — full guide to writing scenario classes
- **[Tracking & Results](tracking-results.md)** — recording observations and metrics during a run
- **[CLI Reference](cli-reference.md)** — every available command, including `adgtk-ds` for dataset management
