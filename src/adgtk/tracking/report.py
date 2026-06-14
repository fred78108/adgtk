"""Experiment-level rollup report generation.

Reads all run manifests for an experiment, computes aggregate
statistics, checks config consistency across runs, and writes:

  results/{experiment_name}/experiment_report.md
  results/{experiment_name}/common/results.csv

Config consistency check: compares run.exp.config.yaml across all runs.
If any run's config differs from the majority baseline, a WARNING is
prominently placed in the markdown report.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Optional

import numpy as np
import yaml

from adgtk.utils.defaults import EXP_RESULTS_FOLDER
from adgtk.tracking.manifest import RunManifest

EXPERIMENT_REPORT_FILE = "experiment_report.md"
RESULTS_CSV_FILE = "results.csv"
CONCLUSIONS_DIR = "conclusions"
MANIFEST_FILE = "run.manifest.json"
RUN_CONFIG_FILE = "run.exp.config.yaml"

_AGENT_KPI_KEYS = [
    "agent.success",
    "agent.goal_completion",
    "agent.path_efficiency",
    "agent.first_attempt_success",
]
_AGENT_KPI_DISPLAY = {
    "agent.success": "Success",
    "agent.goal_completion": "Goal Compl.",
    "agent.path_efficiency": "Path Eff.",
    "agent.first_attempt_success": "1st-Attempt",
}
_AGENT_TOKEN_KEYS = ["agent.tokens_in", "agent.tokens_out"]
_AGENT_TOKEN_DISPLAY = {
    "agent.tokens_in": "Input Tokens",
    "agent.tokens_out": "Output Tokens",
}


# ----------------------------------------------------------------------
# Internal data loading helpers
# ----------------------------------------------------------------------


def _load_manifest(run_path: str) -> Optional[RunManifest]:
    """Load a RunManifest from a run's conclusion folder.

    Args:
        run_path: Path to the run folder.

    Returns:
        A RunManifest instance when the manifest file exists and is valid,
        otherwise None.
    """
    manifest_path = os.path.join(run_path, CONCLUSIONS_DIR, MANIFEST_FILE)
    if not os.path.exists(manifest_path):
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RunManifest(**data)
    except (json.JSONDecodeError, Exception):
        return None


def _load_run_config(run_path: str) -> Optional[dict]:
    """Load a run.exp.config.yaml for a run.

    Args:
        run_path: Path to the run folder.

    Returns:
        A dict containing the parsed YAML config, or None if the file does not
        exist or cannot be parsed.
    """
    config_path = os.path.join(run_path, RUN_CONFIG_FILE)
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None


def _run_sort_key(run_id: str) -> tuple:
    """Create a sort key for run IDs.

    The key orders runs numerically by a leading integer prefix, then
    lexicographically by the remainder.

    Args:
        run_id: Run identifier string.

    Returns:
        A tuple used for sorting run IDs.
    """
    parts = run_id.split(".", 1)
    try:
        return (int(parts[0]), parts[1] if len(parts) > 1 else "")
    except ValueError:
        return (0, run_id)


# ----------------------------------------------------------------------
# Config consistency
# ----------------------------------------------------------------------


def _configs_equal(a: dict, b: dict) -> bool:
    """Compare two configs for deep equality.

    Args:
        a: First config mapping.
        b: Second config mapping.

    Returns:
        True if the configs are equal after JSON serialisation with sorted
        keys, otherwise False.
    """
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def check_config_consistency(
    run_configs: dict[str, Optional[dict]],
) -> tuple[Optional[dict], list[str]]:
    """Identify the baseline config and runs that deviate from it.

    The baseline is the config shared by the majority of runs. Runs with
    missing configs are excluded from the comparison and are not treated as
    deviating.

    Args:
        run_configs: Mapping of run_id to loaded config dict, or None.

    Returns:
        A tuple containing:
        - baseline_config: The majority config dict, or None if no configs
          are available.
        - deviating_run_ids: Sorted list of run IDs whose config differs from
          the baseline.
    """
    available = {
        rid: cfg
        for rid, cfg in run_configs.items()
        if cfg is not None
    }
    if not available:
        return None, []

    groups: list[tuple[dict, list[str]]] = []
    for run_id, cfg in available.items():
        placed = False
        for group_cfg, group_runs in groups:
            if _configs_equal(group_cfg, cfg):
                group_runs.append(run_id)
                placed = True
                break
        if not placed:
            groups.append((cfg, [run_id]))

    if len(groups) == 1:
        return groups[0][0], []

    groups.sort(key=lambda x: len(x[1]), reverse=True)
    baseline_cfg = groups[0][0]
    deviating: list[str] = []
    for _, group_runs in groups[1:]:
        deviating.extend(group_runs)

    return baseline_cfg, sorted(deviating, key=_run_sort_key)


# ----------------------------------------------------------------------
# Data collection
# ----------------------------------------------------------------------


def collect_experiment_data(
    experiment_name: str,
) -> tuple[list[RunManifest], list[str], dict[str, Optional[dict]], list[str]]:
    """Collect run manifests and configs for an experiment.

    Args:
        experiment_name: Name of the experiment to collect.

    Returns:
        A tuple containing:
        - manifests: Successfully loaded RunManifest objects sorted by
          timestamp_start then run_id.
        - skipped_run_ids: Run folders where no manifest could be loaded.
        - run_configs: Mapping of run_id to config dict or None.
        - deviating_run_ids: Runs whose run.exp.config.yaml differs from the
          majority baseline.

    Raises:
        FileNotFoundError: If the experiment results folder does not exist.
    """
    exp_path = os.path.join(EXP_RESULTS_FOLDER, experiment_name)
    if not os.path.exists(exp_path):
        raise FileNotFoundError(
            f"Experiment results folder not found: {exp_path}"
        )

    run_dirs = sorted(
        d
        for d in os.listdir(exp_path)
        if d != "common"
        and os.path.isdir(os.path.join(exp_path, d))
    )

    manifests: list[RunManifest] = []
    skipped: list[str] = []
    run_configs: dict[str, Optional[dict]] = {}

    for run_id in run_dirs:
        run_path = os.path.join(exp_path, run_id)
        manifest = _load_manifest(run_path)
        config = _load_run_config(run_path)
        run_configs[run_id] = config

        if manifest is not None:
            manifests.append(manifest)
        else:
            skipped.append(run_id)

    manifests.sort(
        key=lambda m: (m.timestamp_start or "", _run_sort_key(m.run_id))
    )

    _, deviating = check_config_consistency(run_configs)
    return manifests, skipped, run_configs, deviating


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------


def _fmt_duration(seconds: Optional[float]) -> str:
    """Format a duration in seconds as a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        A formatted duration string, or "--" when the value is None.
    """
    if seconds is None:
        return "--"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


# ----------------------------------------------------------------------
# Markdown report generator
# ----------------------------------------------------------------------


def generate_markdown_report(
    experiment_name: str,
    manifests: list[RunManifest],
    skipped_runs: list[str],
    deviating_run_ids: list[str],
    generated_at: str,
    journal_entries: Optional[list] = None,
) -> str:
    """Render a rolled-up experiment report as Markdown.

    Args:
        experiment_name: Name of the experiment.
        manifests: List of run manifests included in the report.
        skipped_runs: Run IDs skipped because their manifests could not be
          loaded.
        deviating_run_ids: Run IDs whose config differs from the baseline.
        generated_at: Timestamp when the report was generated.

    Returns:
        The rendered markdown report as a string.
    """
    lines: list[str] = []
    n = len(manifests)
    total_runs = n + len(skipped_runs)

    lines.append(f"# Experiment Report: {experiment_name}")
    lines.append("")
    lines.append(f"**Generated**: {generated_at}  ")
    lines.append(
        f"**Runs with data**: {n} of {total_runs}"
        + (
            f"  ({len(skipped_runs)} skipped — no manifest)"
            if skipped_runs
            else ""
        )
    )
    lines.append("")

    if not manifests:
        lines.append("> No run manifests found. Nothing to report.")
        lines.append("> Run `adgtk-results sync` to register existing runs.")
        return "\n".join(lines)

    if deviating_run_ids:
        lines.append("## WARNING: Configuration Inconsistency")
        lines.append("")
        lines.append(
            "> The following runs used a **different** "
            "`run.exp.config.yaml` than the majority of runs. Their "
            "results may not be directly comparable with the rest of "
            "the experiment."
        )
        lines.append("")
        for run_id in deviating_run_ids:
            lines.append(f"- `{run_id}`")
        lines.append("")
        lines.append(
            "> Use `adgtk-results show <experiment> <run_id>` to inspect "
            "an individual run's configuration."
        )
        lines.append("")

    verdict_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    durations: list[float] = []
    timestamps: list[str] = []

    for m in manifests:
        verdict_counts[m.verdict] = verdict_counts.get(m.verdict, 0) + 1
        status_counts[m.status] = status_counts.get(m.status, 0) + 1
        durations.append(m.duration_seconds)
        if m.timestamp_start:
            timestamps.append(m.timestamp_start)

    lines.append("## Summary")
    lines.append("")

    lines.append("### Verdicts")
    lines.append("")
    lines.append("| Verdict | Count | % |")
    lines.append("|---------|------:|--:|")
    for verdict in ["pass", "fail", "inconclusive", "unknown"]:
        count = verdict_counts.get(verdict, 0)
        pct = 100.0 * count / n if n > 0 else 0.0
        lines.append(f"| {verdict} | {count} | {pct:.1f}% |")
    lines.append("")

    lines.append("### Status")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|------:|")
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")

    if durations:
        dur_arr = [d for d in durations if d is not None]
        total_dur = sum(dur_arr)
        avg_dur = total_dur / len(dur_arr) if dur_arr else 0.0
        std_dur = float(np.std(dur_arr)) if len(dur_arr) > 1 else 0.0
        min_dur = min(dur_arr)
        max_dur = max(dur_arr)

        lines.append("### Timing")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total | {_fmt_duration(total_dur)} |")
        lines.append(f"| Average | {_fmt_duration(avg_dur)} |")
        lines.append(f"| Std dev | {std_dur:.2f}s |")
        lines.append(f"| Min | {_fmt_duration(min_dur)} |")
        lines.append(f"| Max | {_fmt_duration(max_dur)} |")
        if timestamps:
            ts_sorted = sorted(timestamps)
            lines.append(f"| First run | {ts_sorted[0]} |")
            lines.append(f"| Last run | {ts_sorted[-1]} |")
        lines.append("")

    # ── agent performance ────────────────────────────────────────────────
    present_kpi_keys = [
        k for k in _AGENT_KPI_KEYS
        if any(k in m.metric_summaries for m in manifests)
    ]
    if present_kpi_keys:
        lines.append("## Agent Performance")
        lines.append("")

        col_hdr = " | ".join(
            _AGENT_KPI_DISPLAY.get(k, k) for k in present_kpi_keys
        )
        col_sep = " | ".join("---:" for _ in present_kpi_keys)
        lines.append(f"| Run | {col_hdr} | Latency (s) | Steps |")
        lines.append(f"|-----|{col_sep}|------------:|------:|")
        for m in manifests:
            cells: list[str] = []
            for k in present_kpi_keys:
                s = m.metric_summaries.get(k)
                cells.append(f"{s.mean:.1%}" if s else "--")
            lat = m.metric_summaries.get("agent.latency")
            lat_str = f"{lat.mean:.3f}" if lat else "--"
            steps = m.metric_summaries.get("agent.latency")
            step_str = str(steps.n) if steps else "--"
            lines.append(
                f"| `{m.run_id}` | {' | '.join(cells)} "
                f"| {lat_str} | {step_str} |"
            )
        lines.append("")

        lines.append("### Cross-Run Agent Statistics")
        lines.append("")
        lines.append("| Metric | Runs | Mean | Std | Min | Max |")
        lines.append("|--------|-----:|-----:|----:|----:|----:|")
        for k in present_kpi_keys:
            run_means = [
                m.metric_summaries[k].mean
                for m in manifests if k in m.metric_summaries
            ]
            if run_means:
                arr = np.array(run_means)
                label = _AGENT_KPI_DISPLAY.get(k, k)
                lines.append(
                    f"| {label} | {len(run_means)} "
                    f"| {np.mean(arr):.1%} | {np.std(arr):.4f} "
                    f"| {np.min(arr):.1%} | {np.max(arr):.1%} |"
                )
        for k in ["agent.latency", "agent.retry_count"]:
            run_means = [
                m.metric_summaries[k].mean
                for m in manifests if k in m.metric_summaries
            ]
            if run_means:
                arr = np.array(run_means)
                label = "Latency (s)" if "latency" in k else "Retries"
                lines.append(
                    f"| {label} | {len(run_means)} "
                    f"| {np.mean(arr):.4f} | {np.std(arr):.4f} "
                    f"| {np.min(arr):.4f} | {np.max(arr):.4f} |"
                )
        lines.append("")

        present_token_keys = [
            k for k in _AGENT_TOKEN_KEYS
            if any(k in m.metric_summaries for m in manifests)
        ]
        if present_token_keys:
            lines.append("### Token Usage")
            lines.append("")
            lines.append(
                "| Metric | Total (all runs) | Avg/Step | Std/Step |"
            )
            lines.append(
                "|--------|----------------:|----------:|---------:|"
            )
            for k in present_token_keys:
                total = sum(
                    m.metric_summaries[k].mean * m.metric_summaries[k].n
                    for m in manifests if k in m.metric_summaries
                )
                step_means = [
                    m.metric_summaries[k].mean
                    for m in manifests if k in m.metric_summaries
                ]
                step_stds = [
                    m.metric_summaries[k].std
                    for m in manifests if k in m.metric_summaries
                ]
                label = _AGENT_TOKEN_DISPLAY.get(k, k)
                avg_mean = float(np.mean(step_means)) if step_means else 0.0
                avg_std = float(np.mean(step_stds)) if step_stds else 0.0
                lines.append(
                    f"| {label} | {total:,.0f} "
                    f"| {avg_mean:.1f} | {avg_std:.1f} |"
                )
            lines.append("")

        tool_keys: list[str] = []
        seen_tools: set[str] = set()
        for m in manifests:
            for k in m.metric_summaries:
                if k.startswith("agent.tool.") and k not in seen_tools:
                    seen_tools.add(k)
                    tool_keys.append(k)
        if tool_keys:
            lines.append("### Tool Usage (cross-run)")
            lines.append("")
            lines.append(
                "| Tool | Total Calls | Avg Success Rate |"
            )
            lines.append("|------|------------:|-----------------:|")
            tool_totals: dict[str, tuple[int, list[float]]] = {}
            for m in manifests:
                for k in tool_keys:
                    s = m.metric_summaries.get(k)
                    if s:
                        prev = tool_totals.get(k, (0, []))
                        tool_totals[k] = (prev[0] + s.n, prev[1] + [s.mean])
            for k in sorted(
                tool_keys,
                key=lambda x: tool_totals.get(x, (0, []))[0],
                reverse=True,
            ):
                total_calls, success_rates = tool_totals.get(k, (0, []))
                avg_sr = (
                    float(np.mean(success_rates)) if success_rates else 0.0
                )
                tool_name = k[len("agent.tool."):]
                lines.append(
                    f"| `{tool_name}` | {total_calls} | {avg_sr:.1%} |"
                )
            lines.append("")

    lines.append("## Per-Run Summary")
    lines.append("")
    lines.append("| Run | Started | Duration | Status | Verdict | Summary |")
    lines.append("|-----|---------|----------|--------|---------|---------|")
    for m in manifests:
        config_flag = " ⚠" if m.run_id in deviating_run_ids else ""
        summary_snippet = ""
        if m.summary:
            summary_snippet = (
                m.summary[:80] + "…" if len(m.summary) > 80 else m.summary
            )
        lines.append(
            "| "
            f"`{m.run_id}`{config_flag} | {m.timestamp_start or '--'} | "
            f"{_fmt_duration(m.duration_seconds)} | {m.status} | "
            f"{m.verdict} | {summary_snippet} |"
        )
    lines.append("")
    if deviating_run_ids:
        lines.append("_⚠ = config deviation from baseline_")
        lines.append("")

    rm_keys: list[str] = []
    seen_rm: set[str] = set()
    for m in manifests:
        for k in m.result_metrics:
            if k not in seen_rm:
                seen_rm.add(k)
                rm_keys.append(k)

    if rm_keys:
        lines.append("## Result Metrics")
        lines.append("")

        col_hdr = " | ".join(rm_keys)
        col_sep = " | ".join(["---"] * len(rm_keys))
        lines.append(f"| Run | {col_hdr} |")
        lines.append(f"|-----|{col_sep}|")
        for m in manifests:
            vals = " | ".join(
                str(m.result_metrics.get(k, "--")) for k in rm_keys
            )
            lines.append(f"| `{m.run_id}` | {vals} |")
        lines.append("")

        numeric_rollup: dict[str, list[float]] = {}
        for k in rm_keys:
            vals_f: list[float] = []
            for m in manifests:
                v = m.result_metrics.get(k)
                if v is not None:
                    try:
                        vals_f.append(float(v))
                    except (TypeError, ValueError):
                        pass
            if vals_f:
                numeric_rollup[k] = vals_f

        if numeric_rollup:
            lines.append("### Cross-Run Result Metric Statistics")
            lines.append("")
            lines.append("| Metric | n | Mean | Std | Min | Max |")
            lines.append("|--------|--:|-----:|----:|----:|----:|")
            for k, vals_f in numeric_rollup.items():
                arr = np.array(vals_f)
                lines.append(
                    "| "
                    f"{k} | {len(vals_f)} | {np.mean(arr):.4f} | "
                    f"{np.std(arr):.4f} | {np.min(arr):.4f} | "
                    f"{np.max(arr):.4f} |"
                )
            lines.append("")

    meas_keys: list[str] = []
    seen_meas: set[str] = set()
    for m in manifests:
        for k in m.metric_summaries:
            if k not in seen_meas:
                seen_meas.add(k)
                meas_keys.append(k)

    if meas_keys:
        lines.append("## Measurement Summaries")
        lines.append("")
        lines.append(
            "_Each cell shows `mean (std)` computed from all samples "
            "within that run._"
        )
        lines.append("")
        col_hdr = " | ".join(meas_keys)
        col_sep = " | ".join(["---"] * len(meas_keys))
        lines.append(f"| Run | {col_hdr} |")
        lines.append(f"|-----|{col_sep}|")
        for m in manifests:
            cells = []
            for k in meas_keys:
                s = m.metric_summaries.get(k)
                cells.append(
                    f"{s.mean:.4f} ({s.std:.4f})" if s else "--"
                )
            lines.append(f"| `{m.run_id}` | {' | '.join(cells)} |")
        lines.append("")

        lines.append("### Cross-Run Measurement Statistics")
        lines.append("")
        lines.append("_Statistics computed from per-run means._")
        lines.append("")
        lines.append(
            "| Metric | Runs | Mean of Means | Std of Means | Min Mean | "
            "Max Mean |"
        )
        lines.append("|--------|-----:|--------------:|-------------:|"
                     "---------:|---------:|")
        for k in meas_keys:
            run_means = [
                m.metric_summaries[k].mean
                for m in manifests
                if k in m.metric_summaries
            ]
            if run_means:
                arr = np.array(run_means)
                lines.append(
                    "| "
                    f"{k} | {len(run_means)} | {np.mean(arr):.4f} | "
                    f"{np.std(arr):.4f} | {np.min(arr):.4f} | "
                    f"{np.max(arr):.4f} |"
                )
        lines.append("")

    all_tag_keys: set[str] = set()
    for m in manifests:
        all_tag_keys.update(m.tags.keys())

    if all_tag_keys:
        lines.append("## Tags")
        lines.append("")
        for tag_key in sorted(all_tag_keys):
            tag_counts: dict[str, int] = {}
            for m in manifests:
                val = m.tags.get(tag_key)
                if val is not None:
                    tag_counts[val] = tag_counts.get(val, 0) + 1
            val_parts = ", ".join(
                f"`{v}` × {c}" for v, c in sorted(tag_counts.items())
            )
            lines.append(f"**{tag_key}**: {val_parts}  ")
        lines.append("")

    if skipped_runs:
        lines.append("## Skipped Runs (No Manifest)")
        lines.append("")
        lines.append(
            "The following run folders were found on disk but had no "
            "`run.manifest.json` and could not be included in this "
            "report:"
        )
        lines.append("")
        for run_id in skipped_runs:
            lines.append(f"- `{run_id}`")
        lines.append("")
        lines.append(
            "> Tip: run `adgtk-results sync` to register these runs in "
            "the registry."
        )
        lines.append("")

    if journal_entries:
        lines.append("## Experiment Journal")
        lines.append("")
        _TYPE_LABELS = {
            "note": "Note",
            "hypothesis": "Hypothesis",
            "finding": "Finding",
            "question": "Question",
        }
        for entry in journal_entries:
            label = _TYPE_LABELS.get(
                getattr(entry, "entry_type", "note"), "Note"
            )
            ts = getattr(entry, "timestamp", "")
            text = getattr(entry, "text", "")
            linked = getattr(entry, "linked_run_id", None)
            tags = getattr(entry, "tags", [])

            header_parts = [f"**[{label}]**"]
            if linked:
                header_parts.append(f"run: `{linked}`")
            if tags:
                header_parts.append(", ".join(f"`{t}`" for t in tags))
            if ts:
                header_parts.append(f"_{ts}_")
            lines.append(" · ".join(header_parts))
            lines.append("")
            lines.append(text)
            lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# CSV export
# ----------------------------------------------------------------------


def save_results_csv(
    manifests: list[RunManifest],
    common_folder: str,
) -> str:
    """Write per-run results to a CSV file in the common folder.

    Args:
        manifests: Sorted list of RunManifest objects.
        common_folder: Path to the experiment's common directory.

    Returns:
        Absolute path to the written CSV file.
    """
    os.makedirs(common_folder, exist_ok=True)
    csv_path = os.path.join(common_folder, RESULTS_CSV_FILE)

    if not manifests:
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("")
        return csv_path

    tag_keys: list[str] = []
    seen_tags: set[str] = set()
    rm_keys: list[str] = []
    seen_rm: set[str] = set()
    meas_keys: list[str] = []
    seen_meas: set[str] = set()

    for m in manifests:
        for k in m.tags:
            if k not in seen_tags:
                seen_tags.add(k)
                tag_keys.append(k)
        for k in m.result_metrics:
            if k not in seen_rm:
                seen_rm.add(k)
                rm_keys.append(k)
        for k in m.metric_summaries:
            if k not in seen_meas:
                seen_meas.add(k)
                meas_keys.append(k)

    base_fields = [
        "run_id",
        "experiment_name",
        "timestamp_start",
        "timestamp_end",
        "duration_seconds",
        "status",
        "verdict",
        "verdict_note",
    ]
    tag_fields = [f"tag_{k}" for k in tag_keys]
    rm_fields = [f"metric_{k}" for k in rm_keys]
    meas_fields: list[str] = []
    for k in meas_keys:
        meas_fields += [
            f"meas_{k}_n",
            f"meas_{k}_mean",
            f"meas_{k}_std",
            f"meas_{k}_min",
            f"meas_{k}_max",
        ]

    fieldnames = base_fields + tag_fields + rm_fields + meas_fields

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in manifests:
            row: dict = {
                "run_id": m.run_id,
                "experiment_name": m.experiment_name,
                "timestamp_start": m.timestamp_start,
                "timestamp_end": m.timestamp_end,
                "duration_seconds": m.duration_seconds,
                "status": m.status,
                "verdict": m.verdict,
                "verdict_note": m.verdict_note,
            }
            for k in tag_keys:
                row[f"tag_{k}"] = m.tags.get(k, "")
            for k in rm_keys:
                row[f"metric_{k}"] = m.result_metrics.get(k, "")
            for k in meas_keys:
                s = m.metric_summaries.get(k)
                if s:
                    row[f"meas_{k}_n"] = s.n
                    row[f"meas_{k}_mean"] = s.mean
                    row[f"meas_{k}_std"] = s.std
                    row[f"meas_{k}_min"] = s.min
                    row[f"meas_{k}_max"] = s.max
                else:
                    row[f"meas_{k}_n"] = ""
                    row[f"meas_{k}_mean"] = ""
                    row[f"meas_{k}_std"] = ""
                    row[f"meas_{k}_min"] = ""
                    row[f"meas_{k}_max"] = ""
            writer.writerow(row)

    return csv_path


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------


def generate_experiment_report(experiment_name: str) -> tuple[str, str]:
    """Generate and save the experiment rollup report and results CSV.

    Args:
        experiment_name: Name of the experiment.

    Returns:
        A tuple containing the report path and the CSV path.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    manifests, skipped, _run_configs, deviating = collect_experiment_data(
        experiment_name
    )

    common_folder = os.path.join(EXP_RESULTS_FOLDER, experiment_name, "common")
    from adgtk.tracking.experiment_journal import load_journal
    journal_entries = load_journal(common_folder)

    report_md = generate_markdown_report(
        experiment_name=experiment_name,
        manifests=manifests,
        skipped_runs=skipped,
        deviating_run_ids=deviating,
        generated_at=generated_at,
        journal_entries=journal_entries or None,
    )

    exp_path = os.path.join(EXP_RESULTS_FOLDER, experiment_name)
    report_path = os.path.join(exp_path, EXPERIMENT_REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    csv_path = save_results_csv(
        manifests=manifests, common_folder=common_folder)

    return report_path, csv_path
