"""Foundation for Reward functions"""

from typing import Protocol, Union
from adgtk.common import FactoryBlueprint
from adgtk.components import State, Action
from adgtk.components.data import PresentableRecord
from adgtk.utils import process_possible_yaml

# py -m pytest -s test/component/test_reward.py


class RewardFunction(Protocol):
    blueprint: FactoryBlueprint

    def calculate(self, last_state: State, last_action: Action) -> float:
        """Calculate a reward

        :param state: The state to compare the reward against
        :type state: State
        :param action: The action taken by the Environment
        :type action: Action
        :return: The calculated reward
        :rtype: float
        """


def get_cleaned_and_sorted_keys(
    data: Union[PresentableRecord, dict, list]
) -> list:
    """Utility function that can be used across the different rewards

    :param data: the data to process
    :type data: Union[PresentableRecord, dict, list]
    :return: a list of lists which contains keys
    :rtype: list
    """
    results = []
    if isinstance(data, list):
        for sample in data:
            results.append(get_cleaned_and_sorted_keys(sample))
    elif isinstance(data, str):
        str_data = process_possible_yaml(data)
        for sample in str_data:
            # this should always be the case but as a safety
            if isinstance(sample, dict):
                results.append(list(sample.keys()))
    elif isinstance(data, dict):
        results.append(list(data.keys()))
    elif isinstance(data, PresentableRecord):
        record_data = data.create_copy_of_data()
        results.append(list(record_data.keys()))

    # now process/cleanup so consistent
    cleaned = []
    for keys in results:
        sample = []
        sorted_keys = sorted(keys)
        for key in sorted_keys:
            sample.append(key.lower())
        cleaned.append(sample)

    return cleaned
