"""Generation specific code."""

from .base import Generator, PromptGenerator
from .prompt import FixedPromptGenerator
from .wrappers import OllamaWrapper


register_list = [
    FixedPromptGenerator,
    OllamaWrapper
]
