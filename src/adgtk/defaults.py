"""Defaults.

Should all be dict objects that can be used to generate configuration
files in the requested format YAML, TOML. etc.
"""
project_defaults = {
    "default_file_format": "toml",
    "blueprint_dir": "blueprints",
    "experiment": {
        "data_dir": "data",
        "results_dir": "results",
        "tensorboard_dir": "runs",
        "experiment_definition_dir": "experiment_definitions"
    },
    "logging": {
        "log_dir": "logs",
        "level": "basic"
    }
}
