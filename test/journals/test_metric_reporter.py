"""_summary_
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
# py -m pytest -s test/journals/test_metric_reporter.py


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
