"""Simple built-in Agent to use directly or inherit from.
removed: # mypy: ignore-errors
"""
import logging
from typing import Union, cast
from sklearn.metrics import f1_score
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.factory import ComponentFeatures, ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.components import State, Action, StateType
from adgtk.components.policy import Policy
from adgtk.components.environment import Environment


class BasicAgent:
    """A basic Agent that tracks F1-score. Useful for limited action
    space scenarios such as classificiation."""

    description = "Agent is focused on prediction, captures F1-score, etc."

    blueprint: FactoryBlueprint = {
        "group_label": "agent",
        "type_label": "basic",
        "arguments": {
            "policy": ArgumentSetting(
                help_str="The policy to use",
                default_value="policy",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }
    features = ComponentFeatures(
        object_factory=True, experiment_journal=True)

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        policy: ComponentDef
    ) -> None:
        self.factory = factory
        self.journal = journal
        # and create the policy from the Factory
        self.policy = self.factory.create(policy)
        self.policy = cast(Policy, self.policy)

    def engage(self, state: State) -> Action:
        """Engages the Policy for a single state. The goal is to exploit
        the policy not explore/train. This method will set the policy
        into exploit mode versus training mode.

        :param state: The state to invoke the Policy with
        :type state: State
        :return: The action based on the Policy
        :rtype: Action
        """
        self.policy.training = False
        return self.policy.invoke(state)

    def train(
        self,
        train_environment: Environment,
        val_environment: Union[Environment, None] = None,
        test_environment: Union[Environment, None] = None,
        epochs: int = 1
    ) -> None:
        """Explores an environment and trains the provided policy to
        learn how to predict match versus non-match for the entities.

        :param train_environment: The env for training
        :type train_environment: Environment
        :param val_environment: validation env
        :type val_environment: Environment, optional
        :param test_environment: The test env
        :type test_environment: Environment, optional
        :param epochs:  outer epochs, for the agent not the policy
        :type epochs: int, optional
        """

        self.policy.training = True

        for epoch in range(epochs):
            # For F1-score, logging, etc
            expected = []
            predictions = []
            state, rollover = train_environment.reset()
            while not rollover:
                expected.append(state.label)
                # invoke Agent
                action = self.policy.invoke(state)
                predictions.append(action.value)

            # now log
            logging.info(f"Completed epoch {epoch}")

        # TODO:
        # 1. log F1 scores, etc
        # 2. complete val, and test loop(s)
