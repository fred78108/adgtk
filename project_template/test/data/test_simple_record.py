"""Testing of simple records
"""


import os
import logging
import pytest
import toml
from adgtk.common import DEFAULT_SETTINGS
from adgtk.components.data.records import PresentableGroup, PresentableRecord
from adgtk.factory.component import ObjectFactory
from structure.presentation.simple import YamlPresentation
from structure.records import DataRecord, DataRecordGroup
from structure.store import SimpleRecordStore


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_simple_record.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

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


@pytest.fixture(name="loaded_factory")
def loaded_factory_fixture(request, settings_file):
    """A loaded factory"""
    factory = ObjectFactory(journal=None)
    factory.register(creator=YamlPresentation)
    factory.register(creator=DataRecord)

    return factory

# ----------------------------------------------------------------------
# Testing Data Record
# ----------------------------------------------------------------------


def test_factory_create(loaded_factory):
    """Validate the factory and init method are working"""
    record: DataRecord = loaded_factory.create(
        {
            "group_label": "record",
            "type_label": "data",
            "arguments": {
                "presentation_def": {
                    "group_label": "presentation",
                    "type_label": "yaml",
                    "arguments": {}  # take defaults
                },
                "data": {},
                "use_cached_str": True,
                "metadata": {}
            }
        }
    )
    # perform basic validation
    assert isinstance(record, DataRecord)
    str_rep = record.__str__()
    assert str_rep == record._string_rep_cached


def test_record_protocol_adherence(loaded_factory):
    """Validate the factory and init method are working"""
    record: DataRecord = loaded_factory.create(
        {
            "group_label": "record",
            "type_label": "data",
            "arguments": {
                "presentation_def": {
                    "group_label": "presentation",
                    "type_label": "yaml",
                    "arguments": {}  # take defaults
                },
                "data": {},
                "use_cached_str": True,
                "metadata": {}
            }
        }
    )
    # perform basic validation
    assert isinstance(record, PresentableRecord)


def test_get_copy_of_data(loaded_factory):
    """Validate that the copy is working as expected"""
    record: DataRecord = loaded_factory.create(
        {
            "group_label": "record",
            "type_label": "data",
            "arguments": {
                "presentation_def": {
                    "group_label": "presentation",
                    "type_label": "yaml",
                    "arguments": {}  # take defaults
                },
                "data": {
                    "name": "a",
                    "age": 1,
                    "test": True
                },
                "use_cached_str": True,
                "metadata": {}
            }
        }
    )

    just_data = record.create_copy_of_data()
    assert just_data["name"] == "a"
    just_data["name"] = "b"
    assert record.data["name"] == "a"
    assert just_data["name"] == "b"


def test_get_keys(loaded_factory):
    """Validate that the key listing works as expected"""
    record: DataRecord = loaded_factory.create(
        {
            "group_label": "record",
            "type_label": "data",
            "arguments": {
                "presentation_def": {
                    "group_label": "presentation",
                    "type_label": "yaml",
                    "arguments": {}  # take defaults
                },
                "data": {
                    "name": "a",
                    "age": 1,
                    "test": True
                },
                "use_cached_str": True,
                "metadata": {}
            }
        }
    )
    keys = record.get_data_keys()
    assert "name" in keys
    assert "age" in keys
    assert "test" in keys


# ----------------------------------------------------------------------
# Testing Data Record Group
# ----------------------------------------------------------------------

def test_data_record_group_protocol_adherence():
    r1 = DataRecord(data={"a": 1})
    r2 = DataRecord(data={"a": 2})
    record = DataRecordGroup(records=[r1, r2], metadata={})
    assert isinstance(record, PresentableGroup)
