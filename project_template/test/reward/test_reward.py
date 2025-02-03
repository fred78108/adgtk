"""Testing of rewards"""

import yaml
import pytest
from adgtk.components.base import Action, State, StateType, ActionType
from structure import DataRecord
from reward.base import get_cleaned_and_sorted_keys
from reward.structure import (
    StructureAdherenceReward,
    KeyMatchReward)


# py -m pytest -s test/reward/test_reward.py

# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------

sample_dict_one = {
    "test": "1",
    "a": "b",
    "cat": "1",
    "d": 4
}

sample_dict_two = {
    "test": "1",
    "b": "b",
    "cat": "1",
    "d": 4
}

sample_dict_three = {
    "test": "1",
    "cat": "b",
}
sample_dict_four = {
    "test": "1",
    "z": "b",
}

sample_dict_five = {
    "tEst": "1",
    "A": "b",
    "Cat": "1",
    "d": 4
}

record_one = DataRecord(data=sample_dict_one)
record_two = DataRecord(data=sample_dict_two)

last_state_one = State(
    type=StateType.DICT,
    value=sample_dict_one)

last_state_two = State(
    type=StateType.DICT,
    value=sample_dict_three)

last_state_three = State(
    type=StateType.PRESENTABLE_RECORD,
    value=record_one)


last_action_one = Action(
    value=sample_dict_one,
    type=ActionType.OTHER)

last_action_two = Action(
    value=sample_dict_two,
    type=ActionType.OTHER)

last_action_three = Action(
    value=sample_dict_three,
    type=ActionType.OTHER)

last_action_four = Action(
    value=sample_dict_four,
    type=ActionType.OTHER)

last_action_five = Action(
    type=ActionType.OTHER,
    value=record_two)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(name="string_last_action_one")
def string_last_action_one_fixture():
    data = yaml.safe_dump(sample_dict_one)
    return Action(
        value=data,
        type=ActionType.STRING)


@pytest.fixture(name="string_last_action_two")
def string_last_action_two_fixture():
    data = yaml.safe_dump(sample_dict_two)
    return Action(
        value=data,
        type=ActionType.STRING)


@pytest.fixture(name="string_last_state_one")
def string_last_state_one_fixture():
    data = yaml.safe_dump(sample_dict_one)
    return State(
        type=StateType.STRING,
        value=data)


# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------

def test_dict_match():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_one,
        last_action=last_action_one)

    assert reward == 1


def test_dict_near_match():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_one,
        last_action=last_action_two)

    assert reward == .75


def test_dict_order_one():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_one,
        last_action=last_action_three)

    assert reward == .5


def test_dict_order_two():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_two,
        last_action=last_action_one)

    assert reward == .5


def test_dict_order_three():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_one,
        last_action=last_action_four)

    assert reward == .25


def test_presentation_record():
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=last_state_three,
        last_action=last_action_five)

    assert reward == .75


def test_presentation_record_match(string_last_action_one, string_last_state_one):
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=string_last_state_one,
        last_action=string_last_action_one)

    assert reward == 1


def test_presentation_record_partial_match(string_last_state_one, string_last_action_two):
    reward_func = StructureAdherenceReward()
    reward = reward_func.calculate(
        last_state=string_last_state_one,
        last_action=string_last_action_two)

    assert reward == 0.75


def test_internal_function_get_keys_dict():
    result = get_cleaned_and_sorted_keys(sample_dict_five)
    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert len(result) == 1
    assert len(result[0]) == 4
    assert result[0][0] == 'a'
    assert result[0][1] == 'cat'
    assert result[0][2] == 'd'
    assert result[0][3] == 'test'


def test_key_match_reward_match_dict():
    reward_func = KeyMatchReward()
    reward = reward_func.calculate(
        last_action=last_action_one,
        last_state=last_state_one)
    assert reward == 1


def test_key_match_reward_near_match_dict():
    reward_func = KeyMatchReward()
    reward = reward_func.calculate(
        last_action=last_action_two,
        last_state=last_state_one)
    assert reward == 0


def test_key_match_reward_match_str(
        string_last_action_one, string_last_state_one):
    reward_func = KeyMatchReward()
    reward = reward_func.calculate(
        last_action=string_last_action_one,
        last_state=string_last_state_one)
    assert reward == 1


def test_key_match_reward_nearmatch_str(
        string_last_action_two, string_last_state_one):
    reward_func = KeyMatchReward()
    reward = reward_func.calculate(
        last_action=string_last_action_two,
        last_state=string_last_state_one)
    assert reward == 0
