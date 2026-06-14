# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

"""
test_logs.py focuses on testing adgtk.utils.logs.create_logger and related functions.

Testing
=======
pytest -s test/utils/test_logs.py

note: Initial test cases generated via a model. Modified for clarity
      and robustness, with PEP-8 adherence and isolated temp dirs.
"""

import logging
import logging.handlers
import pytest
from adgtk.utils.logs import create_logger, is_project_context, get_project_logger
from adgtk.utils.defaults import PROJECT_LOGGER_NAME


@pytest.fixture(autouse=True)
def patch_log_dir(monkeypatch, tmp_path):
    """
    Fixture to patch LOG_DIR with a temporary directory for isolated testing.
    """
    monkeypatch.setattr("adgtk.utils.logs.LOG_DIR", str(tmp_path))
    yield


def test_creates_log_dir_and_file(tmp_path):
    """
    Test that create_logger creates the necessary directories and log file.
    """
    logfile = "mytest.log"
    logger_name = "test_logger"
    subdir = "framework"
    logger = create_logger(
        logfile=logfile,
        logger_name=logger_name,
        subdir=subdir,
        log_to_console=False
    )
    log_path = tmp_path / subdir / logfile
    logger.info("Test log message")
    logger.handlers[0].flush()

    assert log_path.exists(), "Log file was not created"
    content = log_path.read_text()
    assert "Test log message" in content


def test_removes_previous_file_handlers(tmp_path):
    """
    Test that create_logger removes previous file handlers for the same logger.
    """
    logger_name = "test_logger2"
    log1 = create_logger("file1.log", logger_name)
    log2 = create_logger("file2.log", logger_name)
    handlers = [
        h for h in logging.getLogger(logger_name).handlers
        if isinstance(h, logging.FileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].baseFilename.endswith("file2.log")

def test_log_propagation(tmp_path):
    """
    Test that the log_propagate parameter is respected.
    """
    logger = create_logger(
        logfile="prop.log",
        logger_name="prop_logger",
        log_propagate=False
    )
    assert logger.propagate is False


def test_log_level_respected(tmp_path):
    """
    Test that the log_level parameter is respected.
    """
    logger = create_logger(
        logfile="lev.log",
        logger_name="lev_logger",
        log_level=logging.ERROR
    )
    for handler in logger.handlers:
        assert handler.level == logging.ERROR


def test_experiment_name_required_for_runs_subdir(tmp_path):
    """
    Test that create_logger raises a ValueError if experiment_name is not provided
    when subdir is 'runs'.
    """
    with pytest.raises(ValueError, match="Experiment name is required when subdir is 'runs'"):
        create_logger(
            logfile="test.log",
            logger_name="test_logger",
            subdir="runs"
        )


def test_agent_subdir_creates_correct_path(tmp_path):
    """
    Test that the 'agent' subdir creates the correct directory structure.
    """
    experiment_name = "test_experiment"
    logger = create_logger(
        logfile="agent.log",
        logger_name="agent_logger",
        subdir="agent",
        experiment_name=experiment_name
    )
    log_path = tmp_path / "runs" / experiment_name / "agent" / "agent.log"
    logger.info("Agent log message")
    logger.handlers[0].flush()

    assert log_path.exists(), "Agent log file was not created"
    content = log_path.read_text()
    assert "Agent log message" in content


# ----------------------------------------------------------------------
# is_project_context / get_project_logger tests (4.2)
# ----------------------------------------------------------------------

@pytest.fixture(autouse=False)
def clean_project_logger():
    """Remove the project logger between tests so handler state is fresh."""
    def _evict():
        logger = logging.getLogger(PROJECT_LOGGER_NAME)
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()
        logging.Logger.manager.loggerDict.pop(PROJECT_LOGGER_NAME, None)

    _evict()
    yield
    _evict()


def test_is_project_context_true(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bootstrap.py").touch()
    assert is_project_context() is True


def test_is_project_context_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert is_project_context() is False


def test_get_project_logger_outside_project_no_disk_write(
        tmp_path, monkeypatch, clean_project_logger):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("adgtk.utils.logs.LOG_DIR", str(tmp_path / "logs"))
    logger = get_project_logger()
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)
    assert not (tmp_path / "logs").exists()


def test_get_project_logger_inside_project_creates_file(
        tmp_path, monkeypatch, clean_project_logger):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bootstrap.py").touch()
    monkeypatch.setattr("adgtk.utils.logs.LOG_DIR", str(tmp_path / "logs"))
    logger = get_project_logger()
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert (tmp_path / "logs" / "framework").is_dir()


# ----------------------------------------------------------------------
# 4.4 Log rotation tests
# ----------------------------------------------------------------------

def test_framework_subdir_uses_rotating_handler():
    logger = create_logger(
        logfile="rotate.log",
        logger_name="rotate_test_logger",
        subdir="framework",
    )
    rotating = [
        h for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(rotating) == 1
    assert rotating[0].maxBytes == 5_000_000
    assert rotating[0].backupCount == 3


def test_runs_subdir_uses_plain_file_handler():
    logger = create_logger(
        logfile="run.log",
        logger_name="runs_test_logger",
        subdir="runs",
        experiment_name="myexp",
    )
    handlers = logger.handlers
    assert not any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in handlers
    )
    assert any(type(h) is logging.FileHandler for h in handlers)
