"""common components"""
from adgtk.factory import FactoryImplementable
from .base import Action, State, ActionType, StateType
from .agent import BasicAgent, Agent, GenerationAgent
from .environment import CsvEnvironment, Environment, FixedDictEnvironment
from .policy import RandomPolicy, FixedGenerationPolicy
from .processing import CsvToDataStoreProcessor, Processor
from .reward import RandomReward, RewardFunction, PointFiveReward


# ----------------------------------------------------------------------
# Built-in object support
# ----------------------------------------------------------------------

# the ScenarioLoader is looking for register_list. update here to add
# more built-in objects to the factory. MVP uses the ScenarioManager to
# invoke but in the future other runners and managers can use this list.

component_register_list = [
    BasicAgent,
    CsvEnvironment,
    RandomPolicy,
    FixedGenerationPolicy,
    CsvToDataStoreProcessor,
    PointFiveReward,
    RandomReward,
    GenerationAgent,
    FixedDictEnvironment
]
