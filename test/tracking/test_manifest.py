"""Tests for adgtk.tracking.manifest — _compute_metric_summaries, build_manifest, save.

The existing test_manifest_notes.py covers generate_markdown + researcher notes.
This file covers the remaining uncovered functions.

pytest test/tracking/test_manifest.py
"""

import json
import csv
from unittest.mock import patch, MagicMock
from adgtk.tracking.manifest import (
    RunManifest,
    _compute_metric_summaries,
    build_manifest,
    generate_markdown,
    save,
    MANIFEST_FILE,
    REPORT_FILE,
)
from adgtk.tracking.structure import ExperimentRunFolders, MetricSummary, ArtifactEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_folders(tmp_path) -> ExperimentRunFolders:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    conclusion_dir = tmp_path / "conclusion"
    conclusion_dir.mkdir()
    return ExperimentRunFolders(
        log_dir=str(tmp_path / "logs"),
        datasets=str(tmp_path / "datasets"),
        metrics=str(metrics_dir),
        images=str(tmp_path / "images"),
        other=str(tmp_path / "other"),
        conclusion=str(conclusion_dir),
        root_dir=str(tmp_path),
        experiment_name="test_exp",
        common=str(tmp_path / "common"),
        model_dir=str(tmp_path / "models"),
        train_log_dir=str(tmp_path / "train_logs"),
        llm_dir=str(tmp_path / "llm"),
    )


def _minimal_manifest(**overrides) -> RunManifest:
    defaults = dict(
        run_id="001",
        experiment_name="test_exp",
        timestamp_start="2026-06-07 10:00:00",
        timestamp_end="2026-06-07 10:00:05",
        duration_seconds=5.0,
        status="complete",
        config_snapshot={"key": "value"},
    )
    defaults.update(overrides)
    return RunManifest(**defaults)


# ---------------------------------------------------------------------------
# _compute_metric_summaries
# ---------------------------------------------------------------------------

def test_compute_metric_summaries_empty_folder(tmp_path):
    result = _compute_metric_summaries(str(tmp_path))
    assert result == {}


def test_compute_metric_summaries_missing_folder():
    result = _compute_metric_summaries("/nonexistent/path")
    assert result == {}


def test_compute_metric_summaries_reads_csv(tmp_path):
    csv_path = tmp_path / "accuracy.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([0.8, 0.9, 0.85])

    result = _compute_metric_summaries(str(tmp_path))
    assert "accuracy" in result
    s = result["accuracy"]
    assert s.n == 3
    assert abs(s.mean - 0.85) < 1e-6
    assert s.min == 0.8
    assert s.max == 0.9


