"""Fixed prompt generators."""

from typing import Union, cast
from adgtk.factory import ObjectFactory
from adgtk.common import (
    InvalidScenarioState,
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType)
from adgtk.components import State, StateType
from adgtk.components.data import PresentableRecord
from generation import PromptGenerator
from adgtk.components.data import PresentationFormat

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
                argument_type=ArgumentType.ML_STRING,
                help_str="Prompt Prefix",
                default_value="Please create a similar example to: "),
            "suffix": ArgumentSetting(
                argument_type=ArgumentType.ML_STRING,
                help_str="Prompt Suffix",
                default_value=" But do not copy the contents. Create a unique example."),
            "presentation": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                help_str="What data presentation should be used?",
                group_label="presentation"),
            "override_record_presentation": ArgumentSetting(
                argument_type=ArgumentType.BOOL,
                help_str="Use the built-in or override the presentation?",
                default_value=True)
        })

    def __init__(
        self,
        prefix: str,
        suffix: str,
        override_record_presentation: bool,
        presentation: ComponentDef,
        factory: ObjectFactory
    ):
        self.prefix = prefix
        self.suffix = suffix
        self.factory = factory
        # create the presentation format.
        self.presentation = self.factory.create(presentation)
        self.presentation = cast(PresentationFormat, self.presentation)
        self.override_record_presentation = override_record_presentation

    def create_prompt(self, data: Union[str, dict, State]) -> str:
        """create a prompt using the data provided.

        :param data: The data to be used to create the prompt.
        :type data: Union[str, dict, State]
        :return: a language model prompt.
        :rtype: str
        """
        converted = "NOT_SET"
        if isinstance(data, State):
            if data.type == StateType.STRING:
                converted = data.value
            elif data.type == StateType.DICT:
                converted = self.presentation.present(data.value)
            elif data.type == StateType.PRESENTABLE_RECORD:
                record = data.value
                record = cast(PresentableRecord, record)
                if self.override_record_presentation:
                    converted = self.presentation.present(
                        record.create_copy_of_data())
                else:
                    converted = f"{data.value}"
        elif isinstance(data, dict):
            converted = self.presentation.present(dict)
        elif isinstance(data, str):
            converted = data
        else:
            raise InvalidScenarioState(f"Unexpected data type: {type(data)}")

        prompt = f"{self.prefix} {converted} {self.suffix}"
        return prompt
