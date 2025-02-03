from .base import RewardFunction, get_cleaned_and_sorted_keys
from .simple import RandomReward, PointFiveReward
from .structure import StructureAdherenceReward, KeyMatchReward

register_list = [
    RandomReward,
    PointFiveReward,
     StructureAdherenceReward,
     KeyMatchReward]
