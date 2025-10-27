# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

"""test_tracking.py is focused on testing the tracking.FileTracker

Testing
=======
pytest -s test/data/test_tracking.py

note: initial test cases generated via a model. modified code to meet
      needs and fix bugs, etc.
"""


import os
import pytest   # type: ignore
from adgtk.data.tracking import JsonFileTracker

@pytest.fixture
def tmp_inventory(tmp_path):
    return tmp_path / "inventory.json"

@pytest.fixture
def fake_file(tmp_path):
    file = tmp_path / "example.csv"
    file.write_text("col1,col2\nval1,val2\n")
    return file

def make_tracker(tmp_inventory):
    return JsonFileTracker(label="test", inventory_file=str(tmp_inventory))


# --- New tests for JsonFileTracker ---

def test_register_file_adds_to_inventory(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    file_id = tracker.register_file(str(fake_file), encoding="csv")
    loaded = make_tracker(tmp_inventory)
    assert file_id in loaded._inventory


def test_register_file_raises_on_duplicate_id(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    file_id = "test-id"
    tracker.register_file(str(fake_file), encoding="csv", id=file_id)
    with pytest.raises(IndexError):
        tracker.register_file(str(fake_file), encoding="csv", id=file_id)


def test_get_file_id_returns_correct_id(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    file_id = tracker.register_file(str(fake_file), encoding="csv")
    dir, name = os.path.split(fake_file)
    result = tracker.get_file_id(name, path=dir)
    assert result == file_id


def test_list_files_filters_by_tag(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    tracker.register_file(str(fake_file), encoding="csv", tags=["alpha", "beta"])
    tracker.register_file(str(fake_file), encoding="csv", tags=["beta"])
    result = tracker.list_files(tag="alpha")
    assert len(result) == 1


def test_retire_file_removes_entry(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    file_id = tracker.register_file(str(fake_file), encoding="csv")
    tracker.retire_file(file_id)
    assert file_id not in tracker._inventory


def test_get_file_definition_returns_expected(tmp_inventory, fake_file):
    tracker = make_tracker(tmp_inventory)
    file_id = tracker.register_file(str(fake_file), encoding="csv")
    fd = tracker.get_file_definition(file_id)
    assert fd.filename == fake_file.name
    assert fd.file_id == file_id


def test_get_file_id_raises_if_not_found(tmp_inventory):
    tracker = make_tracker(tmp_inventory)
    with pytest.raises(FileNotFoundError):
        tracker.get_file_id("not_there.csv", path="/fake/path")


def test_load_from_disk_populates_inventory(tmp_inventory, fake_file):
    # Step 1: Create a tracker and register a file to write to disk
    tracker = make_tracker(tmp_inventory)
    file_id = tracker.register_file(str(fake_file), encoding="csv")

    # Step 2: Create a new tracker instance, which will trigger _load_from_disk
    new_tracker = make_tracker(tmp_inventory)

    # Step 3: Assert that the loaded inventory contains the expected file_id
    assert file_id in new_tracker._inventory
    fd = new_tracker._inventory[file_id]
    assert fd.filename == fake_file.name