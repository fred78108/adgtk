# mypy: ignore-errors
"""Scenario base
"""


from typing import List, Protocol, runtime_checkable
from adgtk.common import FactoryBlueprint
from adgtk.components import Action, State, StateType


@runtime_checkable
class Policy(Protocol):
    """The Policy base"""
    blueprint: FactoryBlueprint
    training: bool
    supports_env_type: List[StateType]

    def reset(self) -> None:
        """Resets internal state during training."""

    def invoke(self, state: State) -> Action:
        """Invoke the policy to include tracking for training. The
        policy can chose to explore or exploit in response to the ask.

        Args:
            state (State): The state

        Returns:
            Action: The action to take
        """

    def sample(self, state: State) -> Action:
        """Invokes the policy but does not update for training. It only
        seeks to exploit.

        Args:
            state (State): The state

        Returns:
            Action: The action to take
        """
        pass

    def update(self, reward: float) -> None:
        """Updates a policy using the reward from the environment for
        the last action.

        :param reward: The reward from the last action
        :type reward: float
        """

    def refresh(self) -> None:
        """Refreshes the policy by creating training data based on the
        last epoch. This will be used when there is a model to train.
        If there is nothing to update "refresh" then this is a no-op.
        """


@runtime_checkable
class UsesPrompts(Protocol):
    """For logging of the last prompt we need to confirm its implemented"""

    last_prompt: str
