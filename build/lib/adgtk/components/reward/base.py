"""Foundation for Reward functions"""


from typing import Protocol
from adgtk.common import FactoryBlueprint
from adgtk.components import State, Action
from adgtk.factory import ComponentFeatures


class RewardFunction(Protocol):
    blueprint: FactoryBlueprint
    features: ComponentFeatures

    def calculate(self, last_state: State, last_action: Action) -> float:
        """Calculate a reward

        :param state: The state to compare the reward against
        :type state: State
        :param action: The action taken by the Environment
        :type action: Action
        :return: The calculated reward
        :rtype: float
        """
