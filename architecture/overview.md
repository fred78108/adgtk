# ADGTK System Architecture Overview

**Version:** 0.3.0b0
**Last Updated:** 2026-06-07 (updated: rec 1.1 filesystem layout, rec 1.2 task page)

---

## Purpose

ADGTK (Agent Development & General Testing Kit) is a framework for designing, running, and analyzing experiments on agentic AI systems. It provides a structured approach to reproducible experimentation: define a scenario in YAML, run it, and get a canonical record of what happened — observations, metrics, and artifacts — stored as plain files.

---

## System Context

```mermaid
graph TD
    User["Researcher / Developer"]
    CLI["CLI Tools<br/>(adgtk, adgtk-batch, etc.)"]
    Web["Web UI<br/>(adgtk-web)"]
    MCP["MCP Server<br/>(adgtk-mcp)"]
    Agent["AI Agent<br/>(Claude, etc.)"]
    Framework["ADGTK Framework"]
    Results["Results Store<br/>(filesystem)"]
    ExternalData["External Data<br/>(HuggingFace, CSV, etc.)"]

    User -->|"runs experiments"| CLI
    User -->|"browses results"| Web
    Agent -->|"orchestrates runs"| MCP
    CLI --> Framework
    Web --> Framework
    MCP --> Framework
    Framework -->|"reads"| ExternalData
    Framework -->|"writes"| Results
    Web -->|"reads"| Results
    MCP -->|"reads"| Results
```

---

## Module Map

```mermaid
graph TD
    subgraph Entry["Entry Points"]
        CLI["adgtk.cli"]
        API["adgtk.api"]
        MCP_SRV["adgtk.mcp_server"]
    end

    subgraph Core["Core"]
        FACTORY["adgtk.factory<br/>Component Registry"]
        EXP["adgtk.experiment<br/>Runner & Builder"]
        TRACK["adgtk.tracking<br/>Observations & Manifests"]
        MEAS["adgtk.measurements<br/>Metrics Engine"]
        DATA["adgtk.data<br/>Dataset Manager"]
    end

    subgraph Support["Support"]
        UTILS["adgtk.utils<br/>Logging & Helpers"]
        EXAMPLES["adgtk.examples<br/>Reference Implementations"]
    end

    subgraph Bootstrap["Per-Process Bootstrap"]
        BOOT["bootstrap.py<br/>(user project)"]
    end

    BOOT -->|"registers components into"| FACTORY
    CLI --> EXP
    API --> EXP
    API --> TRACK
    MCP_SRV --> EXP
    MCP_SRV --> TRACK
    MCP_SRV --> FACTORY
    EXP -->|"instantiates via"| FACTORY
    EXP -->|"writes to"| TRACK
    EXP -->|"uses"| DATA
    MEAS -->|"registered in"| FACTORY
    TRACK --> UTILS
    EXP --> UTILS
```

---

## Layered Architecture

```mermaid
graph BT
    subgraph L1["Layer 1: Storage (filesystem)"]
        FS_RESULTS["results/ — run artifacts"]
        FS_TRACK[".tracking/ — run index"]
        FS_BP["blueprints/ — YAML definitions"]
        FS_STUDY["studies/ — study definitions"]
    end

    subgraph L2["Layer 2: Core Framework"]
        FACTORY["Factory Registry"]
        RUNNER["Experiment Runner"]
        OBS["Observations API"]
        MANIFEST["Manifest Builder"]
        MEAS_ENG["Measurement Engine"]
        DATASET["Dataset Manager"]
    end

    subgraph L3["Layer 3: Interfaces"]
        CLI_LAYER["9 CLI Commands"]
        WEB_LAYER["FastAPI + HTMX Web UI"]
        MCP_LAYER["MCP Server (15+ tools)"]
    end

    subgraph L4["Layer 4: User Code"]
        USER_SCENARIO["User Scenarios"]
        USER_BOOT["bootstrap.py"]
        USER_BP["Experiment YAML"]
    end

    L1 --> L2
    L2 --> L3
    L4 -->|"declares"| USER_BP
    L4 -->|"registers via"| USER_BOOT
    USER_BOOT --> FACTORY
    USER_BP --> RUNNER
    USER_SCENARIO --> OBS
    USER_SCENARIO --> MEAS_ENG
```

---

## Key Design Principles

| Principle | How It Is Applied |
|-----------|-------------------|
| **Reproducibility** | Every run snapshots its exact YAML config alongside results |
| **Transparency** | The observations API creates a structured "lab journal" for each run |
| **Extensibility** | Factory pattern enables pluggable scenarios, measurements, and datasets without framework changes |
| **Simplicity** | Non-persistent factory, YAML-first definitions, plain-filesystem tracking — no database required |
| **Agentic First** | `AgentWriter`, MCP server, and `agent_turn()` observation type are first-class citizens |
| **Type Safety** | Pydantic validates all external data; `Protocol` classes enforce interfaces without inheritance |

---

## Filesystem Layout

```
{project-root}/
├── bootstrap.py              ← user code: registers components into the factory
├── blueprints/               ← YAML experiment definitions
│   └── my-experiment.yaml
├── studies/                  ← YAML study (multi-experiment) definitions
├── results/                  ← auto-generated run output
│   └── {experiment_name}/
│       ├── common/                   ← shared experiment-level data
│       └── {run_id}/
│           ├── run.exp.config.yaml       ← exact config snapshot
│           ├── conclusions/
│           │   ├── run.manifest.json     ← canonical run record
│           │   ├── report.md             ← human-readable report
│           │   └── results.yaml          ← quick-reference summary
│           ├── metrics/
│           │   └── {tracker}.{label}.csv
│           ├── llm/
│           │   ├── chat.log              ← ANSI-colored LLM conversation
│           │   └── chat.jsonl            ← NDJSON sidecar for web rendering
│           ├── datasets/
│           ├── images/
│           ├── models/
│           └── other/
├── logs/                     ← framework and run logs
│   ├── framework/
│   │   └── adgtk.project.log         ← rotating framework log (5 MB / 3 backups)
│   └── runs/
│       └── {experiment_or_batch}/
│           ├── scenario.log           ← per-run scenario log
│           └── batch.log              ← batch run summary (batch jobs only)
├── settings.yaml             ← user-configurable project settings (auto-created)
├── study-results/            ← cross-experiment aggregated results
└── .tracking/                ← runtime registries
    ├── runs.json             ← index of all completed runs
    ├── project.json          ← experiment inventory
    ├── prefix.json           ← run ID prefix config
    └── tasks/                ← per-task records (ADR-009)
        └── {task_id}/
            ├── record.json   ← TaskRecord (status, pid, timestamps, run_id)
            └── output.log    ← captured stdout/stderr (web-launched tasks)
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python ≥ 3.12 |
| Data Validation | Pydantic |
| Config Format | YAML |
| Web Server | FastAPI + Uvicorn |
| Web Templates | Jinja2 + HTMX |
| Agent Integration | MCP (Model Context Protocol) |
| Data | HuggingFace `datasets`, pandas |
| CLI | prompt-toolkit |
| Testing | pytest, mypy, flake8, tox |

---

## Related Documents

- [Component Architecture](components.md)
- [Data Flow](data-flow.md)
- [Decisions Index](decisions/index.md)
