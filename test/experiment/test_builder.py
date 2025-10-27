# pyright: reportIncompatibleVariableOverride=false
# pyright: reportArgumentType=false
# pyright: reportFunctionMemberAccess=false

"""test_builder.py
Automated tests for adgtk.experiment.builder, fully mocked to require no human interaction.

Note: original coding via a model. modified to meet my needs.

Testing
=======
- with prints from builder: pytest -s test/experiment/test_builder.py
- no prints from builder: pytest test/experiment/test_builder.py
"""
import os
import pytest       # type: ignore
import shutil
from unittest.mock import MagicMock
from adgtk.experiment import builder
from adgtk.experiment.structure import AttributeEntry
from adgtk.factory.structure import BlueprintQuestion

# ----------------------------------------------------------------------
# data and fixtures
# ----------------------------------------------------------------------

class DummyEntry:
    def __init__(self, factory_id, summary):
        self.factory_id = factory_id
        self.summary = summary

@pytest.fixture
def mock_factory(monkeypatch):
    factory_mock = MagicMock()
    entries = [
        DummyEntry(factory_id="f1", summary="First"),
        DummyEntry(factory_id="f2", summary="Second"),
    ]
    factory_mock.list_entries.return_value = entries
    factory_mock.entry_exists.side_effect = lambda x: x in {"f1", "f2"}
    factory_mock.group_exists.side_effect = lambda x: x in {"scenario"}

    def interview_stub(factory_id):
        if factory_id == "f1":
            return [
                BlueprintQuestion(
                    entry_type="str",
                    attribute="foo",
                    question="Enter foo",
                )
            ]
        return []

    factory_mock.get_interview.side_effect = interview_stub
    monkeypatch.setattr("adgtk.experiment.builder.factory", factory_mock)
    return factory_mock

@pytest.fixture
def mock_input(monkeypatch):
    """This is the sequence of answers to simulate."""
    answers = iter([
        "yes",                # automatically create name?
        "test",               # prefix of name
        "ExpDescription",     # Description
        "0",                  # Select "f1"
        "interview_answer",   # Value for "foo"
    ])
    monkeypatch.setattr(
        "adgtk.experiment.builder.get_user_input",
        lambda **kwargs: next(answers))
    return answers

@pytest.fixture(autouse=True)
def reset_working_on():
    builder._working_on.clear()
    yield
    builder._working_on.clear()


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def _cleanup_tracking_folder(tracking_dir: str = ".tracking") -> None:
    """Removes the .tracking directory if it exists.

    :param tracking_dir: Path to the tracking directory
    :type tracking_dir: str
    """
    if os.path.exists(tracking_dir) and os.path.isdir(tracking_dir):
        try:
            shutil.rmtree(tracking_dir)
            assert True
        except Exception as e:
            assert False, f"Failed to remove tracking directory: {e}"

# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


def test_get_user_selection_from_group_valid(mock_factory, monkeypatch, capsys):
    monkeypatch.setattr(
        "adgtk.experiment.builder.get_user_input", lambda **_: "0")
    result = builder._get_user_selection_from_group(
        group="test_group", user_prompt="Pick one"
    )
    assert result == "f1"


def test_get_user_selection_from_group_invalid_index(
    mock_factory,
    monkeypatch,
    capsys
):
    monkeypatch.setattr(
        "adgtk.experiment.builder.get_user_input", lambda **_: "1")
    result = builder._get_user_selection_from_group(
        group="test_group", user_prompt="Pick one"
    )
    assert result == "f2"


def test_get_user_selection_from_group_invalid_value(
    mock_factory,
    monkeypatch,
    capsys
):
    monkeypatch.setattr("adgtk.experiment.builder.get_user_input", lambda **_: "bad_input")
    with pytest.raises(ValueError):
        builder._get_user_selection_from_group(
            group="test_group", user_prompt="Pick one"
        )


def test_perform_interview_str(monkeypatch, mock_factory, capsys):
    question = MagicMock(
        entry_type="str",
        attribute="foo",
        question="Enter foo",
        choices=None,
        group=None
    )
    builder._working_on = ["f1"]
    monkeypatch.setattr("adgtk.experiment.builder.get_user_input", lambda **kwargs: "bar_value")
    attrs = builder._perform_interview([question])
    assert attrs[0].attribute == "foo"
    assert attrs[0].init_config == "bar_value"


def test_expand_with_interview(monkeypatch, mock_factory, capsys):
    builder._working_on = []
    monkeypatch.setattr(
        "adgtk.experiment.builder.get_user_input", lambda **kwargs: "baz_value")
    result = builder._expand("f1", "myattr")
    assert isinstance(result, AttributeEntry)
    assert result.factory_id == "f1"
    assert result.attribute == "myattr"
    assert isinstance(result.init_config, list)
    assert result.init_config[0].init_config == "baz_value"


def test_expand_with_no_interview(monkeypatch, mock_factory, capsys):
    mock_factory.get_interview.side_effect = lambda factory_id: []
    builder._working_on = []
    result = builder._expand("f1", "no_questions")
    assert isinstance(result, AttributeEntry)
    assert result.attribute == "no_questions"
    assert result.init_config is None


def test_build_experiment(
    monkeypatch,
    mock_factory,
    mock_input,
    tmp_path,
    capsys
):

    # Patch open to write to a temp file, so we don't hit the real file system
    out_file = tmp_path / "test.yaml"
    out_file_str = str(out_file)
    monkeypatch.setattr("os.path.join", lambda *args, **kwargs: out_file_str)

    builder.build_experiment()

    # Check YAML file was written and contents are correct
    import yaml
    with open(out_file, "r") as f:
        data = yaml.safe_load(f)
    assert data["name"] == "test.0.1"                   # sys named it
    assert data["description"] == "ExpDescription"
    assert data["attribute"] == "experiment"
    # an experiment should always be a dict for the scenario then
    # the scenario should have a list of dicts w/init_config
    assert isinstance(data["init_config"], dict)    
    assert isinstance(data["init_config"]["init_config"], list)
    assert data["init_config"]["init_config"][0]["attribute"] == "foo"
    assert data["init_config"]["init_config"][0]["init_config"] == "interview_answer"

    # and cleanup. needed because we use an automatic name
    _cleanup_tracking_folder()
