"""Utilities for handling settings.
"""


import os
from typing import Union
from types import SimpleNamespace
import toml
import yaml

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
SETTINGS_FILE = "project.toml"
ALT_SETTINGS_FILE = "project.yaml"

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------    


def load_settings(file_override: Union[str, None] = None) -> SimpleNamespace:
    """Loads the settings file. Note, giving the user the option to use
    either YAML or TOML.

    Args:
        file_override (Union[str, None], optional): override check for
            settings.[toml|yaml]. Defaults to None.

    Raises:
        FileNotFoundError: File is not found

    Returns:
        SimpleNamespace: settings
    """

    # Note: 
    # Not using configparser due to the desire to support lists. This is
    # needed for allowing the user to list their modules in the settings
    # and have them loaded dynamically.

    
    # Safety checks and set filename to load
    if file_override is not None:
        filename = file_override
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Unable to find {filename}")
        else:
            if filename.endswith(".toml"):
                with open(filename, "r", encoding="utf-8") as infile:
                    values = toml.load(infile)
            elif filename.endswith(".yaml"):
                with open(filename, "r", encoding="utf-8") as infile:
                    values = yaml.safe_load(infile)
            else:
                raise ValueError(
                    "Unsupported or missing file: %s", filename)
    else:
        if os.path.exists(os.path.join(".", SETTINGS_FILE)):
            filename = SETTINGS_FILE
            with open(filename, "r", encoding="utf-8") as infile:
                values = toml.load(infile)
        elif os.path.exists(os.path.join(".", ALT_SETTINGS_FILE)):
            filename = ALT_SETTINGS_FILE  
            with open(filename, "r", encoding="utf-8") as infile:
                values = yaml.safe_load(infile)
        else:
            raise FileNotFoundError("Unable to find settings file")
    
    return SimpleNamespace(**values)
