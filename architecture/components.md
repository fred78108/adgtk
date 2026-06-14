# Component Architecture

**Version:** 0.3.0b1
**Last Updated:** 2026-06-07 (updated: rec 1.2 task page, SSE protocol, route map)

---

## Factory System (`adgtk.factory`)

The factory is the central registry for all pluggable components. It is **non-persistent** — rebuilt from scratch on every process start via `bootstrap.py`.

### Structure

```mermaid
classDiagram
    class SupportsFactory {
        <<ABC>>
        +ClassVar factory_id: str
        +ClassVar group: str
        +ClassVar tags: list[str]
        +ClassVar summary: str
        +ClassVar interview_blueprint: list[BlueprintQuestion]
        +ClassVar factory_can_init: bool
    }

    class FactoryEntry {
        +factory_id: str
        +group: str
        +tags: list[str]
        +summary: str
        +cls: type
    }

    class FactoryOrder {
        +factory_id: str
        +init_config: dict
    }

    class BlueprintQuestion {
        +attribute: str
        +question: str
        +options: list[str]
        +default: str
    }

    SupportsFactory <|-- UserScenario : implements
    SupportsFactory <|-- BuiltinMeasurement : implements
    FactoryEntry --> SupportsFactory : references
```

### Global Registry

```mermaid
graph LR
    BOOT["bootstrap.py"]
    REG["register()"]
    INV["_inventory: dict[str, FactoryEntry]"]
    CREATE["create(factory_id)"]
    LIST["list_entries(group, tags)"]
    COMP["Component Instance"]

    BOOT -->|"@register_to_factory"| REG
    REG --> INV
    CREATE --> INV
    LIST --> INV
    CREATE --> COMP
```

### Registration Lifecycle

Every process that runs an ADGTK command calls `run_bootstrap()`, which invokes three ordered hooks from the project's `bootstrap.py`:

1. `foundation()` — Register built-in language primitives and core framework types
2. `builtin()` — Register framework-provided scenarios, measurements, and datasets
3. `user_code()` — Register user-defined components

After bootstrap, the `_inventory` dict is fully populated and all subsequent `create()` calls resolve synchronously without I/O.

---

## Experiment System (`adgtk.experiment`)

### Class Relationships

```mermaid
classDiagram
    class ExperimentDefinition {
        +description: str
        +attribute: str
        +factory_id: str
        +factory_init: bool
        +init_config: list[AttributeEntry]
    }

    class AttributeEntry {
        +attribute: str
        +factory_id: str | None
        +factory_init: bool
        +init_config: list[AttributeEntry] | scalar
    }

    class ScenarioProtocol {
        <<Protocol>>
        +run_scenario(result_folders: ExperimentRunFolders) RunResult
    }

    class RunResult {
        +verdict: str
        +summary: str
        +metrics: dict[str, float]
        +tags: list[str]
    }

    class RunResultBuilder {
        +set_verdict(verdict) RunResultBuilder
        +add_metric(name, value) RunResultBuilder
        +add_tag(tag) RunResultBuilder
        +build() RunResult
    }

    class ExperimentRunFolders {
        <<dataclass>>
        +root: Path
        +conclusion: Path
        +metrics: Path
        +logs: Path
        +datasets: Path
        +images: Path
        +models: Path
        +other: Path
    }

    ExperimentDefinition --> AttributeEntry : contains recursively
    RunResultBuilder --> RunResult : builds
    ScenarioProtocol --> RunResult : returns
    ScenarioProtocol --> ExperimentRunFolders : receives
```

### Experiment Build Process

```mermaid
flowchart TD
    YAML["blueprints/*.yaml"] --> LOAD["_load_experiment_file()"]
    LOAD --> VALIDATE["Pydantic: ExperimentDefinition"]
    VALIDATE --> BUILD["_build_component(AttributeEntry)"]
    BUILD -->|"has factory_id?"| FACTORY_LOOKUP["factory.create(factory_id)"]
    BUILD -->|"scalar value?"| LITERAL["Use value directly"]
    FACTORY_LOOKUP --> RECURSE["Recurse on init_config"]
    RECURSE --> BUILD
    LITERAL --> ASSEMBLE["Assemble kwargs"]
    ASSEMBLE --> SCENARIO["Scenario instance"]
    SCENARIO --> RUN["scenario.run_scenario(folders)"]
    RUN --> RESULT["RunResult"]
```

---

## Tracking & Observations (`adgtk.tracking`)

### Observation Types

