# mypy: ignore-errors
"""_summary_
"""

import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.components.data import RecordStore
from structure import load_record_store_from_csv_file
from adgtk.components import Action, State, ActionType, StateType
from adgtk.factory import ObjectFactory
from adgtk.journals import ExperimentJournal
from reward import RewardFunction


class CsvEnvironment:
    """Environment focused on a presentable record as the state and
    expecting a state of a string. This is a common envirnment for
    generation testing."""

    uses_state_types: list[StateType] = [StateType.PRESENTABLE_RECORD]
    supports_action_types: list[ActionType] = [ActionType.STRING]

    description = "Environment loads a CSV and uses this data as state."
    blueprint: FactoryBlueprint = {
        "group_label": "environment",
        "type_label": "basic",
        "arguments": {
            "record_store": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                group_label="datastore",
                help_str="The data store to use as the states"),
            "reward_function": ArgumentSetting(
                argument_type=ArgumentType.BLUEPRINT,
                group_label="reward",
                help_str="The reward function to use"),
            "max_count": ArgumentSetting(
                argument_type=ArgumentType.INT,
                default_value=0,
                help_str="0=all, else a number to limit the number of states"),
            "random": ArgumentSetting(
                argument_type=ArgumentType.BOOL,
                default_value=False,
                help_str="True: randomize state every epoch"),
            "csv_file": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                default_value="data/file.csv",
                help_str="The CSV to load into the datastore")
        }
    }
    

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        record_store: ComponentDef,
        reward_function: ComponentDef,
        csv_file: str,
        max_count: int = 0,
        random: bool = False
    ):
        self.factory = factory
        self.journal = journal
        self.record_store = self.factory.create(record_store)
        self.reward_func = self.factory.create(reward_function)
        self.max_count = max_count
        self.random = random
        self.state_idx = 0
        self._last_state: State

        # cast for type
        self.datastore = cast(RecordStore, self.record_store)
        # now load
        load_record_store_from_csv_file(
            file_w_path=csv_file, record_store=self.datastore)

        # TODO: Get smarter with this. Perhaps a protocol is needed in
        # the Datastore to state supports state/environment???
        self._states = self.datastore
        self.reward_func = cast(RewardFunction, self.reward_func)
        if len(self._states) == 0:
            logging.error("Zero records loaded")
        elif self.max_count == 0:
            self.max_count = len(self._states)
            if len(self._states) < self.max_count:
                self.max_count = self._states

    def action_space(self) -> list[Action]:
        """Gets a list of acceptable actions

        Returns:
            list[Action]: The acceptable actions
        """
        return []

    def reset(self, value: int = 0) -> tuple[State, bool]:
        """Resets the state

        :param value: The state index., defaults to 0
        :type value: int, optional
        :return: The new state, and rolling over?
        :rtype: tuple[State, bool]
        """
        self.state_idx = value
        self._last_state = State(
            type=StateType.PRESENTABLE_RECORD,
            label="any",
            value=self.datastore[0])

        return self._last_state, False

    def step(self, action: Action) -> tuple[State, bool]:
        """Take an action on the Environment

        Args:
            value (int, optional): _description_. Defaults to 0.

        Returns:
            tuple[State, bool]: the new state and rollover?
        """
        rollover = False
        reward = self.reward_func.calculate(
            last_state=self._last_state,
            last_action=action)

        self.state_idx += 1
        if self.state_idx >= self.max_count:
            self.state_idx = 0
            rollover = True

        self._last_state = State(
            type=StateType.PRESENTABLE_RECORD,
            label="any",
            value=self.datastore[0])
        return self._last_state, reward, rollover
