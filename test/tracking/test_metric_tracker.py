"""Testing of the metric tracker
"""


import os
import shutil
import logging
import pytest
from adgtk.common import (
    METRICS_DATA_FOLDER,
    METRICS_FOLDER,
    METRICS_IMG_FOLDER)
from adgtk.tracking import MetricTracker

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/tracking/test_metric_tracker.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------



@pytest.fixture()
def loaded_tracker() -> MetricTracker:
    metric_tracker = MetricTracker()
    metric_tracker.register_metric(
        label="test1",
        metadata={
            "can_be_anything": True,
            "output_type": "raw"
        })

    metric_tracker.register_metric(
        label="test2",
        metadata={
            "can_be_anything": True,
            "output_type": "avg"
        })

    # load data
    metric_tracker.add_raw_data(
        label="test1",
        values=[.1, .2, .3, .5, .7, .8, .9, .95, .99])

    metric_tracker.add_raw_data(
        label="test2",
        values=[7.1, 2.2, 3.3, 4.5, 5.7, 6.8, 1.9, 2.95, 3.99])

    return metric_tracker
# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_metric_tracker_register():
    """test registration of a metric"""
    # setup
    metric_tracker = MetricTracker()
    assert len(metric_tracker.metrics.keys()) == 0

    # exercise
    metric_tracker.register_metric(label="test1")

    # validate
    assert len(metric_tracker.metrics.keys()) == 1
    assert isinstance(metric_tracker.metrics["test1"], list)


def test_metric_tracker_metric_exists():
    """test metric exists method"""
    # setup
    metric_tracker = MetricTracker()
    metric_tracker.register_metric(label="test1")

    # exercise
    assert metric_tracker.metric_exists("test1")
    assert not metric_tracker.metric_exists("test2")


def test_metric_tracker_remove_metric():
    """test removal of a metric"""
    # setup
    metric_tracker = MetricTracker()
    metric_tracker.register_metric(label="test1")
    assert metric_tracker.metric_exists("test1")
    # exercise
    metric_tracker.remove_metric("test1")
    assert not metric_tracker.metric_exists("test1")


def test_metric_tracker_metric_labels():
    """test fetch of metric labels"""
    # setup
    metric_tracker = MetricTracker()
    metric_tracker.register_metric(label="test1")
    metric_tracker.register_metric(label="test2")
    # exercise
    labels = metric_tracker.metric_labels()
    assert isinstance(labels, list)
    assert "test1" in labels
    assert "test2" in labels
    assert len(labels) == 2


def test_metric_tracker_get_latest_value():
    """test fetch last value"""
    # setup
    metric_tracker = MetricTracker()
    metric_tracker.register_metric(label="test1")
    metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=2)
    metric_tracker.add_data(label="test1", value=5)
    metric_tracker.add_data(label="test2", value=1)
    metric_tracker.add_data(label="test1", value=15)
    test1_last = metric_tracker.get_latest_value('test1')
    assert test1_last == 15
    test2_last = metric_tracker.get_latest_value('test2')
    assert test2_last == 1


def test_metric_tracker_register_duplicate():
    """test that duplicate register does not harm existing"""
    # setup
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    metric_tracker.add_data(label="test1", value=.1)
    assert not metric_tracker.register_metric(label="test1")
    test1_last = metric_tracker.get_latest_value('test1')
    assert test1_last == .1


def test_metric_tracker_get_average():
    """Validate average works as expected"""
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=100)
    metric_tracker.add_data(label="test1", value=2)
    metric_tracker.add_data(label="test1", value=3)
    avg = metric_tracker.get_average(label="test1")
    assert avg == 2


def test_metric_tracker_get_sum():
    """Validate sum works as expected"""
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=100)
    metric_tracker.add_data(label="test1", value=2)
    metric_tracker.add_data(label="test1", value=3)
    avg = metric_tracker.get_sum(label="test1")
    assert avg == 6


def test_metric_tracker_get_all_data():
    """Validate get_all_data works as expected"""

    # setup
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=100)
    metric_tracker.add_data(label="test1", value=2)
    metric_tracker.add_data(label="test1", value=3)

    # exercise / validate
    data = metric_tracker.get_all_data("test1")
    assert len(data) == 3

    # validate no harm to original
    assert data[0] == 1
    data[0] = 5
    assert metric_tracker.metrics["test1"][0] == 1


def test_metric_tracker_clear_metric():
    """Validate clear works as expected"""

    # setup
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=100)
    metric_tracker.add_data(label="test1", value=2)
    metric_tracker.add_data(label="test1", value=3)

    # exercise / validate
    metric_tracker.clear_metric("test1")
    data = metric_tracker.get_all_data("test1")
    assert len(data) == 0
    data2 = metric_tracker.get_all_data("test2")
    assert len(data2) == 1


def test_metric_tracker_add_raw_data():
    """Validate add_raw_data works as expected"""

    # setup
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=1)
    metric_tracker.add_raw_data(label="test1", values=[1, 1, 2])

    # exercise / validate
    data = metric_tracker.get_all_data("test1")
    assert len(data) == 4


def test_metric_tracker_measurement_count():
    """Validate measurement_count works as expected"""

    # setup
    metric_tracker = MetricTracker()
    assert metric_tracker.register_metric(label="test1")
    assert metric_tracker.register_metric(label="test2")
    metric_tracker.add_data(label="test1", value=1)
    metric_tracker.add_data(label="test2", value=1)
    metric_tracker.add_raw_data(label="test1", values=[1, 1, 2])

    # exercise / validate
    assert metric_tracker.measurement_count("test1") == 4
    assert metric_tracker.measurement_count("test2") == 1