```mermaid
classDiagram
    class AnyObservation {
        <<Discriminated Union>>
    }

    class NoteObservation {
        +type: Literal[note]
        +message: str
        +timestamp: datetime
    }

    class WarnObservation {
        +type: Literal[warn]
        +message: str
        +timestamp: datetime
    }

    class AgentTurnObservation {
        +type: Literal[agent_turn]
        +prompt: str
        +response: str
        +tokens_in: int
        +tokens_out: int
        +latency_ms: float
        +timestamp: datetime
    }

    class ConfigNoteObservation {
        +type: Literal[config_note]
        +key: str
        +value: str
        +timestamp: datetime
    }

    class MetricEventObservation {
        +type: Literal[metric_event]
        +name: str
        +value: float
        +timestamp: datetime
    }

    AnyObservation <|-- NoteObservation
    AnyObservation <|-- WarnObservation
    AnyObservation <|-- AgentTurnObservation
    AnyObservation <|-- ConfigNoteObservation
    AnyObservation <|-- MetricEventObservation
```

### Run Manifest Structure

```mermaid
classDiagram
    class RunManifest {
        +run_id: str
        +experiment: str
        +started_at: datetime
        +finished_at: datetime
        +duration_seconds: float
        +verdict: str
        +summary: str
        +metrics: dict[str, float]
        +tags: list[str]
        +observations: list[AnyObservation]
        +artifacts: list[str]
        +config: dict
    }

    class RunEntryModel {
        +run_id: str
        +experiment: str
        +verdict: str
        +started_at: datetime
        +tags: list[str]
    }

    RunManifest --> AnyObservation : contains
    RunEntryModel --> RunManifest : indexes
```

### Module-Level State

The tracking module uses module-level globals to accumulate run data during execution. This avoids passing context objects through every layer of user code.

```mermaid
sequenceDiagram
    participant Runner
    participant Scenario
    participant obs as observations module
    participant Manifest as build_manifest()

    Runner->>obs: reset_observations()
    Runner->>Scenario: run_scenario(folders)
    Scenario->>obs: note("Starting...")
    Scenario->>obs: agent_turn(prompt, response)
    Scenario->>obs: warn("Retrying...")
    Scenario->>obs: metric_event("accuracy", 0.92)
    Scenario-->>Runner: RunResult
    Runner->>Manifest: build_manifest(result, ...)
    Manifest->>obs: get_observations()
    Manifest-->>Runner: RunManifest
```

---

## Measurements (`adgtk.measurements`)

### Engine Architecture

```mermaid
classDiagram
    class MeasurementEngine {
        +add_by_id(factory_id)
        +add_by_type(measurement_type)
        +add_by_tag(tag)
        +measure(value) dict
        +compare(a, b) dict
        +measure_dataset_distribution(dataset) dict
    }

    class ClassBasedMeasurement {
        <<Protocol>>
        +measure(value) float
    }

    class ClassBasedComparison {
        <<Protocol>>
        +compare(a, b) float
    }

    class AgentWriter {
        +log_step(step, latency_ms, tokens_in, tokens_out)
        +log_tool_call(tool_name, success)
        +log_outcome(success, goal_completion, path_efficiency)
        +tracker: MetricTracker
    }

    class MetricTracker {
        +add_data(label, value)
        +export_csv(path)
        +get_series(label) list[float]
    }

    MeasurementEngine --> ClassBasedMeasurement : uses
    MeasurementEngine --> ClassBasedComparison : uses
    AgentWriter --> MetricTracker : writes to
```

### Built-in Measurements

| Factory ID | Type | Description |
|-----------|------|-------------|
| `string-length` | measurement | Character count of a string |
| `dict-total-str-length` | measurement | Recursive string length across a dict |
| `exact-match` | comparison | Binary string equality (0.0 or 1.0) |
| `token-f1` | comparison | Word-overlap F1 score |
| `json-valid` | measurement | Returns 1.0 if string is valid JSON |
| `dict-schema-match` | comparison | Key overlap ratio between two dicts |
| `schema-key-depth` | measurement | Maximum nesting depth of a dict |
| `list-item-type-consistency` | measurement | Homogeneity ratio of a list's types |

### AgentWriter Metrics

`AgentWriter` is a high-level instrumentation layer designed specifically for evaluating agentic systems. It emits named metrics into a `MetricTracker` using semantic, domain-appropriate names.

