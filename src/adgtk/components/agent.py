# mypy: ignore-errors
"""Agent base provides the foundational components for the module.
"""
# pylint: disable=unused-argument

from typing import Union, Protocol, runtime_checkable
from adgtk.common import FactoryBlueprint
from adgtk.components.base import State, Action
from adgtk.components.environment import Environment


@runtime_checkable
class Agent(Protocol):
    """The Agent Protocol"""
    blueprint: FactoryBlueprint

    def engage(self, state: State) -> Action:
        """Engages the Policy for a single state. The goal is to exploit
        the policy not explore/train. This method will set the policy
        into exploit mode versus training mode.

        :param state: The state to invoke the Policy with
        :type state: State
        :return: The action based on the Policy
        :rtype: Action
        """

    def train(
        self,
        experiment_name: str,
        train_environment: Environment,
        val_environment: Union[Environment, None] = None,
        test_environment: Union[Environment, None] = None,
        epochs: int = 1,
    ) -> None:
        """Explores an environment and trains the provided policy to
        learn how to predict match versus non-match for the entities.
        :param experiment_name: The name of the experiment.
        :type experiment_name: str
        :param train_environment: The env for training
        :type train_environment: Environment
        :param val_environment: validation env
        :type val_environment: Environment, optional
        :param test_environment: The test env
        :type test_environment: Environment, optional
        :param epochs:  outer epochs, for the agent not the policy
        :type epochs: int, optional
        """
