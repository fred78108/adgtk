from .generation import RLScenario
from .sample import SampleScenario
from .dataset import MeasureDatasetScenario

register_list = [
    RLScenario,
    SampleScenario,
    MeasureDatasetScenario
]   