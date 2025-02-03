"""Logging functions
"""

import logging
import sys
import os
from adgtk import __version__ as adgtk_ver
from .settings import load_settings


# ----------------------------------------------------------------------
# Future move into settings file
# ----------------------------------------------------------------------
LOG_TO_FILE = True      # future set/override perhaps?


def start_logging(
    name: str,
    surpress_chatty: bool = True,
    preview: bool = False
) -> None:
    """Sets up and starts logging for an experiment

    :param name: The name of the experiment
    :type name: str
    :param surpress_chatty: removes chatty modules httpx and openai and
        sets their log level to logging.WARNING, defaults to True
    :type surpress_chatty: bool, optional
    :param preview: logs preview only, defaults to False
    :type preview: bool, optional
    """
    settings = load_settings()

    # Setup the log directory if it doesn't already exist
    os.makedirs(settings.logging["log_dir"], exist_ok=True)

    # Setup format
    if settings.logging["level"] == "basic":
        fmt_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        fmt_string = "%(asctime)s %(levelname)s"\
            " %(message)s [%(module)s %(funcName)s %(lineno)d]"
        
    # cleanup name
    name = name.lower()
    if name.endswith(".toml") or name.endswith(".yaml"):
        name = name[:-5]

    log_filename = name    
    if not log_filename.endswith(".log"):
        log_filename += ".log"

    log_file = os.path.join(settings.logging["log_dir"], log_filename)
    print(f"Setting the logfile to : {log_file}")

    # Setup the logger
    if LOG_TO_FILE:
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format=fmt_string)
    else:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format=fmt_string)

    # now surpress logging for "chatty" modules
    if surpress_chatty:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)

    if preview:
        logging.info(f"version {adgtk_ver}")
        logging.info("---------------------------------------------------")
        logging.info("----------- PREVIEW and REVIEW MODE ---------------")
        logging.info("---------------------------------------------------")
    else:
        # for when we want to log but don't expect any experiment data.
        logging.info(f"version {adgtk_ver}")
        logging.info("---------------------------------------------------")
        logging.info("------------------- NEW RUN -----------------------")
        logging.info("---------------------------------------------------")
