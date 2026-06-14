# Agentic Data Generation Toolkit
Agentic Data Generation Toolkit for all your Agentic experimentation needs. The goal of this package is to focus on researching and validating agentic systems.

## History and Future direction
Agentic Data Generation Toolkit started with a narrow focus. The goal was to address a need to support my research with Agents that create data in support of my dissertation. I needed the ability to automate testing of agents with an eye towards reproducibility along with confidence in the resulting performance. Versions 0.2.1 and below were focused on supporting this need. After completing my dissertation I realized a gap still exists and a strong desire to continue to refine this project for my future research and work. In addition, and more importantly I hope this benefits others in their research with Agentic systems. 

Starting with Version 0.3 the goal is to introduce capabilities that not only ease use but also expand Agentic testing scenarios. This is a major rewrite of the package and the first step beyond my original scope to a package that eases your research. I'm starting with those lessons learned from using ADGTK for a complex research project then expanding into "wouldn't it be cool if" ideas over the next series of releases.


## Highlights

- A "lab journal" which can be invoked through an experiment.
- Per-run reports saved to disk automatically at the end of every run.
- Experiment rollup reports (`adgtk report`) aggregate metrics, verdicts, and timing across all runs — with a config-consistency warning when runs deviate from the baseline configuration.
- **Study reports** (`adgtk-study run`) roll up results *across* experiments — compare two models, two prompting strategies, or two datasets in a single markdown report and combined CSV.
- **`AgentWriter`** — a TensorBoard-style runtime metric writer for agentic runs. Track latency per step, token usage, tool call distribution, task success, retry count, and path efficiency with a simple three-call API (`log_step` / `log_outcome` / `save`).
- **Built-in measurements** — nine registered measurement functions covering string similarity (`exact_match`, `token_f1`, `json_valid`), dictionary structure (`dict_schema_match`, `schema_key_depth`), and list consistency — all usable directly from `MeasurementEngine` without any setup.
- Extensible architecture. The framework is designed to be extensible on load and during execution.
- **Web interface** (`adgtk-web`) — a browser-based UI for running experiments, browsing results, and managing studies. Supports remote access and Jupyter-style token authentication.

## Package structure

The codebase is organized around five primary modules and two supporting ones:

| Module | Purpose |
|--------|---------|
| `adgtk.cli` | Seven CLI entry points and bootstrap infrastructure |
| `adgtk.mcp_server` | MCP server — exposes project operations as tools for AI agents |
| `adgtk.api` | Web interface — browser-based UI served by FastAPI + HTMX |
| `adgtk.experiment` | Definitions, builder, runner, results, and study rollups (`experiment.study`) |
| `adgtk.tracking` | Observations, metrics, manifests, reports, and dataset file tracking |
| `adgtk.measurements` | `AgentWriter` (runtime metrics), `MeasurementEngine` (dataset evaluation), registry, and nine built-in measurement functions |
| `adgtk.utils` | Shared utilities — CLI helpers, logging, defaults, exceptions |
| `adgtk.factory` | Component registration and instantiation registry |
| `adgtk.data` | Dataset loading and management |
| `adgtk.examples` | Reference implementations — `HelloWorldScenario` |

## Installation

### Via PyPi

To install the package, you can use pip:

```console
pip install adgtk
```

### Manual installation from source

If you wish to clone the repository and install the package manually, you can do so by following these steps:

1. Activate your virtual environment.
2. Download the project from https://github.com/fred78108/adgtk.
3. From the root folder of adgtk, run the following command:

```console
(.venv) $ python -m pip install -e .
```

This will let you modify your copy of adgtk and evaluate the results. This is useful for development of your own version of adgtk.

## Usage

### Command structure

ADGTK provides focused CLI tools, each with a clear scope:

| Command | Requires project? | Purpose |
|---|---|---|
| `adgtk-project` | No | Scaffold and discover projects |
| `adgtk` | Yes | Run, build, and list experiments |
| `adgtk-batch` | Yes | Batch job management |
| `adgtk-factory` | Yes | Inspect registered components |
| `adgtk-results` | Yes | Results inventory and management |
| `adgtk-study` | Yes | Cross-experiment study rollup reports |
| `adgtk-mcp` | Yes | MCP server for AI agent access |
| `adgtk-web` | Yes | Browser-based web interface |

