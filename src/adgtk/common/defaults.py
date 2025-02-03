"""Provides a common place for default values. Helps to avoid circular
importing."""
from typing import Literal

# Used for creating the project.toml/yaml file
# is also used when failing to load settings.

DEFAULT_FILE_FORMAT: Literal["yaml", "toml"] = "yaml"

# not changable by the user
DEFAULT_JOURNAL_REPORTS_DIR = "reports"

# changeable by the user
DEFAULT_EXP_DEF_DIR = "experiment-def"
DEFAULT_DATA_DIR = "data"
DEFAULT_SETTINGS = {
    "experiment": {
        "data_dir": DEFAULT_DATA_DIR,
        "tensorboard_dir": "runs",
        "results_dir": "results",
        "definition_dir": DEFAULT_EXP_DEF_DIR
    },
    "user_modules": [
        'agent',
        'structure',
        'environment',        
        'generation',
        "instrumentation",
        "plugin",
        'processing',
        'scenario',
        'reward',
        'policy'],
    "default_file_format": DEFAULT_FILE_FORMAT,
    "blueprint_dir": "blueprints",
    "logging": {
        "log_dir": "logs",
        "level": "basic"
    },
    "server": {
        "port": 8000,
        "host": "0.0.0.0",
        "proto": "http"
    }
}
