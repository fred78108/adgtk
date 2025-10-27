"""structure.py supports the tracking specific data structures


Structures
==========
 - User-facing models: validated, serialized via BaseModel
 - Internal helpers: lightweight dataclasses, not validated

"""

from dataclasses import asdict, dataclass
import datetime
from typing import ClassVar, Optional
import uuid
from pydantic import BaseModel

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

EXP_RUN_DIR = "runs"
EXP_OTHER_DIR = "other"
EXP_METRICS_FOLDER = "metrics"
EXP_MODEL_DIR = "models"
EXP_IMG_FOLDER = "images"
EXP_DATASET_FOLDER = "datasets"
EXP_RESULTS_FOLDER = "results"
EXP_MODEL_TRAIN_LOG = "model_train_runs"
TRACKING_FOLDER = ".tracking"

RUN_FOLDER_VERSION = 1.1                # Ease of migration

# ----------------------------------------------------------------------
# Structures - User-facing models (external data)
# ----------------------------------------------------------------------

class CommentModel(BaseModel):
    """Used within the journal for recording comments"""
    comment:str
    component:str = "global"
    timestamp: Optional[str] = None


class ExperimentEntryModel(BaseModel):
    """Used to track experiments within a project."""    
    name:str
    description:str
    journal:str
    results_path:str
    id:Optional[str] = str(uuid.uuid4())
    timestamp: Optional[str] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PrefixModel(BaseModel):
    prefix: str
    major_counter: int = 0
    minor_counter: int = 0


# ----------------------------------------------------------------------
# Structures - Internal helpers (non-validated)
# ----------------------------------------------------------------------

@dataclass
class AvailableExperimentModel():
    name:str
    description: str

@dataclass
class ExperimentRunFolders():
    """Provides a fully qualified path for ease of use for listing the
    different subfolders for an experiment."""
    version: ClassVar[float] = RUN_FOLDER_VERSION
    log_dir:str
    datasets:str
    metrics:str
    images:str
    other: str
    conclusion:str
    root_dir: str
    experiment_name: str
    common: str
    model_dir: str
    train_log_dir:str

    def to_dict(self) -> dict:
        return asdict(self)    
