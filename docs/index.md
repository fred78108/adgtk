# ADGTK — Agentic Data Generation Toolkit

**ADGTK** is a Python framework for researching and validating agentic systems. It gives you a structured way to define experiments, run agents against evaluation datasets, record what happened, and compare results across runs — all with an eye toward reproducibility.

---

## Why ADGTK?

Running agent evaluations by hand is tedious and hard to reproduce. ADGTK provides scaffolding so you can focus on *what* you're testing, not the plumbing around it:

- **Lab journal** — the `observations` module records agent turns, findings, config decisions, and warnings as structured events during a run.
- **Automatic reporting** — after each run, a human-readable `report.md` and a machine-readable `run.manifest.json` are written automatically.
- **Extensible factory** — register your own scenarios, measurements, and components without forking the framework.
- **Cross-run comparison** — export all runs for an experiment to CSV or JSON for analysis in a notebook.

## Quick start

```bash
pip install adgtk

adgtk-project create my-research
cd my-research
adgtk build        # interactive experiment wizard
adgtk run          # run it
adgtk-results list # inspect results
```

## What's in the box

| Component | What it does |
|-----------|-------------|
| [Factory](api/factory.md) | Register and instantiate components by ID |
| [Experiment runner](api/experiment.md) | Build and execute experiment definitions |
| [Observations](tracking-results.md) | Record agent turns, notes, warnings, config decisions |
| [MetricTracker](tracking-results.md) | Numeric time-series tracking with CSV output |
| [AgentWriter](advanced/agent-writer.md) | Runtime metric writer — latency, tokens, tool calls, outcome per run |
| [Logging](advanced/logging.md) | Four-logger system — framework, scenario, batch, and LLM conversation logs |
| [MeasurementEngine](api/measurements.md) | Apply registered measurement functions to datasets |
| [DatasetManager](api/data.md) | Register and load evaluation datasets |
| [Studies](user-guide/studies.md) | Cross-experiment rollup — compare results across blueprints |
| [CLI tools](cli-reference.md) | Nine focused commands for projects, experiments, studies, results |
| [MCP server](mcp-server.md) | Expose project operations as MCP tools for Claude and other agents |
| [Web interface](web-interface.md) | Browser-based UI for running experiments and browsing results |

## Navigation

- **[Getting Started](getting-started.md)** — install, create a project, run your first experiment
- **[Concepts](concepts.md)** — understand the core ideas before diving in
- **[User Guide](user-guide/creating-scenarios.md)** — step-by-step guides for common tasks
- **[Studies](user-guide/studies.md)** — compare results across multiple experiments
- **[CLI Reference](cli-reference.md)** — every command, every flag
- **[Tracking & Results](tracking-results.md)** — observations, metrics, manifest, and cross-run export
- **[Advanced](advanced/batch-jobs.md)** — batch jobs, AgentWriter, custom measurements, bootstrap configuration, logging
- **[MCP Server](mcp-server.md)** — use ADGTK from Claude and other MCP-capable agents
- **[Web Interface](web-interface.md)** — browser-based UI with live streaming, results browser, and study management
- **[API Reference](api/factory.md)** — full API documentation

## Project status

ADGTK is in active development (v0.3, alpha). The API may change between minor versions. Feedback and issues welcome at [github.com/fred78108/adgtk](https://github.com/fred78108/adgtk).
