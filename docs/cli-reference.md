# CLI Reference

ADGTK provides nine focused CLI tools. Each has a clear scope, and only `adgtk-project` can be run from outside a project directory.

| Command | Requires project? | Purpose |
|---------|-------------------|---------|
| `adgtk-project` | No | Scaffold and discover projects |
| `adgtk` | Yes | Run, build, and list experiments |
| `adgtk-batch` | Yes | Batch job management |
| `adgtk-factory` | Yes | Inspect registered components |
| `adgtk-ds` | Yes | Dataset inventory management |
| `adgtk-results` | Yes | Results inventory and management |
| `adgtk-study` | Yes | Cross-experiment study rollup reports |
| `adgtk-mcp` | Yes | MCP server — expose project to AI agents |
| `adgtk-web` | Yes | Web interface — browser-based UI |

A **project directory** is any directory containing `bootstrap.py` and a `results/` folder, created by `adgtk-project create`.

---

## adgtk-project

Manage projects. Safe to run from anywhere.

```bash
adgtk-project create <name>            # Scaffold a new project folder
adgtk-project list                     # List projects in the current directory
adgtk-project info                     # Show status of the current directory
adgtk-project install-skills           # Install the ADGTK IDE skill (optional)
adgtk-project install-skills \
  --output-dir PATH                    # Install to a custom directory
```

### Examples

```bash
# Create and enter a project
adgtk-project create my-research
cd my-research

# Check if the current directory is a valid project
adgtk-project info

# Install the ADGTK skill for Claude Code (default)
adgtk-project install-skills

# Install for Cursor or Windsurf
adgtk-project install-skills --output-dir .cursor/rules
adgtk-project install-skills --output-dir .windsurf/rules
```

### IDE skill

`install-skills` copies `adgtk.md` into the target directory (default: `.claude/skills`). The skill gives your AI assistant full knowledge of ADGTK patterns — scenarios, blueprints, observations, and logging — so you can describe what you want to build rather than explaining the framework. Invoke it with `/adgtk` once installed.

---

## adgtk

The primary in-project command for experiments.

```bash
adgtk list                       # List available experiment definitions
adgtk build [name]               # Create an experiment definition (interactive)
adgtk run [name]                 # Run an experiment
adgtk run [name] --n N           # Run an experiment N times
adgtk report [name]              # Generate a rollup report across all runs
adgtk copy [source] [dest]       # Copy a blueprint under a new name
adgtk tasks list                 # List recent task records
adgtk tasks cleanup              # Remove all finished task records (prompts)
adgtk tasks cleanup --auto       # Apply TTL/count cleanup from settings.yaml
```

Running `adgtk` with no arguments shows the experiment list.

If `name` is omitted from `build`, `run`, or `report`, ADGTK prompts you to select from available experiments.

### `run` options

| Flag | Description |
|------|-------------|
| `--n N` | Number of times to run the experiment (default: `1`) |

### `copy` — duplicate a blueprint

`adgtk copy` copies an existing blueprint YAML to a new name. Both arguments are optional — ADGTK will prompt interactively for anything not supplied on the command line.

```bash
adgtk copy                            # fully interactive
adgtk copy my-experiment              # pick source; prompted for new name
adgtk copy my-experiment my-exp-v2   # non-interactive
```

The source must exist in `blueprints/`; the destination must not already exist. After copying, the new blueprint is immediately available for `adgtk run` and `adgtk build`.

### Examples

```bash
adgtk list
adgtk build                         # interactive name selection
adgtk build my-experiment           # name provided upfront
adgtk run                           # interactive selection, single run
adgtk run my-experiment             # run directly, single run
adgtk run my-experiment --n 20      # run the same experiment 20 times
adgtk run --n 5                     # interactive selection, then 5 runs
adgtk report my-experiment          # generate rollup report
adgtk report                        # interactive selection, then generate report
adgtk copy my-experiment my-exp-v2  # copy blueprint
adgtk copy                          # interactive copy
```

When `--n` is greater than 1, ADGTK prints `Run X of N` before each iteration so you can track progress. If no experiment name is given, the interactive prompt fires once and the selection is reused for all subsequent runs.

### `tasks` — manage task records

`adgtk tasks` provides visibility into and cleanup of the task records written to `.tracking/tasks/` by both the CLI and the web server (ADR-009).

```bash
adgtk tasks list                 # Print a table of recent task records
adgtk tasks cleanup              # Remove ALL finished records (prompts for confirmation)
adgtk tasks cleanup --auto       # Apply TTL + count policy from settings.yaml
```

