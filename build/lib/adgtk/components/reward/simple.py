"""Simple reward functions"""

import random
from adgtk.components.base import State, StateType, Action, ActionType
from adgtk.common import (
    FactoryBlueprint,
    ArgumentType,
    ComponentDef,
    ArgumentSetting)
from adgtk.components import State, Action
from adgtk.factory import ComponentFeatures


class RandomReward:
    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="random",
        arguments={})

    features = ComponentFeatures(
        object_factory=False, experiment_journal=False)

    def calculate(self, last_state: State, last_action: Action) -> float:
        """A not very useful reward function other than for testing.

        :param state: The state the action is for
        :type state: State
        :param action: The action taken by the agent
        :type action: Action
        :return: the calculated reward. random between 0 and 1
        :rtype: float
        """

        return random.random()


class PointFiveReward:
    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="point-five",
        arguments={})

    features = ComponentFeatures(
        object_factory=False, experiment_journal=False)

    def calculate(self, last_state: State, last_action: Action) -> float:
        """A not very useful reward function other than for testing.

        :param state: The state the action is for
        :type state: State
        :param action: The action taken by the agent
        :type action: Action
        :return: the calculated reward. Always .5
        :rtype: float
        """
        return .5
