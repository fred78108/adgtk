"""Tests for adgtk.tracking.report — experiment rollup report generation.

pytest test/tracking/test_report.py
"""

import csv
import os
import pytest
from unittest.mock import patch
from adgtk.tracking.report import (
    _load_manifest,
    _load_run_config,
    _run_sort_key,
    _configs_equal,
    _fmt_duration,
    check_config_consistency,
    collect_experiment_data,
    generate_markdown_report,
    save_results_csv,
    generate_experiment_report,
    CONCLUSIONS_DIR,
    MANIFEST_FILE,
    RUN_CONFIG_FILE,
)
from adgtk.tracking.manifest import RunManifest
from adgtk.tracking.structure import MetricSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manifest(**overrides) -> RunManifest:
    defaults = dict(
        run_id="001",
        experiment_name="exp",
        timestamp_start="2026-01-01 10:00:00",
        timestamp_end="2026-01-01 10:01:00",
        duration_seconds=60.0,
        status="complete",
        verdict="pass",
        config_snapshot={"model": "gpt-4"},
    )
    defaults.update(overrides)
    return RunManifest(**defaults)


def _write_manifest(run_path: str, manifest: RunManifest) -> None:
    conc = os.path.join(run_path, CONCLUSIONS_DIR)
    os.makedirs(conc, exist_ok=True)
    with open(os.path.join(conc, MANIFEST_FILE), "w") as f:
        f.write(manifest.model_dump_json(indent=2))


def _write_config(run_path: str, config: dict) -> None:
    import yaml
    with open(os.path.join(run_path, RUN_CONFIG_FILE), "w") as f:
        yaml.dump(config, f)


# ---------------------------------------------------------------------------
# _run_sort_key
# ---------------------------------------------------------------------------

def test_run_sort_key_numeric_prefix():
    assert _run_sort_key("3.abc") < _run_sort_key("10.abc")


def test_run_sort_key_no_dot():
    key = _run_sort_key("005")
    assert key == (5, "")


def test_run_sort_key_non_numeric():
    key = _run_sort_key("abc")
    assert key == (0, "abc")


def test_run_sort_key_with_suffix():
    k1 = _run_sort_key("1.alpha")
    k2 = _run_sort_key("1.beta")
    assert k1 < k2


# ---------------------------------------------------------------------------
# _configs_equal
# ---------------------------------------------------------------------------

def test_configs_equal_same():
    assert _configs_equal({"a": 1, "b": 2}, {"b": 2, "a": 1}) is True


def test_configs_equal_different():
    assert _configs_equal({"a": 1}, {"a": 2}) is False


def test_configs_equal_empty():
    assert _configs_equal({}, {}) is True


# ---------------------------------------------------------------------------
# _fmt_duration
# ---------------------------------------------------------------------------

def test_fmt_duration_none():
    assert _fmt_duration(None) == "--"


def test_fmt_duration_seconds():
    assert _fmt_duration(45.5) == "45.5s"


def test_fmt_duration_minutes():
    assert _fmt_duration(90.0) == "1m 30s"


def test_fmt_duration_hours():
    assert _fmt_duration(3700.0) == "1h 1m 40s"


# ---------------------------------------------------------------------------
# _load_manifest
# ---------------------------------------------------------------------------

def test_load_manifest_returns_manifest(tmp_path):
    run_path = tmp_path / "run1"
    m = _make_manifest(run_id="001")
    _write_manifest(str(run_path), m)
    result = _load_manifest(str(run_path))
    assert result is not None
    assert result.run_id == "001"


def test_load_manifest_missing_file(tmp_path):
    result = _load_manifest(str(tmp_path / "missing"))
    assert result is None


def test_load_manifest_bad_json(tmp_path):
    run_path = tmp_path / "run1"
    conc = run_path / CONCLUSIONS_DIR
    conc.mkdir(parents=True)
    (conc / MANIFEST_FILE).write_text("not json")
    result = _load_manifest(str(run_path))
    assert result is None


# ---------------------------------------------------------------------------
# _load_run_config
# ---------------------------------------------------------------------------

def test_load_run_config_returns_dict(tmp_path):
    run_path = tmp_path / "run1"
    run_path.mkdir()
    _write_config(str(run_path), {"lr": 0.01})
    result = _load_run_config(str(run_path))
    assert result == {"lr": 0.01}


