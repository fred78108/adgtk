"""Testing the common structure functions, etc
"""

# py -m pytest -s test/common/test_structure.py

import anytree as anyTree
from adgtk.common import (
    FactoryBlueprint,
    build_tree,
    convert_exp_def_to_string,
    is_blueprint,
    is_valid_arg_setting,
    default_is_arg_type,
    ArgumentSetting,
    ArgumentType)


def test_is_blueprint_w_blueprint():
    """validates function works with a blueprint"""
    sample = FactoryBlueprint(
        description="test",
        group_label="a",
        type_label="b",
        arguments={})

    assert is_blueprint(sample)


def test_is_blueprint_w_dict():
    """validates function works with a dict"""
    sample = {
        "description": "test",
        "group_label": "a",
        "type_label": "b",
        "arguments": {}
    }

    assert is_blueprint(sample)


def test_is_blueprint_w_missing_arg():
    """validates function works with a dict"""
    sample = {
        "group_label": "a",
        "type_label": "b"
    }

    assert not is_blueprint(sample)


def test_is_blueprint_w_missing_group():
    """validates function works with a dict"""
    sample = {
        "type_label": "b",
        "arguments": {}
    }

    assert not is_blueprint(sample)


def test_is_blueprint_w_missing_type():
    """validates function works with a dict"""
    sample = {
        "group_label": "a",
        "arguments": {}
    }

    assert not is_blueprint(sample)


def test_is_blueprint_w_invalid_group():
    """validates function works with a dict"""
    sample = {
        "group_label": 1,
        "type_label": "b",
        "arguments": {}
    }

    assert not is_blueprint(sample)


def test_is_blueprint_w_invalid_type():
    """validates function works with a dict"""
    sample = {
        "group_label": "A",
        "type_label": 2,
        "arguments": {}
    }

    assert not is_blueprint(sample)


def test_is_blueprint_w_invalid_arg():
    """validates function works with a dict"""
    sample = {
        "group_label": "a",
        "type_label": "b",
        "arguments": ArgumentSetting(
            argument_type=ArgumentType.INT,
            default_value=1,
            help_str="aa"
        )
    }

    assert not is_blueprint(sample)

# --------------- is_valid_arg_setting ----------------------


def test_valid_arg_setting():
    """Validates a check w/invalid returns False"""
    sample = {
        "help_str": "test",
        "default_value": 1,
        "argument_type": ArgumentType.INT}
    assert is_valid_arg_setting(sample)


def test_invalid_arg_setting_missing_help():
    """Validates a check w/invalid returns False"""
    sample = {
        "default_value": 1,
        "argument_type": ArgumentType.INT}
    assert not is_valid_arg_setting(sample)

# --------------- default_is_arg_type ----------------------


def test_default_is_arg_type():
    """Validates a check w/invalid returns False"""
    sample = {
        "help_str": "test",
        "default_value": 1,
        "argument_type": ArgumentType.INT}
    assert default_is_arg_type(sample)


def test_default_is_arg_type_not_int():
    """Validates a check w/invalid returns False"""
    sample = {
        "default_value": "1",
        "argument_type": ArgumentType.INT}
    assert not default_is_arg_type(sample)


# --------------- build tree tests ----------------------

def test_build_tree():
    """Validates basic tree building functions to include a list"""

    root = anyTree.Node("a")
    sample = {
        "group_label": "a",
        "type_label": "b",
        "arguments": {
            "help_str": "test",
            "meas_set": [{'group_label': 'measurement', 'type_label': 'word-count', 'arguments': {'tracker_label': 'word-count', 'use_stopwords': False, 'ignore_case': True}}],
            "argument_type": ArgumentType.LIST}
    }

    result = build_tree(sample, parent=root)
    result_str = anyTree.RenderTree(root, maxlevel=None).by_attr("name")
    # basic checks
    assert isinstance(result_str, str)
    assert "word-count" in result_str
    assert len(result_str) > 100
    assert "[" not in result_str
    assert "{" not in result_str


def test_convert_exp_def_to_string():
    """Validates basic tree building functions to include a list"""

    root = anyTree.Node("a")
    sample = {
        "group_label": "a",
        "type_label": "b",
        "arguments": {
            "help_str": "test",
            "meas_set": [{'group_label': 'measurement', 'type_label': 'word-count', 'arguments': {'tracker_label': 'word-count', 'use_stopwords': False, 'ignore_case': True}}, {'group_label': 'measurement', 'type_label': 'second-count', 'arguments': {'tracker_label': 'second-count', 'use_stopwords': False, 'ignore_case': True}}],
            "argument_type": ArgumentType.LIST}
    }

    result_str = convert_exp_def_to_string(sample)
    # print(result_str)
    assert isinstance(result_str, str)
    assert "word-count" in result_str
    assert "second-count" in result_str
    assert len(result_str) > 100
    assert "[" not in result_str
    assert "{" not in result_str
