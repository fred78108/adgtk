"""Tests the loader functions
"""

# pylint: disable=protected-access

import logging
import os
import pytest
import toml
import test.mockdata.mock as mockdata
from adgtk.factory import ObjectFactory
from structure.store import SimpleRecordStore
from structure.records import DataRecord
from structure.presentation import YamlPresentation
import data.records.loader as loader
from adgtk.common import DEFAULT_SETTINGS

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_record_loader.py


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


# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_create_record(settings_file):
    """Validates creation of a record when passing in a blueprint"""
    record: DataRecord = loader.create_record(data=mockdata.sample_data_one)
    assert record.data["age"] == "24"


def test_create_records_no_store(settings_file):
    """Validates creation of multiple records but not saving to store"""
    results = loader.create_records(data=mockdata.student_list)
    assert isinstance(results, list)
    assert len(results) == len(mockdata.student_list)
    assert isinstance(results[0], DataRecord)


def test_create_records_with_store(settings_file):
    """Validates creation of multiple records and saving to store"""
    factory = ObjectFactory(journal=None)
    factory.register(YamlPresentation)
    factory.register(DataRecord)

    store = SimpleRecordStore()
    results = loader.create_records(
        factory=factory, data=mockdata.student_list, datastore=store)
    # confirm still returns
    assert isinstance(results, list)
    assert len(results) == len(mockdata.student_list)
    assert isinstance(results[0], DataRecord)

    # and also loads the datastore
    assert len(store) == len(mockdata.student_list)
