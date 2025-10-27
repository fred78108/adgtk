"""Tests the measurement engine.

This module contains unit tests for the `MeasurementEngine` class and its methods.
The tests ensure that the engine behaves as expected under various scenarios.

Run the tests
=============
To execute the tests, run the following command:
    python -m pytest -s test/measurement/test_engine.py

Note: Initial test script written by AI, updated manually to meet needs.
"""
from typing import Union
import pytest
from unittest.mock import patch
from adgtk.measurements.engine import (
    MeasurementEngine,
    supports_measurement_type
)
from adgtk.measurements.factory import (
    MeasFactoryEntry,
    manual_measurement_factory_register
)

@pytest.fixture()
def mock_factory_entry():
    """Fixture to provide a mock factory entry for testing."""
    return MeasFactoryEntry(
        factory_id="test_id",
        meas_type="direct_measure",
        tags=["test"],
        item=lambda x: x * 2,
        description="Test measurement"
    )

@pytest.fixture(scope="session")
def mock_measurement_registered():
    # Register a mock measurement to the factory
    def mock_measurement(a:Union[int, float]):
        return a * 2
    def mock_compare(a:Union[int, float], b:Union[int, float]):
        return abs(a-b)
    
    manual_measurement_factory_register(
        item=mock_measurement,
        description="Mock measurement for testing",
        tags=["test"],
        factory_id="test_id"
    )    
    manual_measurement_factory_register(
        item=mock_compare,
        description="Mock comparison for testing",
        tags=["test"],
        factory_id="test_compare_id"
    )    

@pytest.fixture
def mock_measurement_engine(mock_measurement_registered):
    """Creates a measurement engine with a registered measurement."""
    # Using 2 methods for adding the measurement, add and via init
    engine = MeasurementEngine(
        engine_id="test_engine",
        add_factory_ids=["test_id"])
    engine.add("test_compare_id")
    return engine


def test_supports_measurement_type_mixed_annotations():
    """Test `supports_measurement_type` with a function that has mixed annotations."""
    def mixed_func(a: int, b) -> bool:
        return a < b

    # Valid argument types
    assert supports_measurement_type(mixed_func, 3, 4.5) is True

    # Invalid argument types
    assert supports_measurement_type(mixed_func, "invalid", 4.5) is False

    # Missing arguments
    assert supports_measurement_type(mixed_func, 3) is False
    assert supports_measurement_type(mixed_func) is False

# --------------- Core engine functionality ---------------
def test_measurement_engine_initialization(mock_measurement_engine):
    """Test that the `MeasurementEngine` initializes correctly."""
    assert mock_measurement_engine.engine_id == "test_engine"
    assert len(mock_measurement_engine.measurements) == 2
    assert len(mock_measurement_engine.details) == 2

def test_add_measurement_invalid_id(mock_measurement_engine):
    """Test adding a measurement with an invalid ID."""
    with patch("adgtk.measurements.engine.get_measurement_factory_entry", side_effect=IndexError):
        mock_measurement_engine.add("invalid_id")
        assert "invalid_id" not in mock_measurement_engine.measurements

# -------- Measurement tests --------
def test_measure(mock_measurement_engine):
    """Test the `measure` method with valid data."""
    mock_measurement_engine.add("test_id")
    data = [1, 2, 3]
    mock_measurement_engine.measure(data, record_as="sum")
    assert mock_measurement_engine.metric_tracker.get_latest_value("test_id") == 12


# -------- Comparison tests --------

def test_compare_valid_data(mock_measurement_engine):
    """Test the `compare` method with valid data."""    
    data = [(1, 2), (3, 10)]
    mock_measurement_engine.compare(data, record_as="avg")
    result = mock_measurement_engine.metric_tracker.get_latest_value(
        "test_compare_id")
    
    assert result == 4
    


def test_debug_report(mock_measurement_engine, capsys):
    """Test debug_report method prints correctly."""
    mock_measurement_engine.debug_report()
    captured = capsys.readouterr()
    assert "Measurement Engine: test_engine" in captured.out

# -------- Report method tests --------

def test_report_empty_engine():
    """Test report method with an empty engine."""
    engine = MeasurementEngine(engine_id="empty_engine")
    report = engine.report()
    
    assert isinstance(report, dict)
    assert report["engine_id"] == "empty_engine"
    assert report["measurements"] == []

def test_report_with_measurements(mock_measurement_engine):
    """Test report method with measurements and data."""
    # Add some measurement data
    data = [1, 2, 3]
    mock_measurement_engine.measure(data, record_as="avg")
    
    # Add comparison data
    compare_data = [(1, 2), (3, 4)]
    mock_measurement_engine.compare(compare_data, record_as="sum")
    
    report = mock_measurement_engine.report()
    
    # Verify report structure
    assert isinstance(report, dict)
    assert report["engine_id"] == "test_engine"
    assert "measurements" in report
    assert len(report["measurements"]) == 2
    
    # Verify measurement data structure
    for measurement in report["measurements"]:
        assert "label" in measurement
        assert "description" in measurement
        assert "data" in measurement
        assert isinstance(measurement["data"], list)

def test_report_measurement_data_content(mock_measurement_engine):
    """Test that report contains correct measurement data content."""
    # Add specific measurement data
    data = [10, 20, 30]
    mock_measurement_engine.measure(data, record_as="raw")
    
    report = mock_measurement_engine.report()
    
    # Find the test_id measurement in the report
    test_measurement = None
    for measurement in report["measurements"]:
        if measurement["label"] == "test_id":
            test_measurement = measurement
            break
    
    assert test_measurement is not None
    assert test_measurement["description"] == "Mock measurement for testing"
    assert len(test_measurement["data"]) > 0

def test_report_with_multiple_measurement_rounds(mock_measurement_engine):
    """Test report with multiple rounds of measurements."""
    # First round
    data1 = [1, 2, 3]
    mock_measurement_engine.measure(data1, record_as="avg")
    
    # Second round
    data2 = [4, 5, 6]
    mock_measurement_engine.measure(data2, record_as="avg")
    
    report = mock_measurement_engine.report()
    
    # Should have data from both rounds
    assert len(report["measurements"]) == 2
    for measurement in report["measurements"]:
        assert len(measurement["data"]) >= 2  # At least 2 measurements per metric