| Metric Name | Description |
|------------|-------------|
| `agent.latency_ms` | Per-step call latency |
| `agent.tokens_in` | Input tokens per step |
| `agent.tokens_out` | Output tokens per step |
| `agent.success` | Step success flag (0/1) |
| `agent.retry_count` | Number of retries |
| `agent.tool_calls` | Total tool calls in step |
| `agent.goal_completion` | Final goal completion score |
| `agent.path_efficiency` | Ratio of optimal steps to actual steps |

---

## Logging System (`adgtk.utils.logs`)

ADGTK maintains four loggers with distinct scopes. All are created through `create_logger()` or its specialised wrappers.

```mermaid
graph TD
    subgraph Loggers
        PL["Framework logger<br/>PROJECT_LOGGER_NAME<br/>get_project_logger()"]
        SL["Scenario logger<br/>SCENARIO_LOGGER_NAME<br/>get_scenario_logger()"]
        BL["Batch logger<br/>BATCH_LOGGER_NAME<br/>create_logger()"]
        LL["LLM logger<br/>(user-named)<br/>create_llm_logger()"]
    end

    subgraph Files["Log files"]
        PF["logs/framework/adgtk.project.log<br/>(RotatingFileHandler — 5 MB / 3)"]
        SF["logs/runs/{experiment}/scenario.log<br/>(mode=w, one per run)"]
        BF["logs/runs/{batch}/batch.log"]
        LF["results/{run_id}/llm/chat.log<br/>results/{run_id}/llm/chat.jsonl"]
    end

    PL --> PF
    SL --> SF
    BL --> BF
    LL --> LF
```

### Logger constants (`adgtk.utils.defaults`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `PROJECT_LOGGER_NAME` | `"adgtk.project.log"` | Framework / runner lifecycle events |
| `SCENARIO_LOGGER_NAME` | `"SCENARIO"` | Per-run scenario output |
| `BATCH_LOGGER_NAME` | `"BATCH"` | Batch run summary |
| `LOG_ROTATE_MAX_BYTES` | `5_000_000` | Rotation threshold for framework logs |
| `LOG_ROTATE_BACKUP_COUNT` | `3` | Number of backup files kept |

### Project context guard

`get_project_logger()` calls `is_project_context()` before creating any file handler. `is_project_context()` returns `True` only when `bootstrap.py` is present in the CWD. Outside a project directory the logger is returned with a `NullHandler` — no `logs/` tree is created in unexpected locations.

### LLM logger dual output

`create_llm_logger()` attaches two file handlers to the same logger:

1. `RoleColorFormatter` → `.log` file — ANSI-colored role labels for terminal use
2. `NdjsonFormatter` → `.jsonl` file — `{"role":"..","content":"..","ts":".."}` per line, consumed by the web run-detail Logs tab

---

## CLI (`adgtk.cli`)

Nine independent CLI entry points share a common bootstrap invocation pattern:

```mermaid
graph LR
    subgraph CLIs
        A["adgtk"]
        B["adgtk-project"]
        C["adgtk-batch"]
        D["adgtk-factory"]
        DS["adgtk-ds"]
        E["adgtk-results"]
        F["adgtk-study"]
        G["adgtk-mcp"]
        H["adgtk-web"]
    end

    subgraph Responsibilities
        A_R["Run, build & report experiments"]
        B_R["Scaffold new projects"]
        C_R["Manage batch queues"]
        D_R["Inspect factory registry"]
        DS_R["Dataset inventory management"]
        E_R["List, export, report results"]
        F_R["Build & run studies"]
        G_R["Start MCP server"]
        H_R["Start web UI"]
    end

    A --> A_R
    B --> B_R
    C --> C_R
    D --> D_R
    DS --> DS_R
    E --> E_R
    F --> F_R
    G --> G_R
    H --> H_R
```

---

## Web Interface (`adgtk.api`)

### Request / Response Architecture

```mermaid
graph TD
    Browser["Browser (HTMX + Alpine.js)"]
    FastAPI["FastAPI Application"]
    Auth["Token Auth Middleware"]
    Jinja["Jinja2 Templates"]
    TrackRead["tracking.runs (read)"]
    Results["results/ filesystem"]
    Tasks["api.tasks (in-memory TaskState)"]
    TaskDisk[".tracking/tasks/ (TaskRecord on disk)"]

    Browser -->|"HTTP / SSE requests"| FastAPI
    FastAPI --> Auth
    Auth -->|"authorized"| Jinja
    FastAPI --> TrackRead
    FastAPI --> Tasks
    Tasks --> TaskDisk
    TrackRead --> Results
    Jinja -->|"HTML pages + fragments"| Browser
    Tasks -->|"SSE event stream"| Browser
```

