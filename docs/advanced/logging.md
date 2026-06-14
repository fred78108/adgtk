# Logging

ADGTK maintains four distinct loggers, each covering a different scope. This page describes what each one writes, where it writes it, and how to use the logging API in your own scenario code.

---

## Overview

| Logger | Written by | Location | Format |
|--------|-----------|----------|--------|
| **Framework** | Runner, internal framework | `logs/framework/` | Rotating text |
| **Scenario** | Runner (per experiment run) | `logs/runs/{experiment}/` | Plain text |
| **Batch** | Batch runner | `logs/runs/{batch_name}/` | Plain text |
| **LLM** | Your scenario code | `results/{run_id}/llm/` | ANSI text + NDJSON |

---

## Log file locations

```
{project-root}/
├── logs/
│   ├── framework/
│   │   └── adgtk.project.log        ← framework logger, rotating
│   └── runs/
│       └── {experiment_or_batch}/
│           ├── scenario.log          ← scenario logger (overwritten each run)
│           └── batch.log             ← batch logger (batch jobs only)
└── results/
    └── {experiment_name}/
        └── {run_id}/
            └── llm/
                ├── chat.log          ← ANSI-colored conversation text
                └── chat.jsonl        ← NDJSON sidecar for web rendering
```

---

## Framework logger

The framework logger (`adgtk.project.log`) is a long-lived file used by the runner and internal framework modules. It records experiment lifecycle events: task start/stop, blueprint load, error conditions.

**Location:** `logs/framework/adgtk.project.log`

**Rotation:** Uses `RotatingFileHandler` — rotates at 5 MB and keeps 3 backup files (`adgtk.project.log.1`, `.2`, `.3`).

**Project context guard:** `get_project_logger()` checks for `bootstrap.py` in the current directory before writing to disk. If called from outside a project directory (e.g., during `adgtk-project create`), it returns a logger with a `NullHandler` only — no stray `logs/` tree is created.

```python
from adgtk.utils import get_project_logger

logger = get_project_logger()
logger.info("My framework-level message")
```

---

## Scenario logger

The scenario logger (`SCENARIO`) records what happens during a single experiment run. It is created fresh for each run (mode `"w"`) so each file contains exactly one run's output.

**Location:** `logs/runs/{experiment_name}/scenario.log`

```python
from adgtk.utils import get_scenario_logger

logger = get_scenario_logger()
logger.info("Processing item %d of %d", i, n)
```

The runner creates and owns this logger — most scenario code retrieves it via `get_scenario_logger()` rather than creating it directly.

---

## Batch logger

When `adgtk-batch run` executes a batch job, it creates a dedicated batch logger that records a consolidated view of the entire batch run.

**Location:** `logs/runs/{batch_name}/batch.log`

**Contents:**
- Batch start time and total job count
- Per-experiment: start time, outcome (`complete` / `error`), and duration
- One-line summary at completion: total time, pass count, fail count

This gives you a single file to inspect after an overnight batch run without having to piece together individual experiment logs.

---

## LLM logger

The LLM logger records agent conversations: each user turn, model response, and tool exchange. It writes **two parallel files** into the run's `llm/` subfolder:

| File | Purpose | Format |
|------|---------|--------|
| `chat.log` | Terminal / CLI use | ANSI-colored, role-labeled text |
| `chat.jsonl` | Web viewer | Newline-delimited JSON |

Each NDJSON line is a single message:

```json
{"role": "assistant", "content": "Here is my analysis...", "ts": "2026-06-14T12:01:33Z"}
```

Accepted roles: `user`, `assistant`, `system`, `tool`, `error`.

### Creating an LLM logger

```python
from adgtk.utils.logs import create_llm_logger

llm_log = create_llm_logger(
    logfile="chat.log",
    logger_name="my.llm.logger",
    folders=result_folders,         # ExperimentRunFolders passed to run_scenario
    log_to_console=True,            # mirror to terminal (default True)
)
```

A `chat.jsonl` sidecar is written automatically alongside `chat.log`. Pass `json_logfile=""` to suppress it.

### Logging a turn

```python
llm_log.info(user_prompt,   extra={"role": "user"})
llm_log.info(model_response, extra={"role": "assistant"})
llm_log.info(tool_output,    extra={"role": "tool"})
```

Omitting the `role` extra renders the entry without colour coding (uses the `default` style).

### Custom NDJSON filename

```python
llm_log = create_llm_logger(
    logfile="planner.log",
    json_logfile="planner.jsonl",   # defaults to logfile with .log → .jsonl
    ...
)
```

---

## `create_logger` — custom loggers

For any logging need not covered by the built-in loggers, use `create_logger` directly:

```python
from adgtk.utils import create_logger
import logging

logger = create_logger(
    logfile="my.log",
    logger_name="my.module",
    log_level=logging.DEBUG,
    log_to_console=True,
    subdir="runs",
    experiment_name="my-experiment",
)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `logfile` | *(required)* | Filename for the log file |
| `logger_name` | *(required)* | Python logger identifier |
| `log_level` | `logging.INFO` | Minimum level to record |
| `log_to_console` | `False` | Mirror output to stdout |
| `subdir` | `"framework"` | Log tree subdirectory — `"framework"`, `"runs"`, `"common"`, or `"agent"` |
| `experiment_name` | `None` | Required when `subdir` is `"runs"` or `"agent"` |
| `log_propagate` | `False` | Whether to propagate to ancestor loggers |
| `mode` | `"a"` | File open mode — `"a"` append, `"w"` overwrite |

### Log rotation

Only the `"framework"` subdir uses `RotatingFileHandler`. All other subdirs use a plain `FileHandler`. Per-run logs are naturally bounded by the run duration, so rotation is not needed for them.

### Console logging

`log_to_console=True` adds a `StreamHandler` to stdout. The guard uses `type(h) is logging.StreamHandler` (not `isinstance`) so `FileHandler`s — which are a subclass — do not block the console handler from being added.

---

## Viewing logs

### Web interface — Logs page

The **Logs** page (`/logs`) lists every log file in the `logs/` tree, grouped by category:

- **framework** — `adgtk.project.log` and any other framework-level files
- **common** — shared logs not tied to a specific run
- **runs/{name}** — `scenario.log`, `batch.log`, and agent logs for each experiment or batch

Click any file name to load it into the viewer on the right. Files are tail-read (last 200 KB) to keep the page responsive for large logs.

### Web interface — Run detail Logs tab

The run detail page includes a **Logs** tab alongside Observations, Metrics, and Config. It shows:

- **scenario.log** — the scenario logger output for that run, rendered as plain text
- **LLM log files** — each file in `results/{run_id}/llm/` appears as a tab. Files with a `.jsonl` extension are rendered as a **conversation thread**: each message gets a coloured role chip (`USER`, `ASSISTANT`, `SYSTEM`, `TOOL`) and indented content block. Files with a `.log` extension are rendered as plain text.

This makes it easy to replay exactly what the model was sent and said during any run without leaving the browser.
