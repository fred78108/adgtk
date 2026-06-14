"""study/report.py — Cross-experiment study rollup report generation.

Reads all run manifests for each experiment listed in a StudyBlueprint,
recalculates per-experiment statistics, and writes:

  study-results/{study_name}/study_report.md   ← markdown rollup report
  study-results/{study_name}/study_results.csv ← combined per-run CSV

The first run (run 0 by numeric sort) of each experiment is used as the
canonical configuration snapshot for that experiment.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Optional

import numpy as np

from adgtk.utils.defaults import STUDY_RESULTS_DIR
from adgtk.experiment.study.structure import StudyBlueprint
from adgtk.tracking.manifest import RunManifest
from adgtk.tracking.report import collect_experiment_data
from adgtk.tracking.structure import MetricSummary  # noqa: F401

STUDY_REPORT_FILE = "study_report.md"
STUDY_CSV_FILE = "study_results.csv"

_STUDY_AGENT_KPI_KEYS = [
    "agent.success",
    "agent.goal_completion",
    "agent.path_efficiency",
    "agent.first_attempt_success",
]
_STUDY_AGENT_KPI_DISPLAY = {
    "agent.success": "Success",
    "agent.goal_completion": "Goal Compl.",
    "agent.path_efficiency": "Path Eff.",
    "agent.first_attempt_success": "1st-Attempt",
}


# ----------------------------------------------------------------------
# Per-experiment data bundle
# ----------------------------------------------------------------------

class ExperimentData:
    """Collected data for a single experiment within a study."""

    def __init__(
        self,
        name: str,
        manifests: list[RunManifest],
        skipped: list[str],
        deviating: list[str],
        first_run_config: Optional[dict],
    ):
        self.name = name
        self.manifests = manifests
        self.skipped = skipped
        self.deviating = deviating
        self.first_run_config = first_run_config


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def _sort_key(run_id: str) -> tuple:
    parts = run_id.split(".", 1)
    try:
        return (int(parts[0]), parts[1] if len(parts) > 1 else "")
    except ValueError:
        return (0, run_id)


def collect_study_data(
    blueprint: StudyBlueprint,
) -> tuple[list[ExperimentData], list[str]]:
    """Load manifests and configs for every experiment in the blueprint.

    Args:
        blueprint: The StudyBlueprint listing experiments to collect.

    Returns:
        (experiment_data_list, missing_experiments)

        - experiment_data_list: One ExperimentData per found experiment.
        - missing_experiments: Experiment names with no results folder.
    """
    experiment_data: list[ExperimentData] = []
    missing: list[str] = []

    for exp_name in blueprint.experiments:
        try:
            result = collect_experiment_data(exp_name)
            manifests, skipped, run_configs, deviating = result
        except FileNotFoundError:
            missing.append(exp_name)
            continue

        # First run config: the run with the lowest numeric run_id
        first_run_config: Optional[dict] = None
        if run_configs:
            sorted_ids = sorted(run_configs.keys(), key=_sort_key)
            for rid in sorted_ids:
                if run_configs[rid] is not None:
                    first_run_config = run_configs[rid]
                    break

        experiment_data.append(
            ExperimentData(
                name=exp_name,
                manifests=manifests,
                skipped=skipped,
                deviating=deviating,
                first_run_config=first_run_config,
            )
        )

    return experiment_data, missing


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------

def _fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def _config_summary(config: Optional[dict]) -> str:
    """Render a brief flat summary of a config dict for the markdown table."""
    if not config:
        return "_no config_"
    parts = []
    for k, v in config.items():
        if isinstance(v, dict):
            continue
        parts.append(f"`{k}`: {v}")
    return ", ".join(parts) if parts else "_complex config_"


# ----------------------------------------------------------------------
# Per-experiment stats
# ----------------------------------------------------------------------

def _experiment_stats(manifests: list[RunManifest]) -> dict:
    """Compute aggregate statistics for a list of manifests."""
    n = len(manifests)
    if n == 0:
        return {}

    verdict_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    durations: list[float] = []

    for m in manifests:
        verdict_counts[m.verdict] = verdict_counts.get(m.verdict, 0) + 1
        status_counts[m.status] = status_counts.get(m.status, 0) + 1
        if m.duration_seconds is not None:
            durations.append(m.duration_seconds)

    result_metric_means: dict[str, float] = {}
    rm_keys: list[str] = []
    seen: set[str] = set()
    for m in manifests:
        for k in m.result_metrics:
            if k not in seen:
                seen.add(k)
                rm_keys.append(k)

    for k in rm_keys:
        vals = []
        for m in manifests:
            v = m.result_metrics.get(k)
            if v is not None:
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
        if vals:
            result_metric_means[k] = float(np.mean(vals))

    meas_stat: dict[str, dict] = {}
    meas_keys: list[str] = []
    seen_m: set[str] = set()
    for m in manifests:
        for k in m.metric_summaries:
            if k not in seen_m:
                seen_m.add(k)
                meas_keys.append(k)

    for k in meas_keys:
        run_means = [
            m.metric_summaries[k].mean
            for m in manifests
            if k in m.metric_summaries
        ]
        if run_means:
            arr = np.array(run_means)
            meas_stat[k] = {
                "runs": len(run_means),
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
            }

    dur_stats: dict = {}
    if durations:
        arr = np.array(durations)
        dur_stats = {
            "total": float(np.sum(arr)),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    return {
        "n": n,
        "verdict_counts": verdict_counts,
        "status_counts": status_counts,
        "duration": dur_stats,
        "result_metric_means": result_metric_means,
        "meas_stat": meas_stat,
    }


# ----------------------------------------------------------------------
# Markdown report generator
# ----------------------------------------------------------------------

def generate_study_markdown(
    blueprint: StudyBlueprint,
    experiment_data: list[ExperimentData],
    missing_experiments: list[str],
    generated_at: str,
) -> str:
    """Render the study rollup report as Markdown.

    Args:
        blueprint: The StudyBlueprint describing the study.
        experiment_data: Collected data for each found experiment.
        missing_experiments: Experiment names with no results folder.
        generated_at: Human-readable generation timestamp.

    Returns:
        Markdown string ready to be written to disk.
    """
    lines: list[str] = []

    # ── header ────────────────────────────────────────────────────────
    lines.append(f"# Study Report: {blueprint.name}")
    lines.append("")
    if blueprint.description:
        lines.append(f"_{blueprint.description}_")
        lines.append("")
    lines.append(f"**Generated**: {generated_at}  ")
    n_defined = len(blueprint.experiments)
    n_found = len(experiment_data)
    n_missing = len(missing_experiments)
    exp_summary = f"**Experiments**: {n_defined} defined, {n_found} found"
    if n_missing:
        exp_summary += f", {n_missing} missing"
    lines.append(exp_summary)
    if blueprint.tags:
        lines.append(f"**Tags**: {', '.join(blueprint.tags)}")
    lines.append("")

    if missing_experiments:
        lines.append("## Missing Experiments")
        lines.append("")
        lines.append(
            "> The following experiments were listed in the blueprint but had "
            "no results folder on disk:"
        )
        lines.append("")
        for exp in missing_experiments:
            lines.append(f"- `{exp}`")
        lines.append("")

    if not experiment_data:
        lines.append("> No experiment data found. Nothing to report.")
        return "\n".join(lines)

    # ── collect all metric/measurement keys across all experiments ─────
    all_rm_keys: list[str] = []
    seen_rm: set[str] = set()
    all_meas_keys: list[str] = []
    seen_meas: set[str] = set()
    for ed in experiment_data:
        for m in ed.manifests:
            for k in m.result_metrics:
                if k not in seen_rm:
                    seen_rm.add(k)
                    all_rm_keys.append(k)
            for k in m.metric_summaries:
                if k not in seen_meas:
                    seen_meas.add(k)
                    all_meas_keys.append(k)

    # ── cross-experiment comparison table ─────────────────────────────
    lines.append("## Cross-Experiment Overview")
    lines.append("")

    # Detect which agent KPI keys appear across any experiment
    present_kpi_keys = [
        k for k in _STUDY_AGENT_KPI_KEYS
        if any(
            any(k in m.metric_summaries for m in ed.manifests)
            for ed in experiment_data
        )
    ]

    hdr_parts = ["Experiment", "Runs", "Pass%", "Fail%", "Avg Duration"]
    for k in present_kpi_keys:
        hdr_parts.append(_STUDY_AGENT_KPI_DISPLAY.get(k, k))
    for k in all_rm_keys:
        hdr_parts.append(f"{k} (mean)")
    for k in all_meas_keys:
        if not k.startswith("agent."):
            hdr_parts.append(f"{k} (mean)")
    sep_parts = ["---"] * len(hdr_parts)
    lines.append("| " + " | ".join(hdr_parts) + " |")
    lines.append("| " + " | ".join(sep_parts) + " |")

    for ed in experiment_data:
        stats = _experiment_stats(ed.manifests)
        n = stats.get("n", 0)
        vc = stats.get("verdict_counts", {})
        dur = stats.get("duration", {})
        rm_means = stats.get("result_metric_means", {})
        meas_stat = stats.get("meas_stat", {})

        passes = vc.get("pass", 0)
        fails = vc.get("fail", 0)
        pass_pct = f"{passes/n:.0%}" if n else "--"
        fail_pct = f"{fails/n:.0%}" if n else "--"
        avg_dur = _fmt_duration(dur.get("mean"))

        row_parts = [ed.name, str(n), pass_pct, fail_pct, avg_dur]

        for k in present_kpi_keys:
            run_means = [
                m.metric_summaries[k].mean
                for m in ed.manifests if k in m.metric_summaries
            ]
            if run_means:
                row_parts.append(f"{np.mean(run_means):.1%}")
            else:
                row_parts.append("--")

        for k in all_rm_keys:
            v = rm_means.get(k)
            row_parts.append(f"{v:.4f}" if v is not None else "--")
        for k in all_meas_keys:
            if not k.startswith("agent."):
                s = meas_stat.get(k, {})
                row_parts.append(f"{s['mean']:.4f}" if s else "--")
        lines.append("| " + " | ".join(row_parts) + " |")

    lines.append("")

    # ── agent comparison section ───────────────────────────────────────
    if present_kpi_keys:
        lines.append("## Agent Performance Comparison")
        lines.append("")
        lines.append(
            "_Mean of per-run means for each experiment. "
            "Higher is better for all KPIs except Retries._"
        )
        lines.append("")

        col_hdr = " | ".join(
            _STUDY_AGENT_KPI_DISPLAY.get(k, k) for k in present_kpi_keys
        )
        col_sep = " | ".join("---:" for _ in present_kpi_keys)
        lines.append(
            f"| Experiment | Runs | {col_hdr} "
            f"| Avg Latency (s) | Avg Retries |"
        )
        lines.append(
            f"|------------|-----:|{col_sep}|----------------:|------------:|"
        )
        for ed in experiment_data:
            n = len(ed.manifests)
            cells: list[str] = []
            for k in present_kpi_keys:
                run_means = [
                    m.metric_summaries[k].mean
                    for m in ed.manifests if k in m.metric_summaries
                ]
                cells.append(
                    f"{np.mean(run_means):.1%}" if run_means else "--"
                )
            lat_means = [
                m.metric_summaries["agent.latency"].mean
                for m in ed.manifests if "agent.latency" in m.metric_summaries
            ]
            lat_str = f"{np.mean(lat_means):.3f}" if lat_means else "--"
            retry_means = [
                m.metric_summaries["agent.retry_count"].mean
                for m in ed.manifests
                if "agent.retry_count" in m.metric_summaries
            ]
            retry_str = f"{np.mean(retry_means):.2f}" if retry_means else "--"
            lines.append(
                f"| {ed.name} | {n} | {' | '.join(cells)} "
                f"| {lat_str} | {retry_str} |"
            )
        lines.append("")

    # ── per-experiment detail sections ────────────────────────────────
    lines.append("## Experiment Details")
    lines.append("")

    for ed in experiment_data:
        lines.append(f"### {ed.name}")
        lines.append("")

        n = len(ed.manifests)
        total = n + len(ed.skipped)
        lines.append(
            f"**Runs with data**: {n} of {total}"
            + (f"  ({len(ed.skipped)} skipped)" if ed.skipped else "")
        )
        lines.append("")

        # Config from first run
        lines.append("#### Configuration (first run)")
        lines.append("")
        if ed.first_run_config:
            lines.append("```yaml")
            import yaml
            lines.append(
                yaml.safe_dump(ed.first_run_config, sort_keys=False).rstrip()
            )
            lines.append("```")
        else:
            lines.append("_No configuration found._")
        lines.append("")

        if not ed.manifests:
            lines.append("_No run manifests found._")
            lines.append("")
            continue

        stats = _experiment_stats(ed.manifests)
        vc = stats.get("verdict_counts", {})
        dur = stats.get("duration", {})
        rm_means = stats.get("result_metric_means", {})
        meas_stat = stats.get("meas_stat", {})

        # Verdicts
        lines.append("#### Verdicts")
        lines.append("")
        lines.append("| Verdict | Count | % |")
        lines.append("|---------|------:|--:|")
        for verdict in ["pass", "fail", "inconclusive", "unknown"]:
            count = vc.get(verdict, 0)
            pct = 100.0 * count / n if n > 0 else 0.0
            lines.append(f"| {verdict} | {count} | {pct:.1f}% |")
        lines.append("")

        # Timing
        if dur:
            lines.append("#### Timing")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Total | {_fmt_duration(dur.get('total'))} |")
            lines.append(f"| Average | {_fmt_duration(dur.get('mean'))} |")
            lines.append(f"| Std dev | {dur.get('std', 0):.2f}s |")
            lines.append(f"| Min | {_fmt_duration(dur.get('min'))} |")
            lines.append(f"| Max | {_fmt_duration(dur.get('max'))} |")
            lines.append("")

        # Result metrics
        if rm_means:
            lines.append("#### Result Metrics (cross-run means)")
            lines.append("")
            lines.append("| Metric | Mean |")
            lines.append("|--------|-----:|")
            for k, v in rm_means.items():
                lines.append(f"| {k} | {v:.4f} |")
            lines.append("")

        # Per-run result metrics table
        if all_rm_keys:
            run_rm_keys = [
                k for k in all_rm_keys
                if any(k in m.result_metrics for m in ed.manifests)
            ]
            if run_rm_keys:
                lines.append("#### Per-Run Result Metrics")
                lines.append("")
                col_hdr = " | ".join(run_rm_keys)
                col_sep = " | ".join(["---"] * len(run_rm_keys))
                lines.append(f"| Run | {col_hdr} |")
                lines.append(f"|-----|{col_sep}|")
                for m in ed.manifests:
                    vals = " | ".join(
                        str(m.result_metrics.get(k, "--")) for k in run_rm_keys
                    )
                    lines.append(f"| `{m.run_id}` | {vals} |")
                lines.append("")

        # Agent performance (subset of measurement summaries)
        agent_kpi_present = [
            k for k in _STUDY_AGENT_KPI_KEYS if k in meas_stat
        ]
        if agent_kpi_present:
            lines.append("#### Agent Performance")
            lines.append("")
            lines.append("| Metric | Runs | Mean | Std | Min | Max |")
            lines.append("|--------|-----:|-----:|----:|----:|----:|")
            for k in agent_kpi_present:
                s = meas_stat[k]
                label = _STUDY_AGENT_KPI_DISPLAY.get(k, k)
                lines.append(
                    f"| {label} | {s['runs']} | {s['mean']:.1%} | "
                    f"{s['std']:.4f} | {s['min']:.1%} | {s['max']:.1%} |"
                )
            for k in ["agent.latency", "agent.retry_count",
                      "agent.tokens_in", "agent.tokens_out"]:
                if k in meas_stat:
                    s = meas_stat[k]
                    label = {
                        "agent.latency": "Latency (s)",
                        "agent.retry_count": "Retries",
                        "agent.tokens_in": "Input Tokens",
                        "agent.tokens_out": "Output Tokens",
                    }.get(k, k)
                    lines.append(
                        f"| {label} | {s['runs']} | {s['mean']:.4f} | "
                        f"{s['std']:.4f} | {s['min']:.4f} | {s['max']:.4f} |"
                    )
            lines.append("")

        # Non-agent measurement summaries
        non_agent_meas = {
            k: v for k, v in meas_stat.items()
            if not k.startswith("agent.")
        }
        if non_agent_meas:
            lines.append("#### Measurement Statistics (from per-run means)")
            lines.append("")
            lines.append("| Metric | Runs | Mean | Std | Min | Max |")
            lines.append("|--------|-----:|-----:|----:|----:|----:|")
            for k, s in non_agent_meas.items():
                lines.append(
                    f"| {k} | {s['runs']} | {s['mean']:.4f} | "
                    f"{s['std']:.4f} | {s['min']:.4f} | {s['max']:.4f} |"
                )
            lines.append("")

        # Config deviations warning
        if ed.deviating:
            lines.append("#### Configuration Deviations")
            lines.append("")
            lines.append(
                "> The following runs used a different `run.exp.config.yaml` "
                "than the majority baseline:"
            )
            lines.append("")
            for rid in ed.deviating:
                lines.append(f"- `{rid}`")
            lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# CSV export
# ----------------------------------------------------------------------

def save_study_csv(
    experiment_data: list[ExperimentData],
    output_dir: str,
) -> str:
    """Write a combined per-run CSV across all experiments.

    Columns mirror the experiment-level results.csv but include all
    experiments in a single file with ``experiment_name`` as the first
    grouping column.

    Args:
        experiment_data: Collected data for each experiment.
        output_dir: Directory where ``study_results.csv`` will be written.

    Returns:
        Path to the written CSV file.
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, STUDY_CSV_FILE)

    all_manifests: list[RunManifest] = []
    for ed in experiment_data:
        all_manifests.extend(ed.manifests)

    if not all_manifests:
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("")
        return csv_path

    # Collect column sets in insertion order across all experiments
    tag_keys: list[str] = []
    seen_tags: set[str] = set()
    rm_keys: list[str] = []
    seen_rm: set[str] = set()
    meas_keys: list[str] = []
    seen_meas: set[str] = set()

    for m in all_manifests:
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
        "experiment_name", "run_id",
        "timestamp_start", "timestamp_end", "duration_seconds",
        "status", "verdict", "verdict_note",
    ]
    tag_fields = [f"tag_{k}" for k in tag_keys]
    rm_fields = [f"metric_{k}" for k in rm_keys]
    meas_fields: list[str] = []
    for k in meas_keys:
        meas_fields += [
            f"meas_{k}_n", f"meas_{k}_mean",
            f"meas_{k}_std", f"meas_{k}_min", f"meas_{k}_max",
        ]

    fieldnames = base_fields + tag_fields + rm_fields + meas_fields

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in all_manifests:
            row: dict = {
                "experiment_name": m.experiment_name,
                "run_id": m.run_id,
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
                    for suffix in ("n", "mean", "std", "min", "max"):
                        row[f"meas_{k}_{suffix}"] = ""
            writer.writerow(row)

    return csv_path


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def generate_study_report(study_name: str) -> tuple[str, str]:
    """Generate and save the study rollup report and combined CSV.

    Loads the StudyBlueprint from ``studies/{study_name}.yaml``, collects
    data from each experiment, recalculates statistics, and writes both
    output files to ``study-results/{study_name}/``.

    Args:
        study_name: Name of the study (blueprint name, without .yaml).

    Returns:
        (report_path, csv_path) — paths to the files written.

    Raises:
        FileNotFoundError: If the study blueprint does not exist.
    """
    from adgtk.experiment.study.builder import load_study_blueprint

    blueprint = load_study_blueprint(study_name)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    experiment_data, missing = collect_study_data(blueprint)

    report_md = generate_study_markdown(
        blueprint=blueprint,
        experiment_data=experiment_data,
        missing_experiments=missing,
        generated_at=generated_at,
    )

    output_dir = os.path.join(STUDY_RESULTS_DIR, blueprint.name)
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, STUDY_REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    csv_path = save_study_csv(
        experiment_data=experiment_data,
        output_dir=output_dir,
    )

    return report_path, csv_path
