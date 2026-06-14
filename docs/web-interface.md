# Web Interface

ADGTK includes a browser-based web interface that covers the same workflows as the CLI — running experiments, inspecting results, building studies — from any browser, including over a network.

```bash
adgtk-web --project-dir /path/to/project
```

On startup, the URL and access token are printed to the console:

```
  ADGTK Web Interface
  http://127.0.0.1:8000/?token=a3f9c2d1e8b4...
```

Open that URL to authenticate. A session cookie is set so subsequent visits don't require the token again until the server restarts.

---

## Starting the server

```bash
# Minimal — serves on localhost:8000 with a random token
adgtk-web --project-dir ~/research/my-project

# Bind to all interfaces for remote access
adgtk-web --project-dir ~/research/my-project --host 0.0.0.0 --port 8080

# Disable auth (local development only)
adgtk-web --project-dir ~/research/my-project --no-auth

# Fixed token (useful when running behind a reverse proxy)
adgtk-web --project-dir ~/research/my-project --token mysecrettoken
```

### All options

| Flag | Default | Description |
|------|---------|-------------|
| `--project-dir PATH` | *(required)* | ADGTK project directory to serve |
| `--host HOST` | `127.0.0.1` | Network interface to bind to |
| `--port PORT` | `8000` | Port to listen on |
| `--token TOKEN` | *(random)* | Auth token; random if not supplied |
| `--no-auth` | `False` | Disable authentication |

---

## Authentication

The web interface uses the same token-based authentication pattern as Jupyter Notebook.

- A random 32-character hex token is generated at startup unless `--token` or `--no-auth` is provided.
- The first time you visit the URL with `?token=<TOKEN>` in the query string, a session cookie (`adgtk_token`) is set for the browser.
- All subsequent requests from that browser are authenticated via the cookie — the token in the URL is only needed once.
- Restarting the server with a new random token invalidates existing sessions.

**For remote access:** bind with `--host 0.0.0.0` and use a fixed `--token` so the URL stays stable across restarts. Consider running behind nginx or Caddy with TLS if the server is publicly reachable.

**For local development:** `--no-auth` removes the authentication step entirely.

---

## Pages

### Dashboard

The home page gives a project overview at a glance:

- Experiment count and recent run summary
- **Quick run** — select any blueprint from a dropdown and run it immediately; output streams live into the page

### Experiments

Lists all experiment blueprints found in `blueprints/`.

| Action | What it does |
|--------|-------------|
| **Run** | Starts the experiment; output streams live in the Output panel |
| **Report** | Generates the rollup markdown and CSV report for that experiment |
| **Copy** | Opens a modal to duplicate the blueprint under a new name |

Run output appears in a dark terminal-style panel on the right side of the page. Each line of the experiment's stdout is streamed in real time via Server-Sent Events — the page stays live and shows progress without polling.

### Results

Three-level browser: experiment list → experiment detail (runs + report + journal) → run detail.

**Experiment list** shows run count, last verdict, and last run timestamp for every experiment that has results on disk. A **Sync** button reconciles the registry with what is actually on disk, and a **Validate** button checks for:

- Orphaned folders — result directories on disk not registered in `.tracking/runs.json`
- Incomplete runs — registered runs with no `results.yaml`
- Missing folders — registry entries whose result directory no longer exists

**Experiment detail** has three tabs:

- **Runs** — table of every recorded run with status, verdict, and duration. Click any row to drill into the run detail.
- **Report** — the auto-generated rollup report (`experiment_report.md`) rendered as HTML. The report is regenerated automatically when a new run is detected, and can be refreshed on demand with the **Regenerate report** button.
- **Journal** — a per-experiment research journal where you can write notes, hypotheses, findings, and questions linked to specific runs.

**Run detail** shows the full run summary across several tabs: result metrics, verdict, observations from the manifest, configuration snapshot, measurement charts, agent metric time-series, and run images. A **Researcher notes** panel lets you annotate individual runs with timestamped free-text notes.

The **Logs** tab shows every log file written for that run:

