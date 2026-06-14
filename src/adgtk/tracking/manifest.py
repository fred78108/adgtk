"""manifest.py — RunManifest and report generation.

RunManifest is the single structured document produced for every run.
It is the source of truth for the markdown report and the future web interface.

Disk layout (written by runner.py):
  results/{run_id}/conclusion/run.manifest.json   ← canonical JSON
  results/{run_id}/conclusion/report.md            ← generated markdown view
"""

from __future__ import annotations

import csv
import os
from typing import Any, Literal
import numpy as np
from pydantic import BaseModel
from adgtk.tracking.observations import AnyObservation, get_all, get_artifacts
from adgtk.tracking.structure import (
    ArtifactEntry,
    ExperimentRunFolders,
    MetricSummary
)

MANIFEST_FILE = "run.manifest.json"
REPORT_FILE = "report.md"

# ----------------------------------------------------------------------
# RunManifest model
# ----------------------------------------------------------------------


class RunManifest(BaseModel):
    manifest_version: str = "1.0"

    # identity
    run_id: str
    experiment_name: str

    # timing
    timestamp_start: str
    timestamp_end: str
    duration_seconds: float

    # status
    status: Literal["complete", "incomplete", "failed"]
    verdict: Literal["pass", "fail", "inconclusive", "unknown"] = "unknown"
    verdict_note: str = ""

    # full experiment YAML snapshotted at run time
    config_snapshot: dict[str, Any]

    # from RunResult
    result_metrics: dict[str, Any] = {}
    summary: str = ""

    # key=value labels mirrored into RunEntryModel for fast index queries
    tags: dict[str, str] = {}

    # computed from MetricTracker CSVs
    metric_summaries: dict[str, MetricSummary] = {}

    # researcher observations recorded during the run
    observations: list[AnyObservation] = []

    # files produced during the run
    artifacts: list[ArtifactEntry] = []


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------


