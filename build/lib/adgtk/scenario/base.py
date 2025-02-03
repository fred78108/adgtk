"""Scenario base

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

from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from adgtk.factory import ComponentFeatures

SCENARIO_GROUP_LABEL = "scenario"


@dataclass
class ScenarioFeatures(ComponentFeatures):
    """The features for a Scenario"""
    performs_measurements: bool = False
    creates_data: bool = False


@runtime_checkable
class Scenario(Protocol):
    """The Scenario Protocol"""
    features: ScenarioFeatures

    def execute(self, name: str) -> None:
        """Execute actions based on Agent type (interacting with evn,
        expanding data, etc).

        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
