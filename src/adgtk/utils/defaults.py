"""Provides a common place for default values. Helps to avoid circular
importing."""

import os

# Experiment Folders
EXP_DEF_DIR = "blueprints"
BATCH_DEF_DIR = "batch"
SHARED_MODEL_DIR = "models"
EXP_RUN_DIR = "runs"
EXP_OTHER_DIR = "other"
EXP_METRICS_FOLDER = "metrics"
EXP_MODEL_DIR = "models"
EXP_IMG_FOLDER = "images"
EXP_DATASET_FOLDER = "datasets"
EXP_RESULTS_FOLDER = "results"
EXP_MODEL_TRAIN_LOG = "model_train_runs"
TRACKING_FOLDER = ".tracking"
RUN_FOLDER_VERSION = 1.2                # Ease of migration

# Study Folders
STUDY_DEF_DIR = "studies"
STUDY_RESULTS_DIR = "study-results"

# Logging
LOG_DIR = "logs"
SCENARIO_LOGGER_NAME = "SCENARIO"
PROJECT_LOGGER_NAME = "adgtk.project.log"
BATCH_LOGGER_NAME = "BATCH"
LOG_ROTATE_MAX_BYTES = 5_000_000
LOG_ROTATE_BACKUP_COUNT = 3


# Filenames
TASKS_DIR = os.path.join(TRACKING_FOLDER, "tasks")
SETTINGS_FILENAME = "settings.yaml"
