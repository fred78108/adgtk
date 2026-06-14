"""test_researcher_notes.py

Unit tests for adgtk.tracking.researcher_notes — the sidecar note store
that lets researchers annotate completed runs without touching RunManifest.

Each test uses ``tmp_path`` (pytest built-in) so no test touches the real
results tree.

Run with: pytest test/tracking/test_researcher_notes.py
"""

import json
from pathlib import Path

import pytest

from adgtk.tracking.researcher_notes import (
    ResearcherNote,
    NOTES_FILE,
    add_note,
    delete_note,
    load_notes,
    save_notes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_raw(folder: Path, data) -> None:
    """Write arbitrary bytes/text to the notes file for corruption tests."""
    (folder / NOTES_FILE).write_text(data, encoding="utf-8")


def _read_raw(folder: Path):
    return json.loads((folder / NOTES_FILE).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# ResearcherNote model
# ---------------------------------------------------------------------------

def test_model_stores_all_fields():
    note = ResearcherNote(note_id="abc", timestamp="2026-01-01 00:00:00", text="hello")
    assert note.note_id == "abc"
    assert note.timestamp == "2026-01-01 00:00:00"
    assert note.text == "hello"


def test_model_round_trips_via_model_dump():
    note = ResearcherNote(note_id="x", timestamp="t", text="content")
    loaded = ResearcherNote(**note.model_dump())
    assert loaded == note


# ---------------------------------------------------------------------------
# load_notes
# ---------------------------------------------------------------------------

def test_load_notes_returns_empty_list_when_file_absent(tmp_path):
    assert load_notes(str(tmp_path)) == []


def test_load_notes_returns_empty_list_when_dir_absent(tmp_path):
    missing = tmp_path / "no_such_dir"
    assert load_notes(str(missing)) == []


def test_load_notes_returns_notes_from_file(tmp_path):
    notes = [
        ResearcherNote(note_id="1", timestamp="2026-01-01 00:00:00", text="a"),
        ResearcherNote(note_id="2", timestamp="2026-01-02 00:00:00", text="b"),
    ]
    save_notes(notes, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert len(loaded) == 2
    assert loaded[0].note_id == "1"
    assert loaded[1].note_id == "2"


def test_load_notes_returns_researcher_note_instances(tmp_path):
    notes = [ResearcherNote(note_id="x", timestamp="t", text="y")]
    save_notes(notes, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert all(isinstance(n, ResearcherNote) for n in loaded)


def test_load_notes_returns_empty_list_on_corrupt_json(tmp_path):
    _write_raw(tmp_path, "{{not valid json{{")
    assert load_notes(str(tmp_path)) == []


def test_load_notes_returns_empty_list_on_empty_array(tmp_path):
    _write_raw(tmp_path, "[]")
    assert load_notes(str(tmp_path)) == []


def test_load_notes_preserves_text_with_newlines(tmp_path):
    notes = [ResearcherNote(note_id="1", timestamp="t", text="line1\nline2")]
    save_notes(notes, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert loaded[0].text == "line1\nline2"


# ---------------------------------------------------------------------------
# save_notes
# ---------------------------------------------------------------------------

def test_save_notes_creates_file(tmp_path):
    save_notes([], str(tmp_path))
    assert (tmp_path / NOTES_FILE).exists()


def test_save_notes_creates_directory_if_absent(tmp_path):
    nested = tmp_path / "a" / "b" / "conclusions"
    save_notes([], str(nested))
    assert (nested / NOTES_FILE).exists()


def test_save_notes_writes_valid_json(tmp_path):
    notes = [ResearcherNote(note_id="z", timestamp="t", text="x")]
    save_notes(notes, str(tmp_path))
    data = _read_raw(tmp_path)
    assert isinstance(data, list)
    assert data[0]["note_id"] == "z"


def test_save_notes_empty_list_writes_empty_array(tmp_path):
    save_notes([], str(tmp_path))
    data = _read_raw(tmp_path)
    assert data == []


def test_save_notes_overwrites_existing_file(tmp_path):
    first = [ResearcherNote(note_id="1", timestamp="t", text="first")]
    second = [ResearcherNote(note_id="2", timestamp="t", text="second")]
    save_notes(first, str(tmp_path))
    save_notes(second, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].note_id == "2"


def test_save_notes_round_trips_multiple_notes(tmp_path):
    notes = [
        ResearcherNote(note_id=str(i), timestamp="t", text=f"note {i}")
        for i in range(5)
    ]
    save_notes(notes, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert [n.text for n in loaded] == [f"note {i}" for i in range(5)]


# ---------------------------------------------------------------------------
# add_note
# ---------------------------------------------------------------------------

def test_add_note_returns_researcher_note_instance(tmp_path):
    note = add_note("hello", str(tmp_path))
    assert isinstance(note, ResearcherNote)


def test_add_note_text_is_stripped(tmp_path):
    note = add_note("  trimmed  ", str(tmp_path))
    assert note.text == "trimmed"


def test_add_note_assigns_non_empty_note_id(tmp_path):
    note = add_note("x", str(tmp_path))
    assert note.note_id


def test_add_note_assigns_timestamp(tmp_path):
    note = add_note("x", str(tmp_path))
    assert note.timestamp


def test_add_note_persists_to_disk(tmp_path):
    note = add_note("persisted", str(tmp_path))
    loaded = load_notes(str(tmp_path))
    ids = [n.note_id for n in loaded]
    assert note.note_id in ids


def test_add_note_appends_to_existing(tmp_path):
    add_note("first", str(tmp_path))
    add_note("second", str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert len(loaded) == 2


def test_add_note_preserves_order(tmp_path):
    add_note("alpha", str(tmp_path))
    add_note("beta", str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert loaded[0].text == "alpha"
    assert loaded[1].text == "beta"


def test_add_note_note_ids_are_unique(tmp_path):
    notes = [add_note(f"note {i}", str(tmp_path)) for i in range(10)]
    ids = [n.note_id for n in notes]
    assert len(set(ids)) == 10


def test_add_note_creates_directory_if_absent(tmp_path):
    nested = tmp_path / "conclusions"
    add_note("x", str(nested))
    assert (nested / NOTES_FILE).exists()


# ---------------------------------------------------------------------------
# delete_note
# ---------------------------------------------------------------------------

def test_delete_note_returns_true_on_success(tmp_path):
    note = add_note("to delete", str(tmp_path))
    assert delete_note(note.note_id, str(tmp_path)) is True


def test_delete_note_returns_false_when_id_not_found(tmp_path):
    assert delete_note("nonexistent-id", str(tmp_path)) is False


def test_delete_note_returns_false_when_file_absent(tmp_path):
    assert delete_note("any-id", str(tmp_path)) is False


def test_delete_note_removes_note_from_store(tmp_path):
    note = add_note("to delete", str(tmp_path))
    delete_note(note.note_id, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    ids = [n.note_id for n in loaded]
    assert note.note_id not in ids


def test_delete_note_preserves_remaining_notes(tmp_path):
    n1 = add_note("keep", str(tmp_path))
    n2 = add_note("delete me", str(tmp_path))
    delete_note(n2.note_id, str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].note_id == n1.note_id


def test_delete_note_persists_change_to_disk(tmp_path):
    note = add_note("x", str(tmp_path))
    delete_note(note.note_id, str(tmp_path))
    reloaded = load_notes(str(tmp_path))
    assert all(n.note_id != note.note_id for n in reloaded)


def test_delete_note_unknown_id_does_not_modify_store(tmp_path):
    add_note("safe", str(tmp_path))
    delete_note("does-not-exist", str(tmp_path))
    loaded = load_notes(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].text == "safe"


def test_delete_note_can_delete_all_one_by_one(tmp_path):
    notes = [add_note(f"n{i}", str(tmp_path)) for i in range(3)]
    for note in notes:
        delete_note(note.note_id, str(tmp_path))
    assert load_notes(str(tmp_path)) == []
