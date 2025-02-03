""""Rewards that focus on structure"""

import logging
from typing import Union
from adgtk.components.base import State, StateType, Action, ActionType
from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
from adgtk.components import State, Action
from adgtk.components.data import PresentableRecord
from adgtk.utils import process_possible_yaml
from .base import get_cleaned_and_sorted_keys

# py -m pytest -s test/component/test_reward.py


def calculate_overlap(x: list, y: list) -> float:
    counter = 0
    if len(x) > len(y):
        for val in y:
            if val in x:
                counter += 1
        return counter / len(x)

    for val in x:
        if val in y:
            counter += 1
    return counter / len(y)


class RequiredKeyMatchReward:
    """Reward that is based only on the required keys. 1 if all the
    required keys are there, else 0.
    """
    description = "Reward that is based only on the required keys."

    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="required-keys",
        arguments={
            "required_keys": ArgumentSetting(
                argument_type=ArgumentType.LIST,
                help_str="The required keys",
                default_value=[]
            )
        }
    )

    def __init__(self, required_keys: list):
        self.required_keys = required_keys

    def calculate(self, last_state: State, last_action: Action) -> float:
        k_last_action = get_cleaned_and_sorted_keys(last_action.value)
        scores = []
        for action in k_last_action:
            scores.append(calculate_overlap(self.required_keys, action))

        if len(scores) == 0:
            return 0
        return sum(scores) / len(scores)


class KeyMatchReward:
    """Reward of 1 if the keys match, else 0. Does not concern itself
    with the contents, just the keys. If a list it iterates through and
    returns the average.
    """

    description = "A reward that requires an exact key match."

    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="key-match",
        arguments={})

    def calculate(self, last_state: State, last_action: Action) -> float:

        k_last_state = get_cleaned_and_sorted_keys(last_state.value)
        k_last_action = get_cleaned_and_sorted_keys(last_action.value)
        scores = []
        if len(k_last_action) == len(k_last_state):
            for state, action in zip(k_last_state, k_last_action):
                if state == action:
                    scores.append(1)
                else:
                    scores.append(0)
        elif len(k_last_state) == 1:
            for action in k_last_action:
                if k_last_state[0] == action:
                    scores.append(1)
                else:
                    scores.append(0)

        if len(scores) == 0:
            return 0

        return sum(scores)/len(scores)


class StructureAdherenceReward:
    """Measures against the expected keys. Assumes a single record only
    0 = unable to convert string into data
    1 = all keys match
    else ratio of matching. always lower/bigger on count so it can never
    exceed 1.
    """

    description = "A reward that scores based on structure adherence."

    blueprint = FactoryBlueprint(
        group_label="reward",
        type_label="structure",
        arguments={})

    def _get_keys(self, val: Union[PresentableRecord, dict, list, str]) -> list:
        if isinstance(val, PresentableRecord):
            data = val.create_copy_of_data()
        elif isinstance(val, dict):
            data = val
        elif isinstance(val, str):
            possible = process_possible_yaml(val)
            if len(possible) > 0:
                data = possible[0]
            else:
                return []
        # additional protection
        if isinstance(data, dict):
            return list(data.keys())
        else:
            msg = f"StructureAdherenceReward has an unexpected type while "\
                  f"processing. obeserved {type(data)} in _get_keys"
            logging.error(msg)
            return []

    def calculate(self, last_state: State, last_action: Action) -> float:
        # get last state keys
        # expected_keys = self._get_kezys(last_state.value)
        k_last_state = get_cleaned_and_sorted_keys(last_state.value)
        k_last_action = get_cleaned_and_sorted_keys(last_action.value)
        scores = []

        if len(k_last_action) == len(k_last_state):
            for state, action in zip(k_last_state, k_last_action):
                scores.append(calculate_overlap(state, action))
        elif len(k_last_state) == 1:
            for action in k_last_action:
                scores.append(calculate_overlap(k_last_state[0], action))

        if len(scores) == 0:
            return 0
        return sum(scores) / len(scores)
