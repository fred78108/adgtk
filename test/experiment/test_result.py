"""Tests for adgtk.experiment.result — RunResult and RunResultBuilder.

pytest test/experiment/test_result.py
"""

import pytest
from adgtk.experiment.result import RunResult, RunResultBuilder


# ---------------------------------------------------------------------------
# RunResult — default construction
# ---------------------------------------------------------------------------

def test_run_result_defaults():
    r = RunResult()
    assert r.verdict == "inconclusive"
    assert r.metrics == {}
    assert r.tags == {}
    assert r.summary == ""
    assert r.verdict_note == ""


def test_run_result_explicit_values():
    r = RunResult(
        metrics={"accuracy": 0.9},
        verdict="pass",
        verdict_note="above threshold",
        tags={"model": "gpt-4o"},
        summary="great run",
    )
    assert r.verdict == "pass"
    assert r.metrics["accuracy"] == 0.9
    assert r.tags["model"] == "gpt-4o"
    assert r.summary == "great run"
    assert r.verdict_note == "above threshold"


# ---------------------------------------------------------------------------
# RunResultBuilder — individual methods
# ---------------------------------------------------------------------------

def test_builder_set_records_metric():
    b = RunResultBuilder()
    ret = b.set("f1", 0.87)
    assert ret is b
    result = b.finalize()
    assert result.metrics["f1"] == 0.87


def test_builder_set_multiple():
    b = RunResultBuilder()
    b.set("accuracy", 0.92).set("f1", 0.87)
    result = b.finalize()
    assert result.metrics["accuracy"] == 0.92
    assert result.metrics["f1"] == 0.87


def test_builder_tag_coerces_to_str():
    b = RunResultBuilder()
    ret = b.tag("temperature", 0.7)
    assert ret is b
    result = b.finalize()
    assert result.tags["temperature"] == "0.7"


def test_builder_tag_multiple():
    b = RunResultBuilder()
    b.tag("model", "gpt-4o").tag("variant", "v2")
    result = b.finalize()
    assert result.tags["model"] == "gpt-4o"
    assert result.tags["variant"] == "v2"


def test_builder_mark_pass():
    b = RunResultBuilder()
    ret = b.mark_pass("looks good")
    assert ret is b
    result = b.finalize()
    assert result.verdict == "pass"
    assert result.verdict_note == "looks good"


def test_builder_mark_pass_no_note():
    result = RunResultBuilder().mark_pass().finalize()
    assert result.verdict == "pass"
    assert result.verdict_note == ""


def test_builder_mark_fail():
    b = RunResultBuilder()
    ret = b.mark_fail("below threshold")
    assert ret is b
    result = b.finalize()
    assert result.verdict == "fail"
    assert result.verdict_note == "below threshold"


def test_builder_mark_inconclusive():
    b = RunResultBuilder()
    ret = b.mark_inconclusive("not enough data")
    assert ret is b
    result = b.finalize()
    assert result.verdict == "inconclusive"
    assert result.verdict_note == "not enough data"


def test_builder_mark_inconclusive_no_note():
    result = RunResultBuilder().mark_inconclusive().finalize()
    assert result.verdict == "inconclusive"
    assert result.verdict_note == ""


def test_builder_pass_if_condition_true():
    b = RunResultBuilder()
    b.set("accuracy", 0.92)
    ret = b.pass_if(lambda m: m["accuracy"] > 0.85, on_fail="below target")
    assert ret is b
    result = b.finalize()
    assert result.verdict == "pass"
    assert result.verdict_note == ""


def test_builder_pass_if_condition_false():
    b = RunResultBuilder()
    b.set("accuracy", 0.7)
    b.pass_if(lambda m: m["accuracy"] > 0.85, on_fail="below target")
    result = b.finalize()
    assert result.verdict == "fail"
    assert result.verdict_note == "below target"


def test_builder_summarize():
    b = RunResultBuilder()
    ret = b.summarize("experiment went well")
    assert ret is b
    result = b.finalize()
    assert result.summary == "experiment went well"


def test_builder_finalize_returns_run_result():
    result = RunResultBuilder().finalize()
    assert isinstance(result, RunResult)


def test_builder_default_verdict_is_inconclusive():
    result = RunResultBuilder().finalize()
    assert result.verdict == "inconclusive"


def test_builder_chained_fluent_api():
    result = (
        RunResultBuilder()
        .set("accuracy", 0.95)
        .tag("model", "claude")
        .mark_pass("excellent")
        .summarize("all metrics green")
        .finalize()
    )
    assert result.verdict == "pass"
    assert result.metrics["accuracy"] == 0.95
    assert result.tags["model"] == "claude"
    assert result.verdict_note == "excellent"
    assert result.summary == "all metrics green"
