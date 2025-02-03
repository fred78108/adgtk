"""_summary_
"""

import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.components import Action, State, ActionType    
from adgtk.journals import ExperimentJournal
from adgtk.factory import ObjectFactory
from generation import Generator, PromptGenerator


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


class FixedGenerationPolicy:

    description = "Policy that doesn't learn. Generates text using the state"

    blueprint: FactoryBlueprint = {
        "group_label": "policy",
        "type_label": "fixed_gen",
        "arguments": {
            "generator": ArgumentSetting(
                help_str="The LLM blueprint to use",
                group_label="generator",
                argument_type=ArgumentType.BLUEPRINT),
            "prompt_generator": ArgumentSetting(
                help_str="The prompt generation blueprint",
                group_label="prompt",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        generator: ComponentDef,
        prompt_generator: ComponentDef
    ):
        self.factory = factory
        self.journal = journal
        # and build the components
        self.generator = self.factory.create(generator)
        self.generator = cast(Generator, self.generator)
        self.prompt_gen = self.factory.create(prompt_generator)
        self.prompt_gen = cast(PromptGenerator, self.prompt_gen)
        self.last_prompt = "not-set"

    def reset(self) -> None:
        """No action as this is a fixed policy."""
        pass

    def invoke(self, state: State) -> Action:
        """Invoke the policy to include tracking for training. The
        policy can chose to explore or exploit in response to the ask.

        Args:
            state (State): The state

        Returns:
            Action: The action to take
        """
        prompt = self.prompt_gen.create_prompt(state)
        self.last_prompt = prompt
        result = self.generator.generate(prompt)
        return Action(
            value=result,
            type=ActionType.STRING)

    def sample(self, state: State) -> Action:
        """Invokes the policy but does not update for training. It only
        seeks to exploit.

        Args:
            state (State): The state

        Returns:
            Action: The action to take
        """
        return self.invoke(state)

    def update(self, reward: float) -> None:
        """Updates a policy using the reward from the environment for
        the last action. NOTE: for this policy this is a NO-OP

        :param reward: The reward from the last action
        :type reward: float
        """
        pass

    def refresh(self) -> None:
        """Refreshes the policy by creating training data based on the
        last epoch. This will be used when there is a model to train.
        If there is nothing to update "refresh" then this is a no-op.
        NOTE: for this policy this is a NO-OP
        """
        pass
