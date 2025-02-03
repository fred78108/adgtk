"""Summary goes here.

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0

Defects:

1.0

Test
python -m unittest tests.
"""


import os
from typing import Union
from types import SimpleNamespace
import toml


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
SETTINGS_FILE = "settings.toml"
ALT_SETTINGS_FILE = "settings.yaml"

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


def load_settings(file_override: Union[str, None] = None) -> SimpleNamespace:
    """Loads the settings file

    Args:
        file_override (Union[str, None], optional): override check for
            settings.[toml|yaml]. Defaults to None.

    Raises:
        FileNotFoundError: _description_
        NotImplementedError: _description_
        FileNotFoundError: _description_

    Returns:
        SimpleNamespace: settings
    """

    # current_directory = os.getcwd()
    # print(f"Current Directory: {current_directory}")

    # Safety checks and set filename to load
    if file_override is not None:
        filename = file_override
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Unable to find {filename}")
    else:
        if os.path.exists(os.path.join(".", SETTINGS_FILE)):
            filename = SETTINGS_FILE
        elif os.path.exists(os.path.join(".", ALT_SETTINGS_FILE)):
            raise NotImplementedError("DEV needed")
        else:
            raise FileNotFoundError("Unable to find settings file")

    # Load file
    with open(filename, "r", encoding="utf-8") as infile:
        values = toml.load(infile)

    return SimpleNamespace(**values)
