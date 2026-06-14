"""test_manifest_notes.py

Tests for the researcher-notes integration in manifest.py:
  - generate_markdown renders a "Researcher Notes" section when notes are present
  - generate_markdown omits the section when notes is None or empty
  - Notes section appears before the Configuration section
  - save() reads the notes sidecar and passes it to generate_markdown

Run with: pytest test/tracking/test_manifest_notes.py
"""

import json
from adgtk.tracking.manifest import RunManifest, generate_markdown, save
from adgtk.tracking.researcher_notes import ResearcherNote, NOTES_FILE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_note(text: str, ts: str = "2026-06-07 10:01:00") -> ResearcherNote:
    return ResearcherNote(note_id="n1", timestamp=ts, text=text)


# ---------------------------------------------------------------------------
# generate_markdown — no notes
# ---------------------------------------------------------------------------

def test_generate_markdown_no_notes_section_when_none():
    md = generate_markdown(_minimal_manifest(), researcher_notes=None)
    assert "## Researcher Notes" not in md


def test_generate_markdown_no_notes_section_when_empty_list():
    md = generate_markdown(_minimal_manifest(), researcher_notes=[])
    assert "## Researcher Notes" not in md


def test_generate_markdown_no_notes_section_when_omitted():
    md = generate_markdown(_minimal_manifest())
    assert "## Researcher Notes" not in md


# ---------------------------------------------------------------------------
# generate_markdown — with notes
# ---------------------------------------------------------------------------

def test_generate_markdown_notes_section_present():
    note = _make_note("interesting finding")
    md = generate_markdown(_minimal_manifest(), researcher_notes=[note])
    assert "## Researcher Notes" in md


def test_generate_markdown_note_text_included():
    note = _make_note("the accuracy dropped after step 5")
    md = generate_markdown(_minimal_manifest(), researcher_notes=[note])
    assert "the accuracy dropped after step 5" in md


def test_generate_markdown_note_timestamp_included():
    note = _make_note("some note", ts="2026-06-07 10:01:00")
    md = generate_markdown(_minimal_manifest(), researcher_notes=[note])
    assert "2026-06-07 10:01:00" in md


def test_generate_markdown_multiple_notes_all_included():
    notes = [
        ResearcherNote(note_id="a", timestamp="t1", text="first note"),
        ResearcherNote(note_id="b", timestamp="t2", text="second note"),
    ]
    md = generate_markdown(_minimal_manifest(), researcher_notes=notes)
    assert "first note" in md
    assert "second note" in md


def test_generate_markdown_notes_before_configuration():
    note = _make_note("my note")
    md = generate_markdown(_minimal_manifest(), researcher_notes=[note])
    notes_pos = md.index("## Researcher Notes")
    config_pos = md.index("## Configuration")
    assert notes_pos < config_pos


def test_generate_markdown_notes_section_follows_markdown_heading():
    note = _make_note("x")
    md = generate_markdown(_minimal_manifest(), researcher_notes=[note])
    lines = md.splitlines()
    heading_lines = [l for l in lines if l.strip() == "## Researcher Notes"]
    assert len(heading_lines) == 1


# ---------------------------------------------------------------------------
# save() — sidecar integration
# ---------------------------------------------------------------------------

def test_save_writes_manifest_json(tmp_path):
    m = _minimal_manifest()
    save(m, str(tmp_path))
    assert (tmp_path / "run.manifest.json").exists()


def test_save_writes_report_md(tmp_path):
    m = _minimal_manifest()
    save(m, str(tmp_path))
    assert (tmp_path / "report.md").exists()


def test_save_includes_notes_when_sidecar_present(tmp_path):
    notes_data = [
        {"note_id": "1", "timestamp": "2026-06-07 10:00:00", "text": "sidecar note"}
    ]
    (tmp_path / NOTES_FILE).write_text(json.dumps(notes_data), encoding="utf-8")
    m = _minimal_manifest()
    save(m, str(tmp_path))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Researcher Notes" in report
    assert "sidecar note" in report


def test_save_no_notes_section_when_sidecar_absent(tmp_path):
    m = _minimal_manifest()
    save(m, str(tmp_path))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Researcher Notes" not in report


def test_save_no_notes_section_when_sidecar_empty(tmp_path):
    (tmp_path / NOTES_FILE).write_text("[]", encoding="utf-8")
    m = _minimal_manifest()
    save(m, str(tmp_path))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Researcher Notes" not in report


def test_save_multiple_sidecar_notes_all_appear_in_report(tmp_path):
    notes_data = [
        {"note_id": "1", "timestamp": "t1", "text": "note alpha"},
        {"note_id": "2", "timestamp": "t2", "text": "note beta"},
    ]
    (tmp_path / NOTES_FILE).write_text(json.dumps(notes_data), encoding="utf-8")
    m = _minimal_manifest()
    save(m, str(tmp_path))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "note alpha" in report
    assert "note beta" in report


def test_save_manifest_json_is_valid_json(tmp_path):
    m = _minimal_manifest()
    save(m, str(tmp_path))
    data = json.loads((tmp_path / "run.manifest.json").read_text(encoding="utf-8"))
    assert data["run_id"] == "001"


def test_save_report_contains_configuration_section(tmp_path):
    m = _minimal_manifest()
    save(m, str(tmp_path))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Configuration" in report