`adgtk-project` is safe to run from anywhere. The remaining commands must be run from within a project directory (one containing `bootstrap.py` and a `results/` folder).

---

### adgtk-project

Manage projects. Does not require an existing project context.

```console
adgtk-project create <name>   # Scaffold a new project folder
adgtk-project list            # List projects in the current directory
adgtk-project info            # Show status of the current directory
adgtk-project install-skills  # Install the ADGTK IDE skill (optional)
```

**Example — create and enter a project:**

```console
$ adgtk-project create my-research
Successfully created: my-research
  cd my-research
  adgtk list       # list experiments
  adgtk build      # build a new experiment

$ cd my-research
```

---

### adgtk

The primary in-project tool for experiments. Running with no arguments shows the experiment list.

```console
adgtk list                    # List available experiments
adgtk build [name]            # Build a new experiment definition (interactive wizard)
adgtk run [name]              # Run an experiment (prompts for selection if name is omitted)
adgtk run [name] --n N        # Run an experiment N times without a batch file
adgtk report [name]           # Generate a rollup report across all runs of an experiment
adgtk copy [source] [dest]    # Copy a blueprint under a new name
```

**Examples:**

```console
$ adgtk list
$ adgtk build
$ adgtk build exp1
$ adgtk run
$ adgtk run exp1
$ adgtk run exp1 --n 20       # run exp1 twenty times in sequence
$ adgtk run --n 5             # interactive selection, then 5 runs
$ adgtk report exp1           # rollup report + results CSV for exp1
$ adgtk copy exp1 exp1-v2     # copy blueprint exp1 to exp1-v2
$ adgtk copy                  # interactive: pick source then enter new name
```

`adgtk report` writes `results/{experiment}/experiment_report.md` (verdict distributions, timing, per-run table, cross-run metric statistics, and a config-consistency warning if any run deviated from the baseline) and `results/{experiment}/common/results.csv` for use in notebooks.

---

### adgtk-batch

Manage and run batch jobs (sets of experiments defined in a YAML file).

```console
adgtk-batch list          # List available batch job definitions
adgtk-batch run <name>    # Run a batch job
adgtk-batch preview <name>  # Preview a batch job (coming soon)
adgtk-batch create <name>   # Create a batch job definition (coming soon)
```

**Example:**

```console
$ adgtk-batch list
$ adgtk-batch run nightly-suite
```

---

### adgtk-factory

Inspect components registered in the factory.

```console
adgtk-factory list                      # List all registered components
adgtk-factory list <group>              # Filter by group
adgtk-factory list <group> --tags t1   # Filter by group and tags
```

**Examples:**

```console
$ adgtk-factory list
$ adgtk-factory list scenario
$ adgtk-factory list scenario --tags builtin
```

---

### adgtk-results

Results inventory and management. Tracks every experiment run, checks disk integrity, and provides purge operations for storage cleanup.

Run results are registered automatically each time `adgtk run` or `adgtk-batch run` completes. The registry lives in `.tracking/runs.json`.

> **First-time setup:** If you have existing results from before upgrading to 0.3, run `adgtk-results sync` once to backfill the registry from the `results/` folder.

#### Inspection

```console
adgtk-results list                        # All experiments: run count, last run, status
adgtk-results list <experiment>           # All runs for one experiment with duration
adgtk-results show <experiment> <run_id>  # Print results.yaml and run config for a run
adgtk-results validate                    # Report orphaned folders, incomplete and missing runs
adgtk-results disk-usage                  # Disk usage for all experiments
adgtk-results disk-usage <experiment>     # Per-run disk usage for one experiment
```

**Example — overview:**

```console
$ adgtk-results list

Experiment                Runs    Last Run                Status
================================================================
baseline                    5    2025-04-10 14:22:01    OK
exp.1.0                    12    2025-04-18 09:05:44    1 incomplete
exp.2.0                     3    2025-04-20 11:30:12    OK
```

**Example — drill into one experiment:**

```console
$ adgtk-results list exp.1.0

Run                            Status            Duration    Started
====================================================================
11.exp.1.0                     complete           4m 12s    2025-04-18 09:05:44
10.exp.1.0                     incomplete             --    2025-04-17 22:01:03
9.exp.1.0                      complete           3m 58s    2025-04-17 15:44:21
```

