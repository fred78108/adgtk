"""Foundational structure for generation of data. The overall design is
to establish Protocols for dealing with the generation of data.
"""

from typing import Protocol, runtime_checkable, Union
from adgtk.components import State

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


@runtime_checkable
class Generator(Protocol):
    """Generator Protocol for generating data.
    """

    def create(self, prompt: str) -> str:
        """Create the data.
        """


@runtime_checkable
class PromptGenerator(Protocol):
    """Prompt Generator Protocol for generating data.
    """

    def create_prompt(self, data: Union[str, dict, State]) -> str:
        """create a prompt using the data provided.

        :param data: The data to be used to create the prompt.
        :type data: Union[str, dict, State]
        :return: a language model prompt.
        :rtype: str
        """