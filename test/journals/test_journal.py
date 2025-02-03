"""Tests Journal functionality.
"""


import os
import shutil
import logging
import pytest
import toml
from adgtk.common import DEFAULT_JOURNAL_REPORTS_DIR, DEFAULT_SETTINGS
from adgtk.journals import ProjectJournal
from adgtk.journals.experiment import (
    PREVIEW_REPORT_FILENAME,
    ExperimentJournal)


# ----------------------------------------------------------------------
# py -m pytest -s test/journals/test_journal.py
# ----------------------------------------------------------------------

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
# Fixtures & functions
# ----------------------------------------------------------------------


@pytest.fixture(name="settings_file")
def temp_settings_file(request):
    with open(file="project.toml", encoding="utf-8", mode="w") as outfile:
        output = toml.dumps(DEFAULT_SETTINGS)
        outfile.write(output)

    def teardown():
        if os.path.exists("project.toml") and DO_CLEANUP:
            os.remove("project.toml")

    request.addfinalizer(teardown)


@pytest.fixture(name="temp_dir")
def temp_dir_fixture(request):
    """Creates a temp dir for testing"""
    if os.path.exists(TMP_DIR) and CLEAN_BEFORE_RUN:
        shutil.rmtree(TMP_DIR)

    def teardown():
        if os.path.exists(TMP_DIR) and DO_CLEANUP:
            shutil.rmtree(TMP_DIR)

    request.addfinalizer(teardown)

    return TMP_DIR


@pytest.fixture(name="template_dir")
def temp_template_fixture(request):
    """Creates a temp dir for testing"""
    # create folder
    os.makedirs("templates", exist_ok=True)
    # copy files
    source_dir = os.path.join("project_template", "templates")
    for filename in os.listdir(source_dir):
        # Check if it's a file (not a directory) if os.path.isfile(source_file): shutil.copy2(source_file, destination_file) print(f"Copied {filename} to {destination_dir}")
        source_file = os.path.join(source_dir, filename)
        destination_file = os.path.join("templates", filename)
        shutil.copy2(source_file, destination_file)

    def teardown():
        if os.path.exists("templates") and DO_CLEANUP:
            shutil.rmtree("templates")

    request.addfinalizer(teardown)

    return TMP_DIR


@pytest.fixture(name="loaded_journal")
def load_journal_fixture() -> ExperimentJournal:
    journal = ExperimentJournal(use_formatting=True)
    journal.add_entry(
        include_timestamp=True,
        entry_type="comment",
        entry_text="test message 1",
        component="c1")
    journal.add_entry(
        include_timestamp=True,
        entry_type="comment",
        entry_text="test message 2",
        component="c1")
    journal.add_entry(
        include_timestamp=True,
        entry_type="comment",
        entry_text="test message 3",
        component="c2")
    journal.add_entry(
        entry_type="data",
        entry_text="data_file_1",
        component="d1")
    journal.add_entry(
        entry_type="measurement",
        entry_text="measurement1",
        component="m1")
    journal.add_entry(
        entry_type="measurement",
        entry_text="measurement1",
        component="m2")
    return journal

# ----------------------------------------------------------------------
# Testing - Project Journal
# ----------------------------------------------------------------------


def test_project_journal_creation(temp_dir):
    """Validates journal creates a file correctly."""
    journal = ProjectJournal(results_dir=temp_dir, data_file="test.csv")
    assert os.path.exists(journal.data_file)


def test_project_load_file(temp_dir):
    """Validates loading of a file"""
    journal = ProjectJournal(results_dir=temp_dir, data_file="test.csv")
    journal.add_entry(
        name="test",
        status="pending",
        observations='This is, a test of the "delimeter"')
    journal2 = ProjectJournal(results_dir=temp_dir, data_file="test.csv")
    assert len(journal2) == 1


def test_project_update(temp_dir):
    """Validates updating an experiment"""
    journal = ProjectJournal(results_dir=temp_dir, data_file="test.csv")
    journal.add_entry(
        name="test",
        status="pending",
        observations='This is, a test of the "delimeter"')
    journal.update_entry(name="test", status="active")
    assert journal.experiments["test"].status == "active"


def test_project_update_second(temp_dir):
    """Validates updating an experiment"""
    journal = ProjectJournal(results_dir=temp_dir, data_file="test-bool.csv")
    journal.add_entry(name="test1", status="pending")
    assert journal.experiment_found("test1")
    assert not journal.experiment_found("test2")

# ----------------------------------------------------------------------
# Testing - Experiment Journal
# ----------------------------------------------------------------------


def test_journal_add_entry_comment(settings_file):
    journal = ExperimentJournal(use_formatting=False)
    expected = "test1"
    journal.add_entry(
        entry_type="comment",
        entry_text=expected,
        include_timestamp=False)

    assert expected == journal._comments[0]


def test_journal_add_entry_measurement(settings_file):
    journal = ExperimentJournal(use_formatting=False)
    expected = "test1"
    journal.add_entry(
        entry_type="measurement",
        entry_text=expected,
        include_timestamp=False)

    assert expected == journal._measurements[0]


def test_experiment_journal_preview(
    settings_file,
    loaded_journal,
    template_dir, temp_dir
):
    """Validates a preview report is created"""
    expected = os.path.join(
        temp_dir,
        DEFAULT_JOURNAL_REPORTS_DIR,
        PREVIEW_REPORT_FILENAME)
    # before
    if os.path.exists(expected):
        # cleanup if it exists
        os.remove(expected)
        assert not os.path.exists(expected)

    loaded_journal.generate_preview(
        experiment_name="test-case-1",
        experiment_folder=temp_dir)
    assert os.path.exists(expected)
