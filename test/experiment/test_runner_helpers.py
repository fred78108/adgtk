"""Tests for adgtk.experiment.runner helper functions.

Covers: _contains_batch_dir, _load_experiment_file (success and error paths).

pytest test/experiment/test_runner_helpers.py
"""

import pytest
import yaml
from unittest.mock import patch
import adgtk.experiment.runner as runner
from adgtk.utils.defaults import BATCH_DEF_DIR


# ---------------------------------------------------------------------------
# _contains_batch_dir
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,expected", [
    (f"{BATCH_DEF_DIR}/my_batch.yaml", True),
    (f"some/other/{BATCH_DEF_DIR}/file.yaml", True),
    ("blueprints/exp.yaml", False),
    ("results/001/run.yaml", False),
    (f"not_{BATCH_DEF_DIR}/file.yaml", False),
])
def test_contains_batch_dir(path, expected):
    assert runner._contains_batch_dir(path) == expected


# ---------------------------------------------------------------------------
# _load_experiment_file
# ---------------------------------------------------------------------------

def _minimal_exp_yaml() -> dict:
    return {
        "description": "test experiment",
        "attribute": "scenario",
        "factory_id": "my_factory",
        "factory_init": True,
        "init_config": [
            {
                "attribute": "param",
                "factory_id": None,
                "factory_init": False,
                "init_config": "value",
            }
        ],
    }


def test_load_experiment_file_with_full_path(tmp_path):
    exp_file = tmp_path / "my_exp.yaml"
    exp_file.write_text(yaml.dump(_minimal_exp_yaml()))
    result = runner._load_experiment_file(str(exp_file))
    assert result.description == "test experiment"


def test_load_experiment_file_with_yaml_extension(tmp_path):
    exp_file = tmp_path / "exp.yaml"
    exp_file.write_text(yaml.dump(_minimal_exp_yaml()))
    result = runner._load_experiment_file(str(exp_file))
    assert result.factory_id == "my_factory"


def test_load_experiment_file_auto_appends_yaml_extension(tmp_path):
    # Pass a full absolute path without extension — the function adds .yaml
    exp_file = tmp_path / "exp.yaml"
    exp_file.write_text(yaml.dump(_minimal_exp_yaml()))
    # Strip the extension so the function must add it back
    path_no_ext = str(tmp_path / "exp")
    # The function prepends "blueprints/" when no blueprint dir in path;
    # patch the join so the absolute tmp_path is used directly
    with patch("adgtk.experiment.runner._contains_blueprint_dir", return_value=True):
        result = runner._load_experiment_file(path_no_ext)
    assert result.factory_id == "my_factory"


def test_load_experiment_file_malformed_yaml(tmp_path):
    exp_file = tmp_path / "bad.yaml"
    exp_file.write_text("key: [unclosed bracket")
    with pytest.raises(ValueError, match="Malformed"):
        runner._load_experiment_file(str(exp_file))