The web UI uses HTMX for partial-page updates, keeping the server-side rendering model while achieving dynamic UX without a JavaScript framework.

### Task Tracking Layer

Every long-running operation (experiment run, batch, etc.) produces two objects:

- **`TaskState`** (`api/tasks.py`) — in-memory only. Holds the live subprocess handle, buffered output lines for SSE streaming, and a reference to the `TaskRecord`. Exists only while the server is running.
- **`TaskRecord`** (`experiment/task_record.py`) — Pydantic model persisted to `.tracking/tasks/{task_id}/record.json`. Survives server restarts. Includes `run_id` once the run completes.

**Retention and cleanup** — `task_record.py` provides two cleanup functions that are called at web-server startup (if `auto_cleanup` is enabled in `settings.yaml`) and from the `adgtk tasks cleanup` CLI command:

- `purge_old_task_records(max_age_days, max_count)` — two-pass cleanup: first removes finished tasks older than the TTL, then trims to the count cap (oldest first). Running tasks are never deleted.
- `delete_finished_task_records()` — removes all completed/error/stopped task directories regardless of age (used by the manual "Cleanup" button in the web UI).

```mermaid
classDiagram
    class TaskState {
        +task_id: str
        +label: str
        +status: str
        +lines: list[str]
        +run_id: Optional[str]
        +proc: asyncio.Process
        +task_record: TaskRecord
    }

    class TaskRecord {
        +task_id: str
        +experiment_name: str
        +label: str
        +status: str
        +pid: int
        +source: cli | web
        +started_at: datetime
        +finished_at: Optional[datetime]
        +returncode: Optional[int]
        +run_id: Optional[str]
    }

    TaskState --> TaskRecord : persists to disk
```

### Run Page Lifecycle (web-initiated experiment)

```mermaid
sequenceDiagram
    participant User
    participant Dashboard as GET /
    participant RunEP as POST /experiments/name/run
    participant TaskPage as GET /tasks/task_id
    participant SSE as GET /tasks/task_id/stream
    participant Report as GET /results/exp/run_id

    User->>Dashboard: click Quick Run
    Dashboard->>RunEP: htmx POST
    RunEP-->>Dashboard: HX-Redirect → /tasks/task_id
    Dashboard-->>User: browser navigates
    User->>TaskPage: GET /tasks/task_id
    TaskPage-->>User: full page (SSE container)
    User->>SSE: SSE connect
    SSE-->>User: stream output lines
    SSE-->>User: event: done
    SSE-->>User: event: navigate → /results/exp/run_id
    User->>Report: browser navigates to report
```

### SSE Event Protocol

The `/tasks/{task_id}/stream` endpoint emits three event types:

| Event | When | Data |
|-------|------|------|
| `message` (default) | Each captured output line | HTML `<div>` with escaped line |
| `done` | Task terminal state | HTML status badge (complete / error) |
| `navigate` | Complete + `run_id` known | Report URL `/results/{exp}/{run_id}` |
| `dashboardRefresh` | Any terminal state | empty — triggers dashboard list reload |

### Dashboard Refresh

The active-task indicator polls `/tasks/active-indicator` every 3 seconds. When no tasks are running, the response includes `HX-Trigger: dashboardRefresh`. The dashboard "Recent runs" card listens for this event (`hx-trigger="dashboardRefresh from:body"`) and re-fetches `/dashboard/recent-runs` to show the latest completed run without a full-page reload.

### Route Map

**Dashboard**

| Method | Path | Response |
|--------|------|----------|
| GET | `/` | Dashboard home page |
| GET | `/dashboard/recent-runs` | Recent runs list partial |
| GET | `/dashboard/stats` | Experiment/run count stats partial |

**Logs**

| Method | Path | Response |
|--------|------|----------|
| GET | `/logs` | Log browser page (grouped by category) |
| GET | `/logs/raw` | Raw log file text (`?file=<key>`) |

**Experiments**

| Method | Path | Response |
|--------|------|----------|
| POST | `/experiments/{name}/run` | `HX-Redirect: /tasks/{task_id}` |

**Tasks**

| Method | Path | Response |
|--------|------|----------|
| GET | `/tasks` | Full task list page |
| POST | `/tasks/cleanup` | Task list page (all finished removed) |
| GET | `/tasks/active-indicator` | Sidebar running-task indicator partial |
| GET | `/tasks/{task_id}` | Full task detail page |
| GET | `/tasks/{task_id}/stream` | SSE stream (text/event-stream) |
| POST | `/tasks/{task_id}/stop` | Updated active-indicator partial |

