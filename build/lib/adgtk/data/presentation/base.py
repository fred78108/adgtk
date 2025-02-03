"""_summary_
"""


from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from adgtk.factory.base import (
    ComponentFeatures)

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_presentation.py


@dataclass
class PresentationFeatures(ComponentFeatures):
    """Features that support presentation"""
    structured: bool


@runtime_checkable
class PresentationFormat(Protocol):
    """Provides a base for a presentation """
    features: PresentationFeatures

    def present(self, data: dict) -> str:
        """Presents data based on its configuration

        :param data: the data to be presented
        :type data: dict
        :return: a string in the format configured
        :rtype: str
        """
