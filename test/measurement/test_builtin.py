"""
Unit tests for the built-in measurement functions in the adgtk.measurements.builtin module.

This script contains test cases for the following functions:
- string_length: Verifies the length of strings, including edge cases like empty strings and strings with spaces or numbers.
- dict_total_str_length: Verifies the total length of all string representations of values in a dictionary, including handling of non-string values, empty dictionaries, and nested structures.
- key_overlap: Verifies the ratio of overlapping keys between two dictionaries, including edge cases like empty dictionaries and invalid inputs.

These tests ensure the correctness and robustness of the measurement functions.

Test
====
python -m pytest -s test/measurement/test_builtin.py


Note: Initial test script written by AI, updated manually to meet needs.
"""

import pytest
from adgtk.measurements.builtin import string_length, dict_total_str_length, key_overlap

def test_string_length():
    """Test the string_length function.

    Verifies that the function correctly calculates the length of strings,
    including edge cases like empty strings and strings with spaces or numbers.
    """
    assert string_length("hello") == 5
    assert string_length("") == 0
    assert string_length(" ") == 1
    assert string_length("12345") == 5

def test_dict_total_str_length():
    """Test the dict_total_str_length function.

    Verifies that the function correctly calculates the total length of all
    string representations of values in a dictionary, including handling of
    non-string values, empty dictionaries, and nested structures.
    """
    assert dict_total_str_length({"a": "hello", "b": "world"}) == 10
    assert dict_total_str_length({"a": 123, "b": 456}) == 6
    assert dict_total_str_length({"a": None, "b": "test"}) == 4
    assert dict_total_str_length({}) == 0
    assert dict_total_str_length({"a": [1, 2, 3], "b": {"key": "value"}}) == 8

def test_key_overlap():
    """Test the key_overlap function.

    Verifies that the function correctly calculates the ratio of overlapping
    keys between two dictionaries, including edge cases like empty dictionaries
    and invalid inputs.
    """
    assert key_overlap({"a": 1, "b": 2}, {"b": 3, "c": 4}) == .5
    assert key_overlap({"a": 1, "b": 2}, {"a": 3, "b": 4}) == 1.0
    assert key_overlap({}, {"a": 1}) == 0
    assert key_overlap({"a": 1}, {}) == 0
    assert key_overlap({}, {}) == 0

    with pytest.raises(TypeError):
        key_overlap({"a": 1}, "not a dict")     # type:ignore
    with pytest.raises(TypeError):
        key_overlap("not a dict", {"b": 2})     # type:ignore
