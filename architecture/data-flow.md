# Data Flow

**Version:** 0.3.0b1
**Last Updated:** 2026-06-07 (updated: rec 1.2 web-initiated run flow; batch section updated to ADR-009)

---

## Overview

Data in ADGTK flows in one primary direction: **definition → execution → observation → persistence**. This document traces how data moves from YAML blueprint to disk-persisted manifest, and how results are aggregated across runs and experiments.

---

## Primary Execution Flow

```mermaid
flowchart TD
    YAML["blueprints/my-experiment.yaml"]
    BOOT["bootstrap.py → run_bootstrap()"]
    FACTORY_INV["factory._inventory"]
    LOAD["_load_experiment_file()"]
    PARSE["Pydantic: ExperimentDefinition"]
    BUILD["_build_component() ← recursive"]
    SCENARIO["Scenario instance"]
    RUN_FOLDER["ExperimentRunFolders (paths)"]
    RUN["scenario.run_scenario(folders)"]
    OBS_API["observations module (global state)"]
    METRIC_API["MetricTracker"]
    AGENT_WRITER["AgentWriter (optional)"]
    RESULT["RunResult"]
    MANIFEST["RunManifest (Pydantic)"]
    MARKDOWN["report.md"]
    JSON_MANIFEST["results/{id}/conclusions/run.manifest.json"]
    CSV["results/{id}/metrics/*.csv"]
    YAML_SNAP["results/{id}/run.exp.config.yaml"]
    RUNS_JSON[".tracking/runs.json (index)"]

    BOOT --> FACTORY_INV
    YAML --> LOAD
    LOAD --> PARSE
    PARSE -->|"each AttributeEntry"| BUILD
    FACTORY_INV -->|"factory.create()"| BUILD
    BUILD --> SCENARIO
    SCENARIO --> RUN_FOLDER
    SCENARIO --> RUN

    RUN -->|"obs.note/warn/config_note"| OBS_API
    RUN -->|"obs.agent_turn"| OBS_API
    RUN -->|"tracker.add_data"| METRIC_API
    AGENT_WRITER -->|"semantic log_step/outcome"| METRIC_API
    RUN --> RESULT

    RESULT --> MANIFEST
    OBS_API -->|"get_observations()"| MANIFEST
    MANIFEST --> MARKDOWN
    MANIFEST --> JSON_MANIFEST
    METRIC_API -->|"export_csv()"| CSV
    PARSE -->|"snapshot"| YAML_SNAP
    MANIFEST -->|"RunEntryModel"| RUNS_JSON
```

---

## Configuration Resolution

Blueprint YAML uses a recursive `AttributeEntry` structure. Each node is either a **factory-backed component** or a **literal value**. Resolution is depth-first.

```mermaid
flowchart TD
    ROOT["ExperimentDefinition<br/>factory_id: my-scenario"]
    A1["AttributeEntry<br/>attribute: model<br/>factory_id: gpt-4o-wrapper"]
    A2["AttributeEntry<br/>attribute: prompt_template<br/>init_config: my-prompt-text (literal)"]
    A3["AttributeEntry<br/>attribute: max_retries<br/>init_config: 3 (literal)"]
    C1["GPT4oWrapper(prompt_template='my-prompt-text', max_retries=3)"]
    C2["MyScenario(model=<GPT4oWrapper>)"]

    ROOT --> A1
    ROOT --> A2
    ROOT --> A3
    A1 --> C1
    A2 -->|"literal"| C1
    A3 -->|"literal"| C1
    C1 --> C2
```

---

## Observation Accumulation

During a run, the scenario (and any components it calls) writes observations into a module-level list. This list is reset before each run and consumed by `build_manifest()` at the end.

