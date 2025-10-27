"""Structure for builder

Structures
==========
 - User-facing models: validated, serialized via BaseModel
 - Internal helpers: lightweight dataclasses, not validated
"""

from typing import (
    Any,
    Callable,
    Optional,
    Protocol,
    Union,
    get_args,
    runtime_checkable)
from pydantic import BaseModel
from adgtk.data.structure import FileEntry
from adgtk.tracking.structure import ExperimentRunFolders

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

EXPERIMENT_LABEL = "experiment"
SCENARIO_LABEL = "scenario"

AttributeValueType = Union["AttributeEntry", dict, list, str, bool, float, int]


# ----------------------------------------------------------------------
# Structures - User-facing models (external data)
# ----------------------------------------------------------------------

class AttributeEntry(BaseModel):
    """Enables the runner to know how to load the data."""
    attribute: str    
    factory_id: Optional[str] = None
    factory_init: bool = False
    init_config: Optional[
        Union[
            bool,
            int,
            float,
            str,
            "AttributeEntry",
            dict,
            list["AttributeEntry"]]
            ] = None
    
AttributeEntry.model_rebuild()  # str to Type AttributeEntry for Union


class ExperimentDefinition(AttributeEntry):
    """The root of any experiment has two extra items the name and
    description. This allows for easy management and prediction of what
    to expect on load."""
    name:str
    description: str

class BatchDefinition(BaseModel):
    name:str
    experiments: list[str]

class ScenarioResults(BaseModel):
    """The results of an experiment"""
    files: list[FileEntry]


# ----------------------------------------------------------------------
# Structures - Internal helpers (non-validated)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Protocols / Abstract Classes
# ----------------------------------------------------------------------

@runtime_checkable
class ScenarioProtocol(Protocol):
    """Defines a scenario"""
    def run_scenario(
        self,
        result_folders:ExperimentRunFolders
    ) -> ScenarioResults: # type: ignore
        """Runs the scenario as defined"""


# ----------------------------------------------------------------------
# Typing
# ----------------------------------------------------------------------

BuildComponentResult = Union[Callable, float, bool, str, int, list[Any], None]
AttributeConfigType = Union[AttributeEntry, dict]

ATTRIBUTE_CONFIG_TYPES = tuple(get_args(AttributeConfigType))
