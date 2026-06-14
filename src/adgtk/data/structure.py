"""data.py is focused on the internal data structures and functions that
support the society.
"""

from typing import Any, get_args, Literal, Optional, Protocol, Union
from pydantic import BaseModel, ConfigDict, Field
import datetime


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
TRASH_DIR = ".trash"
INTERNAL_DATA_DIR = ".registered_files"


# ----------------------------------------------------------------------
# Foundation
# ----------------------------------------------------------------------
OrientationTypes = Literal[
     "dict_contains_list",
     "dict",
     "list_contains_dict",
     "list_contains_string",
     "pandas",
     "other"]

# what structure will be found on load? helps inform how to load.
FileEncodingTypes = Literal[
    "csv",
    "hf-json",
    "json",
    "pickle",
    "pandas",
    "text",
]

FileActionTypes = Literal["copy", "move", "none"]

PurposeTypes = Literal[
    "test",
    "train",
    "validate",
    "generated",
    "measurement",
    "messages",
    "model",
    "other",
    "performance",
    "prompts"
]

SUPPORTED_ORIENTATION_TYPES = list(get_args(OrientationTypes))
SUPPORTED_FILE_ENCODING_TYPES = list(get_args(FileEncodingTypes))


# ----------------------------------------------------------------------
# Structure
# ----------------------------------------------------------------------

class ColumnDefinition(BaseModel):
    name: str
    type: Literal["float", "str", "dict", "int", "bool", "other"]
    description: str


class FileMetaData(BaseModel):
    """File specific. naming convention: file.csv has file.meta.json.
    This data structure is for the .meta.json."""
    description: str
    fields: list[ColumnDefinition]
    created_by: Optional[str] = None
    updated_date: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat())


class FileDefinition(BaseModel):
    """Defines a file and how to process it. More an internal structure."""
    model_config = ConfigDict(extra="ignore")

    file_id: str        # used for indexing multiple files. must be unique
    filename: str
    path: str
    encoding: FileEncodingTypes
    tags: Optional[Union[str, list[str]]] = None
    description: Optional[str] = None
    extended_metadata: Optional[dict[str, Any]] = None


class DataDefinition(BaseModel):
    """The combined structure"""
    shuffle_on_load: Optional[bool] = None
    key_rename_map: Optional[dict[str, str]] = None
    target_orientation: Optional[OrientationTypes] = None


class FileDataDefinition(DataDefinition):
    file_definition: FileDefinition


class InMemoryDataDefinition(DataDefinition):
    """Used for passing data in-memory"""
    data: Optional[Union[dict, list]]


class FileManagerConfig(BaseModel):
    """Used to make things a bit easier to maintain for the file mgr cli
    """
    label: str
    inventory_filename: str
    folder: str = INTERNAL_DATA_DIR
    load_on_init: bool = True


# ----------------------------------------------------------------------
# Protocol
# ----------------------------------------------------------------------

class CanTrackFiles(Protocol):

    def list_files(
        self,
        tag: Optional[Union[str, list[str]]] = None
    ) -> list[FileDefinition]:
        ...

    def get_file_id(self, filename: str) -> str: ...

    def report(self, tag: Optional[Union[str, list]] = None) -> None: ...

    def register_file(
        self,
        source_file: str,
        encoding: FileEncodingTypes,
        tags: Optional[Union[str, list[str]]] = None,
        file_id: Optional[str] = None,
        description: Optional[str] = None,
        extended_metadata: Optional[dict] = None,
    ) -> str:
        ...

    def retire_file(self, file_id: str) -> None: ...

    def get_file_definition(self, file_id: str) -> FileDefinition: ...
