"""_summary_
"""

import os
import shutil
import logging
import pytest
from adgtk.factory import FactoryImplementable
from adgtk.scenario import Scenario
from scenario.measure import (
    MeasureDatasetScenario,
    MeasureModelPerformanceScenario)
# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/scenario/test_scenario_measure.py


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


@pytest.fixture()
def temp_dir(request):
    if os.path.exists(TMP_DIR) and CLEAN_BEFORE_RUN:
        shutil.rmtree(TMP_DIR)

    def teardown():
        if os.path.exists(TMP_DIR) and DO_CLEANUP:
            shutil.rmtree(TMP_DIR)

    request.addfinalizer(teardown)

    return TMP_DIR

# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_meas_ds_type_adherence():
    """Validates protocol adherence"""
    assert isinstance(MeasureDatasetScenario, FactoryImplementable)
    assert isinstance(MeasureDatasetScenario, Scenario)


def test_meas_model_type_adherence():
    """Validates protocol adherence"""
    assert isinstance(
        MeasureModelPerformanceScenario, FactoryImplementable)
    assert isinstance(MeasureModelPerformanceScenario, Scenario)
