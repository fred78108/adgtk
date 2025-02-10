"""Policies that generate new content."""

from typing import cast
from adgtk.components.policy.base import Policy
from adgtk.components.base import State, Action, ActionType
from adgtk.common import (
    FactoryBlueprint,
    ComponentDef,
    ArgumentSetting,
    ArgumentType)
from adgtk.factory import ObjectFactory
from adgtk.generation import PromptGenerator, Generator


class FixedGenerationPolicy(Policy):
    """Policy for generating content but is incapable of updating."""

    description = "DUPLICATE? TODO to validate/retire?"
    blueprint: FactoryBlueprint = FactoryBlueprint(
        group_label='policy',
        type_label="generation",
        arguments={
            "generator": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                help_str="The generator to use.",
                group_label="generator"),
            "prompt": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                help_str="The prompt Generator to use.",
                group_label="prompt"),
        })

    def __init__(
        self,
        factory: ObjectFactory,
        generator: ComponentDef,
        prompt: ComponentDef
    ):
        self.generator = factory.create(generator)
        self.prompt = factory.create(prompt)

        # and cast
        self.generator = cast(Generator, self.generator)
        self.prompt = cast(PromptGenerator, self.prompt)

    def reset(self) -> None:
        """Resets internal state during training."""
        self.generator.reset()
        self.prompt.reset()

    def invoke(self, state: State) -> Action:
        """Invoke the policy to include tracking for training. The
        policy can chose to explore or exploit in response to the ask.

        Args:
            state (State): The state

        Returns:
            Action: The action to take
        """
        prompt = self.prompt.create_prompt(state)
        result = self.generator.generate(prompt)

        return Action(
            value=result,
            action_type=ActionType.STRING)

    def sample(self, state: State) -> Action:
        """Invokes the policy but does not update for training. It only
        seeks to exploit.

        Args:
            state (str): The state

        Returns:
            str: The action to take
        """
        prompt = self.prompt.create_prompt(state)
        result = self.generator.generate(prompt)

        return Action(
            value=result,
            type=ActionType.STRING)

    def update(self, reward: float) -> None:
        """Update the policy based on the reward.

        Args:
            reward (float): The reward
        """
        # no action taken on update
        pass
