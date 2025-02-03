"""Basic wrapper objects. Helps ease interopability across code base.

TODO: This is currently a WIP. once done testing and completion of MVP
its important to update the comments, cod here!
"""

from typing import Any, TypedDict
from enum import Enum, auto
from dataclasses import dataclass


class StateType(Enum):
    """MVP. need to evaluate which onese to add/remove"""
    TENSOR = auto()
    ARRAY = auto()
    STRING = auto()
    PRESENTABLE_RECORD = auto()
    PRESENTABLE_GROUP = auto()
    DICT = auto()
    OTHER = auto()


class ActionType(Enum):
    """MVP. need to evaluate which onese to add/remove"""
    INT = auto()
    STRING = auto()
    TENSOR = auto()
    ARRAY = auto()
    OTHER = auto()


@dataclass
class State:
    type: StateType
    value: Any
    label: Any = None


@dataclass
class Action:
    value: Any
    type: ActionType