def _compute_metric_summaries(
    metrics_folder: str,
) -> dict[str, MetricSummary]:
    """Read all CSV files in the metrics folder and compute descriptive stats.
    """
    summaries: dict[str, MetricSummary] = {}
    if not os.path.exists(metrics_folder):
        return summaries

    for fname in os.listdir(metrics_folder):
        if not fname.endswith(".csv"):
            continue
        label = fname[:-4]  # strip .csv
        fpath = os.path.join(metrics_folder, fname)
        try:
            with open(fpath, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    values = [float(v) for v in row if v.strip()]
                    if not values:
                        continue
                    arr = np.array(values, dtype=float)
                    summaries[label] = MetricSummary(
                        label=label,
                        n=len(values),
                        mean=float(np.mean(arr)),
                        std=float(np.std(arr)),
                        min=float(np.min(arr)),
                        max=float(np.max(arr)),
                    )
                    break  # one row per file
        except (ValueError, csv.Error):
            pass

    return summaries


def build_manifest(
    run_id: str,
    experiment_name: str,
    timestamp_start: str,
    timestamp_end: str,
    duration_seconds: float,
    status: Literal["complete", "incomplete", "failed"],
    config_snapshot: dict[str, Any],
    result_metrics: dict[str, Any],
    verdict: Literal["pass", "fail", "inconclusive", "unknown"],
    verdict_note: str,
    summary: str,
    tags: dict[str, str],
    folders: ExperimentRunFolders,
) -> RunManifest:
    """Assemble a RunManifest from all run data.

    Reads observations and artifacts from the module-level state in
    observations.py, and computes metric summaries from the CSV files
    written to folders.metrics.
    """
    return RunManifest(
        run_id=run_id,
        experiment_name=experiment_name,
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end,
        duration_seconds=duration_seconds,
        status=status,
        verdict=verdict,
        verdict_note=verdict_note,
        config_snapshot=config_snapshot,
        result_metrics=result_metrics,
        summary=summary,
        tags=tags,
        metric_summaries=_compute_metric_summaries(folders.metrics),
        observations=get_all(),
        artifacts=get_artifacts(),
    )


# ----------------------------------------------------------------------
# Markdown report
# ----------------------------------------------------------------------

_VERDICT_LABEL = {
    "pass": "PASS",
    "fail": "FAIL",
    "inconclusive": "INCONCLUSIVE",
    "unknown": "UNKNOWN",
}

_OBS_KIND_LABEL = {
    "note": "NOTE",
    "warn": "WARN",
    "agent_turn": "AGENT",
    "config_note": "CONFIG",
    "metric_event": "METRIC",
}

# ----------------------------------------------------------------------
# AgentWriter metric groupings
# ----------------------------------------------------------------------

_AGENT_KPI_LABELS: dict[str, str] = {
    "agent.success": "Success Rate",
    "agent.goal_completion": "Goal Completion",
    "agent.path_efficiency": "Path Efficiency",
    "agent.first_attempt_success": "First-Attempt Success",
}
_AGENT_EXEC_LABELS: dict[str, str] = {
    "agent.latency": "Latency (s)",
    "agent.retry_count": "Retries",
    "agent.error": "Error Rate",
    "agent.tool_call_count": "Tool Calls / Step",
}
_AGENT_TOKEN_LABELS: dict[str, str] = {
    "agent.tokens_in": "Input Tokens",
    "agent.tokens_out": "Output Tokens",
}
_AGENT_TOOL_PREFIX = "agent.tool."
_RATE_METRICS = {
    "agent.success",
    "agent.goal_completion",
    "agent.path_efficiency",
    "agent.first_attempt_success",
    "agent.error",
}


def _block_bar(value: float, width: int = 20) -> str:
    """UTF-8 block progress bar for a [0, 1] value."""
    filled = round(max(0.0, min(1.0, value)) * width)
    return "█" * filled + "░" * (width - filled)


def generate_markdown(
    manifest: RunManifest,
    researcher_notes: list | None = None,
) -> str:
    """Render a RunManifest as a human-readable markdown report."""
    lines: list[str] = []

    # ── header ───────────────────────────────────────────────────────────
    verdict_str = _VERDICT_LABEL.get(manifest.verdict, manifest.verdict)
    lines.append(f"# {manifest.experiment_name} — Run {manifest.run_id}")
    lines.append("")
    lines.append(
        f"**Verdict**: {verdict_str} | "
        f"**Duration**: {manifest.duration_seconds:.1f}s | "
        f"**Started**: {manifest.timestamp_start}"
    )
    if manifest.verdict_note:
        lines.append(f"> {manifest.verdict_note}")
    if manifest.summary:
        lines.append("")
        lines.append(manifest.summary)
    lines.append("")

    # ── tags ─────────────────────────────────────────────────────────────
    if manifest.tags:
        lines.append("## Tags")
        lines.append("")
        tag_pairs = " | ".join(f"`{k}`: {v}" for k, v in manifest.tags.items())
        lines.append(tag_pairs)
        lines.append("")

    # ── result metrics ───────────────────────────────────────────────────
    if manifest.result_metrics:
        lines.append("## Results")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in manifest.result_metrics.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    # ── agent performance (from metric_summaries with agent.* prefix) ──────
    agent_sums = {
        k: v for k, v in manifest.metric_summaries.items()
        if k.startswith("agent.")
    }
    other_sums = {
        k: v for k, v in manifest.metric_summaries.items()
        if not k.startswith("agent.")
    }

    if agent_sums:
        lines.append("## Agent Performance")
        lines.append("")

        kpi_data = [
            (label, agent_sums[k])
            for k, label in _AGENT_KPI_LABELS.items()
            if k in agent_sums
        ]
        if kpi_data:
            lines.append("### Outcome KPIs")
            lines.append("")
            lines.append("| Metric | Score | Trend | n | ±Std |")
            lines.append("|--------|------:|-------|--:|-----:|")
            for label, s in kpi_data:
                bar = _block_bar(s.mean)
                lines.append(
                    f"| {label} | **{s.mean:.1%}** | `{bar}` "
                    f"| {s.n} | {s.std:.4f} |"
                )
            lines.append("")

        exec_data = [
            (label, agent_sums[k])
            for k, label in _AGENT_EXEC_LABELS.items()
            if k in agent_sums
        ]
        if exec_data:
            lines.append("### Step Execution")
            lines.append("")
            lines.append("| Metric | Mean | Std | Min | Max | n |")
            lines.append("|--------|-----:|----:|----:|----:|--:|")
            for label, s in exec_data:
                lines.append(
                    f"| {label} | {s.mean:.4f} | {s.std:.4f} "
                    f"| {s.min:.4f} | {s.max:.4f} | {s.n} |"
                )
            lines.append("")

        token_data = [
            (label, agent_sums[k])
            for k, label in _AGENT_TOKEN_LABELS.items()
            if k in agent_sums
        ]
        if token_data:
            lines.append("### Token Budget")
            lines.append("")
            lines.append(
                "| Metric | Total | Per-Step Mean | Std | Min | Max |"
            )
            lines.append(
                "|--------|------:|--------------:|----:|----:|----:|"
            )
            for label, s in token_data:
                total = int(s.mean * s.n)
                lines.append(
                    f"| {label} | {total:,} | {s.mean:.1f} "
                    f"| {s.std:.1f} | {s.min:.0f} | {s.max:.0f} |"
                )
            lines.append("")

        tool_data = sorted(
            [
                (k[len(_AGENT_TOOL_PREFIX):], v)
                for k, v in agent_sums.items()
                if k.startswith(_AGENT_TOOL_PREFIX)
            ],
            key=lambda x: x[1].n,
            reverse=True,
        )
        if tool_data:
            tool_total = sum(s.n for _, s in tool_data)
            lines.append("### Tool Distribution")
            lines.append("")
            lines.append("| Tool | Calls | Share | Success Rate |")
            lines.append("|------|------:|------:|-------------:|")
            for tool_name, s in tool_data:
                share = s.n / tool_total if tool_total else 0.0
                bar = _block_bar(share, width=12)
                lines.append(
                    f"| `{tool_name}` | {s.n} "
                    f"| {share:.1%} `{bar}` | {s.mean:.1%} |"
                )
            lines.append("")

    # ── other measurement summaries ──────────────────────────────────────
    if other_sums:
        lines.append("## Measurements")
        lines.append("")
        lines.append("| Metric | n | Mean | Std | Min | Max |")
        lines.append("|--------|---|------|-----|-----|-----|")
        for s in other_sums.values():
            lines.append(
                f"| {s.label} | {s.n} | {s.mean:.4f} | "
                f"{s.std:.4f} | {s.min:.4f} | {s.max:.4f} |"
            )
        lines.append("")

    # ── observations ─────────────────────────────────────────────────────
    if manifest.observations:
        lines.append("## Observations")
        lines.append("")
        for obs in manifest.observations:
            kind_label = _OBS_KIND_LABEL.get(obs.kind, obs.kind.upper())
            tag_str = f" `{'` `'.join(obs.tags)}`" if obs.tags else ""
            ts = obs.timestamp

            if obs.kind in ("note", "warn"):
                header = f"**[{ts}] {kind_label}**{tag_str}  "
                lines.append(header)
                lines.append(f"{obs.message}")  # type: ignore[union-attr]
            elif obs.kind == "agent_turn":
                model = obs.model  # type: ignore[union-attr]
                tokens_in = obs.tokens_in  # type: ignore[union-attr]
                tokens_out = obs.tokens_out  # type: ignore[union-attr]
                latency_ms = obs.latency_ms  # type: ignore[union-attr]
                prompt = obs.prompt  # type: ignore[union-attr]
                response = obs.response  # type: ignore[union-attr]
                meta_parts = []
                if model:
                    meta_parts.append(f"model={model}")
                if tokens_in is not None:
                    meta_parts.append(f"in={tokens_in}")
                if tokens_out is not None:
                    meta_parts.append(f"out={tokens_out}")
                if latency_ms is not None:
                    meta_parts.append(f"{latency_ms:.0f}ms")
                meta_str = f" ({', '.join(meta_parts)})" if meta_parts else ""
                header = (
                    f"**[{ts}] {kind_label}**{meta_str}{tag_str}"
                )
                lines.append(header)
                lines.append(f"> **Prompt:** {prompt}")
                lines.append(f"> **Response:** {response}")
            elif obs.kind == "config_note":
                param = obs.parameter  # type: ignore[union-attr]
                val = obs.value  # type: ignore[union-attr]
                rationale = obs.rationale  # type: ignore[union-attr]
                header = (
                    f"**[{ts}] {kind_label}** "
                    f"`{param}={val}`{tag_str}  "
                )
                lines.append(header)
                lines.append(f"{rationale}")
            elif obs.kind == "metric_event":
                step = obs.step  # type: ignore[union-attr]
                step_str = "" if step is None else f" step={step}"
                metric = obs.metric  # type: ignore[union-attr]
                val = obs.value  # type: ignore[union-attr]
                note = obs.note  # type: ignore[union-attr]
                header = (
                    f"**[{ts}] {kind_label}** "
                    f"`{metric}={val}`{step_str}{tag_str}"
                )
                lines.append(header)
                if note:
                    lines.append(f"  {note}")
            lines.append("")

    # ── artifacts ────────────────────────────────────────────────────────
    if manifest.artifacts:
        lines.append("## Artifacts")
        lines.append("")
        for a in manifest.artifacts:
            size_str = f" ({a.size_bytes:,} bytes)" if a.size_bytes else ""
            lines.append(f"- `{a.path}` — {a.purpose}{size_str}")
        lines.append("")

    # ── researcher notes ──────────────────────────────────────────────────
    if researcher_notes:
        lines.append("## Researcher Notes")
        lines.append("")
        for note in researcher_notes:
            lines.append(f"**[{note.timestamp}]**  ")
            lines.append(note.text)
            lines.append("")

    # ── config snapshot ──────────────────────────────────────────────────
    lines.append("## Configuration")
    lines.append("")
    lines.append("```yaml")
    # Simple key: value dump without pulling in yaml dependency here
    for k, v in manifest.config_snapshot.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def save(manifest: RunManifest, conclusion_folder: str) -> None:
    """Write run.manifest.json and report.md to the conclusion folder."""
    from adgtk.tracking.researcher_notes import load_notes

    manifest_path = os.path.join(conclusion_folder, MANIFEST_FILE)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    notes = load_notes(conclusion_folder)
    report_path = os.path.join(conclusion_folder, REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown(manifest, researcher_notes=notes or None))
