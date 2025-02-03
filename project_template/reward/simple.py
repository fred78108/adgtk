"""Simple reward functions"""

import random
from adgtk.components.base import State, StateType, Action, ActionType
from adgtk.common import FactoryBlueprint
from adgtk.components import State, Action


class RandomReward:
    description = "A reward that returns 0-1 randomly"
    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="random",
        arguments={})

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
    description = "A reward that always returns 0.5."
    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="point-five",
        arguments={})

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
