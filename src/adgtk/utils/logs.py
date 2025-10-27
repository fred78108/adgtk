"""Logging utility functions for configuring and managing loggers."""


import logging
import os
import sys
from typing import Literal, Optional
import warnings
from adgtk.common.defaults import LOG_DIR, SCENARIO_LOGGER_NAME
from .file import clear_folder

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
    print("WARNING: No active scenario found. Using the framework scenario logger")
    logger = create_logger(
        logfile="default.scenario.log",
        logger_name=SCENARIO_LOGGER_NAME,
        log_to_console=False,
        subdir="framework",
        log_propagate=False,
        mode="w"
    )
    logger.info("---- created due to get_scenario_logger w/out a scenario ----")
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
            raise ValueError("Experiment name is required when subdir is 'runs'")
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
                isinstance(h, logging.StreamHandler) for h in logger.handlers):
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

role_types = Literal["human", "ai", "system", "tool", "error", "default"]

class RoleColorFormatter(logging.Formatter):
    """Formats based on role. Sets the color."""
    ROLE_COLORS = {
        'human': '\033[94m',    # Blue
        'ai': '\033[92m',       # Green
        'system': '\033[95m',   # Magenta
        'tool': '\033[96m',     # Cyan
        'error': '\033[91m',    # Red
        'default': '\033[0m',   # Reset
    }

    def format(self, record):
        role = getattr(record, 'role', 'default')
        color = self.ROLE_COLORS.get(role, self.ROLE_COLORS['default'])
        line = "-" * 30
        bold_role = f"\033[1m{role.upper()}\033[0m"        

        # Split the message into lines
        message_lines = str(record.msg).splitlines()
        if message_lines:
            # Format the first line with the role and color
            message_lines[0] = f"{line} {color}{bold_role} {line}\n{message_lines[0]}\033[0m"
        # Join the lines back together for display
        formatted_message = "\n".join(message_lines)

        # Use the formatted message for output, without modifying record.msg
        return formatted_message



def clear_llm_logs(experiment_name:str) -> None:
    """Clears the LLM dedicated log folder for an experiment

    Args:
        experiment_name (str): The experiment to clear
    """
    section_dir = os.path.join(LOG_DIR, "runs")
    full_log_dir = os.path.join(section_dir, experiment_name)
    llm_dir = os.path.join(full_log_dir, "llm")
    try:
        clear_folder(llm_dir)
    except FileNotFoundError:
        pass

def clear_agent_logs(experiment_name:str) -> None:
    """Clears the agent dedicated log folder for an experiment

    Args:
        experiment_name (str): The experiment to clear
    """
    section_dir = os.path.join(LOG_DIR, "runs")
    full_log_dir = os.path.join(section_dir, experiment_name)
    agent_dir = os.path.join(full_log_dir, "agent")
    try:
        clear_folder(agent_dir)
    except FileNotFoundError:
        pass


def create_llm_logger(
    logfile: str,
    logger_name: str,
    experiment_name: str,    
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_propagate: bool = False,
    mode: Literal["a", "w"] = "a"
) -> logging.Logger:
    """
    Configure and return a logger with role-based color formatting
    that writes to a specified log file and optionally logs to the console.

    Args:
        logfile (str): Name of the log file to create or append to.
        logger_name (str): Name of the logger instance.
        log_level (int, optional): Logging level (e.g., logging.INFO,
            logging.DEBUG). Defaults to logging.INFO.
        log_to_console (bool, optional): Whether to also log messages
            to the console (stdout). Defaults to True.
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
        logging.Logger: Configured logger instance with role-based color formatting.
    """
    section_dir = os.path.join(LOG_DIR, "runs")
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(section_dir, exist_ok=True)
    
    full_log_dir = os.path.join(section_dir, experiment_name)
    os.makedirs(full_log_dir, exist_ok=True)
    llm_dir = os.path.join(full_log_dir, "llm")
    os.makedirs(llm_dir, exist_ok=True)
    log_path = os.path.join(llm_dir, logfile)
    logger = logging.getLogger(logger_name)

    # Remove all existing handlers for this logger
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

    return logger