"""Presentation Testing.
"""

import os
import shutil
import logging
import toml
import matplotlib
import pytest
import numpy as np
import test.mockdata.mock as mockdata
from adgtk.factory import ObjectFactory
from adgtk.common import DEFAULT_SETTINGS
from structure.presentation.simple import YamlPresentation
from structure.presentation.plots import (
    plot_multiple_lines,
    multi_line_data_validation)

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_presentation.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)


DO_CLEANUP = True
CLEAN_BEFORE_RUN = True
TMP_DATA_DIR = "tmp-data-dir"


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
two_meas = [
    [1, 2, 3, 4, 5],
    [2, 4, 3, 1, 7]
]
two_meas_labels = ["meas1", "meas2"]

big_data = [
    np.random.rand(10),
    np.random.rand(10),
    np.random.rand(10),
    np.random.rand(10),
    np.random.rand(10),
]

big_data_labels = ["meas1", "meas2", "meas3", "meas4", "meas5"]

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


@pytest.fixture(name="loaded_factory")
def loaded_factory_fixture(request, settings_file):
    """Creates a loaded factory"""
    factory = ObjectFactory(
        create_blueprint_files=False,
        journal=None)
    factory.register(creator=YamlPresentation)
    return factory

# ----------------------------------------------------------------------
# Yaml Testing
# ----------------------------------------------------------------------


def test_yaml_presentation_flow_false(loaded_factory):
    """Tests the yaml presentation, the factory loading and creating of
    the presentation object as well. Lastly tests the flow style w/False
    """
    presentor: YamlPresentation = loaded_factory.create({
        "group_label": "presentation",
        "type_label": "yaml",
        "arguments": {"default_flow_style": False}
    })
    result = presentor.present(mockdata.sample_data_one)
    assert isinstance(result, str)
    assert "age:" in result
    assert "is_student: true" in result
    assert "{" not in result


def test_yaml_presentation_flow_true(loaded_factory):
    """Tests the yaml presentation, the factory loading and creating of
    the presentation object as well. Lastly tests the flow style w/True
    """
    presentor: YamlPresentation = loaded_factory.create({
        "group_label": "presentation",
        "type_label": "yaml",
        "arguments": {"default_flow_style": True}
    })
    result = presentor.present(mockdata.sample_data_one)
    assert isinstance(result, str)
    assert "age:" in result
    assert "is_student: true" in result
    assert "{" in result


def test_yaml_protocol_adherence():
    """Validates adherence to the protocol
    """
    a = YamlPresentation()
    assert isinstance(a, YamlPresentation)

# ---------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------


def test_plot_generate_return_value(temp_dir):
    """Verifies that a plot generates and returns a"""
    response = plot_multiple_lines(
        data=two_meas,
        labels=two_meas_labels)
    assert type(response) == matplotlib.figure.Figure


def test_plot_generate_w_file_save(temp_dir):
    """Verifies that the file exists with data plotted"""
    expected = os.path.join(temp_dir, "test.png")
    _ = plot_multiple_lines(
        title="Demo-test1",
        x_label="x-label",
        y_label="y-label",
        data_label="mock",
        show_legend=True,
        filename=expected,
        data=two_meas,
        labels=two_meas_labels)

    assert os.path.exists(expected)


def test_plot_big_w_file_save(temp_dir):
    """Verifies that the file exists with larger data"""
    expected = os.path.join(temp_dir, "test_big_data.png")
    _ = plot_multiple_lines(
        title="Demo-test1",
        x_label="x-label",
        y_label="y-label",
        data_label="mock",
        show_legend=True,
        filename=expected,
        data=big_data,
        labels=big_data_labels)

    assert os.path.exists(expected)


def test_plot_invalid_labels(temp_dir):
    """Verifies that the file exists with larger data"""
    expected = os.path.join(temp_dir, "invalid_labels.png")
    _ = plot_multiple_lines(
        title="Demo-test1",
        x_label="x-label",
        y_label="y-label",
        data_label="mock",
        show_legend=True,
        filename=expected,
        data=big_data,
        labels=two_meas_labels)

    assert os.path.exists(expected)


def test_multi_line_data_validation_valid():
    assert multi_line_data_validation(big_data)


def test_multi_line_data_validation_invalids():
    """Quick confirmation of potential issues with data formatting"""
    assert not multi_line_data_validation("4")
    assert not multi_line_data_validation(4)
    assert not multi_line_data_validation([1, 2, 4])
    assert not multi_line_data_validation([[]])
    assert not multi_line_data_validation(["1", "2", "3"])
