"""A Study is a collection of experiments.

A Study builds on and is sourced from the common/results.csv for the
metrics and run 0 for the configuration. Tags are labels attached to the
study itself for cataloguing purposes (distinct from per-run experiment tags).

The StudyBlueprint is saved/loaded as a YAML file in the ``studies/``
directory, mirroring how experiment blueprints live in ``blueprints/``.
"""

from pydantic import BaseModel


class StudyBlueprint(BaseModel):
    name: str
    description: str = ""
    tags: list[str] = []
    experiments: list[str] = []
