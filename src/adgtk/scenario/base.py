"""The Scenario is the overall wrapper for building an experiment. A
Scenario is also managed by the ScenarioManager, which is responsible
for managing the lifecycle of the Scenario. A proper Scenario should
have at a minimum a method called execute, which will be called by the
ScenarioManager to run the experiment.
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