def test_compute_metric_summaries_ignores_non_csv(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")
    result = _compute_metric_summaries(str(tmp_path))
    assert result == {}


def test_compute_metric_summaries_skips_bad_values(tmp_path):
    csv_path = tmp_path / "bad.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["not", "a", "number"])

    result = _compute_metric_summaries(str(tmp_path))
    assert result == {}


def test_compute_metric_summaries_skips_empty_row(tmp_path):
    csv_path = tmp_path / "empty.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([])

    result = _compute_metric_summaries(str(tmp_path))
    assert result == {}


def test_compute_metric_summaries_multiple_files(tmp_path):
    for name, values in [("loss", [0.5, 0.4, 0.3]), ("acc", [0.7, 0.8])]:
        with open(tmp_path / f"{name}.csv", "w", newline="") as f:
            csv.writer(f).writerow(values)

    result = _compute_metric_summaries(str(tmp_path))
    assert "loss" in result
    assert "acc" in result


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------

def test_build_manifest_assembles_correctly(tmp_path):
    folders = _make_folders(tmp_path)
    with open(folders.metrics + "/score.csv", "w", newline="") as f:
        csv.writer(f).writerow([1.0, 2.0, 3.0])

    with patch("adgtk.tracking.manifest.get_all", return_value=[]), \
         patch("adgtk.tracking.manifest.get_artifacts", return_value=[]):
        m = build_manifest(
            run_id="r1",
            experiment_name="exp1",
            timestamp_start="2026-01-01 00:00:00",
            timestamp_end="2026-01-01 00:01:00",
            duration_seconds=60.0,
            status="complete",
            config_snapshot={"model": "gpt-4"},
            result_metrics={"acc": 0.9},
            verdict="pass",
            verdict_note="above threshold",
            summary="great run",
            tags={"env": "prod"},
            folders=folders,
        )

    assert m.run_id == "r1"
    assert m.experiment_name == "exp1"
    assert m.verdict == "pass"
    assert m.result_metrics == {"acc": 0.9}
    assert "score" in m.metric_summaries
    assert m.tags == {"env": "prod"}
    assert m.summary == "great run"


# ---------------------------------------------------------------------------
# generate_markdown — additional coverage
# ---------------------------------------------------------------------------

def test_generate_markdown_with_result_metrics():
    m = _minimal_manifest(result_metrics={"accuracy": 0.95, "f1": 0.88})
    md = generate_markdown(m)
    assert "## Results" in md
    assert "accuracy" in md
    assert "0.95" in md


def test_generate_markdown_with_tags():
    m = _minimal_manifest(tags={"model": "gpt-4o"})
    md = generate_markdown(m)
    assert "## Tags" in md
    assert "model" in md


def test_generate_markdown_with_verdict_note():
    m = _minimal_manifest(verdict_note="above threshold")
    md = generate_markdown(m)
    assert "above threshold" in md


def test_generate_markdown_with_summary():
    m = _minimal_manifest(summary="this experiment was successful")
    md = generate_markdown(m)
    assert "this experiment was successful" in md


def test_generate_markdown_with_artifacts():
    m = _minimal_manifest(
        artifacts=[ArtifactEntry(path="/tmp/file.csv", purpose="other", size_bytes=1024)]
    )
    md = generate_markdown(m)
    assert "## Artifacts" in md
    assert "file.csv" in md
    assert "1,024 bytes" in md


def test_generate_markdown_with_agent_metric_summaries():
    m = _minimal_manifest(
        metric_summaries={
            "agent.success": MetricSummary(
                label="agent.success", n=10, mean=0.9, std=0.1, min=0.5, max=1.0
            )
        }
    )
    md = generate_markdown(m)
    assert "## Agent Performance" in md
    assert "Success Rate" in md


def test_generate_markdown_with_other_metric_summaries():
    m = _minimal_manifest(
        metric_summaries={
            "custom.score": MetricSummary(
                label="custom.score", n=5, mean=0.8, std=0.05, min=0.7, max=0.9
            )
        }
    )
    md = generate_markdown(m)
    assert "## Measurements" in md
    assert "custom.score" in md


def test_generate_markdown_includes_config():
    m = _minimal_manifest(config_snapshot={"lr": 0.01})
    md = generate_markdown(m)
    assert "## Configuration" in md
    assert "lr: 0.01" in md


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------

def test_save_writes_manifest_json(tmp_path):
    conclusion = tmp_path / "conclusion"
    conclusion.mkdir()
    m = _minimal_manifest()

    with patch("adgtk.tracking.researcher_notes.load_notes", return_value=None):
        save(m, str(conclusion))

    manifest_path = tmp_path / "conclusion" / MANIFEST_FILE
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["run_id"] == "001"
    assert data["experiment_name"] == "test_exp"


def test_save_writes_report_md(tmp_path):
    conclusion = tmp_path / "conclusion"
    conclusion.mkdir()
    m = _minimal_manifest()

    with patch("adgtk.tracking.researcher_notes.load_notes", return_value=None):
        save(m, str(conclusion))

    report_path = conclusion / REPORT_FILE
    assert report_path.exists()
    assert "test_exp" in report_path.read_text()


def test_save_includes_researcher_notes_in_report(tmp_path):
    conclusion = tmp_path / "conclusion"
    conclusion.mkdir()
    m = _minimal_manifest()

    mock_note = MagicMock()
    mock_note.timestamp = "2026-06-07 10:01:00"
    mock_note.text = "This is a researcher note."

    with patch("adgtk.tracking.researcher_notes.load_notes", return_value=[mock_note]):
        save(m, str(conclusion))

    report_path = conclusion / REPORT_FILE
    content = report_path.read_text()
    assert "Researcher Notes" in content
    assert "This is a researcher note." in content
