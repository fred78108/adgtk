"""test_experiment_journal.py

Unit tests for adgtk.tracking.experiment_journal — the cross-run journal
that lets researchers record hypotheses, findings, notes, and questions
at the experiment level without touching any run's RunManifest.

Each test uses ``tmp_path`` (pytest built-in) so no test touches the real
results tree.

Run with: pytest test/journals/test_experiment_journal.py
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from adgtk.tracking.experiment_journal import (
    JOURNAL_FILE,
    ExperimentJournalEntry,
    add_entry,
    delete_entry,
    load_journal,
    save_journal,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_raw(folder: Path, data: str) -> None:
    (folder / JOURNAL_FILE).write_text(data, encoding="utf-8")


def _read_raw(folder: Path):
    return json.loads((folder / JOURNAL_FILE).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# ExperimentJournalEntry model
# ---------------------------------------------------------------------------

def test_model_stores_required_fields():
    entry = ExperimentJournalEntry(
        entry_id="abc",
        timestamp="2026-01-01 00:00:00",
        text="hello",
    )
    assert entry.entry_id == "abc"
    assert entry.timestamp == "2026-01-01 00:00:00"
    assert entry.text == "hello"


def test_model_default_entry_type_is_note():
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y"
    )
    assert entry.entry_type == "note"


def test_model_default_tags_is_empty_list():
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y"
    )
    assert entry.tags == []


def test_model_default_linked_run_id_is_none():
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y"
    )
    assert entry.linked_run_id is None


@pytest.mark.parametrize("entry_type", ["note", "hypothesis", "finding", "question"])
def test_model_accepts_all_valid_entry_types(entry_type):
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y", entry_type=entry_type
    )
    assert entry.entry_type == entry_type


def test_model_rejects_invalid_entry_type():
    with pytest.raises(ValidationError):
        ExperimentJournalEntry(
            entry_id="x", timestamp="t", text="y", entry_type="invalid"
        )


def test_model_stores_tags():
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y", tags=["a", "b"]
    )
    assert entry.tags == ["a", "b"]


def test_model_stores_linked_run_id():
    entry = ExperimentJournalEntry(
        entry_id="x", timestamp="t", text="y", linked_run_id="run-42"
    )
    assert entry.linked_run_id == "run-42"


def test_model_round_trips_via_model_dump():
    entry = ExperimentJournalEntry(
        entry_id="abc",
        timestamp="2026-01-01 00:00:00",
        text="content",
        entry_type="hypothesis",
        tags=["tag1", "tag2"],
        linked_run_id="run-1",
    )
    loaded = ExperimentJournalEntry(**entry.model_dump())
    assert loaded == entry


# ---------------------------------------------------------------------------
# load_journal
# ---------------------------------------------------------------------------

def test_load_journal_returns_empty_list_when_file_absent(tmp_path):
    assert load_journal(str(tmp_path)) == []


def test_load_journal_returns_empty_list_when_dir_absent(tmp_path):
    missing = tmp_path / "no_such_dir"
    assert load_journal(str(missing)) == []


def test_load_journal_returns_entries_from_file(tmp_path):
    entries = [
        ExperimentJournalEntry(entry_id="1", timestamp="2026-01-01 00:00:00", text="a"),
        ExperimentJournalEntry(entry_id="2", timestamp="2026-01-02 00:00:00", text="b"),
    ]
    save_journal(entries, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert len(loaded) == 2
    assert loaded[0].entry_id == "1"
    assert loaded[1].entry_id == "2"


def test_load_journal_returns_entry_instances(tmp_path):
    entries = [
        ExperimentJournalEntry(entry_id="x", timestamp="t", text="y")
    ]
    save_journal(entries, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert all(isinstance(e, ExperimentJournalEntry) for e in loaded)


def test_load_journal_returns_empty_list_on_corrupt_json(tmp_path):
    _write_raw(tmp_path, "{{not valid json{{")
    assert load_journal(str(tmp_path)) == []


def test_load_journal_returns_empty_list_on_empty_array(tmp_path):
    _write_raw(tmp_path, "[]")
    assert load_journal(str(tmp_path)) == []


def test_load_journal_preserves_text_with_newlines(tmp_path):
    entries = [
        ExperimentJournalEntry(entry_id="1", timestamp="t", text="line1\nline2")
    ]
    save_journal(entries, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert loaded[0].text == "line1\nline2"


def test_load_journal_preserves_all_optional_fields(tmp_path):
    entries = [
        ExperimentJournalEntry(
            entry_id="1",
            timestamp="t",
            text="y",
            entry_type="finding",
            tags=["x", "y"],
            linked_run_id="run-99",
        )
    ]
    save_journal(entries, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    e = loaded[0]
    assert e.entry_type == "finding"
    assert e.tags == ["x", "y"]
    assert e.linked_run_id == "run-99"


# ---------------------------------------------------------------------------
# save_journal
# ---------------------------------------------------------------------------

def test_save_journal_creates_file(tmp_path):
    save_journal([], str(tmp_path))
    assert (tmp_path / JOURNAL_FILE).exists()


def test_save_journal_creates_directory_if_absent(tmp_path):
    nested = tmp_path / "a" / "b" / "common"
    save_journal([], str(nested))
    assert (nested / JOURNAL_FILE).exists()


def test_save_journal_writes_valid_json(tmp_path):
    entries = [
        ExperimentJournalEntry(entry_id="z", timestamp="t", text="x")
    ]
    save_journal(entries, str(tmp_path))
    data = _read_raw(tmp_path)
    assert isinstance(data, list)
    assert data[0]["entry_id"] == "z"


def test_save_journal_empty_list_writes_empty_array(tmp_path):
    save_journal([], str(tmp_path))
    data = _read_raw(tmp_path)
    assert data == []


def test_save_journal_overwrites_existing_file(tmp_path):
    first = [
        ExperimentJournalEntry(entry_id="1", timestamp="t", text="first")
    ]
    second = [
        ExperimentJournalEntry(entry_id="2", timestamp="t", text="second")
    ]
    save_journal(first, str(tmp_path))
    save_journal(second, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].entry_id == "2"


def test_save_journal_round_trips_multiple_entries(tmp_path):
    entries = [
        ExperimentJournalEntry(entry_id=str(i), timestamp="t", text=f"entry {i}")
        for i in range(5)
    ]
    save_journal(entries, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert [e.text for e in loaded] == [f"entry {i}" for i in range(5)]


# ---------------------------------------------------------------------------
# add_entry
# ---------------------------------------------------------------------------

def test_add_entry_returns_entry_instance(tmp_path):
    entry = add_entry("hello", str(tmp_path))
    assert isinstance(entry, ExperimentJournalEntry)


def test_add_entry_text_is_stripped(tmp_path):
    entry = add_entry("  trimmed  ", str(tmp_path))
    assert entry.text == "trimmed"


def test_add_entry_assigns_non_empty_entry_id(tmp_path):
    entry = add_entry("x", str(tmp_path))
    assert entry.entry_id


def test_add_entry_assigns_timestamp(tmp_path):
    entry = add_entry("x", str(tmp_path))
    assert entry.timestamp


def test_add_entry_persists_to_disk(tmp_path):
    entry = add_entry("persisted", str(tmp_path))
    loaded = load_journal(str(tmp_path))
    ids = [e.entry_id for e in loaded]
    assert entry.entry_id in ids


def test_add_entry_appends_to_existing(tmp_path):
    add_entry("first", str(tmp_path))
    add_entry("second", str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert len(loaded) == 2


def test_add_entry_preserves_order(tmp_path):
    add_entry("alpha", str(tmp_path))
    add_entry("beta", str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert loaded[0].text == "alpha"
    assert loaded[1].text == "beta"


def test_add_entry_ids_are_unique(tmp_path):
    entries = [add_entry(f"entry {i}", str(tmp_path)) for i in range(10)]
    ids = [e.entry_id for e in entries]
    assert len(set(ids)) == 10


def test_add_entry_creates_directory_if_absent(tmp_path):
    nested = tmp_path / "common"
    add_entry("x", str(nested))
    assert (nested / JOURNAL_FILE).exists()


def test_add_entry_default_type_is_note(tmp_path):
    entry = add_entry("x", str(tmp_path))
    assert entry.entry_type == "note"


@pytest.mark.parametrize("entry_type", ["note", "hypothesis", "finding", "question"])
def test_add_entry_stores_entry_type(entry_type, tmp_path):
    entry = add_entry("x", str(tmp_path), entry_type=entry_type)
    assert entry.entry_type == entry_type
    loaded = load_journal(str(tmp_path))
    assert loaded[-1].entry_type == entry_type


def test_add_entry_default_tags_is_empty(tmp_path):
    entry = add_entry("x", str(tmp_path))
    assert entry.tags == []


def test_add_entry_stores_tags(tmp_path):
    entry = add_entry("x", str(tmp_path), tags=["foo", "bar"])
    assert entry.tags == ["foo", "bar"]
    loaded = load_journal(str(tmp_path))
    assert loaded[0].tags == ["foo", "bar"]


def test_add_entry_default_linked_run_id_is_none(tmp_path):
    entry = add_entry("x", str(tmp_path))
    assert entry.linked_run_id is None


def test_add_entry_stores_linked_run_id(tmp_path):
    entry = add_entry("x", str(tmp_path), linked_run_id="run-123")
    assert entry.linked_run_id == "run-123"
    loaded = load_journal(str(tmp_path))
    assert loaded[0].linked_run_id == "run-123"


# ---------------------------------------------------------------------------
# delete_entry
# ---------------------------------------------------------------------------

def test_delete_entry_returns_true_on_success(tmp_path):
    entry = add_entry("to delete", str(tmp_path))
    assert delete_entry(entry.entry_id, str(tmp_path)) is True


def test_delete_entry_returns_false_when_id_not_found(tmp_path):
    assert delete_entry("nonexistent-id", str(tmp_path)) is False


def test_delete_entry_returns_false_when_file_absent(tmp_path):
    assert delete_entry("any-id", str(tmp_path)) is False


def test_delete_entry_removes_entry_from_store(tmp_path):
    entry = add_entry("to delete", str(tmp_path))
    delete_entry(entry.entry_id, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    ids = [e.entry_id for e in loaded]
    assert entry.entry_id not in ids


def test_delete_entry_preserves_remaining_entries(tmp_path):
    e1 = add_entry("keep", str(tmp_path))
    e2 = add_entry("delete me", str(tmp_path))
    delete_entry(e2.entry_id, str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].entry_id == e1.entry_id


def test_delete_entry_persists_change_to_disk(tmp_path):
    entry = add_entry("x", str(tmp_path))
    delete_entry(entry.entry_id, str(tmp_path))
    reloaded = load_journal(str(tmp_path))
    assert all(e.entry_id != entry.entry_id for e in reloaded)


def test_delete_entry_unknown_id_does_not_modify_store(tmp_path):
    add_entry("safe", str(tmp_path))
    delete_entry("does-not-exist", str(tmp_path))
    loaded = load_journal(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].text == "safe"


def test_delete_entry_can_delete_all_one_by_one(tmp_path):
    entries = [add_entry(f"e{i}", str(tmp_path)) for i in range(3)]
    for entry in entries:
        delete_entry(entry.entry_id, str(tmp_path))
    assert load_journal(str(tmp_path)) == []
