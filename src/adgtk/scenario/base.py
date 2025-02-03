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

SCENARIO_GROUP_LABEL = "scenario"


@runtime_checkable
class Scenario(Protocol):
    """The Scenario Protocol"""

    def execute(self, name: str) -> None:
        """Execute the scenario.

        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
