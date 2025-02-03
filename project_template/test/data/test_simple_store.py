"""test_simple_store
"""

import logging
import os
import shutil
import test.mockdata.mock as mockdata
import pytest
import toml
from adgtk.common import DEFAULT_SETTINGS
from adgtk.components.data.store import RecordStore
from adgtk.factory.component import ObjectFactory
from structure.presentation import YamlPresentation
from structure.records import DataRecord
from structure.store import SimpleRecordStore


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_simple_store.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True
TMP_DATA_DIR = "tmp-data-dir"
DB_FILEMAME = "test-db.pkl"

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Data / custom code unique to this class
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture(name="settings_file")
def temp_settings_file(request):
    with open(file="settings.toml", encoding="utf-8", mode="w") as outfile:
        output = toml.dumps(DEFAULT_SETTINGS)
        outfile.write(output)

    def teardown():
        if os.path.exists("settings.toml") and DO_CLEANUP:
            os.remove("settings.toml")

    request.addfinalizer(teardown)


@pytest.fixture(name="record_list")
def record_list_fixture(request, settings_file):
    """A list of created records"""
    factory = ObjectFactory(journal=None)
    factory.register(creator=YamlPresentation)
    factory.register(creator=DataRecord)
    records = []
    for data in mockdata.student_list:
        record: DataRecord = factory.create(
            {
                "group_label": "record",
                "type_label": "data",
                "arguments": {
                    "presentation_def": {
                        "group_label": "presentation",
                        "type_label": "yaml",
                        "arguments": {}  # take defaults
                    },
                    "data": data,
                    "use_cached_str": True,
                    "metadata": {}
                }
            }
        )
        records.append(record)

    return records


@pytest.fixture(name="temp_dir")
def temp_dir_fixture(request):
    """directory management"""
    if os.path.exists(TMP_DATA_DIR) and CLEAN_BEFORE_RUN:
        shutil.rmtree(TMP_DATA_DIR)

    # now create, if exists then problem above.
    os.makedirs(TMP_DATA_DIR, exist_ok=False)

    # and stage teardown

    def teardown():
        if os.path.exists(TMP_DATA_DIR) and DO_CLEANUP:
            shutil.rmtree(TMP_DATA_DIR)

    request.addfinalizer(teardown)

    return TMP_DATA_DIR


@pytest.fixture(name="loaded_db")
def loaded_db_fixture(request, record_list, settings_file) -> SimpleRecordStore:
    """A fully loaded db with student records"""
    db = SimpleRecordStore()
    db.bulk_insert(record_list)
    return db

# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_insert_and_length(record_list):
    """Verifies inserting and length in a single test"""
    db = SimpleRecordStore()
    assert len(db) == 0
    db.insert(record_list[0])
    assert len(db) == 1


def test_iterate(loaded_db):
    """Verifies the store can iterate"""
    saw_alice = False
    saw_bob = False
    saw_charlie = False
    count = 0

    for record in loaded_db:
        if record.data["name"] == "alice":
            saw_alice = True
        elif record.data["name"] == "bob":
            saw_bob = True
        elif record.data["name"] == "charlie":
            saw_charlie = True

        count += 1

    assert saw_alice
    assert saw_bob
    assert saw_charlie
    assert count == 3


def test_clear_all_records(record_list):
    """Verifies the store can clear records"""
    db = SimpleRecordStore()
    db.insert(record_list[0])
    db.insert(record_list[1])
    assert len(db) == 2
    db.clear_all_records()
    assert len(db) == 0


def test_bulk_insert(record_list):
    """Verifies the db can insert in bulk"""
    db = SimpleRecordStore()
    db.bulk_insert(record_list)
    assert len(db) == len(record_list)
    assert len(db) > 0


def test_get_all_records_copy(loaded_db):
    """Verifies it can get all records as a copy"""
    records = loaded_db.get_all_records(as_copy=True)
    assert len(records) == 3
    # verify no change in source data
    record = records[0]
    record.data["name"] = "bert"
    assert loaded_db._records[0].data["name"] == "alice"


def test_get_all_records_memory(loaded_db):
    """Verifies get all records as a list"""
    records = loaded_db.get_all_records(as_copy=False)
    assert loaded_db._records[0].data["name"] == "alice"
    assert len(records) == 3
    # verify no change in source data
    record = records[0]
    record.data["name"] = "bert"
    assert loaded_db._records[0].data["name"] == "bert"

    # and revert back, just in case
    record.data["name"] = "alice"
    assert loaded_db._records[0].data["name"] == "alice"


def test_shuffle(loaded_db):
    """Verifies shuffle of records"""
    flipped = False
    # give it 10 attempts
    name = loaded_db._records[0].create_copy_of_data()["name"]
    for _ in range(10):
        loaded_db.shuffle()
        if name != loaded_db._records[0].create_copy_of_data()["name"]:
            flipped = True
            break
    assert flipped


def test_save_and_load_from_disk(temp_dir, loaded_db, record_list):
    """Verify disk I/O functions"""
    expected_file = os.path.join(temp_dir, DB_FILEMAME)
    assert not os.path.exists(expected_file)
    # validate file exists after save
    loaded_db.save_to_disk(expected_file)
    assert os.path.exists(expected_file)

    # now validate load
    db = SimpleRecordStore()
    db.insert(record_list[0])
    assert len(db) == 1
    db.rebuild_from_disk(expected_file)
    assert len(db) == len(loaded_db)


def test_check_protocol_alignment_simple_record_store():
    """Validates protocol adherence"""
    db = SimpleRecordStore()
    assert isinstance(db, RecordStore)