- **scenario.log** — the scenario-logger output for the run, rendered as scrollable plain text.
- **LLM log files** — each file in the run's `llm/` folder appears as its own sub-tab. Files with a `.jsonl` extension (the NDJSON sidecar written by `create_llm_logger`) are rendered as a **conversation thread**: each message gets a coloured role chip (`USER`, `ASSISTANT`, `SYSTEM`, `TOOL`) and an indented content block. Files with a `.log` extension are rendered as plain text with ANSI codes stripped.

### Batches

Lists all batch job definitions found in `batches/`. Click **Run** next to a batch to execute it; stdout streams live in the output panel, identical to the experiment runner.

### Studies

**Saved studies** lists existing study blueprints with a **Run** button that generates the cross-experiment markdown report and combined CSV.

**New study** provides an inline form to create a study blueprint: name, description, and a checklist of experiments with results on disk. Submitting creates `studies/{name}.yaml` immediately.

### Factory

Read-only component browser. Filter by group (scenario, measurement, etc.) or by tag using the controls at the top of the page. The filter applies on the server and refreshes the table without a full page reload.

### Datasets

Lists all dataset IDs registered in `.tracking/datasets.json`. Each entry has a **Retire** button that removes it from the registry (the file itself is not deleted). To register new datasets use `adgtk-ds register` from the CLI.

### Logs

The **Logs** page (`/logs`) provides a two-panel file browser for everything in the `logs/` directory:

- **Left panel** — log files grouped by category: `framework` (project-level logs), `common`, and `runs/{name}` (one group per experiment or batch job).
- **Right panel** — contents of the selected file, tail-read to the last 200 KB for responsiveness.

Click any file name to load it. This is the quickest way to review the batch log after an unattended run or to inspect the framework log for low-level diagnostic output.

---

### Tasks

Lists all task records from `.tracking/tasks/` — the unified history of experiment runs whether started from the CLI or the web UI. Each row shows the task ID, status, experiment name, source (cli/web), start time, and duration.

Click any row to open the task detail page, which shows the captured output and (once complete) a link to the run's results page.

A **Cleanup** button at the top of the list removes all finished task directories (complete, error, and stopped) at once. Running tasks are never affected.

### Settings

View and edit project-level settings stored in `settings.yaml` at the project root.

**Task retention settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| TTL (days) | `30` | Automatically delete finished task records older than this |
| Max records | `200` | Keep at most this many task directories |
| Auto cleanup | On | Apply retention policy at server startup |

Changes take effect the next time the web server starts (for auto-cleanup) or the next time `adgtk tasks cleanup --auto` is run from the CLI.

---

## Live output streaming

When you run an experiment or batch job from the web interface, the server starts the corresponding CLI command as a subprocess and streams its stdout to the browser line by line using [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). The output panel updates in real time — no polling, no page reloads.

The stream connection is per-task and buffered server-side, so reconnecting (e.g. after a page refresh) replays all output captured so far. A final `✓ complete` or `✗ error` line is appended when the process exits.

---

## Remote access

To use the web interface from another machine:

```bash
adgtk-web --project-dir ~/research/my-project \
           --host 0.0.0.0 \
           --port 8080 \
           --token mysecrettoken
```

Then open `http://<server-ip>:8080/?token=mysecrettoken` in any browser.

**Running as a background service** (systemd example):

```ini
[Unit]
Description=ADGTK Web Interface
After=network.target

[Service]
Type=simple
User=fred
WorkingDirectory=/home/fred/research/my-project
ExecStart=adgtk-web --project-dir /home/fred/research/my-project \
                     --host 0.0.0.0 --port 8080 --token mysecrettoken
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## Technology

The web interface is implemented entirely in Python — no JavaScript build step is required and no Node.js dependency is introduced. It uses:

- **[FastAPI](https://fastapi.tiangolo.com)** — web framework and request routing
- **[Jinja2](https://jinja.palletsprojects.com)** — server-side HTML templating (already a core ADGTK dependency)
- **[HTMX](https://htmx.org)** — dynamic page updates without writing JavaScript (loaded from CDN)
- **[Alpine.js](https://alpinejs.dev)** — lightweight client-side state for modals and toggles (loaded from CDN)
- **[Tailwind CSS](https://tailwindcss.com)** — utility-first styling (loaded from CDN)
- **[uvicorn](https://www.uvicorn.org)** — ASGI server

All CDN resources are loaded from well-known, stable URLs. The interface works in any modern browser with no extensions or plugins required.
