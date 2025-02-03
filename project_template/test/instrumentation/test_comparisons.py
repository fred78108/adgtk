"""_summary_
"""


import os
import shutil
import logging
import pytest

from adgtk.instrumentation import (
    Comparison,
    Measurement,
    SupportsMeasDef)
from structure import DataRecordGroup, DataRecord
from instrumentation.comparisons import (
    GroupDataKeyOverlap,
    GroupDataValueOverlap,
    GroupWordOverlap,
    calc_overlap,
    WordOverlap,
    DataKeyOverlap,
    DataValueOverlap)

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_comparisons.py


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
# Data
# ----------------------------------------------------------------------
# root record
record_one = DataRecord(
    data={"a": "This is a test", "b": "all the cats are outside"})
# for comparing against the root record
record_two = DataRecord(
    data={"a": "This is a test", "c": "dog was here"})

# and the groups
record_group_match = DataRecordGroup(records=[record_one, record_one])
record_group_partial = DataRecordGroup(records=[record_one, record_two])
# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


# --------------------------- direct -----------------------------------
def test_calc_overlap_full_match():
    """Verifies calc_overlap works as expected with all matching"""
    result = calc_overlap(
        a=["a", "b", "c", "d"],
        b=["a", "b", "c", "d"])
    assert result == 1


def test_calc_overlap_half_match():
    """Verifies calc_overlap works as expected with all matching"""
    result = calc_overlap(
        a=["a", "b", "c", "d"],
        b=["a", "b", "e", "f"])
    assert result == .5


def test_calc_overlap_no_match():
    """Verifies calc_overlap works as expected with all matching"""
    result = calc_overlap(
        a=["a", "b", "c", "d"],
        b=["r", "g", "e", "f"])
    assert result == 0


def test_calc_overlap_dup_diff_length():
    """Verifies calc_overlap works as expected with all matching"""
    result = calc_overlap(
        a=["a", "b", "c", "d", "e"],
        b=["a", "b", "a", "f", "g", "h"])
    assert result == 0.4


def test_word_overlap_no_stopwords():
    """Validates the class (which invokes calc_overlap tested above) is
    processing text with no stop words set"""
    meas = WordOverlap()
    result = meas.compare(
        a="This is a test of the word overlap measure in the comparison module",
        b="This is an exercise of the word overlap class")
    assert result == .5


def test_word_overlap_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = WordOverlap()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Comparison)


def test_word_overlap_with_stopwords():
    """Validates the class (which invokes calc_overlap tested above) is
    processing text with stop words set"""
    meas = WordOverlap()
    # simulate engine loading stopwords
    meas.use_stopwords = True
    meas.stopwords = ["this", "an", "word"]

    result = meas.compare(
        a="This is a test of the word overlap measure in the comparison module",
        b="This is an exercise of the word overlap class")
    assert result == .4


def test_data_key_overlap():
    """Validates the DataKeyOverlap meaurement."""
    meas = DataKeyOverlap()
    result = meas.compare(
        a={"a": 1, "b": 2, "c": 3, "d": 4},
        b={"a": 1, "b": 2, "e": 3, "f": 4})
    # we have a .5 match on keys and 1 on values. confirming keys with:
    assert result == .5


def test_data_key_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = DataKeyOverlap()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Comparison)


def test_data_value_overlap_no_stopwords():
    meas = DataValueOverlap()
    result = meas.compare(
        a={
            "a": "This is a test of the word",
            "b": "overlap measure in the",
            "c": "comparison module"
        },
        b={
            "a": "This is an exercise",
            "b": "of the word overlap class"
        })
    assert result == .5


def test_data_value_use_stopwords():
    """Validates the DataKeyOverlap meaurement using stopwords."""
    meas = DataValueOverlap()
    # simulate engine loading stopwords
    meas.use_stopwords = True
    meas.stopwords = ["this", "an", "word"]

    result = meas.compare(
        a={
            "a": "This is a test of the word",
            "b": "overlap measure in the",
            "c": "comparison module"
        },
        b={
            "a": "This is an exercise",
            "b": "of the word overlap class"
        })
    assert result == .4


def test_data_value_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = DataValueOverlap()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Comparison)


# --------------------------- wrappers ---------------------------------
# these tests validate the wrapper classes are working as expected


def test_group_word_overlap():
    """Validates the wrapper for word overlap"""
    meas = GroupWordOverlap()
    m_result = meas.measure(record_group_match)
    assert m_result == 1
    p_result = meas.measure(record_group_partial)
    assert 0 < p_result < 1


def test_group_data_key_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = GroupDataKeyOverlap()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Measurement)


def test_group_data_key_overlap():
    """Validates the wrapper for data key overlap"""
    meas = GroupDataKeyOverlap()
    m_result = meas.measure(record_group_match)
    assert m_result == 1
    p_result = meas.measure(record_group_partial)
    assert p_result == .5


def test_group_data_value_overlap():
    """Validates the wrapper for data value overlap"""
    meas = GroupDataValueOverlap()
    m_result = meas.measure(record_group_match)
    assert m_result == 1
    p_result = meas.measure(record_group_partial)
    assert 0 < p_result < .5


def test_group_data_value_protcol_adherence():
    """Verifies adherence to the protocol"""
    measurement = GroupDataValueOverlap()
    assert isinstance(measurement, SupportsMeasDef)
    assert isinstance(measurement, Measurement)