#### Maintenance

```console
adgtk-results sync                           # Register any on-disk runs missing from the registry
adgtk-results prune <experiment> --keep N    # Delete oldest runs, keeping N most recent
adgtk-results prune <experiment> --keep N -y # Skip confirmation prompt
```

Sync uses the folder modification time as the run timestamp and marks runs as `complete` or `incomplete` based on whether `results.yaml` is present.

#### Export

```console
adgtk-results export <experiment>              # Export all run results to JSON (stdout)
adgtk-results export <experiment> --format csv # Export as CSV
adgtk-results export <experiment> --output results.json  # Write to file
```

Each record includes run metadata (timestamps, duration, status) merged with the fields from that run's `results.yaml`.

#### Purge

Purge operations are destructive and prompt for confirmation unless `-y` is passed.

```console
adgtk-results purge run <experiment> <run_id>   # Delete one run's results folder and registry entry
adgtk-results purge run <experiment> <run_id> -y

adgtk-results purge experiment <experiment>     # Delete all results, logs, and registry entries
adgtk-results purge experiment <experiment> -y
```

`purge run` removes only the `results/` subfolder for that run — logs are shared across runs and are left intact. `purge experiment` removes the results folder **and** `logs/runs/<experiment>/`.

---

### adgtk-study

Cross-experiment study rollup reports. A **study** is a named collection of experiments whose results you want to compare side-by-side — e.g. the same task run with different models or prompt strategies.

Study blueprints are stored in `studies/` as YAML files. Output is written to `study-results/`.

```console
adgtk-study list              # List saved study blueprints
adgtk-study build [name]      # Create a new study blueprint (interactive)
adgtk-study run [name]        # Generate the study report and combined CSV
```

**Example workflow:**

```console
$ adgtk-study build
Study name: model-comparison
Description: GPT-4o vs Claude on the extraction task
Tags (optional): extraction
Available experiments (from results/):
    0 : exp-gpt4o
    1 : exp-claude
> 0,1
Save? [Y/n] Y
  Saved: studies/model-comparison.yaml

$ adgtk-study run model-comparison
  Report : study-results/model-comparison/study_report.md
  CSV    : study-results/model-comparison/study_results.csv
```

`adgtk-study run` writes two files to `study-results/{name}/`:

| File | Purpose |
|------|---------|
| `study_report.md` | Markdown report with cross-experiment overview table, per-experiment config (from first run), verdict/timing/metric/measurement statistics |
| `study_results.csv` | Combined CSV — one row per run across all experiments, ready for notebook analysis |

The combined CSV can be loaded directly into a notebook:

```python
import pandas as pd
df = pd.read_csv("study-results/model-comparison/study_results.csv")
df.groupby("experiment_name")["metric_accuracy"].mean()
```

---

### adgtk-mcp

Start an MCP server so Claude and other AI agents can run experiments, inspect results, and generate reports directly — without the CLI.

```console
adgtk-mcp --project-dir ~/research/my-project
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "adgtk": {
      "command": "adgtk-mcp",
      "args": ["--project-dir", "/absolute/path/to/project"]
    }
  }
}
```

The server exposes 15 tools covering experiments, batches, results, studies, factory components, and datasets. The full list is in the [MCP Server docs](docs/mcp-server.md).

---

### adgtk-web

Start a browser-based web interface for your project. Works over a network — point a browser at it from any machine.

```console
adgtk-web --project-dir ~/research/my-project
```

On startup the URL and token are printed to the console:

```
  ADGTK Web Interface
  http://127.0.0.1:8000/?token=a3f9c2d1...
```

**Common options:**

```console
adgtk-web --project-dir PATH              # Required: path to your ADGTK project
adgtk-web --project-dir PATH --port 8080  # Custom port
adgtk-web --project-dir PATH --no-auth    # Disable authentication (local dev only)
adgtk-web --project-dir PATH --token abc  # Use a fixed token instead of a random one
adgtk-web --host 0.0.0.0 --project-dir PATH  # Bind to all interfaces for remote access
```

The interface covers all major workflows: running experiments with live output streaming, browsing and exporting results, building and running studies, and inspecting registered factory components. See the [Web Interface docs](docs/web-interface.md) for the full reference.

