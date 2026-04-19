"""Common structure. This module is used to define the common structures
that are used throughout the package.
"""
from typing import Protocol
from pydantic import BaseModel


class ResultsFile(BaseModel):
    filename: str
    purpose: str


class ScenarioResult(BaseModel):
    files_written: list[ResultsFile]


class Scenario(Protocol):
    """The Scenario is the root of any experiment"""
    def start_scenario(self) -> ScenarioResult: ...
