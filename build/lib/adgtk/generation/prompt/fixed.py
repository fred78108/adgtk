"""Fixed prompt generators."""

from typing import Union, cast
from adgtk.factory import ObjectFactory, ComponentFeatures
from adgtk.common import (
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType)
from adgtk.generation import PromptGenerator
from adgtk.data import PresentationFormat

# Note:
# https://typing.readthedocs.io/en/latest/spec/protocol.html#protocols
# Explicitly declaring implementation of the protocol even though it is
# not required. Doing so for readability.


class FixedPromptGenerator(PromptGenerator):
    """A fixed policy."""

    description = "Generates a prompt using a pre-defined prefix/suffix."
    blueprint: FactoryBlueprint = FactoryBlueprint(
        group_label='prompt',
        type_label="fixed",
        arguments={
            "prefix": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                help_str="Prompt Prefix",
                default_value="Please create a similar example to: \n"),
            "suffix": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                help_str="Prompt Suffix",
                default_value="\nBut do not copy the contents. Create a unique example."),
            "presentation": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                help_str="What data presentation should be used?",
                default_value="presentation"),
        })

    features = ComponentFeatures(object_factory=True, experiment_journal=False)

    def __init__(
        self,
        prefix: str,
        suffix: str,
        presentation: ComponentDef,
        factory: ObjectFactory
    ):
        self.prefix = prefix
        self.suffix = suffix
        self.factory = factory
        # create the presentation format.
        self.presentation = self.factory.create(presentation)
        self.presentation = cast(PresentationFormat, self.presentation)

    def create_prompt(self, data: Union[str, dict]) -> str:
        """create a prompt using the data provided.

        :param data: The data to be used to create the prompt.
        :type data: Union[str, dict]
        :return: a language model prompt.
        :rtype: str
        """
        if isinstance(data, str):
            return f"{self.prefix}{data}{self.suffix}"

        # more processing is needed.
        return ""
