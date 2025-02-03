"""_summary_
"""

from typing import Protocol, runtime_checkable, Iterable, Any

# ----------------------------------------------------------------------
# Protocols
# ----------------------------------------------------------------------


@runtime_checkable
class CanMoveToCPU(Protocol):
    """Ensures the model can move to the CPU"""

    def to_cpu(self):
        """Moves the model to the CPU"""


@runtime_checkable
class CanMoveToGPU(Protocol):
    """Ensures the model can move to the GPU"""

    def to_gpu(self):
        """Moves the model to the GPU"""


@runtime_checkable
class CanSaveModel(Protocol):
    """Ensures the model can be saved"""

    def save_model(self, save_folder: str) -> None:
        """Saves the model to disk

        :param save_folder: The folder where the model is saved
        :type save_folder: str
        """


@runtime_checkable
class CanLoadModel(Protocol):
    """Ensures the model can be loaded from disk"""

    def load_model(self, from_folder: str, **kwargs) -> None:
        """Loads the model from disk

        :param from_folder: The folder where the model is saved
        :type from_folder: str
        """


@runtime_checkable
class CanGenerateTextUsingPrompt(Protocol):
    """Provides a consistent interface for wrapping a LLM. This is not
    required when using a LLM, but reduces the amount of code when using
    built-in agents."""

    def generate(self, prompt: str, **kwargs) -> str:
        """Generates text based on the prompt

        :param prompt: the prompt for the model
        :type prompt: str
        :return: the resulting text
        :rtype: str
        """


@runtime_checkable
class TrainableModel(Protocol):
    """A trainable model"""

    def train(self, train_dataset: Iterable, **kwargs) -> None:
        """Trains the model

        :param train_dataset: The dataset to train with
        :type train_dataset: Iterable
        """

    def infer(self, sample: Any, **kwargs) -> Any:
        """Infers from a model

        :param sample: The sample to infer
        :type sample: Any
        :return: the model output
        :rtype: Any
        """
