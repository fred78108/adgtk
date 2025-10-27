# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

"""test_project.py is focused on testing the tracking.project


Testing
=======
pytest -s test/tracking/test_project.py

note: initial test cases generated via a model. modifed code to meet
      needs and fix bugs, etc.
"""

import os
import json
import uuid
import pytest

from adgtk.tracking import project
from adgtk.tracking.structure import ExperimentEntryModel

@pytest.fixture
def empty_project_log_file(tmp_path):
    log_path = tmp_path / project.PROJECT_LOG_FILE
    log_path.write_text("[]")
    return log_path

@pytest.fixture(autouse=True)
def setup_tracking_folder(tmp_path, monkeypatch):
    # Patch TRACKING_FOLDER for each test to use a temp dir
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    # Reset internal state
    project._log.clear()
    project._log_loaded = False
    yield

def make_entry(name="TestExperiment", description="desc", journal="j", results_path="p", id=None, timestamp=None):
    return ExperimentEntryModel(
        name=name,
        description=description,
        journal=journal,
        results_path=results_path,
        id=id or str(uuid.uuid4()),
        timestamp=timestamp
    )

def test_add_and_get_entry(empty_project_log_file):
    entry = make_entry()
    project.add_entry(entry)
    found = project.get_entries_by_name(entry.name)
    assert len(found) == 1
    assert found[0].id == entry.id

def test_add_duplicate_id_raises(empty_project_log_file):
    entry = make_entry()
    project.add_entry(entry)
    with pytest.raises(KeyError):
        project.add_entry(entry)  # same id

def test_get_entry_by_id(empty_project_log_file):
    entry = make_entry()
    project.add_entry(entry)
    result = project.get_entry_by_id(entry.id)
    assert result.name == entry.name

def test_get_entry_by_id_not_found():
    with pytest.raises(KeyError):
        project.get_entry_by_id("does-not-exist")

def test_get_entries_by_name_multiple(empty_project_log_file):
    entry1 = make_entry(name="SameName")
    entry2 = make_entry(name="SameName")
    project.add_entry(entry1)
    project.add_entry(entry2)
    found = project.get_entries_by_name("SameName")
    assert len(found) == 2

def test_id_exists(empty_project_log_file):
    entry = make_entry()
    project.add_entry(entry)
    assert project.id_exists(entry.id)
    assert not project.id_exists("random-id")

def test_remove_entry_success(empty_project_log_file):
    entry = make_entry()
    project.add_entry(entry)
    result = project.remove_entry(entry.id)
    assert result
    assert not project.id_exists(entry.id)

def test_remove_entry_not_found(empty_project_log_file):
    result = project.remove_entry("nonexistent-id")
    assert result is False

def test_persistence_between_calls(
        tmp_path, monkeypatch, empty_project_log_file):
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._log.clear()
    project._log_loaded = False
    entry = make_entry()
    project.add_entry(entry)
    # Simulate reload
    project._log.clear()
    project._log_loaded = False
    # Any function that triggers reload
    project.get_entries_by_name(entry.name)
    found = project.get_entry_by_id(entry.id)
    assert found.id == entry.id

def test_handles_missing_optional_fields(empty_project_log_file):
    entry = ExperimentEntryModel(
        name="NoTimestamp",
        description="desc",
        journal="j",
        results_path="p"
        # no id, no timestamp
    )
    project.add_entry(entry)
    found = project.get_entries_by_name("NoTimestamp")
    assert len(found) == 1
    assert found[0].timestamp is not None  # should be auto-set

# Optionally, test log file corrupt or missing (advanced/robustness)

def test_load_log_with_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    file_w_path = os.path.join(tmp_path, project.PROJECT_LOG_FILE)
    with open(file_w_path, "w") as f:
        f.write("{invalid json")
    project._log.clear()
    project._log_loaded = False
    with pytest.raises(json.JSONDecodeError):
        # Will attempt to load corrupt file via any public method
        project.get_entries_by_name("any")


# --------------------- Additional prefix/experiment name tests ---------------------
def test_register_prefix_and_retire(monkeypatch, tmp_path):
    # Isolate prefix file to temp dir
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._prefix_entries.clear()
    project._prefix_loaded = False
    prefix = "testprefix"
    # Register new prefix
    project.register_prefix(prefix)
    assert prefix in project.get_prefix_list()
    # Retire prefix
    project.retire_prefix(prefix)
    assert prefix not in project.get_prefix_list()

# Note : Moved away from that design.
# def test_register_duplicate_prefix_raises(monkeypatch, tmp_path):
#     monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
#     project._prefix_entries.clear()
#     project._prefix_loaded = False
#     prefix = "duptest"
#     project.register_prefix(prefix)
#     with pytest.raises(KeyError):
#         project.register_prefix(prefix)

def test_generate_experiment_name_increments(monkeypatch, tmp_path):
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._prefix_entries.clear()
    project._prefix_loaded = False
    prefix = "gexp"
    name1 = project.generate_experiment_name(prefix=prefix)
    name2 = project.generate_experiment_name(prefix=prefix)
    assert name1.endswith(".0.1")
    assert name2.endswith(".0.2")
    name3 = project.generate_experiment_name(prefix=prefix, update_next="major")
    assert name3.endswith(".1.0")

def test_generate_experiment_name_auto_registers(monkeypatch, tmp_path):
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._prefix_entries.clear()
    project._prefix_loaded = False
    prefix = "autoreg"
    # No need to register manually; should auto-register
    name = project.generate_experiment_name(prefix=prefix)
    assert prefix in project.get_prefix_list()
    assert name.startswith(f"{prefix}.")

def test_generate_experiment_name_corrupt_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    prefix_file = tmp_path / project.PROJECT_PREFIX_FILE
    # Write a corrupt prefix file (missing required fields)
    prefix_file.write_text('{"bad": {"wer": "bad"}}')
    project._prefix_entries.clear()
    project._prefix_loaded = False
    with pytest.raises(ValueError):
        project._load_prefix_file()


def test_add_entry_triggers_prefix_registration(monkeypatch, tmp_path):
    # Setup: Isolate prefix file and tracking folder to temp dir
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._prefix_entries.clear()
    project._prefix_loaded = False
    project._log.clear()
    project._log_loaded = False

    # Proper format: prefix.major.minor
    entry = ExperimentEntryModel(
        name="myprefix.3.7",
        description="desc",
        journal="j",
        results_path="p"
    )
    project.add_entry(entry, request_prefix_registration=True)
    # Should register the prefix 'myprefix' with major=3, minor=7
    assert "myprefix" in project.get_prefix_list()
    prefix_entry = project._prefix_entries["myprefix"]
    assert prefix_entry.major_counter == 3
    assert prefix_entry.minor_counter == 7

def test_add_entry_registration_with_custom_delimiter(monkeypatch, tmp_path):
    # Setup: Isolate prefix file and tracking folder to temp dir
    monkeypatch.setattr(project, "TRACKING_FOLDER", str(tmp_path))
    project._prefix_entries.clear()
    project._prefix_loaded = False
    project._log.clear()
    project._log_loaded = False

    # Use custom delimiter
    entry = ExperimentEntryModel(
        name="aprefix-5-4",
        description="desc",
        journal="j",
        results_path="p"
    )
    project.add_entry(entry, request_prefix_registration=True, register_prefix_delimiter="-")
    assert "aprefix" in project.get_prefix_list()
    prefix_entry = project._prefix_entries["aprefix"]
    assert prefix_entry.major_counter == 5
    assert prefix_entry.minor_counter == 4