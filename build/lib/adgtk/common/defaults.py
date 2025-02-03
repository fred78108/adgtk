"""Provides a common place for default values. Helps to avoid circular
importing."""
from adgtk.utils import DEFAULT_TERMINAL_CSS
from typing import Literal

# Used for creating the settings.toml/yaml file
# is also used when failing to load settings.

DEFAULT_FILE_FORMAT: Literal["yaml", "toml"] = "yaml"
DEFAULT_DATA_DIR = "data"

DEFAULT_SETTINGS = {
    "experiment": {
        "data_dir": DEFAULT_DATA_DIR,
        "tensorboard_dir": "runs",
        "results_dir": "results",
        "definition_dir": "experiment-def"
    },
    "user_modules": ['plugin'],
    "default_file_format": DEFAULT_FILE_FORMAT,
    "blueprint_dir": "blueprints",
    "logging": {
        "log_dir": "logs",
        "level": "basic"
    },
    "terminal": {
        "use_color": True,
        "css": DEFAULT_TERMINAL_CSS
    }
}