**Results**

| Method | Path | Response |
|--------|------|----------|
| GET | `/results` | Experiment list page |
| GET | `/results/{experiment}` | Runs list + report + journal tabs |
| POST | `/results/{experiment}/report` | Regenerated report HTML partial |
| GET | `/results/{experiment}/journal` | Journal entries partial |
| POST | `/results/{experiment}/journal` | Add entry; returns updated partial |
| DELETE | `/results/{experiment}/journal/{id}` | Delete entry; returns updated partial |
| GET | `/results/{experiment}/{run_id}` | Run detail page |
| GET | `/results/{experiment}/{run_id}/notes` | Researcher notes partial |
| POST | `/results/{experiment}/{run_id}/notes` | Add note; returns updated partial |
| DELETE | `/results/{experiment}/{run_id}/notes/{id}` | Delete note; returns updated partial |
| GET | `/results/{experiment}/{run_id}/images/{file}` | Serve run image file |
| GET | `/results/{experiment}/{run_id}/lograw` | Raw log text (scenario / llm) |
| GET | `/results/{experiment}/{run_id}/artifact` | Artifact preview page |
| GET | `/results/{experiment}/{run_id}/artifact/download` | Artifact file download |
| POST | `/results/sync` | Sync registry with disk; returns updated table |
| POST | `/results/validate` | Registry integrity check partial |

**Settings**

| Method | Path | Response |
|--------|------|----------|
| GET | `/settings` | Settings page |
| POST | `/settings` | Save settings; returns updated settings page |

---

## Settings System (`adgtk.utils.project_settings`)

User-configurable project settings are stored in `settings.yaml` at the project root. The file is created with defaults on first access, so no explicit migration step is needed when new settings are added.

```mermaid
classDiagram
    class ProjectSettings {
        +tasks: TaskSettings
    }

    class TaskSettings {
        +ttl_days: int = 30
        +max_count: int = 200
        +auto_cleanup: bool = True
    }

    ProjectSettings --> TaskSettings : contains
```

### `TaskSettings` fields

| Field | Default | Description |
|-------|---------|-------------|
| `ttl_days` | `30` | Delete finished task directories older than this many days |
| `max_count` | `200` | Keep at most this many task directories on disk |
| `auto_cleanup` | `True` | Run TTL + count cleanup automatically at web-server startup |

### Auto-cleanup lifecycle

At web-server startup (`adgtk-web`), after `run_bootstrap()`:

1. `cleanup_orphaned_tasks()` — mark any "running" tasks whose PID is dead as "error"
2. If `auto_cleanup` is `True`, call `purge_old_task_records(ttl_days, max_count)` to enforce the retention policy

The same cleanup can be triggered from the CLI:

```bash
adgtk tasks cleanup --auto   # apply TTL/count from settings.yaml
adgtk tasks cleanup          # delete ALL finished task records
```

---

## MCP Server (`adgtk.mcp_server`)

The MCP server exposes ADGTK capabilities as tools consumable by Claude and other MCP-compatible agents.

```mermaid
graph LR
    Claude["Claude / MCP Client"]
    MCP_SRV["MCP Server<br/>(adgtk-mcp)"]

    subgraph Tools
        T1["list_experiments"]
        T2["run_experiment"]
        T3["get_run_manifest"]
        T4["generate_experiment_report"]
        T5["get_factory_entries"]
        T6["create_measurements"]
        T7["list_batches / run_batch"]
        T8["list_studies / run_study"]
        T9["list_datasets / load_dataset"]
    end

    Claude -->|"MCP protocol"| MCP_SRV
    MCP_SRV --> T1
    MCP_SRV --> T2
    MCP_SRV --> T3
    MCP_SRV --> T4
    MCP_SRV --> T5
    MCP_SRV --> T6
    MCP_SRV --> T7
    MCP_SRV --> T8
    MCP_SRV --> T9
```

This enables agent-driven experiment orchestration: an AI agent can discover available experiments, run them, retrieve results, and adapt its strategy — all through the MCP protocol without human intervention.

---

## Data System (`adgtk.data`)

```mermaid
classDiagram
    class DatasetManager {
        +register(name, loader)
        +load(name) Dataset
        +list_available() list[str]
        +track_file(path)
    }
```

Supports HuggingFace `datasets` library as the primary dataset format, with file tracking to copy referenced datasets into the run's `datasets/` subfolder for reproducibility.

---

## Related Documents

- [System Overview](overview.md)
- [Data Flow](data-flow.md)
- [Decisions Index](decisions/index.md)
