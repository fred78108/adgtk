"""Logging utility functions for configuring and managing loggers."""


import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, Optional
import warnings

from adgtk.utils.defaults import (
    LOG_DIR,
    LOG_ROTATE_BACKUP_COUNT,
    LOG_ROTATE_MAX_BYTES,
    PROJECT_LOGGER_NAME,
    SCENARIO_LOGGER_NAME
)

if TYPE_CHECKING:
    from adgtk.tracking.structure import ExperimentRunFolders


def is_project_context() -> bool:
    """Returns True if the CWD contains bootstrap.py, the project marker."""
    return os.path.isfile("bootstrap.py")


def get_project_logger() -> logging.Logger:
    """Retrieves the project logger. If not already created, it creates the
    project logger then returns it.

    Returns:
        logging.Logger: The logger instance for the project.
    """
    if not is_project_context():
        logger = logging.getLogger(PROJECT_LOGGER_NAME)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger

    if PROJECT_LOGGER_NAME in logging.Logger.manager.loggerDict:
        return logging.getLogger(PROJECT_LOGGER_NAME)

    return create_logger(
        PROJECT_LOGGER_NAME,
        logger_name=__name__,
        subdir="framework"
    )


def get_scenario_logger() -> logging.Logger:
    """
    Retrieve the logger for the current scenario.

    This utility function ensures that the scenario logger is easily
    accessible and helps maintain clarity in experimentation code.

    If no active scenario is running, it creates a logger using the
    framework directory.

    Returns:
        logging.Logger: The logger instance for the current scenario.
    """
    if SCENARIO_LOGGER_NAME in logging.Logger.manager.loggerDict:
        return logging.getLogger(SCENARIO_LOGGER_NAME)

    # not created. using default scenario logger
    msg = ("WARNING: No active scenario found. Using the "
           "framework scenario logger.")
    print(msg)
    logger = create_logger(
        logfile="default.scenario.log",
        logger_name=SCENARIO_LOGGER_NAME,
        log_to_console=False,
        subdir="framework",
        log_propagate=False,
        mode="w"
    )
    logger.info(
        "---- created due to get_scenario_logger w/out a scenario ----")
    return logger


def create_logger(
    logfile: str,
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = False,
    subdir: Literal["framework", "runs", "common", "agent"] = "framework",
    experiment_name: Optional[str] = None,
    log_propagate: bool = False,
    mode: Literal["a", "w"] = "a"
) -> logging.Logger:
    """
    Configure and return a logger that writes to a specified log file
    and optionally logs to the console.

    This function removes any existing file handlers for the logger,
    adds a new file handler with the specified log level and format,
    and optionally adds a console handler. It also ensures that the
    necessary directories for logging are created.

    Args:
        logfile (str): Name of the log file to create or append to.
        logger_name (str): Name of the logger instance.
        log_level (int, optional): Logging level (e.g., logging.INFO,
            logging.DEBUG). Defaults to logging.INFO.
        log_to_console (bool, optional): Whether to also log messages
            to the console (stdout). Defaults to False.
        subdir (Literal["framework", "runs", "common"], optional):
            Subdirectory (under 'logs/') to store the log file.
            Defaults to "framework".
        experiment_name (Optional[str], optional): Name of the experiment
            (required if subdir is "runs"). Defaults to None.
        log_propagate (bool, optional): Whether the logger should propagate
            messages to ancestor loggers. Defaults to False.
        mode (Literal["a", "w"], optional): File mode for the log file
            ("a" for append, "w" for write). Defaults to "a".

    Returns:
        logging.Logger: Configured logger instance.

    Raises:
        ValueError: If `experiment_name` is not provided when `subdir`
            is set to "runs".
    """
    if subdir == "agent":
        # special subdir, its runs/exp/agent
        section_dir = os.path.join(LOG_DIR, "runs")
    else:
        section_dir = os.path.join(LOG_DIR, subdir)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(section_dir, exist_ok=True)

    log_path = "default"
    if subdir in ["runs", "agent"]:
        if experiment_name is None:
            raise ValueError(
                "Experiment name is required when subdir is 'runs'")
        full_log_dir = os.path.join(section_dir, experiment_name)
        os.makedirs(full_log_dir, exist_ok=True)
        # modifier for agent
        if subdir == "agent":
            full_log_dir = os.path.join(full_log_dir, "agent")
            os.makedirs(full_log_dir, exist_ok=True)
        log_path = os.path.join(full_log_dir, logfile)
    elif subdir in ["framework", "common"]:
        log_path = os.path.join(section_dir, logfile)

    logger = logging.getLogger(logger_name)

    # Remove all existing handlers for this logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # Add the new handler
    file_handler: logging.Handler
    if subdir == "framework":
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, mode=mode,
            maxBytes=LOG_ROTATE_MAX_BYTES,
            backupCount=LOG_ROTATE_BACKUP_COUNT,
        )
    else:
        file_handler = logging.FileHandler(log_path, mode=mode)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.setLevel(log_level)
    logger.propagate = log_propagate

    if log_to_console:
        if not any(
                type(h) is logging.StreamHandler for h in logger.handlers):
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            stream_handler.setLevel(log_level)
            logger.addHandler(stream_handler)

    return logger