```mermaid
sequenceDiagram
    participant Runner as Experiment Runner
    participant Reset as observations.reset()
    participant Scen as Scenario
    participant Obs as observations._observations[]
    participant Art as observations._artifacts[]
    participant Build as build_manifest()

    Runner->>Reset: clear state before run
    Runner->>Scen: run_scenario(folders)

    Scen->>Obs: obs.config_note("model", "gpt-4o")
    Scen->>Obs: obs.note("Dataset loaded: 100 items")
    Scen->>Obs: obs.agent_turn(prompt, response, tokens, latency)
    Scen->>Obs: obs.warn("Rate limit hit, backing off")
    Scen->>Art: obs.add_artifact("results/.../output.json")

    Scen-->>Runner: RunResult(verdict, metrics, tags)

    Runner->>Build: build_manifest(result, config, timing)
    Build->>Obs: get_observations()
    Build->>Art: get_artifacts()
    Build-->>Runner: RunManifest
```

---

## Metrics Data Flow

Metrics follow two paths: **direct** (via `MetricTracker`) and **semantic** (via `AgentWriter`, which wraps `MetricTracker`).

```mermaid
flowchart LR
    subgraph Scenario
        DIRECT["tracker.add_data('accuracy', 0.91)"]
        AW["AgentWriter"]
        AW_LOG["aw.log_step(step=1, latency_ms=230, ...)"]
        AW_OUT["aw.log_outcome(success=True, goal=0.9)"]
    end

    subgraph MetricTracker
        MT_DATA["_data: dict[label → list[float]]"]
    end

    subgraph Disk
        CSV1["metrics/my_tracker.accuracy.csv"]
        CSV2["metrics/agent.latency_ms.csv"]
        CSV3["metrics/agent.goal_completion.csv"]
    end

    DIRECT --> MT_DATA
    AW_LOG -->|"emits agent.latency_ms, agent.tokens_*"| MT_DATA
    AW_OUT -->|"emits agent.goal_completion, agent.path_efficiency"| MT_DATA
    MT_DATA -->|"export_csv()"| CSV1
    MT_DATA --> CSV2
    MT_DATA --> CSV3
```

Each label in a `MetricTracker` becomes a separate CSV file. Rows represent values over time (across steps or iterations within a single run).

---

## Results Aggregation: Experiment Report

After multiple runs of the same experiment, `generate_experiment_report()` aggregates across all `RunManifest` records.

```mermaid
flowchart TD
    RUNS_JSON[".tracking/runs.json"]
    FILTER["Filter by experiment name"]
    MANIFESTS["Load run.manifest.json × N"]
    AGG["Aggregate: verdicts, metric distributions, tags"]
    EXP_REPORT["experiment_report.md"]
    EXP_CSV["experiment_summary.csv (optional)"]

    RUNS_JSON --> FILTER
    FILTER --> MANIFESTS
    MANIFESTS --> AGG
    AGG --> EXP_REPORT
    AGG --> EXP_CSV
```

---

## Results Aggregation: Study Rollup

A study groups multiple experiments for cross-experiment comparison.

```mermaid
flowchart TD
    STUDY_YAML["studies/my-study.yaml<br/>(experiments: [exp-a, exp-b, exp-c])"]
    LOAD_EXP["Load all runs per experiment"]
    MANIFESTS["RunManifest × M (across all experiments)"]
    ROLLUP["study rollup: align metrics, compare verdicts"]
    STUDY_REPORT["study-results/{study}/study_report.md"]
    STUDY_CSV["study-results/{study}/study_results.csv"]

    STUDY_YAML --> LOAD_EXP
    LOAD_EXP --> MANIFESTS
    MANIFESTS --> ROLLUP
    ROLLUP --> STUDY_REPORT
    ROLLUP --> STUDY_CSV
```

---

## MCP-Driven Data Flow

When an AI agent drives experiments via the MCP server, the flow is the same internally — the MCP layer is a thin adapter over the same runner and tracking APIs.

```mermaid
sequenceDiagram
    participant Agent as AI Agent (Claude)
    participant MCP as MCP Server
    participant Runner as Experiment Runner
    participant Tracking as Tracking / Filesystem

    Agent->>MCP: list_experiments()
    MCP->>Tracking: read .tracking/project.json
    MCP-->>Agent: [exp-a, exp-b, ...]

    Agent->>MCP: run_experiment("exp-a")
    MCP->>Runner: run_scenario("exp-a")
    Runner->>Tracking: write manifest + index
    MCP-->>Agent: run_id, verdict, summary

    Agent->>MCP: get_run_manifest(run_id)
    MCP->>Tracking: read run.manifest.json
    MCP-->>Agent: full RunManifest JSON
```

