"""Fixed environments
"""

from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.components import Action, State, StateType, ActionType
from adgtk.factory import ObjectFactory
from adgtk.journals import ExperimentJournal
from reward import RewardFunction


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py


class FixedDictEnvironment:
    """An environment that has a single state. Its purpose is to serve
    up this state which is a dict and provide access to the reward
    """

    uses_state_types: list[StateType] = [StateType.PRESENTABLE_RECORD]
    supports_action_types: list[ActionType] = [ActionType.STRING]
    description = "Serves up a single dictionary as a state."

    blueprint: FactoryBlueprint = {
        "group_label": "environment",
        "type_label": "fixed",
        "arguments": {
            "fixed_state": ArgumentSetting(
                argument_type=ArgumentType.DICT,
                default_value={},
                help_str="The dictionary to serve as a fixed state"
            ),
            "state_count": ArgumentSetting(
                argument_type=ArgumentType.INT,
                default_value=10,
                help_str="The number of times to serve before rolling over"
            ),
            "reward_function": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                group_label="reward",
                help_str="The reward function to use")
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        fixed_state: dict,
        state_count: int,
        reward_function: ComponentDef
    ):
        self.factory = factory
        self.journal = journal
        self.reward_func = self.factory.create(reward_function)
        self.reward_func = cast(RewardFunction, self.reward_func)
        self.single_state = State(
            state_type=StateType.DICT,
            value=fixed_state,
            label=1)
        # state management
        self.state_count = state_count
        self.state_idx = 0

    def action_space(self) -> list[Action]:
        """Gets a list of acceptable actions

        Returns:
            list[Action]: The acceptable actions
        """
        return []

    def reset(self, value: int = 0) -> tuple[State, bool]:
        """Resets the state

        :param value: The state index., defaults to 0
        :type value: int, optional
        :return: The new state, and rolling over?
        :rtype: tuple[State, bool]
        """
        self.state_idx = value
        return self.single_state, False

    def step(self, action: Action) -> tuple[State, float, bool]:
        """Take an action on the Environment

            Args:
                value (int, optional): _description_. Defaults to 0.

            Returns:
                tuple[State, bool]: the new state and rollover?
            """
        rollover = False
        reward = self.reward_func.calculate(
            last_state=self.single_state,
            last_action=action)

        self.state_idx += 1
        if self.state_idx >= self.state_count:
            self.state_idx = 0
            rollover = True

        return self.single_state, reward, rollover
