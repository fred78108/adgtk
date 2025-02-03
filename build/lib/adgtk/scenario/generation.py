"""Generation Scenarios
"""

import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ComponentDef,
    ArgumentSetting,
    ArgumentType)
from adgtk.components import Agent, Environment
from adgtk.factory import ComponentFeatures, ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.scenario.base import ScenarioFeatures
# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py


class RLScenario:
    """Reinforcement Learning Scenario is a basic RL setup. It wires in
    both an Agent and an Environment.
    """

    description = "A simple RL scenario that engages an Agents train only."

    # TODO: create validation and test environments. for now jus train!
    blueprint: FactoryBlueprint = {
        "group_label": "scenario",
        "type_label": "reinforcement-learning",
        "arguments": {
            "agent": ArgumentSetting(
                help_str="The Agent configuration",
                default_value="agent",
                argument_type=ArgumentType.BLUEPRINT),
            "train_environment": ArgumentSetting(
                help_str="The Environment the agent will interact with",
                default_value="environment",
                argument_type=ArgumentType.BLUEPRINT),
            "epochs": ArgumentSetting(
                help_str="The number of epochs the agent will generate",
                default_value=1,
                argument_type=ArgumentType.INT)
        }
    }

    features = ScenarioFeatures(
        object_factory=True,
        experiment_journal=True,
        performs_measurements=True,
        creates_data=True)

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        agent: ComponentDef,
        train_environment: ComponentDef,
        epochs: int = 1
    ):
        self.factory = factory
        self.journal = journal
        self.epochs = epochs
        # and create the components
        self.agent = self.factory.create(agent)
        self.agent = cast(Agent, self.agent)
        self.train_env = self.factory.create(train_environment)
        self.train_env = cast(Environment, self.train_env)

    def execute(self, name: str) -> None:
        """Executes the Scenario. The scenario does the following.
        1. invokes the agent.train method
        2. that is all.... more to come?


        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
        logging.info("RLScenario starting execution")
        self.agent.train(
            experiment_name=name,
            train_environment=self.train_env,
            epochs=self.epochs)

        logging.info("RLScenario completed execution")
