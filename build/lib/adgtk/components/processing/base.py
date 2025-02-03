# mypy: ignore-errors
"""Processing. Think of Processing Classes as an Agent without a policy.
They will load and transform data based on their needs. For example,
taking a CSV file and loading into a datastore then saving the store to
disk. Another could be taking from one store to another.

"""
from typing import Any, Union, Protocol, runtime_checkable
from dataclasses import dataclass
from adgtk.data import RecordStore
from adgtk.common import FactoryBlueprint
from adgtk.factory import (
    ComponentFeatures,
    FactoryImplementable)

# ---------------------------------------------------------------------
#
# ---------------------------------------------------------------------


@dataclass
class ProcessingFeatures(ComponentFeatures):
    """Processing Features"""
    file_processing: bool = False


class RecordFactoryEntry:
    """Provides a base for any compnent the factory will build
    """
    # class
    blueprint: FactoryBlueprint
    features: ProcessingFeatures

@ runtime_checkable
class Processor(Protocol):
    """Supports a type of transformation for example loading a csv into
    a data store."""

    datastore: Union[RecordStore, None]

    def process(self) -> Any:
        """Executes a process

        :return: Varies by class. May or may not return an object.
        :rtype: Any
        """