`adgtk tasks list` shows the task ID, status, experiment name, and start time for the 50 most recent records.

`adgtk tasks cleanup` (without `--auto`) asks for confirmation before deleting all completed, error, and stopped task directories. Running tasks are never touched.

`adgtk tasks cleanup --auto` reads `tasks.ttl_days` and `tasks.max_count` from `settings.yaml` and runs the same two-pass cleanup as the web server startup: first removes tasks older than the TTL, then trims to the count cap. See [Web Interface — Settings](web-interface.md#settings) for how to configure these values.

### `report` — experiment rollup

`adgtk report` reads every run's `run.manifest.json` for an experiment and writes two output files:

| File | Location | Purpose |
|------|----------|---------|
| `experiment_report.md` | `results/{experiment}/` | Human-readable rollup report |
| `results.csv` | `results/{experiment}/common/` | Flat CSV with one row per run |

**What the report covers:**

- **Configuration consistency** — compares `run.exp.config.yaml` across all runs. Any run whose config differs from the majority baseline is listed in a prominent warning block and flagged with ⚠ in the per-run table.
- **Verdict distribution** — pass / fail / inconclusive / unknown counts with percentages
- **Status distribution** — complete / incomplete / failed counts
- **Timing** — total, average, std dev, min, and max run duration; first and last run timestamps
- **Per-run summary table** — one row per run with status, verdict, duration, and a snippet of the run's summary text
- **Result metrics** — per-run table plus cross-run statistics (n, mean, std, min, max) for every numeric metric
- **Measurement summaries** — per-run `mean (std)` and cross-run statistics for every `MetricTracker` / `MeasurementEngine` label
- **Tags** — distribution of each tag value across all runs
- **Skipped runs** — run folders that had no manifest (legacy format or interrupted runs)

**CSV columns:**

| Column group | Pattern | Description |
|---|---|---|
| Identity | `run_id`, `experiment_name` | Run identifiers |
| Timing | `timestamp_start`, `timestamp_end`, `duration_seconds` | When and how long |
| Outcome | `status`, `verdict`, `verdict_note` | Run outcome |
| Tags | `tag_<key>` | One column per tag key |
| Result metrics | `metric_<key>` | One column per `result.set()` key |
| Measurements | `meas_<label>_{n,mean,std,min,max}` | Five columns per `MetricTracker` label |

The CSV is designed to be loaded directly into a notebook for analysis:

```python
import pandas as pd
df = pd.read_csv("results/my-experiment/common/results.csv")
df.groupby("tag_prompt_variant")["metric_accuracy"].mean()
```

---

## adgtk-batch

Run sets of experiments defined in a YAML batch file stored in `batches/`.

```bash
adgtk-batch list              # List available batch definitions
adgtk-batch run <name>        # Run a batch job
adgtk-batch preview <name>    # Preview a batch job (coming soon)
adgtk-batch create <name>     # Create a batch definition (coming soon)
```

### Examples

```bash
adgtk-batch list
adgtk-batch run nightly-suite
```

See [Batch Jobs](advanced/batch-jobs.md) for the batch YAML format.

---

## adgtk-factory

Inspect components currently registered in the factory. Runs `bootstrap.py` first, so it reflects your actual registered components.

```bash
adgtk-factory list                          # List all registered components
adgtk-factory list <group>                  # Filter by group
adgtk-factory list <group> --tags <tag>     # Filter by group and tag
```

### Examples

```bash
adgtk-factory list
adgtk-factory list scenario
adgtk-factory list scenario --tags builtin
adgtk-factory list measurement --tags text
```

---

## adgtk-ds

Dataset inventory management. All commands must be run from inside a project directory. The inventory is stored in `.tracking/datasets.json`.

Any argument to `register` can be omitted — ADGTK will interview you for anything that is missing.

### Commands

```bash
adgtk-ds register                          # Fully interactive registration
adgtk-ds register --file PATH              # Provide file upfront; interview fills the rest
adgtk-ds register \
  --file PATH \
  --encoding csv \
  --use train                              # Non-interactive (all args supplied)
adgtk-ds report                            # Print the full inventory
adgtk-ds report <tag> [<tag> ...]          # Filter by one or more tags
adgtk-ds retire                            # Show inventory, then prompt for the ID
adgtk-ds retire --id <id>                  # Retire directly by ID
adgtk-ds find --filename <filename>        # Look up the ID assigned to a filename
```

### `register` options

| Flag | Short | Description |
|------|-------|-------------|
| `--file PATH` | `-f` | Path to the dataset file |
| `--encoding TYPE` | `-e` | File encoding (`csv`, `hf-json`, `json`, `pickle`, `pandas`, `text`) |
| `--use TYPE` | `-u` | Intended use: `train`, `test`, `validate`, or `other` (default: `other`) |
| `--metadata PATH` | `-m` | Path to a companion metadata file |
| `--id ID` | | Custom ID (auto-generated UUID if omitted) |

### Examples

```bash
# Fully interactive — ADGTK asks for everything
adgtk-ds register

# Provide the file upfront; ADGTK asks for encoding, use, and metadata
adgtk-ds register --file data/train.csv

# One-liner, no prompts
adgtk-ds register --file data/train.csv --encoding csv --use train

# View the full inventory
adgtk-ds report

# Show only entries tagged "train"
adgtk-ds report train

# Retire an entry — shows the inventory first so you can find the ID
adgtk-ds retire

# Look up an ID by filename
adgtk-ds find --filename train.csv
```

### How it works

`register` stores an entry in `.tracking/datasets.json` that maps a short ID to the file path, encoding, use category, and any tags. Scenarios and experiments reference datasets by ID rather than by path, so renaming or moving a file only requires updating the registry rather than every experiment definition.

`retire` removes the inventory entry. The file itself is not deleted.

---

## adgtk-results

Results inventory and management. All inspection commands read from `.tracking/runs.json`.

### Inspection

```bash
adgtk-results list                              # All experiments: run count, last run, status
adgtk-results list <experiment>                 # All runs for one experiment
adgtk-results show <experiment> <run_id>        # Print results + config for one run
adgtk-results validate                          # Check for orphaned folders and incomplete runs
adgtk-results disk-usage                        # Disk usage for all experiments
adgtk-results disk-usage <experiment>           # Per-run disk usage for one experiment
```

**Example — experiment overview:**

```
$ adgtk-results list

Experiment                Runs    Last Run                Status
================================================================
baseline                    5    2025-04-10 14:22:01    OK
exp.1.0                    12    2025-04-18 09:05:44    1 incomplete
exp.2.0                     3    2025-04-20 11:30:12    OK
```

**Example — runs for one experiment:**

```
$ adgtk-results list exp.1.0

Run                            Status            Duration    Started
====================================================================
12.exp.1.0                     complete           4m 12s    2025-04-18 09:05:44
11.exp.1.0                     incomplete             --    2025-04-17 22:01:03
10.exp.1.0                     complete           3m 58s    2025-04-17 15:44:21
```

### Maintenance

```bash
adgtk-results sync                            # Register on-disk runs missing from the registry
adgtk-results prune <experiment> --keep N     # Delete oldest runs, keeping N most recent
adgtk-results prune <experiment> --keep N -y  # Skip confirmation
```

`sync` is useful after upgrading from a version prior to 0.3, or after manually copying run folders. It uses folder modification time as the run timestamp and marks runs as `complete` or `incomplete` based on whether `results.yaml` is present.

### Export

```bash
adgtk-results export <experiment>                         # JSON to stdout
adgtk-results export <experiment> --format csv            # CSV to stdout
adgtk-results export <experiment> --output results.json   # Write to file
adgtk-results export <experiment> --format csv --output runs.csv
```

Each record includes run metadata merged with fields from `results.yaml`. Tags appear as columns, making it easy to load into a notebook:

```python
import pandas as pd
df = pd.read_csv("runs.csv")
df.groupby("prompt_variant")["accuracy_mean"].mean()
```

### Purge

Purge operations are destructive and prompt for confirmation unless `-y` is passed.

```bash
# Delete one run
adgtk-results purge run <experiment> <run_id>
adgtk-results purge run <experiment> <run_id> -y

# Delete all runs for an experiment
adgtk-results purge experiment <experiment>
adgtk-results purge experiment <experiment> -y
```

`purge run` removes the `results/` subfolder for that run — logs are shared and left intact.
`purge experiment` removes the results folder and `logs/runs/<experiment>/`.

---

## adgtk-study

Cross-experiment study rollup reports. A **study** is a named collection of experiments whose results you want to compare side-by-side. Study blueprints are YAML files stored in `studies/`. Output is written to `study-results/`.

```bash
adgtk-study list              # List saved study blueprints
adgtk-study build [name]      # Create a study blueprint (interactive)
adgtk-study run [name]        # Generate the study report and combined CSV
```

If `name` is omitted from `build` or `run`, ADGTK prompts you to select from available blueprints.

### `build` — interactive study wizard

The wizard lists every experiment with a results folder on disk and lets you select them by index, name, or `all`.

```bash
adgtk-study build
adgtk-study build model-comparison
```

The resulting blueprint is saved to `studies/{name}.yaml`:

```yaml
name: model-comparison
description: GPT-4o vs Claude on the extraction task
tags:
  - extraction
experiments:
  - exp-gpt4o
  - exp-claude
```

Edit this file by hand at any time to add, remove, or reorder experiments.

### `run` — generate the study report

```bash
adgtk-study run model-comparison
adgtk-study run                    # interactive selection
```

Reads all run manifests for each listed experiment, recalculates statistics, and writes two files to `study-results/{name}/`:

| File | Purpose |
|------|---------|
| `study_report.md` | Cross-experiment overview table, per-experiment config from first run, verdict/timing/metric/measurement stats |
| `study_results.csv` | Combined flat CSV — one row per run across all experiments |

### Output file details

**`study_report.md`** covers:

- **Cross-experiment overview** — one row per experiment with run count, pass/fail counts, average duration, and mean values for every result metric and measurement
- **Per-experiment sections** — configuration snapshot (from the first run's `run.exp.config.yaml`), verdict distribution, timing statistics, per-run result metrics table, measurement statistics, and config-deviation warnings
- **Missing experiments** — experiments listed in the blueprint but with no results folder on disk

**`study_results.csv`** columns:

| Column group | Pattern | Description |
|---|---|---|
| Identity | `experiment_name`, `run_id` | Experiment and run identifiers |
| Timing | `timestamp_start`, `timestamp_end`, `duration_seconds` | When and how long |
| Outcome | `status`, `verdict`, `verdict_note` | Run outcome |
| Tags | `tag_<key>` | One column per tag key seen across all runs |
| Result metrics | `metric_<key>` | One column per `result.set()` key |
| Measurements | `meas_<label>_{n,mean,std,min,max}` | Five columns per `MetricTracker` label |

Load in a notebook:

```python
import pandas as pd
df = pd.read_csv("study-results/model-comparison/study_results.csv")
df.groupby("experiment_name")["metric_accuracy"].mean()
```

### Examples

```bash
# Build a study comparing two experiments
adgtk-study build model-comparison

# Generate the report
adgtk-study run model-comparison

# List all saved study blueprints
adgtk-study list
```

---

## adgtk-mcp

Start an MCP (Model Context Protocol) server that exposes your ADGTK project to Claude and other MCP-capable agents. See [MCP Server](mcp-server.md) for full documentation.

```bash
adgtk-mcp                            # Serve the project in the current directory
adgtk-mcp --project-dir PATH         # Serve a project at a specific path
```

The server validates the project directory and runs `bootstrap.py` at startup. Once running, all 15 ADGTK tools are available to any connected MCP client.

### Options

| Flag | Description |
|------|-------------|
| `--project-dir PATH` | ADGTK project to serve (defaults to current directory) |

### Examples

```bash
# Start the server for the current project
cd ~/research/my-project
adgtk-mcp

# Start the server pointed at a specific project
adgtk-mcp --project-dir ~/research/my-project
```

---

## adgtk-web

Start a browser-based web interface for your project. See [Web Interface](web-interface.md) for full documentation.

```bash
adgtk-web --project-dir PATH         # Required: path to an ADGTK project
adgtk-web --project-dir PATH --port 8080      # Custom port (default: 8000)
adgtk-web --project-dir PATH --host 0.0.0.0  # Bind to all interfaces (remote access)
adgtk-web --project-dir PATH --no-auth       # Disable authentication
adgtk-web --project-dir PATH --token TOKEN   # Use a fixed token
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--project-dir PATH` | *(required)* | ADGTK project directory to serve |
| `--host HOST` | `127.0.0.1` | Interface to bind to (`0.0.0.0` for remote access) |
| `--port PORT` | `8000` | Port to listen on |
| `--token TOKEN` | *(random)* | Auth token; a random token is generated if omitted |
| `--no-auth` | `False` | Disable authentication entirely |

### Authentication

By default a random token is generated each time the server starts. The full URL including the token is printed to the console:

```
  ADGTK Web Interface
  http://127.0.0.1:8000/?token=a3f9c2d1e8b4...
```

Visiting that URL sets a session cookie so you won't need the token again until the server restarts. Pass `--token` to use a fixed value, or `--no-auth` to disable the check entirely (local development only).

### Examples

```bash
# Local development, no auth
adgtk-web --project-dir ~/research/my-project --no-auth

# Remote access with random token
adgtk-web --project-dir ~/research/my-project --host 0.0.0.0 --port 8080

# Fixed token for scripted access or sharing
adgtk-web --project-dir ~/research/my-project --token mysecrettoken
```
