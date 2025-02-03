# mypy: ignore-errors
"""Summary goes here.

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0

Defects:

1.0

Test
python -m unittest tests.
"""

from adgtk.common import FactoryBlueprint
from adgtk.components import Action, State, StateType


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


class RandomPolicy:
    """A Policy that uses Random to select action"""

    description = "Policy randomly selects an action from the action space."
    blueprint: FactoryBlueprint = {
        "group_label": "policy",
        "type_label": "random",
        "arguments": {}
    }

    def __init__(self):
        self.supports_env_type = [StateType.OTHER]

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

    def update(self, reward: float) -> None:
        """Updates a policy using the reward from the environment for
        the last action.

        Args:
            reward (float): The reward from the last action

        Raises:
            NotImplementedError: Ensures added by a child class
        """

    def refresh(self) -> None:
        """Refreshes the policy by creating training data based on the
        last epoch. This will be used when there is a model to train.
        If there is nothing to update "refresh" then this is a no-op.
        """
