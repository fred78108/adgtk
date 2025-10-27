# pyright: reportIncompatibleVariableOverride=false
# pyright: reportArgumentType=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportIncompatibleMethodOverride=false

"""test_runner.py
Automated tests for adgtk.experiment.runner, fully mocked to require no human interaction.

Note: original coding via a model. modified to meet my needs.

TODO
====
1. continue cleaning up and getting this code tight

Testing
=======
pytest -s test/experiment/test_runner.py
"""

import os
import sys
import tempfile
import yaml
import pytest   # type: ignore
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
import adgtk.experiment.runner as runner
from adgtk.experiment.structure import (
    AttributeEntry,
    ExperimentDefinition,
    ScenarioResults,
    ScenarioProtocol,
)
from adgtk.tracking.structure import ExperimentRunFolders

# ---------------------
# Fixtures & Utilities
# ---------------------
@pytest.fixture
def attribute_entry_simple():
    return AttributeEntry(
        attribute="test_attr",
        factory_id="dummy_factory",
        factory_init=False,
        init_config=[True]
    )

@pytest.fixture
def experiment_definition(attribute_entry_simple):
    return ExperimentDefinition(
        name="Test Experiment",
        description="desc",
        attribute="root",
        factory_id="scenario_factory",
        factory_init=True,
        init_config=[
            {
                "attribute": "child",
                "factory_id": "dummy_factory",
                "factory_init": False,
                "init_config": [42]
            }
        ]
    )

@pytest.fixture
def mock_experiment_run_folders():
    return MagicMock(spec=ExperimentRunFolders)

class DummyScenario(ScenarioProtocol):
    def run_scenario(
        self,
        result_folders:ExperimentRunFolders
    ) -> ScenarioResults: # type: ignore

        # This uses a mocked ExperimentRunFolders
        return ScenarioResults(files=[])

# ---------------------
# _contains_blueprint_dir
# ---------------------
@pytest.mark.parametrize("test_path,exp", [
    ("foo/blueprints/bar.yaml", True),
    ("foo/bar.yaml", False),
    ("blueprints/bar.yaml", True),
    ("bar.yaml", False),
    ("", False)
])
def test_contains_blueprint_dir(test_path, exp):
    assert runner._contains_blueprint_dir(test_path) == exp

# ---------------------
# _build_component
# ---------------------
def test_build_component_simple_returns_value():
    ae = AttributeEntry(attribute="a", factory_id="f", factory_init=False, init_config=True)
    assert runner._build_component(ae) is True

def test_build_component_factory_init(monkeypatch):
    def fake_create(factory_id, **args):
        class DummyObj:
            a = 1
        return DummyObj()
    monkeypatch.setattr(runner.factory, "create", fake_create)
    ae = AttributeEntry(
        attribute="a",
        factory_id="f",
        factory_init=True,
        init_config=[
            AttributeEntry(
                attribute="b",
                factory_id=None,
                factory_init=False,
                init_config=True
            )
        ]
    )
    result = runner._build_component(ae)
    assert hasattr(result, "a")

def test_build_component_missing_factory_id():
    ae = {"init_config":True}
    with pytest.raises(ValueError):
        runner._build_component(ae)

def test_build_component_missing():
    ae = AttributeEntry(
        attribute="a", factory_id="f", factory_init=True, init_config=None)
    with pytest.raises(KeyError):
        runner._build_component(ae)


def test_get_scenario_not_scenario_protocol(monkeypatch):
    class NotScenario: pass
    def fake_build_component(attr): return NotScenario()
    monkeypatch.setattr(runner, "_build_component", fake_build_component)
    exp_def = ExperimentDefinition(
        name="Test", description="desc", attribute="x", factory_id="y", factory_init=True, init_config={"attribute":"foo","factory_id":"bar","factory_init":False,"init_config":[1]}
    )
    with pytest.raises(ValueError):
        runner._load_scenario(exp_def)

def test_get_scenario_class_returned(monkeypatch):
    def fake_build_component(attr): return DummyScenario
    monkeypatch.setattr(runner, "_build_component", fake_build_component)
    exp_def = ExperimentDefinition(
        name="Test", description="desc", attribute="x", factory_id="y", factory_init=True, init_config={"attribute":"foo","factory_id":"bar","factory_init":False,"init_config":[1]}
    )
    with pytest.raises(ValueError):
        runner._load_scenario(exp_def)

# ---------------------
# _load_experiment_file
# ---------------------
def test_load_experiment_file_adds_yaml(tmp_path):
    config = {
        "name": "Test",
        "description": "desc",
        "attribute": "foo",
        "factory_id": "bar",
        "factory_init": False,
        "init_config": []
    }
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    fname = bp_dir / "experiment.yaml"
    fname.write_text(yaml.dump(config))
    # Should work with or without .yaml
    loaded = runner._load_experiment_file(str(fname))
    assert loaded.name == "Test"

def test_load_experiment_file_invalid_yaml(tmp_path):
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    fname = bp_dir / "experiment.yaml"
    fname.write_text("bad: [unclosed")
    # Should sys.exit(1) on validation error, so patch sys.exit
    with patch.object(sys, "exit", side_effect=RuntimeError):
        with pytest.raises(ValueError):
            runner._load_experiment_file(str(fname))

def test_load_experiment_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        runner._load_experiment_file(str(tmp_path / "doesnotexist.yaml"))

# ---------------------
# run_scenario
# ---------------------
def test_run_scenario_success(monkeypatch, tmp_path, mock_experiment_run_folders):
    config = {
        "name": "Test",
        "description": "desc",
        "attribute": "root",
        "factory_id": "scenario_factory",
        "factory_init": True,
        "init_config": {
            "attribute": "child",
            "factory_id": "child_factory",
            "factory_init": False,
            "init_config": [1]
        }
    }
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    fname = bp_dir / "scenario.yaml"
    fname.write_text(yaml.dump(config))
    monkeypatch.setattr(runner, "_load_scenario", lambda conf: DummyScenario())
    # Should print result
    runner.run_scenario(str(fname))
