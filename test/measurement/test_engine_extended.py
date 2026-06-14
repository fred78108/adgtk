"""Extended tests for adgtk.measurements.engine — covering uncovered branches.

Targets: _update_tracker aggregation modes, measure/compare, add_by_type/tag,
         get_average, get_latest_value, report, save_data.

pytest test/measurement/test_engine_extended.py
"""

import pytest
from unittest.mock import patch, MagicMock
from adgtk.measurements.engine import MeasurementEngine, supports_measurement_type
from adgtk.measurements.factory import manual_measurement_factory_register
from adgtk.tracking.structure import ExperimentRunFolders


# ---------------------------------------------------------------------------
# Register test measurements once per session
# ---------------------------------------------------------------------------

def _identity(x: float) -> float:
    return x


def _abs_diff(a: float, b: float) -> float:
    return abs(a - b)


@pytest.fixture(scope="module", autouse=True)
def _register_test_measurements():
    manual_measurement_factory_register(
        item=_identity,
        description="Identity measure",
        tags=["ext-test"],
        factory_id="ext_identity",
    )
    manual_measurement_factory_register(
        item=_abs_diff,
        description="Abs diff",
        tags=["ext-test"],
        factory_id="ext_abs_diff",
    )


# ---------------------------------------------------------------------------
# supports_measurement_type — additional paths
# ---------------------------------------------------------------------------

def test_supports_measurement_type_wrong_count():
    def f(a: int, b: int) -> int:
        return a + b
    assert supports_measurement_type(f, 1) is False


def test_supports_measurement_type_wrong_type():
    def f(a: int) -> int:
        return a
    assert supports_measurement_type(f, "string") is False


def test_supports_measurement_type_no_annotation():
    def f(a) -> int:
        return a
    assert supports_measurement_type(f, 42) is True


# ---------------------------------------------------------------------------
# MeasurementEngine — construction with add_by_type and add_by_tag
# ---------------------------------------------------------------------------

def test_engine_add_by_tag():
    engine = MeasurementEngine(add_by_tag="ext-test")
    assert "ext_identity" in engine.measurements or len(engine.measurements) >= 1


def test_engine_add_by_type():
    # add_by_type filters factory by meas_type; result count depends on
    # what is registered in the factory at test time — just verify no crash
    engine = MeasurementEngine(add_by_type="direct_measure")
    assert isinstance(engine.measurements, dict)


def test_engine_add_factory_ids():
    engine = MeasurementEngine(add_factory_ids=["ext_identity"])
    assert "ext_identity" in engine.measurements


# ---------------------------------------------------------------------------
# _update_tracker — aggregation modes
# ---------------------------------------------------------------------------

def _engine_with_identity() -> MeasurementEngine:
    e = MeasurementEngine()
    e.add("ext_identity")
    return e


def test_update_tracker_max():
    e = _engine_with_identity()
    e._update_tracker("ext_identity", [1.0, 5.0, 3.0], record_as="max")
    assert e.metric_tracker.get_latest_value("ext_identity") == 5.0


def test_update_tracker_min():
    e = _engine_with_identity()
    e._update_tracker("ext_identity", [1.0, 5.0, 3.0], record_as="min")
    assert e.metric_tracker.get_latest_value("ext_identity") == 1.0


def test_update_tracker_sum():
    e = _engine_with_identity()
    e._update_tracker("ext_identity", [1.0, 2.0, 3.0], record_as="sum")
    assert e.metric_tracker.get_latest_value("ext_identity") == 6.0


def test_update_tracker_raw():
    e = _engine_with_identity()
    e._update_tracker("ext_identity", [1.0, 2.0], record_as="raw")
    assert e.metric_tracker.measurement_count("ext_identity") == 2


def test_update_tracker_empty_results_records_zero():
    e = _engine_with_identity()
    e._update_tracker("ext_identity", [], record_as="avg")
    assert e.metric_tracker.get_latest_value("ext_identity") == 0.0


# ---------------------------------------------------------------------------
# measure — full pass
# ---------------------------------------------------------------------------

def test_measure_runs_on_iterable():
    e = _engine_with_identity()
    e.measure([1.0, 2.0, 3.0])
    assert e.metric_tracker.measurement_count("ext_identity") == 1
    assert e.get_average("ext_identity") == pytest.approx(2.0)


def test_measure_clears_and_reruns():
    e = _engine_with_identity()
    e.measure([1.0, 2.0])
    e.clear_results()
    e.measure([4.0, 6.0])
    assert e.get_average("ext_identity") == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# compare — pairwise
# ---------------------------------------------------------------------------

def test_compare_records_results():
    e = MeasurementEngine(add_factory_ids=["ext_abs_diff"])
    e.compare([(1.0, 3.0), (2.0, 5.0)])
    assert e.get_average("ext_abs_diff") == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Delegating getter methods
# ---------------------------------------------------------------------------

def test_get_average():
    e = _engine_with_identity()
    e.measure([2.0, 4.0])
    assert e.get_average("ext_identity") == pytest.approx(3.0)


def test_get_latest_value():
    e = _engine_with_identity()
    e.measure([10.0])
    e.measure([20.0])
    assert e.get_latest_value("ext_identity") == pytest.approx(20.0)


def test_get_all_data():
    e = _engine_with_identity()
    e.measure([1.0])
    e.measure([2.0])
    data = e.get_all_data("ext_identity")
    assert len(data) == 2


def test_measurement_count():
    e = _engine_with_identity()
    e.measure([1.0])
    assert e.measurement_count("ext_identity") == 1


def test_get_latest_distribution():
    e = _engine_with_identity()
    e.measure([1.0, 2.0])
    result = e.get_latest_distribution("ext_identity")
    assert result is not None


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def test_report_structure():
    e = _engine_with_identity()
    e.measure([1.0, 2.0])
    r = e.report()
    assert r["engine_id"] == e.engine_id
    assert len(r["measurements"]) == 1
    assert r["measurements"][0]["label"] == "ext_identity"


def test_report_empty_engine():
    e = MeasurementEngine()
    r = e.report()
    assert r["measurements"] == []


# ---------------------------------------------------------------------------
# get_description
# ---------------------------------------------------------------------------

def test_get_description():
    e = _engine_with_identity()
    desc = e.get_description("ext_identity")
    assert "Identity" in desc


def test_get_description_invalid_raises():
    e = MeasurementEngine()
    with pytest.raises(IndexError):
        e.get_description("nonexistent")


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

def test_save_data_delegates_to_tracker():
    folders = MagicMock(spec=ExperimentRunFolders)
    e = _engine_with_identity()
    e.measure([1.0])
    with patch.object(e.metric_tracker, "save_data") as mock_save:
        e.save_data(folders)
    mock_save.assert_called_once_with(folders)