def set_logfile(
    logfile: str,
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = False,
    subdir: Literal["framework", "runs", "common", "agent"] = "framework",
    experiment_name: Optional[str] = None,
    log_propagate: bool = True,
    mode: Literal["a", "w"] = "a"
) -> logging.Logger:
    """
    [DEPRECATED] Configure and return a logger that writes to a specified
    log file and optionally logs to the console.

    This function is deprecated as of version 0.2. Use `create_logger`
    instead. It retains the same functionality as `create_logger`.

    Args:
        logfile (str): Name of the log file to create or append to.
        logger_name (str): Name of the logger instance.
        log_level (int, optional): Logging level (e.g., logging.INFO,
            logging.DEBUG). Defaults to logging.INFO.
        log_to_console (bool, optional): Whether to also log messages
            to the console (stdout). Defaults to False.
        subdir (Literal["framework", "runs", "common"], optional):
            Subdirectory (under 'logs/') to store the log file.
            Defaults to "framework".
        experiment_name (Optional[str], optional): Name of the experiment
            (required if subdir is "runs"). Defaults to None.
        log_propagate (bool, optional): Whether the logger should propagate
            messages to ancestor loggers. Defaults to True.
        mode (Literal["a", "w"], optional): File mode for the log file
            ("a" for append, "w" for write). Defaults to "a".

    Returns:
        logging.Logger: Configured logger instance.

    Raises:
        ValueError: If `experiment_name` is not provided when `subdir`
            is set to "runs".

    Warnings:
        DeprecationWarning: This function is deprecated. Use `create_logger`
        instead.
    """
    warnings.warn(
        "set_logfile is deprecated. Use create_logger instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_logger(
        logfile=logfile,
        logger_name=logger_name,
        log_level=log_level,
        log_to_console=log_to_console,
        subdir=subdir,
        experiment_name=experiment_name,
        log_propagate=log_propagate,
        mode=mode
    )


# ----------------------------------------------------------------------
# Color Logger
# ----------------------------------------------------------------------

role_types = Literal["user", "assistant", "system", "tool", "error", "default"]


class NdjsonFormatter(logging.Formatter):
    """Formats a log record as a single JSON line for NDJSON output."""

    def format(self, record: logging.LogRecord) -> str:
        role = getattr(record, 'role', 'default')
        ts = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).isoformat()
        return json.dumps({"role": role, "content": str(record.msg), "ts": ts})


class RoleColorFormatter(logging.Formatter):
    """Formats based on role. Sets the color."""
    ROLE_COLORS = {
        'user': '\033[94m',         # Blue
        'assistant': '\033[92m',    # Green
        'system': '\033[95m',       # Magenta
        'tool': '\033[96m',         # Cyan
        'error': '\033[91m',        # Red
        'default': '\033[0m',       # Reset
        # legacy aliases kept for backwards compatibility
        'human': '\033[94m',
        'ai': '\033[92m',
    }

    def format(self, record):
        """Formats the log record with role-based colors.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message.
        """
        role = getattr(record, 'role', 'default')
        color = self.ROLE_COLORS.get(role, self.ROLE_COLORS['default'])
        line = "-" * 30
        bold_role = f"\033[1m{role.upper()}\033[0m"

        # Split the message into lines
        message_lines = str(record.msg).splitlines()
        if message_lines:
            # Format the first line with the role and color
            message_lines[0] = (f"{line} {color}{bold_role} {line}"
                                f"\n{message_lines[0]}\033[0m")
        # Join the lines back together for display
        formatted_message = "\n".join(message_lines)

        # Use the formatted message for output, without modifying record.msg
        return formatted_message


def create_llm_logger(
    logfile: str,
    logger_name: str,
    folders: "ExperimentRunFolders",
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_propagate: bool = False,
    mode: Literal["a", "w"] = "a",
    json_logfile: Optional[str] = None,
) -> logging.Logger:
    """Configure and return a logger with role-based color formatting that
    writes into the run's llm/ subfolder.

    Log entries should set a ``role`` attribute on the LogRecord to get
    colour-coded output.  Accepted values: ``user``, ``assistant``,
    ``system``, ``tool``, ``error``.  Example::

        logger.info(content, extra={"role": "assistant"})

    A parallel NDJSON file is written alongside the text log for web
    rendering.  Each line: ``{"role": "...", "content": "...", "ts": "..."}``.
    The NDJSON filename defaults to ``logfile`` with ``.log`` replaced by
    ``.jsonl``.  Pass ``json_logfile=""`` to suppress NDJSON output.

    Args:
        logfile: Filename for the log (e.g. ``"chat.log"``).
        logger_name: Python logger identifier.
        folders: The current run's folder object — log is written to
            ``folders.llm_dir / logfile``.
        log_level: Logging level. Defaults to ``logging.INFO``.
        log_to_console: Mirror output to stdout. Defaults to ``True``.
        log_propagate: Propagate to ancestor loggers. Defaults to ``False``.
        mode: File open mode — ``"a"`` to append, ``"w"`` to overwrite.
        json_logfile: NDJSON sidecar filename. Defaults to ``logfile`` with
            ``.log`` replaced by ``.jsonl``.  Pass ``""`` to disable.

    Returns:
        Configured ``logging.Logger`` with role-based colour formatting.
    """
    os.makedirs(folders.llm_dir, exist_ok=True)
    log_path = os.path.join(folders.llm_dir, logfile)

    logger = logging.getLogger(logger_name)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    msg_formatter = RoleColorFormatter("%(message)s")
    file_handler = logging.FileHandler(log_path, mode=mode)
    file_handler.setFormatter(msg_formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.setLevel(log_level)
    logger.propagate = log_propagate

    if log_to_console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(msg_formatter)
        stream_handler.setLevel(log_level)
        logger.addHandler(stream_handler)

    # NDJSON sidecar for web rendering
    if json_logfile is None:
        stem = logfile[:-4] if logfile.endswith(".log") else logfile
        json_logfile = stem + ".jsonl"
    if json_logfile:
        json_path = os.path.join(folders.llm_dir, json_logfile)
        json_handler = logging.FileHandler(json_path, mode=mode)
        json_handler.setFormatter(NdjsonFormatter())
        json_handler.setLevel(log_level)
        logger.addHandler(json_handler)

    return logger
