"""Processing Scenarios are focused on common transformations such as
loading a csv into an internal data store structure."""


# from adgtk.factory.blueprint import FactoryBlueprint, EXPAND_USING_DEFAULT
from adgtk.common import FactoryBlueprint
from adgtk.factory import FactoryImplementable
from .base import SCENARIO_GROUP_LABEL, ScenarioFeatures
# from adgtk.data import DataStoreFeatureFlags, DataStore
# from adgtk.components


class FileProcessingScenario:
    """This scenario processes a file."""

    description = "File processing scenario. ..Under development.."
    blueprint: FactoryBlueprint = {
        "group_label": SCENARIO_GROUP_LABEL,
        "type_label": "file-processing",
        "arguments": {}
    }
    features = ScenarioFeatures(
        object_factory=True,
        experiment_journal=True)
