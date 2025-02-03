"""_summary_
"""

import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.journals import ExperimentJournal
from adgtk.factory import ComponentFeatures, ObjectFactory
from adgtk.generation import Generator, PromptGenerator
from adgtk.components import Action, State, StateType
from adgtk.common import InvalidScenarioState
# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py

# TODO: move from string rep to get data keys and prompt uses keys only!


class FixedGenerationPolicy:

    description = "Policy that doesn'tlearn. Generates text using the state"

    blueprint: FactoryBlueprint = {
        "group_label": "policy",
        "type_label": "fixed_gen",
        "arguments": {
            "generator": ArgumentSetting(
                help_str="The LLM blueprint to use",
                default_value="generator",
                argument_type=ArgumentType.BLUEPRINT),
            "prompt_generator": ArgumentSetting(
                help_str="The prompt generation blueprint",
                default_value="prompt",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    features = ComponentFeatures(
        object_factory=True, experiment_journal=True)

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
        prompt = ""
        if state.type == StateType.PRESENTABLE_RECORD:
            # convert presentable record to string, then send to prompt gen
            prompt = self.prompt_gen.create_prompt(f"{state.value}")
        elif state.type == StateType.STRING:
            prompt = self.prompt_gen.create_prompt(state.value)
        else:
            msg = f"valid State type for policy: {state.type.name}"
            logging.error(msg)
            raise InvalidScenarioState(msg)

        result = self.generator.generate(prompt)
        return result

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
