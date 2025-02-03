"""Generation specific code."""

from .base import Generator, PromptGenerator
from .prompt import FixedPromptGenerator
from .wrappers import OllamaWrapper


generation_register_list = [
    FixedPromptGenerator,
    OllamaWrapper
]
