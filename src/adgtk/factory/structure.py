"""structure.py

Goals
=====
Provides the structure that is factory specific.

Design
======
The focus on this structure is to reduce the amount of code needed to
work with the factory. For example the FactoryOrder provides an easy to
use structure for creating objects while the SupportsFactory reduces the
amount of code needed in custom classes, registration, etc.

Structures
==========
 - User-facing models: validated, serialized via BaseModel
 - Internal helpers: lightweight dataclasses, not validated


Testing
=====
N/A

Notes
=====
1. This takes the lessons learned from earlier adgtk versions to reduce
   the amount of code the user needs to write as well as simplifying the
   overall code maintenance for this project.
"""
from abc import ABC
import secrets
from typing import (
    Callable,
    ClassVar,
    Literal,
    Optional,
    Union)
from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

SupportedCaptureTypes = Literal[
    "bool",
    "float",
    "int",
    "str",
    "ml-string",
    "list[float]",
    "list[int]",
    "list[bool]",
    "list[str]",
    "list[expand]",
    "expand"
    ]

SupportedChoiceTypes = Union[int, float, str]

# ----------------------------------------------------------------------
# Structures - User-facing models (external data)
# ----------------------------------------------------------------------

class BlueprintQuestion(BaseModel):
    """Used by an experiment builder (interview, etc).

    This should be part of a list of questions. Each BlueprintQuestion
    represents a single attribute that needs to be captured for
    experiment definition creation. 

    attribute: The associated attribute in __init__
    question: The question to ask the user
    entry_type: Helps with formatting the experience
    helper: A secondary string to aid the interview
    group: The group to expand. this is triggered if type is expand or
           list[expand]
    choices: restricts to a list of choices. ex: string must be 'cat' or
             'dog' or 3, 5, or 7
    min_value: if entry_type is numeric restricts the minimum value
    max_value: if entry_type is numeric restricts the maximum value
    """
    attribute:str
    question: str
    entry_type:SupportedCaptureTypes
    helper: Optional[str] = ""
    group: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: list[SupportedChoiceTypes] = Field(default_factory=list)    
    default_value: Optional[SupportedChoiceTypes] = None


class FactoryOrder(BaseModel):
    """An experiment will define an 'order' for the factory. The ideal
    approach is to use the factory_id. But if this is not available then
    the order should have both a group and a name. This will then allow
    for loading dynamic components in the factory such as functions."""
    factory_id:str
    init_args: Optional[dict] = None


class FactoryEntry(BaseModel):
    """The entry within the component factory."""
    creator: Callable
    group: str
    tags: list[str] = Field(default_factory=list)
    summary: str
    factory_id:str = secrets.token_hex(4)
    interview_blueprint: list[BlueprintQuestion] = Field(default_factory=list)
    factory_can_init: bool = True

# ----------------------------------------------------------------------
# Structures - Internal helpers (non-validated)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Protocols / Abstract Classes
# ----------------------------------------------------------------------

class SupportsFactory(ABC):
    """The foundation for any class based item. By inheriting this class
    in your code you are reducing the amount of code you need to write
    to register your custom Class. Of course, you can register without
    using this but it increases the amount of attributes you need to set
    so this is more a convinience than a requirement.
    """
    factory_id: ClassVar[str]
    group: ClassVar[str]
    tags: ClassVar[list[str]]  = []
    interview_blueprint: ClassVar[list[BlueprintQuestion]] = []
    summary: ClassVar[str] = "No summary found"
    factory_can_init: ClassVar[bool] = True
