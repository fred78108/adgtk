# MCP Server

ADGTK includes a built-in [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server. Once started, it exposes your project's experiments, results, studies, and components as tools that Claude and other MCP-capable agents can call directly — no CLI commands required.

This is useful for:

- Letting Claude run and inspect experiments on your behalf
- Automating research workflows from within an AI assistant
- Querying results and generating reports conversationally

---

## Starting the server

```bash
adgtk-mcp --project-dir /path/to/project
```

`--project-dir` defaults to the current working directory. The server validates the project on startup (checks for `bootstrap.py` and `results/`) and runs `bootstrap.py` to register your components before accepting any connections.

---

## Connecting from Claude Desktop

Add an entry to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "adgtk": {
      "command": "adgtk-mcp",
      "args": ["--project-dir", "/absolute/path/to/your/project"]
    }
  }
}
```

The path must be absolute. After saving the config, restart Claude Desktop and the ADGTK tools will appear in the tool list.

---

## Available tools

### Project

| Tool | Description |
|------|-------------|
| `project_status` | Return the project directory path and whether it is a valid ADGTK project |

### Experiments

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_experiments` | — | List all experiment blueprints available in the project |
| `run_experiment` | `name` | Run a blueprint and return the result summary |
| `generate_experiment_report` | `experiment_name` | Generate a markdown and CSV rollup report |
| `copy_experiment` | `source`, `destination` | Copy a blueprint to a new name |

`run_experiment` calls the same runner as `adgtk run`. The result includes the verdict, run ID, and the path to the results folder.

### Batches

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_batches` | — | List available batch job definition names |
| `run_batch` | `name` | Run all experiments in a batch file sequentially |

### Results

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_runs` | `experiment_name` *(optional)* | List runs, optionally filtered to one experiment |
| `get_run_details` | `experiment_name`, `run_id` | Return the config and results YAML for a specific run |
| `export_results` | `experiment_name`, `format` | Export all run records as JSON or CSV |
| `validate_results` | — | Check for orphaned folders, incomplete runs, and missing registry entries |

`export_results` defaults to JSON. Pass `format="csv"` for a CSV string ready to load into pandas.

### Studies

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_studies` | — | List available study blueprint names |
| `run_study` | `name` | Generate a cross-experiment study report and combined CSV |

### Factory and datasets

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_components` | `group` *(optional)*, `tags` *(optional)* | List registered factory components, optionally filtered |
| `list_datasets` | — | List the IDs of all registered datasets |

---

## Example session

Once connected, you can ask Claude things like:

> "List my experiments, then run `baseline` and show me the verdict."

> "Generate a report for `exp-gpt4o` and summarise the results."

> "Validate my results registry and tell me if anything is wrong."

> "Export the runs for `model-comparison` as CSV and show me the pass rate by tag."

Claude will call the appropriate MCP tools, read the returned data, and respond with a natural-language summary.

---

## Pairing with the IDE skill

The MCP server handles the *runtime* side of your workflow. For the *authoring* side — writing scenario classes, observations, and logging — install the ADGTK IDE skill:

```bash
adgtk-project install-skills          # Claude Code
adgtk-project install-skills --output-dir .cursor/rules   # Cursor
adgtk-project install-skills --output-dir .windsurf/rules # Windsurf
```

A typical session looks like: use the skill to scaffold a new scenario class, register it in `bootstrap.py`, then switch to the MCP server to run it, inspect the results, and decide whether to iterate — all without leaving your AI assistant.

---

## Architecture note

The MCP server and the CLI share the same underlying library functions — there is no duplication of logic. `run_experiment` calls the same `run_scenario()` function as `adgtk run`; `generate_experiment_report` calls the same `generate_experiment_report()` as `adgtk report`. The server simply provides an additional interface to the same project.
