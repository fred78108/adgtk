"""Shared testing objects. The objects should only be primatives with at
most a reference to a Protocol. This is so as to allow for re-use and
avoid running into issues with failure on imports, etc.

Versions:
v 0.1
- mvp
"""


from dataclasses import dataclass
from adgtk.common import (
    FactoryBlueprint,
    InvalidBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.factory import (
    ObjectFactory)
from adgtk.journals import ExperimentJournal

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

STATIC_STRING_ONE = "fixed-result"
SCENARIO_GROUP_LABEL = "scenario"

# ----------------------------------------------------------------------
# Blueprints to use for testing
# ----------------------------------------------------------------------
TABBY_CAT_BLUEPRINT: FactoryBlueprint = {
    "group_label": "cat",
    "type_label": "tabby",
    "arguments": {
        "count": ArgumentSetting(
            help_str="number of cats",
            default_value=1,
            argument_type=ArgumentType.INT)
    }
}

SIAMESE_CAT_BLUEPRINT = {
    "group_label": "cat",
    "type_label": "siamese",
    "arguments": {
        "count": ArgumentSetting(
            help_str="number of cats",
            default_value=2,
            argument_type=ArgumentType.INT)
    }
}

ORANGE_CAT_BLUEPRINT = {
    "group_label": "cat",
    "type_label": "orange",
    "arguments": {
        "count": ArgumentSetting(
            help_str="number of cats",
            default_value=3,
            argument_type=ArgumentType.INT)
    }
}

PET_BLUEPRINT_HOME = {
    "group_label": "pet",
    "type_label": "home",
    "arguments": {
        "cat": ArgumentSetting(
            help_str="House cat is",
            ArgumentType=ArgumentType.BLUEPRINT,
            default_value="cat")
    }
}


PET_BLUEPRINT_WORK = {
    "group_label": "pet",
    "type_label": "work",
    "arguments": {
        "cat": ArgumentSetting(
            help_str="House cat is",
            ArgumentType=ArgumentType.BLUEPRINT,
            default_value="cat")
    }
}


# Mock Scenario One builds a "pet" with only count.
# this can come in handy when testing a nested build
MOCK_SCENARIO_ONE_BP: FactoryBlueprint = {
    "group_label": SCENARIO_GROUP_LABEL,
    "type_label": "one",
    "arguments": {
        "pet": ArgumentSetting(
            help_str="House cat is",
            ArgumentType=ArgumentType.BLUEPRINT,
            default_value="pet")
    }
}


MOCK_SCENARIO_TWO_BP: FactoryBlueprint = {
    "group_label": SCENARIO_GROUP_LABEL,
    "type_label": "one",
    "arguments": {
        "name": ArgumentSetting(
            help_str="The name",
            ArgumentType=ArgumentType.STRING,
            default_value="birdy"),
        "tree": ArgumentSetting(
            help_str="Tree type",
            ArgumentType=ArgumentType.STRING,
            default_value="birch"),
        "pet":  ArgumentSetting(
            help_str="House cat is",
            ArgumentType=ArgumentType.BLUEPRINT,
            default_value="pet")
    }
}
# ----------------------------------------------------------------------
# Component Definitions - for creation
# ----------------------------------------------------------------------
PET_COMPONENT_DEF_WORK: ComponentDef = {
    "group_label": "pet",
    "type_label": "work",
    "arguments": {
        "cat": {
            "group_label": "cat",
            "type_label": "tabby",
            "arguments": {"count": 1}
        }
    }
}

# Testing of optional key "init_w_object_factory"
TABBY_COMPONENT_DEF: ComponentDef = {
    "group_label": "cat",
    "type_label": "tabby",
    "arguments": {"count": 1}
}


# Mock Scenario One builds a "pet" with only count.
# this can come in handy when testing a nested build
MOCK_SCENARIO_DEF_ONE: ComponentDef = {
    "group_label": SCENARIO_GROUP_LABEL,
    "type_label": "one",
    "arguments": {
        "pet": {
            "group_label": "pet",
            "type_label": "home",
            "arguments": {"count": 6}
        }
    }
}

# MOCK_SCENARIO_ONE requires a "pet"
MOCK_SCENARIO_DEF_ONE_BAD: ComponentDef = {
    "group_label": SCENARIO_GROUP_LABEL,
    "type_label": "one",
    "arguments": {
        "no-pet": {
            "group_label": "pet",
            "type_label": "home",
            "arguments": {"count": 0}
        }
    }
}

MOCK_SCENARIO_DEF_TWO: ComponentDef = {
    "group_label": SCENARIO_GROUP_LABEL,
    "type_label": "one",
    "arguments": {
        "tree": "birch",
        "pet": {
            "group_label": "pet",
            "type_label": "home",
            "name": "birdy",
            "arguments": {"count": 6}
        }
    }
}


# ----------------------------------------------------------------------
# Components to build
# ----------------------------------------------------------------------


class DummyClass:
    """Used for simulating our creation object"""
    description = "testing"
    blueprint: FactoryBlueprint = {
        "group_label": "dummy",
        "type_label": "dummy",
        "arguments": {}
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal
        self.count = 0
        if "count" in args:
            self.count = args["count"]


class PetDummyClass:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = {
        "group_label": "dummy",
        "type_label": "pet",
        "arguments": {}
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        if "cat" in args:
            self.cat = args["cat"]


class TabbyCat:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = TABBY_CAT_BLUEPRINT

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]


class SiameseCat:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = SIAMESE_CAT_BLUEPRINT

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]


class OrangeCat:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = ORANGE_CAT_BLUEPRINT

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]


