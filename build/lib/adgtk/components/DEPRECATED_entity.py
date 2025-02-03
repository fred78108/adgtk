"""Included Measurement scenarios

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0

Defects:

1.0
"""


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: this should not be part of the initial package!! move to project
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

from dataclasses import dataclass


@dataclass
class DEPRICATED_Entity:
    """A core object"""
    data: dict
    string_rep: str
    schema: str = "entity"


@dataclass
class DEPRECATED_EntityPairState:
    """A core object pair"""
    left: DEPRICATED_Entity
    right: DEPRICATED_Entity
    label: int
    schema: str = "entity-pair"
