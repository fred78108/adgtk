from adgtk.factory import FactoryImplementable
from .base import InvalidMeasurementConfiguration
from .measurements import (
    MeasureItemCount,
    MeasureTextLength,
    MeasureWordCount)
from .comparisons import (
    WordOverlap,
    DataKeyOverlap,
    DataValueOverlap)

from .engine import (
    MeasurementEngine,
    MeasurementSet)

# the ScenarioLoader is looking for register_list. update here to add
# more built-in objects to the factory. MVP uses the ScenarioManager to
# invoke but in the future other runners and managers can use this list.

# tuple is (Class, set_as_default blueprint)
measurement_register_list = [
    MeasureItemCount,
    MeasureTextLength,
    MeasureWordCount,
    WordOverlap,
    DataKeyOverlap,
    DataValueOverlap,
    MeasurementEngine,
    MeasurementSet
]
