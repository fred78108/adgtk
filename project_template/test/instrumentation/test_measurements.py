"""_summary_
"""


import os
import shutil
import logging
import pytest
import adgtk.common.css as css
from adgtk.instrumentation import (
    Comparison,
    SupportsMeasDef,
    Measurement)
from instrumentation import (
    MeasureTextLength,
    MeasureWordCount,
    MeasureItemCount)
from structure.store import SimpleRecordStore
from structure.records import DataRecord
import test.mockdata.mock as mockdata


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_measurements.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True
TMP_DIR = f"tmp-dir-{__name__}"

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture(name="temp_dir")
def temp_dir_fixture(request):
    """a temporary directory"""
    if os.path.exists(TMP_DIR) and CLEAN_BEFORE_RUN:
        shutil.rmtree(TMP_DIR)

    def teardown():
        if os.path.exists(TMP_DIR) and DO_CLEANUP:
            shutil.rmtree(TMP_DIR)

    request.addfinalizer(teardown)

    return TMP_DIR


@pytest.fixture(name="loaded_dataset")
def loaded_dataset_fixture():
    """A loaded dataset"""
    ds = SimpleRecordStore()
    ds.insert(DataRecord(data=mockdata.sample_data_one))
    ds.insert(DataRecord(data=mockdata.sample_data_two))
    return ds


# ----------------------------------------------------------------------
# Data - may move to Mockdata. for now doing in-line
# ----------------------------------------------------------------------
STRING_ONE = "This is a test of the unit test broadcast network."
STOP_WORDS = ["this", "is", "a", "of", "the"]
# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_text_length_intro():
    """Verifies that the intro generates html."""
    measurement = MeasureTextLength()
    result = measurement.report(header=2)

    assert f"<h2 class=\"{css.MEAS_HEADER_CSS_TAG}\">" in result
    assert "</h2>" in result


def test_text_length():
    """Verifies string length works as expected """
    measurement = MeasureTextLength()
    result = measurement.measure(STRING_ONE)
    assert result == len(STRING_ONE)


def test_text_length_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = MeasureTextLength()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Measurement)


def test_word_count_default():
    """Verfies word count works as expected."""
    measurement = MeasureWordCount()
    result = measurement.measure(STRING_ONE)
    assert result == len(STRING_ONE.split())


def test_word_length_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = MeasureWordCount()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Measurement)


def test_word_count_alt_seperator():
    """verifies word split measure works with alt seperator."""
    measurement = MeasureWordCount(seperator="e")
    result = measurement.measure(STRING_ONE)
    assert result == len(STRING_ONE.split(sep="e"))


def test_word_count_stopwords_ignore_case():
    """Verifies stop_words works regardless of case"""
    measurement = MeasureWordCount(
        use_stopwords=True, ignore_case=True)
    # simulate post init setting of stopwords
    measurement.stopwords = STOP_WORDS
    result = measurement.measure(STRING_ONE)
    assert result == 5


def test_word_count_stopwords_use_case():
    """Verifies case matter when flag is not set"""
    measurement = MeasureWordCount(
        use_stopwords=True, ignore_case=False)
    # simulate post init setting of stopwords
    measurement.stopwords = STOP_WORDS
    result = measurement.measure(STRING_ONE)
    # unable to remove "This" due to case so +1
    assert result == 6


def test_word_count_stopwords_alt_sep():
    """Verifies case matter when flag is not set and alt sep."""
    measurement = MeasureWordCount(
        seperator="e",
        use_stopwords=True, ignore_case=False)
    # simulate post init setting of stopwords
    measurement.stopwords = STOP_WORDS
    measurement.use_stopwords = True

    result = measurement.measure(STRING_ONE)
    assert result == 5


def test_item_count_with_data_store(loaded_dataset):
    """Verifies the item count works with a loaded datastore"""
    # setup measurement
    measurement = MeasureItemCount()

    result = measurement.measure(loaded_dataset)
    assert result == 2


def test_item_count_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = MeasureItemCount()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Measurement)
