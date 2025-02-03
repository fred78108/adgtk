# mypy: ignore-errors
"""Environment base
"""
# pylint: disable=unused-argument
from typing import Protocol, runtime_checkable
from adgtk.components.base import StateType, Action, ActionType, State


@runtime_checkable
class Environment(Protocol):
    """The Environment Procotol"""

    supports_state: list[StateType]
    supports_action: list[ActionType]

    def action_space(self) -> list[Action]:
        """Gets a list of acceptable actions

        Returns:
            list[Action]: The acceptable actions
        """

    def reset(self, value: int = 0) -> tuple[State, bool]:
        """Resets the state

        :param value: The state index., defaults to 0
        :type value: int, optional
        :return: The new state, and rolling over?
        :rtype: tuple[State, bool]
        """

    def step(self, action: Action) -> tuple[State, float, bool]:
        """Take action on the environment

        :param action: The action to take
        :type action: Action
        :return: State, reward, and rollover
        :rtype: tuple[State, float, bool]
        """
