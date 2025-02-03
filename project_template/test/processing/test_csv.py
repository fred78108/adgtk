"""Testing of the scenario loader
"""


import os
import logging
import pytest
import toml
from adgtk.common import DEFAULT_SETTINGS
from adgtk.factory import ObjectFactory
from adgtk.common import ComponentDef
from structure.presentation import YamlPresentation
from structure.store import SimpleRecordStore
from structure.records import DataRecord
from processing.csv import CsvToDataStoreProcessor

# py -m pytest test/processing/test_csv.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

# py -m pytest -s test/processing/test_csv.py

# ----------------------------------------------------------------------
# Common
# ----------------------------------------------------------------------

CSV_BLUEPRINT: ComponentDef = {
    "group_label": "processing",
    "type_label": "csv-to-datastore",
    "arguments": {
        "source_file": "your file with path goes here",
        "clean_whitespace": True
    }
}

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


@pytest.fixture(name="object_factory")
def object_factory_fixture(settings_file):
    """Creates a factory for testing"""
    factory = ObjectFactory(journal=None)
    factory.register(creator=DataRecord)
    factory.register(creator=YamlPresentation)
    factory.register(creator=CsvToDataStoreProcessor)
    return factory


def test_factory_creation(object_factory):
    """Validates the typical end-to-end pattern"""
    file_w_path = os.path.join("test", "mockdata", "ds1.csv")
    blueprint = CSV_BLUEPRINT.copy()
    blueprint["arguments"]["source_file"] = file_w_path
    # print(f"Testing with blueprint: {blueprint}")
    processor: CsvToDataStoreProcessor = object_factory.create(blueprint)
    assert isinstance(processor, CsvToDataStoreProcessor)

    # No Datastore is set on load. it needs to be set either as part
    data_store = SimpleRecordStore()
    processor.datastore = data_store

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0


def test_process_with_filter_include(object_factory):
    """Validates filtering with include"""
    data_store = SimpleRecordStore()
    processor = CsvToDataStoreProcessor(
        source_file=os.path.join("test", "mockdata", "ds1.csv"),
        datastore=data_store,
        factory=object_factory,
        journal=None,
        include_columns=["name", "age"])

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0
    inspect_data = data_store._records[0].create_copy_of_data()
    data_keys = list(inspect_data.keys())
    assert "name" in data_keys
    assert "age" in data_keys
    assert "student" not in data_keys


def test_process_with_filter_include_no_clean(object_factory):
    """Validates filtering with include and not cleaning cols"""
    data_store = SimpleRecordStore()
    processor = CsvToDataStoreProcessor(
        source_file=os.path.join("test", "mockdata", "ds1.csv"),
        datastore=data_store,
        factory=object_factory,
        journal=None,
        include_columns=["name", "age"],
        clean_whitespace=False)

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0
    inspect_data = data_store._records[0].create_copy_of_data()
    data_keys = list(inspect_data.keys())
    assert "name" in data_keys
    assert "age" not in data_keys       # it has leading whitespace
    assert "student" not in data_keys


def test_process_with_exclude(object_factory):
    """Validates filtering with exclude"""
    data_store = SimpleRecordStore()
    processor = CsvToDataStoreProcessor(
        source_file=os.path.join("test", "mockdata", "ds1.csv"),
        datastore=data_store,
        factory=object_factory,
        journal=None,
        exclude_columns=["name"],
        clean_whitespace=True)

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0
    inspect_data = data_store._records[0].create_copy_of_data()
    data_keys = list(inspect_data.keys())
    assert "name" not in data_keys
    assert "age" in data_keys
    assert "student" in data_keys


def test_process_with_exclude_and_include_no_collision(object_factory):
    """Validates filtering with both include and exclude"""
    data_store = SimpleRecordStore()
    processor = CsvToDataStoreProcessor(
        source_file=os.path.join("test", "mockdata", "ds1.csv"),
        datastore=data_store,
        factory=object_factory,
        journal=None,
        exclude_columns=["name"],
        include_columns=["age"],
        clean_whitespace=True)

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0
    inspect_data = data_store._records[0].create_copy_of_data()
    data_keys = list(inspect_data.keys())
    assert "name" not in data_keys
    assert "age" in data_keys
    assert "student" not in data_keys


def test_process_with_exclude_and_include_collision(object_factory):
    """Validates priority of filter when both include/exclude are set"""
    data_store = SimpleRecordStore()
    processor = CsvToDataStoreProcessor(
        source_file=os.path.join("test", "mockdata", "ds1.csv"),
        datastore=data_store,
        factory=object_factory,
        journal=None,
        exclude_columns=["name"],
        include_columns=["name"],
        clean_whitespace=True)

    assert len(data_store) == 0
    processor.process()
    assert len(data_store) > 0
    inspect_data = data_store._records[0].create_copy_of_data()
    data_keys = list(inspect_data.keys())
    assert "name" in data_keys
    assert "age" not in data_keys
    assert "student" not in data_keys
