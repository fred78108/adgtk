"""Sample Scenario.

This scenario shows the minimum config and code required to create a
scenario along with a very simple experiment.
"""

from adgtk.common import FactoryBlueprint
from adgtk.factory.component import ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.scenario import SCENARIO_GROUP_LABEL


class SampleScenario:

    description = "Sample Scenario"    
    blueprint: FactoryBlueprint = {
        "introduction":"""The Sample Scenario shows the absolute minimum needed for a scenario. It does nothing but print a message.
""",
        "group_label": SCENARIO_GROUP_LABEL,
        "type_label": "sample",
        "arguments": {}
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
    ) -> None:
        pass

    def execute(self, name: str) -> None:
        """Loads a model and performs a series of measurements on it.

        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
        print("execute - the sample scenario has executed.")