class PetHome:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = PET_BLUEPRINT_HOME

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]


class PetWork:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = PET_BLUEPRINT_WORK

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]


class MockScenario:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = MOCK_SCENARIO_ONE_BP

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        **args
    ) -> None:
        """A Mock Scenario used for testing. This Scenario provides a
        good example of how to use the factory to create internal
        objects.

        :param factory: The factory to load
        :type factory: ObjectFactory
        :param journal: Not used yet. needed by Protocol
        :type journal: ExperimentJournal
        :raises InvalidBlueprint: When the blueprint is invalid
        """
        self._factory = factory
        self._journal = journal

        self.count = 0
        if "count" in args:
            self.count = args["count"]

        if "pet" in args:
            self.pet = factory.create(args["pet"])
        else:
            raise InvalidBlueprint

        self.scenario_run_count = 0
        self.scenario_preview_count = 0

    def execute(self) -> None:
        """Mock method"""
        self.scenario_run_count += 1

    def preview(self) -> None:
        """Mock method"""
        self.scenario_preview_count += 1


class TabbyOptionalFactoryClass:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = MOCK_SCENARIO_ONE_BP

    def __init__(
        self,
        journal: ExperimentJournal,
        **args
    ) -> None:
        self._journal = journal
        self.count = 0
        if "count" in args:
            self.count = args["count"]


class TabbyOptionalJournalClass:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = MOCK_SCENARIO_ONE_BP

    def __init__(
        self,
        factory: ObjectFactory,
        **args
    ) -> None:
        self._factory = factory
        self.count = 0
        if "count" in args:
            self.count = args["count"]


class TabbyNoOptionalKeysClass:
    """Another mock testing object"""
    description = "testing"
    blueprint: FactoryBlueprint = MOCK_SCENARIO_ONE_BP

    def __init__(
        self,
        **args
    ) -> None:
        self.count = 0
        if "count" in args:
            self.count = args["count"]


# ----------------------------------------------------------------------
# record data
# ----------------------------------------------------------------------
sample_data_one = {
    "name": "alice",
    "age": "24",
    "is_student": True
}

sample_data_two = {
    "name": "bob",
    "age": "25",
    "is_student": True
}

sample_data_three = {
    "name": "charlie",
    "age": "26",
    "is_student": False
}

student_list = [sample_data_one, sample_data_two, sample_data_three]

# longer data strings. useful for measurements, etc.
longer_data_one = {
    "name": "alice",
    "age": 24,
    "background": "Alice lives in a small town and rides a bike to work"
}

longer_data_two = {
    "name": "bob",
    "age": 25,
    "background": "Bob lives in a big city and take the bus to work"
}

longer_data_three = {
    "name": "Charlie",
    "age": "26",
    "education": "Charlie has a Masters Degree in Computer Science"
}


# ----------------------------------------------------------------------
# Re-usable format when content doesn't matter
# ----------------------------------------------------------------------

class FixedPresentationFormat:
    """Presentation format testing"""
    description = "testing"
    blueprint: FactoryBlueprint = {
        "group_label": "presentation",
        "type_label": "fixed",
        "arguments": {}
    }

    def present(self, data: dict) -> str:
        """Mock method"""
        # NO-OP but keeps the linter from complaining
        if data is not None:
            return STATIC_STRING_ONE
        return STATIC_STRING_ONE