def test_load_run_config_missing_file(tmp_path):
    result = _load_run_config(str(tmp_path / "norun"))
    assert result is None


# ---------------------------------------------------------------------------
# check_config_consistency
# ---------------------------------------------------------------------------

def test_check_config_consistency_all_same():
    cfg = {"model": "gpt-4"}
    run_configs = {"001": cfg, "002": cfg.copy(), "003": cfg.copy()}
    baseline, deviating = check_config_consistency(run_configs)
    assert baseline == cfg
    assert deviating == []


def test_check_config_consistency_one_deviation():
    baseline = {"model": "gpt-4"}
    deviant = {"model": "gpt-3.5"}
    run_configs = {
        "001": baseline,
        "002": baseline.copy(),
        "003": deviant,
    }
    b, deviating = check_config_consistency(run_configs)
    assert b == baseline
    assert "003" in deviating


def test_check_config_consistency_all_none():
    run_configs = {"001": None, "002": None}
    baseline, deviating = check_config_consistency(run_configs)
    assert baseline is None
    assert deviating == []


def test_check_config_consistency_empty():
    baseline, deviating = check_config_consistency({})
    assert baseline is None
    assert deviating == []


def test_check_config_consistency_mixed_none_and_valid():
    cfg = {"k": 1}
    run_configs = {"001": cfg, "002": None}
    baseline, deviating = check_config_consistency(run_configs)
    assert baseline == cfg
    assert deviating == []


# ---------------------------------------------------------------------------
# collect_experiment_data
# ---------------------------------------------------------------------------

def test_collect_experiment_data_raises_on_missing_folder(tmp_path):
    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        with pytest.raises(FileNotFoundError):
            collect_experiment_data("nonexistent")


def test_collect_experiment_data_empty_experiment(tmp_path):
    exp_path = tmp_path / "myexp"
    exp_path.mkdir()
    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        manifests, skipped, configs, deviating = collect_experiment_data("myexp")
    assert manifests == []
    assert skipped == []


def test_collect_experiment_data_with_manifests(tmp_path):
    exp_path = tmp_path / "myexp"
    exp_path.mkdir()
    run_path = exp_path / "001"
    run_path.mkdir()
    m = _make_manifest(run_id="001", experiment_name="myexp")
    _write_manifest(str(run_path), m)

    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        manifests, skipped, configs, deviating = collect_experiment_data("myexp")

    assert len(manifests) == 1
    assert manifests[0].run_id == "001"
    assert skipped == []


def test_collect_experiment_data_skips_run_without_manifest(tmp_path):
    exp_path = tmp_path / "myexp"
    exp_path.mkdir()
    (exp_path / "001").mkdir()

    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        manifests, skipped, configs, deviating = collect_experiment_data("myexp")

    assert manifests == []
    assert "001" in skipped


def test_collect_experiment_data_skips_common_folder(tmp_path):
    exp_path = tmp_path / "myexp"
    exp_path.mkdir()
    (exp_path / "common").mkdir()

    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        manifests, skipped, _, _ = collect_experiment_data("myexp")

    assert skipped == []


# ---------------------------------------------------------------------------
# generate_markdown_report
# ---------------------------------------------------------------------------

def test_generate_markdown_report_no_manifests():
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "No run manifests found" in md


def test_generate_markdown_report_basic():
    m = _make_manifest(verdict="pass", status="complete")
    md = generate_markdown_report(
        experiment_name="my_exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01 12:00:00",
    )
    assert "# Experiment Report: my_exp" in md
    assert "## Summary" in md
    assert "## Per-Run Summary" in md
    assert "pass" in md


def test_generate_markdown_report_with_skipped():
    m = _make_manifest()
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=["bad_run"],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "## Skipped Runs" in md
    assert "bad_run" in md


def test_generate_markdown_report_with_deviation_warning():
    m = _make_manifest(run_id="001")
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=["001"],
        generated_at="2026-01-01",
    )
    assert "WARNING: Configuration Inconsistency" in md


def test_generate_markdown_report_with_result_metrics():
    m = _make_manifest(result_metrics={"accuracy": 0.9, "f1": 0.85})
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "## Result Metrics" in md
    assert "accuracy" in md


