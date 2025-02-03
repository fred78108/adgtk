"""test_scenario_manager.py created"""
from dataclasses import dataclass
from typing import List
from adgtk.factory import FactoryImplementable


@dataclass
class MockFeatures:
    use: bool = False
    object_factory: bool = False
    experiment_journal: bool = False


class DummyClass:
    description = "test"
    blueprint = {
        "group_label": "dummy",
        "type_label": "dummy",
        "arguments": {}
    }
    features = MockFeatures()

    def __init__(
        self,
        **args
    ) -> None:
        self.count = 0
        if "count" in args:
            self.count = args["count"]


register_list: List[tuple] = [DummyClass]