---

## Web-Initiated Run Flow

When a run is started from the web UI, the flow diverges from the CLI path. The web server creates a `TaskState` and `TaskRecord` before launching the subprocess, then streams live output to the browser via SSE.

```mermaid
sequenceDiagram
    participant Browser
    participant Web as Web Server (api/tasks.py)
    participant Sub as Subprocess (adgtk run)
    participant Disk as .tracking/tasks/{task_id}/

    Browser->>Web: POST /experiments/name/run
    Web->>Disk: create record.json (status=running, pid=0)
    Web-->>Browser: HX-Redirect → /tasks/task_id
    Browser->>Web: GET /tasks/task_id (full page)
    Browser->>Web: SSE connect /tasks/task_id/stream

    Web->>Sub: spawn with env ADGTK_TASK_ID=task_id
    Sub->>Disk: update record.json (real pid)
    loop each output line
        Sub-->>Web: stdout line
        Web->>Disk: append output.log
        Web-->>Browser: SSE message event (HTML line)
    end

    Sub-->>Web: exit (returncode)
    Web->>Disk: update record.json (status, run_id, finished_at)
    Web-->>Browser: SSE done event
    Web-->>Browser: SSE navigate event → /results/exp/run_id
    Browser->>Web: GET /results/exp/run_id (report page)
```

After the run completes, `_find_run_id()` in `api/tasks.py` scans `results/{experiment_name}/` for the directory with the newest modification time since the task started, and stores it as `task.run_id` / `TaskRecord.run_id`.

---

## Batch Execution Flow

The batch system sequences multiple experiments. Task state is written to `.tracking/tasks/{task_id}/record.json` (ADR-009).

```mermaid
flowchart TD
    BATCH_DEF["Batch definition (list of experiment names)"]
    TASK_REC[".tracking/tasks/{task_id}/record.json"]
    LOOP["adgtk-batch run"]
    NEXT["Pop next experiment"]
    RUNNER["run_scenario()"]
    UPDATE["Update record.json (progress)"]
    DONE{"All done?"}
    COMPLETE["Batch complete"]

    BATCH_DEF --> TASK_REC
    TASK_REC --> LOOP
    LOOP --> NEXT
    NEXT --> RUNNER
    RUNNER --> UPDATE
    UPDATE --> DONE
    DONE -->|"No"| NEXT
    DONE -->|"Yes"| COMPLETE
```

---

## Task Retention Flow

At web-server startup (and optionally from the CLI), finished task directories are pruned according to the project's `settings.yaml` retention policy.

```mermaid
flowchart TD
    START["adgtk-web startup"]
    ORPHAN["cleanup_orphaned_tasks()\nMark running tasks with dead PIDs as error"]
    LOAD_SETTINGS["load_project_settings()\nRead settings.yaml (auto-created if missing)"]
    AUTO_CHECK{"auto_cleanup\nenabled?"}
    PURGE["purge_old_task_records(\n  max_age_days=ttl_days,\n  max_count=max_count\n)"]
    TTL["Pass 1 — TTL\nDelete finished tasks older than ttl_days"]
    COUNT["Pass 2 — Count cap\nDelete oldest finished tasks until ≤ max_count"]
    DONE["Server ready"]

    START --> ORPHAN
    ORPHAN --> LOAD_SETTINGS
    LOAD_SETTINGS --> AUTO_CHECK
    AUTO_CHECK -->|"Yes"| PURGE
    AUTO_CHECK -->|"No"| DONE
    PURGE --> TTL
    TTL --> COUNT
    COUNT --> DONE
```

Running tasks are never deleted by either cleanup pass. The same policy can be applied manually from the CLI with `adgtk tasks cleanup --auto`, or all finished records can be removed at once with `adgtk tasks cleanup` (prompts for confirmation) or the **Cleanup** button in the web UI's Tasks page.

---

## Related Documents

- [System Overview](overview.md)
- [Component Architecture](components.md)
- [Decisions Index](decisions/index.md)