def test_generate_markdown_report_with_tags():
    m = _make_manifest(tags={"model": "gpt-4", "variant": "v2"})
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "## Tags" in md
    assert "model" in md


def test_generate_markdown_report_with_agent_kpis():
    m = _make_manifest(
        metric_summaries={
            "agent.success": MetricSummary(
                label="agent.success", n=10, mean=0.8,
                std=0.1, min=0.5, max=1.0
            )
        }
    )
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "## Agent Performance" in md


def test_generate_markdown_report_with_measurement_summaries():
    m = _make_manifest(
        metric_summaries={
            "score": MetricSummary(
                label="score", n=5, mean=0.7, std=0.05, min=0.6, max=0.8
            )
        }
    )
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[m],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "## Measurement Summaries" in md


def test_generate_markdown_report_with_journal_entries():
    entry = type("E", (), {
        "entry_type": "finding",
        "timestamp": "2026-01-01",
        "text": "Found something interesting",
        "linked_run_id": "001",
        "tags": ["important"],
    })()
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=[_make_manifest()],
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
        journal_entries=[entry],
    )
    assert "## Experiment Journal" in md
    assert "Found something interesting" in md


def test_generate_markdown_report_timing_section():
    manifests = [
        _make_manifest(run_id="001", duration_seconds=30.0),
        _make_manifest(run_id="002", duration_seconds=90.0),
    ]
    md = generate_markdown_report(
        experiment_name="exp",
        manifests=manifests,
        skipped_runs=[],
        deviating_run_ids=[],
        generated_at="2026-01-01",
    )
    assert "### Timing" in md


# ---------------------------------------------------------------------------
# save_results_csv
# ---------------------------------------------------------------------------

def test_save_results_csv_empty_manifests(tmp_path):
    csv_path = save_results_csv([], str(tmp_path))
    assert os.path.exists(csv_path)
    assert open(csv_path).read() == ""


def test_save_results_csv_writes_header(tmp_path):
    m = _make_manifest()
    csv_path = save_results_csv([m], str(tmp_path))
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "001"
    assert rows[0]["verdict"] == "pass"


def test_save_results_csv_with_tags(tmp_path):
    m = _make_manifest(tags={"model": "gpt-4"})
    csv_path = save_results_csv([m], str(tmp_path))
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]["tag_model"] == "gpt-4"


def test_save_results_csv_with_metrics(tmp_path):
    m = _make_manifest(result_metrics={"accuracy": 0.9})
    csv_path = save_results_csv([m], str(tmp_path))
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]["metric_accuracy"] == "0.9"


def test_save_results_csv_with_measurement_summaries(tmp_path):
    m = _make_manifest(
        metric_summaries={
            "score": MetricSummary(
                label="score", n=5, mean=0.7, std=0.05, min=0.6, max=0.8
            )
        }
    )
    csv_path = save_results_csv([m], str(tmp_path))
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]["meas_score_mean"] == "0.7"
    assert rows[0]["meas_score_n"] == "5"


def test_save_results_csv_creates_common_folder(tmp_path):
    new_dir = str(tmp_path / "common" / "nested")
    save_results_csv([], new_dir)
    assert os.path.isdir(new_dir)


# ---------------------------------------------------------------------------
# generate_experiment_report
# ---------------------------------------------------------------------------

def test_generate_experiment_report_raises_when_no_folder(tmp_path):
    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)):
        with pytest.raises(FileNotFoundError):
            generate_experiment_report("nonexistent")


def test_generate_experiment_report_writes_files(tmp_path):
    exp_path = tmp_path / "myexp"
    exp_path.mkdir()
    run_path = exp_path / "001"
    run_path.mkdir()
    m = _make_manifest(run_id="001", experiment_name="myexp")
    _write_manifest(str(run_path), m)
    (exp_path / "common").mkdir()

    with patch("adgtk.tracking.report.EXP_RESULTS_FOLDER", str(tmp_path)), \
         patch("adgtk.tracking.experiment_journal.load_journal", return_value=None):
        report_path, csv_path = generate_experiment_report("myexp")

    assert os.path.exists(report_path)
    assert os.path.exists(csv_path)
    assert "myexp" in open(report_path).read()
