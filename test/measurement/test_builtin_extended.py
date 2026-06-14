"""Extended tests for adgtk.measurements.builtin — covering uncovered functions.

Covers: exact_match, token_f1, json_valid, schema_key_depth, dict_schema_match,
        list_item_type_consistency, and dict_total_str_length list/nested paths.

pytest test/measurement/test_builtin_extended.py
"""

import pytest
from adgtk.measurements.builtin import (
    exact_match,
    token_f1,
    json_valid,
    schema_key_depth,
    dict_schema_match,
    list_item_type_consistency,
    dict_total_str_length,
)


# ---------------------------------------------------------------------------
# exact_match
# ---------------------------------------------------------------------------

def test_exact_match_identical():
    assert exact_match("hello", "hello") == 1.0


def test_exact_match_different():
    assert exact_match("hello", "world") == 0.0


def test_exact_match_empty_strings():
    assert exact_match("", "") == 1.0


def test_exact_match_case_sensitive():
    assert exact_match("Hello", "hello") == 0.0


# ---------------------------------------------------------------------------
# token_f1
# ---------------------------------------------------------------------------

def test_token_f1_identical():
    assert token_f1("the cat sat", "the cat sat") == pytest.approx(1.0)


def test_token_f1_partial_overlap():
    result = token_f1("the cat sat", "the dog sat")
    assert 0.0 < result < 1.0


def test_token_f1_no_overlap():
    assert token_f1("hello world", "foo bar") == 0.0


def test_token_f1_empty_pred():
    assert token_f1("", "hello") == 0.0


def test_token_f1_empty_gold():
    assert token_f1("hello", "") == 0.0


def test_token_f1_both_empty():
    assert token_f1("", "") == 0.0


def test_token_f1_case_insensitive():
    assert token_f1("The Cat", "the cat") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# json_valid
# ---------------------------------------------------------------------------

def test_json_valid_valid_json():
    assert json_valid('{"key": "value"}') == 1.0


def test_json_valid_valid_list():
    assert json_valid('[1, 2, 3]') == 1.0


def test_json_valid_valid_number():
    assert json_valid('42') == 1.0


def test_json_valid_invalid_json():
    assert json_valid("not json") == 0.0


def test_json_valid_empty_string():
    assert json_valid("") == 0.0


def test_json_valid_none():
    assert json_valid(None) == 0.0  # type: ignore


# ---------------------------------------------------------------------------
# schema_key_depth
# ---------------------------------------------------------------------------

def test_schema_key_depth_flat():
    assert schema_key_depth({"a": 1, "b": 2}) == 1


def test_schema_key_depth_nested():
    assert schema_key_depth({"a": {"b": {"c": 1}}}) == 3


def test_schema_key_depth_empty():
    assert schema_key_depth({}) == 1


def test_schema_key_depth_mixed_depth():
    d = {"a": 1, "b": {"c": {"d": 1}}}
    assert schema_key_depth(d) == 3


# ---------------------------------------------------------------------------
# dict_schema_match
# ---------------------------------------------------------------------------

def test_dict_schema_match_identical():
    d = {"a": 1, "b": {"c": 2}}
    assert dict_schema_match(d, d) == pytest.approx(1.0)


def test_dict_schema_match_no_overlap():
    a = {"x": 1}
    b = {"y": 2}
    assert dict_schema_match(a, b) == 0.0


def test_dict_schema_match_partial():
    a = {"x": 1, "y": 2}
    b = {"x": 1, "z": 3}
    result = dict_schema_match(a, b)
    assert 0.0 < result < 1.0


def test_dict_schema_match_both_empty():
    assert dict_schema_match({}, {}) == 1.0


def test_dict_schema_match_nested_paths():
    a = {"a": {"b": 1}}
    b = {"a": {"b": 2}}
    assert dict_schema_match(a, b) == pytest.approx(1.0)


def test_dict_schema_match_type_error():
    with pytest.raises(TypeError):
        dict_schema_match({"a": 1}, "not a dict")  # type: ignore


# ---------------------------------------------------------------------------
# list_item_type_consistency
# ---------------------------------------------------------------------------

def test_list_item_type_consistency_uniform_int():
    assert list_item_type_consistency([1, 2, 3]) == pytest.approx(1.0)


def test_list_item_type_consistency_uniform_str():
    assert list_item_type_consistency(["a", "b", "c"]) == pytest.approx(1.0)


def test_list_item_type_consistency_mixed():
    result = list_item_type_consistency([1, "a", 2, "b", 3])
    assert result == pytest.approx(3 / 5)


def test_list_item_type_consistency_empty():
    assert list_item_type_consistency([]) == 0.0


def test_list_item_type_consistency_single():
    assert list_item_type_consistency([42]) == 1.0


# ---------------------------------------------------------------------------
# dict_total_str_length — list item paths
# ---------------------------------------------------------------------------

def test_dict_total_str_length_with_list_of_strings():
    d = {"items": ["hello", "world"]}
    assert dict_total_str_length(d) == 10


def test_dict_total_str_length_with_list_of_numbers():
    d = {"nums": [1, 2, 3]}
    assert dict_total_str_length(d) == 3


def test_dict_total_str_length_nested_dict():
    d = {"outer": {"inner": "hi"}}
    assert dict_total_str_length(d) == 2


def test_dict_total_str_length_list_with_mixed_types():
    d = {"mixed": [1, "abc", 2.5]}
    assert dict_total_str_length(d) == 1 + 3 + 3
