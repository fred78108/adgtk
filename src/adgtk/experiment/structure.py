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
from adgtk.experiment.result import RunResult
from adgtk.tracking.structure import ExperimentRunFolders

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

EXPERIMENT_LABEL = "experiment"
SCENARIO_LABEL = "scenario"

AttributeValueType = Union[
    "AttributeEntry", dict, list, str, bool, float, int
]


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
            list["AttributeEntry"],
            list[str],
            list[int],
            list[float],
            list[bool],
            list[dict],
        ]
    ] = None


AttributeEntry.model_rebuild()  # str to Type AttributeEntry for Union


class ExperimentDefinition(AttributeEntry):
    """The root of any experiment definition. The experiment name is derived
    from the blueprint filename (stem without .yaml extension)."""
    description: str


class BatchDefinition(BaseModel):
    name: str
    experiments: list[str]


# ----------------------------------------------------------------------
# Protocols / Abstract Classes
# ----------------------------------------------------------------------

@runtime_checkable
class ScenarioProtocol(Protocol):
    """Defines a scenario"""
    def run_scenario(
        self,
        result_folders: ExperimentRunFolders
    ) -> RunResult:
        """Runs the scenario as defined"""
        ...


# ----------------------------------------------------------------------
# Typing
# ----------------------------------------------------------------------

BuildComponentResult = Union[Callable, float, bool, str, int, list[Any], None]
AttributeConfigType = Union[AttributeEntry, dict]

ATTRIBUTE_CONFIG_TYPES = tuple(get_args(AttributeConfigType))
